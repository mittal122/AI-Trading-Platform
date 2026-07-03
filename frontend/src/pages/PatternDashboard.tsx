import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPatternDashboard } from '../api/client'
import type { PatternDashboardRow } from '../api/client'
import { usePersistedState } from '../hooks/usePersistedState'

const DIR_STYLE: Record<string, string> = {
  BULLISH: 'text-green-400 bg-green-500/10 border-green-500/30',
  BEARISH: 'text-red-400 bg-red-500/10 border-red-500/30',
  NEUTRAL: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
}

const STATUS_STYLE: Record<string, string> = {
  CONFIRMED: 'text-green-400', DEVELOPING: 'text-yellow-400', BROKEN: 'text-red-400',
}

export default function PatternDashboard() {
  const navigate = useNavigate()
  const [symbolInput, setSymbolInput] = usePersistedState('patternDashboard.symbol', 'BTCUSDT')
  const [symbol, setSymbol] = useState(symbolInput)
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

  function submitSymbol() {
    const next = symbolInput.trim().toUpperCase()
    if (next) { setSymbolInput(next); setSymbol(next) }
  }

  const visibleRows = rows.filter(r => r.confidence >= minConfidence)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Pattern Dashboard</h1>
          <p className="text-slate-500 text-sm">Every active pattern across all timeframes, one symbol at a time — click a row to open its chart</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={symbolInput} onChange={e => setSymbolInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submitSymbol()} onBlur={submitSymbol}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500 w-32"
          />
          <button onClick={load} disabled={loading}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
            {loading ? 'Scanning all timeframes…' : 'Scan All Timeframes'}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="text-sm font-semibold text-slate-300">
            Active Patterns ({visibleRows.length}{rows.length !== visibleRows.length ? ` of ${rows.length}` : ''})
          </h2>
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-500">Min confidence:</label>
            <input type="range" min={0} max={100} step={5} value={minConfidence}
              onChange={e => setMinConfidence(Number(e.target.value))} className="w-32" />
            <span className="text-xs text-slate-400 w-10">{minConfidence}%</span>
          </div>
        </div>

        {visibleRows.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">
            {loading ? 'Scanning every timeframe — this calls AI for every pattern found, can take a minute…' : 'No patterns yet — click "Scan All Timeframes".'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-[#2a2d3e]">
                  <th className="pb-2 pr-4">Timeframe</th>
                  <th className="pb-2 pr-4">Pattern</th>
                  <th className="pb-2 pr-4">Confidence</th>
                  <th className="pb-2 pr-4">Bias</th>
                  <th className="pb-2 pr-4">Price</th>
                  <th className="pb-2 pr-4">Entry</th>
                  <th className="pb-2 pr-4">Stop Loss</th>
                  <th className="pb-2 pr-4">Target</th>
                  <th className="pb-2 pr-4">R:R</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2">Updated</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((r, i) => (
                  <tr key={i}
                    onClick={() => navigate(`/patterns?symbol=${r.symbol}&interval=${r.interval}`)}
                    className="border-b border-[#2a2d3e]/50 hover:bg-[#0f1117]/40 cursor-pointer">
                    <td className="py-2 pr-4 text-slate-300 font-medium">{r.interval}</td>
                    <td className="py-2 pr-4 text-white">{r.pattern_name}</td>
                    <td className="py-2 pr-4 text-indigo-400">{r.confidence.toFixed(1)}%</td>
                    <td className="py-2 pr-4">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded border ${DIR_STYLE[r.direction]}`}>{r.direction}</span>
                    </td>
                    <td className="py-2 pr-4 text-slate-400">${r.current_price.toFixed(2)}</td>
                    <td className="py-2 pr-4 text-slate-400">
                      {r.entry_zone_low ? `$${r.entry_zone_low.toFixed(2)}–$${r.entry_zone_high?.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2 pr-4 text-red-400/80">{r.stop_loss ? `$${r.stop_loss.toFixed(2)}` : '—'}</td>
                    <td className="py-2 pr-4 text-green-400/80">{r.target_1 ? `$${r.target_1.toFixed(2)}` : '—'}</td>
                    <td className="py-2 pr-4 text-slate-400">{r.risk_reward ? `1:${r.risk_reward.toFixed(2)}` : '—'}</td>
                    <td className={`py-2 pr-4 font-medium ${STATUS_STYLE[r.status]}`}>{r.status}</td>
                    <td className="py-2 text-slate-600 text-xs">{new Date(r.last_updated).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
