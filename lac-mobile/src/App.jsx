/**
 * LAC Mobile v8 — Full-featured Privacy Blockchain App
 * Telegram-like design with all LAC features
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import {
  MessageCircle, Wallet, Settings, Send, Shield, Eye, Lock,
  Copy, ArrowLeft, Plus, Users, User, ChevronRight, LogOut,
  Clock, Hash, Award, Zap, Download, Upload, Search, X, Menu,
  RefreshCw, AlertTriangle, Check, Globe, Trash2, Star, Phone,
  Activity, Blocks, TrendingUp, QrCode, Network, Bell, Filter,
  ChevronDown, Bookmark, Gift, Flame, Timer, Link2, UserPlus, ArrowUpRight, ArrowDownLeft, Skull
} from 'lucide-react';

// ─── API Layer ────────────────────────────────────────
const api = async (path, opts = {}) => {
  const seed = localStorage.getItem('lac_seed');
  const h = { 'Content-Type': 'application/json' };
  if (seed) h['X-Seed'] = seed;
  const r = await fetch(path, { method: opts.method || 'GET', headers: { ...h, ...opts.headers }, body: opts.body ? JSON.stringify(opts.body) : undefined });
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || 'Error');
  return d;
};
const post = (p, b) => api(p, { method: 'POST', body: b });
const get = (p) => api(p);

// ─── Utils ────────────────────────────────────────────
const sAddr = (a) => a ? `${a.slice(0,8)}…${a.slice(-4)}` : '';
const ago = (ts) => { if (!ts) return ''; const s = ~~(Date.now()/1000-ts); return s<60?'now':s<3600?~~(s/60)+'m':s<86400?~~(s/3600)+'h':~~(s/86400)+'d'; };
const fmt = (n) => { const v=Number(n)||0; return v%1===0?v.toLocaleString():v.toLocaleString(undefined,{maximumFractionDigits:2}); };
const cp = (t) => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(t).then(() => toast.success('Copied!')).catch(() => cpFallback(t));
    } else { cpFallback(t); }
  } catch { cpFallback(t); }
};
const cpFallback = (t) => {
  const ta = document.createElement('textarea'); ta.value = t; ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
  document.body.appendChild(ta); ta.focus(); ta.select();
  try { document.execCommand('copy'); toast.success('Copied!'); } catch { prompt('Copy manually:', t); }
  document.body.removeChild(ta);
};

// ─── Shared Components ────────────────────────────────
const Header = ({ title, onBack, right }) => (
  <header className="flex items-center gap-3 px-4 py-3.5 bg-[#0a1f18]/90 backdrop-blur-lg border-b border-emerald-900/30 sticky top-0 z-10">
    {onBack && <button onClick={onBack} className="p-1 -ml-1"><ArrowLeft className="w-5 h-5 text-gray-400" /></button>}
    <h1 className="text-white font-semibold text-[17px] flex-1">{title}</h1>
    {right}
  </header>
);

const Card = ({ children, className = '', gradient, onClick }) => (
  <div onClick={onClick} className={`rounded-2xl p-4 border border-emerald-900/20 ${gradient || 'bg-[#0f1f1a]'} ${onClick?'cursor-pointer active:bg-emerald-900/10':''} ${className}`}>{children}</div>
);

const StatBox = ({ icon, label, value, color = 'text-emerald-400', small }) => (
  <div className={`bg-[#0a1a15] rounded-xl ${small ? 'p-2.5' : 'p-3'} text-center border border-emerald-900/15`}>
    <div className={`${small ? 'text-xl' : 'text-2xl'} font-bold ${color}`}>{value}</div>
    <div className="text-gray-500 text-[10px] mt-0.5 flex items-center justify-center gap-1">{icon}{label}</div>
  </div>
);

const Btn = ({ children, onClick, color = 'emerald', disabled, loading, full, ghost, small, className = '' }) => {
  const colors = {
    emerald: ghost ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-700/40' : 'bg-gradient-to-b from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-600/25',
    purple: ghost ? 'bg-purple-900/30 text-purple-400 border border-purple-700/40' : 'bg-gradient-to-b from-purple-500 to-purple-600 text-white shadow-lg shadow-purple-600/25',
    amber: ghost ? 'bg-amber-900/30 text-amber-400 border border-amber-700/40' : 'bg-gradient-to-b from-amber-500 to-amber-600 text-white shadow-lg shadow-amber-600/25',
    red: ghost ? 'bg-red-900/30 text-red-400 border border-red-700/40' : 'bg-gradient-to-b from-red-500 to-red-600 text-white shadow-lg shadow-red-600/25',
    gray: 'bg-gray-800 text-gray-300 border border-gray-700',
  };
  return (
    <button onClick={onClick} disabled={disabled || loading}
      className={`${small?'px-3 py-1.5 text-xs':'px-4 py-3 text-sm'} rounded-xl font-semibold transition-all active:scale-[0.98] disabled:opacity-40 ${full?'w-full':''} ${colors[color]} ${className}`}>
      {loading ? '⏳' : children}
    </button>
  );
};

const Input = ({ value, onChange, placeholder, mono, type = 'text', right }) => (
  <div className="relative">
    <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      className={`w-full bg-[#0a1a15] text-white px-4 py-3 rounded-xl border border-emerald-900/30 outline-none focus:border-emerald-600/50 transition text-sm ${mono?'font-mono':''}`} />
    {right && <div className="absolute right-3 top-1/2 -translate-y-1/2">{right}</div>}
  </div>
);

const Badge = ({ children, color = 'emerald' }) => {
  const c = { emerald: 'bg-emerald-900/40 text-emerald-400 border-emerald-700/30', purple: 'bg-purple-900/40 text-purple-400 border-purple-700/30', amber: 'bg-amber-900/40 text-amber-400 border-amber-700/30', red: 'bg-red-900/40 text-red-400 border-red-700/30', gray: 'bg-gray-800 text-gray-400 border-gray-700' };
  return <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${c[color]}`}>{children}</span>;
};

const TabBar = ({ tabs, active, onChange }) => (
  <div className="flex bg-[#0a1a15] rounded-xl p-0.5 gap-0.5">
    {tabs.map(([id, label]) => (
      <button key={id} onClick={() => onChange(id)}
        className={`flex-1 py-2 rounded-lg text-xs font-semibold transition-all ${active === id ? 'bg-emerald-600/20 text-emerald-400' : 'text-gray-500'}`}>
        {label}
      </button>
    ))}
  </div>
);

const ListItem = ({ icon, title, sub, right, onClick, badge }) => (
  <button onClick={onClick} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-emerald-900/10 active:bg-emerald-900/20 transition border-b border-gray-800/30">
    <div className="w-11 h-11 rounded-full bg-[#0f2a22] flex items-center justify-center shrink-0">{icon}</div>
    <div className="flex-1 min-w-0 text-left">
      <div className="flex items-center gap-2"><p className="text-white text-[14px] font-medium truncate">{title}</p>{badge}</div>
      {sub && <p className="text-gray-500 text-xs truncate">{sub}</p>}
    </div>
    {right || <ChevronRight className="w-4 h-4 text-gray-700 shrink-0" />}
  </button>
);

const Empty = ({ emoji, text, sub }) => (
  <div className="flex flex-col items-center py-16 text-gray-600">
    <div className="text-4xl mb-3 opacity-40">{emoji}</div>
    <p className="text-sm">{text}</p>
    {sub && <p className="text-xs mt-1 text-gray-700">{sub}</p>}
  </div>
);

const LevelBadge = ({ level }) => {
  const colors = ['from-gray-500 to-gray-600','from-emerald-500 to-emerald-600','from-teal-400 to-emerald-500','from-cyan-400 to-teal-500','from-amber-400 to-orange-500','from-red-400 to-rose-500','from-purple-400 to-pink-500'];
  return (
    <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${colors[level]||colors[0]} flex items-center justify-center text-white text-xs font-black shadow-lg`}>
      L{level}
    </div>
  );
};

// ━━━ APP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function App() {
  const [seed, setSeed] = useState(localStorage.getItem('lac_seed'));
  if (!seed) return <LoginScreen onAuth={s => { localStorage.setItem('lac_seed', s); setSeed(s); }} />;
  return <MainApp onLogout={() => { localStorage.clear(); setSeed(null); }} />;
}

// ━━━ LOGIN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const LoginScreen = ({ onAuth }) => {
  const [mode, setMode] = useState('welcome');
  const [imp, setImp] = useState('');
  const [gen, setGen] = useState('');
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  const mkSeed = () => { const c='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'; let s=''; for(let i=0;i<64;i++) s+=c[~~(Math.random()*c.length)]; return s; };

  const create = async () => {
    setLoading(true);
    try { const s = mkSeed(); const r = await post('/api/register', { seed: s }); if(r.ok){ setGen(s); localStorage.setItem('lac_address',r.address); setMode('backup'); } }
    catch(e){ toast.error(e.message); } finally { setLoading(false); }
  };

  const login = async () => {
    if(!imp.trim()||imp.length<16){ toast.error('Invalid seed'); return; }
    setLoading(true);
    try { const r = await post('/api/login', { seed: imp.trim() }); if(r.ok){ localStorage.setItem('lac_address',r.address); onAuth(imp.trim()); } }
    catch(e){ toast.error(e.message); } finally { setLoading(false); }
  };

  if (mode === 'welcome') return (
    <div className="h-screen bg-[#060f0c] flex flex-col items-center justify-center p-8">
      <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center mb-6 shadow-2xl shadow-emerald-600/30">
        <span className="text-4xl font-black text-white">L</span>
      </div>
      <h1 className="text-3xl font-bold text-white mb-1">LAC</h1>
      <p className="text-emerald-600 text-sm mb-1">Privacy-First Blockchain</p>
      <p className="text-gray-600 text-xs mb-10">Zero-History · VEIL · STASH · PoET</p>
      <div className="w-full max-w-sm space-y-3">
        <Btn onClick={create} color="emerald" full loading={loading}>Create Wallet</Btn>
        <Btn onClick={() => setMode('import')} color="gray" full>I Have a Seed</Btn>
      </div>
    </div>
  );

  if (mode === 'backup') return (
    <div className="h-screen bg-[#060f0c] flex flex-col p-6">
      <div className="flex-1 flex flex-col justify-center">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-amber-600/20 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-amber-400" />
          </div>
          <h2 className="text-2xl font-bold text-white">Save Your Seed</h2>
          <p className="text-gray-400 mt-2 text-sm">Write it down. This is your ONLY recovery method.</p>
        </div>
        <Card className="mb-4" gradient="bg-[#0a1810] border-amber-800/30">
          <p className="text-emerald-400 font-mono text-[13px] break-all leading-6 select-all">{gen}</p>
        </Card>
        <Btn onClick={() => { cp(gen); setSaved(true); }} color="gray" full>📋 Copy to Clipboard</Btn>
        {saved && <div className="mt-4"><Btn onClick={() => onAuth(gen)} color="emerald" full>I Saved It — Let's Go</Btn></div>}
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-[#060f0c] flex flex-col p-6">
      <button onClick={() => setMode('welcome')} className="text-gray-500 mb-6 flex items-center gap-1 text-sm"><ArrowLeft className="w-4 h-4" /> Back</button>
      <div className="flex-1 flex flex-col justify-center">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Import Wallet</h2>
        <textarea value={imp} onChange={e => setImp(e.target.value)} rows={3}
          className="w-full bg-[#0a1a15] text-emerald-400 font-mono text-sm p-4 rounded-2xl border border-emerald-900/30 outline-none resize-none mb-4" placeholder="Paste seed…" />
        <Btn onClick={login} color="emerald" full disabled={imp.length<16} loading={loading}>Login</Btn>
      </div>
    </div>
  );
};

// ━━━ MAIN SHELL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const MainApp = ({ onLogout }) => {
  const [tab, setTab] = useState('wallet');
  const [profile, setProfile] = useState(null);
  const [sub, setSub] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const panicClicks = useRef(0);
  const panicTimer = useRef(null);

  const reload = useCallback(async () => { try { setProfile(await get('/api/profile')); } catch {} }, []);
  useEffect(() => { reload(); const i = setInterval(reload, 10000); return () => clearInterval(i); }, [reload]);

  const handlePanic = () => {
    panicClicks.current += 1;
    if (panicTimer.current) clearTimeout(panicTimer.current);
    if (panicClicks.current >= 3) {
      panicClicks.current = 0;
      if (confirm('⚠️ PANIC MODE\n\nThis will DESTROY all wallet data!\nAre you absolutely sure?')) {
        post('/api/panic').then(() => { toast('🔥 Wallet wiped!'); onLogout(); }).catch(() => { localStorage.clear(); onLogout(); });
      }
    } else {
      toast(`⚠️ PANIC: tap ${3-panicClicks.current} more`, {duration:1500, icon:'🚨'});
      panicTimer.current = setTimeout(() => { panicClicks.current = 0; }, 2500);
    }
  };

  const p = profile || {};
  const uname = p.username && p.username !== 'Anonymous' && p.username !== 'None' ? p.username : null;

  if (sub) {
    const back = () => setSub(null);
    const done = () => { back(); reload(); };
    const screens = {
      chat: <ChatView peer={sub.peer} onBack={back} profile={profile} />,
      group: <GroupView group={sub.group} onBack={back} profile={profile} />,
      newchat: <NewChat onBack={back} onGo={p => setSub({type:'chat',peer:p})} />,
      newgroup: <NewGroup onBack={back} onDone={done} />,
      send: <SendView onBack={back} profile={profile} onDone={done} />,
      stash: <STASHView onBack={back} onDone={done} />,
      txs: <TxsView onBack={back} />,
      username: <UsernameView onBack={back} onDone={done} />,
      contacts: <ContactsView onBack={back} onChat={p => setSub({type:'chat',peer:p})} />,
      timelock: <TimelockView onBack={back} profile={profile} onDone={done} />,
      dms: <DeadManSwitchView onBack={back} profile={profile} onDone={done} />,
      mining: <MiningView onBack={back} profile={profile} />,
      explorer: <ExplorerView onBack={back} />,
      dashboard: <DashboardView onBack={back} />,
      validator: <ValidatorView onBack={back} profile={profile} onRefresh={reload} />,
      dice: <DiceView onBack={back} profile={profile} onRefresh={reload} />,
    };
    return (
      <div className="w-full h-screen bg-gradient-to-br from-gray-900 to-gray-950 flex items-center justify-center p-2 sm:p-4">
        <div className="w-full max-w-md h-full max-h-[850px] bg-[#060f0c] rounded-3xl shadow-2xl shadow-emerald-900/20 overflow-hidden border border-emerald-900/30 flex flex-col relative">
          {screens[sub.type] || null}
        </div>
      </div>
    );
  }

  const menuItems = [
    { icon: User, label: 'Profile', act: () => { setTab('profile'); setMenuOpen(false); } },
    { icon: Activity, label: 'Explorer', act: () => { setSub({type:'explorer'}); setMenuOpen(false); } },
    { icon: Zap, label: 'Mining', act: () => { setSub({type:'mining'}); setMenuOpen(false); } },
    { icon: Timer, label: 'Time-Lock', act: () => { setSub({type:'timelock'}); setMenuOpen(false); } },
    { icon: Skull, label: 'Dead Man Switch', act: () => { setSub({type:'dms'}); setMenuOpen(false); } },
    { icon: Lock, label: 'STASH Pool', act: () => { setSub({type:'stash'}); setMenuOpen(false); } },
    { icon: Hash, label: 'Username', act: () => { setSub({type:'username'}); setMenuOpen(false); } },
    { icon: Users, label: 'Contacts', act: () => { setSub({type:'contacts'}); setMenuOpen(false); } },
    { icon: TrendingUp, label: 'Dashboard', act: () => { setSub({type:'dashboard'}); setMenuOpen(false); } },
    { icon: Shield, label: 'Validator', act: () => { setSub({type:'validator'}); setMenuOpen(false); } },
  ];

  return (
    <div className="w-full h-screen bg-gradient-to-br from-gray-900 to-gray-950 flex items-center justify-center p-2 sm:p-4">
      <div className="w-full max-w-md h-full max-h-[850px] bg-[#060f0c] rounded-3xl shadow-2xl shadow-emerald-900/20 overflow-hidden border border-emerald-900/30 flex flex-col relative">
        <Toaster position="top-center" toastOptions={{style:{background:'#0f2a22',color:'#e5fff5',borderRadius:'14px',border:'1px solid rgba(14,230,138,.15)',fontSize:'13px'}}} />

        {/* Hamburger Menu Overlay */}
        {menuOpen && (
          <div className="absolute inset-0 z-50 flex">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMenuOpen(false)} />
            <div className="relative w-[280px] h-full bg-[#0a1510] border-r border-emerald-900/30 overflow-y-auto z-10 shadow-2xl">
              {/* Menu Header */}
              <div className="p-5 border-b border-emerald-900/20">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-white font-bold text-lg">Menu</span>
                  <button onClick={() => setMenuOpen(false)} className="text-gray-500"><X className="w-5 h-5" /></button>
                </div>
                <div className="flex items-center gap-3 p-3 bg-[#0f2a22] rounded-xl border border-emerald-900/20">
                  <div className="w-11 h-11 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center">
                    <span className="text-white font-bold text-sm">{(p.address||'LA').slice(4,6).toUpperCase()}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm truncate">{uname || 'Anonymous'}</p>
                    <p className="text-gray-500 text-[11px] font-mono truncate">{sAddr(p.address)}</p>
                    <Badge>{`L${p.level ?? 0}`}</Badge>
                  </div>
                </div>
              </div>
              {/* Menu Items */}
              <div className="py-2">
                {menuItems.map((m, i) => (
                  <button key={i} onClick={m.act} className="w-full flex items-center gap-3 px-5 py-3 text-gray-300 hover:bg-emerald-900/20 hover:text-white transition">
                    <m.icon className="w-5 h-5 text-gray-500" /><span className="text-sm font-medium">{m.label}</span>
                  </button>
                ))}
              </div>
              <div className="border-t border-emerald-900/20 p-5">
                <Btn onClick={() => { if(confirm('Save seed first!')) onLogout(); }} color="red" full>
                  <span className="flex items-center justify-center gap-2"><LogOut className="w-4 h-4" />Logout</span>
                </Btn>
                <p className="text-gray-700 text-[10px] text-center mt-3">LAC v8 · Zero-History · PoET</p>
              </div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {tab === 'chats' && <ChatsTab profile={profile} onNav={setSub} onMenu={() => setMenuOpen(true)} />}
          {tab === 'wallet' && <WalletTab profile={profile} onNav={setSub} onRefresh={reload} onMenu={() => setMenuOpen(true)} setTab={setTab} />}
          {tab === 'explore' && <ExploreTab onNav={setSub} onMenu={() => setMenuOpen(true)} />}
          {tab === 'profile' && <ProfileTab profile={profile} onNav={setSub} onLogout={onLogout} onRefresh={reload} onMenu={() => setMenuOpen(true)} />}
        </div>

        {/* Bottom Navigation */}
        <nav className="bg-[#0a1510] border-t border-emerald-900/20 flex shrink-0">
          {[
            { id: 'chats', icon: MessageCircle, label: 'Chats' },
            { id: 'wallet', icon: Wallet, label: 'Wallet' },
            { id: 'panic', icon: AlertTriangle, label: 'PANIC', isPanic: true },
            { id: 'explore', icon: Activity, label: 'Explore' },
            { id: 'profile', icon: User, label: 'Profile' },
          ].map(n => (
            <button key={n.id} onClick={n.isPanic ? handlePanic : () => setTab(n.id)}
              className={`flex-1 py-3 flex flex-col items-center gap-0.5 transition ${n.isPanic ? 'text-red-500 hover:text-red-400' : tab===n.id?'text-emerald-400':'text-gray-600'}`}>
              <n.icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{n.label}</span>
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
};

// ━━━ CHATS TAB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ChatsTab = ({ profile, onNav, onMenu }) => {
  const [sec, setSec] = useState('dm');
  const [msgs, setMsgs] = useState([]);
  const [groups, setGroups] = useState([]);

  const load = async () => { try { const [i,g] = await Promise.all([get('/api/inbox'),get('/api/groups')]); setMsgs(i.messages||[]); setGroups(g.groups||[]); } catch {} };
  useEffect(() => { load(); const i = setInterval(load, 3000); return () => clearInterval(i); }, []);

  const convos = {};
  msgs.forEach(m => {
    const sent = m.direction==='sent';
    const peer = sent ? (m.to||'?') : (m.from_address||m.from||'?');
    const name = sent ? (m.to_display||m.to||'?') : (m.from||sAddr(m.from_address)||'Anon');
    if (!convos[peer]) convos[peer] = { peer, name, last: null, cnt: 0 };
    convos[peer].cnt++;
    if (!convos[peer].last || (m.timestamp||0) > (convos[peer].last.timestamp||0)) { convos[peer].last = m; if (!sent) convos[peer].name = name; }
  });
  const sorted = Object.values(convos).sort((a,b) => (b.last?.timestamp||0)-(a.last?.timestamp||0));

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
            <h1 className="text-xl font-bold text-white">Chats</h1>
          </div>
          <button onClick={() => onNav({type: sec==='dm'?'newchat':'newgroup'})}
            className="w-9 h-9 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-full flex items-center justify-center shadow-lg shadow-emerald-600/25">
            <Plus className="w-4 h-4 text-white" />
          </button>
        </div>
        <TabBar tabs={[['dm','💬 Messages'],['groups','👥 Groups']]} active={sec} onChange={setSec} />
      </div>
      <div className="flex-1 overflow-y-auto">
        {sec === 'dm' ? (
          sorted.length === 0 ? <Empty emoji="💬" text="No messages" sub="Start a conversation" /> :
          sorted.map(c => (
            <ListItem key={c.peer}
              icon={<User className="w-5 h-5 text-emerald-500" />}
              title={c.name} sub={c.last?.text||c.last?.message||''}
              right={<span className="text-gray-600 text-[11px]">{ago(c.last?.timestamp)}</span>}
              onClick={() => onNav({type:'chat',peer:{address:c.peer,name:c.name}})} />
          ))
        ) : (
          groups.length === 0 ? <Empty emoji="👥" text="No groups" sub="Create a group" /> :
          groups.map(g => {
            const tb = {public:['emerald','🌍 Public'],private:['purple','🔒 Private'],l1_blockchain:['blue','⛓ L1'],l2_ephemeral:['amber','⚡ L2']}[g.type]||['emerald','🌍 Public'];
            return (
            <ListItem key={g.id||g.name}
              icon={<Users className="w-5 h-5 text-purple-400" />}
              title={g.name}
              badge={<Badge color={tb[0]}>{tb[1]}</Badge>}
              sub={`${g.member_count||0} members · ${g.post_count||0} posts`}
              onClick={() => onNav({type:'group',group:g})} />
          );})
        )}
      </div>
    </div>
  );
};

// ━━━ CHAT VIEW ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ChatView = ({ peer, onBack, profile }) => {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [mode, setMode] = useState('regular'); // regular | ephemeral | burn
  const end = useRef(null);
  const resolvedAddr = useRef(peer.address);
  const localMsgs = useRef([]); // client-side message store (source of truth)
  const lastJson = useRef(''); // prevent unnecessary re-renders

  // Merge server data into local store without losing optimistic messages
  const mergeServer = (serverMsgs) => {
    const local = localMsgs.current;
    // Build a set of server message keys
    const serverKeys = new Set(serverMsgs.map(m => m.text + '|' + (m.timestamp||0)));
    // Keep unconfirmed optimistic messages
    const surviving = local.filter(m => m._opt && !serverKeys.has(m.text + '|' + m.timestamp));
    // Merge and sort
    const merged = [...serverMsgs, ...surviving].sort((a,b) => (a.timestamp||0) - (b.timestamp||0));
    // Only update React state if data actually changed
    const json = JSON.stringify(merged.map(m => m.text + (m._opt?'_p':'') + m.timestamp));
    if (json !== lastJson.current) {
      lastJson.current = json;
      localMsgs.current = merged;
      setMsgs(merged);
    }
  };

  const load = async () => {
    try {
      const r = await get('/api/chat?peer='+encodeURIComponent(resolvedAddr.current));
      if (r.peer_addr && r.peer_addr.startsWith('lac')) resolvedAddr.current = r.peer_addr;
      mergeServer(r.messages || []);
    } catch {}
  };
  useEffect(() => { load(); const i=setInterval(load,1500); return()=>clearInterval(i); }, []);
  useEffect(() => { end.current?.scrollIntoView({behavior:'smooth'}); }, [msgs]);

  const send = async () => {
    if(!text.trim()||sending) return;
    const txt = text.trim();
    setSending(true);
    setText('');
    // INSTANT optimistic
    const ts = ~~(Date.now()/1000);
    const isEph = mode === 'ephemeral';
    const isBurn = mode === 'burn';
    const opt = {
      from: profile?.username||profile?.address, from_address: profile?.address,
      to: peer.address, text: txt, timestamp: ts,
      direction: 'sent', ephemeral: isEph, burn: isBurn, msg_type: isEph?'ephemeral':'regular', _opt: true
    };
    localMsgs.current = [...localMsgs.current, opt];
    setMsgs([...localMsgs.current]);
    lastJson.current = ''; // force next merge to update
    setSending(false); // unblock immediately
    // Fire and forget — poll will confirm
    try {
      const res = await post('/api/message.send',{to:peer.address,text:txt,ephemeral:isEph,burn:isBurn});
      if (res.to_address) resolvedAddr.current = res.to_address;
    } catch(e) {
      toast.error(e.message);
      localMsgs.current = localMsgs.current.filter(m => m !== opt);
      setMsgs([...localMsgs.current]);
    }
  };

  const peerName = peer.name && peer.name.length < 30 ? peer.name : sAddr(peer.address);
  const myAddr = profile?.address;

  return (
    <div className="h-full bg-[#060f0c] flex flex-col">
      <Header title={peerName} onBack={onBack}
        right={<div className="flex gap-1">
          {[['regular','💬','gray'],['ephemeral','⏱','amber'],['burn','🔥','red']].map(([m,ic,c]) => 
            <button key={m} onClick={() => setMode(m)} className={`px-2 py-1 rounded-lg text-[10px] font-medium transition ${mode===m?`bg-${c}-600/20 text-${c}-400 border border-${c}-600/30`:'bg-gray-800/50 text-gray-600 border border-transparent'}`}>{ic}</button>
          )}
        </div>} />
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {msgs.length===0 && !sending && <Empty emoji="💬" text="No messages yet" sub="Send the first message" />}
        {msgs.map((m,i) => {
          const mine = m.direction==='sent' || m.from_address===myAddr;
          const isEph = m.ephemeral || m.msg_type==='ephemeral';
          const isBurn = m.burn;
          const burned = m.burned;
          return (
            <div key={i} className={`flex ${mine?'justify-end':'justify-start'}`}>
              <div className={`max-w-[78%] px-3.5 py-2 rounded-2xl ${burned?'bg-gray-900/50 border border-gray-800':mine?'bg-gradient-to-br from-emerald-600 to-emerald-700 text-white rounded-br-sm':'bg-[#0f2a22] text-gray-100 rounded-bl-sm border border-emerald-900/20'}`}>
                {!mine && <p className="text-purple-400 text-[11px] font-medium mb-0.5">{m.from||sAddr(m.from_address)}</p>}
                <p className={`text-[14px] leading-snug ${burned?'text-gray-600 italic':''}`}>{m.text||m.message}</p>
                <div className={`flex items-center gap-1.5 mt-0.5 ${mine?'justify-end':''}`}>
                  {isEph && <span className="text-[9px] opacity-50">⏱</span>}
                  {isBurn && !burned && <span className="text-[9px] text-red-400">🔥</span>}
                  <span className={`text-[10px] ${mine?'text-emerald-300/50':'text-gray-600'}`}>{ago(m.timestamp)}</span>
                  {mine && <span className="text-[10px] text-emerald-300/60">{m._opt ? '⏳' : '✓'}</span>}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={end} />
      </div>
      {/* Message mode indicator */}
      {mode === 'ephemeral' && <div className="text-center py-1 bg-amber-900/10"><span className="text-amber-400/70 text-[10px]">⏱ Ephemeral L2 — self-destruct 5 min</span></div>}
      {mode === 'burn' && <div className="text-center py-1 bg-red-900/10"><span className="text-red-400/70 text-[10px]">🔥 Burn after read — destroyed when opened</span></div>}
      <div className="p-2.5 bg-[#0a1510] border-t border-emerald-900/20">
        <div className="flex gap-2 items-end">
          <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key==='Enter'&&!e.shiftKey&&send()}
            className="flex-1 bg-[#0a1a15] text-white px-4 py-2.5 rounded-2xl text-sm outline-none border border-emerald-900/30 focus:border-emerald-600/40 placeholder-gray-600"
            placeholder={mode==='ephemeral'?'Ephemeral (5min)…':mode==='burn'?'🔥 Burn after read…':'Message…'} />
          <button onClick={send} disabled={sending||!text.trim()} className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-full flex items-center justify-center shrink-0 disabled:opacity-30 shadow-lg shadow-emerald-600/20">
            <Send className="w-4 h-4 text-white ml-0.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

// ━━━ GROUP VIEW ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const GroupView = ({ group, onBack, profile }) => {
  const [posts, setPosts] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const end = useRef(null);
  const isEph = group.type==='l2_ephemeral' || group.type==='ephemeral';
  const isL1 = group.type==='l1_blockchain';
  const isPrivate = group.type==='private';
  const typeBadge = isEph ? ['amber','⚡ L2 Ephemeral'] : isL1 ? ['blue','⛓ L1 Chain'] : isPrivate ? ['purple','🔒 Private'] : ['emerald','🌍 Public'];
  const gid = group.id || group.name;
  const localPosts = useRef([]);
  const lastJson = useRef('');

  const mergeServer = (serverPosts) => {
    const local = localPosts.current;
    const serverKeys = new Set(serverPosts.map(p => (p.text||p.message) + '|' + (p.timestamp||0)));
    const surviving = local.filter(p => p._opt && !serverKeys.has(p.text + '|' + p.timestamp));
    const merged = [...serverPosts, ...surviving].sort((a,b) => (a.timestamp||0) - (b.timestamp||0));
    const json = JSON.stringify(merged.map(p => (p.text||p.message) + (p._opt?'_p':'') + p.timestamp));
    if (json !== lastJson.current) {
      lastJson.current = json;
      localPosts.current = merged;
      setPosts(merged);
    }
  };

  const load = async () => {
    try { mergeServer((await get('/api/group/posts?group_id='+encodeURIComponent(gid))).posts||[]); } catch {}
  };
  useEffect(() => { load(); const i=setInterval(load,1500); return()=>clearInterval(i); }, []);
  useEffect(() => { end.current?.scrollIntoView({behavior:'smooth'}); }, [posts]);

  const send = async () => {
    if(!text.trim()||sending) return;
    const txt = text.trim();
    setSending(true);
    setText('');
    const ts = ~~(Date.now()/1000);
    const opt = { from: profile?.username||'You', from_address: profile?.address, text: txt, message: txt, timestamp: ts, _opt: true };
    localPosts.current = [...localPosts.current, opt];
    setPosts([...localPosts.current]);
    lastJson.current = '';
    setSending(false);
    try { await post('/api/group.post',{group_id:gid,message:txt}); }
    catch(e) {
      toast.error(e.message);
      localPosts.current = localPosts.current.filter(p => p !== opt);
      setPosts([...localPosts.current]);
    }
  };

  return (
    <div className="h-full bg-[#060f0c] flex flex-col">
      <Header title={group.name} onBack={onBack} right={
        <div className="flex items-center gap-2">
          <button onClick={() => { cp(gid); toast.success('Group link copied!'); }} className="p-1.5 rounded-lg bg-gray-800 text-gray-400 active:bg-gray-700"><Copy className="w-3.5 h-3.5" /></button>
          <Badge color={typeBadge[0]}>{typeBadge[1]}</Badge>
        </div>} />
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {isEph && <div className="text-center py-1"><span className="text-amber-400/60 text-[10px] bg-amber-600/10 px-3 py-1 rounded-full">⚡ Messages self-destruct after 5 min</span></div>}
        {isL1 && <div className="text-center py-1"><span className="text-blue-400/60 text-[10px] bg-blue-600/10 px-3 py-1 rounded-full">⛓ On-chain · Zero-History cleans L3→L2→L1</span></div>}
        {isPrivate && <div className="text-center py-1"><span className="text-purple-400/60 text-[10px] bg-purple-600/10 px-3 py-1 rounded-full">🔒 Private group · Invite only</span></div>}
        {posts.length===0 && <Empty emoji="💬" text="No messages yet" sub="Write the first message" />}
        {posts.map((p,i) => { const mine=p.from_address===profile?.address; return (
          <div key={i} className={`flex ${mine?'justify-end':'justify-start'}`}>
            <div className={`max-w-[78%] px-3.5 py-2 rounded-2xl ${mine?'bg-gradient-to-br from-emerald-600 to-emerald-700 text-white rounded-br-sm':'bg-[#0f2a22] text-gray-100 rounded-bl-sm border border-emerald-900/20'}`}>
              {!mine && <p className="text-purple-400 text-[11px] font-medium mb-0.5">{p.from||'Anon'}</p>}
              <p className="text-[14px] leading-snug">{p.text||p.message}</p>
              <p className={`text-[10px] mt-0.5 ${mine?'text-emerald-300/50':'text-gray-600'}`}>{ago(p.timestamp)}</p>
            </div>
          </div>
        ); })}
        <div ref={end} />
      </div>
      <div className="p-2.5 bg-[#0a1510] border-t border-emerald-900/20">
        <div className="flex gap-2 items-end">
          <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key==='Enter'&&!e.shiftKey&&send()}
            className="flex-1 bg-[#0a1a15] text-white px-4 py-2.5 rounded-2xl text-sm outline-none border border-emerald-900/30 placeholder-gray-600" placeholder="Message…" />
          <button onClick={send} disabled={sending||!text.trim()} className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-full flex items-center justify-center shrink-0 disabled:opacity-30"><Send className="w-4 h-4 text-white ml-0.5" /></button>
        </div>
      </div>
    </div>
  );
};

// ━━━ NEW CHAT / GROUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const NewChat = ({ onBack, onGo }) => {
  const [to, setTo] = useState('');
  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="New Message" onBack={onBack} />
    <div className="p-4"><p className="text-gray-500 text-xs mb-2">Enter @username or lac1… address</p>
      <Input value={to} onChange={setTo} placeholder="@alice or lac1…" mono />
      <div className="mt-4"><Btn onClick={() => to.trim()&&onGo({address:to.trim(),name:to.trim()})} color="emerald" full disabled={!to.trim()}>Start Chat</Btn></div>
    </div></div>);
};

const NewGroup = ({ onBack, onDone }) => {
  const [name, setName] = useState(''); const [type, setType] = useState('public'); const [ld, setLd] = useState(false);
  const go = async () => { setLd(true); try { await post('/api/group.create',{name:name.trim(),type}); toast.success('Created!'); onDone(); } catch(e){ toast.error(e.message); } finally { setLd(false); } };
  const types = [
    ['public','🌍 Public','Anyone can see and write. Data on server.'],
    ['private','🔒 Private','By invite only. Encrypted.'],
    ['l1_blockchain','⛓ L1 Blockchain','Messages in blocks. Zero-History cleans by tiers.'],
    ['l2_ephemeral','⚡ L2 Ephemeral','5 minutes and gone.'],
  ];
  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="Create Group" onBack={onBack} />
    <div className="p-4 space-y-4">
      <div><label className="text-gray-500 text-xs mb-1 block">Name</label><Input value={name} onChange={setName} placeholder="Group name" /></div>
      <div><label className="text-gray-500 text-xs mb-2 block">Type</label>
        <div className="space-y-2">
          {types.map(([id,l,d]) => (
            <button key={id} onClick={() => setType(id)} className={`w-full p-3 rounded-xl border text-left transition ${type===id?'border-emerald-500 bg-emerald-600/10':'border-gray-800 bg-[#0a1a15]'}`}>
              <p className="text-white text-sm font-medium">{l}</p><p className="text-gray-500 text-[10px] mt-0.5">{d}</p>
            </button>))}
        </div>
      </div>
      <Btn onClick={go} color="emerald" full disabled={!name.trim()} loading={ld}>Create Group</Btn>
    </div></div>);
};

