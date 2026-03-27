#!/usr/bin/env python3
"""
Nulla — Bitcoin Wallet CLI

Usage:
  nulla create             Create new wallet
  nulla import [words...]  Restore from mnemonic
  nulla balance            Show BTC balance
  nulla receive            Show receive address
  nulla send <to> <btc>    Send BTC
  nulla utxos              List UTXOs
  nulla history            Transaction history
  nulla node               ElectrumX server status
  nulla fee                Current fee estimate
  nulla accounts           List all derived addresses

Options:
  --testnet     Use testnet (default: mainnet)
  --keystore PATH
"""

import sys
import os
import json
import getpass
import argparse
import time
from pathlib import Path
from typing import Optional

from nulla_core import (
    NullaWallet, NullaError, KeystoreError, WalletError,
    validate_address, format_btc
)
from nulla_electrum import ElectrumClient, ElectrumError
from nulla_tx import build_send_tx, UTXO, DUST_LIMIT_P2WPKH

DEFAULT_KEYSTORE = Path.home() / ".nulla" / "wallet.nulla"

_NO_COLOR = not sys.stdout.isatty() or os.environ.get("NO_COLOR")
def _c(code): return "" if _NO_COLOR else code

R  = _c("\033[0m");  B  = _c("\033[1m");   DIM = _c("\033[2m")
GR = _c("\033[92m"); YL = _c("\033[93m");  CY  = _c("\033[96m")
RD = _c("\033[91m"); OR = _c("\033[33m")

BANNER = f"""{OR}
  ╔╗╔╦ ╦╦  ╦  ╔═╗
  ║║║║ ║║  ║  ╠═╣
  ╝╚╝╚═╝╩═╝╩═╝╩ ╩  {DIM}Bitcoin Light Wallet v1.0.0{R}
"""

def die(msg):  print(f"{RD}✗ {msg}{R}", file=sys.stderr); sys.exit(1)
def ok(msg):   print(f"{GR}✓{R} {msg}")
def info(msg): print(f"{CY}→{R} {msg}")
def warn(msg): print(f"{YL}⚠{R} {msg}")
def hr(w=54):  print(f"{DIM}{'─'*w}{R}")

def prompt_pw(confirm=False, label="Password") -> str:
    pw = getpass.getpass(f"  {label}: ")
    if not pw: die("Password cannot be empty")
    if confirm:
        pw2 = getpass.getpass("  Confirm: ")
        if pw != pw2: die("Passwords do not match")
    return pw

def load_wallet(path: Path, pw=None) -> NullaWallet:
    if not path.exists(): die(f"No keystore at {path}\n  Run: nulla create")
    if pw is None: pw = prompt_pw()
    try:    return NullaWallet.load(str(path), pw)
    except KeystoreError as e: die(str(e))

def get_electrum(args) -> ElectrumClient:
    network = "testnet" if args.testnet else "mainnet"
    return ElectrumClient(network=network)

def trunc(s, l=12, r=8):
    return f"{s[:l]}…{s[-r:]}" if len(s) > l+r+3 else s

def utxos_for_wallet(wallet: NullaWallet, el: ElectrumClient) -> list:
    result = []
    for addr in wallet.all_addresses():
        try:
            for u in el.get_utxos(addr.electrum_scripthash):
                result.append(UTXO(u["tx_hash"], u["tx_pos"], u["value"], addr, u.get("height",0)))
        except ElectrumError: pass
    return result

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_create(args):
    path = Path(args.keystore)
    if path.exists():
        ans = input(f"{YL}  ⚠ Overwrite existing keystore? [yes/no]: {R}")
        if ans.strip().lower() != "yes": return info("Aborted")
    path.parent.mkdir(parents=True, exist_ok=True)
    pw = prompt_pw(confirm=True)
    network = "testnet" if args.testnet else "mainnet"
    info("Generating wallet...")
    wallet = NullaWallet.generate(pw, network=network)
    wallet.save(str(path), pw)
    words = (wallet.mnemonic or "").split()
    print()
    hr(58); print(f"  {B}NEW BITCOIN WALLET{R}"); hr(58)
    print(f"\n  {CY}Primary address (SegWit):{R}")
    print(f"  {wallet.address}")
    print(f"\n  {B}{YL}RECOVERY PHRASE — WRITE DOWN & STORE OFFLINE:{R}\n")
    for row in range(0, len(words), 6):
        chunk = words[row:row+6]
        cols = "  ".join(f"{i+row+1:2}. {w:<12}" for i,w in enumerate(chunk))
        print(f"  {B}{cols}{R}")
    print(f"\n  {RD}Never share this phrase. No recovery without it.{R}")
    print(f"\n  Keystore: {path}\n  Network:  {network}")
    hr(58); print()

