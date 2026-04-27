# ⛓️ LAC — LightAnonChain
**Privacy-first blockchain that physically deletes your data.**

> *"Privacy that expires"* — the only blockchain where data doesn't exist forever.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Beta Testnet](https://img.shields.io/badge/Status-Beta%20Testnet-orange.svg)]()
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![Live Testnet](https://img.shields.io/badge/Live%20Testnet-lac--beta.uk-brightgreen.svg)](https://lac-beta.uk)
[![Blocks](https://img.shields.io/badge/Blocks-400%2C000%2B-blue.svg)]()
[![Built in Ukraine](https://img.shields.io/badge/Built%20in-Ukraine%20🇺🇦-yellow.svg)]()

---

## 🚀 Live Beta Testnet

**Try it now:** [https://lac-beta.uk](https://lac-beta.uk)

<img width="1280" height="503" alt="photo_2026-04-27_21-48-19" src="https://github.com/user-attachments/assets/eea2c008-9508-4351-9546-1767c3083caa" />

No installation. Works in any browser on any device.

400,000+ blocks mined. Real users. Real data deletion.

---

## What is LAC?

LAC is a **Privacy Communication Platform** built on its own blockchain. Not just a coin — a full ecosystem for private communication with a unique **Zero-History architecture**: data is physically deleted after 30/90 days, not just encrypted forever like Monero or Zcash.

Think **Monero + Signal + Dead Man's Switch + RPG** — in one protocol, running on your phone.

---

## Why LAC is different

| Feature | Monero | Zcash | Signal | Session | **LAC** |
|---------|--------|-------|--------|---------|---------|
| Physical data deletion | ❌ | ❌ | ❌ | ❌ | ✅ |
| Ring Signatures | ✅ | ❌ | ❌ | ❌ | ✅ |
| Built-in encrypted chat | ❌ | ❌ | ✅ | ✅ | ✅ |
| Burn after read | ❌ | ❌ | ❌ | ❌ | ✅ |
| Dead Man's Switch | ❌ | ❌ | ❌ | ❌ | ✅ |
| Soul-bound NFT companions | ❌ | ❌ | ❌ | ❌ | ✅ |
| Offline mesh networking | ❌ | ❌ | ❌ | ❌ | ✅ |
| Built-in Bitcoin wallet | ❌ | ❌ | ❌ | ❌ | ✅ |
| Post-quantum encryption | ❌ | ❌ | ❌ | ❌ | ✅ Kyber-768 |
| Mobile-first PWA | ❌ | ❌ | ✅ | ✅ | ✅ |
| Geographic secret recovery | ❌ | ❌ | ❌ | ❌ | ✅ |

**No other blockchain deletes your data. Monero hides it. Zcash encrypts it. LAC destroys it.**

---

## Core Features

### 🕳️ Zero-History Architecture
Three-tier data lifecycle with physical deletion:

```
L3 Full Data  → 30 days  → physically deleted from disk
L2 Hashes     → 90 days  → cryptographic proofs only
L1 Commitment → forever  → Merkle root, verified by validators
```

After deletion, the original data is **gone**. Not encrypted. Not hidden. Erased.

### 👻 VEIL Transfers
Anonymous transactions using ring signatures + stealth addresses. Sender, receiver, and amount — all hidden. Post-quantum secure with Kyber-768 key encapsulation.

### 🎒 STASH Pool
Anonymous asset storage with fixed denominations (100 / 1K / 10K / 100K LAC). Deposit → receive secret key → withdraw from any address. Zero on-chain link between deposit and withdrawal.

### 💬 Encrypted Messaging
- **Regular messages** — E2E encrypted (Ed25519 + X25519 + XSalsa20-Poly1305), persistent
- **Ephemeral L2 messages** — auto-delete after 5 minutes, hash recorded then destroyed
- **🔥 Burn after read** — destroyed the instant recipient opens them
- **Channels & Groups** — public, private, secret. L1 on-chain or L2 ephemeral
- **Voice messages & images** — with automatic L2 cleanup

### ⚡ Wraith System — Soul-bound NFT Companions
Every wallet can mint a **Wraith** — a unique soul-bound token permanently linked to your address and recorded on-chain. Not transferable. Not tradeable. Yours forever until released.

> ⚠️ **Status:** Core mechanics live in testnet. Full RPG progression, marketplace and Echo evolution are in active development.

```
WRAITH-A1314660A342
Void Moth #5701 · Rare
━━━━━━━━━━━━━━━━━━━━
👁  Head   [Void Lens L3     ]  ●●●○○
❤️  Core   [Iron Heart L5    ]  ●●●●●
⚡  Arms   [Speed Claw L2    ]  ●●○○○
🦿  Legs   [empty            ]
🛡  Armor  [Ghost Aura L1    ]  ●○○○○
━━━━━━━━━━━━━━━━━━━━
+8% block chance  -20% fees  +15% shards
✦ iron_will  ✦ echo_memory
```

**5 equipment slots** (Head / Core / Arms / Legs / Armor), each takes items crafted from **Shards**. Items upgrade to Level 5 with +25% bonus per level. Rare **Mutations** drop randomly on upgrades.

Wraith bonuses are **real and applied on-chain**: block chance in mining, fee discounts on transfers, shard drops from mining and group posts.

5 Wraith types with different strengths: `Wolf` (miner), `Raven` (scout), `Cat` (trader), `Fox` (chaos), `Moth` (elite/rare).

### 🌐 LAC Mesh — Offline Networking
**[lac-mesh](https://github.com/epidemiaya/lac-mesh)** module enables peer-to-peer communication without internet using **WiFi Direct** (Android). Nodes form a mesh network and relay messages between each other.

- No internet required — communicates over local WiFi P2P
- TCP transport on port 47731
- Ed25519 encryption compatible with the main LAC protocol
- Store-and-forward routing with TTL and flood algorithm
- Native Android plugin via Capacitor

This is the foundation for LAC's **DePIN layer** — physical infrastructure operated by real devices.

### 🐍 Nagini Protocol
**[nagini-protocol](https://github.com/epidemiaya/nagini-protocol)** — geographic secret distribution:
- Split your seed into N shards (Shamir Secret Sharing)
- Each shard encrypted with the GPS coordinates of a physical location
- Recover only by visiting K locations in the real world
- **Dead Man's Switch** + **Duress PIN** built in
- Mobile PWA with GPS capture

### 💀 Dead Man's Switch
If you don't check in for N days, automatic on-chain actions trigger:
- Transfer all funds to designated address
- Send pre-written messages
- Burn STASH keys
- Wipe wallet completely

Everything recorded anonymously on L1. No other blockchain has this.

### ₿ Bitcoin SPV Wallet (built-in)
Non-custodial Bitcoin wallet derived from your LAC seed. One seed → two wallets.

- Keys derived locally via `SHA256(SHA256("LAC-BTC-WALLET-v1:" + seed))` — never transmitted
- Native SegWit `bc1q...` addresses (BIP84), full BIP143 signing
- UTXO management, fee estimation (slow / mid / fast)
- Blockchain data via Blockstream Esplora — only address visible, not key
- One backup covers both LAC and BTC

### ⛏️ PoET Mining
Proof of Elapsed Time — fair mining without GPU arms race. 19 winners per block. CPU-friendly, energy-efficient. Level system (L0–L7 ⚡ GOD) multiplies rewards and mining chances.

Level 7 GOD requires 2,000,000 LAC burned — gives 2x mining chance and 2x validator rewards.

### 🔐 Zero-History Validators
L5/L6 wallets become validators that sign commitments before data is deleted. Slashing for bad behavior. Validator rewards per commitment signature.

### 🎯 Anonymous Referral Quests
Phase 1 referral system with on-chain quest milestones. All referrals are anonymous — cryptographic proofs only, no real addresses exposed. Quest rewards up to 500,000 LAC for top referrers.

---

## DePIN Vision

LAC is evolving into a **DePIN (Decentralized Physical Infrastructure Network)** for private communications.

**Current:** Software nodes running on VPS/cloud servers.

**Roadmap:**
- **LAC Mesh nodes** — dedicated hardware devices (Raspberry Pi-class) running lac-node + WiFi Direct mesh, creating offline-capable privacy networks in cities
- **Privacy hotspots** — physical devices that relay anonymous messages and earn LAC
- **Smart sensors** — IoT devices that report location/environmental data privately via LAC
- **Edge compute nodes** — small hardware validators that earn rewards for commitment signatures

Node operators earn LAC through mining rewards and validator fees. The more physical nodes — the more resilient and censorship-resistant the network.

**Node Sale** is planned for Q2–Q3 2026 — node licenses granting mining boosts and validator priority.

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│              LAC Mobile App (PWA)                  │
│     React + Tailwind · Mobile-first · Any browser   │
├────────────────────────────────────────────────────┤
│                 LAC Node (Python)                  │
│   gevent WSGI · WebSocket · PoET · Ring Sigs       │
├────────────┬─────────────┬──────────────────────── ┤
│  L3 Full   │  L2 Hashes  │   L1 Commitments        │
│  30 days   │   90 days   │   Forever (Merkle)      │
│  (deleted) │  (deleted)  │   (validator-signed)    │
├────────────┴─────────────┴─────────────────────────┤
│              LAC Mesh (WiFi Direct)                │
│    P2P offline · Ed25519 · Store-and-forward       │
└────────────────────────────────────────────────────┘
```

---

## Quick Start

### Requirements
- Python 3.10+
- Node.js 18+

### Run the node
```bash
git clone https://github.com/epidemiaya/LightAnonChain-
cd LightAnonChain-/lac-node
pip install flask cryptography gevent
python lac_node.py
# Node on http://localhost:38400
```

### Run the mobile app
```bash
cd ../lac-mobile
npm install
npm run dev
# App on http://localhost:5173
```

---

## Project Structure

```
LightAnonChain/
├── lac-node/
│   ├── lac_node.py           # Main node (8000+ lines)
│   ├── lac_zero_history.py   # Zero-History deletion engine
│   ├── lac_crypto.py         # Ed25519, X25519, Kyber-768
│   └── requirements.txt
├── lac-mobile/
│   ├── src/App.jsx           # Full mobile app (6000+ lines)
│   └── vite.config.js
└── README.md
```

**Related repos:**
- [epidemiaya/lac-mesh](https://github.com/epidemiaya/lac-mesh) — WiFi Direct offline mesh module
- [epidemiaya/nagini-protocol](https://github.com/epidemiaya/nagini-protocol) — Geographic secret distribution

---

## Tokenomics

| Parameter | Value |
|-----------|-------|
| Max Supply | ~1.84B LAC (100-year emission) |
| Block Time | ~10 seconds |
| Initial Reward | 190 LAC/block |
| Transaction Fee | 0.1 LAC (transfers) · 1.0 LAC (messages) |
| Username | 50 LAC (burned) |
| Level Upgrade | 100 – 2,000,000 LAC (burned) |
| Wraith Mint | 500 LAC |
| Level 7 ⚡ GOD | 2x mining · 2x validator reward |

**Burn mechanics active in testnet:** every message, username, level upgrade, and Wraith action burns LAC. At scale, burn exceeds emission → deflationary.

---

## Roadmap

**Completed ✅**
- Core blockchain with PoET consensus
- Zero-History three-tier deletion (L3/L2/L1)
- Ring signatures + stealth addresses (VEIL)
- STASH anonymous pool
- Encrypted messaging (regular / ephemeral / burn-after-read)
- Channels & Groups (public / private / secret)
- Dead Man's Switch
- Time-Lock transactions
- Nagini Protocol (geographic secret recovery)
- LAC Mesh (WiFi Direct offline networking)
- Bitcoin SPV wallet (non-custodial, in-browser)
- Wraith soul-bound NFT system with RPG equipment
- Anonymous referral quest system
- Zero-History validators with slashing/rewards
- WebSocket real-time sync
- Mobile web app (iOS + Android, browser-based)
- Post-quantum encryption (Kyber-768)
- Public beta testnet (400,000+ blocks)

**In progress 🔨**
- Native iOS & Android apps (App Store / Google Play)
- Node Sale infrastructure (license system on-chain)

**Planned 📋**
- BTC ↔ LAC Atomic Swaps (HTLC, trustless)
- Mainnet launch
- Security audit
- LAC Mesh hardware nodes (DePIN)
- Username marketplace
- LAC ShadowMail (private email layer)
- Smart device integration (IoT / edge compute)

---

## Use Cases

**Journalists & Activists** — documents that self-destruct. Dead Man's Switch releases information if you go silent. Nagini Protocol hides your seed across physical locations.

**Crypto Privacy** — VEIL transfers break the on-chain trail. STASH pool breaks deposit/withdrawal links. Zero-History means forensic evidence doesn't exist after 90 days.

**Inheritance** — Dead Man's Switch transfers funds to heirs without lawyers, without trusted third parties, without anyone knowing the amount.

**Offline Communication** — LAC Mesh works without internet. WiFi Direct creates local encrypted networks between devices.

**Node Operators** — run a node, earn LAC from mining and validator rewards. Node Sale licenses boost your earning multiplier.

---

## Security

This is **testnet software**. Do not use for real funds. Not formally audited yet.

Bitcoin wallet keys are derived locally and never transmitted. Your LAC seed controls both wallets — store it safely.

Security audit planned before mainnet.

---

## Support the Project

**Bitcoin:** `bc1qwrgfqgj3mvzupgy0rj37ky5kjwslmq53a2h9qw`

Every contribution helps keep the testnet running.

---

## Contributing

1. Fork the repo
2. Create a feature branch
3. Commit and push
4. Open a Pull Request

---

**Built in Ukraine 🇺🇦 · Started November 2025 · [lac-beta.uk](https://lac-beta.uk) · [lac-chain.com](https://lac-chain.com)**
