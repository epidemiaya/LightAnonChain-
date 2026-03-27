#!/usr/bin/env python3
"""
Nulla — Local Server
Flask JSON API + React SPA
Binds to 127.0.0.1 only (localhost-only, never exposed to network).
Run: python nulla_server.py [--port 7421] [--testnet]
"""

import os
import json
import time
import secrets
import threading
import webbrowser
import argparse
from pathlib import Path
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory, session

from nulla_core import (
    NullaWallet, NullaError, KeystoreError, WalletError,
    validate_address, format_btc
)
from nulla_electrum import ElectrumClient, ElectrumError
from nulla_tx import build_send_tx, UTXO, estimate_fee

try:
    from flask_cors import CORS
    _HAS_CORS = True
except ImportError:
    _HAS_CORS = False

# ── App config ────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="ui/dist", static_url_path="")
app.secret_key = secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY  = True,
    SESSION_COOKIE_SAMESITE  = "Lax",
    SESSION_COOKIE_SECURE    = False,  # localhost only
    PERMANENT_SESSION_LIFETIME = 3600,
)

if _HAS_CORS:
    CORS(app, origins=["http://localhost:5173", "http://localhost:7421"],
         supports_credentials=True)

DEFAULT_KEYSTORE = str(Path.home() / ".nulla" / "wallet.nulla")

# Global state
_wallet: NullaWallet = None
_electrum: ElectrumClient = None
_network: str = "mainnet"

# Simple TTL cache — avoids hammering ElectrumX on every page load
import time as _time
_cache: dict = {}
_CACHE_TTL = 60  # seconds

