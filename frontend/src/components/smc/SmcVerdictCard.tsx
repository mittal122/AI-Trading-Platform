import type { SmcAnalysis } from '../../api/client'

const DIR_COLOR: Record<string, string> = {
  BULLISH: 'text-green-400', BEARISH: 'text-red-400', NEUTRAL: 'text-slate-400',
}
const CONF_COLOR: Record<string, string> = {
  high: 'text-green-400', medium: 'text-yellow-400', low: 'text-slate-500',
}
const TREND_STYLE: Record<string, string> = {
  up: 'text-green-400 bg-green-500/10 border-green-500/30',
  down: 'text-red-400 bg-red-500/10 border-red-500/30',
  neutral: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
}

function TrendChip({ label, trend }: { label: string; trend: string }) {
  return (
    <span className={`text-xs font-medium px-2 py-1 rounded-lg border ${TREND_STYLE[trend] ?? TREND_STYLE.neutral}`}>
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
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-widest text-slate-500">Market Bias</p>
        <span className="text-xs text-slate-600">total {v.total.toFixed(0)}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-3">
        <span className={`text-3xl font-bold ${DIR_COLOR[v.label]}`}>{v.label}</span>
        <span className={`text-sm font-medium ${CONF_COLOR[v.confidence_label]}`}>
          {v.confidence.toFixed(0)}% {v.confidence_label}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <TrendChip label="Structure" trend={a.trend} />
        {a.htf?.available
          ? <TrendChip label="Higher TF" trend={a.htf.trend} />
          : <span className="text-xs text-slate-600 px-2 py-1">Higher TF n/a</span>}
      </div>
      <p className="mt-3 text-xs text-slate-500 leading-relaxed">
        Bias is the weighted lean of six factors. It sets direction, not a trade —
        a signal only fires when a side clears the confluence checklist below.
      </p>
    </div>
  )
}
