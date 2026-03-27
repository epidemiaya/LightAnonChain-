# Nulla — Bitcoin Light Wallet

A minimalist Bitcoin light client built in the spirit of Electrum.
No full node required. Connects directly to the Bitcoin network via ElectrumX servers.

Standalone app — future integration with [LightAnonChain (LAC)](https://lac-beta.uk) for BTC↔LAC atomic swaps.

## Features

- **BIP39** — 24-word mnemonic (256-bit entropy)
- **BIP84** — Native SegWit addresses (`bc1q…`)
- **BIP44** — Legacy addresses (`1…`)
- **ElectrumX** — connects to Bitcoin network without running a full node
- **UTXO management** — coin selection, fee estimation, change addresses
- **BIP143** — correct sighash for SegWit transactions
- **Encrypted keystore** — AES-256-GCM + PBKDF2 × 600k iterations + HMAC-SHA256
- **CLI + Web UI** — both interfaces included
- **Testnet support** — `--testnet` flag

## Architecture

```
nulla_core.py       BIP39/32/44/84 HD wallet, bech32, keystore
nulla_electrum.py   ElectrumX protocol client (SSL/TCP, JSON-RPC)
nulla_tx.py         Bitcoin transaction builder (P2WPKH + P2PKH, BIP143)
nulla_cli.py        Command-line interface
nulla_server.py     Flask JSON API + React SPA
ui/                 React frontend (dark theme, Bitcoin orange)
```

## Quick Start

```bash
git clone https://github.com/epidemiaya/nulla
cd nulla

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# Build UI
cd ui
npm install
npm run build
cd ..

# Start (opens browser automatically)
python nulla_server.py
```

Open: **http://localhost:7421**

---

## CLI Usage

```bash
python nulla_cli.py create              # Create new wallet
python nulla_cli.py import word1 ...    # Restore from mnemonic
python nulla_cli.py balance             # Show balance
python nulla_cli.py receive             # Show receive address
python nulla_cli.py send bc1q... 0.001  # Send BTC
python nulla_cli.py utxos               # List UTXOs
python nulla_cli.py history             # Transaction history
python nulla_cli.py fee                 # Current fee estimates
python nulla_cli.py node                # ElectrumX server status
python nulla_cli.py accounts            # All derived addresses

# Testnet
python nulla_cli.py --testnet balance
python nulla_server.py --testnet
```

---

## ElectrumX Servers (Mainnet)

Nulla automatically selects the fastest available server:

- `electrum.blockstream.info:700`
- `electrum.bitaroo.net:50002`
- `fortress.qtornado.com:443`
- `electrum.jochen-hoenicke.de:50006`
- `bitcoin.aranguren.org:50002`

---

## Security

| Component | Detail |
|-----------|--------|
| secp256k1 | `coincurve` bindings (same library as Bitcoin Core) |
| Signing | Deterministic ECDSA (RFC6979), low-S enforced (BIP62) |
| Keystore | AES-256-GCM, PBKDF2-SHA256 × 600,000 iterations |
| MAC | HMAC-SHA256 verified before decryption (constant-time) |
| Server | Binds to `127.0.0.1` only — never exposed to network |
| Memory | `wallet.lock()` wipes key material from RAM |

---

## Roadmap

- [x] BIP39 / BIP84 / BIP44 HD wallet
- [x] ElectrumX protocol client
- [x] P2WPKH transaction building & signing
- [x] CLI + Web UI
- [ ] P2SH-SegWit (BIP49) support
- [ ] Hardware wallet (Trezor / Ledger)
- [ ] BTC↔LAC atomic swap module

---

## License

MIT — part of the [LightAnonChain](https://lac-beta.uk) ecosystem.
