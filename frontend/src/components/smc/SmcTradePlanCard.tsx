import type { SmcTradePlan } from '../../api/client'

const STRENGTH_STYLE: Record<string, string> = {
  STRONG: 'text-green-400 bg-green-500/10 border-green-500/40',
  MODERATE: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  WEAK: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
  REJECTED: 'text-red-400 bg-red-500/10 border-red-500/40',
}
const FACTOR_LABEL: Record<string, string> = {
  order_block_in_zone: 'Order block at entry',
  fvg_in_zone: 'Fair-value gap at entry',
  htf_aligned: 'Higher timeframe agrees',
  correct_dealing_range: 'Right side of the range',
  recent_liquidity_sweep: 'Recent liquidity sweep',
  poi_present: 'Point of interest nearby',
  order_flow_aligned: 'Order flow agrees',
  candle_pattern: 'Confirming candle',
}

function fmt(n: number) {
  return n >= 1000 ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : n.toPrecision(5)
}

function Level({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-[#0f1117] rounded-lg p-2.5">
      <p className="text-[10px] uppercase tracking-wide text-slate-600">{label}</p>
      <p className={`text-sm font-semibold ${color}`}>{fmt(value)}</p>
    </div>
  )
}

export default function SmcTradePlanCard({ plan }: { plan: SmcTradePlan }) {
  const isLong = plan.side === 'long'
  const sideColor = isLong ? 'text-green-400' : 'text-red-400'
  const conf = plan.confluence

  return (
    <div className={`bg-[#1a1d27] border rounded-xl p-4 ${
      plan.fired ? (isLong ? 'border-green-500/40' : 'border-red-500/40') : 'border-[#2a2d3e]'}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold uppercase ${sideColor}`}>{plan.side}</span>
          <span className="text-xs text-slate-600">from {plan.source.replace('_', ' ')}</span>
        </div>
        <span className={`text-xs font-bold px-2 py-1 rounded-lg border ${STRENGTH_STYLE[plan.strength]}`}>
          {plan.fired ? '● FIRED' : plan.strength} · {plan.strength_score}/110
        </span>
      </div>

      <div className="grid grid-cols-4 gap-2">
        <Level label="Entry" value={plan.entry} color="text-white" />
        <Level label="Stop" value={plan.stop_loss} color="text-red-400" />
        <Level label="TP1" value={plan.take_profit_1} color="text-green-400" />
        <Level label="TP2" value={plan.take_profit_2} color="text-green-400" />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Reward:risk <span className="text-slate-300 font-medium">{plan.risk_reward.toFixed(2)}:1</span>
        <span className="text-slate-600"> · {plan.note}</span>
      </p>

      {conf && (
        <div className="mt-3 border-t border-[#2a2d3e] pt-3">
          <p className="text-[10px] uppercase tracking-wide text-slate-600 mb-2">Confluence</p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {conf.factors.map(f => (
              <div key={f.name} className="flex items-center gap-1.5 text-xs">
                <span className={f.hit ? 'text-green-400' : 'text-slate-700'}>{f.hit ? '✓' : '·'}</span>
                <span className={f.hit ? 'text-slate-300' : 'text-slate-600'}>
                  {FACTOR_LABEL[f.name] ?? f.name}
                </span>
                <span className="text-slate-700 ml-auto">+{f.points}</span>
              </div>
            ))}
          </div>
          {conf.reject_reasons.length > 0 && (
            <div className="mt-2 space-y-1">
              {conf.reject_reasons.map((r, i) => (
                <p key={i} className="text-xs text-red-400/80">✕ {r}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
