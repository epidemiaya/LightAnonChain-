"""
Nulla — ElectrumX Protocol Client
Connects to public ElectrumX servers via SSL TCP.
Implements the Electrum JSON-RPC protocol (newline-delimited).

Note: ElectrumX servers commonly use self-signed certificates.
We disable hostname/cert verification (standard practice for Electrum clients)
but still use SSL for transport encryption.
"""

import ssl
import json
import socket
import time
import threading
import random
from typing import Any, Dict, List, Optional, Tuple

# Public ElectrumX servers — (host, ssl_port)
# Many use self-signed certs — this is normal for ElectrumX
MAINNET_SERVERS = [
    ("electrum.blockstream.info",  700),
    ("fortress.qtornado.com",      443),
    ("electrum.emzy.de",           50002),
    ("bitcoin.aranguren.org",      50002),
    ("electrum.jochen-hoenicke.de",50006),
    ("btc.electroncash.dk",        60002),
    ("electrum.bitaroo.net",       50002),
    ("electrum2.bitaroo.net",      50002),
    ("electrum1.bluewallet.io",    443),
    ("e.keff.org",                 50002),
]

TESTNET_SERVERS = [
    ("testnet.aranguren.org",      51002),
    ("testnet.qtornado.com",       51002),
    ("electrum.blockstream.info",  993),
]

NULLA_USER_AGENT = "Nulla/1.0.0"
ELECTRUM_PROTOCOL = "1.4"
CONNECT_TIMEOUT   = 5   # fail fast → try next server
REQUEST_TIMEOUT   = 8


class ElectrumError(Exception):
    pass

class ElectrumConnectionError(ElectrumError):
    pass

class ElectrumRPCError(ElectrumError):
    def __init__(self, msg: str, code: int = 0):
        super().__init__(msg)
        self.code = code


