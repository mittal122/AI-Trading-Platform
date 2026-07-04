import { useEffect, useState } from 'react'
import { deleteBinanceKeys, getBinanceKeyStatus, saveBinanceKeys, getAdminToken, setAdminToken } from '../api/client'

export default function Settings() {
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [status, setStatus] = useState<{ configured: boolean; key_preview: string | null } | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const [adminToken, setAdminTokenInput] = useState(getAdminToken())
  const [adminSaved, setAdminSaved] = useState(false)

  useEffect(() => {
    getBinanceKeyStatus().then(res => setStatus(res.data)).catch(() => setStatus({ configured: false, key_preview: null }))
  }, [])

  useEffect(() => {
    if (!confirmRemove) return
    const t = setTimeout(() => setConfirmRemove(false), 4000)
    return () => clearTimeout(t)
  }, [confirmRemove])

  async function handleSave() {
    setSaving(true)
    setMessage(null)
    try {
      const res = await saveBinanceKeys({ api_key: apiKey.trim(), api_secret: apiSecret.trim() })
      setStatus(res.data)
      setApiKey('')
      setApiSecret('')
      setMessage({ text: 'Binance API keys saved.' })
    } catch (e: any) {
      setMessage({ text: e?.response?.data?.detail ?? 'Failed to save keys.', error: true })
    } finally {
      setSaving(false)
    }
  }

  async function handleRemove() {
    if (!confirmRemove) {
      setConfirmRemove(true)
      return
    }
    setConfirmRemove(false)
    try {
      const res = await deleteBinanceKeys()
      setStatus(res.data)
      setMessage({ text: 'Binance API keys removed.' })
    } catch {
      setMessage({ text: 'Failed to remove keys.', error: true })
    }
  }

  function saveAdmin() {
    setAdminToken(adminToken.trim())
    setAdminSaved(true)
    setTimeout(() => setAdminSaved(false), 2500)
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      {/* Admin token — only needed when the deployment locks money endpoints
          (ADMIN_API_TOKEN set server-side). Blank on single-operator localhost. */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-300">Admin Access Token</h2>
        <p className="text-xs text-slate-500">
          Only required if this deployment has locked the sensitive actions (saving Binance keys,
          starting live trading, deleting all history) behind an admin token. Leave blank for a
          local single-operator setup. Stored only in this browser and sent as an <code className="text-indigo-400">X-Admin-Token</code> header.
        </p>
        <div className="flex items-center gap-3">
          <input type="password" autoComplete="off" value={adminToken}
            onChange={e => setAdminTokenInput(e.target.value)} placeholder="admin token (optional)"
            className="flex-1 max-w-md bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500" />
          <button onClick={saveAdmin}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm text-white font-medium">
            Save
          </button>
          {adminSaved && <span className="text-xs text-green-400">✓ Saved for this browser</span>}
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">Binance Account (Live Trading)</h2>
          {status && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${status.configured ? 'bg-green-500/10 text-green-400' : 'bg-slate-700/40 text-slate-500'}`}>
              {status.configured ? `Configured — ${status.key_preview}` : 'Not configured'}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">
          Enter your own Binance API key/secret to place real orders in Live Trading.
          Stored encrypted in the database, never shown again after saving.
          Leave blank to keep using Paper Trading / dry-run mode only.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">API Key</label>
            <input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={status?.configured ? '••••••••••••••••' : 'Binance API key'}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">API Secret</label>
            <input
              type="password"
              autoComplete="off"
              value={apiSecret}
              onChange={e => setApiSecret(e.target.value)}
              placeholder={status?.configured ? '••••••••••••••••' : 'Binance API secret'}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving || apiKey.trim().length < 10 || apiSecret.trim().length < 10}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm text-white font-medium"
          >
            {saving ? 'Saving…' : 'Save Keys'}
          </button>
          {status?.configured && (
            <button
              onClick={handleRemove}
              className={`px-4 py-2 rounded-lg text-sm font-medium border ${confirmRemove ? 'bg-red-600 border-red-600 text-white' : 'border-[#2a2d3e] text-slate-400 hover:text-red-400'}`}
            >
              {confirmRemove ? 'Click again to confirm' : 'Remove Keys'}
            </button>
          )}
          {message && (
            <span className={`text-xs ${message.error ? 'text-red-400' : 'text-green-400'}`}>{message.text}</span>
          )}
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-300">Environment Variables Required</h2>
        {[
          ['NVIDIA_API_KEY', 'Required for all AI features — routes to NVIDIA NIM (chat, analyst, validator, etc.)'],
          ['BINANCE_API_KEY', 'Fallback only — prefer the Binance Account form above'],
          ['BINANCE_SECRET', 'Fallback only — prefer the Binance Account form above'],
          ['DATABASE_URL', 'Optional — defaults to SQLite (trading.db)'],
          ['MARKET_ANALYST_MODEL', 'Optional — defaults to nemotron-3-super'],
          ['CHAT_ASSISTANT_MODEL', 'Optional — defaults to kimi-k2.5'],
        ].map(([k, v]) => (
          <div key={k} className="flex items-start gap-3 py-2 border-b border-[#2a2d3e]/50 last:border-0">
            <code className="text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded shrink-0">{k}</code>
            <p className="text-xs text-slate-500">{v}</p>
          </div>
        ))}
      </div>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Phase Completion</h2>
        {[
          ['Phase 1', 'Core Infrastructure', true],
          ['Phase 2', 'Professional Strategy System', true],
          ['Phase 3', 'Advanced Risk Management', true],
          ['Phase 4', 'Portfolio Analytics', true],
          ['Phase 5', 'AI Integration', true],
          ['Phase 6', 'Paper Trading', true],
          ['Phase 7', 'Live Trading', true],
          ['Phase 8', 'Database Integration', true],
          ['Phase 9', 'Frontend Dashboard', true],
          ['Phase 10', 'SaaS Platform', true],
        ].map(([phase, label, done]) => (
          <div key={String(phase)} className="flex items-center gap-3 py-2 border-b border-[#2a2d3e]/50 last:border-0">
            <span className={`text-sm ${done ? 'text-green-400' : 'text-slate-600'}`}>{done ? '✓' : '○'}</span>
            <span className="text-xs text-slate-500 w-16">{phase}</span>
            <span className={`text-sm ${done ? 'text-slate-300' : 'text-slate-600'}`}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