// ━━━ WALLET TAB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const WalletTab = ({ profile, onNav, onRefresh, onMenu, setTab }) => {
  const p = profile || {};
  return (
    <div className="h-full overflow-y-auto pb-4">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="flex items-center gap-3">
          <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
          <h1 className="text-xl font-bold text-white">Wallet</h1>
        </div>
        <button onClick={onRefresh} className="text-emerald-500 text-xs font-medium">✓ Refresh</button>
      </div>
      {/* Balance Card */}
      <div className="mx-4 mt-4">
        <Card gradient="bg-gradient-to-br from-purple-600 via-blue-600 to-emerald-600 border-purple-500/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-xs">Total Balance</p>
              <p className="text-4xl font-bold text-white mt-1">{fmt(p.balance)}</p>
              <p className="text-purple-200 text-lg">LAC</p>
            </div>
            <LevelBadge level={p.level??0} />
          </div>
          <div className="flex items-center gap-2 mt-3">
            <span className="text-purple-200/60 text-[11px] font-mono">{sAddr(p.address)}</span>
            <button onClick={() => cp(p.address)} className="text-purple-200/40 hover:text-white"><Copy className="w-3 h-3" /></button>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            <Btn onClick={() => onNav({type:'send'})} color="emerald" small>↗ Send</Btn>
            <Btn onClick={async () => { try { const r=await post('/api/faucet'); toast.success(`+${r.added||30} LAC`); onRefresh(); } catch(e){ toast.error(e.message); } }} color="gray" small>🚰 Faucet</Btn>
          </div>
        </Card>
      </div>

      {/* Quick Grid */}
      <div className="grid grid-cols-4 gap-2 px-4 mt-3">
        {[
          {icon:'👻',label:'VEIL',act:()=>onNav({type:'send'})},
          {icon:'🎒',label:'STASH',act:()=>onNav({type:'stash'})},
          {icon:'🎲',label:'Dice',act:()=>onNav({type:'dice'})},
          {icon:'👥',label:'Contacts',act:()=>onNav({type:'contacts'})},
        ].map((a,i) => (
          <button key={i} onClick={a.act} className="flex flex-col items-center gap-1 py-2.5 rounded-xl bg-[#0a1a15] border border-emerald-900/15 active:bg-emerald-900/20">
            <span className="text-xl">{a.icon}</span>
            <span className="text-gray-500 text-[10px]">{a.label}</span>
          </button>
        ))}
      </div>

      {/* Mining */}
      <div className="mx-4 mt-3">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2"><Zap className="w-4 h-4 text-emerald-400" /><span className="text-white text-sm font-semibold">Mining</span></div>
            <button onClick={() => onNav({type:'mining'})} className="text-emerald-500 text-xs">Details →</button>
          </div>
          <MiningMini />
        </Card>
      </div>

      {/* Level */}
      <div className="mx-4 mt-3">
        <Card>
          <div className="flex items-center justify-between mb-1">
            <span className="text-white text-sm font-semibold">Level Progress</span>
            <Badge>L{p.level??0}</Badge>
          </div>
          <LevelBar level={p.level??0} balance={p.balance||0} />
        </Card>
      </div>

      {/* Recent TXs */}
      <div className="mx-4 mt-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-gray-500 text-xs font-medium">Recent Transactions</span>
          <button onClick={() => onNav({type:'txs'})} className="text-emerald-500 text-[11px]">View All</button>
        </div>
        <RecentTxs />
      </div>
    </div>
  );
};

