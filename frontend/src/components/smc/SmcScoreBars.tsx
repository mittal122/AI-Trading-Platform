import type { SmcVerdict } from '../../api/client'

const LABELS: Record<string, string> = {
  structure: 'Structure', order_blocks: 'Order Blocks', fvg: 'Fair Value Gaps',
  liquidity: 'Liquidity', zone: 'Dealing Zone', volume: 'Volume',
}

// Six diverging bars, -100..+100, centered at 0. Up-green = bullish
// contribution, down-red = bearish (directional, so not accent). The weight
// (its share of the verdict) is shown per row.
export default function SmcScoreBars({ v }: { v: SmcVerdict }) {
  return (
    <div className="card card-pad">
      <p className="panel-title mb-3">Bias Factors</p>
      <div className="space-y-2.5">
        {v.breakdown.components.map(c => {
          const pct = Math.min(50, Math.abs(c.raw) / 2)  // half-width = 100
          const bull = c.raw >= 0
          return (
            <div key={c.name}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-fg-soft">{LABELS[c.name] ?? c.name}</span>
                <span className="num text-fg-faint">
                  {c.raw >= 0 ? '+' : ''}{c.raw.toFixed(0)} · {(c.weight * 100).toFixed(0)}%
                </span>
              </div>
              <div className="relative h-2 bg-line rounded-full overflow-hidden">
                <div className="absolute left-1/2 top-0 h-full w-px bg-line-strong" />
                <div
                  className={`absolute top-0 h-full ${bull ? 'bg-up/70' : 'bg-down/70'}`}
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