def _cache_get(key):
    entry = _cache.get(key)
    if entry and (_time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["val"]
    return None

def _cache_set(key, val):
    _cache[key] = {"val": val, "ts": _time.time()}

def _cache_clear():
    _cache.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

def err(msg: str, code: int = 400):
    return jsonify({"ok": False, "error": str(msg)}), code

def ok(**kw):
    return jsonify({"ok": True, **kw})

def require_unlocked(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _wallet is None or not _wallet._unlocked:
            return err("Wallet locked", 401)
        return f(*args, **kwargs)
    return wrapper

# ── Connection pool ───────────────────────────────────────────────────────────
# ElectrumX is sequential JSON-RPC over one TCP socket.
# For parallel queries we need N independent connections.

import threading as _threading
_pool_lock  = _threading.Lock()
_conn_pool  = []   # list of connected ElectrumClient instances
POOL_SIZE   = 4    # 4 parallel connections is enough

def _get_electrum() -> ElectrumClient:
    """Get or create a single shared client (for single queries)."""
    global _electrum
    if _electrum is None:
        _electrum = ElectrumClient(network=_network)
    if not _electrum.is_connected:
        _electrum.connect()
    return _electrum

def _get_pool() -> list:
    """Get or create a pool of N connected ElectrumClient instances."""
    global _conn_pool
    with _pool_lock:
        # Remove dead connections
        _conn_pool = [c for c in _conn_pool if c.is_connected]
        # Fill pool up to POOL_SIZE
        while len(_conn_pool) < POOL_SIZE:
            try:
                c = ElectrumClient(network=_network)
                c.connect()
                _conn_pool.append(c)
            except Exception:
                break
        return list(_conn_pool)

def _query_parallel(scripthashes: list, method: str) -> dict:
    """
    Query multiple scripthashes in parallel using connection pool.
    Returns {scripthash: result}.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    pool    = _get_pool()
    n       = len(pool)
    results = {}

    if not pool:
        # Fallback: single connection sequential
        el = _get_electrum()
        for sh in scripthashes:
            try:
                results[sh] = el.call(method, [sh])
            except Exception:
                results[sh] = None
        return results

    def fetch(sh, conn):
        try:
            return sh, conn.call(method, [sh])
        except Exception:
            return sh, None

    with ThreadPoolExecutor(max_workers=n) as executor:
        futs = [
            executor.submit(fetch, sh, pool[i % n])
            for i, sh in enumerate(scripthashes)
        ]
        for f in as_completed(futs):
            sh, val = f.result()
            results[sh] = val

    return results

def _all_utxos_for_wallet() -> list:
    """Fetch UTXOs for all wallet addresses in parallel."""
    addrs  = _wallet.all_addresses()
    sh_map = {a.electrum_scripthash: a for a in addrs}
    raw    = _query_parallel(list(sh_map.keys()), "blockchain.scripthash.listunspent")

    utxo_list = []
    for sh, utxos in raw.items():
        if not utxos:
            continue
        addr = sh_map[sh]
        for u in utxos:
            utxo_list.append(UTXO(
                txid    = u["tx_hash"],
                vout    = u["tx_pos"],
                value   = u["value"],
                address = addr,
                height  = u.get("height", 0),
            ))
    return utxo_list


# ── API: system ───────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    ks = session.get("keystore_path", DEFAULT_KEYSTORE)
    return ok(
        wallet_exists   = Path(ks).exists(),
        wallet_unlocked = bool(_wallet and _wallet._unlocked),
        network         = _network,
        version         = "1.0.0",
    )


# ── API: wallet lifecycle ──────────────────────────────────────────────────────

@app.route("/api/wallet/create", methods=["POST"])
def api_create():
    global _wallet
    d  = request.json or {}
    pw = d.get("password", "")
    if len(pw) < 8:
        return err("Password must be at least 8 characters")
    ks_path = d.get("keystore", DEFAULT_KEYSTORE)
    try:
        w = NullaWallet.generate(pw, network=_network)
        Path(ks_path).parent.mkdir(parents=True, exist_ok=True)
        w.save(ks_path, pw)
        _wallet = w
        session["keystore_path"] = ks_path
        return ok(
            address  = w.address,
            mnemonic = w.mnemonic,
            accounts = w.all_accounts_summary(),
        )
    except Exception as e:
        return err(str(e))


@app.route("/api/wallet/import", methods=["POST"])
def api_import():
    global _wallet
    d        = request.json or {}
    mnemonic = d.get("mnemonic", "").strip()
    pw       = d.get("password", "")
    if not mnemonic: return err("Mnemonic required")
    if len(pw) < 8:  return err("Min 8 characters")
    ks_path = d.get("keystore", DEFAULT_KEYSTORE)
    try:
        w = NullaWallet.from_mnemonic(mnemonic, pw, network=_network)
        Path(ks_path).parent.mkdir(parents=True, exist_ok=True)
        w.save(ks_path, pw)
        _wallet = w
        session["keystore_path"] = ks_path
        return ok(address=w.address, accounts=w.all_accounts_summary())
    except WalletError as e:
        return err(str(e))


@app.route("/api/wallet/unlock", methods=["POST"])
def api_unlock():
    global _wallet
    d  = request.json or {}
    pw = d.get("password", "")
    ks = d.get("keystore", session.get("keystore_path", DEFAULT_KEYSTORE))
    try:
        w = NullaWallet.load(ks, pw)
        _wallet = w
        session["keystore_path"] = ks
        return ok(address=w.address, network=w.network)
    except KeystoreError as e:
        return err(str(e), 401)


@app.route("/api/wallet/lock", methods=["POST"])
def api_lock():
    global _wallet
    if _wallet:
        _wallet.lock()
        _wallet = None
    return ok()


@app.route("/api/wallet/info")
@require_unlocked
def api_info():
    return ok(
        address  = _wallet.address,
        network  = _wallet.network,
        accounts = _wallet.all_accounts_summary(),
        metadata = _wallet.metadata,
    )


# ── API: addresses ───────────────────────────────────────────────────────────

@app.route("/api/addresses")
@require_unlocked
def api_addresses():
    """All addresses with balances, grouped by type."""
    cache_key = f"addrs_{_wallet.address}"
    cached = _cache_get(cache_key)
    if cached:
        return jsonify({"ok": True, "groups": cached, "cached": True})
    try:
        summary   = _wallet.all_accounts_summary()
        addrs     = _wallet.all_addresses()
        sh_map    = {a.electrum_scripthash: a for a in addrs}
        balances  = _query_parallel(list(sh_map.keys()), "blockchain.scripthash.get_balance")

        # Build addr→balance lookup
        bal_map = {}
        for sh, b in balances.items():
            addr_obj = sh_map.get(sh)
            if addr_obj:
                bal_map[addr_obj.address] = {
                    "confirmed":   (b or {}).get("confirmed", 0),
                    "unconfirmed": (b or {}).get("unconfirmed", 0),
                }

        # Inject balances into summary
        for group in summary:
            for a in group["addresses"]:
                b = bal_map.get(a["address"], {"confirmed": 0, "unconfirmed": 0})
                a["confirmed"]   = b["confirmed"]
                a["unconfirmed"] = b["unconfirmed"]
                a["has_balance"] = b["confirmed"] + b["unconfirmed"] > 0

        _cache_set(cache_key, summary)
        return ok(groups=summary)
    except Exception as e:
        return err(str(e))


@app.route("/api/scan", methods=["POST"])
@require_unlocked
def api_scan():
    """Gap limit scan — discover all used addresses like Electrum does on restore."""
    try:
        el      = _get_electrum()
        total   = _wallet.scan_gap_limit(el, gap=20)
        _cache_clear()
        return ok(scanned=total, message=f"Scanned {total} addresses")
    except Exception as e:
        return err(str(e))


# ── API: balance ──────────────────────────────────────────────────────────────

@app.route("/api/balance")
@require_unlocked
def api_balance():
    cache_key = f"balance_{_wallet.address}"
    cached = _cache_get(cache_key)
    if cached:
        return jsonify({"ok": True, **cached, "cached": True})
    try:
        addrs  = _wallet.all_addresses()
        sh_map = {a.electrum_scripthash: a for a in addrs}
        raw    = _query_parallel(list(sh_map.keys()), "blockchain.scripthash.get_balance")

        confirmed = unconfirmed = 0
        for val in raw.values():
            if val:
                confirmed   += val.get("confirmed", 0)
                unconfirmed += val.get("unconfirmed", 0)

        result = dict(
            confirmed   = confirmed,
            unconfirmed = unconfirmed,
            total       = confirmed + unconfirmed,
            formatted   = format_btc(confirmed + unconfirmed),
            address     = _wallet.address,
        )
        _cache_set(cache_key, result)
        return ok(**result)
    except Exception as e:
        return err(str(e))


# ── API: UTXOs ────────────────────────────────────────────────────────────────

@app.route("/api/utxos")
@require_unlocked
def api_utxos():
    try:
        utxos = _all_utxos_for_wallet()
        return ok(utxos=[{
            "txid":    u.txid,
            "vout":    u.vout,
            "value":   u.value,
            "address": u.address.address,
            "height":  u.height,
            "type":    u.address.addr_type,
        } for u in utxos])
    except ElectrumError as e:
        return err(str(e))


# ── Per-TX detail cache (survives across requests, TTL 10 min) ────────────────
_tx_detail_cache: dict = {}
_TX_CACHE_TTL = 600  # confirmed txs don't change — cache 10 min

def _tx_cache_get(txid: str):
    e = _tx_detail_cache.get(txid)
    if e and (_time.time() - e["ts"]) < _TX_CACHE_TTL:
        return e["val"]
    return None

def _tx_cache_set(txid: str, val: dict):
    _tx_detail_cache[txid] = {"val": val, "ts": _time.time()}


# ── API: transactions ─────────────────────────────────────────────────────────

@app.route("/api/transactions")
@require_unlocked
def api_transactions():
    from concurrent.futures import ThreadPoolExecutor
    limit = int(request.args.get("limit", 25))
    cache_key = f"txs_{_wallet.address}_{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return jsonify({"ok": True, "transactions": cached, "cached": True})
    try:
        addrs        = _wallet.all_addresses()
        my_addrs     = {a.address for a in addrs}
        scripthashes = [a.electrum_scripthash for a in addrs]

        # Step 1: history in parallel (fast — no verbose)
        history = _query_parallel(scripthashes, "blockchain.scripthash.get_history")
        all_txs = []
        seen = set()
        for sh, items in history.items():
            for item in (items or []):
                if item["tx_hash"] not in seen:
                    seen.add(item["tx_hash"])
                    all_txs.append(item)
        all_txs.sort(key=lambda x: -(x.get("height") or 9_999_999))
        all_txs = all_txs[:limit]

        if not all_txs:
            _cache_set(cache_key, [])
            return ok(transactions=[])

        # Step 2: fetch tx details — use per-tx cache, skip confirmed hits
        pool_conns = _get_pool()
        n = max(1, len(pool_conns))

        def fetch_tx(args):
            item, conn_idx = args
            txid      = item["tx_hash"]
            height    = item.get("height", 0)
            confirmed = (height or 0) > 0

            # Hit per-tx cache for confirmed txs (they never change)
            if confirmed:
                cached_tx = _tx_cache_get(txid)
                if cached_tx:
                    return cached_tx

            try:
                conn = pool_conns[conn_idx % n]
                raw  = conn.get_transaction(txid, verbose=True)
                total = 0
                if isinstance(raw, dict):
                    for vout in raw.get("vout", []):
                        spk  = vout.get("scriptPubKey", {})
                        addr = (spk.get("address") or
                                (spk.get("addresses") or [None])[0])
                        if addr and addr in my_addrs:
                            total += int(vout.get("value", 0) * 1e8)
                result = {
                    "txid":      txid,
                    "height":    height,
                    "confirmed": confirmed,
                    "amount":    total,
                    "direction": "in" if total > 0 else "out",
                }
                if confirmed:
                    _tx_cache_set(txid, result)
                return result
            except Exception:
                return {
                    "txid":      txid,
                    "height":    height,
                    "confirmed": confirmed,
                    "amount":    0,
                    "direction": "unknown",
                }

        with ThreadPoolExecutor(max_workers=n) as pool:
            result = list(pool.map(fetch_tx,
                [(item, i) for i, item in enumerate(all_txs)]))

        _cache_set(cache_key, result)
        return ok(transactions=result)
    except ElectrumError as e:
        return err(str(e))


# ── API: fee estimate ─────────────────────────────────────────────────────────

@app.route("/api/fee")
def api_fee():
    blocks = int(request.args.get("blocks", 3))
    try:
        el       = _get_electrum()
        fee_rate = el.estimate_fee(blocks)
        return ok(fee_rate=fee_rate, blocks=blocks, unit="sat/vbyte")
    except ElectrumError as e:
        return err(str(e))


# ── API: send ─────────────────────────────────────────────────────────────────

@app.route("/api/send", methods=["POST"])
@require_unlocked
def api_send():
    d          = request.json or {}
    to         = d.get("to", "").strip()
    amount_btc = d.get("amount")
    fee_rate   = int(d.get("fee_rate", 5))

    if not to:
        return err("Recipient address required")
    if not validate_address(to, _wallet.network):
        return err(f"Invalid Bitcoin address: {to}")

    try:
        amount_sats = int(float(amount_btc) * 1e8)
    except (TypeError, ValueError):
        return err("Invalid amount")

    if amount_sats <= 0:
        return err("Amount must be positive")

    try:
        # Get UTXOs
        utxos = _all_utxos_for_wallet()
        if not utxos:
            return err("No spendable UTXOs")

        change_addr = _wallet.change_address("p2wpkh")

        raw_hex, fee_sats, change_sats = build_send_tx(
            all_utxos      = utxos,
            to_address     = to,
            amount_sats    = amount_sats,
            change_address = change_addr,
            fee_rate       = fee_rate,
        )

        # Broadcast
        el   = _get_electrum()
        txid = el.broadcast(raw_hex)

        _cache_clear()  # invalidate balance/tx cache after send
        return ok(
            txid       = txid,
            amount     = amount_sats,
            fee        = fee_sats,
            change     = change_sats,
            formatted  = format_btc(amount_sats),
        )
    except Exception as e:
        return err(str(e))


# ── API: preview transaction (without broadcast) ──────────────────────────────

@app.route("/api/send/preview", methods=["POST"])
@require_unlocked
def api_send_preview():
    """Returns fee estimate before confirming send."""
    d          = request.json or {}
    to         = d.get("to", "").strip()
    amount_btc = d.get("amount")
    fee_rate   = int(d.get("fee_rate", 5))

    if not to or not amount_btc:
        return err("Address and amount required")

    try:
        amount_sats = int(float(amount_btc) * 1e8)
        utxos       = _all_utxos_for_wallet()
        total_sats  = sum(u.value for u in utxos)

        from nulla_tx import select_utxos
        selected, fee = select_utxos(utxos, amount_sats, fee_rate)

        return ok(
            amount      = amount_sats,
            fee         = fee,
            total       = amount_sats + fee,
            change      = sum(u.value for u in selected) - amount_sats - fee,
            balance     = total_sats,
            fee_rate    = fee_rate,
            inputs_used = len(selected),
        )
    except Exception as e:
        return err(str(e))


# ── API: node ─────────────────────────────────────────────────────────────────

@app.route("/api/node/status")
def api_node_status():
    try:
        el = _get_electrum()
        si = el.server_info or {}
        # Use cached info — no reconnect, instant response
        if el.is_connected and si:
            return ok(
                connected  = True,
                server     = si.get("host"),
                port       = si.get("port"),
                protocol   = si.get("protocol"),
                height     = _get_electrum().get_block_height(),
                latency_ms = 0,
            )
        return ok(connected=False, error="Not connected")
    except Exception as e:
        return ok(connected=False, error=str(e))


# ── Static SPA ────────────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    dist = app.static_folder
    if path and Path(dist, path).is_file():
        return send_from_directory(dist, path)
    index = Path(dist, "index.html")
    if index.exists():
        return send_from_directory(dist, "index.html")
    return (
        "<pre style='font:13px monospace;padding:2em;background:#080808;color:#d4d4d4'>"
        "Nulla UI not built.\n\n"
        "Run:\n  cd ui && npm install && npm run build\n\n"
        "Dev mode:\n  cd ui && npm run dev  (port 5173)\n"
        "</pre>"
    ), 200


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _network

    parser = argparse.ArgumentParser(description="Nulla Bitcoin Wallet")
    parser.add_argument("--port",       type=int, default=7421)
    parser.add_argument("--host",       default="127.0.0.1")
    parser.add_argument("--testnet",    action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    _network = "testnet" if args.testnet else "mainnet"

    print(f"""
  ╔╗╔╦ ╦╦  ╦  ╔═╗
  ║║║║ ║║  ║  ╠═╣
  ╝╚╝╚═╝╩═╝╩═╝╩ ╩  Bitcoin Light Wallet v1.0.0
  ─────────────────────────────────────────────
  UI:       http://localhost:{args.port}
  Network:  {_network.upper()}
  Keystore: {DEFAULT_KEYSTORE}
  Ctrl+C to stop
""")

    if not args.no_browser:
        def _open():
            time.sleep(1.2)
            webbrowser.open(f"http://localhost:{args.port}")
        threading.Thread(target=_open, daemon=True).start()

    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