const MiningMini = () => {
  const [d, setD] = useState(null);
  useEffect(() => { get('/api/wallet/mining?limit=100').then(setD).catch(() => {}); }, []);
  if (!d) return <p className="text-gray-600 text-xs">Loading…</p>;
  const earned = d.total_mined || 0;
  const mined = d.count || 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-2xl font-bold text-emerald-400">{earned > 0 ? fmt(earned) : '0'} <span className="text-sm text-gray-500">LAC earned</span></p>
        </div>
        <div className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${mined>0?'bg-emerald-900/40 text-emerald-400':'bg-amber-900/30 text-amber-400'}`}>
          {mined>0?'⛏ Active':'⏳ Waiting'}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <StatBox label="Blocks Mined" value={mined} small />
        <StatBox label="Per Block" value="~10 LAC" color="text-gray-400" small />
      </div>
    </div>
  );
};

const levelCosts = [100, 700, 2000, 10000, 100000, 500000, 0]; // L0→L1, L1→L2, ... L5→L6, L6=MAX
const LevelBar = ({ level, balance }) => {
  const cost = levelCosts[level] || 0; // cost to go from current level to next
  const pct = cost > 0 ? Math.min(100, (balance/cost)*100) : 100;
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1"><span className="text-gray-500">L{level}</span><span className="text-gray-500">{cost>0?`${fmt(balance)}/${fmt(cost)} LAC`:'MAX'}</span><span className="text-gray-500">L{level+1}</span></div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all" style={{width:`${pct}%`}} /></div>
    </div>
  );
};

const RecentTxs = () => {
  const [txs, setTxs] = useState(null);
  useEffect(() => {
    get('/api/wallet/transactions').then(d => {
      const t=d.transactions||{};
      setTxs([...(t.sent||[]).map(x=>({...x,dir:'sent'})),...(t.received||[]).map(x=>({...x,dir:'received'})),...(t.mining||[]).map(x=>({...x,dir:'mined'})),...(t.burned||[]).map(x=>({...x,dir:'burned'}))].sort((a,b)=>(b.timestamp||0)-(a.timestamp||0)).slice(0,5));
    }).catch(() => setTxs([]));
  }, []);
  if (!txs) return null;
  if (txs.length===0) return <p className="text-gray-700 text-sm text-center py-4">No transactions</p>;
  return <div>{txs.map((tx,i) => <TxRow key={i} tx={tx} />)}</div>;
};

const TxRow = ({ tx }) => {
  const isIn = tx.dir==='received'||tx.dir==='mined';
  const icons = {received:<ArrowDownLeft className="w-4 h-4 text-emerald-400"/>,sent:<ArrowUpRight className="w-4 h-4 text-gray-400"/>,mined:<Zap className="w-4 h-4 text-blue-400"/>,burned:<Flame className="w-4 h-4 text-red-400"/>};
  const bgs = {received:'bg-emerald-900/30',sent:'bg-gray-800',mined:'bg-blue-900/30',burned:'bg-red-900/30'};
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-gray-800/20">
      <div className={`w-9 h-9 rounded-full flex items-center justify-center ${bgs[tx.dir]||'bg-gray-800'}`}>{icons[tx.dir]}</div>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm">{tx.dir==='mined'?'Mining Reward':tx.type||tx.dir}</p>
        <p className="text-gray-600 text-[11px]">{ago(tx.timestamp)}{tx.block?` · #${tx.block}`:''}</p>
      </div>
      <span className={`text-sm font-semibold ${isIn?'text-emerald-400':'text-gray-400'}`}>{isIn?'+':'−'}{fmt(tx.amount)}</span>
    </div>
  );
};

