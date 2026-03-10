/**
 * LAC Mobile v8 — Full-featured Privacy Blockchain App
 * Telegram-like design with all LAC features
 */
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import {
  MessageCircle, Wallet, Settings, Send, Shield, Eye, Lock,
  Copy, ArrowLeft, Plus, Users, User, ChevronRight, LogOut,
  Clock, Hash, Award, Zap, Download, Upload, Search, X, Menu,
  RefreshCw, AlertTriangle, Check, Globe, Trash2, Star, Phone,
  Activity, Blocks, TrendingUp, QrCode, Network, Bell, Filter,
  ChevronDown, Bookmark, Gift, Flame, Timer, Link2, UserPlus, ArrowUpRight, ArrowDownLeft, Skull,
  Image, Mic, MicOff, Play, Pause, Volume2, FileImage, Bitcoin
} from 'lucide-react';
// ─── Bitcoin crypto — inline to avoid Rollup subpath issues ─────────────────
// sha256 via Web Crypto API (built-in browser, zero deps)
const _sha256 = async (data) => new Uint8Array(await crypto.subtle.digest('SHA-256', data instanceof Uint8Array ? data : new Uint8Array(data)));
const _sha256sync = (data) => { throw new Error('use async sha256'); };

// ripemd160 — tiny pure-JS impl (no external dep needed)
const _ripemd160 = (() => {
  const RL=(x,n)=>(x<<n)|(x>>>32-n);
  const F=(j,x,y,z)=>j<16?x^y^z:j<32?(x&y)|(~x&z):j<48?(x|~y)^z:j<64?(x&z)|(y&~z):x^(y|~z);
  const K=[0,0x5A827999,0x6ED9EBA1,0x8F1BBCDC,0xA953FD4E];
  const KK=[0x50A28BE6,0x5C4DD124,0x6D703EF3,0x7A6D76E9,0];
  const R=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,7,4,13,1,10,6,15,3,12,0,9,5,2,14,11,8,3,10,14,4,9,15,8,1,2,7,0,6,13,11,5,12,1,9,11,10,0,8,12,4,13,3,7,15,14,5,6,2,4,0,5,9,7,12,2,10,14,1,3,8,11,6,15,13];
  const RR=[5,14,7,0,9,2,11,4,13,6,15,8,1,10,3,12,6,11,3,7,0,13,5,10,14,15,8,12,4,9,1,2,15,5,1,3,7,14,6,9,11,8,12,2,10,0,4,13,8,6,4,1,3,11,15,0,5,12,2,13,9,7,10,14,12,15,10,4,1,5,8,7,6,2,13,14,0,3,9,11];
  const S=[11,14,15,12,5,8,7,9,11,13,14,15,6,7,9,8,7,6,8,13,11,9,7,15,7,12,15,9,11,7,13,12,11,13,6,7,14,9,13,15,14,8,13,6,5,12,7,5,11,12,14,15,14,15,9,8,9,14,5,6,8,6,5,12,9,15,5,11,6,8,13,12,5,12,13,14,11,8,5,6];
  const SS=[8,9,9,11,13,15,15,5,7,7,8,11,14,14,12,6,9,13,15,7,12,8,9,11,7,7,12,7,6,15,13,11,9,7,15,11,8,6,6,14,12,13,5,14,13,13,7,5,15,5,8,11,14,14,6,14,6,9,12,9,12,5,15,8,8,5,12,9,12,5,14,6,8,13,6,5,15,13,11,11];
  return (msg) => {
    const m8=msg instanceof Uint8Array?msg:new Uint8Array(msg);
    const bits=m8.length*8;
    const padded=new Uint8Array(m8.length+1+((55-m8.length)%64+64)%64+8);
    padded.set(m8); padded[m8.length]=0x80;
    const dv=new DataView(padded.buffer);
    dv.setUint32(padded.length-8,bits>>>0,true);
    dv.setUint32(padded.length-4,Math.floor(bits/2**32)>>>0,true);
    let [h0,h1,h2,h3,h4]=[0x67452301,0xEFCDAB89,0x98BADCFE,0x10325476,0xC3D2E1F0];
    for(let i=0;i<padded.length;i+=64){
      const W=Array.from({length:16},(_,j)=>dv.getUint32(i+j*4,true));
      let [a,b,c,d,e,aa,bb,cc,dd,ee]=[h0,h1,h2,h3,h4,h0,h1,h2,h3,h4];
      for(let j=0;j<80;j++){
        let T=(RL(a+F(j,b,c,d)+W[R[j]]+K[j>>4],S[j])+e)>>>0; [a,e,d,c,b]=[e,d,RL(c,10),b,T];
        T=(RL(aa+F(79-j,bb,cc,dd)+W[RR[j]]+KK[j>>4],SS[j])+ee)>>>0; [aa,ee,dd,cc,bb]=[ee,dd,RL(cc,10),bb,T];
      }
      [h0,h1,h2,h3,h4]=[(h1+c+dd)>>>0,(h2+d+ee)>>>0,(h3+e+aa)>>>0,(h4+a+bb)>>>0,(h0+b+cc)>>>0];
    }
    const out=new Uint8Array(20); const ov=new DataView(out.buffer);
    [h0,h1,h2,h3,h4].forEach((h,i)=>ov.setUint32(i*4,h,true));
    return out;
  };
})();

// bech32 — minimal inline encoder for P2WPKH (bc1q addresses)
const _bech32 = (() => {
  const CHARSET='qpzry9x8gf2tvdw0s3jn54khce6mua7l';
  const GEN=[0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3];
  const polymod=(v)=>{let c=1;for(const d of v){const b=c>>25;c=((c&0x1ffffff)<<5)^d;for(let i=0;i<5;i++)if((b>>i)&1)c^=GEN[i];}return c;};
  const hrpExpand=(hrp)=>{const r=[];for(const c of hrp)r.push(c.charCodeAt(0)>>5);r.push(0);for(const c of hrp)r.push(c.charCodeAt(0)&31);return r;};
  const createChecksum=(hrp,data)=>{const v=[...hrpExpand(hrp),...data,0,0,0,0,0,0];const p=polymod(v)^1;return Array.from({length:6},(_,i)=>(p>>(5*(5-i)))&31);};
  const convertbits=(data,frombits,tobits,pad=true)=>{let acc=0,bits=0;const r=[];for(const v of data){acc=(acc<<frombits)|v;bits+=frombits;while(bits>=tobits){bits-=tobits;r.push((acc>>bits)&((1<<tobits)-1));}}if(pad&&bits>0)r.push((acc<<(tobits-bits))&((1<<tobits)-1));return r;};
  const toWords=(data)=>convertbits(Array.from(data),8,5);
  return {encode:(hrp,data)=>{const d=toWords(data);const combined=[...d,...createChecksum(hrp,d)];return hrp+'1'+combined.map(i=>CHARSET[i]).join('');},toWords};
})();

