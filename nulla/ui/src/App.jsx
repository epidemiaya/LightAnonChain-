import { useState, useEffect, useCallback, useRef } from "react";

const T = {
  bg:       "#080808",
  surface:  "#0e0e0e",
  surface2: "#141414",
  border:   "rgba(255,255,255,0.07)",
  accent:   "#f7931a",   // Bitcoin orange
  accentDim:"rgba(247,147,26,0.12)",
  text:     "#d4d4d4",
  muted:    "#4a4a4a",
  red:      "#ff5252",
  green:    "#4caf50",
  yellow:   "#ffd166",
  font:     "'JetBrains Mono','Fira Code','Cascadia Code',monospace",
};

const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:${T.bg};color:${T.text};font-family:${T.font};font-size:13px;line-height:1.6;-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:${T.muted}}
::selection{background:${T.accentDim};color:${T.accent}}
input,textarea{font-family:${T.font};background:${T.surface2};border:1px solid ${T.border};color:${T.text};border-radius:4px;padding:10px 12px;font-size:13px;width:100%;outline:none;transition:border-color 0.15s}
input:focus,textarea:focus{border-color:${T.accent};box-shadow:0 0 0 2px ${T.accentDim}}
textarea{resize:vertical;min-height:80px}
button{font-family:${T.font};cursor:pointer;border:none;border-radius:4px;font-size:13px;transition:opacity 0.15s,transform 0.1s}
button:active{transform:scale(0.97)}
button:disabled{opacity:0.4;cursor:not-allowed;transform:none}
@keyframes fadeIn{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
@keyframes spin{to{transform:rotate(360deg)}}
.fade-in{animation:fadeIn 0.2s ease forwards}
`;

// ── Helpers ───────────────────────────────────────────────────────────────────
const api = async (path, body) => {
  const opts = { credentials: "include", headers: { "Content-Type": "application/json" } };
  if (body !== undefined) { opts.method = "POST"; opts.body = JSON.stringify(body); }
  const r = await fetch(`/api${path}`, opts);
  return r.json();
};

const copyText = t => navigator.clipboard?.writeText(t).catch(() => {});

const fmtBtc = (sats) => {
  if (sats === undefined || sats === null) return "—";
  const n = Number(sats);
  if (isNaN(n)) return "—";
  if (n < 1000) return `${n} sat`;
  const btc = n / 1e8;
  if (btc >= 0.001) return `${btc.toFixed(8)} BTC`;
  return `${n.toLocaleString()} sat`;
};

const trunc = (s = "", l = 12, r = 8) =>
  s.length > l + r + 3 ? `${s.slice(0, l)}…${s.slice(-r)}` : s;

// ── Base UI ───────────────────────────────────────────────────────────────────
const Spinner = () => (
  <span style={{ display:"inline-block", width:13, height:13,
    border:`2px solid ${T.muted}`, borderTopColor:T.accent,
    borderRadius:"50%", animation:"spin 0.8s linear infinite" }} />
);

const Btn = ({ children, onClick, variant="primary", disabled, style }) => {
  const styles = {
    primary: { background: T.accent, color: "#000", fontWeight: 700, padding: "10px 20px" },
    ghost:   { background: "transparent", color: T.text, border: `1px solid ${T.border}`, padding: "10px 20px" },
    danger:  { background: "transparent", color: T.red, border: `1px solid ${T.red}33`, padding: "10px 20px" },
  };
  return <button onClick={onClick} disabled={disabled} style={{ ...styles[variant], letterSpacing: "0.04em", ...style }}>{children}</button>;
};

const Card = ({ children, style }) => (
  <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 6, padding: "14px 16px", ...style }}>
    {children}
  </div>
);

const Label = ({ children }) => (
  <div style={{ color: T.muted, fontSize: 10, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>{children}</div>
);

const ErrBox = ({ msg }) => msg ? (
  <div style={{ background: `${T.red}11`, border: `1px solid ${T.red}33`, borderRadius: 4, padding: "10px 12px", color: T.red, fontSize: 12, marginTop: 10 }}>{msg}</div>
) : null;

const Field = ({ label, ...p }) => (
  <div style={{ marginBottom: 14 }}>
    {label && <Label>{label}</Label>}
    <input {...p} />
  </div>
);

const Dot = ({ on, color }) => (
  <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%",
    background: on ? (color || T.accent) : T.muted,
    boxShadow: on ? `0 0 5px ${color || T.accent}` : "none", marginRight: 6 }} />
);

// ── Setup screen ──────────────────────────────────────────────────────────────
function ScreenSetup({ onDone }) {
  const [view, setView] = useState("home");
  const [pw, setPw] = useState(""); const [pw2, setPw2] = useState("");
  const [mnemonic, setMnemonic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState(null);

  const doCreate = async () => {
    if (pw.length < 8) return setError("Min 8 characters");
    if (pw !== pw2) return setError("Passwords don't match");
    setLoading(true); setError("");
    const r = await api("/wallet/create", { password: pw });
    setLoading(false);
    if (!r.ok) return setError(r.error);
    setCreated(r);
  };

  const doImport = async () => {
    if (!mnemonic.trim()) return setError("Enter mnemonic phrase");
    if (pw.length < 8) return setError("Min 8 characters");
    if (pw !== pw2) return setError("Passwords don't match");
    setLoading(true); setError("");
    const r = await api("/wallet/import", { mnemonic: mnemonic.trim(), password: pw });
    setLoading(false);
    if (!r.ok) return setError(r.error);
    onDone(r.address);
  };

  // Show mnemonic after create
  if (created) {
    const words = (created.mnemonic || "").split(" ");
    return (
      <div className="fade-in" style={{ padding: "20px", maxWidth: 440, margin: "0 auto" }}>
        <div style={{ color: T.accent, fontWeight: 700, fontSize: 15, marginBottom: 4 }}>✓ Wallet created</div>
        <div style={{ color: T.muted, fontSize: 12, marginBottom: 18 }}>Save your recovery phrase. This is the only backup for your funds.</div>
        <div style={{ background: T.surface2, border: `1px solid ${T.yellow}44`, borderRadius: 6, padding: 16, marginBottom: 16 }}>
          <div style={{ color: T.yellow, fontSize: 10, letterSpacing: "0.12em", marginBottom: 12 }}>⚠ RECOVERY PHRASE — WRITE OFFLINE</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "6px 16px" }}>
            {words.map((w, i) => (
              <div key={i}><span style={{ color: T.muted, fontSize: 10, marginRight: 4 }}>{i+1}.</span>{w}</div>
            ))}
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <Label>Primary address (Native SegWit)</Label>
          <div style={{ fontSize: 11, wordBreak: "break-all", color: T.text, background: T.surface2,
            border: `1px solid ${T.border}`, borderRadius: 4, padding: "8px 12px", lineHeight: 1.7 }}>
            {created.address}
          </div>
        </div>
        <Btn style={{ width: "100%", padding: 14 }} onClick={() => onDone(created.address)}>
          I SAVED MY PHRASE → OPEN WALLET
        </Btn>
      </div>
    );
  }

  if (view === "home") return (
    <div className="fade-in" style={{ padding: "70px 24px 24px", maxWidth: 400, margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: 52 }}>
        <div style={{ fontSize: 11, letterSpacing: "0.3em", color: T.muted, marginBottom: 8 }}>BITCOIN LIGHT WALLET</div>
        <div style={{ fontSize: 36, fontWeight: 700, color: T.accent, letterSpacing: "-0.02em" }}>NULLA</div>
        <div style={{ color: T.muted, fontSize: 11, marginTop: 8 }}>Keys stay on your device. Always.</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <Btn onClick={() => setView("create")} style={{ width: "100%", padding: 14 }}>CREATE NEW WALLET</Btn>
        <Btn variant="ghost" onClick={() => setView("import")} style={{ width: "100%", padding: 14 }}>RESTORE FROM MNEMONIC</Btn>
      </div>
    </div>
  );

  if (view === "create") return (
    <div className="fade-in" style={{ padding: "24px", maxWidth: 400, margin: "0 auto" }}>
      <button onClick={() => setView("home")} style={{ background:"none", color:T.muted, fontSize:12, marginBottom:20, cursor:"pointer" }}>← back</button>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 16 }}>Create wallet</div>
      <Field label="Password (min 8 chars)" type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="••••••••••" />
      <Field label="Confirm password" type="password" value={pw2} onChange={e => setPw2(e.target.value)} placeholder="••••••••••" />
      <ErrBox msg={error} />
      <Btn style={{ width: "100%", marginTop: 16, padding: 14 }} onClick={doCreate} disabled={loading}>
        {loading ? <Spinner /> : "GENERATE WALLET"}
      </Btn>
    </div>
  );

  return (
    <div className="fade-in" style={{ padding: "24px", maxWidth: 400, margin: "0 auto" }}>
      <button onClick={() => setView("home")} style={{ background:"none", color:T.muted, fontSize:12, marginBottom:20, cursor:"pointer" }}>← back</button>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 16 }}>Restore wallet</div>
      <div style={{ marginBottom: 14 }}>
        <Label>24-word recovery phrase</Label>
        <textarea value={mnemonic} onChange={e => setMnemonic(e.target.value)} placeholder="word1 word2 word3 ..." rows={4} />
      </div>
      <Field label="New password" type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="••••••••••" />
      <Field label="Confirm" type="password" value={pw2} onChange={e => setPw2(e.target.value)} placeholder="••••••••••" />
      <ErrBox msg={error} />
      <Btn style={{ width: "100%", marginTop: 16, padding: 14 }} onClick={doImport} disabled={loading}>
        {loading ? <Spinner /> : "RESTORE WALLET"}
      </Btn>
    </div>
  );
}

// ── Unlock ────────────────────────────────────────────────────────────────────
function ScreenUnlock({ onDone }) {
  const [pw, setPw] = useState(""); const [err2, setErr2] = useState(""); const [loading, setLoading] = useState(false);
  const ref = useRef(); useEffect(() => ref.current?.focus(), []);
  const doUnlock = async () => {
    if (!pw) return;
    setLoading(true); setErr2("");
    const r = await api("/wallet/unlock", { password: pw });
    setLoading(false);
    if (!r.ok) return setErr2(r.error);
    onDone(r.address);
  };
  return (
    <div className="fade-in" style={{ padding: "80px 24px 24px", maxWidth: 360, margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: 40 }}>
        <div style={{ fontSize: 30, fontWeight: 700, color: T.accent }}>NULLA</div>
        <div style={{ color: T.muted, fontSize: 12, marginTop: 6 }}>Enter password to unlock</div>
      </div>
      <Field type="password" value={pw} ref={ref} onChange={e => setPw(e.target.value)}
        onKeyDown={e => e.key === "Enter" && doUnlock()} placeholder="Password" />
      <ErrBox msg={err2} />
      <Btn style={{ width: "100%", marginTop: 12, padding: 14 }} onClick={doUnlock} disabled={loading || !pw}>
        {loading ? <Spinner /> : "UNLOCK"}
      </Btn>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
function ScreenDashboard({ wallet, onNav }) {
  const [bal, setBal] = useState(null);
  const [txs, setTxs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nodeOk, setNodeOk] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const [b, t, n] = await Promise.all([api("/balance"), api("/transactions?limit=5"), api("/node/status")]);
      if (b.ok) setBal(b);
      if (t.ok) setTxs(t.transactions || []);
      setNodeOk(n.connected || false);
      setLoading(false);
    })();
  }, []);

  const totalSats = bal ? (bal.confirmed || 0) + (bal.unconfirmed || 0) : 0;

  return (
    <div className="fade-in" style={{ paddingBottom: 80 }}>
      {/* Balance */}
      <div style={{ background: `linear-gradient(180deg, ${T.surface} 0%, ${T.bg} 100%)`,
        borderBottom: `1px solid ${T.border}`, padding: "28px 20px 20px", textAlign: "center" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginBottom: 12 }}>
          <Dot on={nodeOk} />
          <span style={{ color: T.muted, fontSize: 10, letterSpacing: "0.1em" }}>BITCOIN BALANCE</span>
        </div>
        {loading ? (
          <div style={{ fontSize: 32, color: T.muted }}><Spinner /></div>
        ) : (
          <>
            <div style={{ fontSize: 32, fontWeight: 700, color: T.accent, letterSpacing: "-0.02em", lineHeight: 1 }}>
              {fmtBtc(totalSats)}
            </div>
            {bal?.unconfirmed > 0 && (
              <div style={{ color: T.yellow, fontSize: 11, marginTop: 6 }}>
                +{fmtBtc(bal.unconfirmed)} pending
              </div>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, padding: "14px 14px 0" }}>
        <Btn onClick={() => onNav("send")} style={{ flex: 1, padding: 12 }}>↑ SEND</Btn>
        <Btn variant="ghost" onClick={() => onNav("receive")} style={{ flex: 1, padding: 12 }}>↓ RECEIVE</Btn>
      </div>

      {/* Address */}
      <div style={{ padding: "14px" }}>
        <Card>
          <Label>YOUR BITCOIN ADDRESS</Label>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ flex: 1, fontSize: 11, color: T.muted, wordBreak: "break-all", lineHeight: 1.6 }}>
              {wallet?.address || "—"}
            </div>
            <Btn variant="ghost" onClick={() => copyText(wallet?.address)}
              style={{ flexShrink: 0, padding: "6px 10px", fontSize: 11 }}>copy</Btn>
          </div>
        </Card>
      </div>

      {/* Recent txs */}
      <div style={{ padding: "0 14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
          <Label>RECENT TRANSACTIONS</Label>
          {txs.length > 0 && (
            <button onClick={() => onNav("history")}
              style={{ background: "none", color: T.muted, fontSize: 11, cursor: "pointer" }}>all →</button>
          )}
        </div>
        {loading ? (
          <div style={{ textAlign: "center", padding: 24 }}><Spinner /></div>
        ) : txs.length === 0 ? (
          <div style={{ color: T.muted, fontSize: 12, textAlign: "center", padding: "20px 0" }}>No transactions yet</div>
        ) : (
          txs.map((tx, i) => <TxRow key={i} tx={tx} />)
        )}
      </div>
    </div>
  );
}

function TxRow({ tx }) {
  const isIn = tx.direction === "in";
  const conf = tx.confirmed;
  return (
    <div style={{ display: "flex", alignItems: "center",
      padding: "10px 12px", background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 5, marginBottom: 6 }}>
      <div style={{ width: 30, height: 30, borderRadius: "50%",
        background: isIn ? "rgba(76,175,80,0.1)" : "rgba(247,147,26,0.1)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 14, marginRight: 10, flexShrink: 0 }}>
        {isIn ? "↓" : "↑"}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, color: T.muted, whiteSpace: "nowrap",
          overflow: "hidden", textOverflow: "ellipsis" }}>
          {trunc(tx.txid, 14, 6)}
        </div>
        <div style={{ fontSize: 10, color: conf ? T.muted : T.yellow, marginTop: 2 }}>
          {conf ? `block ${tx.height}` : "⏳ unconfirmed"}
        </div>
      </div>
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        {tx.amount > 0 && (
          <div style={{ fontWeight: 600, color: isIn ? T.green : T.accent, fontSize: 12 }}>
            {isIn ? "+" : "-"}{fmtBtc(tx.amount)}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Send ──────────────────────────────────────────────────────────────────────
function ScreenSend() {
  const [to, setTo] = useState(""); const [amount, setAmount] = useState("");
  const [feeRate, setFeeRate] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [success, setSuccess] = useState(null);
  const [feeEstimates, setFeeEstimates] = useState(null);

  useEffect(() => {
    api("/fee").then(r => r.ok && setFeeEstimates(r));
  }, []);

  const doPreview = async () => {
    if (!to.trim() || !amount) return setError("Fill in all fields");
    setError(""); setLoading(true);
    const r = await api("/send/preview", { to: to.trim(), amount: parseFloat(amount), fee_rate: feeRate });
    setLoading(false);
    if (!r.ok) return setError(r.error);
    setPreview(r);
  };

  const doSend = async () => {
    setLoading(true); setError("");
    const r = await api("/send", { to: to.trim(), amount: parseFloat(amount), fee_rate: feeRate });
    setLoading(false);
    if (!r.ok) { setPreview(null); return setError(r.error); }
    setSuccess(r);
  };

  if (success) return (
    <div className="fade-in" style={{ padding: "60px 24px", textAlign: "center", maxWidth: 400, margin: "0 auto" }}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>✓</div>
      <div style={{ color: T.accent, fontWeight: 700, fontSize: 16, marginBottom: 8 }}>Transaction broadcast</div>
      <div style={{ color: T.muted, fontSize: 12, marginBottom: 4 }}>{fmtBtc(success.amount)} sent</div>
      <div style={{ color: T.muted, fontSize: 11, marginBottom: 20 }}>
        <a href={`https://mempool.space/tx/${success.txid}`} target="_blank"
          style={{ color: T.accent }}>{trunc(success.txid, 14, 8)}</a>
      </div>
      <Btn style={{ width: "100%" }} onClick={() => { setSuccess(null); setTo(""); setAmount(""); setPreview(null); }}>
        SEND ANOTHER
      </Btn>
    </div>
  );

  return (
    <div className="fade-in" style={{ padding: "20px", maxWidth: 420, margin: "0 auto" }}>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 18 }}>Send Bitcoin</div>

      <Field label="Recipient address" value={to} onChange={e => { setTo(e.target.value); setPreview(null); }}
        placeholder="bc1q…  or  1…  or  3…" />
      <Field label="Amount (BTC)" type="number" value={amount} min="0" step="0.00001"
        onChange={e => { setAmount(e.target.value); setPreview(null); }} placeholder="0.00100000" />

      {/* Fee selector */}
      <div style={{ marginBottom: 14 }}>
        <Label>FEE RATE (SAT/VBYTE)</Label>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {[
            { label: "slow", blocks: 6 },
            { label: "normal", blocks: 3 },
            { label: "fast", blocks: 1 },
          ].map(({ label, blocks }) => {
            const rate = feeEstimates?.[`${blocks}b`] || (blocks === 1 ? 20 : blocks === 3 ? 10 : 5);
            return (
              <button key={label} onClick={() => { setFeeRate(rate); setPreview(null); }}
                style={{ padding: "6px 12px", borderRadius: 4, fontSize: 11,
                  background: feeRate === rate ? T.accentDim : T.surface2,
                  color: feeRate === rate ? T.accent : T.muted,
                  border: `1px solid ${feeRate === rate ? T.accent : T.border}` }}>
                {label} · {rate} sat/vB
              </button>
            );
          })}
          <input type="number" value={feeRate} min={1}
            onChange={e => { setFeeRate(parseInt(e.target.value)||1); setPreview(null); }}
            style={{ width: 80, padding: "6px 10px", fontSize: 11 }} placeholder="custom" />
        </div>
      </div>

      {preview && (
        <Card style={{ marginBottom: 14, borderColor: `${T.yellow}44` }}>
          <div style={{ color: T.yellow, fontSize: 11, marginBottom: 10 }}>⚠ Review before sending</div>
          <div style={{ fontSize: 12, lineHeight: 2.2, color: T.muted }}>
            {[
              ["To", trunc(to, 14, 8)],
              ["Amount", fmtBtc(preview.amount)],
              ["Fee", `${fmtBtc(preview.fee)} (${feeRate} sat/vB)`],
              ["Total", fmtBtc(preview.total)],
              ["Inputs", `${preview.inputs_used} UTXO(s)`],
            ].map(([k, v]) => (
              <div key={k}>{k}: <span style={{ color: k === "Total" ? T.accent : T.text, fontWeight: k==="Total"?"700":"400" }}>{v}</span></div>
            ))}
          </div>
        </Card>
      )}

      <ErrBox msg={error} />

      {!preview ? (
        <Btn style={{ width: "100%", marginTop: 8, padding: 14 }} onClick={doPreview} disabled={loading}>
          {loading ? <Spinner /> : "REVIEW TRANSACTION →"}
        </Btn>
      ) : (
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="ghost" onClick={() => setPreview(null)} style={{ flex: 1, padding: 13 }}>BACK</Btn>
          <Btn style={{ flex: 2, padding: 13 }} onClick={doSend} disabled={loading}>
            {loading ? <Spinner /> : "CONFIRM & BROADCAST"}
          </Btn>
        </div>
      )}
    </div>
  );
}