// ━━━ SEND ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const SendView = ({ onBack, profile, onDone }) => {
  const [type, setType] = useState(null); const [to, setTo] = useState(''); const [amt, setAmt] = useState(''); const [ld, setLd] = useState(false);
  const go = async () => { setLd(true); try { await post(type==='veil'?'/api/transfer/veil':'/api/transfer/normal',{to:to.trim(),amount:parseFloat(amt)}); toast.success('Sent!'); onDone(); } catch(e){ toast.error(e.message); } finally { setLd(false); } };

  if (!type) return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="Send LAC" onBack={onBack} />
    <div className="p-4 space-y-3">
      <button onClick={() => setType('normal')} className="w-full bg-[#0f1f1a] border border-emerald-900/20 rounded-2xl p-4 flex items-center gap-4 active:bg-emerald-900/20">
        <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center"><Send className="w-6 h-6 text-white" /></div>
        <div className="text-left"><p className="text-white font-semibold">Normal Transfer</p><p className="text-gray-500 text-xs">Public on blockchain · 0.1 LAC fee</p></div>
      </button>
      <button onClick={() => setType('veil')} className="w-full bg-[#0f1f1a] border border-emerald-900/20 rounded-2xl p-4 flex items-center gap-4 active:bg-purple-900/20">
        <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-fuchsia-600 rounded-2xl flex items-center justify-center"><Eye className="w-6 h-6 text-white" /></div>
        <div className="text-left"><p className="text-white font-semibold">VEIL Transfer</p><p className="text-gray-500 text-xs">Full anonymity · Ring + Phantom TXs · 1.0 LAC</p>
          <span className="flex gap-1 mt-1 flex-wrap">{['Ring Sig','Phantom','OTA','Zero-History'].map(f => <Badge key={f} color="purple">{f}</Badge>)}</span>
        </div>
      </button>
    </div></div>);

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title={type==='veil'?'VEIL Transfer':'Normal Transfer'} onBack={() => setType(null)} />
    <div className="p-4 space-y-4">
      <div className={`rounded-xl p-3 border flex items-center gap-2 ${type==='veil'?'bg-purple-900/15 border-purple-700/30':'bg-blue-900/15 border-blue-700/30'}`}>
        {type==='veil'?<Eye className="w-4 h-4 text-purple-400"/>:<Send className="w-4 h-4 text-blue-400"/>}
        <span className="text-gray-400 text-xs">Fee: {type==='veil'?'1.0':'0.1'} LAC</span>
      </div>
      <div><label className="text-gray-500 text-xs mb-1 block">To</label><Input value={to} onChange={setTo} placeholder="@username or lac1…" mono /></div>
      <div><label className="text-gray-500 text-xs mb-1 block">Amount</label><Input value={amt} onChange={setAmt} type="number" placeholder="0" />
        <p className="text-gray-700 text-[11px] mt-1">Available: {fmt(profile?.balance)} LAC</p></div>
      <Btn onClick={go} color={type==='veil'?'purple':'emerald'} full loading={ld} disabled={!to.trim()||!amt}>Send {amt||'0'} LAC</Btn>
    </div></div>);
};