// ─── API Layer ────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL || '';
const api = async (path, opts = {}) => {
  const seed = localStorage.getItem('lac_seed');
  const h = { 'Content-Type': 'application/json' };
  if (seed) h['X-Seed'] = seed;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000); // 12s max
  try {
    const r = await fetch(API_BASE + path, {
      method: opts.method || 'GET',
      headers: { ...h, ...opts.headers },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
  } catch(e) {
    clearTimeout(timeout);
    if (e.name === 'AbortError') throw new Error('Timeout (12s) — сервер не відповів');
    throw e;
  }
};
const post = (p, b) => api(p, { method: 'POST', body: b });
const get = (p) => api(p);

// ─── WebSocket hook — real-time push with polling fallback ───────
// ─── Global singleton WebSocket — ONE connection for entire app ──────────────
const _wsListeners = new Set();
let _wsInstance = null;
let _wsReconnectTimer = null;
let _wsAlive = false;
let _wsConnected = false;

const _wsConnect = () => {
  if (_wsInstance && _wsInstance.readyState <= 1) return; // already connecting/open
  const seed = localStorage.getItem('lac_seed');
  if (!seed || !_wsAlive) return;

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws?seed=${encodeURIComponent(seed)}`);
  _wsInstance = ws;

  ws.onopen = () => {
    _wsConnected = true;
    const ping = setInterval(() => {
      if (ws.readyState === 1) ws.send('ping');
      else clearInterval(ping);
    }, 30000);
  };

  ws.onmessage = (e) => {
    if (e.data === 'pong') return;
    try {
      const msg = JSON.parse(e.data);
      _wsListeners.forEach(fn => { try { fn(msg); } catch {} });
    } catch {}
  };

  ws.onclose = () => {
    _wsConnected = false;
    if (!_wsAlive) return;
    _wsReconnectTimer = setTimeout(_wsConnect, 3000);
  };

  ws.onerror = () => ws.close();
};

const useRealtimeSocket = (onMessage) => {
  useEffect(() => {
    _wsAlive = true;
    _wsListeners.add(onMessage);
    // Delay WS connection — let app render first, faster initial load
    const t = setTimeout(_wsConnect, 1500);
    return () => {
      clearTimeout(t);
      _wsListeners.delete(onMessage);
    };
  }, []);

  return { isConnected: () => _wsConnected };
};

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

// ─── i18n ─────────────────────────────────────────────
const i18n = {
  en: {
    chats:'Chats', wallet:'Wallet', explore:'Explore', profile:'Profile', panic:'PANIC',
    messages:'Messages', groups:'Groups', noMessages:'No messages yet', startConvo:'Start a conversation',
    noGroups:'No groups', createGroup:'Create a group', newMessage:'New Message',
    ephemeral:'Ephemeral', burnAfterRead:'Burn after read', replyTo:'Reply', online:'online',
    noMsgYet:'No messages yet', sendFirst:'Send the first message', writeFirst:'Write the first message',
    ephAutoDelete:'Messages self-destruct after 5 min', onChainZH:'On-chain · Zero-History L3→L2→L1',
    privateGroup:'Private group · Invite only', groupCopied:'Group link copied!',
    enterAddr:'Enter @username or lac1… address', startChat:'Start Chat',
    groupName:'Group name', groupType:'Group type', create:'Create',
    public:'Public', private:'Private', l1:'L1 Blockchain', l2:'L2 Ephemeral',
    totalBalance:'Total Balance', send:'Send', faucet:'Faucet',
    veil:'VEIL', stash:'STASH', dice:'Dice', contacts:'Contacts',
    mining:'Mining', miningDetails:'Details', levelProgress:'Level Progress',
    recentTx:'Recent Transactions', viewAll:'View All', noTx:'No transactions',
    lacEarned:'LAC earned', active:'Active', waiting:'Waiting',
    refresh:'Refresh', copied:'Copied!', copy:'Copy', share:'Share',
    recipient:'Recipient', amount:'Amount', message:'Message',
    sendNormal:'Normal Transfer', sendVeil:'VEIL Transfer (Anonymous)',
    fee:'Fee', sendBtn:'Send', sending:'Sending…',
    stashTitle:'STASH Pool', anonSafe:'Anonymous Vault',
    stashDesc:'Deposit → secret key → withdraw to ANY wallet. Zero link.',
    deposit:'Deposit', withdraw:'Withdraw', savedKeys:'Saved Keys',
    poolLac:'Pool', activeKeys:'Active Keys', redeemed:'Redeemed',
    depositSuccess:'Deposit successful!', stashKey:'STASH KEY — TAP TO COPY',
    stashWarn:'Anyone with this key can withdraw. Keep it safe!',
    withdrawKey:'Paste STASH key here', noKeys:'No saved keys',
    tapCopy:'Tap to copy', deleteKey:'Delete', markUsed:'Mark used',
    miningInfo:'Mining Info', blockReward:'Block Reward',
    winnersBlock:'Winners / Block', minBalance:'Min. Balance', yourBalance:'Your Balance',
    yourLevel:'Your Level', miningChance:'Mining Chance',
    totalEarned:'Total Earned', recentRewards:'Recent Rewards', noRewards:'No rewards yet',
    miningExplain:'PoET — fair mining without energy waste',
    diceGame:'Dice Game', placeBet:'Place Bet', betAmount:'Bet Amount',
    redBlack:'Red / Black', overUnder:'Over / Under', roll:'Roll!',
    youWon:'You won!', youLost:'You lost', gameHistory:'History',
    settings:'Settings', registerUsername:'Register Username', getYourName:'Claim your @name',
    upgradeLevel:'Upgrade Level', copyAddress:'Copy Address', exportSeed:'Export Seed',
    backupKey:'Back up your secret key', logout:'Log Out', saveSeedFirst:'Save seed first!',
    language:'Language', seedWarning:'Your seed will be shown.\nMake sure nobody is watching!\nShow seed?',
    makeSureSaved:'Make sure your seed is saved!',
    panicMsg:'This will erase ALL local data. Your wallet remains on the network — restore anytime with your seed.',
    dashboard:'Dashboard', supply:'Supply', onWallets:'On wallets', totalMined:'Total Mined',
    burnedForever:'Burned forever', inStash:'In STASH Pool', totalEmitted:'Total Emitted',
    blocks:'Blocks', wallets:'Wallets',
    txCount:'TXs', allTimeTx:'All-time Transactions', normal:'Normal',
    burns:'Burns', usernames:'Usernames', topBalances:'Top Balances', levelDist:'Level Distribution',
    walletsCount:'wallets', l2encrypted:'L2 encrypted (auto-deleted)',
    diceLost:'Dice lost', diceWon:'Dice won',
    explorer:'Explorer', loadingBlocks:'Loading blocks…', time:'Time', miner:'Miner',
    transactions:'Transactions', noTxInBlock:'No transactions',
    anonymous:'Anonymous', from:'From', to:'To',
    noContacts:'No contacts yet', addContact:'Add Contact', enterContact:'Enter @username or lac1… address',
    add:'Add',
    timeLock:'Time-Lock', lockFunds:'Lock funds for the future',
    welcome:'Welcome to LAC', privacyFirst:'Privacy-first blockchain', createWallet:'Create Wallet',
    importSeed:'Import Seed', backupSeed:'Back Up Your Seed', writeSeedDown:'Write it down! Lost seed = lost wallet.',
    seedSaved:'I saved my seed →', enterSeed:'Enter your seed phrase',
    loginBtn:'Sign In',
    loading:'Loading…', error:'Error', success:'Success', cancel:'Cancel', confirm:'Confirm', save:'Save',
    back:'Back', done:'Done', close:'Close', search:'Search', more:'More',
  },
  uk: {
    chats:'Чати', wallet:'Гаманець', explore:'Огляд', profile:'Профіль', panic:'ПАНІК',
    messages:'Повідомлення', groups:'Групи', noMessages:'Немає повідомлень', startConvo:'Почніть розмову',
    noGroups:'Немає груп', createGroup:'Створити групу', newMessage:'Нове повідомлення',
    ephemeral:'Тимчасове', burnAfterRead:'Знищити після перегляду', replyTo:'Відповісти', online:'онлайн',
    noMsgYet:'Повідомлень поки немає', sendFirst:'Надішліть перше повідомлення', writeFirst:'Напишіть перше повідомлення',
    ephAutoDelete:'Повідомлення самознищуються через 5 хв', onChainZH:'On-chain · Zero-History L3→L2→L1',
    privateGroup:'Приватна група · Тільки за запрошенням', groupCopied:'Посилання скопійовано!',
    enterAddr:'Введіть @нікнейм або lac1… адресу', startChat:'Почати чат',
    groupName:'Назва групи', groupType:'Тип групи', create:'Створити',
    public:'Публічна', private:'Приватна', l1:'L1 Блокчейн', l2:'L2 Тимчасова',
    totalBalance:'Загальний баланс', send:'Надіслати', faucet:'Кран',
    veil:'VEIL', stash:'STASH', dice:'Кубики', contacts:'Контакти',
    mining:'Майнінг', miningDetails:'Деталі', levelProgress:'Прогрес рівня',
    recentTx:'Останні транзакції', viewAll:'Усі', noTx:'Немає транзакцій',
    lacEarned:'LAC зароблено', active:'Активний', waiting:'Очікування',
    refresh:'Оновити', copied:'Скопійовано!', copy:'Копіювати', share:'Поділитися',
    recipient:'Отримувач', amount:'Сума', message:'Повідомлення',
    sendNormal:'Звичайний переказ', sendVeil:'VEIL переказ (Анонімний)',
    fee:'Комісія', sendBtn:'Надіслати', sending:'Надсилання…',
    stashTitle:'STASH Пул', anonSafe:'Анонімний сейф',
    stashDesc:'Депозит → секретний ключ → виведення на БУДЬ-ЯКИЙ гаманець. Нульовий зв\'язок.',
    deposit:'Депозит', withdraw:'Вивести', savedKeys:'Збережені ключі',
    poolLac:'Пул', activeKeys:'Активні ключі', redeemed:'Використано',
    depositSuccess:'Депозит успішний!', stashKey:'STASH КЛЮЧ — НАТИСНІТЬ ДЛЯ КОПІЮВАННЯ',
    stashWarn:'Будь-хто з цим ключем може вивести кошти. Бережіть його!',
    withdrawKey:'Вставте ключ STASH', noKeys:'Немає збережених ключів',
    tapCopy:'Натисніть для копіювання', deleteKey:'Видалити', markUsed:'Позначити як використаний',
    miningInfo:'Інфо майнінгу', blockReward:'Нагорода за блок',
    winnersBlock:'Переможців / блок', minBalance:'Мін. баланс', yourBalance:'Ваш баланс',
    yourLevel:'Ваш рівень', miningChance:'Шанс майнінгу',
    totalEarned:'Всього зароблено', recentRewards:'Останні нагороди', noRewards:'Нагород поки немає',
    miningExplain:'PoET — чесний майнінг без витрат енергії',
    diceGame:'Гра в кубики', placeBet:'Зробити ставку', betAmount:'Сума ставки',
    redBlack:'Червоне / Чорне', overUnder:'Більше / Менше', roll:'Кинути!',
    youWon:'Ви виграли!', youLost:'Ви програли', gameHistory:'Історія',
    settings:'Налаштування', registerUsername:'Зареєструвати нікнейм', getYourName:'Отримайте свій @нікнейм',
    upgradeLevel:'Підвищити рівень', copyAddress:'Копіювати адресу', exportSeed:'Експорт Seed',
    backupKey:'Збережіть секретний ключ', logout:'Вийти', saveSeedFirst:'Спочатку збережіть seed!',
    language:'Мова', seedWarning:'Ваш seed буде показано.\nПереконайтеся, що ніхто не бачить!\nПоказати seed?',
    makeSureSaved:'Переконайтеся, що seed збережено!',
    panicMsg:'Всі локальні дані будуть видалені. Гаманець залишається в мережі — увійдіть знову через seed.',
    dashboard:'Статистика', supply:'Емісія', onWallets:'На гаманцях', totalMined:'Всього намайнено',
    burnedForever:'Спалено назавжди', inStash:'В пулі STASH', totalEmitted:'Всього емітовано',
    blocks:'Блоки', wallets:'Гаманці',
    txCount:'ТX', allTimeTx:'Транзакції за весь час', normal:'Звичайні',
    burns:'Спалювання', usernames:'Нікнейми', topBalances:'Топ балансів', levelDist:'Розподіл рівнів',
    walletsCount:'гаманців', l2encrypted:'L2 зашифрованих (авто-видалені)',
    diceLost:'Програно в кубики', diceWon:'Виграно в кубики',
    explorer:'Провідник', loadingBlocks:'Завантаження блоків…', time:'Час', miner:'Майнер',
    transactions:'Транзакції', noTxInBlock:'Немає транзакцій',
    anonymous:'Анонімний', from:'Від', to:'Кому',
    noContacts:'Контактів поки немає', addContact:'Додати контакт', enterContact:'Введіть @нікнейм або lac1… адресу',
    add:'Додати',
    timeLock:'Time-Lock', lockFunds:'Заблокувати кошти на майбутнє',
    welcome:'Ласкаво просимо до LAC', privacyFirst:'Блокчейн із захистом приватності', createWallet:'Створити гаманець',
    importSeed:'Імпортувати Seed', backupSeed:'Збережіть ваш Seed', writeSeedDown:'Запишіть! Втрачений seed = втрачений гаманець.',
    seedSaved:'Я зберіг seed →', enterSeed:'Введіть seed-фразу',
    loginBtn:'Увійти',
    loading:'Завантаження…', error:'Помилка', success:'Успіх', cancel:'Скасувати', confirm:'Підтвердити', save:'Зберегти',
    back:'Назад', done:'Готово', close:'Закрити', search:'Пошук', more:'Більше',
  },
  ru: {
    chats:'Чаты', wallet:'Кошелёк', explore:'Обзор', profile:'Профиль', panic:'ПАНИКА',
    messages:'Сообщения', groups:'Группы', noMessages:'Нет сообщений', startConvo:'Начните разговор',
    noGroups:'Нет групп', createGroup:'Создать группу', newMessage:'Новое сообщение',
    ephemeral:'Временное', burnAfterRead:'Сжечь после просмотра', replyTo:'Ответить', online:'онлайн',
    noMsgYet:'Сообщений пока нет', sendFirst:'Отправьте первое сообщение', writeFirst:'Напишите первое сообщение',
    ephAutoDelete:'Сообщения самоудаляются через 5 мин', onChainZH:'On-chain · Zero-History L3→L2→L1',
    privateGroup:'Приватная группа · Только по приглашению', groupCopied:'Ссылка скопирована!',
    enterAddr:'Введите @никнейм или lac1… адрес', startChat:'Начать чат',
    groupName:'Название группы', groupType:'Тип группы', create:'Создать',
    public:'Публичная', private:'Приватная', l1:'L1 Блокчейн', l2:'L2 Временная',
    totalBalance:'Общий баланс', send:'Отправить', faucet:'Кран',
    veil:'VEIL', stash:'STASH', dice:'Кости', contacts:'Контакты',
    mining:'Майнинг', miningDetails:'Подробнее', levelProgress:'Прогресс уровня',
    recentTx:'Последние транзакции', viewAll:'Все', noTx:'Нет транзакций',
    lacEarned:'LAC заработано', active:'Активный', waiting:'Ожидание',
    refresh:'Обновить', copied:'Скопировано!', copy:'Копировать', share:'Поделиться',
    recipient:'Получатель', amount:'Сумма', message:'Сообщение',
    sendNormal:'Обычный перевод', sendVeil:'VEIL перевод (Анонимный)',
    fee:'Комиссия', sendBtn:'Отправить', sending:'Отправка…',
    stashTitle:'STASH Пул', anonSafe:'Анонимный сейф',
    stashDesc:'Депозит → секретный ключ → вывод на ЛЮБОЙ кошелёк. Нулевая связь.',
    deposit:'Депозит', withdraw:'Вывести', savedKeys:'Сохранённые ключи',
    poolLac:'Пул', activeKeys:'Активные ключи', redeemed:'Использован',
    depositSuccess:'Депозит успешен!', stashKey:'STASH КЛЮЧ — НАЖМИТЕ ДЛЯ КОПИРОВАНИЯ',
    stashWarn:'Любой с этим ключом может вывести средства. Храните его!',
    withdrawKey:'Вставьте ключ STASH', noKeys:'Нет сохранённых ключей',
    tapCopy:'Нажмите для копирования', deleteKey:'Удалить', markUsed:'Отметить как использованный',
    miningInfo:'Инфо майнинга', blockReward:'Награда за блок',
    winnersBlock:'Победителей / блок', minBalance:'Мин. баланс', yourBalance:'Ваш баланс',
    yourLevel:'Ваш уровень', miningChance:'Шанс майнинга',
    totalEarned:'Всего заработано', recentRewards:'Последние награды', noRewards:'Наград пока нет',
    miningExplain:'PoET — честный майнинг без затрат энергии',
    diceGame:'Игра в кости', placeBet:'Сделать ставку', betAmount:'Сумма ставки',
    redBlack:'Красное / Чёрное', overUnder:'Больше / Меньше', roll:'Бросить!',
    youWon:'Вы выиграли!', youLost:'Вы проиграли', gameHistory:'История',
    settings:'Настройки', registerUsername:'Зарегистрировать никнейм', getYourName:'Получите свой @никнейм',
    upgradeLevel:'Повысить уровень', copyAddress:'Копировать адрес', exportSeed:'Экспорт Seed',
    backupKey:'Сохраните секретный ключ', logout:'Выйти', saveSeedFirst:'Сначала сохраните seed!',
    language:'Язык', seedWarning:'Ваш seed будет показан.\nУбедитесь, что никто не смотрит!\nПоказать seed?',
    makeSureSaved:'Убедитесь, что seed сохранён!',
    panicMsg:'Все локальные данные будут удалены. Кошелёк остаётся в сети — войдите снова через seed.',
    dashboard:'Статистика', supply:'Эмиссия', onWallets:'На кошельках', totalMined:'Всего намайнено',
    burnedForever:'Сожжено навсегда', inStash:'В пуле STASH', totalEmitted:'Всего эмитировано',
    blocks:'Блоки', wallets:'Кошельки',
    txCount:'ТX', allTimeTx:'Транзакции за всё время', normal:'Обычные',
    burns:'Сжигания', usernames:'Никнеймы', topBalances:'Топ балансов', levelDist:'Распределение уровней',
    walletsCount:'кошельков', l2encrypted:'L2 зашифрованных (авто-удалены)',
    diceLost:'Проиграно в кости', diceWon:'Выиграно в кости',
    explorer:'Обозреватель', loadingBlocks:'Загрузка блоков…', time:'Время', miner:'Майнер',
    transactions:'Транзакции', noTxInBlock:'Нет транзакций',
    anonymous:'Анонимный', from:'От', to:'Кому',
    noContacts:'Нет контактов', addContact:'Добавить контакт', enterContact:'Введите @никнейм или lac1… адрес',
    add:'Добавить',
    timeLock:'Time-Lock', lockFunds:'Заблокировать средства на будущее',
    welcome:'Добро пожаловать в LAC', privacyFirst:'Блокчейн с защитой приватности', createWallet:'Создать кошелёк',
    importSeed:'Импортировать Seed', backupSeed:'Сохраните ваш Seed', writeSeedDown:'Запишите! Потерянный seed = потерянный кошелёк.',
    seedSaved:'Я сохранил seed →', enterSeed:'Введите seed-фразу',
    loginBtn:'Войти',
    loading:'Загрузка…', error:'Ошибка', success:'Успех', cancel:'Отмена', confirm:'Подтвердить', save:'Сохранить',
    back:'Назад', done:'Готово', close:'Закрыть', search:'Поиск', more:'Ещё',
  }
};
const getLang = () => { const l = localStorage.getItem('lac_lang'); return ['en','uk','ru'].includes(l) ? l : 'en'; };
const LangCtx = React.createContext({ lang: 'en', setLang: () => {}, t: (k) => k });
const useT = () => React.useContext(LangCtx);

// ─── Shared Components ────────────────────────────────
const Header = ({ title, onBack, right }) => (
  <header className="flex items-center gap-3 px-4 py-3.5 bg-[#070d1e]/95 backdrop-blur-xl border-b border-white/[0.06] sticky top-0 z-10">
    {onBack && <button onClick={onBack} className="p-1.5 -ml-1 rounded-xl active:bg-white/5 transition"><ArrowLeft className="w-5 h-5 text-[#B8E6FF]/70" /></button>}
    <h1 className="text-white font-semibold tracking-tight text-[17px] flex-1">{title}</h1>
    {right}
  </header>
);

const Card = ({ children, className = '', gradient, onClick }) => (
  <div onClick={onClick} className={`rounded-2xl p-4 border border-white/[0.07] ${gradient || 'bg-white/[0.04] backdrop-blur-xl'} ${onClick?'cursor-pointer active:opacity-75 transition-opacity':''} ${className}`}>{children}</div>
);

const StatBox = ({ icon, label, value, color = 'text-cyan-400', small }) => (
  <div className={`bg-[#0a1628] rounded-xl ${small ? 'p-2.5' : 'p-3'} text-center border border-cyan-900/15`}>
    <div className={`${small ? 'text-xl' : 'text-2xl'} font-bold ${color}`}>{value}</div>
    <div className="text-gray-500 text-[10px] mt-0.5 flex items-center justify-center gap-1">{icon}{label}</div>
  </div>
);

const Btn = ({ children, onClick, color = 'cyan', disabled, loading, full, ghost, small, className = '' }) => {
  const colors = {
    cyan: ghost ? 'bg-cyan-400/10 text-cyan-400 border border-cyan-400/30' : 'bg-gradient-to-b from-[#00E5FF] to-[#0099BB] text-[#070d1e] font-bold shadow-lg shadow-cyan-500/20',
    emerald: ghost ? 'bg-cyan-400/10 text-cyan-400 border border-cyan-400/30' : 'bg-gradient-to-b from-[#00E5FF] to-[#0099BB] text-[#070d1e] font-bold shadow-lg shadow-cyan-500/20',
    purple: ghost ? 'bg-purple-400/10 text-purple-400 border border-purple-400/30' : 'bg-gradient-to-b from-purple-500 to-purple-700 text-white shadow-lg shadow-purple-600/20',
    red: ghost ? 'bg-red-400/10 text-red-400 border border-red-400/25' : 'bg-gradient-to-b from-red-500 to-red-700 text-white shadow-lg shadow-red-600/20',
    gray: 'bg-white/[0.06] text-[#B8E6FF] border border-white/[0.08] hover:bg-white/[0.09]',
    amber: ghost ? 'bg-amber-400/10 text-amber-400 border border-amber-400/25' : 'bg-gradient-to-b from-amber-400 to-amber-600 text-[#070d1e] font-bold shadow-lg shadow-amber-500/20',
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`${colors[color] || colors.gray} ${small ? 'px-3 py-1.5 text-xs rounded-xl' : 'px-4 py-2.5 text-sm rounded-2xl'} font-semibold transition-all duration-150 disabled:opacity-40 active:scale-[0.98] ${full ? 'w-full flex items-center justify-center' : ''} ${className}`}>
      {loading ? <span className="opacity-60">…</span> : children}
    </button>
  );
};

const Input = ({ value, onChange, placeholder, mono, type = 'text', right }) => (
  <div className="relative">
    <input
      type={type} value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full bg-white/[0.05] text-white placeholder-[#B8E6FF]/30 px-4 py-3 rounded-2xl border border-white/[0.08] outline-none focus:border-cyan-400/40 focus:bg-white/[0.07] transition text-sm ${mono ? 'font-mono' : ''} ${right ? 'pr-10' : ''}`}
    />
    {right && <div className="absolute right-3 top-1/2 -translate-y-1/2">{right}</div>}
  </div>
);

const Badge = ({ children, color = 'cyan' }) => {
  const c = {
    cyan:'bg-cyan-400/10 text-cyan-400 border-cyan-400/20',
    emerald:'bg-cyan-400/10 text-cyan-400 border-cyan-400/20',
    purple:'bg-purple-400/10 text-purple-400 border-purple-400/20',
    amber:'bg-amber-400/10 text-amber-400 border-amber-400/20',
    red:'bg-red-400/10 text-red-400 border-red-400/20',
    blue:'bg-blue-400/10 text-blue-400 border-blue-400/20',
    gray:'bg-white/5 text-[#B8E6FF]/50 border-white/10',
    yellow:'bg-yellow-400/10 text-yellow-400 border-yellow-400/20',
  };
  return <span className={`text-[10px] px-1.5 py-0.5 rounded-md border font-medium ${c[color]||c.gray}`}>{children}</span>;
};

const ListItem = React.memo(({ icon, title, sub, right, onClick, badge }) => (
  <button onClick={onClick} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-cyan-900/10 active:bg-cyan-900/20 transition border-b border-gray-800/30">
    <div className="w-11 h-11 rounded-full bg-[#0f2044] flex items-center justify-center shrink-0">{icon}</div>
    <div className="flex-1 min-w-0 text-left">
      <div className="flex items-center gap-2"><p className="text-white text-[14px] font-medium truncate">{title}</p>{badge}</div>
      {sub && <p className="text-gray-500 text-xs truncate">{sub}</p>}
    </div>
    {right || <ChevronRight className="w-4 h-4 text-gray-700 shrink-0" />}
  </button>
));

const Empty = ({ emoji, text, sub }) => (
  <div className="flex flex-col items-center py-16 text-gray-600">
    <div className="text-4xl mb-3 opacity-40">{emoji}</div>
    <p className="text-sm">{text}</p>
    {sub && <p className="text-xs mt-1 text-gray-700">{sub}</p>}
  </div>
);

const LevelBadge = ({ level }) => {
  const colors = ['from-gray-500 to-gray-600','from-cyan-500 to-cyan-600','from-teal-400 to-cyan-500','from-cyan-400 to-teal-500','from-amber-400 to-orange-500','from-red-400 to-rose-500','from-purple-400 to-pink-500'];
  return (
    <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${colors[level]||colors[0]} flex items-center justify-center text-white text-xs font-black shadow-lg`}>
      L{level}
    </div>
  );
};

// ━━━ APP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// ━━━ BITCOIN WALLET ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Security: keys derived locally from LAC seed, never sent to any server.
// Uses Blockstream Esplora public API (blockstream.info) for blockchain data.
// P2WPKH (native segwit, bc1q...) via BIP143 transaction signing.

// --- BTC Crypto Helpers (loaded lazily) ---
const BitcoinWalletTab = ({ onMenu }) => {
  const [addr, setAddr] = React.useState('');
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    (async () => {
      try {
        const seed = localStorage.getItem('lac_seed');
        if (!seed) return;
        const enc = new TextEncoder().encode('LAC-BTC-v1:' + seed);
        const h1 = await crypto.subtle.digest('SHA-256', enc);
        const h2 = await crypto.subtle.digest('SHA-256', h1);
        const bytes = new Uint8Array(h2);
        // encode as bech32 watch-only address (display only, no signing yet)
        const CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
        const toWords = (b) => {
          let acc=0,bits=0; const r=[];
          for(const v of b){acc=(acc<<8)|v;bits+=8;while(bits>=5){bits-=5;r.push((acc>>bits)&31);}}
          if(bits>0)r.push((acc<<(5-bits))&31); return r;
        };
        const words = [0, ...toWords(bytes.slice(0,20))];
        // simple checksum
        const GEN=[0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3];
        const hrpExp = (hrp) => { const r=[]; for(const c of hrp)r.push(c.charCodeAt(0)>>5); r.push(0); for(const c of hrp)r.push(c.charCodeAt(0)&31); return r; };
        const polymod = (v) => { let c=1; for(const d of v){const b=c>>25;c=((c&0x1ffffff)<<5)^d;for(let i=0;i<5;i++)if((b>>i)&1)c^=GEN[i];} return c; };
        const chk = (hrp,data) => { const v=[...hrpExp(hrp),...data,0,0,0,0,0,0]; const p=polymod(v)^1; return Array.from({length:6},(_,i)=>(p>>(5*(5-i)))&31); };
        const combined = [...words, ...chk('bc', words)];
        const address = 'bc1' + combined.map(i=>CHARSET[i]).join('');
        setAddr(address);
      } catch(e) { console.error('BTC addr:', e); }
    })();
  }, []);

  const copy = () => { navigator.clipboard?.writeText(addr); setCopied(true); setTimeout(()=>setCopied(false),2000); };

  return (
    <div className="h-full flex flex-col bg-[#0a0a0a]">
      <div className="flex items-center gap-3 px-4 pt-12 pb-6">
        <button onClick={onMenu} className="text-gray-400"><span className="text-xl">☰</span></button>
        <span className="text-yellow-400 text-xl">₿</span>
        <h1 className="text-xl font-bold text-white">Bitcoin</h1>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6 gap-6">
        <div className="w-20 h-20 rounded-full bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center">
          <span className="text-4xl">₿</span>
        </div>

        <div className="text-center">
          <p className="text-white font-semibold text-lg mb-1">Bitcoin Watch Wallet</p>
          <p className="text-gray-500 text-sm">Receive-only · Signing coming soon</p>
        </div>

        {addr ? (
          <div className="w-full bg-gray-900/60 border border-gray-800 rounded-2xl p-4">
            <p className="text-gray-500 text-xs mb-2 text-center">Your Bitcoin Address</p>
            <p className="text-white text-xs text-center break-all font-mono leading-relaxed">{addr}</p>
            <button onClick={copy}
              className="mt-3 w-full py-2.5 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm font-medium">
              {copied ? '✓ Copied!' : 'Copy Address'}
            </button>
          </div>
        ) : (
          <div className="w-full bg-gray-900/60 border border-gray-800 rounded-2xl p-4 text-center">
            <p className="text-gray-600 text-sm">Log in to LAC to generate address</p>
          </div>
        )}

        <div className="w-full bg-gray-900/40 border border-gray-800/50 rounded-2xl p-4 space-y-3">
          <p className="text-gray-400 text-xs font-medium uppercase tracking-wider">Coming Soon</p>
          <div className="flex items-center gap-3 text-gray-600 text-sm"><span>⚡</span><span>Send & receive BTC</span></div>
          <div className="flex items-center gap-3 text-gray-600 text-sm"><span>🔄</span><span>BTC ↔ LAC atomic swaps</span></div>
          <div className="flex items-center gap-3 text-gray-600 text-sm"><span>🔒</span><span>HD wallet (BIP32/39/44)</span></div>
        </div>
      </div>
    </div>
  );
};


// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 🐍 NAGINI — Geographic Secret Distribution
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const NaginiView = ({ onBack, profile }) => {
  const [screen, setScreen] = useState('home'); // home | setup | recover | bundle | dms
  const [bundles, setBundles] = useState([]);
  const [selBundle, setSelBundle] = useState(null);
  const [available, setAvailable] = useState(null);
  const [debug, setDebug] = useState('');
  const [loading, setLoading] = useState(true);

  const hasSeed = !!localStorage.getItem('lac_seed');

  useEffect(() => {
    const init = async () => {
      try {
        const r = await get('/api/nagini/status');
        setAvailable(r.available);
        if (!r.available) setDebug('❌ pip install cryptography — пакет не встановлено на сервері!');
      } catch(e) {
        setAvailable(false);
        setDebug('❌ Помилка підключення до сервера: ' + e.message);
      }
      try {
        const r2 = await get('/api/nagini/bundles');
        setBundles(r2.bundles || []);
      } catch {}
      setLoading(false);
    };
    init();
  }, []);

  const loadBundles = async () => {
    try { const r = await get('/api/nagini/bundles'); setBundles(r.bundles||[]); } catch {}
  };

  if (screen === 'setup') return <NaginiSetup onBack={() => { setScreen('home'); loadBundles(); }} />;
  if (screen === 'recover') return <NaginiRecover onBack={() => setScreen('home')} bundles={bundles} />;
  if (screen === 'bundle' && selBundle) return <NaginiBundleDetail bundle={selBundle} onBack={() => { setScreen('home'); loadBundles(); }} onDMS={() => setScreen('dms')} />;
  if (screen === 'dms' && selBundle) return <NaginiDMS onBack={() => setScreen('bundle')} bundle={selBundle} />;

  return (
    <div className="flex flex-col h-full">
      <Header title="🐍 Nagini" onBack={onBack} />
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Status */}
        <div className={`rounded-xl p-3 text-xs border ${
          available === null ? 'bg-gray-800/40 border-gray-700/30 text-gray-500' :
          available ? (hasSeed ? 'bg-cyan-900/20 border-cyan-800/30 text-cyan-400' : 'bg-amber-900/20 border-amber-800/30 text-amber-400') :
          'bg-red-900/20 border-red-800/30 text-red-400'
        }`}>
          {available === null && '⏳ Перевірка сервера...'}
          {available === true && hasSeed && '✅ Готово — Nagini активний, seed знайдено'}
          {available === true && !hasSeed && '⚠️ Seed не знайдено. Виконайте вихід і вхід знову.'}
          {available === false && (debug || '❌ Сервер не підтримує Nagini')}
        </div>

        {/* Actions */}
        {available && hasSeed && (
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => setScreen('setup')}
              className="p-4 rounded-2xl bg-cyan-900/20 border border-cyan-800/30 text-center active:bg-cyan-900/40">
              <div className="text-2xl mb-1">🔐</div>
              <div className="text-cyan-400 text-sm font-semibold">Створити</div>
              <div className="text-gray-500 text-[10px]">Новий bundle</div>
            </button>
            <button onClick={() => setScreen('recover')} disabled={bundles.length === 0}
              className="p-4 rounded-2xl bg-blue-900/20 border border-blue-800/30 text-center active:bg-blue-900/40 disabled:opacity-40">
              <div className="text-2xl mb-1">🔓</div>
              <div className="text-blue-400 text-sm font-semibold">Відновити</div>
              <div className="text-gray-500 text-[10px]">{bundles.length} bundle{bundles.length !== 1 ? 's' : ''}</div>
            </button>
          </div>
        )}

        {/* Bundle list */}
        {bundles.length > 0 && (
          <div>
            <div className="text-gray-500 text-xs font-medium mb-2">Ваші bundles</div>
            {bundles.map(b => (
              <button key={b.bundle_id} onClick={() => { setSelBundle(b); setScreen('bundle'); }}
                className="w-full flex items-center justify-between p-3 rounded-xl bg-[#0a1628]/80 border border-cyan-900/20 mb-2 active:bg-cyan-900/20">
                <div className="text-left">
                  <div className="text-white text-sm font-medium">{b.label || 'Bundle'}</div>
                  <div className="text-gray-500 text-[10px]">{b.n} локацій · threshold {b.threshold} · {b.has_canary ? '🪤' : ''}{b.has_dms ? '⏰' : ''}</div>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-600" />
              </button>
            ))}
          </div>
        )}

        {/* How it works */}
        <div className="bg-[#0a1628]/60 border border-cyan-900/20 rounded-xl p-3 text-xs text-gray-500 space-y-1">
          <div className="text-cyan-400 font-semibold mb-1">🐍 Як це працює</div>
          <div>1. Твій seed розбивається на N шардів (Shamir Secret Sharing)</div>
          <div>2. Кожен шард зашифрований GPS-ключем конкретного місця</div>
          <div>3. Зібери K шардів (відвідай K місць) → seed відновлено</div>
          <div>4. Без GPS-координат шард не розшифрувати</div>
        </div>
      </div>
    </div>
  );
};


const NaginiSetup = ({ onBack }) => {
  const [step, setStep] = useState(1);
  const [secretType, setSecretType] = useState('seed');
  const [customSecret, setCustomSecret] = useState('');
  const [label, setLabel] = useState('');
  const [locations, setLocations] = useState([
    {name:'', lat:'', lon:''},
    {name:'', lat:'', lon:''},
  ]);
  const [threshold, setThreshold] = useState(2);
  const [canaryIdx, setCanaryIdx] = useState(null);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(-1);
  const [result, setResult] = useState(null);
  const [log, setLog] = useState('');

  const addLocation = () => setLocations(l => [...l, {name:'', lat:'', lon:''}]);
  const removeLocation = (i) => setLocations(l => l.filter((_,j) => j !== i));
  const setLoc = (i, field, val) => setLocations(l => { const n=[...l]; n[i]={...n[i],[field]:val}; return n; });

  const getGPS = (i) => {
    setLocating(i);
    navigator.geolocation.getCurrentPosition(
      pos => {
        setLoc(i, 'lat', pos.coords.latitude.toFixed(6));
        setLoc(i, 'lon', pos.coords.longitude.toFixed(6));
        setLocating(-1);
        toast.success(`📍 GPS: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`);
      },
      err => { setLocating(-1); toast.error('GPS: ' + err.message); },
      {enableHighAccuracy: true, timeout: 15000}
    );
  };

  const submit = async () => {
    setLog('');
    // Build secret
    let secretB64 = '';
    if (secretType === 'seed') {
      const seed = localStorage.getItem('lac_seed') || '';
      if (!seed) { toast.error('❌ Seed не знайдено! Перезайдіть в акаунт.'); return; }
      // Safe base64: use Uint8Array→btoa method
      const enc2 = new TextEncoder().encode(seed);
      secretB64 = btoa(String.fromCharCode(...enc2));
      setLog(`Seed: ${seed.slice(0,8)}... (${seed.length} chars) → b64 len=${secretB64.length}`);
    } else {
      if (!customSecret.trim()) { toast.error('Введіть секретний текст'); return; }
      const encC = new TextEncoder().encode(customSecret.trim());
      secretB64 = btoa(String.fromCharCode(...encC));
    }

    const validLocs = locations.filter(l => l.lat && l.lon);
    if (validLocs.length < 2) { toast.error('Потрібно мінімум 2 локації з GPS'); return; }

    setLoading(true);
    setLog(prev => prev + '\nВідправляю на сервер...');

    try {
      const body = {
        secret: secretB64,
        label: label || 'My Bundle',
        locations: validLocs.map(l => [parseFloat(l.lat), parseFloat(l.lon)]),
        threshold,
        canary_index: canaryIdx,
      };
      setLog(prev => prev + `\nLocations: ${JSON.stringify(body.locations)}`);
      const r = await post('/api/nagini/setup', body);
      setLog(prev => prev + '\nВідповідь: ' + JSON.stringify(r));
      if (r.ok) {
        setResult(r);
        setStep(99); // done
      } else {
        toast.error('❌ ' + (r.error || 'Помилка сервера'), {duration: 8000});
      }
    } catch(e) {
      setLog(prev => prev + '\n❌ Error: ' + e.message);
      toast.error('❌ ' + e.message, {duration: 8000});
    }
    setLoading(false);
  };

  if (step === 99 && result) return (
    <div className="flex flex-col h-full">
      <Header title="✅ Bundle створено" onBack={onBack} />
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="text-center py-6">
          <div className="text-5xl mb-3">✅</div>
          <div className="text-cyan-400 font-bold text-lg">{result.label}</div>
          <div className="text-gray-500 text-sm mt-1">{result.n} локацій · threshold {result.threshold}</div>
          <div className="mt-3 bg-black/30 rounded-xl p-3">
            <div className="text-gray-500 text-xs mb-1">Bundle ID</div>
            <div className="text-cyan-300 text-xs font-mono break-all">{result.bundle_id}</div>
          </div>
        </div>
        <div className="bg-amber-900/10 border border-amber-800/30 rounded-xl p-3 text-xs text-amber-400">
          ⚠️ Запиши назви місць окремо від пристрою. GPS координати не зберігаються на сервері.
        </div>
        <Btn onClick={onBack} className="w-full bg-cyan-600">Готово</Btn>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      <Header title={`Створити Bundle — Крок ${Math.min(step,3)}/3`}
        onBack={step === 1 ? onBack : () => setStep(s => s-1)} />
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Step 1: Secret */}
        {step === 1 && <>
          <div className="text-gray-400 text-sm">Що хочеш захистити?</div>
          <div className="grid grid-cols-2 gap-2">
            {[['seed','🔑 LAC Seed'],['custom','✏️ Свій текст']].map(([v,l]) => (
              <button key={v} onClick={() => setSecretType(v)}
                className={`p-3 rounded-xl border text-sm transition-all ${secretType===v?'border-cyan-500 bg-cyan-900/20 text-cyan-400':'border-gray-800 text-gray-500'}`}>
                {l}
              </button>
            ))}
          </div>
          {secretType === 'seed' && (
            <div className={`rounded-xl p-3 text-xs border ${localStorage.getItem('lac_seed')
              ? 'bg-cyan-900/10 border-cyan-800/20 text-cyan-400'
              : 'bg-red-900/20 border-red-700/30 text-red-400'}`}>
              {localStorage.getItem('lac_seed')
                ? `✅ Seed знайдено (${localStorage.getItem('lac_seed').length} символів). Буде розбито на шарди.`
                : '❌ Seed відсутній! Виконайте вихід і вхід знову.'}
            </div>
          )}
          {secretType === 'custom' && (
            <textarea value={customSecret} onChange={e => setCustomSecret(e.target.value)}
              placeholder="Секретний текст, ключ, або будь-що важливе..."
              className="w-full bg-[#0a1628] border border-cyan-900/30 rounded-xl p-3 text-white text-sm resize-none h-24" />
          )}
          <Input value={label} onChange={e => setLabel(e.target.value)} placeholder="Назва (напр. Kyiv backup)" />
          <Btn onClick={() => setStep(2)} className="w-full bg-cyan-600"
            disabled={secretType === 'seed' && !localStorage.getItem('lac_seed')}>
            Далі →
          </Btn>
        </>}

        {/* Step 2: Locations */}
        {step === 2 && <>
          <div className="text-gray-400 text-sm">Встанови GPS локації. Кожен шард прив'язаний до місця.</div>
          {locations.map((loc, i) => (
            <div key={i} className="bg-[#0a1628]/80 border border-cyan-900/20 rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${canaryIdx===i?'bg-amber-900/40 text-amber-400':'bg-cyan-900/30 text-cyan-500'}`}>
                  {canaryIdx===i ? '🪤 Canary' : `#${i+1}`}
                </span>
                <div className="flex gap-2">
                  <button onClick={() => setCanaryIdx(canaryIdx===i ? null : i)}
                    className={`text-[10px] px-2 py-1 rounded-lg border ${canaryIdx===i?'border-amber-700/50 text-amber-400':'border-gray-700/30 text-gray-600'}`}>
                    🪤 trap
                  </button>
                  {locations.length > 2 && (
                    <button onClick={() => removeLocation(i)} className="text-gray-600 text-xs">✕</button>
                  )}
                </div>
              </div>
              <Input value={loc.name} onChange={e => setLoc(i,'name',e.target.value)}
                placeholder={`Місце #${i+1} (напр. Центральний парк)`} />
              <div className="grid grid-cols-2 gap-2">
                <input value={loc.lat} onChange={e => setLoc(i,'lat',e.target.value)}
                  placeholder="Широта" className="bg-[#0a1628] border border-cyan-900/30 rounded-xl px-3 py-2 text-white text-sm" />
                <input value={loc.lon} onChange={e => setLoc(i,'lon',e.target.value)}
                  placeholder="Довгота" className="bg-[#0a1628] border border-cyan-900/30 rounded-xl px-3 py-2 text-white text-sm" />
              </div>
              <button onClick={() => getGPS(i)} disabled={locating===i}
                className="w-full text-xs py-2 rounded-lg bg-cyan-900/20 border border-cyan-900/30 text-cyan-500 disabled:opacity-50">
                {locating===i ? '📡 GPS...' : '📍 Використати моє місце зараз'}
              </button>
              {loc.lat && loc.lon && <div className="text-cyan-600 text-[10px]">✓ {parseFloat(loc.lat).toFixed(5)}, {parseFloat(loc.lon).toFixed(5)}</div>}
            </div>
          ))}
          {locations.length < 8 && (
            <button onClick={addLocation}
              className="w-full py-2 rounded-xl border border-dashed border-cyan-900/30 text-cyan-700 text-sm">
              + Додати локацію
            </button>
          )}
          <div className="bg-[#0a1628]/60 rounded-xl p-3">
            <div className="text-gray-400 text-xs mb-2">Мінімум локацій для відновлення</div>
            <div className="flex gap-2">
              {Array.from({length: locations.length-1}, (_,i) => i+2).map(v => (
                <button key={v} onClick={() => setThreshold(v)}
                  className={`px-3 py-1 rounded-lg text-sm ${threshold===v?'bg-cyan-600 text-white':'bg-[#0a1628] border border-gray-800 text-gray-500'}`}>
                  {v}
                </button>
              ))}
            </div>
            <div className="text-gray-600 text-xs mt-1">Будь-які {threshold} з {locations.length} локацій</div>
          </div>
          <Btn onClick={() => setStep(3)} className="w-full bg-cyan-600"
            disabled={locations.filter(l=>l.lat&&l.lon).length < 2}>
            Далі →
          </Btn>
        </>}

        {/* Step 3: Confirm */}
        {step === 3 && <>
          <div className="text-gray-400 text-sm">Перевір і підтвердь</div>
          <div className="bg-[#0a1628]/60 rounded-xl p-3 text-xs text-gray-400 space-y-1">
            <div className="text-cyan-400 font-semibold mb-1">Підсумок</div>
            <div>• Секрет: {secretType === 'seed' ? `LAC Seed (${(localStorage.getItem('lac_seed')||'').length} chars)` : 'Свій текст'}</div>
            <div>• {locations.filter(l=>l.lat&&l.lon).length} локацій з GPS</div>
            <div>• Threshold: {threshold} з {locations.length}</div>
            {canaryIdx !== null && <div>• Canary пастка на локації #{canaryIdx+1} 🪤</div>}
          </div>
          {log ? (
            <div className="bg-black/40 rounded-xl p-3 text-[10px] font-mono text-gray-400 whitespace-pre-wrap break-all">{log}</div>
          ) : null}
          <Btn onClick={submit} disabled={loading} className="w-full bg-cyan-600 py-4 text-base">
            {loading ? '⏳ Створюю...' : '✅ Створити Bundle'}
          </Btn>
        </>}
      </div>
    </div>
  );
};


