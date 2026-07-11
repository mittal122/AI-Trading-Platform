import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { getPatternDashboard } from '../api/client'
import type { PatternDashboardRow } from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'
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
    <div className="relative p-3 space-y-3 max-w-[1800px] mx-auto">
      <LoadingOverlay show={loading} label="Scanning every timeframe — this can take a minute…" />
      {/* Toolbar */}
      <div className="card flex items-center gap-3 px-3 py-2 flex-wrap">
        <span className="panel-title">Pattern Dashboard</span>
        <span className="text-[11px] text-fg-faint hidden md:inline">
          Confirmed patterns across all timeframes — click a row to open its chart
        </span>
        <div className="ml-auto flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="field-label !mb-0" htmlFor="pattern-min-conf">Min conf</label>
            <input id="pattern-min-conf" type="range" min={0} max={100} step={5} value={minConfidence}
              onChange={e => setMinConfidence(Number(e.target.value))} className="w-28 accent-accent cursor-pointer" />
            <span className="num text-[11px] text-fg-soft w-9">{minConfidence}%</span>
          </div>
          <SymbolSearchInput value={symbol} onCommit={setSymbol} className="w-40" />
          <button onClick={load} disabled={loading} className="btn btn-primary">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} aria-label="rescan" />
            {loading ? 'Scanning…' : 'Scan All Timeframes'}
          </button>
        </div>
      </div>

      {error && <div className="card card-pad border-down/40 text-down text-sm">{error}</div>}

      {confirmedRows.length === 0 ? (
        <div className="card card-pad text-center text-fg-faint text-xs py-8">
          {loading ? 'Scanning every timeframe — this calls AI for every pattern found, can take a minute…'
            : rows.length === 0 ? 'No recent patterns found — the scan runs automatically; "Scan All Timeframes" re-runs it.'
            : 'No CONFIRMED signals right now — patterns are still DEVELOPING or were BROKEN.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
          <PatternSection title="BULLISH — CONFIRMED" chipCls="chip-up" rows={bullish} navigate={navigate} />
          <PatternSection title="BEARISH — CONFIRMED" chipCls="chip-down" rows={bearish} navigate={navigate} />
        </div>
      )}
    </div>
  )
}

function PatternSection({ title, chipCls, rows, navigate }: {
  title: string; chipCls: string; rows: PatternDashboardRow[]
  navigate: ReturnType<typeof useNavigate>
}) {
  return (
    // min-w-0: without it a grid child refuses to shrink below its nowrap
    // table content, forcing the whole page wider than the viewport (the
    // toolbar's scan button then gets clipped off-screen).
    <section className="card min-w-0">
      <header className="flex items-center justify-between px-3 pt-3 pb-2">
        <h2 className="panel-title">{title}</h2>
        <span className={`chip ${chipCls} num`}>{rows.length}</span>
      </header>
      {rows.length === 0 ? (
        <p className="text-fg-faint text-xs text-center py-6">No confirmed signals.</p>
      ) : (
        <div className="pb-1.5 overflow-x-auto">
          <table className="w-full text-[12.5px]">
            <thead>
              <tr>
                <th className="th pl-3">Timeframe</th>
                <th className="th">Pattern</th>
                <th className="th pr-3 text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}
                  onClick={() => navigate(`/patterns?symbol=${r.symbol}&interval=${r.interval}`)}
                  className="row-hover cursor-pointer">
                  <td className="td num pl-3 font-medium text-fg-soft">{r.interval}</td>
                  <td className="td text-fg">{r.pattern_name}</td>
                  <td className="td num pr-3 text-right text-accent">{r.confidence.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