// ━━━ STASH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const STASHView = ({ onBack, onDone }) => {
  const [tab, setTab] = useState('dep'); const [nom, setNom] = useState(null); const [key, setKey] = useState('');
  const [res, setRes] = useState(null); const [ld, setLd] = useState(false); const [info, setInfo] = useState(null);
  const [savedKeys, setSavedKeys] = useState(() => {
    try { return JSON.parse(localStorage.getItem('lac_stash_keys')||'[]'); } catch { return []; }
  });
  useEffect(() => { get('/api/stash/info').then(setInfo).catch(()=>{}); }, []);
  const noms = [{c:0,a:100},{c:1,a:1000},{c:2,a:10000},{c:3,a:100000}];

  const saveKey = (k, amount) => {
    const entry = { key: k, amount, created: Date.now(), used: false };
    const updated = [...savedKeys, entry];
    setSavedKeys(updated);
    localStorage.setItem('lac_stash_keys', JSON.stringify(updated));
  };
  const delKey = (idx) => {
    const updated = savedKeys.filter((_, i) => i !== idx);
    setSavedKeys(updated);
    localStorage.setItem('lac_stash_keys', JSON.stringify(updated));
    toast.success('Key deleted');
  };
  const markUsed = (keyStr) => {
    const updated = savedKeys.map(s => s.key === keyStr ? {...s, used: true} : s);
    setSavedKeys(updated);
    localStorage.setItem('lac_stash_keys', JSON.stringify(updated));
  };

  const dep = async () => {
    setLd(true);
    try {
      const r = await post('/api/stash/deposit',{nominal_code:nom});
      cp(r.stash_key); // auto-copy
      saveKey(r.stash_key, r.amount);
      setRes({t:'dep', key:r.stash_key, a:r.amount});
      toast.success(`✅ ${fmt(r.amount)} LAC deposited! Key copied & saved.`);
    } catch(e) { toast.error(e.message); }
    finally { setLd(false); }
  };
  const wdr = async () => {
    setLd(true);
    try {
      const r = await post('/api/stash/withdraw',{stash_key:key.trim()});
      markUsed(key.trim());
      toast.success(`💰 +${fmt(r.amount)} LAC withdrawn!`);
      setRes({t:'wdr', a:r.amount});
      setKey('');
    } catch(e) { toast.error(e.message); }
    finally { setLd(false); }
  };

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="🎒 STASH Pool" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      <Card gradient="bg-gradient-to-br from-amber-900/20 to-[#0f1f18] border-amber-800/20" className="mb-4">
        <p className="text-amber-400 font-semibold text-sm">Anonymous Money Safe</p>
        <p className="text-gray-500 text-[11px] mt-1">Deposit → secret key → withdraw to ANY wallet. Zero link.</p>
        {info && <div className="mt-2 grid grid-cols-3 gap-2">
          <div><p className="text-amber-300 text-xs font-bold">{fmt(info.total_balance||0)}</p><p className="text-gray-600 text-[9px]">Pool LAC</p></div>
          <div><p className="text-emerald-400 text-xs font-bold">{info.active_keys||0}</p><p className="text-gray-600 text-[9px]">Active keys</p></div>
          <div><p className="text-gray-400 text-xs font-bold">{info.spent_count||0}</p><p className="text-gray-600 text-[9px]">Redeemed</p></div>
        </div>}
      </Card>

      {/* Result feedback */}
      {res?.t==='dep' && res.key && (
        <Card gradient="bg-emerald-900/15 border-emerald-700/30" className="mb-3">
          <p className="text-emerald-400 text-sm font-bold">✅ Deposit successful! Key auto-copied & saved.</p>
          <p className="text-emerald-300 font-mono text-[10px] break-all select-all bg-[#060f0c] p-2 rounded-lg mt-2">{res.key}</p>
          <div className="flex gap-2 mt-2">
            <button onClick={() => cp(res.key)} className="text-emerald-400 text-xs flex items-center gap-1 bg-emerald-900/20 px-2 py-1 rounded-lg"><Copy className="w-3 h-3"/> Copy again</button>
          </div>
          <p className="text-gray-600 text-[10px] mt-2">⚠️ Anyone with this key can withdraw. Keep it safe!</p>
        </Card>
      )}
      {res?.t==='wdr' && (
        <Card gradient="bg-emerald-900/15 border-emerald-700/30" className="mb-3">
          <p className="text-emerald-400 text-sm font-bold">💰 +{fmt(res.a)} LAC withdrawn to your wallet!</p>
        </Card>
      )}

      <TabBar tabs={[['dep','💎 Deposit'],['wdr','💰 Withdraw'],['keys','🔑 Saved']]} active={tab} onChange={v => { setTab(v); setRes(null); }} />
      <div className="mt-3">
        {tab==='dep' ? (
          <div className="space-y-2">
            {noms.map(n => (
              <button key={n.c} onClick={() => setNom(n.c)} className={`w-full p-3 rounded-xl border text-left ${nom===n.c?'border-amber-500 bg-amber-600/10':'border-gray-800 bg-[#0a1a15]'}`}>
                <span className="text-white font-semibold text-sm">{fmt(n.a)} LAC</span>
                <span className="text-gray-600 text-[11px] ml-2">(fee: 2 LAC)</span>
              </button>))}
            <Btn onClick={dep} color="amber" full loading={ld} disabled={nom===null}>Deposit to STASH</Btn>
          </div>
        ) : tab==='wdr' ? (
          <div className="space-y-3">
            <textarea value={key} onChange={e => setKey(e.target.value)} rows={3} placeholder="Paste STASH key…"
              className="w-full bg-[#0a1a15] text-emerald-400 font-mono text-[11px] p-3 rounded-xl border border-emerald-900/30 outline-none resize-none" />
            <Btn onClick={wdr} color="emerald" full loading={ld} disabled={!key.trim()}>Withdraw</Btn>
          </div>
        ) : (
          <div className="space-y-2">
            {savedKeys.length === 0 ? <Empty emoji="🔑" text="No saved keys" sub="Deposit to get your first STASH key" /> :
            savedKeys.map((s, i) => (
              <Card key={i} gradient={s.used ? 'bg-gray-800/20 border-gray-700/20' : 'bg-amber-900/10 border-amber-800/20'}>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className={`font-mono text-[10px] break-all ${s.used ? 'text-gray-600 line-through' : 'text-amber-300'}`}>{s.key}</p>
                    <p className="text-gray-600 text-[10px] mt-1">{fmt(s.amount)} LAC · {s.used ? '✅ Used' : '⏳ Active'}</p>
                  </div>
                  <div className="flex gap-1 ml-2 shrink-0">
                    {!s.used && <button onClick={() => { cp(s.key); toast.success('Copied!'); }} className="p-1.5 bg-amber-900/20 rounded-lg"><Copy className="w-3 h-3 text-amber-400" /></button>}
                    <button onClick={() => { if(confirm('Delete this key?')) delKey(i); }} className="p-1.5 bg-red-900/20 rounded-lg"><Trash2 className="w-3 h-3 text-red-400" /></button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div></div>);
};

// ━━━ TIMELOCK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const TimelockView = ({ onBack, profile, onDone }) => {
  const [to, setTo] = useState(''); const [amt, setAmt] = useState(''); const [delay, setDelay] = useState(''); const [ld, setLd] = useState(false); const [pending, setPending] = useState([]);
  useEffect(() => { get('/api/timelock/pending').then(d => setPending(d.pending||d.locks||[])).catch(()=>{}); }, []);

  const estTime = (blocks) => {
    if (!blocks || blocks <= 0) return '';
    const s = blocks * 10;
    if (s < 60) return `~${s}s`;
    if (s < 3600) return `~${Math.floor(s/60)}m`;
    const h = Math.floor(s/3600);
    return `~${h}h ${Math.floor((s%3600)/60)}m`;
  };

  const go = async () => {
    setLd(true);
    try {
      const r = await post('/api/timelock/create',{to:to.trim(),amount:parseFloat(amt),delay_blocks:parseInt(delay)});
      toast.success(`TimeLock: ${r.estimated_time}`);
      onDone();
    } catch(e){ toast.error(e.message); }
    finally { setLd(false); }
  };

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="⏰ Time-Lock" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <Card><p className="text-gray-400 text-xs">Send LAC in the future. Funds locked until X blocks pass (~10s/block).</p></Card>
      <div><label className="text-gray-500 text-xs mb-1 block">Recipient</label><Input value={to} onChange={setTo} placeholder="@user or lac1…" mono /></div>
      <div><label className="text-gray-500 text-xs mb-1 block">Amount (LAC)</label><Input value={amt} onChange={setAmt} type="number" placeholder="0" /></div>
      <div>
        <label className="text-gray-500 text-xs mb-1 block">Send in (blocks) {delay && <span className="text-emerald-400">{estTime(parseInt(delay))}</span>}</label>
        <Input value={delay} onChange={setDelay} type="number" placeholder="e.g. 60 = ~10min" />
        <div className="flex gap-2 mt-2">
          {[['10min',60],['1hr',360],['6hr',2160],['24hr',8640]].map(([label,b]) =>
            <button key={b} onClick={() => setDelay(String(b))} className="px-3 py-1.5 bg-emerald-900/20 text-emerald-400 text-[10px] rounded-lg border border-emerald-800/20 active:bg-emerald-800/30">{label}</button>
          )}
        </div>
      </div>
      <Btn onClick={go} color="emerald" full loading={ld} disabled={!to||!amt||!delay}>Create TimeLock</Btn>
      {pending.length > 0 && (<div>
        <p className="text-gray-500 text-xs font-medium mt-4 mb-2">Pending Locks</p>
        {pending.map((l,i) => <Card key={i} className="mb-2"><p className="text-white text-sm">{fmt(l.amount)} LAC → {sAddr(l.to)}</p><p className="text-gray-600 text-[11px]">Block #{l.unlock_block} · {l.blocks_remaining||'?'} blocks left</p></Card>)}
      </div>)}
    </div></div>);
};

// ━━━ DEAD MAN'S SWITCH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const DeadManSwitchView = ({ onBack, profile, onDone }) => {
  const [status, setStatus] = useState(null);
  const [days, setDays] = useState('30');
  const [actions, setActions] = useState([{ type: 'transfer_all', to: '' }]);
  const [ld, setLd] = useState(false);
  const [showSetup, setShowSetup] = useState(false);

  useEffect(() => { get('/api/dms/status').then(setStatus).catch(()=>{}); }, []);

  const addAction = (type) => {
    if (actions.length >= 5) return;
    const a = { type };
    if (type === 'transfer_all' || type === 'transfer') a.to = '';
    if (type === 'transfer') a.amount = '';
    if (type === 'message') { a.to = ''; a.text = ''; }
    setActions([...actions, a]);
  };

  const updateAction = (i, field, val) => {
    const u = [...actions]; u[i][field] = val; setActions(u);
  };

  const removeAction = (i) => setActions(actions.filter((_,j) => j !== i));

  const save = async () => {
    setLd(true);
    try {
      await post('/api/dms/setup', { timeout_days: parseInt(days), actions });
      toast.success(`💀 DMS armed: ${days} days`);
      get('/api/dms/status').then(setStatus);
      setShowSetup(false);
    } catch(e) { toast.error(e.message); }
    finally { setLd(false); }
  };

  const cancel = async () => {
    try { await post('/api/dms/cancel'); toast.success('DMS disabled'); get('/api/dms/status').then(setStatus); }
    catch(e) { toast.error(e.message); }
  };

  const actionLabels = { transfer_all: '💸 Transfer All', transfer: '💰 Transfer Amount', message: '✉️ Send Message', burn_stash: '🔥 Burn STASH Keys', wipe: '💀 Wipe Wallet' };

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="💀 Dead Man's Switch" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <Card gradient="bg-gradient-to-br from-red-900/20 to-[#0f1f18] border-red-800/20">
        <p className="text-red-400 font-semibold text-sm">Dead Man's Switch</p>
        <p className="text-gray-500 text-[11px] mt-1">If you don't log in for X days, automatic actions trigger: transfer funds, send messages, or wipe your wallet.</p>
      </Card>

      {status?.enabled ? (
        <Card>
          <div className="flex justify-between items-center">
            <div>
              <p className="text-emerald-400 text-sm font-medium">✅ DMS Active</p>
              <p className="text-gray-500 text-[11px] mt-1">Timeout: {status.timeout_days} days</p>
              <p className="text-gray-500 text-[11px]">Days remaining: <span className="text-amber-400">{status.days_remaining}</span></p>
              <p className="text-gray-600 text-[10px] mt-1">{status.actions?.length||0} actions configured</p>
            </div>
            <Btn onClick={cancel} color="gray" small>Disable</Btn>
          </div>
          {status.actions?.map((a,i) => <p key={i} className="text-gray-500 text-[10px] mt-1">→ {actionLabels[a.type]||a.type} {a.to ? `to ${a.to}` : ''}</p>)}
        </Card>
      ) : status?.triggered_at ? (
        <Card><p className="text-red-400 text-sm">💀 DMS was triggered</p><p className="text-gray-600 text-[10px]">Actions were executed. Set up a new one if needed.</p></Card>
      ) : (
        <Card><p className="text-gray-500 text-sm">No DMS configured</p></Card>
      )}

      {!showSetup && !status?.enabled && <Btn onClick={() => setShowSetup(true)} color="red" full>Configure Dead Man's Switch</Btn>}

      {showSetup && (<>
        <div>
          <label className="text-gray-500 text-xs mb-1 block">Trigger after (days without login)</label>
          <Input value={days} onChange={setDays} type="number" placeholder="30" />
          <div className="flex gap-2 mt-2">
            {[7,14,30,90,180].map(d => <button key={d} onClick={() => setDays(String(d))} className={`px-3 py-1.5 text-[10px] rounded-lg border ${days===String(d)?'bg-red-900/20 text-red-400 border-red-800/30':'bg-gray-800/50 text-gray-600 border-gray-700/30'}`}>{d}d</button>)}
          </div>
        </div>

        <p className="text-gray-500 text-xs font-medium">Actions (executed in order):</p>
        {actions.map((a, i) => (
          <Card key={i} className="relative">
            <button onClick={() => removeAction(i)} className="absolute top-2 right-2 text-gray-600 text-xs">✕</button>
            <p className="text-red-400 text-[11px] font-medium mb-2">{actionLabels[a.type]}</p>
            {(a.type === 'transfer_all' || a.type === 'transfer' || a.type === 'message') && (
              <Input value={a.to||''} onChange={v => updateAction(i,'to',v)} placeholder="@recipient or lac1..." mono />
            )}
            {a.type === 'transfer' && <Input value={a.amount||''} onChange={v => updateAction(i,'amount',v)} type="number" placeholder="Amount LAC" />}
            {a.type === 'message' && <Input value={a.text||''} onChange={v => updateAction(i,'text',v)} placeholder="Message text..." />}
          </Card>
        ))}

        <div className="flex flex-wrap gap-2">
          {Object.entries(actionLabels).map(([type, label]) =>
            <button key={type} onClick={() => addAction(type)} className="px-2.5 py-1.5 bg-gray-800 text-gray-400 text-[10px] rounded-lg border border-gray-700/30 active:bg-gray-700">+ {label}</button>
          )}
        </div>

        <Btn onClick={save} color="red" full loading={ld} disabled={!days || actions.length === 0}>Arm Dead Man's Switch</Btn>
      </>)}
    </div></div>);
};

// ━━━ MINING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const MiningView = ({ onBack, profile }) => {
  const [d, setD] = useState(null);
  useEffect(() => { get('/api/wallet/mining?limit=50').then(setD).catch(()=>{}); }, []);
  const p = profile||{};
  const rewards = d?.mining_rewards || [];
  const earned = d?.total_mined || 0;
  const mined = d?.count || 0;

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="⛏️ Mining" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      <Card gradient="bg-gradient-to-br from-emerald-800/30 to-[#0f1f18] border-emerald-700/30" className="mb-4 text-center">
        <div className="text-4xl mb-2">⛏️</div>
        <p className="text-emerald-400 font-bold text-lg">{mined > 0 ? 'Mining Active' : 'Mining Waiting'}</p>
        <p className="text-gray-500 text-xs">PoET Consensus · Weighted Lottery</p>
      </Card>
      <div className="grid grid-cols-2 gap-2 mb-4">
        <StatBox label="Your Level" value={`L${p.level??0}`} />
        <StatBox label="Mining Chance" value={`${[15,20,25,30,35,40,45][p.level??0]||15}%`} color="text-emerald-400" />
        <StatBox label="Blocks Mined" value={mined} />
        <StatBox label="Total Earned" value={earned > 0 ? fmt(earned)+' LAC' : '0'} color="text-emerald-400" />
      </div>
      <Card><p className="text-white text-sm font-semibold mb-2">Mining Info</p>
        {[['Block Reward','190 LAC'],['Winners/Block','19'],['Min Balance','50 LAC'],['Your Balance',fmt(p.balance)+' LAC']].map(([k,v]) => (
          <div key={k} className="flex justify-between py-1.5 border-b border-gray-800/20"><span className="text-gray-500 text-xs">{k}</span><span className="text-white text-xs font-medium">{v}</span></div>
        ))}
      </Card>
      {rewards.length > 0 && (<div className="mt-4">
        <p className="text-gray-500 text-xs font-medium mb-2">Recent Rewards</p>
        {rewards.slice(0,10).map((r,i) => <Card key={i} className="mb-1.5"><div className="flex justify-between"><span className="text-emerald-400 text-sm font-semibold">+{fmt(r.reward||r.amount)} LAC</span><span className="text-gray-600 text-[11px]">Block #{r.block}</span></div></Card>)}
      </div>)}
    </div></div>);
};

// ━━━ TRANSACTIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const TxsView = ({ onBack }) => {
  const [txs, setTxs] = useState([]); const [ld, setLd] = useState(true); const [f, setF] = useState('all');
  useEffect(() => {
    get('/api/wallet/transactions').then(d => { const t=d.transactions||{};
      setTxs([...(t.sent||[]).map(x=>({...x,dir:'sent'})),...(t.received||[]).map(x=>({...x,dir:'received'})),...(t.mining||[]).map(x=>({...x,dir:'mined'})),...(t.burned||[]).map(x=>({...x,dir:'burned'}))].sort((a,b)=>(b.timestamp||0)-(a.timestamp||0)));
    }).catch(()=>{}).finally(()=>setLd(false));
  }, []);
  const show = f==='all'?txs:txs.filter(t=>t.dir===f);
  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="📜 Transactions" onBack={onBack} right={<span className="text-gray-600 text-xs">{show.length}</span>} />
    <div className="flex gap-1 px-4 py-2">
      {[['all','All'],['received','In'],['sent','Out'],['mined','Mined'],['burned','Burn']].map(([id,l]) => (
        <button key={id} onClick={() => setF(id)} className={`px-3 py-1 rounded-lg text-[11px] font-semibold ${f===id?'bg-emerald-600 text-white':'bg-gray-800 text-gray-500'}`}>{l}</button>
      ))}
    </div>
    <div className="flex-1 overflow-y-auto px-4">
      {ld?<p className="text-gray-600 py-8 text-center text-sm">Loading…</p>:show.length===0?<Empty emoji="📜" text="No transactions"/>:show.map((tx,i) => <TxRow key={i} tx={tx} />)}
    </div></div>);
};