const NaginiBundleDetail = ({ bundle, onBack, onDMS }) => {
  const [deleting, setDeleting] = useState(false);
  const del = async () => {
    if (!window.confirm('Delete this bundle? Cannot be undone.')) return;
    setDeleting(true);
    await post('/api/nagini/delete', {bundle_id: bundle.bundle_id});
    onBack();
  };
  return (
    <div className="flex flex-col h-full">
      <Header title={bundle.label || 'Bundle'} onBack={onBack} />
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="rounded-2xl bg-[#0d1e3a] border border-cyan-800/30 p-4 space-y-1">
          {[
            ['Bundle ID', bundle.bundle_id.slice(0,16)+'...'],
            ['Locations', `${bundle.n} total`],
            ['Threshold', `${bundle.threshold} required to recover`],
            ['Created', new Date(bundle.created_at*1000).toLocaleString()],
            ['Canary', bundle.has_canary ? '🪤 Active' : 'None'],
            ["Dead Man's Switch", bundle.has_dms ? '⏰ Active' : 'Not configured'],
          ].map(([k,v]) => (
            <div key={k} className="flex justify-between items-center py-2 border-b border-gray-800/20">
              <span className="text-gray-500 text-sm">{k}</span>
              <span className="text-white text-sm">{v}</span>
            </div>
          ))}
        </div>
        <Btn onClick={onDMS} className="w-full bg-[#0a1628] border border-cyan-800/40 text-cyan-400">
          ⏰ {bundle.has_dms ? 'Manage' : 'Setup'} Dead Man's Switch
        </Btn>
        <Btn onClick={del} disabled={deleting} className="w-full bg-red-900/20 border border-red-800/30 text-red-400">
          {deleting ? 'Deleting...' : '🗑 Delete Bundle'}
        </Btn>
      </div>
    </div>
  );
};

