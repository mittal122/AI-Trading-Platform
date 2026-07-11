import { useState } from 'react'
import { runSmcBacktest } from '../../api/client'
import type { SmcBacktestResult } from '../../api/client'
import { usePersistedState } from '../../hooks/usePersistedState'

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="bg-raised border border-line rounded-md p-3">
      <p className="field-label">{label}</p>
      <p className={`num text-lg font-semibold ${tone ?? 'text-fg'}`}>{value}</p>
    </div>
  )
}

// Dependency-free equity curve — a normalized SVG polyline in brand amber,
// over a faint hairline grid.
function EquitySparkline({ curve }: { curve: number[] }) {
  if (curve.length < 2) return <p className="text-xs text-fg-faint">No closed trades to plot.</p>
  const w = 600, h = 120, pad = 4
  const min = Math.min(...curve), max = Math.max(...curve)
  const span = max - min || 1
  const pts = curve.map((v, i) => {
    const x = pad + (i / (curve.length - 1)) * (w - 2 * pad)
    const y = pad + (1 - (v - min) / span) * (h - 2 * pad)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-28" preserveAspectRatio="none">
      {[0.25, 0.5, 0.75].map(f => (
        <line key={f} x1={pad} x2={w - pad} y1={pad + f * (h - 2 * pad)} y2={pad + f * (h - 2 * pad)}
          stroke="#232837" strokeWidth="1" />
      ))}
      <polyline points={pts} fill="none" stroke="#f5a623" strokeWidth="1.5" />
    </svg>
  )
}

const REASON_STYLE: Record<string, string> = {
  TAKE_PROFIT: 'text-up', STOP_LOSS: 'text-down',
  TIME_EXIT: 'text-accent', END_OF_DATA: 'text-fg-soft',
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

  const roiTone = result && result.roi >= 0 ? 'text-up' : 'text-down'

  return (
    <div className="card card-pad space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="panel-title">Backtest</p>
          <p className="text-xs text-fg-faint">Replays this exact strategy over history — same firing rules, walk-forward.</p>
        </div>
        <div className="flex items-end gap-2 text-xs">
          <label>
            <span className="field-label">Capital</span>
            <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))}
              className="input input-mono w-24" />
          </label>
          <label>
            <span className="field-label">Risk %</span>
            <input type="number" value={riskPct} step="0.5" onChange={e => setRiskPct(Number(e.target.value))}
              className="input input-mono w-20" />
          </label>
          <label>
            <span className="field-label">Candles</span>
            <input type="number" value={candles} step="100" onChange={e => setCandles(Number(e.target.value))}
              className="input input-mono w-24" />
          </label>
          <button onClick={run} disabled={loading} className="btn btn-primary">
            {loading ? 'Running…' : 'Run backtest'}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-fg-faint">Replaying <span className="num">{candles}</span> candles — this can take a few seconds…</p>}
      {error && <p className="text-sm text-down">{error}</p>}

      {result && !loading && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
            <Stat label="Trades" value={`${result.total_trades}`} />
            <Stat label="Win rate" value={`${result.win_rate.toFixed(0)}%`} />
            <Stat label="Profit factor" value={result.profit_factor.toFixed(2)} />
            <Stat label="ROI" value={`${result.roi >= 0 ? '+' : ''}${result.roi.toFixed(2)}%`} tone={roiTone} />
            <Stat label="Max drawdown" value={`${result.max_drawdown.toFixed(1)}%`} tone="text-down" />
            <Stat label="Long / Short" value={`${result.long_trades} / ${result.short_trades}`} />
            <Stat label="Final" value={result.final_capital.toFixed(0)} tone={roiTone} />
          </div>

          <div className="bg-raised border border-line rounded-md p-3">
            <p className="field-label mb-1">Equity curve</p>
            <EquitySparkline curve={result.equity_curve} />
          </div>

          {result.trades.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="th">Side</th><th className="th">Entry</th>
                    <th className="th">Exit</th><th className="th">PnL %</th>
                    <th className="th">Reason</th><th className="th">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={i} className="row-hover border-b border-line/50">
                      <td className={`td font-medium ${t.side === 'long' ? 'text-up' : 'text-down'}`}>{t.side}</td>
                      <td className="td num text-fg-soft">{t.entry.toPrecision(6)}</td>
                      <td className="td num text-fg-soft">{t.exit_price.toPrecision(6)}</td>
                      <td className={`td num ${t.pnl >= 0 ? 'text-up' : 'text-down'}`}>{t.pnl_pct >= 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%</td>
                      <td className={`td ${REASON_STYLE[t.exit_reason]}`}>{t.exit_reason.replace('_', ' ').toLowerCase()}</td>
                      <td className="td num text-fg-faint">{t.strength_score}</td>
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
