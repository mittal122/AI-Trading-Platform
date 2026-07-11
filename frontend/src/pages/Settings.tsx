import { useEffect, useState } from 'react'
import { Check, Circle } from 'lucide-react'
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
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* Admin token — only needed when the deployment locks money endpoints
          (ADMIN_API_TOKEN set server-side). Blank on single-operator localhost. */}
      <section className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2">
          <h2 className="panel-title">Admin Access Token</h2>
        </header>
        <div className="px-3 pb-3 space-y-3">
          <p className="text-xs text-fg-faint">
            Only required if this deployment has locked the sensitive actions (saving Binance keys,
            starting live trading, deleting all history) behind an admin token. Leave blank for a
            local single-operator setup. Stored only in this browser and sent as an <code className="text-accent">X-Admin-Token</code> header.
          </p>
          <div className="flex items-center gap-3">
            <input type="password" autoComplete="off" value={adminToken}
              onChange={e => setAdminTokenInput(e.target.value)} placeholder="admin token (optional)"
              className="input input-mono flex-1 max-w-md" />
            <button onClick={saveAdmin} className="btn btn-primary">
              Save
            </button>
            {adminSaved && (
              <span className="text-xs text-up flex items-center gap-1">
                <Check size={12} aria-label="saved" /> Saved for this browser
              </span>
            )}
          </div>
        </div>
      </section>

      <section className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2">
          <h2 className="panel-title">Binance Account (Live Trading)</h2>
          {status && (
            <span className={`chip ${status.configured ? 'chip-up' : 'chip-muted'}`}>
              {status.configured ? `Configured — ${status.key_preview}` : 'Not configured'}
            </span>
          )}
        </header>
        <div className="px-3 pb-3 space-y-3">
          <p className="text-xs text-fg-faint">
            Enter your own Binance API key/secret to place real orders in Live Trading.
            Stored encrypted in the database, never shown again after saving.
            Leave blank to keep using Paper Trading / dry-run mode only.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="field-label">API Key</label>
              <input
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder={status?.configured ? '••••••••••••••••' : 'Binance API key'}
                className="input input-mono w-full"
              />
            </div>
            <div>
              <label className="field-label">API Secret</label>
              <input
                type="password"
                autoComplete="off"
                value={apiSecret}
                onChange={e => setApiSecret(e.target.value)}
                placeholder={status?.configured ? '••••••••••••••••' : 'Binance API secret'}
                className="input input-mono w-full"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving || apiKey.trim().length < 10 || apiSecret.trim().length < 10}
              className="btn btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving…' : 'Save Keys'}
            </button>
            {status?.configured && (
              <button
                onClick={handleRemove}
                className={`btn ${confirmRemove ? 'btn-sell' : 'btn-danger-outline'}`}
              >
                {confirmRemove ? 'Click again to confirm' : 'Remove Keys'}
              </button>
            )}
            {message && (
              <span className={`text-xs ${message.error ? 'text-down' : 'text-up'}`}>{message.text}</span>
            )}
          </div>
        </div>
      </section>

      <section className="card">
        <header className="px-3 pt-3 pb-2">
          <h2 className="panel-title">Environment Variables Required</h2>
        </header>
        <div className="px-3 pb-2">
          {[
            ['NVIDIA_API_KEY', 'Required for all AI features — routes to NVIDIA NIM (chat, analyst, validator, etc.)'],
            ['BINANCE_API_KEY', 'Fallback only — prefer the Binance Account form above'],
            ['BINANCE_SECRET', 'Fallback only — prefer the Binance Account form above'],
            ['DATABASE_URL', 'Optional — defaults to SQLite (trading.db)'],
            ['MARKET_ANALYST_MODEL', 'Optional — defaults to nemotron-3-super'],
            ['CHAT_ASSISTANT_MODEL', 'Optional — defaults to kimi-k2.5'],
          ].map(([k, v]) => (
            <div key={k} className="flex items-start gap-3 py-1.5 border-b border-line/50 last:border-0">
              <code className="num text-[11px] text-accent bg-accent-soft px-1.5 py-0.5 rounded shrink-0">{k}</code>
              <p className="text-xs text-fg-faint">{v}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <header className="px-3 pt-3 pb-2">
          <h2 className="panel-title">Phase Completion</h2>
        </header>
        <div className="px-3 pb-2">
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
            <div key={String(phase)} className="flex items-center gap-3 py-1.5 border-b border-line/50 last:border-0">
              {done
                ? <Check size={14} className="text-up shrink-0" aria-label="complete" />
                : <Circle size={14} className="text-fg-faint shrink-0" aria-label="incomplete" />}
              <span className="num text-[11px] text-fg-faint w-16">{phase}</span>
              <span className={`text-[12.5px] ${done ? 'text-fg-soft' : 'text-fg-faint'}`}>{label}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