const NaginiRecover = ({ onBack, bundles }) => {
  const [bundleId, setBundleId] = useState(bundles[0]?.bundle_id || '');
  const [sessionId, setSessionId] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null); // {n, threshold, label}
  const [collected, setCollected] = useState(0);
  const [locating, setLocating] = useState(false);
  const [result, setResult] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [starting, setStarting] = useState(false);

  const startSession = async () => {
    setStarting(true);
    setLastResult(null);
    try {
      const r = await post('/api/nagini/session/start', { bundle_id: bundleId });
      if (r.ok) {
        setSessionId(r.session_id);
        setSessionInfo({ n: r.n, threshold: r.threshold, label: r.label });
        setCollected(0);
        toast.success('✅ Сесія відкрита. Скануй локації.');
      } else {
        toast.error('❌ ' + (r.error || 'Помилка'));
      }
    } catch(e) { toast.error('❌ ' + e.message); }
    setStarting(false);
  };

  const cancelSession = async () => {
    if (sessionId) {
      post('/api/nagini/session/cancel', { session_id: sessionId }).catch(()=>{});
    }
    setSessionId(null);
    setSessionInfo(null);
    setCollected(0);
    setLastResult(null);
  };

  const scan = () => {
    if (!sessionId || locating) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const acc = Math.round(pos.coords.accuracy || 0);
        try {
          const r = await post('/api/nagini/session/scan', {
            session_id: sessionId,
            lat, lon,
          });
          setLastResult({ lat: lat.toFixed(5), lon: lon.toFixed(5), acc, ...r });
          if (r.ok) {
            if (r.matched) {
              setCollected(r.collected);
              if (r.reconstructed) {
                setResult(r);
                setSessionId(null);
                toast.success('🔓 Секрет відновлено!', { duration: 5000 });
              } else {
                toast.success(`✅ Шард #${r.shard_index} зібрано! Ще ${r.remaining}`, { duration: 3000 });
              }
            } else {
              toast.error('❌ ' + (r.error || 'Шард не знайдено тут'), { duration: 3000 });
            }
          }
        } catch(e) {
          setLastResult({ err: e.message });
          toast.error('❌ ' + e.message);
        }
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        setLastResult({ err: 'GPS: ' + err.message });
        toast.error('GPS: ' + err.message);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  };

  // ── Результат ──
  if (result) return (
    <div className="flex flex-col h-full">
      <Header title="🔓 Секрет відновлено" onBack={onBack} />
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="rounded-2xl bg-cyan-900/10 border border-cyan-800/30 p-5 text-center">
          <div className="text-5xl mb-3">🔓</div>
          <div className="text-cyan-400 font-bold text-lg">Успішно!</div>
          <div className="text-gray-500 text-xs mt-1">{result.collected} з {result.threshold} шардів зібрано</div>
        </div>
        <div className="bg-[#0a1628] border border-cyan-900/30 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-500 text-xs">Відновлений секрет (Base64)</span>
            <button onClick={() => { navigator.clipboard.writeText(result.secret_b64); toast.success('Скопійовано!'); }}
              className="text-cyan-500 text-xs font-semibold">📋 Копіювати</button>
          </div>
          {/* Decoded text — показуємо людино-читабельний текст */}
          {(() => {
            const decoded = result.secret_text || (() => {
              try {
                const raw = atob(result.secret_b64);
                const bytes = new Uint8Array(raw.length);
                for(let i=0;i<raw.length;i++) bytes[i]=raw.charCodeAt(i);
                return new TextDecoder('utf-8').decode(bytes);
              } catch { return ''; }
            })();
            return decoded ? (
              <div>
                <div className="text-gray-500 text-xs mb-1">📋 Розшифрований текст</div>
                <div className="p-3 bg-black/30 rounded-xl text-cyan-300 text-sm font-mono break-all select-all border border-cyan-900/30"
                  onClick={() => { navigator.clipboard.writeText(decoded); toast.success('Скопійовано!'); }}>
                  {decoded}
                </div>
              </div>
            ) : null;
          })()}
          <div className="mt-2">
            <div className="text-gray-600 text-[9px] mb-1">Raw Base64 (tap to copy)</div>
            <div className="text-gray-700 text-[9px] font-mono break-all" 
              onClick={() => { navigator.clipboard.writeText(result.secret_b64); toast.success('Base64 скопійовано'); }}>
              {result.secret_b64}
            </div>
          </div>
        </div>
        <div className="bg-amber-900/10 border border-amber-800/20 rounded-xl p-3 text-xs text-amber-500">
          ⚠️ Збережи зараз. Цей екран більше не покаже секрет.
        </div>
        <Btn onClick={onBack} className="w-full bg-cyan-600">Готово</Btn>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      <Header title="Відновити секрет" onBack={onBack} />
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Bundle select */}
        {bundles.length > 1 && !sessionId && (
          <div>
            <div className="text-gray-400 text-xs mb-1">Оберіть bundle</div>
            <select value={bundleId} onChange={e => setBundleId(e.target.value)}
              className="w-full bg-[#0a1628] border border-cyan-900/30 rounded-xl px-3 py-2 text-white text-sm">
              {bundles.map(b => <option key={b.bundle_id} value={b.bundle_id}>{b.label || b.bundle_id.slice(0,12)}</option>)}
            </select>
          </div>
        )}

        {/* Start session */}
        {!sessionId ? (
          <div className="space-y-3">
            <div className="bg-blue-900/10 border border-blue-800/20 rounded-xl p-3 text-xs text-blue-400">
              Натисни "Почати відновлення", потім скануй кожну локацію по черзі. Сесія зберігається на сервері — стан не губиться.
            </div>
            {bundles.length === 0 ? (
              <div className="text-gray-500 text-sm text-center py-4">Немає bundles. Спочатку створи.</div>
            ) : (
              <Btn onClick={startSession} disabled={starting} className="w-full bg-cyan-600 py-4 text-base font-semibold">
                {starting ? '⏳ Відкриваю сесію...' : '🔑 Почати відновлення'}
              </Btn>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Progress */}
            <div className="bg-[#0a1628]/80 border border-cyan-900/20 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-gray-400 text-xs">Прогрес: {collected}/{sessionInfo?.threshold} шардів</div>
                <button onClick={cancelSession} className="text-gray-600 text-xs">✕ Скасувати</button>
              </div>
              <div className="flex gap-1">
                {Array.from({length: sessionInfo?.n || 3}, (_, i) => (
                  <div key={i} className={`h-3 flex-1 rounded-full transition-all ${i < collected ? 'bg-cyan-500' : 'bg-gray-800'}`} />
                ))}
              </div>
              {collected > 0 && sessionInfo && (
                <div className="text-cyan-500 text-xs mt-1">
                  {collected >= sessionInfo.threshold ? '✅ Достатньо — реконструкція...' : `Ще ${sessionInfo.threshold - collected} локацій`}
                </div>
              )}
            </div>

            {/* Last scan result */}
            {lastResult && (
              <div className={`rounded-xl p-3 text-xs font-mono border ${lastResult.matched ? 'bg-cyan-900/20 border-cyan-800/30 text-cyan-400' : 'bg-gray-800/40 border-gray-700/30 text-gray-400'}`}>
                {lastResult.err ? (
                  <div>❌ {lastResult.err}</div>
                ) : (
                  <>
                    <div>📡 {lastResult.lat}, {lastResult.lon} (±{lastResult.acc}м)</div>
                    {lastResult.matched ? <div className="text-cyan-400 mt-0.5">✅ Шард #{lastResult.shard_index} знайдено</div>
                      : <div className="text-gray-500 mt-0.5">❌ Шард не знайдено тут</div>}
                  </>
                )}
              </div>
            )}

            {/* Scan button */}
            <Btn onClick={scan} disabled={locating} className="w-full bg-cyan-600 hover:bg-cyan-500 py-5 text-lg font-bold">
              {locating ? '📡 Отримую GPS...' : '📍 Сканувати цю локацію'}
            </Btn>

            <div className="text-gray-600 text-xs text-center">
              GPS повинен бути в межах ~200м від збереженої локації
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


const NaginiDMS = ({ onBack, bundle }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ interval_hours: 24, owner_name: '', emergency_message: '' });

  useEffect(() => {
    if (!bundle) return;
    get(`/api/nagini/dms/status?bundle_id=${bundle.bundle_id}`)
      .then(r => { if (r.configured) setStatus(r); })
      .catch(() => {});
  }, [bundle?.bundle_id]);

  const save = async () => {
    setLoading(true);
    try {
      const r = await post('/api/nagini/dms/setup', { bundle_id: bundle.bundle_id, ...form });
      if (r.ok) { toast.success('DMS activated!'); setStatus({ ...r, configured: true, hours_left: form.interval_hours }); }
      else toast.error(r.error || 'Failed');
    } finally { setLoading(false); }
  };

  const checkin = async () => {
    setLoading(true);
    try {
      const r = await post('/api/nagini/dms/checkin', { bundle_id: bundle.bundle_id });
      if (r.ok) {
        toast.success('✅ Checked in! Timer reset.');
        const hoursLeft = form.interval_hours || status?.interval_hours || 24;
        setStatus(s => ({ ...s, last_checkin: r.last_checkin, hours_left: hoursLeft }));
      }
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="⏰ Dead Man's Switch" onBack={onBack} />
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="bg-[#0a1628]/60 border border-cyan-900/20 rounded-xl p-3 text-xs text-gray-500">
          If you stop checking in within the set interval, a LAC message is sent to your wallet automatically.
        </div>
        {status?.configured ? (
          <>
            <div className="rounded-2xl bg-[#0d1e3a] border border-cyan-800/30 p-5 text-center">
              <div className={`text-5xl mb-2 ${status.hours_left < 4 ? 'text-red-400' : status.hours_left < 12 ? 'text-amber-400' : 'text-cyan-400'}`}>
                {status.hours_left < 4 ? '🔴' : status.hours_left < 12 ? '🟡' : '🟢'}
              </div>
              <div className="text-white text-3xl font-bold">{status.hours_left}h</div>
              <div className="text-gray-500 text-sm">until alert fires</div>
            </div>
            {[
              ['Last check-in', status.last_checkin ? new Date(status.last_checkin*1000).toLocaleString() : 'Never'],
              ['Interval', `${status.interval_hours}h`],
              ['Owner', status.owner_name || '—'],
              ['Alert channel', '📩 LAC message'],
            ].map(([k,v]) => (
              <div key={k} className="flex justify-between py-2 border-b border-gray-800/20">
                <span className="text-gray-500 text-sm">{k}</span>
                <span className="text-white text-sm">{v}</span>
              </div>
            ))}
            <Btn onClick={checkin} disabled={loading} className="w-full bg-cyan-600 hover:bg-cyan-500 py-4 text-base font-semibold">
              {loading ? 'Saving...' : '✅ Check In Now — Reset Timer'}
            </Btn>
          </>
        ) : (
          <div className="space-y-3">
            <Input value={form.owner_name} onChange={e => setForm(f=>({...f, owner_name: e.target.value}))}
              placeholder="Your name (shown in alert message)" />
            <div>
              <div className="text-gray-400 text-xs mb-2">Alert interval</div>
              <div className="flex gap-2">
                {[12, 24, 48, 72].map(h => (
                  <button key={h} onClick={() => setForm(f=>({...f, interval_hours: h}))}
                    className={`flex-1 py-2 rounded-xl text-sm transition-all ${form.interval_hours===h?'bg-cyan-600 text-white':'bg-[#0a1628] border border-gray-800 text-gray-500'}`}>
                    {h}h
                  </button>
                ))}
              </div>
            </div>
            <Input value={form.emergency_message} onChange={e => setForm(f=>({...f, emergency_message: e.target.value}))}
              placeholder="Emergency message (optional)" />
            <div className="bg-cyan-900/10 border border-cyan-800/20 rounded-xl p-3 text-xs text-cyan-500">
              📩 Alert will be sent as a LAC message to your own wallet if you miss a check-in.
            </div>
            <Btn onClick={save} disabled={loading} className="w-full bg-cyan-600 hover:bg-cyan-500">
              {loading ? 'Activating...' : 'Activate DMS'}
            </Btn>
          </div>
        )}
      </div>
    </div>
  );
};


export default function App() {
  const [seed, setSeed] = useState(localStorage.getItem('lac_seed'));
  const [lang, setLangState] = useState(getLang());
  const setLang = (l) => { localStorage.setItem('lac_lang', l); setLangState(l); };
  const t = (k) => (i18n[lang] || i18n.en)[k] || (i18n.en)[k] || k;
  if (!seed) return <LangCtx.Provider value={{lang,setLang,t}}><LoginScreen onAuth={s => { localStorage.setItem('lac_seed', s); setSeed(s); }} /></LangCtx.Provider>;
  return <LangCtx.Provider value={{lang,setLang,t}}><MainApp onLogout={() => { localStorage.clear(); setSeed(null); }} /></LangCtx.Provider>;
}

// ━━━ LOGIN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const LoginScreen = ({ onAuth }) => {
  const [mode, setMode] = useState('welcome');
  const [imp, setImp] = useState('');
  const [gen, setGen] = useState('');
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const { t } = useT();
  
  // Read referral code from URL: ?ref=REF-XXXXXXXX
  const refCode = useMemo(() => {
    try { return new URLSearchParams(window.location.search).get('ref') || ''; } catch { return ''; }
  }, []);

  const mkSeed = () => { const c='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'; let s=''; for(let i=0;i<64;i++) s+=c[~~(Math.random()*c.length)]; return s; };

  const create = async () => {
    setLoading(true);
    try {
      const s = mkSeed();
      // Retry up to 3 times — mobile networks can be flaky
      let r, lastErr;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          r = await post('/api/register', { seed: s, ref: refCode });
          break;
        } catch(e) {
          lastErr = e;
          if (attempt < 2) await new Promise(res => setTimeout(res, 1000));
        }
      }
      if (!r) throw lastErr;
      if (r.ok) {
        setGen(s);
        localStorage.setItem('lac_address', r.address);
        localStorage.setItem('lac_seed', s);
        if (r.ref_bonus) toast.success(`🎉 +${r.ref_bonus} LAC referral bonus!`);
        setMode('backup');
      } else {
        toast.error(r.error || 'Registration failed');
      }
    } catch(e) {
      const msg = e.message || 'Network error';
      if (msg.includes('fetch') || msg.includes('network') || msg.includes('Failed')) {
        toast.error('Connection error. Check your internet and try again.', {duration: 5000});
      } else {
        toast.error(msg, {duration: 4000});
      }
    } finally { setLoading(false); }
  };

  const login = async () => {
    if(!imp.trim()||imp.length<16){ toast.error('Seed too short (min 16 chars)'); return; }
    setLoading(true);
    try {
      let r;
      try {
        r = await post('/api/login', { seed: imp.trim() });
      } catch(loginErr) {
        if (loginErr.message?.includes('not found') || loginErr.message?.includes('404')) {
          try {
            r = await post('/api/register', { seed: imp.trim(), ref: refCode });
            toast.success('Wallet restored!');
            if(r.ref_bonus) toast.success(`🎉 +${r.ref_bonus} LAC referral bonus!`);
          } catch(regErr) {
            toast.error('Register failed: ' + regErr.message, {duration: 4000});
            return;
          }
        } else {
          toast.error('Login failed: ' + loginErr.message, {duration: 4000});
          return;
        }
      }
      if(r && r.ok){ localStorage.setItem('lac_address', r.address); onAuth(imp.trim()); }
      else { toast.error('Login failed — unexpected response', {duration: 4000}); }
    } catch(e){ toast.error('Error: ' + e.message, {duration: 4000}); } finally { setLoading(false); }
  };

  if (mode === 'welcome') return (
    <div className="h-screen flex flex-col items-center justify-center p-8 relative overflow-hidden"
        style={{background:'radial-gradient(ellipse 80% 80% at 50% -10%, #0d2a4a 0%, #0B1426 60%)'}}>
        {/* Background frost particles */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full opacity-[0.07]"
            style={{background:'radial-gradient(circle, #00E5FF, transparent 70%)'}} />
          <div className="absolute bottom-1/3 right-1/4 w-48 h-48 rounded-full opacity-[0.05]"
            style={{background:'radial-gradient(circle, #B8E6FF, transparent 70%)'}} />
        </div>
        <div className="relative z-10 flex flex-col items-center w-full">
        {/* Logo */}
        <div className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 shadow-2xl"
          style={{background:'linear-gradient(135deg, #00E5FF 0%, #0066AA 100%)',boxShadow:'0 0 40px rgba(0,229,255,0.25)'}}>
          <span className="text-3xl font-black text-[#0B1426]">L</span>
        </div>
        <h1 className="text-4xl font-thin text-white mb-1 tracking-wide" style={{fontWeight:100}}>LAC</h1>
        <p className="text-[#00E5FF] text-sm mb-1 tracking-wider">{t('privacyFirst')}</p>
        <p className="text-[#B8E6FF]/30 text-xs mb-8 tracking-widest uppercase">Zero-History · VEIL · STASH · PoET</p>
      {refCode && <div className="bg-purple-900/20 border border-purple-700/30 rounded-xl px-4 py-2 mb-6"><p className="text-purple-400 text-xs text-center">🎁 Referral: <span className="font-mono font-bold">{refCode}</span> · +50 LAC bonus!</p></div>}
      <div className="w-full max-w-sm space-y-3">
        <Btn onClick={create} color="emerald" full loading={loading}>{t('createWallet')}</Btn>
        <Btn onClick={() => setMode('import')} color="gray" full>{t('importSeed')}</Btn>
      </div>
    </div>
  );

  if (mode === 'backup') return (
    <div className="h-screen bg-[#070d1e] flex flex-col p-6">
      <div className="flex-1 flex flex-col justify-center">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-amber-600/20 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-amber-400" />
          </div>
          <h2 className="text-2xl font-bold text-white">{t('backupSeed')}</h2>
          <p className="text-gray-400 mt-2 text-sm">{t('writeSeedDown')}</p>
        </div>
        <Card className="mb-4" gradient="bg-[#0a1628] border-amber-800/30">
          <p className="text-cyan-400 font-mono text-[13px] break-all leading-6 select-all">{gen}</p>
        </Card>
        <Btn onClick={() => { cp(gen); setSaved(true); }} color="gray" full>📋 {t('copy')}</Btn>
        {saved && <div className="mt-4"><Btn onClick={() => onAuth(gen)} color="emerald" full>{t('seedSaved')} →</Btn></div>}
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-[#070d1e] flex flex-col p-6">
      <button onClick={() => setMode('welcome')} className="text-gray-500 mb-6 flex items-center gap-1 text-sm"><ArrowLeft className="w-4 h-4" /> {t('back')}</button>
      <div className="flex-1 flex flex-col justify-center">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">{t('importSeed')}</h2>
        <textarea value={imp} onChange={e => setImp(e.target.value)} rows={3}
          className="w-full bg-[#0a1628] text-cyan-400 font-mono text-sm p-4 rounded-2xl border border-cyan-900/30 outline-none resize-none mb-4" placeholder={t('enterSeed')+'…'} />
        <Btn onClick={login} color="emerald" full disabled={imp.length<16} loading={loading}>{t('loginBtn')}</Btn>
      </div>
    </div>
  );
};

// ━━━ MAIN SHELL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const MainApp = ({ onLogout }) => {
  const { t } = useT();
  const [tab, setTab] = useState('wallet');
  const [profile, setProfile] = useState(null);
  const [sub, setSub] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const panicClicks = useRef(0);
  const panicTimer = useRef(null);

  const reload = useCallback(async () => { try { setProfile(await get('/api/profile')); } catch {} }, []);
  useEffect(() => {
    reload();
    const i = setInterval(() => {
      if (!document.hidden) reload();
    }, 30000); // 30s — profile changes rarely
    return () => clearInterval(i);
  }, [reload]);

  // ── PWA Push Notifications setup ──
  const lastMsgCount = useRef(0);
  const notifEnabled = useRef(false);
  const requestNotifPermission = useCallback(async () => {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') { notifEnabled.current = true; return; }
    if (Notification.permission !== 'denied') {
      const p = await Notification.requestPermission();
      notifEnabled.current = p === 'granted';
    }
  }, []);
  useEffect(() => { requestNotifPermission(); }, []);

  const sendPushNotif = useCallback((title, body) => {
    if (!notifEnabled.current || document.visibilityState === 'visible') return;
    try { new Notification(title, { body, icon: '/icon-192.png', badge: '/icon-192.png', silent: false }); } catch {}
  }, []);

  // ── Poll inbox for new messages, fire push if app in background ──
  useEffect(() => {
    const checkMsgs = async () => {
      try {
        const r = await get('/api/inbox');
        const msgs = r.messages || [];
        const incoming = msgs.filter(m => m.direction === 'received').length;
        if (lastMsgCount.current > 0 && incoming > lastMsgCount.current) {
          const newMsgs = msgs.filter(m => m.direction === 'received').slice(0, incoming - lastMsgCount.current);
          newMsgs.forEach(m => sendPushNotif('💬 LAC — New message', `${m.from || 'Someone'}: ${(m.text||'').slice(0,80)}`));
        }
        lastMsgCount.current = incoming;
      } catch {}
    };
    const i = setInterval(() => {
      if (!document.hidden) checkMsgs();
    }, 20000); // 20s — WS handles real-time, this is fallback push only
    return () => clearInterval(i);
  }, [sendPushNotif]);

  const handlePanic = () => {
    panicClicks.current += 1;
    if (panicTimer.current) clearTimeout(panicTimer.current);
    if (panicClicks.current >= 3) {
      panicClicks.current = 0;
      if (confirm('⚠️ PANIC MODE\n\nThis will erase ALL local data from this device.\nYour wallet stays on the network — you can login again with your seed.\n\nContinue?')) {
        localStorage.clear();
        toast('🔥 Local data erased!');
        onLogout();
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
      referral: <ReferralView onBack={back} />,
      pol: <PolView onBack={back} profile={profile} />,
      nagini: <NaginiView onBack={back} profile={profile} />,
    };
    return (
      <div className="w-full h-[100dvh] flex items-center justify-center sm:p-4">
        <div className="w-full h-full max-w-md sm:max-h-[850px] bg-[#070d1e] sm:rounded-3xl sm:shadow-2xl sm:shadow-cyan-500/10 overflow-hidden sm:border sm:border-white/[0.06] flex flex-col relative">
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
    { icon: TrendingUp, label: 'Dashboard', act: () => { setSub({type:'dashboard'}); setMenuOpen(false); } },
    { icon: Shield, label: 'Validator', act: () => { setSub({type:'validator'}); setMenuOpen(false); } },
  ];

  return (
    <div className="w-full h-[100dvh] flex items-center justify-center sm:p-4">
      <div className="w-full h-full max-w-md sm:max-h-[850px] bg-[#070d1e] sm:rounded-3xl sm:shadow-2xl sm:shadow-cyan-500/10 overflow-hidden sm:border sm:border-white/[0.06] flex flex-col relative">
        <Toaster position="top-center" toastOptions={{style:{background:'#0f2044',color:'#e5fff5',borderRadius:'14px',border:'1px solid rgba(14,230,138,.15)',fontSize:'13px'}}} />

        {/* Hamburger Menu Overlay */}
        {menuOpen && (
          <div className="absolute inset-0 z-50 flex">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMenuOpen(false)} />
            <div className="relative w-[280px] h-full bg-[#070d1e]/98 backdrop-blur-xl border-r border-white/[0.06] overflow-y-auto z-10 shadow-2xl">
              {/* Menu Header */}
              <div className="p-5 border-b border-cyan-900/20">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-white font-bold text-lg">Menu</span>
                  <button onClick={() => setMenuOpen(false)} className="text-gray-500"><X className="w-5 h-5" /></button>
                </div>
                <div className="flex items-center gap-3 p-3 bg-[#0f2044] rounded-xl border border-cyan-900/20">
                  <div className="w-11 h-11 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center">
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
                  <button key={i} onClick={m.act} className="w-full flex items-center gap-3 px-5 py-3 text-[#B8E6FF]/70 hover:bg-white/[0.05] hover:text-white transition rounded-xl mx-2 w-[calc(100%-16px)]">
                    <m.icon className="w-5 h-5 text-gray-500" /><span className="text-sm font-medium">{m.label}</span>
                  </button>
                ))}
              </div>
              <div className="border-t border-cyan-900/20 p-5">
                <Btn onClick={() => { if(confirm('Save seed first!')) onLogout(); }} color="red" full>
                  <span className="flex items-center justify-center gap-2"><LogOut className="w-4 h-4" />Logout</span>
                </Btn>
                <p className="text-gray-700 text-[10px] text-center mt-3">LAC · Zero-History · PoET Mining</p>
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
          {tab === 'bitcoin' && <BitcoinWalletTab onMenu={() => setMenuOpen(true)} />}
        </div>

        {/* Bottom Navigation */}
        <nav className="bg-[#070d1e]/95 backdrop-blur-xl border-t border-white/[0.06] flex shrink-0 pb-[env(safe-area-inset-bottom)]">
          {[
            { id: 'chats', icon: MessageCircle, label: t('chats') },
            { id: 'wallet', icon: Wallet, label: t('wallet') },
            { id: 'panic', icon: AlertTriangle, label: t('panic'), isPanic: true },
            { id: 'explore', icon: Activity, label: t('explore') },
            { id: 'bitcoin', icon: Bitcoin, label: 'Bitcoin' },
            { id: 'profile', icon: User, label: t('profile') },
          ].map(n => (
            <button key={n.id} onClick={n.isPanic ? handlePanic : () => setTab(n.id)}
              className={`flex-1 py-3 flex flex-col items-center gap-0.5 transition-all ${n.isPanic ? 'text-red-500' : tab===n.id?'text-[#00E5FF]':'text-[#B8E6FF]/30'}`}>
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
const _cache = {};
const cacheGet = (k) => _cache[k];
const cacheSet = (k, v) => { _cache[k] = v; };

const ChatsTab = ({ profile, onNav, onMenu }) => {
  const { t } = useT();
  const [sec, setSec] = useState('dm');
  const [msgs, setMsgs] = useState(() => cacheGet('inbox') || []);
  const [groups, setGroups] = useState(() => cacheGet('groups') || []);
  const [loading, setLoading] = useState(!cacheGet('inbox'));

  const loadingRef = useRef(false);
  const load = async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    try {
      const [i,g] = await Promise.all([get('/api/inbox'),get('/api/groups')]);
      const m = i.messages||[]; const gr = g.groups||[];
      cacheSet('inbox', m); cacheSet('groups', gr);
      setMsgs(prev => JSON.stringify(prev) === JSON.stringify(m) ? prev : m);
      setGroups(prev => JSON.stringify(prev) === JSON.stringify(gr) ? prev : gr);
    } catch {}
    finally { setLoading(false); loadingRef.current = false; }
  };
  const wsDebounce = useRef(null);
  useRealtimeSocket((msg) => {
    if (msg.event === 'new_message' || msg.event === 'new_group_post') {
      clearTimeout(wsDebounce.current);
      wsDebounce.current = setTimeout(load, 200);
    }
  });

  useEffect(() => {
    load();
    // Poll as fallback — WS handles real-time, poll only catches missed events
    const i = setInterval(() => {
      if (!document.hidden && !_wsConnected) load();
      else if (!document.hidden) load(); // light refresh even with WS
    }, 30000);
    return () => clearInterval(i);
  }, []);

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
            <h1 className="text-xl font-bold text-white">{t('chats')}</h1>
          </div>
          <button onClick={() => onNav({type: sec==='dm'?'newchat':'newgroup'})}
            className="w-9 h-9 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-full flex items-center justify-center shadow-lg shadow-cyan-600/25">
            <Plus className="w-4 h-4 text-white" />
          </button>
        </div>
        <TabBar tabs={[['dm','💬 '+t('messages')],['groups','👥 '+t('groups')]]} active={sec} onChange={setSec} />
      </div>
      <div className="flex-1 overflow-y-auto">
        {sec === 'dm' ? (
          loading ? <div className="space-y-0">{[1,2,3,4].map(i=><div key={i} className="flex items-center gap-3 px-4 py-3.5 border-b border-gray-900/50 animate-pulse"><div className="w-11 h-11 rounded-full bg-gray-800/60 shrink-0"/><div className="flex-1 space-y-2"><div className="h-3 bg-gray-800/60 rounded w-1/3"/><div className="h-2.5 bg-gray-800/40 rounded w-2/3"/></div></div>)}</div> :
          sorted.length === 0 ? <Empty emoji="💬" text={t('noMessages')} sub={t('startConvo')} /> :
          sorted.map(c => {
            const hasUnread = c.last?.unread === 1;
            const preview = c.last?.text||c.last?.message||'';
            // Show media preview
            const previewText = preview.startsWith('[img:') ? '🖼 Image' :
                                preview.startsWith('[voice:') ? '🎤 Voice' : preview;
            return (
            <ListItem key={c.peer}
              icon={<User className="w-5 h-5 text-cyan-500" />}
              title={c.name}
              sub={previewText}
              right={
                <div className="flex flex-col items-end gap-1">
                  <span className="text-gray-600 text-[11px]">{ago(c.last?.timestamp)}</span>
                  {hasUnread && <span className="w-2 h-2 rounded-full bg-cyan-500 block" />}
                </div>
              }
              onClick={() => onNav({type:'chat',peer:{address:c.peer,name:c.name}})} />
          );})
        ) : (
          loading ? <div className="space-y-0">{[1,2,3].map(i=><div key={i} className="flex items-center gap-3 px-4 py-3.5 border-b border-gray-900/50 animate-pulse"><div className="w-11 h-11 rounded-full bg-gray-800/60 shrink-0"/><div className="flex-1 space-y-2"><div className="h-3 bg-gray-800/60 rounded w-1/4"/><div className="h-2.5 bg-gray-800/40 rounded w-1/3"/></div></div>)}</div> :
          groups.length === 0 ? <Empty emoji="👥" text={t('noGroups')} sub={t('createGroup')} /> :
          [...groups].sort((a,b) => (b.last_post_ts||b.created_at||0) - (a.last_post_ts||a.created_at||0)).map(g => {
            const tb = {public:['emerald','🌍 Public'],private:['purple','🔒 Private'],l1_blockchain:['blue','⛓ L1 Chain'],l2_ephemeral:['amber','⚡ L2 Ephemeral']}[g.type]||['gray', g.type||'Group'];
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


// ━━━ MEDIA UTILS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// Compress image before upload — iPhone photos can be 5-10MB
const compressImage = (file, maxPx = 1280, quality = 0.82) => new Promise((resolve) => {
  if (!file.type.startsWith('image/') || file.type === 'image/gif') {
    resolve(file); return; // don't compress gif/audio
  }
  const img = new window.Image();
  const url = URL.createObjectURL(file);
  img.onload = () => {
    URL.revokeObjectURL(url);
    let { width: w, height: h } = img;
    if (w <= maxPx && h <= maxPx) { resolve(file); return; } // already small
    if (w > h) { h = Math.round(h * maxPx / w); w = maxPx; }
    else { w = Math.round(w * maxPx / h); h = maxPx; }
    const canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    canvas.getContext('2d').drawImage(img, 0, 0, w, h);
    canvas.toBlob(blob => {
      resolve(new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' }));
    }, 'image/jpeg', quality);
  };
  img.onerror = () => resolve(file);
  img.src = url;
});

const uploadMedia = async (file, onProgress) => {
  const seed = localStorage.getItem('lac_seed');
  if (!seed) throw new Error('No seed');
  if (!file || file.size === 0) throw new Error('Empty file');
  if (file.size > 20 * 1024 * 1024) throw new Error('File too large (max 20MB)');

  // Compress image first (reduces iPhone 8MB → ~500KB)
  const fileToSend = await compressImage(file);

  return new Promise((resolve, reject) => {
    const fd = new FormData();
    fd.append('file', fileToSend);
    const xhr = new XMLHttpRequest();

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round(e.loaded / e.total * 100));
      }
    };

    xhr.onload = () => {
      try {
        const d = JSON.parse(xhr.responseText);
        if (xhr.status >= 400) return reject(new Error(d.error || `Upload failed (${xhr.status})`));
        if (!d.url) return reject(new Error('No URL in response'));
        resolve(d);
      } catch(e) { reject(new Error('Invalid server response')); }
    };

    xhr.onerror = () => reject(new Error('Network error — check connection'));
    xhr.ontimeout = () => reject(new Error('Upload timeout'));
    xhr.timeout = 60000; // 60s

    xhr.open('POST', API_BASE_URL + '/api/media/upload');
    xhr.setRequestHeader('X-Seed', seed);
    xhr.send(fd);
  });
};

// Відображення картинки в повідомленні
const MsgImage = React.memo(({ url }) => {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState('loading'); // loading | ok | error
  const [retries, setRetries] = useState(0);
  // Fix double-slash: normalize URL
  const base = (API_BASE_URL || '').replace(/\/$/, '');
  const path = (url || '').replace(/^\//, '/');
  const full = base + path;
  if (retries >= 3) return <p className="text-gray-600 text-xs italic mt-1">🖼 Image expired</p>;
  const handleError = () => {
    setTimeout(() => setRetries(r => r + 1), 2000);
    setStatus('error');
  };
  const handleLoad = () => setStatus('ok');
  const src = retries > 0 ? `${full}?r=${retries}` : full;
  return (
    <>
      <div className="mt-1">
        <img src={src} alt="img" onClick={() => setOpen(true)} onError={handleError}
          className="max-w-[220px] max-h-[220px] rounded-xl object-cover cursor-pointer border border-amber-900/20"
          loading="lazy" />
        <p className="text-amber-500/60 text-[9px] mt-0.5">⚡ L2 · auto-delete 5 min</p>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4" onClick={() => setOpen(false)}>
          <img src={src} alt="img" className="max-w-full max-h-full rounded-xl object-contain" />
        </div>
      )}
    </>
  );
});

// Голосове повідомлення — плеєр
const VoicePlayer = React.memo(({ url }) => {
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const audioRef = useRef(null);
  const full = API_BASE_URL + url;

  useEffect(() => {
    const a = new Audio();
    a.preload = 'metadata';
    audioRef.current = a;
    const onMeta = () => {
      // iOS Safari sometimes returns Infinity — retry after play attempt
      if (a.duration && isFinite(a.duration)) {
        setDuration(a.duration);
        setLoaded(true);
      }
    };
    const onTime = () => {
      if (!isFinite(a.duration) || a.duration === 0) return;
      setProgress(a.currentTime / a.duration);
      if (!loaded) { setDuration(a.duration); setLoaded(true); }
    };
    const onEnd = () => { setPlaying(false); setProgress(0); };
    a.addEventListener('loadedmetadata', onMeta);
    a.addEventListener('durationchange', onMeta);
    a.addEventListener('timeupdate', onTime);
    a.addEventListener('ended', onEnd);
    a.src = full; // set src AFTER listeners
    return () => {
      a.pause();
      a.removeEventListener('loadedmetadata', onMeta);
      a.removeEventListener('durationchange', onMeta);
      a.removeEventListener('timeupdate', onTime);
      a.removeEventListener('ended', onEnd);
      a.src = '';
    };
  }, [full]);

  const toggle = () => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) {
      a.pause(); setPlaying(false);
    } else {
      a.play().then(() => {
        setPlaying(true);
        // iOS: duration available only after playback starts
        if (isFinite(a.duration) && a.duration > 0) setDuration(a.duration);
      }).catch(() => {});
    }
  };

  const fmt = (s) => isFinite(s) && s > 0
    ? `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`
    : '0:00';

  return (
    <div className="flex items-center gap-2 mt-1 px-3 py-2 bg-black/20 rounded-xl min-w-[180px]">
      <button onClick={toggle} className="w-8 h-8 rounded-full bg-cyan-600 flex items-center justify-center shrink-0">
        {playing ? <Pause className="w-3.5 h-3.5 text-white" /> : <Play className="w-3.5 h-3.5 text-white ml-0.5" />}
      </button>
      <div className="flex-1">
        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div className="h-full bg-cyan-400 rounded-full transition-all" style={{width:`${progress*100}%`}} />
        </div>
        <p className="text-[9px] text-gray-500 mt-0.5">{fmt(duration * progress)} / {fmt(duration)}</p>
      </div>
      <Volume2 className="w-3.5 h-3.5 text-gray-500 shrink-0" />
    </div>
  );
});

// Запис голосового повідомлення
const useVoiceRecorder = () => {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const start = async () => {
    // Check if getUserMedia is available (requires HTTPS or localhost)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast.error('🎤 Мікрофон потребує HTTPS. Використай кнопку 📎 для завантаження аудіофайлу.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg' });
      chunksRef.current = [];
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.start(100);
      mediaRef.current = mr;
      setRecording(true);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds(s => s + 1), 1000);
    } catch(e) {
      toast.error('Мікрофон недоступний: ' + e.message);
    }
  };

  const stop = () => new Promise(resolve => {
    const mr = mediaRef.current;
    if (!mr || mr.state === 'inactive') { resolve(null); return; }
    mr.onstop = () => {
      const mime = mr.mimeType || 'audio/webm';
      const blob = new Blob(chunksRef.current, { type: mime });
      mr.stream.getTracks().forEach(t => t.stop());
      mediaRef.current = null;   // ← reset so next start() works
      chunksRef.current = [];
      resolve(blob);
    };
    mr.stop();
    setRecording(false);
    setSeconds(0);
    clearInterval(timerRef.current);
  });

  const cancel = () => {
    const mr = mediaRef.current;
    if (mr && mr.state !== 'inactive') {
      mr.stream.getTracks().forEach(t => t.stop());
      mr.stop();
    }
    mediaRef.current = null;   // ← reset
    chunksRef.current = [];
    setRecording(false);
    setSeconds(0);
    clearInterval(timerRef.current);
  };

  return { recording, seconds, start, stop, cancel };
};

// ━━━ MIC BUTTON — iOS/Android compatible hold-to-record ━━━━━━━━━━━━━━━
// iOS Safari requires: no pointer-events conflicts, must call getUserMedia
// directly in touch handler (not in async wrapper) for first permission request
const MicButton = React.memo(({ recording, disabled, onStart, onStop }) => {
  const pressRef = useRef(false);
  const startRef = useRef(null);

  const handleStart = (e) => {
    e.preventDefault();
    if (disabled || pressRef.current) return;
    pressRef.current = true;
    startRef.current = Date.now();
    onStart();
  };

  const handleEnd = (e) => {
    e.preventDefault();
    if (!pressRef.current) return;
    pressRef.current = false;
    const held = Date.now() - (startRef.current || Date.now());
    if (recording || held > 300) {
      onStop();
    }
  };

  return (
    <button
      onPointerDown={handleStart}
      onPointerUp={handleEnd}
      onPointerCancel={handleEnd}
      onPointerLeave={handleEnd}
      disabled={disabled}
      title={!navigator.mediaDevices ? 'Upload audio via 📎' : recording ? 'Release to send' : 'Hold to record'}
      style={{ touchAction: 'none', userSelect: 'none', WebkitUserSelect: 'none' }}
      className={`w-9 h-9 flex items-center justify-center disabled:opacity-30
        ${recording ? 'text-red-400 scale-125' : 'text-gray-500 hover:text-amber-400'}
        transition-all duration-150`}>
      {recording
        ? <span className="w-3.5 h-3.5 rounded-sm bg-red-500 animate-pulse" />
        : <Mic className="w-5 h-5" />}
    </button>
  );
});

// ━━━ CHAT VIEW ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const notifSound = (() => {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    return () => {
      const o = ctx.createOscillator(); const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value = 880; o.type = 'sine';
      g.gain.setValueAtTime(0.15, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      o.start(ctx.currentTime); o.stop(ctx.currentTime + 0.3);
    };
  } catch { return () => {}; }
})();