// ━━━ DICE GAME ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const DiceView = ({ onBack, profile, onRefresh }) => {
  const [mode, setMode] = useState('color'); // 'color' or 'number'
  const [bet, setBet] = useState('10');
  const [playing, setPlaying] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);

  const loadHistory = async () => {
    try { const r = await get('/api/dice/history'); setHistory(r.history||[]); setStats(r.stats||null); } catch {}
  };
  useEffect(() => { loadHistory(); }, []);

  const play = async (choice) => {
    if (playing) return;
    const amount = parseFloat(bet) || 0;
    if (amount < 1) { toast.error('Min bet: 1 LAC'); return; }
    if (amount > (profile?.balance||0)) { toast.error('Not enough LAC'); return; }
    setPlaying(true); setResult(null);
    try {
      const r = await post('/api/dice/play', { type: mode, choice, amount });
      setResult(r);
      if (r.won) toast.success(`🎉 Won +${fmt(r.payout)} LAC!`);
      else toast(`💀 Lost ${fmt(r.bet)} LAC`, {icon:'🎲'});
      onRefresh();
      loadHistory();
    } catch(e) { toast.error(e.message); }
    finally { setPlaying(false); }
  };

  const p = profile || {};

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="🎲 Dice" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      {/* Balance */}
      <div className="text-center mb-4">
        <p className="text-gray-500 text-xs">Your Balance</p>
        <p className="text-2xl font-bold text-white">{fmt(p.balance)} <span className="text-sm text-gray-500">LAC</span></p>
      </div>

      {/* Mode toggle */}
      <TabBar tabs={[['color','🔴 Red/Black'],['number','🔢 Over/Under']]} active={mode} onChange={setMode} />

      {/* Bet amount */}
      <div className="mt-4">
        <p className="text-gray-500 text-xs mb-2">Bet Amount</p>
        <div className="flex gap-2">
          <input type="number" value={bet} onChange={e => setBet(e.target.value)}
            className="flex-1 bg-[#0a1a15] text-white text-center font-bold text-lg px-4 py-3 rounded-xl border border-emerald-900/30 outline-none" />
          <div className="flex flex-col gap-1">
            {[10,50,100].map(v => (
              <button key={v} onClick={() => setBet(String(v))} className="px-3 py-1 bg-gray-800 text-gray-400 text-[11px] rounded-lg active:bg-gray-700">{v}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Game buttons */}
      <div className="mt-4">
        {mode === 'color' ? (
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => play('red')} disabled={playing}
              className="py-4 rounded-2xl bg-gradient-to-b from-red-500 to-red-700 text-white font-bold text-lg shadow-lg shadow-red-900/30 active:scale-95 transition disabled:opacity-50">
              🔴 RED
            </button>
            <button onClick={() => play('black')} disabled={playing}
              className="py-4 rounded-2xl bg-gradient-to-b from-gray-700 to-gray-900 text-white font-bold text-lg shadow-lg shadow-gray-900/30 active:scale-95 transition disabled:opacity-50 border border-gray-600">
              ⚫ BLACK
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => play('over')} disabled={playing}
              className="py-4 rounded-2xl bg-gradient-to-b from-emerald-500 to-emerald-700 text-white font-bold text-lg shadow-lg shadow-emerald-900/30 active:scale-95 transition disabled:opacity-50">
              ⬆️ OVER 50
            </button>
            <button onClick={() => play('under')} disabled={playing}
              className="py-4 rounded-2xl bg-gradient-to-b from-amber-500 to-amber-700 text-white font-bold text-lg shadow-lg shadow-amber-900/30 active:scale-95 transition disabled:opacity-50">
              ⬇️ UNDER 50
            </button>
          </div>
        )}
      </div>

      {/* Spinning animation */}
      {playing && <div className="text-center py-6"><p className="text-3xl animate-bounce">🎲</p><p className="text-gray-500 text-xs mt-2">Rolling…</p></div>}

      {/* Result */}
      {result && !playing && (
        <Card gradient={result.won?'bg-gradient-to-br from-emerald-900/30 to-[#0f1f18] border-emerald-500/30':'bg-gradient-to-br from-red-900/20 to-[#0f1f18] border-red-700/30'} className="mt-4 text-center">
          <p className="text-3xl mb-1">{result.won ? '🎉' : '💀'}</p>
          <p className={`text-xl font-bold ${result.won?'text-emerald-400':'text-red-400'}`}>
            {result.won ? `Won +${fmt(result.payout)} LAC` : `Lost ${fmt(result.bet)} LAC`}
          </p>
          <p className="text-gray-500 text-sm mt-1">
            Roll: <span className="text-white font-mono">{result.roll}</span> → <span className={`font-bold ${result.result==='RED'?'text-red-400':result.result==='BLACK'?'text-gray-300':'text-emerald-400'}`}>{result.result}</span>
          </p>
          <p className="text-gray-700 text-[10px] mt-1 font-mono">proof: {result.proof_hash}</p>
        </Card>
      )}

      {/* Stats */}
      {stats && stats.total_games > 0 && (
        <div className="grid grid-cols-3 gap-2 mt-4">
          <StatBox label="Games" value={stats.total_games} small />
          <StatBox label="Win Rate" value={stats.total_games>0 ? Math.round(stats.wins/stats.total_games*100)+'%' : '—'} color={stats.wins>stats.losses?'text-emerald-400':'text-red-400'} small />
          <StatBox label="Profit" value={`${stats.profit>=0?'+':''}${fmt(stats.profit)}`} color={stats.profit>=0?'text-emerald-400':'text-red-400'} small />
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="mt-4">
          <p className="text-gray-500 text-xs font-medium mb-2">Recent Games</p>
          {history.slice(0,8).map((g,i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-800/20">
              <div className="flex items-center gap-2">
                <span className="text-sm">{g.won ? '🟢' : '🔴'}</span>
                <span className="text-gray-400 text-xs">{g.choice?.toUpperCase()} → {g.result}</span>
              </div>
              <span className={`text-xs font-medium ${g.won?'text-emerald-400':'text-red-400'}`}>
                {g.won ? `+${fmt(g.payout)}` : `-${fmt(g.amount)}`}
              </span>
            </div>
          ))}
        </div>
      )}

      <Card className="mt-4" gradient="bg-gray-800/20 border-gray-700/30">
        <p className="text-gray-600 text-[10px] leading-relaxed">
          🎲 Provably fair — results from SHA256(block_hash + address + time). 
          Red/Black: 49% each, 2% green (house edge). Over/Under: 50/50.
          Min bet: 1 LAC, Max: 10,000 LAC.
        </p>
      </Card>
    </div>
  </div>);
};

