import type { SmcVerdict } from '../../api/client'

const LABELS: Record<string, string> = {
  structure: 'Structure', order_blocks: 'Order Blocks', fvg: 'Fair Value Gaps',
  liquidity: 'Liquidity', zone: 'Dealing Zone', volume: 'Volume',
}

// Six diverging bars, -100..+100, centered at 0. Green = bullish contribution,
// red = bearish. The weight (its share of the verdict) is shown per row.
export default function SmcScoreBars({ v }: { v: SmcVerdict }) {
  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
      <p className="text-xs uppercase tracking-widest text-slate-500 mb-3">Bias Factors</p>
      <div className="space-y-2.5">
        {v.breakdown.components.map(c => {
          const pct = Math.min(50, Math.abs(c.raw) / 2)  // half-width = 100
          const bull = c.raw >= 0
          return (
            <div key={c.name}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400">{LABELS[c.name] ?? c.name}</span>
                <span className="text-slate-600">
                  {c.raw >= 0 ? '+' : ''}{c.raw.toFixed(0)} · {(c.weight * 100).toFixed(0)}%
                </span>
              </div>
              <div className="relative h-2 bg-[#0f1117] rounded-full overflow-hidden">
                <div className="absolute left-1/2 top-0 h-full w-px bg-[#2a2d3e]" />
                <div
                  className={`absolute top-0 h-full ${bull ? 'bg-green-500/70' : 'bg-red-500/70'}`}
                  style={bull
                    ? { left: '50%', width: `${pct}%` }
                    : { right: '50%', width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