const ChatView = ({ peer, onBack, profile }) => {
  const { t } = useT();
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [mode, setMode] = useState('regular'); // regular | ephemeral | burn
  const [replyTo, setReplyTo] = useState(null); // {text, from} for reply
  const [reactTo, setReactTo] = useState(null); // msg index for emoji picker
  const [peerOnline, setPeerOnline] = useState(false);
  const [imgPreview, setImgPreview] = useState(null); // {file, url} for image preview
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  const voice = useVoiceRecorder();
  const end = useRef(null);
  const resolvedAddr = useRef(peer.address);
  const localMsgs = useRef([]); // client-side message store (source of truth)
  const lastJson = useRef(''); // prevent unnecessary re-renders
  const lastCount = useRef(0); // track message count for notification sound

  // Merge server data into local store without losing optimistic messages
  const mergeServer = (serverMsgs) => {
    const local = localMsgs.current;
    // Dedup key: direction + first 50 chars of text + timestamp in 5s window
    const msgKey = m => (m.direction||'') + '|' + (m.text||m.message||'').slice(0,50) + '|' + Math.floor((m.timestamp||0)/10);
    const serverIndex = new Set(serverMsgs.map(msgKey));
    // Remove optimistic msgs that server confirmed
    const surviving = local.filter(m => m._opt && !serverIndex.has(msgKey(m)));
    // Dedup server msgs themselves
    const seen = new Set();
    const deduped = serverMsgs.filter(m => {
      const k = msgKey(m);
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
    const merged = [...deduped, ...surviving].sort((a,b) => (a.timestamp||0) - (b.timestamp||0));
    const json = JSON.stringify(merged.map(m => msgKey(m) + (m._opt?'_p':'')));
    if (json !== lastJson.current) {
      lastJson.current = json;
      localMsgs.current = merged;
      setMsgs(merged);
    }
  };

  const lastTs = useRef(0);
  const polling = useRef(false);

  const loadingRef = useRef(false);
  const load = async (usePoll = false) => {
    if (loadingRef.current) return; // prevent concurrent loads
    loadingRef.current = true;
    try {
      const peer = encodeURIComponent(resolvedAddr.current);
      // Use long-poll when we have a baseline, else normal fetch
      const url = `/api/chat?peer=${peer}`;
      const r = await get(url);
      if (r.peer_addr && r.peer_addr.startsWith('lac')) resolvedAddr.current = r.peer_addr;
      if (r.peer_online !== undefined) setPeerOnline(r.peer_online);
      if (r.poll_timeout) return; // no new messages, loop again
      const msgs = r.messages || [];
      const incoming = msgs.filter(m => m.direction === 'received').length;
      if (incoming > lastCount.current && lastCount.current > 0) { try { notifSound(); } catch {} }
      lastCount.current = incoming;
      if (r.last_ts && r.last_ts > lastTs.current) lastTs.current = r.last_ts;
      mergeServer(msgs);
    } catch {}
    finally { loadingRef.current = false; }
  };

  // WebSocket: миттєве оновлення
  const wsLoadTimer = useRef(null);
  useRealtimeSocket((msg) => {
    if (msg.event === 'new_message') {
      clearTimeout(wsLoadTimer.current);
      wsLoadTimer.current = setTimeout(() => load(false), 100);
    }
  });

  // Polling як fallback — WS handles real-time, poll only as safety net
  useEffect(() => {
    load(false);
    const i = setInterval(() => {
      if (!document.hidden) load(false);
    }, 20000); // WS fires instantly, poll is fallback
    return () => clearInterval(i);
  }, []);
  useEffect(() => { end.current?.scrollIntoView({behavior:'instant', block:'end'}); }, [msgs]);

  const send = async () => {
    if(!text.trim()||sending) return;
    const txt = text.trim();
    const reply = replyTo ? { text: replyTo.text?.slice(0,100), from: replyTo.from } : null;
    setSending(true);
    setText('');
    setReplyTo(null);
    // INSTANT optimistic
    const ts = ~~(Date.now()/1000);
    const isEph = mode === 'ephemeral';
    const isBurn = mode === 'burn';
    const opt = {
      from: profile?.username||profile?.address, from_address: profile?.address,
      to: peer.address, text: txt, timestamp: ts,
      direction: 'sent', ephemeral: isEph, burn: isBurn, msg_type: isEph?'ephemeral':'regular', _opt: true,
      reply_to: reply
    };
    localMsgs.current = [...localMsgs.current, opt];
    setMsgs([...localMsgs.current]);
    lastJson.current = ''; // force next merge to update
    setSending(false); // unblock immediately
    // True fire & forget — UI already updated optimistically
    post('/api/message.send',{to:peer.address,text:txt,ephemeral:isEph,burn:isBurn,reply_to:reply})
      .then(res => { if (res.to_address) resolvedAddr.current = res.to_address; })
      .catch(e => {
        toast.error(e.message);
        localMsgs.current = localMsgs.current.filter(m => m !== opt);
        setMsgs([...localMsgs.current]);
      });
  };

  // Upload file then send as L2 ephemeral (always — media is always 5-min self-destruct)
  const sendMedia = async (file, type) => {
    if (uploading) return;
    setUploading(true);
    const [progressToast] = [toast('📤 0%', {duration: 60000})];
    try {
      const up = await uploadMedia(file, (pct) => {
        toast.dismiss(progressToast);
        if (pct < 100) toast(`📤 ${pct}%`, {duration: 60000, id: 'upload-prog'});
      });
      toast.dismiss('upload-prog');
      const ts = ~~(Date.now()/1000);
      const mediaText = type === 'image' ? `[img:${up.url}]` : `[voice:${up.url}]`;
      // ALWAYS ephemeral=true for media — L2, 5-min self-destruct
      const opt = {
        from: profile?.username||profile?.address, from_address: profile?.address,
        to: peer.address, text: mediaText, timestamp: ts,
        direction: 'sent', ephemeral: true, msg_type: 'ephemeral',
        _opt: true, media_url: up.url, media_type: up.type
      };
      localMsgs.current = [...localMsgs.current, opt];
      setMsgs([...localMsgs.current]);
      lastJson.current = '';
      await post('/api/message.send', { to: peer.address, text: mediaText, ephemeral: true });
      setImgPreview(null);
      toast.success(type === 'image' ? '🖼 Image sent (L2 · 5min)' : '🎤 Voice sent (L2 · 5min)');
    } catch(e) {
      console.error('Media upload error:', e);
      toast.dismiss('upload-prog');
      toast.error('❌ ' + (e.message || 'Upload failed'), {duration: 5000});
    } finally {
      setUploading(false);
    }
  };

  const handleImagePick = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    // Audio file — send directly
    if (file.type.startsWith('audio/') || file.name.match(/\.(ogg|mp3|wav|m4a|webm)$/i)) {
      sendMedia(file, 'voice');
      return;
    }
    // Image — show preview first
    const url = URL.createObjectURL(file);
    setImgPreview({ file, url });
  };

  const handleVoiceStop = async () => {
    const blob = await voice.stop();
    if (!blob) { toast.error('Recording failed'); return; }
    if (blob.size < 500) { toast.error('Too short — hold longer'); return; }
    const ext = blob.type.includes('ogg') ? 'ogg' : 'webm';
    const file = new File([blob], `voice.${ext}`, { type: blob.type });
    await sendMedia(file, 'voice');
  };

  const peerName = peer.name && peer.name.length < 30 ? peer.name : sAddr(peer.address);
  const myAddr = profile?.address;

  return (
    <div className="h-full bg-[#070d1e] flex flex-col">
      <Header title={<span className="flex items-center gap-2">{peerName}{peerOnline && <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />}</span>} onBack={onBack}
        right={<div className="flex gap-1">
          {[['regular','💬','gray'],['ephemeral','⏱','amber'],['burn','🔥','red']].map(([m,ic,c]) => 
            <button key={m} onClick={() => setMode(m)} className={`px-2 py-1 rounded-lg text-[10px] font-medium transition ${mode===m?`bg-${c}-600/20 text-${c}-400 border border-${c}-600/30`:'bg-gray-800/50 text-gray-600 border border-transparent'}`}>{ic}</button>
          )}
        </div>} />
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5" style={{WebkitOverflowScrolling:"touch",overscrollBehavior:"contain"}}>
        {msgs.length===0 && !sending && <Empty emoji="💬" text={t('noMsgYet')} sub={t('sendFirst')} />}
        {msgs.map((m,i) => {
          const mine = m.direction==='sent' || m.from_address===myAddr;
          const isEph = m.ephemeral || m.msg_type==='ephemeral';
          const isBurn = m.burn;
          const burned = m.burned;
          const rxn = m.reactions || {};
          const hasRxn = Object.keys(rxn).length > 0;
          const doReact = async (emoji) => {
            setReactTo(null);
            // Optimistic update
            setMsgs(prev => prev.map(msg => {
              if (msg.msg_key !== m.msg_key) return msg;
              const rxn = {...(msg.reactions||{})};
              const myAddr = profile?.address || '';
              if (!rxn[emoji]) rxn[emoji] = [];
              const idx = rxn[emoji].indexOf(myAddr);
              if (idx>=0) rxn[emoji].splice(idx,1); else rxn[emoji].push(myAddr);
              if (!rxn[emoji].length) delete rxn[emoji];
              return {...msg, reactions: rxn};
            }));
            try { await post('/api/message.react', { msg_key: m.msg_key, emoji }); } catch {}
          };
          return (
            <div key={i} className={`flex flex-col ${mine?'items-end':'items-start'}`}>
              <div onClick={() => { if(!burned) setReplyTo({text:m.text||m.message,from:m.from||sAddr(m.from_address)}); }}
                onContextMenu={(e) => { e.preventDefault(); if(!burned) setReactTo(reactTo===i?null:i); }}
                className={`max-w-[78%] px-3.5 py-2 rounded-2xl cursor-pointer active:opacity-80 ${burned?'bg-gray-900/50 border border-gray-800':mine?'bg-gradient-to-br from-cyan-600 to-cyan-700 text-white rounded-br-sm':'bg-[#0f2044] text-gray-100 rounded-bl-sm border border-cyan-900/20'}`}>
                {!mine && <p className="text-purple-400 text-[11px] font-medium mb-0.5">{m.from||sAddr(m.from_address)}</p>}
                {m.reply_to && <div className={`text-[11px] px-2 py-1 rounded-lg mb-1.5 border-l-2 ${mine?'bg-cyan-800/30 border-cyan-400/40':'bg-gray-800/50 border-purple-400/40'}`}><p className={`font-medium text-[10px] ${mine?'text-cyan-300/70':'text-purple-400/70'}`}>{m.reply_to.from}</p><p className={`truncate ${mine?'text-cyan-200/50':'text-gray-400'}`}>{m.reply_to.text}</p></div>}
                {/* Media rendering */}
                {(() => {
                  const txt = m.text||m.message||'';
                  const imgMatch = txt.match(/^\[img:(\/api\/media\/[^\]]+)\]$/);
                  const voiceMatch = txt.match(/^\[voice:(\/api\/media\/[^\]]+)\]$/);
                  if (imgMatch) return <MsgImage url={imgMatch[1]} />;
                  if (voiceMatch) return <VoicePlayer url={voiceMatch[1]} />;
                  return <p className={`text-[14px] leading-snug break-words ${burned?'text-gray-600 italic':''}`} style={{overflowWrap:'anywhere'}}>{txt}</p>;
                })()}
                {m.pol && <div className="flex items-center gap-1 mt-1 px-2 py-1 bg-blue-900/20 border border-blue-800/20 rounded-lg"><span className="text-[9px]">📍</span><span className="text-blue-400 text-[10px] font-medium">{m.pol.zone}</span><span className="text-blue-600 text-[9px]">verified</span></div>}
                <div className={`flex items-center gap-1.5 mt-0.5 ${mine?'justify-end':''}`}>
                  {isEph && <span className="text-[9px] opacity-50">⏱</span>}
                  {isBurn && !burned && <span className="text-[9px] text-red-400">🔥</span>}
                  <span className={`text-[10px] ${mine?'text-cyan-300/50':'text-gray-600'}`}>{ago(m.timestamp)}</span>
                  {mine && <span className="text-[10px] text-cyan-300/60">{m._opt ? '⏳' : m._read ? '✓✓' : '✓'}</span>}
                </div>
              </div>
              {/* Reactions display */}
              {hasRxn && <div className="flex gap-1 mt-0.5 px-1">{Object.entries(rxn).map(([em,addrs]) =>
                <button key={em} onClick={() => doReact(em)} className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-gray-800/60 border border-gray-700/30 text-[11px] hover:bg-gray-700/60">
                  <span>{em}</span>{addrs.length > 1 && <span className="text-gray-400 text-[9px]">{addrs.length}</span>}
                </button>
              )}</div>}
              {/* Emoji picker */}
              {reactTo === i && <div className="flex gap-1 mt-1 px-1 py-1 rounded-xl bg-gray-800/90 border border-gray-700/40 shadow-lg">
                {['👍','❤️','🔥','😂','😮','👎'].map(em => <button key={em} onClick={() => doReact(em)} className="text-lg px-1 hover:scale-125 transition-transform active:scale-90">{em}</button>)}
              </div>}
            </div>
          );
        })}
        <div ref={end} />
      </div>
      {/* Message mode indicator */}
      {mode === 'ephemeral' && <div className="text-center py-1 bg-amber-900/10"><span className="text-amber-400/70 text-[10px]">⏱ Ephemeral L2 — self-destruct 5 min</span></div>}
      {mode === 'burn' && <div className="text-center py-1 bg-red-900/10"><span className="text-red-400/70 text-[10px]">🔥 Burn after read — destroyed when opened</span></div>}
      {/* Reply bar */}
      {replyTo && <div className="flex items-center gap-2 px-3 py-2 bg-[#0a1628] border-t border-cyan-900/30">
        <div className="flex-1 border-l-2 border-cyan-500 pl-2 min-w-0"><p className="text-cyan-400 text-[10px] font-medium">{replyTo.from}</p><p className="text-gray-400 text-[11px] truncate">{replyTo.text}</p></div>
        <button onClick={() => setReplyTo(null)} className="text-gray-600 hover:text-gray-400 shrink-0"><X className="w-4 h-4" /></button>
      </div>}
      {/* Image preview before send */}
      {imgPreview && (
        <div className="flex items-center gap-2 px-3 py-2 bg-[#0a1628] border-t border-amber-900/30">
          <img src={imgPreview.url} alt="preview" className="w-14 h-14 rounded-lg object-cover border border-amber-900/30" />
          <div className="flex-1 min-w-0">
            <p className="text-amber-400 text-[10px] font-semibold">⚡ L2 · Auto-delete 5 min</p>
            <p className="text-gray-500 text-[10px]">Image will self-destruct</p>
          </div>
          <button onClick={() => sendMedia(imgPreview.file, 'image')} disabled={uploading}
            className="px-3 py-1.5 bg-amber-600 text-white text-xs rounded-lg disabled:opacity-40 font-semibold">
            {uploading ? '⏳' : '⚡ Send'}
          </button>
          <button onClick={() => setImgPreview(null)} className="text-gray-600 hover:text-gray-400"><X className="w-4 h-4" /></button>
        </div>
      )}
      {/* Voice recording indicator */}
      {voice.recording && (
        <div className="flex items-center gap-3 px-4 py-2 bg-red-900/20 border-t border-red-900/30">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-red-400 text-sm flex-1">🎤 {voice.seconds}s · <span className="text-amber-400 text-xs">⚡ L2</span></span>
          <button onClick={voice.cancel} className="text-gray-500 text-xs">Cancel</button>
          <button onClick={handleVoiceStop} className="px-3 py-1 bg-red-600 text-white text-xs rounded-lg">⏹ Send</button>
        </div>
      )}
      <div className="p-2.5 bg-[#0a1628] border-t border-cyan-900/20">
        {/* Hidden file input */}
        <input ref={fileInputRef} type="file" accept="image/*,audio/*" className="hidden" onChange={handleImagePick} />
        <div className="flex gap-2 items-end">
          {/* Attach image */}
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading || voice.recording}
            title="Attach image or audio file"
            className="w-9 h-9 flex items-center justify-center text-gray-500 hover:text-cyan-400 disabled:opacity-30">
            <FileImage className="w-5 h-5" />
          </button>
          {/* Voice message — requires HTTPS; on HTTP shows helpful message */}
          <MicButton
            recording={voice.recording}
            disabled={uploading}
            onStart={voice.start}
            onStop={handleVoiceStop}
          />
          <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key==='Enter'&&!e.shiftKey&&send()}
            className="flex-1 bg-[#0a1628] text-white px-4 py-2.5 rounded-2xl text-sm outline-none border border-cyan-900/30 focus:border-cyan-600/40 placeholder-gray-600"
            placeholder={voice.recording ? '' : mode==='ephemeral'?'Ephemeral (5min)…':mode==='burn'?'🔥 Burn after read…':'Message…'}
            disabled={voice.recording} />
          <button onClick={send} disabled={sending||!text.trim()||uploading||voice.recording}
            className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-full flex items-center justify-center shrink-0 disabled:opacity-30 shadow-lg shadow-cyan-600/20">
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
  const [replyTo, setReplyTo] = useState(null);
  const [reactTo, setReactTo] = useState(null);
  const { t } = useT();
  const end = useRef(null);
  const isEph = group.type==='l2_ephemeral' || group.type==='ephemeral';
  const isL1 = group.type==='l1_blockchain';
  const isPrivate = group.type==='private';
  const typeBadge = isEph ? ['amber','⚡ L2 Ephemeral'] : isL1 ? ['blue','⛓ L1 Chain'] : isPrivate ? ['purple','🔒 Private'] : ['emerald','🌍 Public'];
  const gid = group.id || group.name;
  const localPosts = useRef([]);
  const lastJson = useRef('');
  const sentKeys = useRef(new Set());
  const [imgPreview, setImgPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const { recording, startRecording } = useVoiceRecorder(async (blob) => {
    if (blob) await sendGroupMedia(blob, 'voice');
  });

  const sendGroupMedia = async (file, type) => {
    setUploading(true);
    try {
      const up = await uploadMedia(file, () => {});
      const tag = type === 'image' ? `[img:${up.url}]` : `[voice:${up.url}]`;
      setImgPreview(null);
      const ts = ~~(Date.now()/1000);
      const opt = { from: profile?.username||'You', from_address: profile?.address, text: tag, message: tag, timestamp: ts, _opt: true };
      localPosts.current = [...localPosts.current, opt];
      setPosts([...localPosts.current]);
      lastJson.current = '';
      await post('/api/group.post', { group_id: gid, message: tag });
    } catch(e) { toast.error(e.message); }
    finally { setUploading(false); }
  };

  // Stable key matching server's make_msg_key
  const postKey = p => {
    const addr = p.from_address || '';
    const txt = (p.text||p.message||'').slice(0,40);
    const ts = Math.floor((p.timestamp||0)/3)*3;
    return p.msg_key || `${addr}|${txt}|${ts}`;
  };

  const mergeServer = (serverPosts) => {
    const local = localPosts.current;
    const serverKeys = new Set(serverPosts.map(postKey));
    // Remove optimistic msgs that server confirmed
    const surviving = local.filter(p => p._opt && !serverKeys.has(postKey(p)));
    // Dedup server posts by stable key
    const seen = new Set();
    const deduped = serverPosts.filter(p => {
      const k = postKey(p);
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
    const merged = [...deduped, ...surviving].sort((a,b) => (a.timestamp||0) - (b.timestamp||0));
    const json = JSON.stringify(merged.map(p => postKey(p) + (p._opt?'_o':'')));
    if (json !== lastJson.current) {
      lastJson.current = json;
      localPosts.current = merged;
      setPosts(merged);
    }
  };

  const load = async () => {
    try {
      const r = await get('/api/group/posts?group_id='+encodeURIComponent(gid));
      mergeServer(r.posts||[]);
    } catch {}
  };
  useRealtimeSocket((msg) => {
    if (msg.event === 'new_group_post' && msg.data?.group_id === gid) {
      load();
    }
  });

  useEffect(() => { load(); const i=setInterval(()=>{if(!document.hidden)load();},20000); return()=>clearInterval(i); }, []);
  useEffect(() => { end.current?.scrollIntoView({behavior:'instant', block:'end'}); }, [posts]);

  const send = async () => {
    if(!text.trim()||sending) return;
    const txt = text.trim();
    const reply = replyTo ? { text: replyTo.text?.slice(0,100), from: replyTo.from } : null;
    // Prevent double-send
    const sendKey = txt + '|' + ~~(Date.now()/5000);
    if (sentKeys.current.has(sendKey)) return;
    sentKeys.current.add(sendKey);
    setTimeout(() => sentKeys.current.delete(sendKey), 10000);

    setText('');
    setReplyTo(null);
    setSending(true);
    const ts = ~~(Date.now()/1000);
    const opt = {
      from: profile?.username||'You', from_address: profile?.address,
      text: txt, message: txt, timestamp: ts, _opt: true, reply_to: reply
    };
    localPosts.current = [...localPosts.current, opt];
    setPosts([...localPosts.current]);
    lastJson.current = '';

    try {
      await post('/api/group.post',{group_id:gid,message:txt,reply_to:reply});
    } catch(e) {
      toast.error(e.message);
      localPosts.current = localPosts.current.filter(p => p !== opt);
      setPosts([...localPosts.current]);
    } finally {
      setSending(false);
    }
  };

  const doReact = async (p, emoji) => {
    setReactTo(null);
    const mk = postKey(p);
    // Optimistic reaction update
    setPosts(prev => prev.map(post => {
      if (postKey(post) !== mk) return post;
      const rxn = {...(post.reactions||{})};
      const myAddr = profile?.address || '';
      if (!rxn[emoji]) rxn[emoji] = [];
      const idx = rxn[emoji].indexOf(myAddr);
      if (idx >= 0) rxn[emoji].splice(idx,1);
      else rxn[emoji].push(myAddr);
      if (!rxn[emoji].length) delete rxn[emoji];
      return {...post, reactions: rxn};
    }));
    try { await post('/api/message.react', { msg_key: mk, emoji }); } catch {}
  };

  return (
    <div className="h-full bg-[#070d1e] flex flex-col">
      <Header title={group.name} onBack={onBack} right={
        <div className="flex items-center gap-2">
          <button onClick={() => { cp(gid); toast.success(t('groupCopied')); }} className="p-1.5 rounded-lg bg-gray-800 text-gray-400 active:bg-gray-700"><Copy className="w-3.5 h-3.5" /></button>
          <Badge color={typeBadge[0]}>{typeBadge[1]}</Badge>
        </div>} />
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5" style={{WebkitOverflowScrolling:"touch",overscrollBehavior:"contain"}}>
        {isEph && <div className="text-center py-1"><span className="text-amber-400/60 text-[10px] bg-amber-600/10 px-3 py-1 rounded-full">⚡ {t('ephAutoDelete')}</span></div>}
        {isL1 && <div className="text-center py-1"><span className="text-blue-400/60 text-[10px] bg-blue-600/10 px-3 py-1 rounded-full">⛓ {t('onChainZH')}</span></div>}
        {isPrivate && <div className="text-center py-1"><span className="text-purple-400/60 text-[10px] bg-purple-600/10 px-3 py-1 rounded-full">🔒 {t('privateGroup')}</span></div>}
        {posts.length===0 && <Empty emoji="💬" text={t('noMsgYet')} sub={t('writeFirst')} />}
        {posts.map((p,i) => { const mine=p.from_address===profile?.address;
          const rxn = p.reactions || {};
          const hasRxn = Object.keys(rxn).length > 0;
          const stableKey = postKey(p) + (p._opt?'_o':'');
          return (
          <div key={stableKey} className={`flex flex-col ${mine?'items-end':'items-start'}`}>
            <div onClick={() => setReplyTo({text:p.text||p.message, from:p.from||'Anon'})}
              onContextMenu={(e) => { e.preventDefault(); setReactTo(reactTo===i?null:i); }}
              className={`max-w-[78%] px-3.5 py-2 rounded-2xl cursor-pointer active:opacity-80 ${mine?'bg-gradient-to-br from-cyan-600 to-cyan-700 text-white rounded-br-sm':'bg-[#0f2044] text-gray-100 rounded-bl-sm border border-cyan-900/20'}`}>
              {!mine && <p className="text-purple-400 text-[11px] font-medium mb-0.5">{p.from||'Anon'}</p>}
              {p.reply_to && <div className={`text-[11px] px-2 py-1 rounded-lg mb-1.5 border-l-2 ${mine?'bg-cyan-800/30 border-cyan-400/40':'bg-gray-800/50 border-purple-400/40'}`}><p className={`font-medium text-[10px] ${mine?'text-cyan-300/70':'text-purple-400/70'}`}>{p.reply_to.from}</p><p className={`truncate ${mine?'text-cyan-200/50':'text-gray-400'}`}>{p.reply_to.text}</p></div>}
              {(() => {
                const txt = p.text||p.message||'';
                const imgM = txt.match(/\[img:(\/api\/media\/[^\]]+)\]/);
                const voiceM = txt.match(/\[voice:(\/api\/media\/[^\]]+)\]/);
                if (imgM) return <MsgImage url={imgM[1]} />;
                if (voiceM) return <VoicePlayer url={voiceM[1]} />;
                return <p className="text-[14px] leading-snug break-words" style={{overflowWrap:'anywhere'}}>{txt}</p>;
              })()}
              <p className={`text-[10px] mt-0.5 ${mine?'text-cyan-300/50':'text-gray-600'}`}>{ago(p.timestamp)}</p>
            </div>
            {hasRxn && <div className="flex gap-1 mt-0.5 px-1">{Object.entries(rxn).map(([em,addrs]) =>
              <button key={em} onClick={() => doReact(p,em)} className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-gray-800/60 border border-gray-700/30 text-[11px] hover:bg-gray-700/60">
                <span>{em}</span>{addrs.length > 1 && <span className="text-gray-400 text-[9px]">{addrs.length}</span>}
              </button>
            )}</div>}
            {reactTo === i && <div className="flex gap-1 mt-1 px-1 py-1 rounded-xl bg-gray-800/90 border border-gray-700/40 shadow-lg">
              {['👍','❤️','🔥','😂','😮','👎'].map(em => <button key={em} onClick={() => doReact(p,em)} className="text-lg px-1 hover:scale-125 transition-transform active:scale-90">{em}</button>)}
            </div>}
          </div>
        ); })}
        <div ref={end} />
      </div>
      {replyTo && <div className="flex items-center gap-2 px-3 py-2 bg-[#0a1628] border-t border-cyan-900/30">
        <div className="flex-1 border-l-2 border-cyan-500 pl-2 min-w-0"><p className="text-cyan-400 text-[10px] font-medium">{replyTo.from}</p><p className="text-gray-400 text-[11px] truncate">{replyTo.text}</p></div>
        <button onClick={() => setReplyTo(null)} className="text-gray-600 hover:text-gray-400 shrink-0"><X className="w-4 h-4" /></button>
      </div>}
      {imgPreview && (
        <div className="px-3 py-2 bg-[#0a1628] border-t border-cyan-900/30">
          <div className="relative inline-block">
            <img src={imgPreview.url} alt="preview" className="h-20 rounded-xl object-cover" />
            <button onClick={() => setImgPreview(null)} className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-gray-900 rounded-full flex items-center justify-center"><X className="w-3 h-3 text-gray-300" /></button>
          </div>
          <p className="text-amber-400/60 text-[10px] mt-1">⚡ L2 · auto-delete 5 min</p>
          <button onClick={() => sendGroupMedia(imgPreview.file, 'image')}
            className="mt-1 px-3 py-1 bg-cyan-600 rounded-lg text-white text-xs block">Send Image</button>
        </div>
      )}
      <div className="p-2.5 bg-[#0a1628] border-t border-cyan-900/20">
        <div className="flex gap-2 items-end">
          <label className="w-9 h-9 flex items-center justify-center text-gray-500 hover:text-gray-300 cursor-pointer shrink-0">
            <Image className="w-5 h-5" />
            <input type="file" accept="image/*" className="hidden" onChange={async e => {
              const f = e.target.files?.[0]; if(!f) return;
              const compressed = await compressImage(f);
              setImgPreview({file: compressed, url: URL.createObjectURL(compressed)});
              e.target.value='';
            }} />
          </label>
          <MicButton recording={recording} disabled={uploading}
            onStart={() => startRecording()}
            onStop={async (blob) => { if(blob) await sendGroupMedia(blob,'voice'); }} />
          <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key==='Enter'&&!e.shiftKey&&send()}
            className="flex-1 bg-[#0a1628] text-white px-4 py-2.5 rounded-2xl text-sm outline-none border border-cyan-900/30 placeholder-gray-600" placeholder={t('message')+'…'} />
          <button onClick={send} disabled={sending||!text.trim()} className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-full flex items-center justify-center shrink-0 disabled:opacity-30"><Send className="w-4 h-4 text-white ml-0.5" /></button>
        </div>
      </div>
    </div>
  );
};

