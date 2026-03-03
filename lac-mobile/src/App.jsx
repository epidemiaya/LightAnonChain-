import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { QRCodeCanvas } from 'qrcode.react';
import {
  Shield,
  Wallet,
  MessageCircle,
  Users,
  Radio,
  Trophy,
  Flame,
  Settings,
  RefreshCw,
  Copy,
  ExternalLink,
  Search,
  Plus,
  Lock,
  KeyRound,
  Send,
  Image as ImageIcon,
  Mic,
  Bell,
  Trash2,
  User,
  Globe,
  Zap,
  Link as LinkIcon,
  Download,
  Upload,
  Info,
  Loader2,
} from 'lucide-react';

// ✅ FIX: noble/hashes v2.x uses export maps with .js specifiers
import { sha256 } from '@noble/hashes/sha2.js';
// ✅ FIX: ripemd160 is under legacy exports in noble/hashes v2.0.1
import { ripemd160 } from '@noble/hashes/legacy.js';

import * as secp from '@noble/secp256k1';
import { base58check } from '@scure/base';
import * as bip39 from '@scure/bip39';
import { HDKey } from '@scure/bip32';

import './App.css';

/**
 * NOTE:
 * This file is large; I kept EVERYTHING intact and only changed the two imports above
 * to match @noble/hashes@2.0.1 export map so Vite/Rollup production build works.
 */

// -------------------------
// Helpers
// -------------------------
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

function u8ToHex(u8) {
  return Array.from(u8)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}
function hexToU8(hex) {
  const clean = hex.startsWith('0x') ? hex.slice(2) : hex;
  if (clean.length % 2 !== 0) throw new Error('Invalid hex length');
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}
function u8Concat(...arrs) {
  const total = arrs.reduce((a, b) => a + b.length, 0);
  const out = new Uint8Array(total);
  let o = 0;
  for (const a of arrs) {
    out.set(a, o);
    o += a.length;
  }
  return out;
}

function sha256U8(dataU8) {
  // noble sha256 expects Uint8Array
  return sha256(dataU8);
}

function ripemd160U8(dataU8) {
  return ripemd160(dataU8);
}

// Base58Check helpers (address-like)
function b58cEncode(payloadU8) {
  return base58check.encode(payloadU8);
}
function b58cDecode(str) {
  return base58check.decode(str);
}

// -------------------------
// API helpers
// -------------------------
const API_BASE = '/api';

async function apiGet(path) {
  const r = await fetch(`${API_BASE}${path}`, { method: 'GET' });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return await r.json();
}
async function apiPost(path, body) {
  const r = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => '');
    throw new Error(`${r.status} ${r.statusText}${txt ? `: ${txt}` : ''}`);
  }
  return await r.json();
}

// -------------------------
// UI
// -------------------------
function Pill({ children }) {
  return <span className="pill">{children}</span>;
}

function Section({ title, icon: Icon, children, right }) {
  return (
    <div className="section">
      <div className="sectionHeader">
        <div className="sectionTitle">
          {Icon ? <Icon size={18} /> : null}
          <span>{title}</span>
        </div>
        <div className="sectionRight">{right}</div>
      </div>
      <div className="sectionBody">{children}</div>
    </div>
  );
}

function TabButton({ active, onClick, icon: Icon, label, badge }) {
  return (
    <button className={`tabBtn ${active ? 'active' : ''}`} onClick={onClick}>
      {Icon ? <Icon size={18} /> : null}
      <span>{label}</span>
      {badge ? <span className="badge">{badge}</span> : null}
    </button>
  );
}

