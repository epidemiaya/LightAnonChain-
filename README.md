# ⛓️ LAC — LightAnonChain

**Privacy-first blockchain that physically deletes data.**

> *"Privacy that expires"* — the only blockchain where your data doesn't exist forever.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Beta Testnet](https://img.shields.io/badge/Status-Beta%20Testnet-orange.svg)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![Live Demo](https://img.shields.io/badge/Live%20Demo-lac--beta.uk-emerald.svg)](https://lac-beta.uk)

---

## 🚀 Live Beta

**Try it now:** [https://lac-beta.uk](https://lac-beta.uk)

No installation. Works in browser. Add to Home Screen on iOS/Android for app-like experience.

---

## What is LAC?

LAC is a lightweight privacy blockchain with a unique feature: **Zero-History** — it physically deletes blockchain data after cryptographic verification. Unlike Monero or Zcash where encrypted data stays forever, LAC erases it completely.

LAC combines **anonymous transactions** (ring signatures, stealth addresses) with **encrypted messaging** — like having Monero + Signal in one protocol, but with data that cleans itself.

## Why LAC?

| Feature | Monero | Zcash | Secret Network | Session | **LAC** |
|---------|--------|-------|----------------|---------|---------|
| Ring Signatures | ✅ | ❌ | ❌ | ❌ | ✅ |
| Physical data deletion | ❌ | ❌ | ❌ | ❌ | ✅ |
| Built-in encrypted chat | ❌ | ❌ | ❌ | ✅ | ✅ |
| Burn after read messages | ❌ | ❌ | ❌ | ❌ | ✅ |
| Dead Man's Switch | ❌ | ❌ | ❌ | ❌ | ✅ |
| Mobile-first design | ❌ | ❌ | ❌ | ✅ | ✅ |
| Anonymous DeFi (STASH) | ❌ | Partial | ✅ | ❌ | ✅ |
| Post-quantum encryption | ❌ | ❌ | ❌ | ❌ | ✅ (Kyber-768) |
| Bitcoin SPV wallet | ❌ | ❌ | ❌ | ❌ | ✅ |
| BTC ↔ LAC Atomic Swaps | ❌ | ❌ | ❌ | ❌ | 🔜 |

**No other blockchain deletes your data.** Monero hides it. Zcash encrypts it. LAC destroys it.

## Core Features

### 🔒 Zero-History Architecture
Three-tier data lifecycle with physical deletion:
- **L3 (Full Data)** — complete blocks, 30 days retention
- **L2 (Hashes Only)** — cryptographic proofs, 90 days
- **L1 (Commitments)** — Merkle root commitments, forever

After L2→L1 transition, the original data is **physically deleted from disk**. Not encrypted, not hidden — gone.

### 👻 VEIL Transfers
Anonymous transactions using ring signatures + stealth addresses (one-time addresses). Sender, receiver, and amount — all hidden. Post-quantum secure with Kyber-768 encapsulation.

### 🎒 STASH Pool
Anonymous asset storage. Deposit LAC → receive secret key → withdraw from any address. Zero on-chain link between deposit and withdrawal. Fixed denominations (100/1K/10K/100K LAC) for unlinkability.

### 💬 Encrypted Messaging
Two layers of private communication:
- **Regular messages** — persistent, E2E encrypted (Ed25519 + X25519 + XSalsa20-Poly1305)
- **Ephemeral L2 messages** — self-destruct after 5 minutes, hash recorded then deleted
- **🔥 Burn after read** — destroyed the moment recipient opens them
- **Group chats** — public, private, L1 blockchain, L2 ephemeral types
- **Voice messages & images** — media with automatic L2 cleanup

### 💀 Dead Man's Switch
If you don't log in for X days, automatic actions trigger:
- Transfer all funds to an heir
- Send pre-written messages
- Burn STASH keys
- Wipe wallet completely

All actions recorded on-chain anonymously. No other blockchain has this.

### ⛏️ PoET Consensus
Proof of Elapsed Time — fair mining without GPU advantage. 19 winners per block, rewards distributed proportionally. CPU-friendly, energy-efficient.


### ₿ Bitcoin SPV Wallet (built-in)
Non-custodial Bitcoin wallet built directly into the LAC mobile app — no separate app needed.

- **Keys derived locally** from your LAC seed via `SHA256(SHA256("LAC-BTC-WALLET-v1:" + seed))` — never transmitted anywhere
- **P2WPKH** native segwit addresses (`bc1q...`), BIP143 signing
- Send, receive, UTXO management, fee estimation (slow / mid / fast)
- Blockchain data via Blockstream Esplora public API — only your address is visible, not your key
- Transaction signing fully in-browser using `@noble/secp256k1`
- **One seed phrase covers both wallets** — back up once, recover everything

### ⚡ BTC ↔ LAC Atomic Swaps *(coming soon)*
Trustless cross-chain exchange using Hash Time-Lock Contracts (HTLC). No exchange, no KYC, no custodian.

```
1. Alice generates secret S, locks BTC on Bitcoin with hash(S) + timelock
2. Bob sees hash(S), locks LAC on LAC chain with same hash + timelock
3. Alice reveals S → claims LAC
4. Bob sees S on-chain → claims BTC
5. If either party disappears → both get refunds after timelock
```

LAC Time-Lock transactions are already live on-chain — atomic swaps add the P2P coordination layer.

### ⏰ Time-Lock Transactions
Schedule future payments. "Send 1000 LAC to @alice in 360 blocks (~1 hour)." Funds locked until target block.

## Architecture

```
┌─────────────────────────────────────────┐
│           LAC Mobile App (PWA)          │
│    React + Tailwind · Telegram-like UI  │
│    PWA · Service Worker · Offline cache │
├─────────────────────────────────────────┤
│             LAC Node (Python)           │
│  gevent WSGIServer · 1000+ concurrent   │
│  PoET Mining · Ring Sigs · E2E Crypto   │
├──────────┬──────────┬───────────────────┤
│  L3 Full │ L2 Hash  │  L1 Commitment    │
│  30 days │ 90 days  │  Forever          │
│ (delete) │ (delete) │  (Merkle root)    │
└──────────┴──────────┴───────────────────┘
```

## Quick Start

### Requirements
- Python 3.10+
- Node.js 18+ (for mobile app)

### Run the node

```bash
cd lac-node
pip install flask cryptography gevent
python lac_node.py
# Node starts on http://localhost:38400
```

### Run the mobile app

```bash
cd lac-mobile
npm install
npm run dev
# App starts on http://localhost:5173
```

### View the explorer

Open `explorer/explorer.html` in a browser (connects to local node automatically).

## Project Structure

```
LightAnonChain/
├── lac-node/
│   ├── lac_node.py          # Main node (6500+ lines)
│   ├── lac_timelock.py      # Time-lock transaction module
│   ├── lac_zero_history.py  # Zero-History deletion engine
│   └── requirements.txt
├── lac-mobile/
│   ├── src/App.jsx          # Full mobile app (3500+ lines)
│   ├── vite.config.js       # PWA + code splitting config
│   ├── package.json
│   └── ...
├── explorer/
│   └── explorer.html        # Block explorer (standalone)
├── docs/
│   ├── LAC_PROJECT_OVERVIEW.md
│   ├── LAC_COMPARISON.md
│   ├── LAC_FAQ.md
│   └── ZERO_HISTORY_INTEGRATION.md
├── README.md
└── LICENSE
```

## Tokenomics

| Parameter | Value |
|-----------|-------|
| Max Supply | ~1840M LAC (100-year emission) |
| Block Time | ~10 seconds |
| Initial Reward | 190 LAC/block |
| Halving | Gradual reduction over 100 years |
| Transaction Fee | 0.1 LAC (transfers), 1.0 LAC (messages) |
| Username Cost | 50 LAC |
| Level Upgrade | 100-50,000 LAC (burn) |

## Roadmap

- [x] Core blockchain with PoET consensus
- [x] Ring signatures + stealth addresses
- [x] Zero-History three-tier deletion
- [x] VEIL anonymous transfers
- [x] STASH anonymous pool
- [x] Encrypted messaging (regular + ephemeral + burn)
- [x] Dead Man's Switch
- [x] Time-Lock transactions
- [x] Mobile web app (Telegram-like UI)
- [x] Block explorer
- [x] PWA — Add to Home Screen (iOS & Android)
- [x] Public beta testnet → [lac-beta.uk](https://lac-beta.uk)
- [x] Let's Encrypt SSL
- [x] gevent async server (1000+ concurrent users)
- [x] Voice messages & image sharing
- [x] Group chats (public / private / L1 / L2 ephemeral)
- [x] E2E encryption (Ed25519 + X25519 + XSalsa20-Poly1305)
- [x] Read receipts + unread indicators
- [x] WebSocket real-time messaging
- [x] Bitcoin SPV wallet (non-custodial, local keys, Esplora API)
- [x] Level 7 ⚡ GOD — top-tier validator status
- [ ] BTC ↔ LAC Atomic Swaps (HTLC, trustless, P2P)
- [ ] Multi-node peer discovery & sync
- [ ] Mobile app (App Store / Google Play)
- [ ] Username marketplace (on-chain)
- [ ] Security audit
- [ ] Mainnet launch Q2 2025

## Use Cases

**Journalists & Activists** — send documents that self-destruct. Dead Man's Switch releases information if you go silent.

**Crypto Privacy** — VEIL transfers with ring signatures. STASH pool breaks any on-chain link. Zero-History means evidence doesn't exist after 90 days. Bitcoin wallet shares one seed with LAC — one backup covers everything.

**Inheritance** — Dead Man's Switch transfers funds to heirs without lawyers, notaries, or trusted third parties.

**Private Communication** — end-to-end encrypted messages with burn-after-read. Not stored on servers, not stored on blockchain.

**Cross-chain** — Atomic swaps let you exchange BTC ↔ LAC directly, peer-to-peer, with no exchange, no KYC, no custodian.

## Contributing

LAC is in active development. Contributions welcome:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

## Security

This is testnet software. **Do not use for real funds.** The protocol has not been formally audited. The Bitcoin wallet derives private keys locally and never transmits them. Blockchain data is fetched from Blockstream Esplora over HTTPS. Your LAC seed phrase controls both your LAC and Bitcoin wallets — keep it safe.

If you discover a vulnerability, please open an issue or contact us directly.

## License

MIT License. See [LICENSE](LICENSE) for details.

---

**Built in Ukraine 🇺🇦**