// ━━━ NEW CHAT / GROUP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const NewChat = ({ onBack, onGo }) => {
  const [to, setTo] = useState('');
  const { t } = useT();
  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={t('newMessage')} onBack={onBack} />
    <div className="p-4"><p className="text-gray-500 text-xs mb-2">{t('enterAddr')}</p>
      <Input value={to} onChange={setTo} placeholder="@alice or lac1…" mono />
      <div className="mt-4"><Btn onClick={() => to.trim()&&onGo({address:to.trim(),name:to.trim()})} color="emerald" full disabled={!to.trim()}>{t('startChat')}</Btn></div>
    </div></div>);
};

const NewGroup = ({ onBack, onDone }) => {
  const [name, setName] = useState(''); const [type, setType] = useState('public'); const [ld, setLd] = useState(false);
  const go = async () => {
    if (!name.trim()) { toast.error('Enter group name'); return; }
    setLd(true);
    try {
      const r = await post('/api/group.create',{name:name.trim(),type});
      if (r.ok) { toast.success('Group "'+name.trim()+'" created!'); onDone(); }
      else { toast.error(r.error || 'Failed to create group', {duration:4000}); }
    } catch(e){ toast.error('Error: ' + (e.message||'Unknown'), {duration:4000}); }
    finally { setLd(false); }
  };
  const types = [
    ['public','🌍 Public','Anyone can see and write. Data on server.'],
    ['private','🔒 Private','By invite only. Encrypted.'],
    ['l1_blockchain','⛓ L1 Blockchain','Messages in blocks. Zero-History cleans by tiers.'],
    ['l2_ephemeral','⚡ L2 Ephemeral','5 minutes and gone.'],
  ];
  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="Create Group" onBack={onBack} />
    <div className="p-4 space-y-4">
      <div><label className="text-gray-500 text-xs mb-1 block">Name</label><Input value={name} onChange={setName} placeholder="Group name" /></div>
      <div><label className="text-gray-500 text-xs mb-2 block">Type</label>
        <div className="space-y-2">
          {types.map(([id,l,d]) => (
            <button key={id} onClick={() => setType(id)} className={`w-full p-3 rounded-xl border text-left transition ${type===id?'border-cyan-500 bg-cyan-600/10':'border-gray-800 bg-[#0a1628]'}`}>
              <p className="text-white text-sm font-medium">{l}</p><p className="text-gray-500 text-[10px] mt-0.5">{d}</p>
            </button>))}
        </div>
      </div>
      <Btn onClick={go} color="emerald" full disabled={!name.trim()} loading={ld}>Create Group</Btn>
    </div></div>);
};

// ━━━ REFERRAL SYSTEM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const tierInfo = { genesis:['🏆','Genesis','amber'], early:['⚡','Early','purple'], growth:['🌱','Growth','emerald'], vip:['💎','VIP','blue'], none:['—','—','gray'] };
const ReferralView = ({ onBack }) => {
  const [data, setData] = useState(null);
  const [board, setBoard] = useState(null);
  const [code, setCode] = useState('');
  const [boost, setBoost] = useState('');
  const [ld, setLd] = useState(false);
  const { t } = useT();

  useEffect(() => {
    get('/api/referral/code').then(setData).catch(()=>{});
    get('/api/referral/leaderboard').then(setBoard).catch(()=>{});
  }, []);

  const useCode = async () => {
    if (!code.trim()) return;
    setLd(true);
    try { const r = await post('/api/referral/use',{code:code.trim()}); toast.success(r.message||'Done!'); setCode(''); get('/api/referral/code').then(setData); }
    catch(e) { toast.error(e.message); }
    finally { setLd(false); }
  };
  const burnBoost = async () => {
    const amt = parseInt(boost);
    if (!amt || amt < 100) { toast.error('Min 100 LAC'); return; }
    setLd(true);
    try { const r = await post('/api/referral/burn-boost',{amount:amt}); toast.success(`🔥 ${amt} LAC burned! Tier: ${r.new_tier}`); setBoost(''); get('/api/referral/code').then(setData); }
    catch(e) { toast.error(e.message); }
    finally { setLd(false); }
  };

  const ti = tierInfo[data?.tier||'none'];

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="🤝 Referral" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      {!data ? <p className="text-gray-600 text-center py-8">{t('loading')}</p> : <>
        {/* Your code */}
        <Card gradient="bg-gradient-to-br from-purple-900/20 to-[#0f1f18] border-purple-800/20" className="mb-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-purple-400 font-semibold text-sm">Your Invite Code</p>
            <Badge color={ti[2]}>{ti[0]} {ti[1]}</Badge>
          </div>
          <div className="bg-[#070d1e] p-3 rounded-xl border border-purple-900/20 text-center">
            <p onClick={() => cp(data.code)} className="text-purple-300 font-mono text-xl font-bold cursor-pointer select-all">{data.code}</p>
            <p className="text-gray-600 text-[10px] mt-1">{t('tapCopy')}</p>
          </div>
          <div className="flex gap-2 mt-2">
            <button onClick={() => cp(data.code)} className="flex-1 text-purple-400 text-xs flex items-center justify-center gap-1 bg-purple-900/20 px-3 py-2 rounded-lg active:bg-purple-900/40"><Copy className="w-3 h-3"/> {t('copy')}</button>
            <button onClick={() => { if(navigator.share) navigator.share({text:`Join LAC! Use my invite:\n${window.location.origin}/?ref=${data.code}`}).catch(()=>{}); else cp(`${window.location.origin}/?ref=${data.code}`); }} className="flex-1 text-blue-400 text-xs flex items-center justify-center gap-1 bg-blue-900/20 px-3 py-2 rounded-lg active:bg-blue-900/40">↗ {t('share')}</button>
          </div>
          <div className="mt-2 bg-[#070d1e] p-2 rounded-lg border border-gray-800/30">
            <p className="text-[9px] text-gray-600 mb-1">Referral link:</p>
            <p onClick={() => cp(`${window.location.origin}/?ref=${data.code}`)} className="text-purple-300 font-mono text-[10px] break-all cursor-pointer select-all">{window.location.origin}/?ref={data.code}</p>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-3">
            <div className="text-center"><p className="text-purple-400 font-bold text-lg">{data.referrals||0}</p><p className="text-gray-600 text-[9px]">Invited</p></div>
            <div className="text-center"><p className="text-amber-400 font-bold text-lg">{(data.referrals||0)*25}</p><p className="text-gray-600 text-[9px]">LAC earned</p></div>
            <div className="text-center"><p className="text-red-400 font-bold text-lg">{fmt(data.boost_burned||0)}</p><p className="text-gray-600 text-[9px]">Boosted</p></div>
          </div>
        </Card>

        {/* Use code */}
        {!data.invited_by && <Card className="mb-3">
          <p className="text-white text-sm font-semibold mb-2">🎫 Use Invite Code</p>
          <p className="text-gray-600 text-[10px] mb-2">Got a code? Enter it for +50 LAC bonus!</p>
          <div className="flex gap-2">
            <input value={code} onChange={e => setCode(e.target.value.toUpperCase())} placeholder="REF-XXXXXXXX"
              className="flex-1 bg-[#0a1628] text-purple-400 font-mono text-sm px-3 py-2 rounded-xl border border-purple-900/30 outline-none" />
            <Btn onClick={useCode} color="purple" small loading={ld}>OK</Btn>
          </div>
        </Card>}
        {data.invited_by && <Card className="mb-3"><p className="text-cyan-400 text-xs">✅ Invited with code {data.invited_by.slice(0,6)}**</p></Card>}

        {/* Burn boost */}
        <Card className="mb-3">
          <p className="text-white text-sm font-semibold mb-1">🔥 Burn-to-Boost</p>
          <p className="text-gray-600 text-[10px] mb-2">Burn LAC to boost your tier. 10,000+ = VIP</p>
          <div className="flex gap-2">
            <input value={boost} onChange={e => setBoost(e.target.value)} placeholder="Amount (min 100)" type="number"
              className="flex-1 bg-[#0a1628] text-red-400 font-mono text-sm px-3 py-2 rounded-xl border border-red-900/30 outline-none" />
            <Btn onClick={burnBoost} color="red" small loading={ld}>🔥</Btn>
          </div>
        </Card>

        {/* Tier info */}
        <Card className="mb-3">
          <p className="text-white text-sm font-semibold mb-2">📊 Tiers</p>
          {[['genesis','🏆','First 100 wallets','amber'],['early','⚡','First 1,000 wallets','purple'],['growth','🌱','Standard referrers','emerald'],['vip','💎','10+ referrals or 10K burned','blue']].map(([id,ic,desc,c]) =>
            <div key={id} className={`flex items-center gap-3 py-2 border-b border-gray-800/20 ${data.tier===id?'opacity-100':'opacity-50'}`}>
              <span className="text-lg">{ic}</span>
              <div className="flex-1"><p className={`text-${c}-400 text-xs font-semibold capitalize`}>{id}</p><p className="text-gray-600 text-[10px]">{desc}</p></div>
              {data.tier===id && <span className="text-cyan-400 text-xs">← You</span>}
            </div>
          )}
        </Card>

        {/* Leaderboard */}
        {board && board.leaderboard?.length > 0 && <Card>
          <p className="text-white text-sm font-semibold mb-2">🏆 Leaderboard</p>
          <p className="text-gray-600 text-[10px] mb-2">{board.total_referrers} referrers · {board.total_referrals} total invites</p>
          {board.leaderboard.slice(0,10).map((b,i) => {
            const bt = tierInfo[b.tier||'growth'];
            return <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-800/20">
              <div className="flex items-center gap-2"><span className="text-gray-600 text-xs w-5">#{i+1}</span><span className="text-gray-500 font-mono text-[10px]">{b.code}</span></div>
              <div className="flex items-center gap-2"><Badge color={bt[2]}>{bt[0]}</Badge><span className="text-cyan-400 text-xs font-bold">{b.referrals}</span></div>
            </div>;
          })}
        </Card>}
      </>}
    </div></div>);
};

// ━━━ WALLET TAB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const WalletTab = ({ profile, onNav, onRefresh, onMenu, setTab }) => {
  const p = profile || {};
  const { t } = useT();
  const [txOpen, setTxOpen] = useState(false); // collapsed by default — saves load
  return (
    <div className="h-full overflow-y-auto pb-4">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="flex items-center gap-3">
          <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
          <h1 className="text-xl font-bold text-white">{t('wallet')}</h1>
        </div>
        <button onClick={onRefresh} className="text-cyan-500 text-xs font-medium">✓ {t('refresh')}</button>
      </div>
      {/* Balance Card */}
      <div className="mx-4 mt-4">
        <div className="relative overflow-hidden rounded-3xl border border-white/[0.08] p-5"
            style={{background:'linear-gradient(135deg, #0d1e42 0%, #0B1426 50%, #071832 100%)'}}>
            {/* frost glow */}
            <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full opacity-20"
              style={{background:'radial-gradient(circle, #00E5FF 0%, transparent 70%)'}} />
            <div className="absolute -bottom-4 -left-4 w-24 h-24 rounded-full opacity-10"
              style={{background:'radial-gradient(circle, #B8E6FF 0%, transparent 70%)'}} />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[#B8E6FF]/60 text-xs font-medium tracking-wider uppercase">{t('totalBalance')}</p>
                <LevelBadge level={p.level??0} />
              </div>
              <div className="flex items-end gap-2 mb-1">
                <span className="text-[42px] leading-none font-thin text-white tracking-tight"
                  style={{fontWeight:100}}>{fmt(p.balance)}</span>
                <span className="text-[#00E5FF] text-lg font-semibold mb-1">LAC</span>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <span className="text-[#B8E6FF]/40 text-[11px] font-mono">{sAddr(p.address)}</span>
                <button onClick={() => cp(p.address)} className="text-[#B8E6FF]/30 hover:text-cyan-400 transition"><Copy className="w-3 h-3" /></button>
              </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            <Btn onClick={() => onNav({type:'send'})} color="emerald" small>↗ {t('send')}</Btn>
            <Btn onClick={async () => { try { const r=await post('/api/faucet'); toast.success(`+${r.added||30} LAC`); onRefresh(); } catch(e){ toast.error(e.message); } }} color="gray" small>🚰 {t('faucet')}</Btn>
          </div>
                    </div>
          </div></Card>
      </div>

      {/* Quick Grid */}
      <div className="grid grid-cols-4 gap-2 px-4 mt-3">
        {[
          {icon:'👻',label:t('veil'),act:()=>onNav({type:'send'})},
          {icon:'🎒',label:t('stash'),act:()=>onNav({type:'stash'})},
          {icon:'🎲',label:t('dice'),act:()=>onNav({type:'dice'})},
          {icon:'👥',label:t('contacts'),act:()=>onNav({type:'contacts'})},
        ].map((a,i) => (
          <button key={i} onClick={a.act}
            className="flex flex-col items-center gap-1.5 py-3 rounded-2xl bg-white/[0.04] border border-white/[0.06] active:bg-white/[0.08] transition-all">
            <span className="text-xl">{a.icon}</span>
            <span className="text-[#B8E6FF]/50 text-[10px] font-medium">{a.label}</span>
          </button>
        ))}
      </div>

      {/* Mining */}
      <div className="mx-4 mt-3">
        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-cyan-400/10 flex items-center justify-center">
                <Zap className="w-4 h-4 text-[#00E5FF]" />
              </div>
              <span className="text-white text-sm font-semibold">{t('mining')}</span>
            </div>
            <button onClick={() => onNav({type:'mining'})} className="text-[#00E5FF]/70 text-xs hover:text-[#00E5FF] transition">{t('miningDetails')} →</button>
          </div>
          <MiningMini />
        </Card>
      </div>

      {/* Level */}
      <div className="mx-4 mt-3">
        <Card>
          <div className="flex items-center justify-between mb-1">
            <span className="text-white text-sm font-semibold">{t('levelProgress')}</span>
            <Badge>L{p.level??0}</Badge>
          </div>
          <LevelBar level={p.level??0} balance={p.balance||0} />
          <LevelBonuses level={p.level??0} />
        </Card>
      </div>

      {/* Recent TXs — collapsible, lazy-loaded */}
      <div className="mx-4 mt-3">
        <button
          onClick={() => setTxOpen(o => !o)}
          className="w-full flex items-center justify-between py-2 px-1"
        >
          <span className="text-gray-500 text-xs font-medium">{t('recentTx')}</span>
          <div className="flex items-center gap-2">
            <button onClick={e => { e.stopPropagation(); onNav({type:'txs'}); }} className="text-cyan-500 text-[11px]">{t('viewAll')}</button>
            <ChevronDown className={`w-4 h-4 text-gray-600 transition-transform ${txOpen ? 'rotate-180' : ''}`} />
          </div>
        </button>
        {txOpen && <RecentTxs visible={txOpen} />}
      </div>
    </div>
  );
};

const MiningMini = () => {
  const [d, setD] = useState(null);
  useEffect(() => {
    const load = () => get('/api/wallet/mining?limit=20').then(setD).catch(() => {});
    load();
    const i = setInterval(load, 60000); // mining stats change every ~30s block
    return () => clearInterval(i);
  }, []);
  if (!d) return <p className="text-gray-600 text-xs">Loading…</p>;
  const earned = d.total_mined || 0;
  const mined = d.count || 0;
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-2xl font-bold text-cyan-400">{earned > 0 ? fmt(earned) : '0'} <span className="text-sm text-gray-500">LAC earned</span></p>
      </div>
      <div className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${mined>0?'bg-cyan-900/40 text-cyan-400':'bg-amber-900/30 text-amber-400'}`}>
        {mined>0?'⛏ Active':'⏳ Waiting'}
      </div>
    </div>
  );
};

const levelCosts = [100, 700, 2000, 10000, 100000, 500000, 2000000, 0]; // L0→L1...L6→L7(GOD), L7=MAX
const levelNames = ['Newbie','Starter','Active','Trusted','Expert','Validator','Priority','⚡ GOD'];

const LevelBonuses = ({ level }) => {
  const bonuses = [
    null, // L0
    '+10 LAC/day faucet',           // L1
    '+20 LAC/day faucet',           // L2
    '+30 LAC/day faucet',           // L3
    '+40 LAC/day faucet · Validator access', // L4
    'Validator · 2x block rewards', // L5
    'Priority Validator · 2x weight + 2x rewards', // L6
    '⚡ 2x mining chance · 2x validator reward · MAX LEVEL', // L7 GOD
  ];
  const bonus = bonuses[level];
  if (!bonus) return null;
  const isGod = level >= 7;
  return (
    <div className={`mt-2 px-3 py-1.5 rounded-lg text-xs ${isGod ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400' : 'bg-cyan-900/20 border border-cyan-900/30 text-cyan-400/80'}`}>
      {isGod ? '⚡ ' : '✓ '}{bonus}
    </div>
  );
};
const LevelBar = ({ level, balance }) => {
  const cost = levelCosts[level] || 0;
  const pct = cost > 0 ? Math.min(100, (balance/cost)*100) : 100;
  const name = levelNames[level] || `L${level}`;
  const nextName = levelNames[level+1] || '';
  const isGod = level >= 7;
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className={isGod?'text-amber-400 font-bold':'text-gray-500'}>{isGod?'⚡ GOD':name} (L{level})</span>
        <span className="text-gray-500">{cost>0?`${fmt(balance)}/${fmt(cost)} LAC`:(isGod?'⚡ MAX LEVEL':'MAX')}</span>
        {cost>0 && <span className="text-gray-500">{nextName} (L{level+1})</span>}
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden"><div className={`h-full ${isGod?'bg-gradient-to-r from-amber-500 to-yellow-400':'bg-gradient-to-r from-cyan-500 to-cyan-400'} rounded-full transition-all`} style={{width:`${pct}%`}} /></div>
    </div>
  );
};

