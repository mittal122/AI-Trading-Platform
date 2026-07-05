import { useCallback, useEffect, useState } from 'react'
import {
  getSmcWatchlist, addSmcWatch, toggleSmcWatch, removeSmcWatch,
  getScannerSettings, updateScannerSettings, scanSmcNow,
  getSmcSignals, acceptSmcSignal, dismissSmcSignal,
} from '../../api/client'
import type { SmcWatchItem, SmcScannerSettings, SmcSignal } from '../../api/client'
import SymbolSearchInput from '../SymbolSearchInput'

const INTERVALS = ['5m', '15m', '30m', '1h', '4h', '1d']
const STATUS_STYLE: Record<string, string> = {
  new: 'text-indigo-300 bg-indigo-500/10 border-indigo-500/30',
  accepted: 'text-green-400 bg-green-500/10 border-green-500/30',
  dismissed: 'text-slate-500 bg-slate-500/10 border-slate-500/30',
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
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Signal Scanner</p>
          <p className="text-xs text-slate-600">Watches your list server-side every 60s; stores only high-confluence fired setups.</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={settings.enabled}
              onChange={e => saveSettings({ ...settings, enabled: e.target.checked })} />
            Enabled
          </label>
          <label className="flex items-center gap-1.5 text-xs text-slate-400">
            Max / week
            <select value={settings.max_signals_per_week}
              onChange={e => saveSettings({ ...settings, max_signals_per_week: Number(e.target.value) })}
              className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1 text-white outline-none">
              {[2, 3, 4].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <button onClick={scanNow} disabled={busy}
            className="px-3 py-1.5 bg-[#0f1117] border border-[#2a2d3e] text-slate-300 hover:text-white text-xs rounded-lg disabled:opacity-50">
            {busy ? 'Scanning…' : 'Scan now'}
          </button>
        </div>
      </div>

      {!settings.enabled && (
        <p className="text-xs text-yellow-400/80">Scanner is off — turn it on to store new signals. The watchlist still tracks candles.</p>
      )}

      {/* Watchlist */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-40"><SymbolSearchInput value={addSym} onChange={setAddSym} /></div>
          <select value={addInt} onChange={e => setAddInt(e.target.value)}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-2 text-xs text-white outline-none">
            {INTERVALS.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
          <button onClick={add} className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg">Add watch</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {watches.length === 0 && <p className="text-xs text-slate-600">No symbols watched yet.</p>}
          {watches.map(w => (
            <span key={w.id} className={`flex items-center gap-2 text-xs px-2 py-1 rounded-lg border ${
              w.active ? 'border-[#2a2d3e] text-slate-300' : 'border-[#2a2d3e] text-slate-600'}`}>
              <button onClick={() => toggleSmcWatch(w.id, !w.active).then(refresh)}
                title={w.active ? 'Pause' : 'Resume'} className={w.active ? 'text-green-400' : 'text-slate-600'}>●</button>
              {w.symbol} <span className="text-slate-600">{w.interval}</span>
              <button onClick={() => removeSmcWatch(w.id).then(refresh)} className="text-slate-600 hover:text-red-400">✕</button>
            </span>
          ))}
        </div>
      </div>

      {/* Pending signals */}
      <div>
        <p className="text-[10px] uppercase tracking-wide text-slate-600 mb-2">Pending signals ({pending.length})</p>
        {pending.length === 0 && <p className="text-xs text-slate-600">No pending signals. Strong SMC setups are rare — the scanner waits for one.</p>}
        <div className="space-y-2">
          {pending.map(s => (
            <div key={s.id} className="bg-[#0f1117] rounded-lg p-3 flex items-center flex-wrap gap-x-4 gap-y-2">
              <span className={`text-sm font-bold uppercase ${s.side === 'long' ? 'text-green-400' : 'text-red-400'}`}>{s.side}</span>
              <span className="text-sm text-slate-300">{s.symbol} <span className="text-slate-600">{s.interval}</span></span>
              <span className="text-xs text-slate-500">Entry {s.entry.toPrecision(6)} · SL {s.stop_loss.toPrecision(6)} · TP {s.take_profit_1.toPrecision(6)}</span>
              <span className="text-xs text-slate-500">{s.score}/110</span>
              <div className="ml-auto flex gap-2">
                <button onClick={() => acceptSmcSignal(s.id).then(refresh)}
                  className="px-3 py-1 bg-green-600/80 hover:bg-green-600 text-white text-xs rounded-lg">Accept (paper)</button>
                <button onClick={() => dismissSmcSignal(s.id).then(refresh)}
                  className="px-3 py-1 bg-[#1a1d27] border border-[#2a2d3e] text-slate-400 hover:text-white text-xs rounded-lg">Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wide text-slate-600 mb-2">Recent</p>
          <div className="space-y-1">
            {history.map(s => (
              <div key={s.id} className="flex items-center gap-3 text-xs">
                <span className={`px-2 py-0.5 rounded border ${STATUS_STYLE[s.status]}`}>{s.status}</span>
                <span className={s.side === 'long' ? 'text-green-400' : 'text-red-400'}>{s.side}</span>
                <span className="text-slate-400">{s.symbol} {s.interval}</span>
                <span className="text-slate-600">{s.score}/110</span>
                {s.paired_trade_id && <span className="text-slate-600">→ paper #{s.paired_trade_id}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