// ━━━ VALIDATOR ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ValidatorView = ({ onBack, profile, onRefresh }) => {
  const [status, setStatus] = useState(null);
  const [validators, setValidators] = useState([]);
  const [ld, setLd] = useState(false);

  const load = async () => {
    try { setStatus(await get('/api/validator/status')); } catch {}
    try { const r = await get('/api/validator/list'); setValidators(r.validators||[]); } catch {}
  };
  useEffect(() => { load(); }, []);

  const toggle = async () => {
    setLd(true);
    try {
      const r = await post('/api/validator/register', { enable: !status?.validator_mode });
      toast.success(r.validator_mode ? '🛡️ Validator ON' : 'Validator OFF');
      await load();
      onRefresh();
    } catch(e) { toast.error(e.message); }
    finally { setLd(false); }
  };

  const p = profile || {};
  const s = status || {};
  const eligible = s.eligible || p.level >= 5;
  const active = s.validator_mode;

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="🛡️ Validator" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      {/* Status Card */}
      <Card gradient={active ? 'bg-gradient-to-br from-purple-900/40 to-[#0f1f18] border-purple-700/30' : 'bg-gradient-to-br from-[#0a2a1f] to-[#0f1f18] border-emerald-800/30'} className="mb-4 text-center">
        <div className="text-4xl mb-2">{active ? '🛡️' : '🔒'}</div>
        <p className={`font-bold text-lg ${active?'text-purple-400':'text-gray-400'}`}>
          {active ? 'Validator Active' : eligible ? 'Validator Ready' : 'Not Eligible'}
        </p>
        <p className="text-gray-600 text-xs mt-1">
          {eligible ? 'Zero-History block validation' : `Need Level 5+ (current: L${p.level??0})`}
        </p>
        {eligible && (
          <div className="mt-4">
            <Btn onClick={toggle} color={active?'red':'purple'} loading={ld}>
              {active ? 'Disable Validator' : 'Enable Validator'}
            </Btn>
          </div>
        )}
      </Card>

      {/* Stats */}
      {eligible && (
        <div className="grid grid-cols-2 gap-2 mb-4">
          <StatBox label="Your Level" value={`L${s.level??p.level??0}`} />
          <StatBox label="Weight" value={s.weight||'—'} color="text-purple-400" />
          <StatBox label="Daily Earning" value={s.estimated_daily_earning?fmt(s.estimated_daily_earning)+' LAC':'—'} color="text-emerald-400" />
          <StatBox label="Yearly Earning" value={s.estimated_yearly_earning?fmt(s.estimated_yearly_earning)+' LAC':'—'} color="text-emerald-400" />
        </div>
      )}

      {/* Info */}
      <Card><p className="text-white text-sm font-semibold mb-2">Validator Info</p>
        {[
          ['Required Level', 'L5+'],
          ['L5 Reward', '0.5 LAC/commitment'],
          ['L6 Reward', '1.0 LAC/commitment'],
          ['Min Validators', s.min_validators||3],
          ['Commitment Interval', `${s.commitment_interval||30}s`],
          ['Your Balance', fmt(p.balance)+' LAC'],
        ].map(([k,v]) => (
          <div key={k} className="flex justify-between py-1.5 border-b border-gray-800/20">
            <span className="text-gray-500 text-xs">{k}</span>
            <span className="text-white text-xs font-medium">{v}</span>
          </div>
        ))}
      </Card>

      {/* Active Validators */}
      {validators.length > 0 && (
        <div className="mt-4">
          <p className="text-gray-500 text-xs font-medium mb-2">Active Validators ({validators.length})</p>
          {validators.map((v,i) => (
            <Card key={i} className="mb-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge color="purple">L{v.level}</Badge>
                  <span className="text-gray-400 text-xs font-mono">{v.address}</span>
                </div>
                <span className="text-gray-600 text-[11px]">w:{v.weight}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Requirements if not eligible */}
      {!eligible && (
        <Card className="mt-4" gradient="bg-amber-900/10 border-amber-700/20">
          <p className="text-amber-400 text-sm font-semibold mb-2">How to become a Validator</p>
          <div className="space-y-2 text-xs text-gray-400">
            <p>1. Reach Level 5 (burn 100,000 LAC total)</p>
            <p>2. Maintain minimum balance</p>
            <p>3. Enable Validator mode</p>
            <p>4. Earn rewards for validating Zero-History blocks</p>
          </div>
        </Card>
      )}
    </div>
  </div>);
};

// ━━━ USERNAME ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const UsernameView = ({ onBack, onDone }) => {
  const [name, setName] = useState(''); const [avail, setAvail] = useState(null); const [ld, setLd] = useState(false);
  const cost = !name||name.length<3?0:name.length===3?1000:name.length===4?100:10;
  const chk = async () => { try { const r=await post('/api/username/check',{username:name.toLowerCase()}); setAvail(r.available); toast(r.available?'Available!':'Taken',{icon:r.available?'✅':'❌'}); } catch(e){ toast.error(e.message); } };
  const reg = async () => { setLd(true); try { await post('/api/username/register',{username:name.toLowerCase()}); toast.success(`@${name} registered!`); onDone(); } catch(e){ toast.error(e.message); } finally { setLd(false); } };

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="👤 Username" onBack={onBack} />
    <div className="p-4 space-y-4">
      <Card><p className="text-gray-400 text-xs">Register a @username so people can find you. Shorter = more expensive.</p></Card>
      <div className="flex gap-2">
        <div className="flex-1 flex items-center bg-[#0a1a15] border border-emerald-900/30 rounded-xl overflow-hidden">
          <span className="text-gray-600 pl-3">@</span>
          <input value={name} onChange={e => { setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g,'')); setAvail(null); }}
            className="flex-1 bg-transparent text-white px-2 py-3 outline-none text-sm" placeholder="name" maxLength={20} />
        </div>
        <Btn onClick={chk} color="gray" disabled={name.length<3} small>Check</Btn>
      </div>
      <div className="flex justify-between text-[11px]"><span className="text-gray-600">3-20 chars · a-z 0-9 _</span><span className="text-amber-400">{cost>0?cost+' LAC':'—'}</span></div>
      {avail===true && <Btn onClick={reg} color="emerald" full loading={ld}>Register @{name} ({cost} LAC)</Btn>}
      {avail===false && <p className="text-red-400 text-sm text-center">Already taken</p>}

      <Card className="mt-4"><p className="text-white text-sm font-semibold mb-2">💰 Pricing</p>
        {[['3 chars','1,000 LAC'],['4 chars','100 LAC'],['5+ chars','10 LAC']].map(([k,v]) => (
          <div key={k} className="flex justify-between py-1.5 border-b border-gray-800/20"><span className="text-gray-500 text-xs">{k}</span><span className="text-amber-400 text-xs font-medium">{v}</span></div>
        ))}
      </Card>
    </div></div>);
};

// ━━━ CONTACTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ContactsView = ({ onBack, onChat }) => {
  const [contacts, setContacts] = useState([]); const [addr, setAddr] = useState('');
  useEffect(() => { get('/api/contacts').then(d => setContacts(d.contacts||[])).catch(()=>{}); }, []);
  const add = async () => { if(!addr.trim()) return; try { await post('/api/contact/add',{address:addr.trim()}); toast.success('Added!'); setAddr(''); setContacts((await get('/api/contacts')).contacts||[]); } catch(e){ toast.error(e.message); } };

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="👥 Contacts" onBack={onBack} />
    <div className="p-4">
      <div className="flex gap-2 mb-4"><Input value={addr} onChange={setAddr} placeholder="Add address or @user" mono /><Btn onClick={add} color="emerald" small><UserPlus className="w-4 h-4"/></Btn></div>
      {contacts.length===0?<Empty emoji="👥" text="No contacts yet"/>:contacts.map((c,i) => (
        <ListItem key={i} icon={<User className="w-5 h-5 text-emerald-500"/>} title={c.username||sAddr(c.address)} sub={c.address?sAddr(c.address):''}
          onClick={() => onChat({address:c.address,name:c.username||c.address})} />
      ))}
    </div></div>);
};

// ━━━ DASHBOARD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const DashboardView = ({ onBack }) => {
  const [s, setS] = useState(null);
  useEffect(() => { get('/api/stats').then(setS).catch(()=>{}); }, []);
  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="📊 Dashboard" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      {!s?<p className="text-gray-600 text-center py-8">Loading…</p>:<>
        <div className="grid grid-cols-2 gap-2 mb-4">
          <StatBox icon="⛓" label="Total Blocks" value={fmt(s.total_blocks)} />
          <StatBox icon="👛" label="Wallets" value={fmt(s.total_wallets)} />
          <StatBox icon="💰" label="Total Supply" value={fmt(s.total_supply)} />
          <StatBox icon="🎒" label="STASH Pool" value={fmt(s.stash_pool_balance)} color="text-amber-400" />
        </div>
        <Card className="mb-3"><p className="text-white text-sm font-semibold mb-2">Recent (100 blocks)</p>
          <div className="grid grid-cols-3 gap-2">
            <StatBox label="Transactions" value={s.recent_tx_count||0} small />
            <StatBox label="VEIL" value={s.recent_veil||0} color="text-purple-400" small />
            <StatBox label="Normal" value={s.recent_normal||0} small />
          </div>
        </Card>
        {s.top_balances && <Card><p className="text-white text-sm font-semibold mb-2">🏆 Top Balances</p>
          {s.top_balances.slice(0,5).map((b,i) => <div key={i} className="flex justify-between py-1 border-b border-gray-800/20"><span className="text-gray-500 text-xs">#{i+1}</span><span className="text-emerald-400 text-xs">{fmt(b)} LAC</span></div>)}
        </Card>}
        {s.level_distribution && <Card className="mt-3"><p className="text-white text-sm font-semibold mb-2">📊 Level Distribution</p>
          {Object.entries(s.level_distribution).sort().map(([k,v]) => <div key={k} className="flex justify-between py-1 border-b border-gray-800/20"><span className="text-gray-500 text-xs">{k}</span><span className="text-white text-xs">{v} wallets</span></div>)}
        </Card>}
      </>}
    </div></div>);
};