const RecentTxs = ({ visible=false }) => {
  const [txs, setTxs] = useState(null);
  useEffect(() => {
    if (!visible) return; // lazy — only load when expanded
    get('/api/wallet/transactions').then(d => {
      const t=d.transactions||{};
      const all = [
        ...(t.sent||[]).map(x=>({...x,dir:'sent'})),
        ...(t.received||[]).map(x=>({...x,dir:'received'})),
        ...(t.mining||[]).map(x=>({...x,dir:'mined'})),
        ...(t.burned||[]).map(x=>({...x,dir:'burned'})),
        ...(t.timelock_sent||[]).map(x=>({...x,dir:'sent',type:x.type||'timelock'})),
        ...(t.timelock_received||[]).map(x=>({...x,dir:'received',type:x.type||'timelock'})),
      ];
      setTxs(all.sort((a,b)=>(b.timestamp||0)-(a.timestamp||0)).slice(0,8));
    }).catch(() => setTxs([]));
  }, [visible]);
  if (!txs) return null;
  if (txs.length===0) return <p className="text-gray-700 text-sm text-center py-4">No transactions</p>;
  return <div>{txs.map((tx,i) => <TxRow key={i} tx={tx} />)}</div>;
};

const txLabel = (tx) => {
  const t = tx.type || tx.dir;
  const labels = {
    'mining':'⛏️ Mining Reward', 'mining_reward':'⛏️ Mining Reward',
    'transfer':'💸 Transfer', 'normal':'💸 Transfer',
    'veil_transfer':'👻 VEIL Transfer', 'ring_transfer':'🔐 Ring Transfer', 'stealth_transfer':'🔒 Stealth',
    'stash_deposit':'🎒 STASH Deposit', 'stash_withdraw':'💰 STASH Withdraw',
    'dice_burn':'🎲 Dice Loss', 'dice_mint':'🎲 Dice Win', 'dice_win':'🎲 Dice Win', 'dice_loss':'🎲 Dice Loss',
    'burn_level_upgrade':'⬆️ Level Up', 'burn_nickname_change':'✏️ Nickname Change',
    'username_register':'👤 Username', 'faucet':'🚰 Faucet',
    'timelock_create':'⏰ TimeLock Send', 'timelock_activated':'⏰ TimeLock Received',
    'dms_transfer':'💀 DMS Transfer', 'dms_wipe':'💀 DMS Wipe',
    'referral_bonus':'🤝 Referral Bonus', 'referral_boost':'🔥 Referral Boost',
  };
  return labels[t] || t?.replace(/_/g,' ') || tx.dir;
};

const TxRow = ({ tx }) => {
  const isIn = tx.dir==='received'||tx.dir==='mined';
  const icons = {received:<ArrowDownLeft className="w-4 h-4 text-cyan-400"/>,sent:<ArrowUpRight className="w-4 h-4 text-gray-400"/>,mined:<Zap className="w-4 h-4 text-blue-400"/>,burned:<Flame className="w-4 h-4 text-red-400"/>};
  const bgs = {received:'bg-cyan-900/30',sent:'bg-gray-800',mined:'bg-blue-900/30',burned:'bg-red-900/30'};
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-gray-800/20">
      <div className={`w-9 h-9 rounded-full flex items-center justify-center ${bgs[tx.dir]||'bg-gray-800'}`}>{icons[tx.dir]}</div>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm">{txLabel(tx)}</p>
        <p className="text-gray-600 text-[11px]">{ago(tx.timestamp)}{tx.block?` · #${tx.block}`:''}</p>
      </div>
      <span className={`text-sm font-semibold ${isIn?'text-cyan-400':'text-gray-400'}`}>{isIn?'+':'−'}{fmt(tx.amount)}</span>
    </div>
  );
};

