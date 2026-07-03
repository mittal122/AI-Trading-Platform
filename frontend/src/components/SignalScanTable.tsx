import type { TradingSignal } from '../api/client'

const DIR_STYLE: Record<string, string> = {
  BUY:  'text-green-400 bg-green-500/10 border-green-500/30',
  SELL: 'text-red-400 bg-red-500/10 border-red-500/30',
  FLAT: 'text-slate-500 bg-slate-500/5 border-slate-500/10',
}

const GRADE_COLOR: Record<string, string> = {
  'A+': 'text-green-400', A: 'text-green-500', B: 'text-yellow-400',
  C: 'text-orange-400', D: 'text-red-400', F: 'text-red-600',
}

export default function SignalScanTable({ signals, labelKey, onRowClick }: {
  signals: TradingSignal[]
  labelKey: 'strategy' | 'interval'
  onRowClick?: (signal: TradingSignal) => void
}) {
  if (!signals.length) {
    return <p className="text-slate-500 text-sm text-center py-6">No signals yet</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 border-b border-[#2a2d3e]">
            <th className="pb-2 pr-4">{labelKey === 'strategy' ? 'Strategy' : 'Timeframe'}</th>
            <th className="pb-2 pr-4">Signal</th>
            <th className="pb-2 pr-4">Confidence</th>
            <th className="pb-2 pr-4">Entry</th>
            <th className="pb-2 pr-4">Stop Loss</th>
            <th className="pb-2 pr-4">Take Profit</th>
            <th className="pb-2 pr-4">R:R</th>
            <th className="pb-2 pr-4">ETA</th>
            <th className="pb-2 pr-4">Grade</th>
            <th className="pb-2">Regime</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => {
            const label = labelKey === 'strategy' ? s.strategy : s.interval
            const actionable = s.direction === 'BUY' || s.direction === 'SELL'
            return (
              <tr
                key={i}
                onClick={() => onRowClick?.(s)}
                className={`border-b border-[#2a2d3e]/50 ${onRowClick ? 'cursor-pointer hover:bg-[#0f1117]/40' : ''} ${actionable ? '' : 'opacity-60'}`}
              >
                <td className="py-2 pr-4 font-medium text-white">{label}</td>
                <td className="py-2 pr-4">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded border ${DIR_STYLE[s.direction] ?? DIR_STYLE.FLAT}`}>
                    {s.direction}
                  </span>
                </td>
                <td className="py-2 pr-4 text-slate-300">{s.confidence.toFixed(1)}%</td>
                <td className="py-2 pr-4 text-slate-400">{s.entry ? `$${s.entry.toFixed(2)}` : '—'}</td>
                <td className="py-2 pr-4 text-red-400/80">{actionable ? `$${s.stop_loss.toFixed(2)}` : '—'}</td>
                <td className="py-2 pr-4 text-green-400/80">{actionable ? `$${s.take_profit.toFixed(2)}` : '—'}</td>
                <td className="py-2 pr-4 text-slate-400">{actionable ? `1:${s.risk_reward.toFixed(2)}` : '—'}</td>
                <td className="py-2 pr-4 text-indigo-400">{s.eta_display ?? '—'}</td>
                <td className={`py-2 pr-4 font-semibold ${s.quality_grade ? GRADE_COLOR[s.quality_grade] ?? 'text-slate-400' : 'text-slate-600'}`}>
                  {s.quality_grade ?? '—'}
                </td>
                <td className="py-2 text-slate-500 text-xs">{s.regime ?? '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