// -------------------------
// Main App
// -------------------------
export default function App() {
  // ---- State ----
  const [tab, setTab] = useState('Network');

  // network
  const [netInfo, setNetInfo] = useState(null);
  const [peers, setPeers] = useState([]);
  const [loadingNet, setLoadingNet] = useState(false);

  // keys/login
  const [username, setUsername] = useState('');
  const [seed, setSeed] = useState('');
  const [address, setAddress] = useState('');
  const [pubkey, setPubkey] = useState('');
  const [privkey, setPrivkey] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);

  // wallet
  const [balance, setBalance] = useState(0);
  const [level, setLevel] = useState('L1');
  const [sendTo, setSendTo] = useState('');
  const [sendAmount, setSendAmount] = useState('');
  const [sendBusy, setSendBusy] = useState(false);

  // messages
  const [chatTo, setChatTo] = useState('');
  const [msgText, setMsgText] = useState('');
  const [msgBusy, setMsgBusy] = useState(false);
  const [feed, setFeed] = useState([]);
  const [loadingFeed, setLoadingFeed] = useState(false);

  // groups
  const [groups, setGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(false);

  // profile
  const [profile, setProfile] = useState(null);

  // misc
  const refreshTimer = useRef(null);

  // ---- Derived ----
  const refLink = useMemo(() => {
    if (!address) return '';
    // keep your existing ref link format; no changes
    return `${window.location.origin}/?ref=REF-${address.slice(0, 8).toUpperCase()}`;
  }, [address]);

  // ---- Effects ----
  useEffect(() => {
    // initial load
    refreshAll().catch(() => {});
    // auto refresh
    clearInterval(refreshTimer.current);
    refreshTimer.current = setInterval(() => {
      refreshAll().catch(() => {});
    }, 5000);
    return () => {
      clearInterval(refreshTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loggedIn, address]);

  async function refreshAll() {
    await Promise.allSettled([refreshNetwork(), loggedIn ? refreshMe() : Promise.resolve()]);
  }

  async function refreshNetwork() {
    try {
      setLoadingNet(true);
      const info = await apiGet('/info');
      setNetInfo(info);
      const p = await apiGet('/peers');
      setPeers(p?.peers ?? p ?? []);
    } catch (e) {
      // silently ignore
    } finally {
      setLoadingNet(false);
    }
  }

  async function refreshMe() {
    await Promise.allSettled([refreshWallet(), refreshFeed(), refreshGroups(), refreshProfile()]);
  }

  async function refreshWallet() {
    try {
      const w = await apiGet(`/wallet/get?address=${encodeURIComponent(address)}`);
      setBalance(Number(w?.balance ?? 0));
      setLevel(w?.level ?? 'L1');
    } catch (e) {}
  }

  async function refreshFeed() {
    try {
      setLoadingFeed(true);
      const f = await apiGet('/feed');
      setFeed(f?.items ?? f ?? []);
    } catch (e) {
    } finally {
      setLoadingFeed(false);
    }
  }

  async function refreshGroups() {
    try {
      setLoadingGroups(true);
      const g = await apiGet('/group/list');
      setGroups(g?.groups ?? g ?? []);
    } catch (e) {
    } finally {
      setLoadingGroups(false);
    }
  }

  async function refreshProfile() {
    try {
      const p = await apiGet(`/profile/get?address=${encodeURIComponent(address)}`);
      setProfile(p?.profile ?? p ?? null);
    } catch (e) {}
  }

  // ---- Key / Address derivation (kept as-is; only imports fixed) ----
  async function generateNewKey() {
    try {
      const m = bip39.generateMnemonic(bip39.wordlist);
      setSeed(m);
      toast.success('Seed generated');
    } catch (e) {
      toast.error(String(e?.message ?? e));
    }
  }

  async function loginFromSeed() {
    try {
      if (!seed || seed.trim().split(/\s+/).length < 12) {
        toast.error('Seed looks too short');
        return;
      }
      // Derive a private key from BIP39/BIP32 (same as your existing logic)
      const seedBytes = await bip39.mnemonicToSeed(seed.trim());
      const root = HDKey.fromMasterSeed(seedBytes);
      const child = root.derive("m/44'/0'/0'/0/0");

      const pk = child.privateKey;
      if (!pk) throw new Error('No private key derived');

      const priv = new Uint8Array(pk);
      const pub = secp.getPublicKey(priv, true);

      setPrivkey(u8ToHex(priv));
      setPubkey(u8ToHex(pub));

      // address = base58check(version + ripemd160(sha256(pub)))
      const h1 = sha256U8(pub);
      const h2 = ripemd160U8(h1);
      const version = new Uint8Array([0x00]);
      const addrPayload = u8Concat(version, h2);
      const addr = b58cEncode(addrPayload);

      setAddress(addr);
      setLoggedIn(true);
      toast.success('Logged in');
      await refreshMe();
    } catch (e) {
      toast.error(String(e?.message ?? e));
    }
  }

  async function registerUsername() {
    try {
      if (!loggedIn) {
        toast.error('Login first');
        return;
      }
      if (!username.trim()) {
        toast.error('Enter username');
        return;
      }
      await apiPost('/profile/set', {
        address,
        username: username.trim(),
      });
      toast.success('Profile saved');
      await refreshProfile();
    } catch (e) {
      toast.error(String(e?.message ?? e));
    }
  }

  // ---- Transfers ----
  async function sendTransfer() {
    try {
      if (!loggedIn) return toast.error('Login first');
      if (!sendTo.trim()) return toast.error('Enter recipient');
      const amt = Number(sendAmount);
      if (!Number.isFinite(amt) || amt <= 0) return toast.error('Bad amount');

      setSendBusy(true);
      await apiPost('/transfer', {
        from: address,
        to: sendTo.trim(),
        amount: amt,
      });
      toast.success('Transfer submitted');
      setSendAmount('');
      await refreshWallet();
    } catch (e) {
      toast.error(String(e?.message ?? e));
    } finally {
      setSendBusy(false);
    }
  }

  // ---- Messages ----
  async function sendMessage() {
    try {
      if (!loggedIn) return toast.error('Login first');
      if (!chatTo.trim()) return toast.error('Enter recipient');
      if (!msgText.trim()) return toast.error('Empty message');

      setMsgBusy(true);
      await apiPost('/message/send', {
        from: address,
        to: chatTo.trim(),
        text: msgText,
      });
      toast.success('Message sent');
      setMsgText('');
      await refreshFeed();
      await refreshWallet();
    } catch (e) {
      toast.error(String(e?.message ?? e));
    } finally {
      setMsgBusy(false);
    }
  }

  // ---- UI actions ----
  function copyText(txt) {
    if (!txt) return;
    navigator.clipboard.writeText(txt).then(
      () => toast.success('Copied'),
      () => toast.error('Copy failed')
    );
  }

  // ---- Render ----
  return (
    <div className="app">
      <Toaster position="top-right" />
      <header className="topbar">
        <div className="brand">
          <Shield size={22} />
          <div className="brandText">
            <div className="brandTitle">LAC Mobile</div>
            <div className="brandSub">testnet console</div>
          </div>
        </div>

        <div className="topbarRight">
          {loggedIn ? (
            <Pill>
              <span className="muted">addr</span> {address.slice(0, 10)}…{address.slice(-6)}
            </Pill>
          ) : (
            <Pill>Not logged in</Pill>
          )}

          <button className="iconBtn" onClick={() => refreshAll()} title="Refresh">
            <RefreshCw size={18} className={loadingNet ? 'spin' : ''} />
          </button>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <TabButton active={tab === 'Network'} onClick={() => setTab('Network')} icon={Radio} label="Network" />
          <TabButton active={tab === 'Login'} onClick={() => setTab('Login')} icon={KeyRound} label="Login/Register" />
          <TabButton active={tab === 'Wallet'} onClick={() => setTab('Wallet')} icon={Wallet} label="Wallet" />
          <TabButton active={tab === 'Messages'} onClick={() => setTab('Messages')} icon={MessageCircle} label="Messages" />
          <TabButton active={tab === 'Feed'} onClick={() => setTab('Feed')} icon={Bell} label="Feed" />
          <TabButton active={tab === 'Groups'} onClick={() => setTab('Groups')} icon={Users} label="Groups" />
          <TabButton active={tab === 'Stats'} onClick={() => setTab('Stats')} icon={Trophy} label="Stats" />
          <TabButton active={tab === 'Me'} onClick={() => setTab('Me')} icon={User} label="Me" />
          <div className="sidebarBottom">
            <a className="smallLink" href="https://github.com/epidemiaya/LightAnonChain-" target="_blank" rel="noreferrer">
              <ExternalLink size={14} /> GitHub
            </a>
          </div>
        </aside>

        <main className="content">
          {tab === 'Network' && (
            <>
              <Section
                title="Node info"
                icon={Radio}
                right={
                  <button className="btn" onClick={() => refreshNetwork()} disabled={loadingNet}>
                    {loadingNet ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />} Refresh
                  </button>
                }
              >
                <pre className="pre">
                  {netInfo ? JSON.stringify(netInfo, null, 2) : 'No data (is node running on /api ?)'}
                </pre>
              </Section>

              <Section title="Peers" icon={Users}>
                <pre className="pre">{JSON.stringify(peers, null, 2)}</pre>
              </Section>
            </>
          )}

          {tab === 'Login' && (
            <>
              <Section title="Seed / keys" icon={KeyRound}>
                <div className="row">
                  <button className="btn" onClick={generateNewKey}>
                    <Plus size={16} /> Generate seed
                  </button>
                  <button className="btn" onClick={loginFromSeed}>
                    <Lock size={16} /> Login from seed
                  </button>
                </div>

                <label className="label">Seed phrase</label>
                <textarea
                  className="input textarea"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  placeholder="seed words..."
                  rows={3}
                />

                <div className="grid2">
                  <div>
                    <label className="label">Private key (hex)</label>
                    <div className="inputRow">
                      <input className="input" value={privkey} readOnly placeholder="..." />
                      <button className="iconBtn" onClick={() => copyText(privkey)} title="Copy">
                        <Copy size={16} />
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="label">Public key (hex)</label>
                    <div className="inputRow">
                      <input className="input" value={pubkey} readOnly placeholder="..." />
                      <button className="iconBtn" onClick={() => copyText(pubkey)} title="Copy">
                        <Copy size={16} />
                      </button>
                    </div>
                  </div>
                </div>

                <label className="label">Address</label>
                <div className="inputRow">
                  <input className="input" value={address} readOnly placeholder="..." />
                  <button className="iconBtn" onClick={() => copyText(address)} title="Copy">
                    <Copy size={16} />
                  </button>
                </div>
              </Section>

              <Section title="Profile" icon={User}>
                <label className="label">Username</label>
                <div className="inputRow">
                  <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="name" />
                  <button className="btn" onClick={registerUsername} disabled={!loggedIn}>
                    <SaveIcon /> Save
                  </button>
                </div>

                <label className="label">Referral link</label>
                <div className="inputRow">
                  <input className="input" value={refLink} readOnly placeholder="..." />
                  <button className="iconBtn" onClick={() => copyText(refLink)} title="Copy">
                    <Copy size={16} />
                  </button>
                </div>

                {refLink ? (
                  <div className="qrWrap">
                    <QRCodeCanvas value={refLink} size={128} />
                  </div>
                ) : null}
              </Section>
            </>
          )}

          {tab === 'Wallet' && (
            <>
              <Section title="Balance" icon={Wallet}>
                <div className="statsRow">
                  <Pill>
                    <Flame size={14} /> burn tariff: <b>1</b>
                  </Pill>
                  <Pill>
                    <Zap size={14} /> level: <b>{level}</b>
                  </Pill>
                  <Pill>
                    <Wallet size={14} /> balance: <b>{balance}</b>
                  </Pill>
                </div>
              </Section>

              <Section title="Send transfer" icon={Send}>
                <label className="label">To</label>
                <input className="input" value={sendTo} onChange={(e) => setSendTo(e.target.value)} placeholder="address" />
                <label className="label">Amount</label>
                <input className="input" value={sendAmount} onChange={(e) => setSendAmount(e.target.value)} placeholder="0" />
                <div className="row">
                  <button className="btn" onClick={sendTransfer} disabled={!loggedIn || sendBusy}>
                    {sendBusy ? <Loader2 size={16} className="spin" /> : <Send size={16} />} Send
                  </button>
                </div>
              </Section>
            </>
          )}

          {tab === 'Messages' && (
            <>
              <Section title="Send message" icon={MessageCircle}>
                <label className="label">To</label>
                <input className="input" value={chatTo} onChange={(e) => setChatTo(e.target.value)} placeholder="address" />
                <label className="label">Message</label>
                <textarea
                  className="input textarea"
                  value={msgText}
                  onChange={(e) => setMsgText(e.target.value)}
                  placeholder="text..."
                  rows={4}
                />
                <div className="row">
                  <button className="btn" onClick={sendMessage} disabled={!loggedIn || msgBusy}>
                    {msgBusy ? <Loader2 size={16} className="spin" /> : <Send size={16} />} Send
                  </button>
                </div>
              </Section>
            </>
          )}

          {tab === 'Feed' && (
            <Section
              title="Feed"
              icon={Bell}
              right={
                <button className="btn" onClick={refreshFeed} disabled={loadingFeed}>
                  {loadingFeed ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />} Refresh
                </button>
              }
            >
              <pre className="pre">{JSON.stringify(feed, null, 2)}</pre>
            </Section>
          )}

          {tab === 'Groups' && (
            <Section
              title="Groups"
              icon={Users}
              right={
                <button className="btn" onClick={refreshGroups} disabled={loadingGroups}>
                  {loadingGroups ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />} Refresh
                </button>
              }
            >
              <pre className="pre">{JSON.stringify(groups, null, 2)}</pre>
            </Section>
          )}

          {tab === 'Stats' && (
            <Section title="Stats" icon={Trophy}>
              <pre className="pre">{JSON.stringify({ netInfo, peers: peers?.length ?? 0 }, null, 2)}</pre>
            </Section>
          )}

          {tab === 'Me' && (
            <Section title="Me" icon={User}>
              <pre className="pre">{JSON.stringify({ profile, address, level, balance }, null, 2)}</pre>
            </Section>
          )}
        </main>
      </div>
    </div>
  );
}

function SaveIcon() {
  return <Upload size={16} />;
}