def cmd_import(args):
    path = Path(args.keystore)
    path.parent.mkdir(parents=True, exist_ok=True)
    mnemonic = " ".join(args.words) if args.words else input("  Mnemonic: ").strip()
    if not mnemonic: die("Mnemonic required")
    pw = prompt_pw(confirm=True)
    network = "testnet" if args.testnet else "mainnet"
    try:
        wallet = NullaWallet.from_mnemonic(mnemonic, pw, network=network)
        wallet.save(str(path), pw)
        ok(f"Wallet restored → {wallet.address}")
    except WalletError as e: die(str(e))

def cmd_balance(args):
    wallet = load_wallet(Path(args.keystore))
    el = get_electrum(args)
    info("Connecting to ElectrumX...")
    try:
        el.connect()
        confirmed = unconfirmed = 0
        for addr in wallet.all_addresses():
            b = el.get_balance(addr.electrum_scripthash)
            confirmed   += b["confirmed"]
            unconfirmed += b["unconfirmed"]
        print(); hr(50)
        print(f"  {B}BALANCE  [{wallet.network.upper()}]{R}")
        hr(50)
        print(f"  Address:     {DIM}{trunc(wallet.address)}{R}")
        print(f"  {B}{GR}{format_btc(confirmed + unconfirmed)}{R}")
        if unconfirmed:
            print(f"  Unconfirmed: {format_btc(unconfirmed)} (pending)")
        hr(50); print()
    except ElectrumError as e: die(str(e))

def cmd_send(args):
    wallet  = load_wallet(Path(args.keystore))
    to      = args.to.strip()
    amount_btc = float(args.amount)
    fee_rate   = int(args.fee_rate)
    amount_sats= int(amount_btc * 1e8)

    if not validate_address(to, wallet.network):
        die(f"Invalid Bitcoin address: {to}")
    if amount_sats <= 0:
        die("Amount must be positive")

    el = get_electrum(args)
    info("Fetching UTXOs...")
    try:
        el.connect()
        utxos       = utxos_for_wallet(wallet, el)
        total_sats  = sum(u.value for u in utxos)
        change_addr = wallet.change_address("p2wpkh")

        if not utxos: die("No spendable UTXOs")
        if total_sats < amount_sats: die(f"Insufficient balance: {format_btc(total_sats)}")

        from nulla_tx import select_utxos
        selected, fee = select_utxos(utxos, amount_sats, fee_rate)
        change = sum(u.value for u in selected) - amount_sats - fee

        print(); hr(54); print(f"  {B}{YL}CONFIRM TRANSACTION{R}"); hr(54)
        print(f"  To:       {to}")
        print(f"  Amount:   {B}{format_btc(amount_sats)}{R}")
        print(f"  Fee:      {format_btc(fee)}  ({fee_rate} sat/vB)")
        print(f"  Total:    {B}{format_btc(amount_sats + fee)}{R}")
        if change > DUST_LIMIT_P2WPKH:
            print(f"  Change:   {format_btc(change)}")
        print(f"  Inputs:   {len(selected)} UTXO(s)")
        hr(54)
        ans = input("  Type YES to broadcast: ").strip()
        if ans != "YES": return info("Cancelled")

        raw_hex, fee_sats, change_sats = build_send_tx(
            utxos, to, amount_sats, change_addr, fee_rate
        )
        info("Broadcasting...")
        txid = el.broadcast(raw_hex)
        ok(f"Sent!\n  TXID: {txid}")
        print(f"  View: https://mempool.space/tx/{txid}")
    except Exception as e: die(str(e))

def cmd_receive(args):
    wallet = load_wallet(Path(args.keystore))
    print(); hr(72); print(f"  {B}RECEIVE BITCOIN{R}"); hr(72)
    print(f"  Native SegWit (bc1…):")
    print(f"  {CY}{wallet.address}{R}")
    legacy = wallet.default_address("p2pkh").address
    print(f"\n  Legacy (1…) — for older wallets:")
    print(f"  {DIM}{legacy}{R}")
    hr(72); print()

def cmd_utxos(args):
    wallet = load_wallet(Path(args.keystore))
    el = get_electrum(args)
    info("Fetching UTXOs...")
    try:
        el.connect()
        utxos = utxos_for_wallet(wallet, el)
        if not utxos: return info("No UTXOs found")
        total = sum(u.value for u in utxos)
        print(); hr(72)
        print(f"  {B}UTXOs  ({len(utxos)} total — {format_btc(total)}){R}")
        hr(72)
        print(f"  {'TXID':14} {'VOUT':5} {'VALUE':18} {'TYPE':8} STATUS")
        hr(72)
        for u in sorted(utxos, key=lambda x: -x.value):
            status = f"block {u.height}" if u.height > 0 else f"{YL}unconfirmed{R}"
            print(f"  {u.txid[:12]}… {u.vout:<5} {format_btc(u.value):18} {u.address.addr_type:8} {status}")
        hr(72)
        print(f"  {B}Total: {format_btc(total)}{R}")
        print()
    except ElectrumError as e: die(str(e))