// ── Receive ───────────────────────────────────────────────────────────────────
function ScreenReceive({ wallet }) {
  const [copied, setCopied] = useState(false);
  const copy = () => { copyText(wallet?.address); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <div className="fade-in" style={{ padding: "20px", maxWidth: 420, margin: "0 auto" }}>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 18 }}>Receive Bitcoin</div>
      <Card style={{ textAlign: "center", padding: "28px 20px", marginBottom: 14 }}>
        <div style={{ width: 64, height: 64, borderRadius: "50%", background: T.accentDim,
          border: `2px solid ${T.accent}44`, display: "flex", alignItems: "center",
          justifyContent: "center", margin: "0 auto 16px", fontSize: 24, color: T.accent }}>₿</div>
        <div style={{ fontSize: 10, color: T.muted, letterSpacing: "0.12em", marginBottom: 10 }}>NATIVE SEGWIT (bc1…)</div>
        <div style={{ fontSize: 12, wordBreak: "break-all", lineHeight: 1.8, color: T.text }}>
          {wallet?.address}
        </div>
      </Card>
      <Btn style={{ width: "100%", padding: 14 }} onClick={copy}>
        {copied ? "✓ COPIED" : "COPY ADDRESS"}
      </Btn>
      <div style={{ marginTop: 14, padding: "10px 14px", background: T.surface2,
        borderRadius: 5, color: T.muted, fontSize: 11, lineHeight: 1.8 }}>
        This is a Native SegWit address (bech32).<br />
        Accepted by all major wallets and exchanges.
      </div>
    </div>
  );
}