// ━━━ EXPLORER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const txMeta = (t) => {
  const m = {
    'normal':['💸','Transfer','emerald'], 'transfer':['💸','Transfer','emerald'],
    'veil_transfer':['👻','VEIL','purple'], 'ring_transfer':['🔐','Ring','purple'], 'stealth_transfer':['🔒','Stealth','purple'],
    'stash_deposit':['🎒','STASH In','amber'], 'stash_withdraw':['💰','STASH Out','amber'],
    'dice_burn':['🎲','Dice Burn','yellow'], 'dice_mint':['🎲','Dice Win','yellow'],
    'dms_transfer':['💀','DMS Transfer','red'], 'dms_transfer_all':['💀','DMS Transfer','red'],
    'dms_message':['💀','DMS Msg','red'], 'dms_wipe':['💀','DMS Wipe','red'], 'dms_burn_stash':['💀','DMS Burn','red'],
    'timelock_create':['⏰','TimeLock','blue'], 'timelock_release':['⏰','Unlock','blue'],
    'burn_level_upgrade':['⬆️','Level Up','red'], 'burn_nickname_change':['✏️','Nickname','red'],
    'username_register':['👤','Username','emerald'], 'faucet':['🚰','Faucet','gray'],
    'mining_reward':['⛏️','Reward','emerald'], 'poet_reward':['⛏️','Reward','emerald'],
  };
  return m[t] || ['📄', t?.replace(/_/g,' ')||'Event', 'gray'];
};

const isAnon = (t) => ['veil_transfer','ring_transfer','stealth_transfer','stash_deposit','stash_withdraw','dice_burn','dice_mint','dms_transfer','dms_transfer_all','dms_message','dms_wipe','dms_burn_stash'].includes(t);

const ExplorerView = ({ onBack }) => {
  const [blocks, setBlocks] = useState([]); const [h, setH] = useState(0); const [sel, setSel] = useState(null);
  useEffect(() => {
    (async () => { try { const hd=await get('/api/chain/height'); setH(hd.height||0); const s=Math.max(0,(hd.height||0)-30); const bd=await get(`/api/blocks/range?start=${s}&end=${hd.height}`); setBlocks((bd.blocks||[]).reverse()); } catch {} })();
  }, []);

  if (sel) {
    const txs = (sel.transactions||[]).filter(t => t.type!=='mining_reward' && t.type!=='poet_reward');
    const msgs = (sel.ephemeral_msgs||[]).length;
    const reward = sel.total_reward || (sel.mining_rewards||[]).reduce((s,r)=>s+(r.reward||0),0);
    const miners = sel.mining_winners_count || (sel.mining_rewards||[]).length;
    return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title={`Block #${sel.index}`} onBack={() => setSel(null)} />
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <Card gradient="bg-gradient-to-br from-emerald-900/20 to-[#0f1f18] border-emerald-800/15">
          <p className="text-[10px] text-gray-600 font-mono break-all">{sel.hash||'—'}</p>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div><p className="text-[9px] text-gray-600 uppercase">Time</p><p className="text-white text-[11px]">{new Date(sel.timestamp*1000).toLocaleString()}</p></div>
            <div><p className="text-[9px] text-gray-600 uppercase">Miner</p><p className="text-purple-400 text-[11px]">🔒 PoET Anonymous</p></div>
          </div>
        </Card>
        {reward > 0 && <Card><div className="flex justify-between items-center"><span className="text-gray-400 text-xs">⛏️ {miners} miner{miners>1?'s':''}</span><span className="text-emerald-400 font-bold font-mono">{reward.toFixed(2)} LAC</span></div></Card>}
        <p className="text-gray-500 text-[11px] font-medium">📋 Transactions ({txs.length})</p>
        {txs.length === 0 ? <p className="text-gray-700 text-[11px] text-center py-4">No transactions</p> :
          txs.map((tx,i) => {
            const [ic, label, color] = txMeta(tx.type);
            const anon = isAnon(tx.type);
            return (<Card key={i}>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-white text-[12px] font-medium">{ic} {label}</span>
                <Badge color={color}>{tx.type?.includes('veil')||tx.type?.includes('ring')||tx.type?.includes('stealth')?'PRIVATE':tx.type?.includes('stash')?'STASH':tx.type?.includes('dms')?'DMS':tx.type?.includes('dice')?'DICE':tx.type?.includes('time')?'TIMER':'PUBLIC'}</Badge>
              </div>
              <div className="grid grid-cols-2 gap-1 text-[10px]">
                <div><span className="text-gray-600">From: </span><span className={anon?'text-purple-400 italic':'text-gray-400 font-mono'}>{anon?'🔒 Anonymous':sAddr(tx.from||'')}</span></div>
                <div><span className="text-gray-600">To: </span><span className={anon?'text-purple-400 italic':'text-gray-400 font-mono'}>{anon?'🔒 Anonymous':sAddr(tx.to||'')}</span></div>
                {tx.amount>0 && <div><span className="text-gray-600">Amount: </span><span className={anon?'text-purple-400 italic':'text-emerald-400 font-mono font-bold'}>{anon?'🔒 Hidden':fmt(tx.amount)+' LAC'}</span></div>}
                {tx.unlock_block && <div><span className="text-gray-600">Unlock: </span><span className="text-blue-400 font-mono">Block #{tx.unlock_block}</span></div>}
              </div>
            </Card>);
          })}
        {msgs > 0 && <>
          <p className="text-gray-500 text-[11px] font-medium">💬 L2 Ephemeral ({msgs})</p>
          <Card><p className="text-purple-400/70 text-[11px] text-center">🔒 {msgs} encrypted messages — auto-delete 5min</p></Card>
        </>}
      </div></div>);
  }

  return (<div className="h-full bg-[#060f0c] flex flex-col"><Header title="⛓ Explorer" onBack={onBack} right={<Badge>#{h}</Badge>} />
    <div className="flex-1 overflow-y-auto p-4">
      {blocks.length===0?<p className="text-gray-600 text-center py-8">Loading…</p>:
        blocks.map(b => {
          const txs = (b.transactions||[]).filter(t => t.type!=='mining_reward' && t.type!=='poet_reward');
          const msgs = (b.ephemeral_msgs||[]).length;
          return (<Card key={b.index} className="mb-2" onClick={() => setSel(b)}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-emerald-400 text-sm font-bold">#{b.index}</span>
              <span className="text-gray-600 text-[11px]">{ago(b.timestamp)}</span>
            </div>
            <div className="flex gap-3 text-[11px] mb-1">
              <span className="text-gray-500">{txs.length} tx</span>
              {msgs > 0 && <span className="text-purple-400/60">{msgs} msg</span>}
              <span className="text-gray-600">🔒 PoET</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {txs.slice(0,5).map((tx,i) => {
                const [ic, label, color] = txMeta(tx.type);
                return <Badge key={i} color={color}>{ic} {label}{!isAnon(tx.type) && tx.amount>0?` ${fmt(tx.amount)}`:''}</Badge>;
              })}
              {txs.length>5 && <Badge color="gray">+{txs.length-5}</Badge>}
            </div>
          </Card>);
        })}
    </div></div>);
};

// ━━━ EXPLORE TAB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ExploreTab = ({ onNav, onMenu }) => (
  <div className="h-full overflow-y-auto pb-4">
    <div className="px-4 pt-4 pb-2 flex items-center gap-3">
      <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
      <h1 className="text-xl font-bold text-white">Explore</h1>
    </div>
    <div className="px-4 space-y-2">
      {[
        {icon:'⛓',title:'Block Explorer',sub:'Browse blocks & transactions',type:'explorer'},
        {icon:'📊',title:'Network Dashboard',sub:'Stats, top balances, distribution',type:'dashboard'},
        {icon:'⛏️',title:'Mining',sub:'Your mining stats & rewards',type:'mining'},
        {icon:'⏰',title:'Time-Lock',sub:'Schedule future payments',type:'timelock'},
        {icon:'💀',title:'Dead Man\'s Switch',sub:'Auto-actions if you go inactive',type:'dms'},
        {icon:'👥',title:'Contacts',sub:'Your address book',type:'contacts'},
        {icon:'🛡️',title:'Validator',sub:'Zero-History validator node',type:'validator'},
        {icon:'🎲',title:'Dice',sub:'Provably fair blockchain game',type:'dice'},
      ].map(item => (
        <button key={item.type} onClick={() => onNav({type:item.type})}
          className="w-full bg-[#0f1f1a] border border-emerald-900/15 rounded-2xl p-4 flex items-center gap-4 active:bg-emerald-900/20">
          <span className="text-2xl">{item.icon}</span>
          <div className="text-left flex-1"><p className="text-white font-medium text-[14px]">{item.title}</p><p className="text-gray-600 text-xs">{item.sub}</p></div>
          <ChevronRight className="w-4 h-4 text-gray-700" />
        </button>
      ))}
    </div>
  </div>
);

// ━━━ PROFILE TAB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ProfileTab = ({ profile, onNav, onLogout, onRefresh, onMenu }) => {
  const p = profile||{};
  const [upg, setUpg] = useState(false);
  const uname = p.username && p.username!=='Anonymous' && p.username!=='None' ? p.username : null;

  const upgrade = async () => { setUpg(true); try { const r=await post('/api/upgrade_level'); toast.success(`Upgraded to L${r.new_level}!`); onRefresh(); } catch(e){ toast.error(e.message); } finally { setUpg(false); } };

  return (
    <div className="h-full overflow-y-auto pb-4">
      <div className="flex items-center gap-3 px-4 pt-4 pb-2">
        <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
        <h1 className="text-xl font-bold text-white">Profile</h1>
      </div>
      <div className="mx-4">
        <Card gradient="bg-gradient-to-br from-[#0a2a1f] to-[#0f1f18] border-emerald-800/30" className="text-center">
          <LevelBadge level={p.level??0} />
          <p className="text-white text-xl font-bold mt-3">{uname||'Anonymous'}</p>
          <p className="text-gray-600 text-[11px] font-mono mt-1">{sAddr(p.address)}</p>
          <div className="flex justify-center gap-4 mt-3">
            <div className="text-center"><p className="text-white font-bold">{fmt(p.balance)}</p><p className="text-gray-600 text-[10px]">LAC</p></div>
            <div className="text-center"><p className="text-white font-bold">{p.tx_count||0}</p><p className="text-gray-600 text-[10px]">TXs</p></div>
            <div className="text-center"><p className="text-white font-bold">{p.msg_count||0}</p><p className="text-gray-600 text-[10px]">Messages</p></div>
          </div>
        </Card>
      </div>

      <div className="mx-4 mt-4 space-y-0.5">
        {!uname && <ListItem icon={<User className="w-5 h-5 text-purple-400"/>} title="Register Username" sub="Get your @name" onClick={() => onNav({type:'username'})} />}
        <ListItem icon={<Award className="w-5 h-5 text-amber-400"/>} title="Upgrade Level" sub={`L${p.level??0} → L${(p.level??0)+1} · ${levelCosts[p.level??0]>0 ? fmt(levelCosts[p.level??0])+' LAC' : 'MAX'}`}
          onClick={upgrade} right={upg?<span className="text-xs text-gray-500">…</span>:undefined} />
        <ListItem icon={<Copy className="w-5 h-5 text-blue-400"/>} title="Copy Address" sub={sAddr(p.address)} onClick={() => cp(p.address)} />
        <ListItem icon={<Lock className="w-5 h-5 text-red-400"/>} title="Export Seed" sub="Backup your secret key" onClick={() => {
          const s=localStorage.getItem('lac_seed');
          if(s){ const show=confirm('⚠️ Your seed will be shown.\nMake sure nobody is watching!\n\nShow seed?');
            if(show){ cp(s); prompt('Your seed (copied to clipboard):', s); }
          } else { toast.error('No seed found'); }
        }} />
        <div className="h-px bg-gray-800/30 my-2" />
        <ListItem icon={<LogOut className="w-5 h-5 text-red-400"/>} title="Logout" sub="Save seed first!" onClick={() => { if(confirm('Make sure seed is saved!')) onLogout(); }} />
      </div>
      <p className="text-center text-gray-800 text-[10px] mt-6">LAC v8 · Zero-History Blockchain · PoET Consensus</p>
    </div>
  );
};