class ElectrumClient:
    """
    Thread-safe ElectrumX client.
    Connects to the first reachable server from the list.
    Auto-reconnects on failure.
    """

    def __init__(self, network: str = "mainnet", servers: List[Tuple] = None):
        self.network      = network
        self._servers     = servers or (MAINNET_SERVERS if network == "mainnet" else TESTNET_SERVERS)
        self._sock        = None
        self._ssl_sock    = None
        self._lock        = threading.Lock()
        self._req_id      = 0
        self._connected   = False
        self._server_info: Optional[Dict] = None
        self._buf         = b""

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, shuffle: bool = False) -> Dict:
        """
        Try each server in priority order until one connects.
        shuffle=False keeps the fast servers first.
        Returns server info dict.
        Raises ElectrumConnectionError if all fail.
        """
        servers = list(self._servers)
        if shuffle:
            random.shuffle(servers)

        last_err = None
        for host, port in servers:
            try:
                self._do_connect(host, port)
                info = self._handshake()
                self._connected   = True
                self._server_info = {"host": host, "port": port, **info}
                return self._server_info
            except Exception as e:
                last_err = e
                self._cleanup()
                continue

        raise ElectrumConnectionError(
            f"All {len(servers)} ElectrumX servers unreachable. Last: {last_err}"
        )

    def _do_connect(self, host: str, port: int):
        # ElectrumX servers commonly use self-signed certificates.
        # All Electrum clients (including the official one) disable cert
        # verification by default. We still use SSL for encryption.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

        raw = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT)
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._ssl_sock = ctx.wrap_socket(raw, server_hostname=host)
        self._ssl_sock.settimeout(REQUEST_TIMEOUT)
        self._buf = b""

    def _handshake(self) -> Dict:
        resp = self._call("server.version", [NULLA_USER_AGENT, ELECTRUM_PROTOCOL])
        return {"server_version": resp[0], "protocol": resp[1]}

    def disconnect(self):
        self._connected = False
        self._cleanup()

    def _cleanup(self):
        try:
            if self._ssl_sock:
                self._ssl_sock.close()
        except Exception:
            pass
        self._ssl_sock = None
        self._buf      = b""

    def _ensure_connected(self):
        if not self._connected or self._ssl_sock is None:
            self.connect()

    # ── JSON-RPC transport ────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _send(self, obj: dict):
        line = json.dumps(obj) + "\n"
        self._ssl_sock.sendall(line.encode())

    def _recv_line(self) -> dict:
        while b"\n" not in self._buf:
            chunk = self._ssl_sock.recv(4096)
            if not chunk:
                raise ElectrumConnectionError("Server closed connection")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line.decode())

    def _call(self, method: str, params: list = None) -> Any:
        req_id = self._next_id()
        req    = {"id": req_id, "method": method, "params": params or []}
        self._send(req)
        # Drain any subscription messages before our response
        for _ in range(10):
            resp = self._recv_line()
            if resp.get("id") == req_id:
                if "error" in resp and resp["error"]:
                    err = resp["error"]
                    msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                    raise ElectrumRPCError(msg, err.get("code", 0) if isinstance(err, dict) else 0)
                return resp.get("result")
        raise ElectrumConnectionError("No matching response received")

    def call(self, method: str, params: list = None, retry: int = 2) -> Any:
        """Public call with auto-reconnect."""
        with self._lock:
            for attempt in range(retry + 1):
                try:
                    self._ensure_connected()
                    return self._call(method, params)
                except ElectrumRPCError:
                    raise  # Don't retry RPC errors
                except Exception as e:
                    self._cleanup()
                    self._connected = False
                    if attempt == retry:
                        raise ElectrumConnectionError(f"Call failed after {retry+1} attempts: {e}")
                    time.sleep(1.5 ** attempt)

    # ── Bitcoin API ───────────────────────────────────────────────────────────

    def get_balance(self, scripthash: str) -> Dict:
        """
        Returns {"confirmed": sats, "unconfirmed": sats}
        """
        result = self.call("blockchain.scripthash.get_balance", [scripthash])
        return {
            "confirmed":   result.get("confirmed", 0),
            "unconfirmed": result.get("unconfirmed", 0),
            "total":       result.get("confirmed", 0) + result.get("unconfirmed", 0),
        }

    def get_history(self, scripthash: str) -> List[Dict]:
        """Returns list of {tx_hash, height, fee?}"""
        return self.call("blockchain.scripthash.get_history", [scripthash]) or []

    def get_utxos(self, scripthash: str) -> List[Dict]:
        """
        Returns list of UTXOs:
        {tx_hash, tx_pos, height, value}
        """
        return self.call("blockchain.scripthash.listunspent", [scripthash]) or []

    def get_transaction(self, txid: str, verbose: bool = False) -> Any:
        """Get raw transaction hex (verbose=False) or dict (verbose=True)."""
        return self.call("blockchain.transaction.get", [txid, verbose])

    def broadcast(self, raw_tx_hex: str) -> str:
        """Broadcast raw transaction. Returns txid."""
        return self.call("blockchain.transaction.broadcast", [raw_tx_hex])

    def estimate_fee(self, blocks: int = 3) -> int:
        """
        Estimate fee rate in sat/byte for confirmation within `blocks` blocks.
        Returns integer sat/byte (minimum 1).
        """
        btc_per_kb = self.call("blockchain.estimatefee", [blocks])
        if not btc_per_kb or btc_per_kb < 0:
            return 5  # Fallback: 5 sat/byte
        # Convert BTC/kB → sat/byte
        sat_per_byte = int(btc_per_kb * 1e8 / 1000)
        return max(1, sat_per_byte)

    def get_block_height(self) -> int:
        """Current best block height."""
        result = self.call("blockchain.headers.subscribe")
        if isinstance(result, dict):
            return result.get("height", 0)
        return 0

    # ── Multi-address operations ──────────────────────────────────────────────

    def get_balance_multi(self, scripthashes: List[str]) -> Dict[str, Dict]:
        """Fetch balance for multiple scripthashes."""
        result = {}
        for sh in scripthashes:
            try:
                result[sh] = self.get_balance(sh)
            except ElectrumError:
                result[sh] = {"confirmed": 0, "unconfirmed": 0, "total": 0}
        return result

    def get_utxos_multi(self, scripthashes: List[str]) -> List[Dict]:
        """Aggregate UTXOs for multiple scripthashes."""
        all_utxos = []
        for sh in scripthashes:
            try:
                utxos = self.get_utxos(sh)
                for u in utxos:
                    u["scripthash"] = sh
                all_utxos.extend(utxos)
            except ElectrumError:
                pass
        return all_utxos

    def get_history_multi(self, scripthashes: List[str]) -> List[Dict]:
        """Aggregate tx history for multiple scripthashes."""
        seen   = set()
        result = []
        for sh in scripthashes:
            try:
                for tx in self.get_history(sh):
                    if tx["tx_hash"] not in seen:
                        tx["scripthash"] = sh
                        result.append(tx)
                        seen.add(tx["tx_hash"])
            except ElectrumError:
                pass
        # Sort by height descending (newest first), unconfirmed (height=0) first
        result.sort(key=lambda x: -x.get("height", 9_999_999))
        return result

    # ── Server info ───────────────────────────────────────────────────────────

    def test_connection(self) -> Dict:
        t0 = time.time()
        try:
            info = self.connect(shuffle=True)
            latency = int((time.time() - t0) * 1000)
            height  = self.get_block_height()
            return {
                "connected":  True,
                "server":     info.get("host"),
                "port":       info.get("port"),
                "protocol":   info.get("protocol"),
                "height":     height,
                "latency_ms": latency,
            }
        except ElectrumError as e:
            return {"connected": False, "error": str(e)}

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ssl_sock is not None

    @property
    def server_info(self) -> Optional[Dict]:
        return self._server_info