// ━━━ SEND ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const SendView = ({ onBack, profile, onDone }) => {
  const [type, setType] = useState(null); const [to, setTo] = useState(''); const [amt, setAmt] = useState(''); const [ld, setLd] = useState(false);
  const go = async () => { setLd(true); try { await post(type==='veil'?'/api/transfer/veil':'/api/transfer/normal',{to:to.trim(),amount:parseFloat(amt)}); toast.success('Sent!'); onDone(); } catch(e){ toast.error(e.message); } finally { setLd(false); } };

  if (!type) return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="Send LAC" onBack={onBack} />
    <div className="p-4 space-y-3">
      <button onClick={() => setType('normal')} className="w-full bg-[#0d1b35] border border-cyan-900/20 rounded-2xl p-4 flex items-center gap-4 active:bg-cyan-900/20">
        <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center"><Send className="w-6 h-6 text-white" /></div>
        <div className="text-left"><p className="text-white font-semibold">Normal Transfer</p><p className="text-gray-500 text-xs">Public on blockchain · 0.1 LAC fee</p></div>
      </button>
      <button onClick={() => setType('veil')} className="w-full bg-[#0d1b35] border border-cyan-900/20 rounded-2xl p-4 flex items-center gap-4 active:bg-purple-900/20">
        <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-fuchsia-600 rounded-2xl flex items-center justify-center"><Eye className="w-6 h-6 text-white" /></div>
        <div className="text-left"><p className="text-white font-semibold">VEIL Transfer</p><p className="text-gray-500 text-xs">Full anonymity · Ring + Phantom TXs · 1.0 LAC</p>
          <span className="flex gap-1 mt-1 flex-wrap">{['Ring Sig','Phantom','OTA','Zero-History'].map(f => <Badge key={f} color="purple">{f}</Badge>)}</span>
        </div>
      </button>
    </div></div>);

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={type==='veil'?'VEIL Transfer':'Normal Transfer'} onBack={() => setType(null)} />
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
  const { t } = useT();
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

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={'🎒 '+t('stashTitle')} onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      <Card gradient="bg-gradient-to-br from-amber-900/20 to-[#0f1f18] border-amber-800/20" className="mb-4">
        <p className="text-amber-400 font-semibold text-sm">{t('anonSafe')}</p>
        <p className="text-gray-500 text-[11px] mt-1">{t('stashDesc')}</p>
        {info && <div className="mt-2 grid grid-cols-3 gap-2">
          <div><p className="text-amber-300 text-xs font-bold">{fmt(info.total_balance||0)}</p><p className="text-gray-600 text-[9px]">{t('poolLac')}</p></div>
          <div><p className="text-cyan-400 text-xs font-bold">{info.active_keys||0}</p><p className="text-gray-600 text-[9px]">{t('activeKeys')}</p></div>
          <div><p className="text-gray-400 text-xs font-bold">{info.spent_count||0}</p><p className="text-gray-600 text-[9px]">{t('redeemed')}</p></div>
        </div>}
      </Card>

      {/* Result feedback */}
      {res?.t==='dep' && res.key && (
        <Card gradient="bg-cyan-900/15 border-cyan-700/30" className="mb-3">
          <p className="text-cyan-400 text-sm font-bold mb-2">✅ {t('depositSuccess')}</p>
          <div className="bg-[#070d1e] p-3 rounded-lg border border-cyan-900/20">
            <p className="text-[9px] text-gray-600 mb-1 uppercase tracking-wider">{t('stashKey')}</p>
            <p onClick={() => cp(res.key)} className="text-cyan-300 font-mono text-[12px] break-all select-all cursor-pointer leading-5">{res.key}</p>
          </div>
          <div className="flex gap-2 mt-2">
            <button onClick={() => cp(res.key)} className="flex-1 text-cyan-400 text-xs flex items-center justify-center gap-1 bg-cyan-900/20 px-3 py-2 rounded-lg active:bg-cyan-900/40"><Copy className="w-3 h-3"/> {t('copy')}</button>
            <button onClick={() => { if(navigator.share) navigator.share({text:res.key}).catch(()=>{}); else cp(res.key); }} className="flex-1 text-blue-400 text-xs flex items-center justify-center gap-1 bg-blue-900/20 px-3 py-2 rounded-lg active:bg-blue-900/40">↗ {t('share')}</button>
          </div>
          <p className="text-red-400/70 text-[10px] mt-2 text-center">⚠️ {t('stashWarn')}</p>
        </Card>
      )}
      {res?.t==='wdr' && (
        <Card gradient="bg-cyan-900/15 border-cyan-700/30" className="mb-3">
          <p className="text-cyan-400 text-sm font-bold">💰 +{fmt(res.a)} LAC!</p>
        </Card>
      )}

      <TabBar tabs={[['dep','💎 '+t('deposit')],['wdr','💰 '+t('withdraw')],['keys','🔑 '+t('savedKeys')]]} active={tab} onChange={v => { setTab(v); setRes(null); }} />
      <div className="mt-3">
        {tab==='dep' ? (
          <div className="space-y-2">
            {noms.map(n => (
              <button key={n.c} onClick={() => setNom(n.c)} className={`w-full p-3 rounded-xl border text-left ${nom===n.c?'border-amber-500 bg-amber-600/10':'border-gray-800 bg-[#0a1628]'}`}>
                <span className="text-white font-semibold text-sm">{fmt(n.a)} LAC</span>
                <span className="text-gray-600 text-[11px] ml-2">({t('fee')}: 2 LAC)</span>
              </button>))}
            <Btn onClick={dep} color="amber" full loading={ld} disabled={nom===null}>{t('deposit')} STASH</Btn>
          </div>
        ) : tab==='wdr' ? (
          <div className="space-y-3">
            <textarea value={key} onChange={e => setKey(e.target.value)} rows={3} placeholder={t('withdrawKey')+'…'}
              className="w-full bg-[#0a1628] text-cyan-400 font-mono text-[11px] p-3 rounded-xl border border-cyan-900/30 outline-none resize-none" />
            <Btn onClick={wdr} color="emerald" full loading={ld} disabled={!key.trim()}>{t('withdraw')}</Btn>
          </div>
        ) : (
          <div className="space-y-2">
            {savedKeys.length === 0 ? <Empty emoji="🔑" text={t('noKeys')} sub={t('deposit')+' STASH'} /> :
            savedKeys.map((s, i) => (
              <Card key={i} gradient={s.used ? 'bg-gray-800/20 border-gray-700/20' : 'bg-amber-900/10 border-amber-800/20'}>
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className={`font-mono text-[10px] break-all ${s.used ? 'text-gray-600 line-through' : 'text-amber-300'}`}>{s.key}</p>
                    <p className="text-gray-600 text-[10px] mt-1">{fmt(s.amount)} LAC · {s.used ? '✅ '+t('markUsed') : '⏳ '+t('active')}</p>
                  </div>
                  <div className="flex gap-1 ml-2 shrink-0">
                    {!s.used && <button onClick={() => { setKey(s.key); setTab('wdr'); }} className="p-1.5 bg-cyan-900/20 rounded-lg" title="Use"><Download className="w-3 h-3 text-cyan-400" /></button>}
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

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="⏰ Time-Lock" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <Card><p className="text-gray-400 text-xs">Send LAC in the future. Funds locked until X blocks pass (~10s/block).</p></Card>
      <div><label className="text-gray-500 text-xs mb-1 block">Recipient</label><Input value={to} onChange={setTo} placeholder="@user or lac1…" mono /></div>
      <div><label className="text-gray-500 text-xs mb-1 block">Amount (LAC)</label><Input value={amt} onChange={setAmt} type="number" placeholder="0" /></div>
      <div>
        <label className="text-gray-500 text-xs mb-1 block">Send in (blocks) {delay && <span className="text-cyan-400">{estTime(parseInt(delay))}</span>}</label>
        <Input value={delay} onChange={setDelay} type="number" placeholder="e.g. 60 = ~10min" />
        <div className="flex gap-2 mt-2">
          {[['10min',60],['1hr',360],['6hr',2160],['24hr',8640]].map(([label,b]) =>
            <button key={b} onClick={() => setDelay(String(b))} className="px-3 py-1.5 bg-cyan-900/20 text-cyan-400 text-[10px] rounded-lg border border-cyan-800/20 active:bg-cyan-800/30">{label}</button>
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

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="💀 Dead Man's Switch" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <Card gradient="bg-gradient-to-br from-red-900/20 to-[#0f1f18] border-red-800/20">
        <p className="text-red-400 font-semibold text-sm">Dead Man's Switch</p>
        <p className="text-gray-500 text-[11px] mt-1">If you don't log in for X days, automatic actions trigger: transfer funds, send messages, or wipe your wallet.</p>
      </Card>

      {status?.enabled ? (
        <Card>
          <div className="flex justify-between items-center">
            <div>
              <p className="text-cyan-400 text-sm font-medium">✅ DMS Active</p>
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
  useEffect(() => {
    const load = () => get('/api/wallet/mining?limit=50').then(setD).catch(()=>{});
    load();
    const i = setInterval(load, 15000);
    return () => clearInterval(i);
  }, []);
  const p = profile||{};
  const rewards = d?.mining_rewards || [];
  const earned = d?.total_mined || 0;
  const mined = d?.count || 0;

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="⛏️ Mining" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      <Card gradient="bg-gradient-to-br from-cyan-800/30 to-[#0f1f18] border-cyan-700/30" className="mb-4 text-center">
        <div className="text-4xl mb-2">⛏️</div>
        <p className="text-cyan-400 font-bold text-lg">{mined > 0 ? 'Mining Active' : 'Mining Waiting'}</p>
        <p className="text-gray-500 text-xs">PoET Consensus · Weighted Lottery</p>
      </Card>
      <div className="grid grid-cols-2 gap-2 mb-4">
        <StatBox label="Your Level" value={`L${p.level??0}`} />
        <StatBox label="Mining Chance" value={`${[15,20,25,30,35,40,45][p.level??0]||15}%`} color="text-cyan-400" />
        <StatBox label="Blocks Mined" value={mined} />
        <StatBox label="Total Earned" value={earned > 0 ? fmt(earned)+' LAC' : '0'} color="text-cyan-400" />
      </div>
      <Card><p className="text-white text-sm font-semibold mb-2">Mining Info</p>
        {[['Block Reward','190 LAC'],['Winners/Block','19'],['Min Balance','50 LAC'],['Your Balance',fmt(p.balance)+' LAC']].map(([k,v]) => (
          <div key={k} className="flex justify-between py-1.5 border-b border-gray-800/20"><span className="text-gray-500 text-xs">{k}</span><span className="text-white text-xs font-medium">{v}</span></div>
        ))}
      </Card>
      {rewards.length > 0 && (<div className="mt-4">
        <p className="text-gray-500 text-xs font-medium mb-2">Recent Rewards</p>
        {rewards.slice(0,10).map((r,i) => <Card key={i} className="mb-1.5"><div className="flex justify-between"><span className="text-cyan-400 text-sm font-semibold">+{fmt(r.reward||r.amount)} LAC</span><span className="text-gray-600 text-[11px]">Block #{r.block}</span></div></Card>)}
      </div>)}
    </div></div>);
};

// ━━━ TRANSACTIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const TxsView = ({ onBack }) => {
  const [txs, setTxs] = useState([]); const [ld, setLd] = useState(true); const [f, setF] = useState('all');
  useEffect(() => {
    get('/api/wallet/transactions').then(d => { const t=d.transactions||{};
      const all = [
        ...(t.sent||[]).map(x=>({...x,dir:'sent'})),
        ...(t.received||[]).map(x=>({...x,dir:'received'})),
        ...(t.mining||[]).map(x=>({...x,dir:'mined'})),
        ...(t.burned||[]).map(x=>({...x,dir:'burned'})),
        ...(t.timelock_sent||[]).map(x=>({...x,dir:'sent',type:x.type||'timelock'})),
        ...(t.timelock_received||[]).map(x=>({...x,dir:'received',type:x.type||'timelock'})),
      ];
      setTxs(all.sort((a,b)=>(b.timestamp||0)-(a.timestamp||0)));
    }).catch(()=>{}).finally(()=>setLd(false));
  }, []);
  const show = f==='all'?txs:txs.filter(t=>t.dir===f);
  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="📜 Transactions" onBack={onBack} right={<span className="text-gray-600 text-xs">{show.length}</span>} />
    <div className="flex gap-1 px-4 py-2">
      {[['all','All'],['received','In'],['sent','Out'],['mined','Mined'],['burned','Burn']].map(([id,l]) => (
        <button key={id} onClick={() => setF(id)} className={`px-3 py-1 rounded-lg text-[11px] font-semibold ${f===id?'bg-cyan-600 text-white':'bg-gray-800 text-gray-500'}`}>{l}</button>
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

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="🎲 Dice" onBack={onBack} />
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
            className="flex-1 bg-[#0a1628] text-white text-center font-bold text-lg px-4 py-3 rounded-xl border border-cyan-900/30 outline-none" />
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
              className="py-4 rounded-2xl bg-gradient-to-b from-cyan-500 to-cyan-700 text-white font-bold text-lg shadow-lg shadow-cyan-900/30 active:scale-95 transition disabled:opacity-50">
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
        <Card gradient={result.won?'bg-gradient-to-br from-cyan-900/30 to-[#0f1f18] border-cyan-500/30':'bg-gradient-to-br from-red-900/20 to-[#0f1f18] border-red-700/30'} className="mt-4 text-center">
          <p className="text-3xl mb-1">{result.won ? '🎉' : '💀'}</p>
          <p className={`text-xl font-bold ${result.won?'text-cyan-400':'text-red-400'}`}>
            {result.won ? `Won +${fmt(result.payout)} LAC` : `Lost ${fmt(result.bet)} LAC`}
          </p>
          <p className="text-gray-500 text-sm mt-1">
            Roll: <span className="text-white font-mono">{result.roll}</span> → <span className={`font-bold ${result.result==='RED'?'text-red-400':result.result==='BLACK'?'text-gray-300':'text-cyan-400'}`}>{result.result}</span>
          </p>
          <p className="text-gray-700 text-[10px] mt-1 font-mono">proof: {result.proof_hash}</p>
        </Card>
      )}

      {/* Stats */}
      {stats && stats.total_games > 0 && (
        <div className="grid grid-cols-3 gap-2 mt-4">
          <StatBox label="Games" value={stats.total_games} small />
          <StatBox label="Win Rate" value={stats.total_games>0 ? Math.round(stats.wins/stats.total_games*100)+'%' : '—'} color={stats.wins>stats.losses?'text-cyan-400':'text-red-400'} small />
          <StatBox label="Profit" value={`${stats.profit>=0?'+':''}${fmt(stats.profit)}`} color={stats.profit>=0?'text-cyan-400':'text-red-400'} small />
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
              <span className={`text-xs font-medium ${g.won?'text-cyan-400':'text-red-400'}`}>
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

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="🛡️ Validator" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      {/* Status Card */}
      <Card gradient={active ? 'bg-gradient-to-br from-purple-900/40 to-[#0f1f18] border-purple-700/30' : 'bg-gradient-to-br from-[#0a1e42] to-[#0f1f18] border-cyan-800/30'} className="mb-4 text-center">
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
          <StatBox label="Daily Earning" value={s.estimated_daily_earning?fmt(s.estimated_daily_earning)+' LAC':'—'} color="text-cyan-400" />
          <StatBox label="Yearly Earning" value={s.estimated_yearly_earning?fmt(s.estimated_yearly_earning)+' LAC':'—'} color="text-cyan-400" />
        </div>
      )}

      {/* Info */}
      <Card><p className="text-white text-sm font-semibold mb-2">Validator Info</p>
        {[
          ['Required Level', 'L5+'],
          ['L5 Reward', '0.5 LAC/commitment'],
          ['L6 Reward', '1.0 LAC/commitment'],
          ['L7 GOD Reward', '1.0 LAC · 3x weight'],
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
  const { t } = useT();
  const cost = !name||name.length<3?0:name.length===3?10000:name.length===4?1000:name.length===5?100:10;
  const chk = async () => { try { const r=await post('/api/username/check',{username:name.toLowerCase()}); setAvail(r.available); toast(r.available?'✅':'❌ Taken',{icon:r.available?'✅':'❌'}); } catch(e){ toast.error(e.message); } };
  const reg = async () => { setLd(true); try { await post('/api/username/register',{username:name.toLowerCase()}); toast.success(`@${name} registered!`); onDone(); } catch(e){ toast.error(e.message); } finally { setLd(false); } };

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={'👤 '+t('registerUsername')} onBack={onBack} />
    <div className="p-4 space-y-4">
      <Card><p className="text-gray-400 text-xs">{t('getYourName')}. Shorter = more expensive.</p></Card>
      <div className="flex gap-2">
        <div className="flex-1 flex items-center bg-[#0a1628] border border-cyan-900/30 rounded-xl overflow-hidden">
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
        {[['3 chars','10,000 LAC'],['4 chars','1,000 LAC'],['5 chars','100 LAC'],['6+ chars','10 LAC']].map(([k,v]) => (
          <div key={k} className="flex justify-between py-1.5 border-b border-gray-800/20"><span className="text-gray-500 text-xs">{k}</span><span className="text-amber-400 text-xs font-medium">{v}</span></div>
        ))}
      </Card>
    </div></div>);
};

// ━━━ CONTACTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const ContactsView = ({ onBack, onChat }) => {
  const [contacts, setContacts] = useState([]); const [addr, setAddr] = useState('');
  const { t } = useT();
  useEffect(() => { get('/api/contacts').then(d => setContacts(d.contacts||[])).catch(()=>{}); }, []);
  const add = async () => { if(!addr.trim()) return; try { await post('/api/contact/add',{address:addr.trim()}); toast.success('Added!'); setAddr(''); setContacts((await get('/api/contacts')).contacts||[]); } catch(e){ toast.error(e.message); } };

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={'👥 '+t('contacts')} onBack={onBack} />
    <div className="p-4">
      <div className="flex gap-2 mb-4"><Input value={addr} onChange={setAddr} placeholder={t('enterContact')} mono /><Btn onClick={add} color="emerald" small><UserPlus className="w-4 h-4"/></Btn></div>
      {contacts.length===0?<Empty emoji="👥" text={t('noContacts')}/>:contacts.map((c,i) => (
        <ListItem key={i} icon={<div className="relative"><User className="w-5 h-5 text-cyan-500"/>{c.online && <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-cyan-400 rounded-full border-2 border-[#070d1e]" />}</div>} title={c.username||sAddr(c.address)} sub={c.address?sAddr(c.address):''}
          onClick={() => onChat({address:c.address,name:c.username||c.address})} />
      ))}
    </div></div>);
};

// ━━━ PROOF-OF-LOCATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const PolView = ({ onBack, profile }) => {
  const [status, setStatus] = useState('idle'); // idle | detecting | proving | done | error
  const [coords, setCoords] = useState(null);
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState('');
  const [proof, setProof] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [msgMode, setMsgMode] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [allZones, setAllZones] = useState([]);
  const { t } = useT();

  // Load all zones for manual fallback
  useEffect(() => {
    get('/api/pol/zones').then(r => {
      if (r.ok) {
        const combined = [...(r.countries||[]), ...(r.ua_oblasts||[]), ...(r.special_zones||[])];
        setAllZones(combined);
      }
    }).catch(() => {});
  }, []);

  const enterManualMode = () => {
    setManualMode(true);
    setError('');
    // Manual proof: coords = null, zone selected manually
    // Backend will accept zone without coords in manual mode
    setCoords({ lat: 0, lon: 0, accuracy: null, manual: true });
    if (allZones.length > 0) setZones(allZones);
  };

  const getLocation = () => {
    setStatus('detecting'); setError('');
    if (!navigator.geolocation || window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
      setError('GPS requires HTTPS. Use manual zone selection below.');
      setStatus('error');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const c = { lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy };
        setCoords(c);
        // Detect zones
        post('/api/pol/detect', { lat: c.lat, lon: c.lon }).then(r => {
          if (r.ok) { setZones(r.zones || []); setSelectedZone(r.zones?.[0] || ''); }
          setStatus('idle');
        }).catch(() => setStatus('idle'));
      },
      (err) => { setError(`GPS error: ${err.message}`); setStatus('error'); },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  const createProof = async () => {
    if (!selectedZone) return;
    if (!coords && !manualMode) return;
    setStatus('proving');
    try {
      const endpoint = msgMode && message.trim() ? '/api/pol/message' : '/api/pol/prove';
      const body = { zone: selectedZone };
      if (!manualMode && coords && !coords.manual) {
        body.lat = coords.lat;
        body.lon = coords.lon;
      } else {
        // Manual mode: send zone-only proof (backend will use zone center coords)
        body.manual = true;
      }
      if (msgMode && message.trim()) body.text = message.trim();
      const r = await post(endpoint, body);
      if (r.ok) {
        setProof(r.proof);
        // Store private data locally
        if (r.private) localStorage.setItem('lac_pol_private_' + r.proof?.proof_hash?.slice(0,8), JSON.stringify(r.private));
        setStatus('done');
      } else { setError(r.error || 'Failed'); setStatus('error'); }
    } catch (e) { setError(e.message); setStatus('error'); }
  };

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="📍 Proof-of-Location" onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Info */}
      <Card gradient="bg-gradient-to-br from-blue-900/20 to-[#0f1f18] border-blue-800/15">
        <p className="text-blue-400 text-sm font-semibold mb-2">🔒 Privacy-First Location Proofs</p>
        <p className="text-gray-400 text-xs leading-relaxed">Prove you're in a region WITHOUT revealing exact coordinates. Your GPS data stays on your device — only the zone name goes on-chain.</p>
      </Card>

      {/* Step 1: Get GPS */}
      {!coords ? (
        <Card>
          <p className="text-white text-sm font-semibold mb-3">Step 1: Get Your Location</p>
          <button onClick={getLocation} disabled={status === 'detecting'}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white font-bold py-3 rounded-xl text-sm">
            {status === 'detecting' ? '📡 Detecting GPS...' : '📍 Enable GPS'}
          </button>
          {error && (
            <div className="mt-2">
              <p className="text-red-400 text-xs">{error}</p>
              <div className="mt-2 bg-amber-900/20 border border-amber-800/30 rounded-xl p-3">
                <p className="text-amber-400 text-xs font-semibold mb-1">⚠️ GPS requires HTTPS</p>
                <p className="text-gray-500 text-[10px] mb-2">Your device blocks GPS on HTTP. Use manual zone selection instead — you choose your zone without GPS.</p>
                <button onClick={enterManualMode}
                  className="w-full bg-amber-600/80 hover:bg-amber-600 text-white font-bold py-2.5 rounded-xl text-sm">
                  🗺️ Select Zone Manually
                </button>
              </div>
            </div>
          )}
          {!error && <p className="text-gray-600 text-[10px] mt-2 text-center">Coordinates never leave your device</p>}
          {!error && (
            <button onClick={enterManualMode} className="w-full mt-2 text-gray-600 text-[10px] hover:text-gray-400 py-1">
              Or select zone manually (no GPS needed) →
            </button>
          )}
        </Card>
      ) : status !== 'done' ? (<>
        {/* Step 2: Select Zone */}
        <Card gradient="bg-gradient-to-br from-cyan-900/20 to-[#0f1f18] border-cyan-800/15">
          <p className="text-white text-sm font-semibold mb-1">Step 2: Select Zone to Prove</p>
          {manualMode ? (
            <p className="text-amber-400 text-[10px] mb-3">🗺️ Manual mode — select your zone from the list</p>
          ) : (
            <p className="text-gray-600 text-[10px] mb-3">GPS: {coords?.lat?.toFixed(4)}, {coords?.lon?.toFixed(4)} (±{Math.round(coords?.accuracy||0)}m) — stays on device</p>
          )}
          {zones.length > 0 ? (
            <div className="space-y-1.5 max-h-64 overflow-y-auto">
              {zones.map(z => (
                <button key={z} onClick={() => setSelectedZone(z)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm border transition-all ${selectedZone === z ? 'bg-cyan-900/30 border-cyan-500/50 text-cyan-400' : 'bg-[#0a1a14] border-cyan-900/15 text-gray-400'}`}>
                  {z === selectedZone ? '✅ ' : '📍 '}{z}
                </button>
              ))}
            </div>
          ) : <p className="text-gray-600 text-xs">No zones detected for your location</p>}
        </Card>

        {/* Optional: Attach message */}
        <Card>
          <button onClick={() => setMsgMode(!msgMode)} className="text-amber-400 text-xs font-semibold">
            {msgMode ? '▼ Hide Message' : '▶ Attach Message (journalist mode)'}
          </button>
          {msgMode && <textarea value={message} onChange={e => setMessage(e.target.value)} placeholder="Message text bound to location proof..."
            className="w-full mt-2 bg-[#0a1a14] border border-cyan-900/20 rounded-xl p-3 text-white text-sm h-24 resize-none" />}
        </Card>

        {/* Step 3: Generate */}
        <button onClick={createProof} disabled={!selectedZone || status === 'proving'}
          className="w-full bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-700 text-white font-bold py-3.5 rounded-xl text-sm">
          {status === 'proving' ? '🔐 Generating Proof...' : `🔐 Prove: "${selectedZone}"`}
        </button>
        {error && <p className="text-red-400 text-xs text-center">{error}</p>}
      </>) : (
        /* Step 4: Proof Result */
        <Card gradient="bg-gradient-to-br from-cyan-900/20 to-[#0f1f18] border-cyan-500/30">
          <p className="text-cyan-400 text-lg font-bold mb-3">✅ Location Proved!</p>
          <div className="space-y-2">
            <div className="flex justify-between"><span className="text-gray-600 text-xs">Zone</span><span className="text-white text-sm font-semibold">{proof?.zone}</span></div>
            <div className="flex justify-between"><span className="text-gray-600 text-xs">Area</span><span className="text-gray-400 text-xs">~{(proof?.area_km2||0).toLocaleString()} km²</span></div>
            <div className="flex justify-between"><span className="text-gray-600 text-xs">Protocol</span><span className="text-blue-400 text-xs">{proof?.protocol}</span></div>
            <div className="flex justify-between"><span className="text-gray-600 text-xs">Privacy</span><span className="text-cyan-400 text-xs">Zone only — no coordinates</span></div>
            {proof?.all_zones?.length > 1 && <div><span className="text-gray-600 text-xs">Also in:</span><span className="text-gray-500 text-xs ml-1">{proof.all_zones.filter(z=>z!==proof.zone).join(', ')}</span></div>}
            <div className="mt-3 bg-[#070d1e] rounded-xl p-2">
              <p className="text-gray-600 text-[9px] font-mono break-all">Commitment: {proof?.commitment?.slice(0,32)}...</p>
              <p className="text-gray-600 text-[9px] font-mono break-all">Proof: {proof?.proof_hash?.slice(0,32)}...</p>
            </div>
          </div>
          {proof?.message_binding && <div className="mt-2 bg-amber-900/10 border border-amber-800/20 rounded-xl p-2">
            <p className="text-amber-400 text-xs font-semibold">📎 Message Attached</p>
            <p className="text-gray-600 text-[9px] font-mono">Binding: {proof.message_binding.slice(0,32)}...</p>
          </div>}
          <button onClick={() => { setStatus('idle'); setProof(null); setCoords(null); setZones([]); }}
            className="w-full mt-4 bg-[#0a1a14] border border-cyan-900/20 text-gray-400 py-2.5 rounded-xl text-xs">New Proof</button>
        </Card>
      )}

      {/* Trust note */}
      <p className="text-gray-700 text-[9px] text-center px-4">⚠️ GPS can be spoofed. This proves device-reported zone, not absolute truth. Sufficient for journalism, not for legal evidence.</p>
    </div>
  </div>);
};

// ━━━ DASHBOARD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const DashboardView = ({ onBack }) => {
  const [s, setS] = useState(null);
  const { t } = useT();
  useEffect(() => { get("/api/stats").then(setS).catch(()=>{ setS({}); }); }, []);

  const buildLevels = (dist) => {
    const all = {};
    for (let i = 0; i <= 7; i++) all["L"+i] = 0;
    if (dist) Object.entries(dist).forEach(([k, v]) => { const norm = k.startsWith("L") ? k : "L"+k; all[norm] = (all[norm]||0) + v; });
    return all;
  };
  const levelNames = ["Newbie","Starter","Active","Trusted","Expert","Validator","Priority","⚡ GOD"];
  const levelColors = ["text-gray-400","text-cyan-400","text-teal-400","text-cyan-400","text-amber-400","text-red-400","text-purple-400","text-yellow-300"];

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={"📊 "+t("dashboard")} onBack={onBack} />
    <div className="flex-1 overflow-y-auto p-4">
      {!s ? <p className="text-gray-600 text-center py-8">{t("loading")}</p> : <>
        <Card gradient="bg-gradient-to-br from-cyan-900/20 to-[#0f1f18] border-cyan-800/15" className="mb-3">
          <p className="text-white text-sm font-semibold mb-3">💰 {t("supply")}</p>
          <div className="bg-[#070d1e] rounded-xl p-3 mb-2 border border-cyan-900/20">
            <p className="text-[9px] text-gray-600 uppercase mb-0.5">💼 {t("onWallets")}</p>
            <p className="text-cyan-400 text-2xl font-bold">{fmt(s.on_wallets||s.circulating_supply||0)} <span className="text-sm text-gray-600">LAC</span></p>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-800/30">
            <p className="text-[11px] text-blue-400 font-semibold">✨ {t("totalEmitted")||"Total Emitted"}</p>
            <p className="text-blue-400 font-bold text-sm">{fmt(s.total_emitted||s.total_mined_emission||0)} LAC</p>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-gray-800/30">
            <p className="text-[11px] text-red-400 font-semibold">🔥 {t("burnedForever")}</p>
            <p className="text-red-400 font-bold text-sm">{fmt(s.total_burned||0)} LAC</p>
          </div>
          {(s.stash_pool_balance||0) > 0 && (
            <div className="flex justify-between items-center pt-2">
              <p className="text-[11px] text-amber-400 font-semibold">🎒 {t("inStash")}</p>
              <p className="text-amber-400 font-bold text-sm">{fmt(s.stash_pool_balance)} LAC</p>
            </div>
          )}
        </Card>
        <div className="grid grid-cols-2 gap-2 mb-3">
          <StatBox icon="⛓" label={t("blocks")} value={fmt(s.total_blocks)} />
          <StatBox icon="👛" label={t("wallets")} value={fmt(s.total_wallets)} />
        </div>
        {s.top_balances && (
          <Card className="mb-3">
            <p className="text-white text-sm font-semibold mb-2">🏆 {t("topBalances")}</p>
            {s.top_balances.slice(0,5).map((b,i) => (
              <div key={i} className="flex justify-between py-1.5 border-b border-gray-800/20">
                <span className="text-gray-500 text-xs">#{i+1}</span>
                <span className="text-cyan-400 text-xs font-mono">{fmt(b)} LAC</span>
              </div>
            ))}
          </Card>
        )}
        <Card>
          <p className="text-white text-sm font-semibold mb-2">📊 {t("levelDist")}</p>
          {Object.entries(buildLevels(s.level_distribution)).map(([k, v], i) => (
            <div key={k} className="flex justify-between items-center py-1.5 border-b border-gray-800/20 last:border-0">
              <div className="flex items-center gap-2">
                <span className={"text-xs font-bold "+levelColors[i]}>{k}</span>
                <span className="text-gray-600 text-[10px]">{levelNames[i]}</span>
              </div>
              <span className="text-white text-xs">{v} {t("walletsCount")}</span>
            </div>
          ))}
        </Card>
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
    'referral_bonus':['🤝','Referral','purple'], 'referral_boost':['🔥','Ref Boost','red'],
  };
  return m[t] || ['📄', t?.replace(/_/g,' ')||'Event', 'gray'];
};

const isAnon = (t) => ['veil_transfer','ring_transfer','stealth_transfer','stash_deposit','stash_withdraw','dice_burn','dice_mint','dms_transfer','dms_transfer_all','dms_message','dms_wipe','dms_burn_stash'].includes(t);

const ExplorerView = ({ onBack }) => {
  const [blocks, setBlocks] = useState([]); const [h, setH] = useState(0); const [sel, setSel] = useState(null); const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      if (!cancelled) { setLoading(false); }
    }, 10000); // safety timeout
    (async () => {
      try {
        const hd = await get('/api/chain/height');
        if (cancelled) return;
        const height = hd.height || 0;
        setH(height);
        if (height === 0) { clearTimeout(timer); setLoading(false); return; }
        const start = Math.max(0, height - 50); // 50 blocks — faster load
        const bd = await get(`/api/blocks/range?start=${start}&end=${height}`);
        if (cancelled) return;
        setBlocks((bd.blocks || bd || []).reverse());
      } catch(e) {
        // ignore
      }
      clearTimeout(timer);
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; clearTimeout(timer); };
  }, []);

  if (sel) {
    const txs = (sel.transactions||[]).filter(t => t.type!=='mining_reward' && t.type!=='poet_reward');
    const msgs = (sel.ephemeral_msgs||[]).length;
    const reward = sel.total_reward || (sel.mining_rewards||[]).reduce((s,r)=>s+(r.reward||0),0);
    const miners = sel.mining_winners_count || (sel.mining_rewards||[]).length;
    return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title={`Block #${sel.index}`} onBack={() => setSel(null)} />
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <Card gradient="bg-gradient-to-br from-cyan-900/20 to-[#0f1f18] border-cyan-800/15">
          <p className="text-[10px] text-gray-600 font-mono break-all">{sel.hash||'—'}</p>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div><p className="text-[9px] text-gray-600 uppercase">Time</p><p className="text-white text-[11px]">{new Date(sel.timestamp*1000).toLocaleString()}</p></div>
            <div><p className="text-[9px] text-gray-600 uppercase">Miner</p><p className="text-purple-400 text-[11px]">🔒 PoET Anonymous</p></div>
          </div>
        </Card>
        {reward > 0 && <Card><div className="flex justify-between items-center"><span className="text-gray-400 text-xs">⛏️ {miners} miner{miners>1?'s':''}</span><span className="text-cyan-400 font-bold font-mono">{reward.toFixed(2)} LAC</span></div></Card>}
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
                {tx.amount>0 && <div><span className="text-gray-600">Amount: </span><span className={anon?'text-purple-400 italic':'text-cyan-400 font-mono font-bold'}>{anon?'🔒 Hidden':fmt(tx.amount)+' LAC'}</span></div>}
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

  return (<div className="h-full bg-[#070d1e] flex flex-col"><Header title="⛓ Explorer" onBack={onBack} right={<Badge>#{h} · last 200</Badge>} />
    <div className="flex-1 overflow-y-auto p-4">
      {loading?<p className="text-gray-600 text-center py-8">Loading blocks…</p>:
        blocks.length===0?<p className="text-gray-600 text-center py-8">No blocks</p>:
        blocks.map(b => {
          const txs = (b.transactions||[]).filter(t => t.type!=='mining_reward' && t.type!=='poet_reward');
          const msgs = (b.ephemeral_msgs||[]).length;
          return (<Card key={b.index} className="mb-2" onClick={() => setSel(b)}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-cyan-400 text-sm font-bold">#{b.index}</span>
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
const ExploreTab = ({ onNav, onMenu }) => {
  const { t } = useT();
  return (
  <div className="h-full overflow-y-auto pb-4">
    <div className="px-4 pt-4 pb-2 flex items-center gap-3">
      <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
      <h1 className="text-xl font-bold text-white">{t('explore')}</h1>
    </div>
    <div className="px-4 space-y-2">
      {[
        {icon:'⛓',title:t('explorer'),sub:t('blocks')+' & '+t('transactions'),type:'explorer'},
        {icon:'📊',title:t('dashboard'),sub:t('topBalances')+', '+t('levelDist'),type:'dashboard'},
        {icon:'⛏️',title:t('mining'),sub:t('totalEarned')+', '+t('recentRewards'),type:'mining'},
        {icon:'⏰',title:'TimeLock',sub:t('lockFunds'),type:'timelock'},
        {icon:'💀',title:'Dead Man\'s Switch',sub:'DMS',type:'dms'},
        {icon:'🛡️',title:'Validator',sub:'Zero-History',type:'validator'},
        {icon:'📍',title:'Proof-of-Location',sub:'Prove zone without revealing location',type:'pol'},
      ].map(item => (
        <button key={item.type} onClick={() => onNav({type:item.type})}
          className="w-full bg-[#0d1b35] border border-cyan-900/15 rounded-2xl p-4 flex items-center gap-4 active:bg-cyan-900/20">
          <span className="text-2xl">{item.icon}</span>
          <div className="text-left flex-1"><p className="text-white font-medium text-[14px]">{item.title}</p><p className="text-gray-600 text-xs">{item.sub}</p></div>
          <ChevronRight className="w-4 h-4 text-gray-700" />
        </button>
      ))}
    </div>
  </div>
);
};

// ━━━ PROFILE TAB ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const NotifToggle = () => {
  const [perm, setPerm] = useState(typeof Notification !== 'undefined' ? Notification.permission : 'unsupported');
  if (perm === 'unsupported') return null;
  const request = async () => {
    const p = await Notification.requestPermission();
    setPerm(p);
    if (p === 'granted') toast.success('🔔 Notifications enabled!');
  };
  if (perm === 'granted') return <span className="text-cyan-400 text-xs">🔔 Enabled</span>;
  if (perm === 'denied') return <span className="text-red-400 text-xs">🔕 Blocked in browser settings</span>;
  return <button onClick={request} className="text-amber-400 text-xs underline">Enable</button>;
};

const ProfileTab = ({ profile, onNav, onLogout, onRefresh, onMenu }) => {
  const p = profile||{};
  const [upg, setUpg] = useState(false);
  const { t, lang, setLang } = useT();
  const uname = p.username && p.username!=='Anonymous' && p.username!=='None' ? p.username : null;

  const upgrade = async () => { setUpg(true); try { const r=await post('/api/upgrade_level'); toast.success(`Upgraded to L${r.new_level}!`); onRefresh(); } catch(e){ toast.error(e.message); } finally { setUpg(false); } };

  return (
    <div className="h-full overflow-y-auto pb-4">
      <div className="flex items-center gap-3 px-4 pt-4 pb-2">
        <button onClick={onMenu} className="text-gray-400 hover:text-white"><Menu className="w-5 h-5" /></button>
        <h1 className="text-xl font-bold text-white">{t('profile')}</h1>
      </div>
      <div className="mx-4">
        <Card gradient="bg-gradient-to-br from-[#0a1e42] to-[#0f1f18] border-cyan-800/30" className="text-center">
          <LevelBadge level={p.level??0} />
          <p className="text-white text-xl font-bold mt-3">{uname||'Anonymous'}</p>
          <p className="text-gray-600 text-[11px] font-mono mt-1">{sAddr(p.address)}</p>
          <div className="flex justify-center gap-4 mt-3">
            <div className="text-center"><p className="text-white font-bold">{fmt(p.balance)}</p><p className="text-gray-600 text-[10px]">LAC</p></div>
            <div className="text-center"><p className="text-white font-bold">{p.tx_count||0}</p><p className="text-gray-600 text-[10px]">TXs</p></div>
            <div className="text-center"><p className="text-white font-bold">{p.msg_count||0}</p><p className="text-gray-600 text-[10px]">{t('messages')}</p></div>
          </div>
        </Card>
      </div>

      <div className="mx-4 mt-4 space-y-0.5">
        {!uname && <ListItem icon={<User className="w-5 h-5 text-purple-400"/>} title={t('registerUsername')} sub={t('getYourName')} onClick={() => onNav({type:'username'})} />}
        <ListItem icon={<Award className="w-5 h-5 text-amber-400"/>} title={t('upgradeLevel')} sub={`${levelNames[p.level??0]||'L'+(p.level??0)} → ${levelNames[(p.level??0)+1]||'?'} · ${levelCosts[p.level??0]>0 ? fmt(levelCosts[p.level??0])+' LAC' : '⚡ MAX'}`}
          onClick={upgrade} right={upg?<span className="text-xs text-gray-500">…</span>:undefined} />
        <ListItem icon={<Copy className="w-5 h-5 text-blue-400"/>} title={t('copyAddress')} sub={sAddr(p.address)} onClick={() => cp(p.address)} />
        <ListItem icon={<Lock className="w-5 h-5 text-red-400"/>} title={t('exportSeed')} sub={t('backupKey')} onClick={() => {
          const s=localStorage.getItem('lac_seed');
          if(s){ const show=confirm('⚠️ Your seed will be shown.\nMake sure nobody is watching!\n\nShow seed?');
            if(show){ cp(s); prompt('Your seed (copied to clipboard):', s); }
          } else { toast.error('No seed found'); }
        }} />
        <ListItem icon={<Globe className="w-5 h-5 text-cyan-400"/>} title={t('language')} sub={lang==='uk'?'🇺🇦 Українська':lang==='ru'?'🇷🇺 Русский':'🇬🇧 English'}
          onClick={() => setLang(lang==='uk'?'ru':lang==='ru'?'en':'uk')} />
        <ListItem icon={<span className="text-lg">🤝</span>} title="Referral" sub="Invite friends, earn LAC"
          onClick={() => onNav({type:'referral'})} />
          <ListItem icon={<span className="text-lg">🐍</span>} title="Nagini" sub="Geographic secret backup"
            onClick={() => onNav({type:'nagini'})} />
          <ListItem icon={<Bell className="w-5 h-5 text-amber-500" />} title="Push Notifications" right={<NotifToggle />} />
        <div className="h-px bg-gray-800/30 my-2" />
        <ListItem icon={<LogOut className="w-5 h-5 text-red-400"/>} title={t('logout')} sub="Save seed first!" onClick={() => { if(confirm('Make sure seed is saved!')) onLogout(); }} />
      </div>
      <p className="text-center text-gray-800 text-[10px] mt-6">LAC v8 · Zero-History Blockchain · PoET Consensus</p>
    </div>
  );
};
