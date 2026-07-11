import type { SmcAnalysis } from '../../api/client'

const DIR_COLOR: Record<string, string> = {
  BULLISH: 'text-up', BEARISH: 'text-down', NEUTRAL: 'text-fg-soft',
}
const CONF_COLOR: Record<string, string> = {
  high: 'text-up', medium: 'text-accent', low: 'text-fg-faint',
}
const TREND_CHIP: Record<string, string> = {
  up: 'chip-up', down: 'chip-down', neutral: 'chip-muted',
}

function TrendChip({ label, trend }: { label: string; trend: string }) {
  return (
    <span className={`chip ${TREND_CHIP[trend] ?? 'chip-muted'}`}>
      {label} {trend}
    </span>
  )
}

// The verdict is the market-bias read (§6.2) — it describes lean, NOT a trade.
// Whether to actually trade is the fired/rejected signal below it.
export default function SmcVerdictCard({ a }: { a: SmcAnalysis }) {
  const v = a.verdict
  if (!v) return null
  return (
    <div className="card card-pad">
      <div className="flex items-center justify-between">
        <p className="panel-title">Market Bias</p>
        <span className="num text-[11px] text-fg-faint">total {v.total.toFixed(0)}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-3">
        <span className={`text-2xl font-bold ${DIR_COLOR[v.label]}`}>{v.label}</span>
        <span className={`num text-sm font-medium ${CONF_COLOR[v.confidence_label]}`}>
          {v.confidence.toFixed(0)}% {v.confidence_label}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <TrendChip label="Structure" trend={a.trend} />
        {a.htf?.available
          ? <TrendChip label="Higher TF" trend={a.htf.trend} />
          : <span className="text-xs text-fg-faint px-2 py-1">Higher TF n/a</span>}
      </div>
      <p className="mt-3 text-xs text-fg-faint leading-relaxed">
        Bias is the weighted lean of six factors. It sets direction, not a trade —
        a signal only fires when a side clears the confluence checklist below.
      </p>
    </div>
  )
}