def cmd_history(args):
    wallet = load_wallet(Path(args.keystore))
    el = get_electrum(args)
    info("Fetching history...")
    try:
        el.connect()
        scripthashes = [a.electrum_scripthash for a in wallet.all_addresses()]
        history = el.get_history_multi(scripthashes)[:args.limit]
        if not history: return info("No transactions found")
        print(); hr(72); print(f"  {B}HISTORY{R}"); hr(72)
        for tx in history:
            h    = tx["height"]
            conf = f"block {h}" if h > 0 else f"{YL}unconfirmed{R}"
            print(f"  {tx['tx_hash'][:20]}…  {DIM}{conf}{R}")
            print(f"    mempool.space/tx/{tx['tx_hash']}")
        hr(72); print()
    except ElectrumError as e: die(str(e))

def cmd_node(args):
    el = get_electrum(args)
    info("Testing ElectrumX connection...")
    result = el.test_connection()
    print(); hr(50); print(f"  {B}NODE STATUS{R}"); hr(50)
    if not result["connected"]:
        print(f"  {RD}✗ {result.get('error','Failed')}{R}")
    else:
        print(f"  {GR}✓ Connected{R}")
        print(f"  Server:   {result['server']}:{result['port']}")
        print(f"  Protocol: {result['protocol']}")
        print(f"  Height:   {result['height']:,}")
        print(f"  Latency:  {result['latency_ms']} ms")
    hr(50); print()

def cmd_fee(args):
    el = get_electrum(args)
    try:
        el.connect()
        print(); hr(46); print(f"  {B}FEE ESTIMATES{R}"); hr(46)
        for blocks, label in [(1,"~10 min"), (3,"~30 min"), (6,"~1 hour")]:
            rate = el.estimate_fee(blocks)
            print(f"  {blocks} block(s) [{label}]:  {B}{rate} sat/vbyte{R}")
        hr(46); print()
    except ElectrumError as e: die(str(e))

def cmd_accounts(args):
    wallet = load_wallet(Path(args.keystore))
    print(); hr(76); print(f"  {B}ADDRESSES{R}"); hr(76)
    for group in wallet.all_accounts_summary():
        t = group["type"]
        label = "Native SegWit (BIP84)" if t=="p2wpkh" else "Legacy (BIP44)"
        print(f"\n  {CY}{label}{R}")
        for a in group["addresses"][:5]:
            marker = f"{GR}●{R}" if a["path"].endswith("/0/0") else f"{DIM}○{R}"
            print(f"  {marker} {a['address']}  {DIM}{a['path']}{R}")
    hr(76); print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(BANNER)
    p = argparse.ArgumentParser(prog="nulla", description="Nulla Bitcoin Wallet")
    p.add_argument("--keystore", default=str(DEFAULT_KEYSTORE))
    p.add_argument("--testnet",  action="store_true")

    sub = p.add_subparsers(dest="cmd", metavar="command")

    sub.add_parser("create",   help="Create new wallet")
    pi = sub.add_parser("import",  help="Import from mnemonic")
    pi.add_argument("words", nargs="*")
    sub.add_parser("balance",  help="Show balance")
    sub.add_parser("receive",  help="Show receive address")
    sub.add_parser("utxos",    help="List UTXOs")
    sub.add_parser("node",     help="ElectrumX status")
    sub.add_parser("fee",      help="Fee estimates")
    sub.add_parser("accounts", help="All derived addresses")

    ps = sub.add_parser("send", help="Send BTC")
    ps.add_argument("to")
    ps.add_argument("amount", help="Amount in BTC")
    ps.add_argument("--fee-rate", default="5", help="sat/vbyte [5]")

    ph = sub.add_parser("history", help="Transaction history")
    ph.add_argument("--limit", type=int, default=20)

    args = p.parse_args()
    if not args.cmd:
        p.print_help(); return

    handlers = {
        "create": cmd_create, "import": cmd_import,
        "balance": cmd_balance, "send": cmd_send,
        "receive": cmd_receive, "utxos": cmd_utxos,
        "history": cmd_history, "node": cmd_node,
        "fee": cmd_fee, "accounts": cmd_accounts,
    }

    try:
        handlers[args.cmd](args)
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrupted{R}")
    except NullaError as e:
        die(str(e))

if __name__ == "__main__":
    main()