// ── History ───────────────────────────────────────────────────────────────────
function ScreenHistory() {
  const [txs, setTxs] = useState([]); const [loading, setLoading] = useState(true);
  useEffect(() => {
    api("/transactions?limit=50").then(r => { if (r.ok) setTxs(r.transactions || []); setLoading(false); });
  }, []);
  return (
    <div className="fade-in" style={{ paddingBottom: 80 }}>
      <div style={{ padding: "16px 14px 10px", fontWeight: 700, fontSize: 15 }}>History</div>
      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner /></div>
      ) : txs.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40, color: T.muted, fontSize: 12 }}>No transactions found</div>
      ) : (
        <div style={{ padding: "0 10px" }}>
          {txs.map((tx, i) => (
            <div key={i} style={{ padding: "10px 12px", background: T.surface,
              border: `1px solid ${T.border}`, borderRadius: 5, marginBottom: 6 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: T.muted }}>{trunc(tx.txid, 16, 8)}</span>
                <span style={{ fontSize: 10, color: tx.confirmed ? T.muted : T.yellow }}>
                  {tx.confirmed ? `✓ ${tx.height}` : "⏳ pending"}
                </span>
              </div>
              <a href={`https://mempool.space/tx/${tx.txid}`} target="_blank"
                style={{ fontSize: 10, color: T.accent }}>view on mempool.space ↗</a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Settings ──────────────────────────────────────────────────────────────────
function ScreenSettings({ wallet, onLocked }) {
  const [node, setNode] = useState(null); const [loading, setLoading] = useState(true);
  useEffect(() => { api("/node/status").then(r => { setNode(r); setLoading(false); }); }, []);
  const doLock = async () => { await api("/wallet/lock", {}); onLocked(); };
  return (
    <div className="fade-in" style={{ padding: "20px 14px 80px", maxWidth: 420, margin: "0 auto" }}>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 18 }}>Settings</div>

      <Card style={{ marginBottom: 14 }}>
        <Label>ELECTRUMX SERVER</Label>
        {loading ? <Spinner /> : node?.connected ? (
          <div style={{ fontSize: 12, lineHeight: 2, color: T.muted }}>
            <div><Dot on color={T.green} />{node.server}:{node.port}</div>
            <div style={{ marginLeft: 13 }}>Protocol: {node.protocol} · Block: {node.height?.toLocaleString()} · {node.latency_ms}ms</div>
          </div>
        ) : (
          <div style={{ color: T.red, fontSize: 12 }}><Dot on color={T.red} />{node?.error || "Disconnected"}</div>
        )}
      </Card>

      <Card style={{ marginBottom: 14 }}>
        <Label>WALLET</Label>
        <div style={{ fontSize: 11, color: T.muted, wordBreak: "break-all", lineHeight: 1.7 }}>
          {wallet?.address}
        </div>
        {wallet?.network && (
          <div style={{ marginTop: 8, fontSize: 11 }}>
            <span style={{ background: T.accentDim, color: T.accent,
              padding: "2px 8px", borderRadius: 10, fontSize: 10, letterSpacing: "0.08em" }}>
              {wallet.network?.toUpperCase()}
            </span>
          </div>
        )}
      </Card>

      <Card>
        <Label>SECURITY</Label>
        <div style={{ color: T.muted, fontSize: 12, marginBottom: 12 }}>
          Lock wallet to clear keys from memory.
        </div>
        <Btn variant="danger" onClick={doLock} style={{ width: "100%" }}>LOCK WALLET</Btn>
      </Card>

      <div style={{ textAlign: "center", marginTop: 24, color: T.muted, fontSize: 11 }}>
        Nulla v1.0.0 · Bitcoin Light Wallet<br />
        <span style={{ fontSize: 10 }}>Connects via ElectrumX Protocol</span>
      </div>
    </div>
  );
}

// ── Addresses ────────────────────────────────────────────────────────────────
function ScreenAddresses() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState("");
  const [copied, setCopied] = useState("");
  const [showChange, setShowChange] = useState(false);

  const TYPE_COLOR = {
    "p2wpkh":      T.accent,
    "p2sh-p2wpkh": "#a78bfa",
    "p2pkh":       T.muted,
  };

  const loading_ref = useRef(false);

  const load = async () => {
    if (loading_ref.current) return;
    loading_ref.current = true;
    setLoading(true);
    const r = await api("/addresses");
    if (r.ok) setGroups(r.groups || []);
    setLoading(false);
    loading_ref.current = false;
  };

  useEffect(() => { load(); }, []);

  const doScan = async () => {
    setScanning(true); setScanMsg("");
    const r = await api("/scan", {});
    setScanning(false);
    setScanMsg(r.ok ? `✓ ${r.message}` : `✗ ${r.error}`);
    if (r.ok) load();
  };

  const copy = (addr) => {
    copyText(addr);
    setCopied(addr);
    setTimeout(() => setCopied(""), 1500);
  };

  return (
    <div className="fade-in" style={{ paddingBottom: 80 }}>
      <div style={{ padding: "14px 14px 10px", display: "flex",
        alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontWeight: 700, fontSize: 15 }}>Addresses</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={() => setShowChange(v => !v)}
            style={{ background: showChange ? T.accentDim : "transparent",
              color: showChange ? T.accent : T.muted, border: `1px solid ${T.border}`,
              borderRadius: 4, padding: "4px 10px", fontSize: 11, cursor: "pointer" }}>
            {showChange ? "hide change" : "show change"}
          </button>
          <Btn variant="ghost" onClick={doScan} disabled={scanning}
            style={{ padding: "6px 12px", fontSize: 11 }}>
            {scanning ? <Spinner /> : "⟳ scan"}
          </Btn>
        </div>
      </div>

      {scanMsg && (
        <div style={{ margin: "0 14px 10px", padding: "8px 12px", borderRadius: 4,
          background: scanMsg.startsWith("✓") ? "rgba(0,229,160,0.08)" : "rgba(255,82,82,0.08)",
          color: scanMsg.startsWith("✓") ? T.green : T.red, fontSize: 12 }}>
          {scanMsg}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: 40 }}><Spinner /></div>
      ) : groups.map(group => {
        const addrs = group.addresses.filter(a => showChange || !a.is_change);
        if (!addrs.length) return null;
        return (
          <div key={group.type} style={{ padding: "0 10px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8,
              padding: "6px 4px 8px" }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%",
                background: TYPE_COLOR[group.type] || T.muted }} />
              <span style={{ fontSize: 11, fontWeight: 600,
                color: TYPE_COLOR[group.type] || T.muted,
                letterSpacing: "0.08em" }}>
                {group.label}
              </span>
              <span style={{ fontSize: 10, color: T.muted }}>{group.bip}</span>
            </div>

            {addrs.map((a, i) => {
              const total = (a.confirmed || 0) + (a.unconfirmed || 0);
              const isCopied = copied === a.address;
              return (
                <div key={i} style={{ background: T.surface,
                  border: `1px solid ${a.has_balance ? TYPE_COLOR[group.type] + "33" : T.border}`,
                  borderRadius: 5, padding: "10px 12px", marginBottom: 6,
                  opacity: a.is_change ? 0.7 : 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "flex-start", gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, wordBreak: "break-all",
                        lineHeight: 1.6, color: a.has_balance ? T.text : T.muted,
                        fontFamily: T.font }}>
                        {a.address}
                      </div>
                      <div style={{ fontSize: 10, color: T.muted, marginTop: 3 }}>
                        {a.path}
                        {a.is_change && <span style={{ marginLeft: 6, color: T.yellow,
                          background: "rgba(255,209,102,0.1)", padding: "1px 6px",
                          borderRadius: 3 }}>change</span>}
                      </div>
                    </div>
                    <div style={{ textAlign: "right", flexShrink: 0 }}>
                      {total > 0 && (
                        <div style={{ fontWeight: 600, fontSize: 12,
                          color: TYPE_COLOR[group.type] }}>
                          {fmtBtc(total)}
                        </div>
                      )}
                      <button onClick={() => copy(a.address)}
                        style={{ background: "none", color: isCopied ? T.green : T.muted,
                          fontSize: 11, cursor: "pointer", marginTop: 4 }}>
                        {isCopied ? "✓" : "copy"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}


// ── Navigation ────────────────────────────────────────────────────────────────
const NAV = [
  { id: "dashboard",  label: "Home",    icon: "◈" },
  { id: "send",       label: "Send",    icon: "↑" },
  { id: "receive",    label: "Receive", icon: "↓" },
  { id: "addresses",  label: "Addrs",   icon: "⊞" },
  { id: "settings",   label: "Config",  icon: "⚙" },
];

function BottomNav({ active, onChange }) {
  return (
    <div style={{ position: "fixed", bottom: 0, left: 0, right: 0,
      background: T.surface, borderTop: `1px solid ${T.border}`,
      display: "flex", zIndex: 100,
      paddingBottom: "env(safe-area-inset-bottom)" }}>
      {NAV.map(n => (
        <button key={n.id} onClick={() => onChange(n.id)}
          style={{ flex: 1, padding: "12px 0", background: "transparent",
            color: active === n.id ? T.accent : T.muted,
            display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
            borderTop: active === n.id ? `2px solid ${T.accent}` : "2px solid transparent",
            transition: "color 0.15s" }}>
          <span style={{ fontSize: 16, lineHeight: 1 }}>{n.icon}</span>
          <span style={{ fontSize: 9, letterSpacing: "0.06em" }}>{n.label}</span>
        </button>
      ))}
    </div>
  );
}

// ── App root ──────────────────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState("loading");
  const [tab, setTab] = useState("dashboard");
  const [wallet, setWallet] = useState(null);

  useEffect(() => {
    const style = document.createElement("style");
    style.textContent = GLOBAL_CSS;
    document.head.appendChild(style);
    document.body.style.background = T.bg;
    return () => document.head.removeChild(style);
  }, []);

  useEffect(() => {
    (async () => {
      const r = await api("/status");
      if (r.wallet_unlocked) {
        const info = await api("/wallet/info");
        if (info.ok) { setWallet({ address: info.address, network: info.network }); setScreen("app"); return; }
      }
      setScreen(r.wallet_exists ? "unlock" : "setup");
    })();
  }, []);

  if (screen === "loading") return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center",
      height: "100vh", flexDirection: "column", gap: 14, color: T.accent }}>
      <div style={{ fontSize: 28, fontWeight: 700 }}>NULLA</div>
      <Spinner />
    </div>
  );
  if (screen === "setup") return <div style={{ minHeight: "100vh", background: T.bg }}><ScreenSetup onDone={a => { setWallet({ address: a }); setScreen("app"); }} /></div>;
  if (screen === "unlock") return <div style={{ minHeight: "100vh", background: T.bg }}><ScreenUnlock onDone={a => { setWallet({ address: a }); setScreen("app"); }} /></div>;

  return (
    <div style={{ minHeight: "100vh", background: T.bg, maxWidth: 480, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ position: "sticky", top: 0, zIndex: 99, background: T.bg,
        borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center",
        padding: "12px 16px", paddingTop: "calc(12px + env(safe-area-inset-top))" }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: T.accent, letterSpacing: "0.1em", flex: 1 }}>NULLA</span>
        <span style={{ fontSize: 10, color: T.muted, letterSpacing: "0.1em" }}>₿ BITCOIN</span>
      </div>

      <div style={{ paddingBottom: 60 }}>
        {tab === "dashboard" && <ScreenDashboard wallet={wallet} onNav={setTab} />}
        {tab === "send"      && <ScreenSend />}
        {tab === "receive"   && <ScreenReceive wallet={wallet} />}
        {tab === "history"   && <ScreenHistory />}
        {tab === "addresses" && <ScreenAddresses />}
        {tab === "settings"  && <ScreenSettings wallet={wallet} onLocked={() => { setWallet(null); setScreen("unlock"); }} />}
      </div>
      <BottomNav active={tab} onChange={setTab} />
    </div>
  );
}
