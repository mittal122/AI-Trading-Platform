import { useState } from 'react'
import { runSmcBacktest } from '../../api/client'
import type { SmcBacktestResult } from '../../api/client'
import { usePersistedState } from '../../hooks/usePersistedState'

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="bg-[#0f1117] rounded-lg p-3">
      <p className="text-[10px] uppercase tracking-wide text-slate-600">{label}</p>
      <p className={`text-lg font-semibold ${tone ?? 'text-white'}`}>{value}</p>
    </div>
  )
}

// Dependency-free equity curve — a normalized SVG polyline. Green if the run
// ended up, red if down.
function EquitySparkline({ curve }: { curve: number[] }) {
  if (curve.length < 2) return <p className="text-xs text-slate-600">No closed trades to plot.</p>
  const w = 600, h = 120, pad = 4
  const min = Math.min(...curve), max = Math.max(...curve)
  const span = max - min || 1
  const pts = curve.map((v, i) => {
    const x = pad + (i / (curve.length - 1)) * (w - 2 * pad)
    const y = pad + (1 - (v - min) / span) * (h - 2 * pad)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const up = curve[curve.length - 1] >= curve[0]
  const stroke = up ? '#22c55e' : '#ef4444'
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-28" preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.5" />
    </svg>
  )
}

const REASON_STYLE: Record<string, string> = {
  TAKE_PROFIT: 'text-green-400', STOP_LOSS: 'text-red-400',
  TIME_EXIT: 'text-yellow-400', END_OF_DATA: 'text-slate-400',
}

export default function SmcBacktestPanel({ symbol, interval }: { symbol: string; interval: string }) {
  const [capital, setCapital] = usePersistedState('smc.bt.capital', 1000)
  const [riskPct, setRiskPct] = usePersistedState('smc.bt.risk', 2)
  const [candles, setCandles] = usePersistedState('smc.bt.candles', 500)
  const [result, setResult] = useState<SmcBacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run() {
    setLoading(true); setError(null)
    try {
      const { data } = await runSmcBacktest({ symbol, interval, limit: candles, capital, risk_pct: riskPct })
      setResult(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Backtest failed.')
    } finally {
      setLoading(false)
    }
  }

  const roiTone = result && result.roi >= 0 ? 'text-green-400' : 'text-red-400'

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500">Backtest</p>
          <p className="text-xs text-slate-600">Replays this exact strategy over history — same firing rules, walk-forward.</p>
        </div>
        <div className="flex items-end gap-2 text-xs">
          <label className="flex flex-col text-slate-500">Capital
            <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))}
              className="w-24 bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1.5 text-white outline-none mt-0.5" /></label>
          <label className="flex flex-col text-slate-500">Risk %
            <input type="number" value={riskPct} step="0.5" onChange={e => setRiskPct(Number(e.target.value))}
              className="w-20 bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1.5 text-white outline-none mt-0.5" /></label>
          <label className="flex flex-col text-slate-500">Candles
            <input type="number" value={candles} step="100" onChange={e => setCandles(Number(e.target.value))}
              className="w-24 bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1.5 text-white outline-none mt-0.5" /></label>
          <button onClick={run} disabled={loading}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg">
            {loading ? 'Running…' : 'Run backtest'}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">Replaying {candles} candles — this can take a few seconds…</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}

      {result && !loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
            <Stat label="Trades" value={`${result.total_trades}`} />
            <Stat label="Win rate" value={`${result.win_rate.toFixed(0)}%`} />
            <Stat label="Profit factor" value={result.profit_factor.toFixed(2)} />
            <Stat label="ROI" value={`${result.roi >= 0 ? '+' : ''}${result.roi.toFixed(2)}%`} tone={roiTone} />
            <Stat label="Max drawdown" value={`${result.max_drawdown.toFixed(1)}%`} tone="text-red-400" />
            <Stat label="Long / Short" value={`${result.long_trades} / ${result.short_trades}`} />
            <Stat label="Final" value={result.final_capital.toFixed(0)} tone={roiTone} />
          </div>

          <div className="bg-[#0f1117] rounded-lg p-3">
            <p className="text-[10px] uppercase tracking-wide text-slate-600 mb-1">Equity curve</p>
            <EquitySparkline curve={result.equity_curve} />
          </div>

          {result.trades.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-[#2a2d3e] text-left">
                    <th className="pb-2 pr-4">Side</th><th className="pb-2 pr-4">Entry</th>
                    <th className="pb-2 pr-4">Exit</th><th className="pb-2 pr-4">PnL %</th>
                    <th className="pb-2 pr-4">Reason</th><th className="pb-2">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={i} className="border-b border-[#2a2d3e]/50">
                      <td className={`py-1.5 pr-4 font-medium ${t.side === 'long' ? 'text-green-400' : 'text-red-400'}`}>{t.side}</td>
                      <td className="py-1.5 pr-4 text-slate-300">{t.entry.toPrecision(6)}</td>
                      <td className="py-1.5 pr-4 text-slate-300">{t.exit_price.toPrecision(6)}</td>
                      <td className={`py-1.5 pr-4 ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>{t.pnl_pct >= 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%</td>
                      <td className={`py-1.5 pr-4 ${REASON_STYLE[t.exit_reason]}`}>{t.exit_reason.replace('_', ' ').toLowerCase()}</td>
                      <td className="py-1.5 text-slate-500">{t.strength_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
