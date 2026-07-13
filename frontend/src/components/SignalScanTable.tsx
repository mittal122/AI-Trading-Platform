import { useEffect, useState } from 'react'
import type { TradingSignal } from '../api/client'

const DIR_CHIP: Record<string, string> = {
  BUY:  'chip-up',
  SELL: 'chip-down',
  FLAT: 'chip-muted',
}

const GRADE_COLOR: Record<string, string> = {
  'A+': 'text-up', A: 'text-up', B: 'text-accent',
  C: 'text-accent', D: 'text-down', F: 'text-down',
}

export default function SignalScanTable({ signals, labelKey, onRowClick }: {
  signals: TradingSignal[]
  labelKey: 'strategy' | 'interval'
  onRowClick?: (signal: TradingSignal) => void
}) {
  // Weak/FLAT rows hide their levels by default (they're not actionable) —
  // clicking a row reveals its entry/stop/target anyway, per row.
  const [revealed, setRevealed] = useState<Set<number>>(new Set())
  useEffect(() => { setRevealed(new Set()) }, [signals])

  if (!signals.length) {
    return <p className="text-fg-faint text-sm text-center py-6">No signals yet</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left">
            <th className="th">{labelKey === 'strategy' ? 'Strategy' : 'Timeframe'}</th>
            <th className="th">Signal</th>
            <th className="th">Confidence</th>
            <th className="th">Entry</th>
            <th className="th">Stop Loss</th>
            <th className="th">Take Profit</th>
            <th className="th">R:R</th>
            <th className="th">ETA</th>
            <th className="th">Grade</th>
            <th className="th">Regime</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => {
            const label = labelKey === 'strategy' ? s.strategy : s.interval
            const actionable = s.direction === 'BUY' || s.direction === 'SELL'
            const showLevels = actionable || revealed.has(i)
            return (
              <tr
                key={i}
                onClick={() => {
                  onRowClick?.(s)
                  setRevealed(prev => new Set(prev).add(i))
                }}
                title={showLevels ? undefined : 'Click to show entry / stop / target'}
                className={`row-hover cursor-pointer ${actionable ? '' : 'opacity-60'}`}
              >
                <td className="td font-medium text-fg">{label}</td>
                <td className="td">
                  <span className={`chip ${DIR_CHIP[s.direction] ?? DIR_CHIP.FLAT}`}>
                    {s.direction}
                  </span>
                </td>
                <td className="td num">{s.confidence.toFixed(1)}%</td>
                <td className="td num">{showLevels && s.entry ? `$${s.entry.toFixed(2)}` : '—'}</td>
                <td className="td num text-down/80">{showLevels && s.stop_loss ? `$${s.stop_loss.toFixed(2)}` : '—'}</td>
                <td className="td num text-up/80">{showLevels && s.take_profit ? `$${s.take_profit.toFixed(2)}` : '—'}</td>
                <td className="td num">{showLevels && s.risk_reward ? `1:${s.risk_reward.toFixed(2)}` : '—'}</td>
                <td className="td num text-accent">{s.eta_display ?? '—'}</td>
                <td className={`td num font-semibold ${s.quality_grade ? GRADE_COLOR[s.quality_grade] ?? 'text-fg-soft' : 'text-fg-faint'}`}>
                  {s.quality_grade ?? '—'}
                </td>
                <td className="td text-xs text-fg-faint">{s.regime ?? '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
