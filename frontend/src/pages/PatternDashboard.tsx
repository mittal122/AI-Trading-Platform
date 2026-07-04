import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPatternDashboard } from '../api/client'
import type { PatternDashboardRow } from '../api/client'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { usePersistedState } from '../hooks/usePersistedState'

// Chronological, not alphabetical — matches the platform's standard scan set.
const INTERVAL_ORDER = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
function intervalRank(interval: string): number {
  const i = INTERVAL_ORDER.indexOf(interval)
  return i === -1 ? INTERVAL_ORDER.length : i
}

export default function PatternDashboard() {
  const navigate = useNavigate()
  const [symbol, setSymbol] = usePersistedState('patternDashboard.symbol', 'BTCUSDT')
  const [rows, setRows] = useState<PatternDashboardRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [minConfidence, setMinConfidence] = usePersistedState('patternDashboard.minConf', 0)

  async function load() {
    setLoading(true); setError('')
    try {
      const res = await getPatternDashboard(symbol)
      setRows(res.data.rows)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to load pattern dashboard')
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  // Auto-scan on page visit and whenever the symbol changes — no manual
  // "Scan All Timeframes" click required (the button stays as a manual
  // refresh).
  useEffect(() => { load() }, [symbol])  // eslint-disable-line react-hooks/exhaustive-deps

  // Only confirmed signals — DEVELOPING/BROKEN rows are noise for a "what's
  // actionable right now" dashboard. NEUTRAL-direction patterns (Doji,
  // Spinning Top, Inside Bar) never reach CONFIRMED by design, so they drop
  // out here too — no separate handling needed.
  const confirmedRows = rows.filter(r => r.status === 'CONFIRMED' && r.confidence >= minConfidence)
  const bullish = confirmedRows.filter(r => r.direction === 'BULLISH').sort((a, b) => intervalRank(a.interval) - intervalRank(b.interval))
  const bearish = confirmedRows.filter(r => r.direction === 'BEARISH').sort((a, b) => intervalRank(a.interval) - intervalRank(b.interval))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Pattern Dashboard</h1>
          <p className="text-slate-500 text-sm">Every active pattern across all timeframes, one symbol at a time — click a row to open its chart</p>
        </div>
        <div className="flex items-center gap-2">
          <SymbolSearchInput value={symbol} onCommit={setSymbol} className="w-40" />
          <button onClick={load} disabled={loading}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
            {loading ? 'Scanning all timeframes…' : 'Scan All Timeframes'}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

      <div className="flex items-center gap-2 justify-end">
        <label className="text-xs text-slate-500">Min confidence:</label>
        <input type="range" min={0} max={100} step={5} value={minConfidence}
          onChange={e => setMinConfidence(Number(e.target.value))} className="w-32" />
        <span className="text-xs text-slate-400 w-10">{minConfidence}%</span>
      </div>

      {confirmedRows.length === 0 ? (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-8 text-center text-slate-500 text-sm">
          {loading ? 'Scanning every timeframe — this calls AI for every pattern found, can take a minute…'
            : rows.length === 0 ? 'No recent patterns found — the scan runs automatically; "Scan All Timeframes" re-runs it.'
            : 'No CONFIRMED signals right now — patterns are still DEVELOPING or were BROKEN.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <PatternSection title="Bullish" accent="text-green-400" rows={bullish} navigate={navigate} />
          <PatternSection title="Bearish" accent="text-red-400" rows={bearish} navigate={navigate} />
        </div>
      )}
    </div>
  )
}

function PatternSection({ title, accent, rows, navigate }: {
  title: string; accent: string; rows: PatternDashboardRow[]
  navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
      <h2 className={`text-sm font-semibold mb-3 ${accent}`}>{title} ({rows.length})</h2>
      {rows.length === 0 ? (
        <p className="text-slate-600 text-xs text-center py-6">No confirmed {title.toLowerCase()} signals.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-[#2a2d3e]">
              <th className="pb-2 pr-4">Timeframe</th>
              <th className="pb-2 pr-4">Pattern</th>
              <th className="pb-2">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}
                onClick={() => navigate(`/patterns?symbol=${r.symbol}&interval=${r.interval}`)}
                className="border-b border-[#2a2d3e]/50 hover:bg-[#0f1117]/40 cursor-pointer">
                <td className="py-2 pr-4 text-slate-300 font-medium">{r.interval}</td>
                <td className="py-2 pr-4 text-white">{r.pattern_name}</td>
                <td className="py-2 text-indigo-400">{r.confidence.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
