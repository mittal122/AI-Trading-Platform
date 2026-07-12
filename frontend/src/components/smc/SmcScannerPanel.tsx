import { useCallback, useEffect, useState } from 'react'
import { Pause, Play, X } from 'lucide-react'
import {
  getSmcWatchlist, addSmcWatch, toggleSmcWatch, removeSmcWatch,
  getScannerSettings, updateScannerSettings, scanSmcNow,
  getSmcSignals, acceptSmcSignal, dismissSmcSignal,
} from '../../api/client'
import type { SmcWatchItem, SmcScannerSettings, SmcSignal } from '../../api/client'
import SymbolSearchInput from '../SymbolSearchInput'

const INTERVALS = ['5m', '15m', '30m', '1h', '4h', '1d']
const STATUS_CHIP: Record<string, string> = {
  new: 'chip-warn', accepted: 'chip-up', dismissed: 'chip-muted',
}

// The scanner watches symbols in the background (server-side, every 60s) and
// stores high-confluence fired setups. This panel is its control surface.
export default function SmcScannerPanel() {
  const [watches, setWatches] = useState<SmcWatchItem[]>([])
  const [settings, setSettings] = useState<SmcScannerSettings>({ enabled: false, max_signals_per_week: 4 })
  const [signals, setSignals] = useState<SmcSignal[]>([])
  const [addSym, setAddSym] = useState('BTCUSDT')
  const [addInt, setAddInt] = useState('1h')
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    const [w, s, sig] = await Promise.allSettled([getSmcWatchlist(), getScannerSettings(), getSmcSignals()])
    if (w.status === 'fulfilled') setWatches(w.value.data)
    if (s.status === 'fulfilled') setSettings(s.value.data)
    if (sig.status === 'fulfilled') setSignals(sig.value.data)
  }, [])

  useEffect(() => {
    refresh()
    const t = window.setInterval(refresh, 30000)  // signals arrive server-side; poll
    return () => window.clearInterval(t)
  }, [refresh])

  async function saveSettings(next: SmcScannerSettings) {
    setSettings(next)
    await updateScannerSettings(next)
  }
  async function add() {
    await addSmcWatch(addSym, addInt); refresh()
  }
  async function scanNow() {
    setBusy(true)
    try { await scanSmcNow(); await refresh() } finally { setBusy(false) }
  }

  const pending = signals.filter(s => s.status === 'new')
  const history = signals.filter(s => s.status !== 'new').slice(0, 10)

  return (
    <div className="card card-pad space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="panel-title">Signal Scanner</p>
          <p className="text-xs text-fg-faint">Watches your list server-side every 60s; stores only high-confluence fired setups.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-fg-soft cursor-pointer">
            <input type="checkbox" checked={settings.enabled}
              onChange={e => saveSettings({ ...settings, enabled: e.target.checked })}
              className="accent-[#f5a623]" />
            Enabled
          </label>
          <label className="flex items-center gap-1.5 text-xs text-fg-soft">
            Max / week
            <select value={settings.max_signals_per_week}
              onChange={e => saveSettings({ ...settings, max_signals_per_week: Number(e.target.value) })}
              className="input !h-7 w-14 text-xs">
              {[2, 3, 4].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <button onClick={scanNow} disabled={busy} className="btn !h-7 !text-xs">
            {busy ? 'Scanning…' : 'Scan now'}
          </button>
        </div>
      </div>

      {!settings.enabled && (
        <p className="text-xs text-accent/90">Scanner is off — turn it on to store new signals. The watchlist still tracks candles.</p>
      )}

      {/* Watchlist */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-40"><SymbolSearchInput value={addSym} onCommit={setAddSym} /></div>
          <select value={addInt} onChange={e => setAddInt(e.target.value)}
            className="input w-20 text-xs">
            {INTERVALS.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
          <button onClick={add} className="btn btn-primary !text-xs">Add watch</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {watches.length === 0 && <p className="text-xs text-fg-faint">No symbols watched yet.</p>}
          {watches.map(w => (
            <span key={w.id} className={`flex items-center gap-2 text-xs px-2 py-1 rounded-md border border-line bg-raised ${
              w.active ? 'text-fg-soft' : 'text-fg-faint'}`}>
              <button onClick={() => toggleSmcWatch(w.id, !w.active).then(refresh)}
                aria-label={w.active ? `Pause ${w.symbol}` : `Resume ${w.symbol}`}
                title={w.active ? 'Pause' : 'Resume'}
                className={`cursor-pointer ${w.active ? 'text-up' : 'text-fg-faint'}`}>
                {w.active ? <Pause size={11} /> : <Play size={11} />}
              </button>
              {w.symbol} <span className="text-fg-faint">{w.interval}</span>
              <button onClick={() => removeSmcWatch(w.id).then(refresh)}
                aria-label={`Remove ${w.symbol}`}
                className="text-fg-faint hover:text-down cursor-pointer"><X size={12} /></button>
            </span>
          ))}
        </div>
      </div>

      {/* Pending signals */}
      <div>
        <p className="field-label mb-2">Pending signals ({pending.length})</p>
        {pending.length === 0 && <p className="text-xs text-fg-faint">No pending signals. Strong SMC setups are rare — the scanner waits for one.</p>}
        <div className="space-y-2">
          {pending.map(s => (
            <div key={s.id} className="bg-raised border border-line rounded-md p-3 flex items-center flex-wrap gap-x-4 gap-y-2">
              <span className={`text-sm font-bold uppercase ${s.side === 'long' ? 'text-up' : 'text-down'}`}>{s.side}</span>
              <span className="text-sm text-fg-soft">{s.symbol} <span className="text-fg-faint">{s.interval}</span></span>
              <span className="num text-xs text-fg-faint">Entry {s.entry.toPrecision(6)} · SL {s.stop_loss.toPrecision(6)} · TP {s.take_profit_1.toPrecision(6)}</span>
              <span className="num text-xs text-fg-faint">{s.score}/110</span>
              <div className="ml-auto flex gap-2">
                <button onClick={() => acceptSmcSignal(s.id).then(refresh)}
                  className={`btn !h-7 !text-xs ${s.side === 'long' ? 'btn-buy' : 'btn-sell'}`}>Accept (paper)</button>
                <button onClick={() => dismissSmcSignal(s.id).then(refresh)}
                  className="btn !h-7 !text-xs">Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div>
          <p className="field-label mb-2">Recent</p>
          <div className="space-y-1">
            {history.map(s => (
              <div key={s.id} className="flex items-center gap-3 text-xs">
                <span className={`chip ${STATUS_CHIP[s.status]}`}>{s.status}</span>
                <span className={s.side === 'long' ? 'text-up' : 'text-down'}>{s.side}</span>
                <span className="text-fg-soft">{s.symbol} {s.interval}</span>
                <span className="num text-fg-faint">{s.score}/110</span>
                {s.paired_trade_id && <span className="num text-fg-faint">→ paper #{s.paired_trade_id}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
