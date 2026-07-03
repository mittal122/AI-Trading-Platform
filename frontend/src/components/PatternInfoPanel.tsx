import type { DetectedPattern } from '../api/client'

const DIR_STYLE: Record<string, string> = {
  BULLISH: 'text-green-400 bg-green-500/10 border-green-500/30',
  BEARISH: 'text-red-400 bg-red-500/10 border-red-500/30',
  NEUTRAL: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
}

const STATUS_STYLE: Record<string, string> = {
  CONFIRMED: 'text-green-400 bg-green-500/10 border-green-500/30',
  DEVELOPING: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  BROKEN: 'text-red-400 bg-red-500/10 border-red-500/30',
}

const REC_STYLE: Record<string, string> = {
  BUY: 'text-green-400 bg-green-500/10 border-green-500/30',
  SELL: 'text-red-400 bg-red-500/10 border-red-500/30',
  WAIT: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  AVOID: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
}

function Stat({ label, value, color = 'text-white' }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[#0f1117] rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-sm font-semibold ${color}`}>{value}</p>
    </div>
  )
}

function fmt(v?: number) {
  return v === undefined || v === null ? '—' : `$${v.toFixed(2)}`
}

export default function PatternInfoPanel({ pattern, aiLoading }: { pattern: DetectedPattern; aiLoading?: boolean }) {
  const ai = pattern.ai

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-base font-bold text-white">{pattern.pattern_name}</h3>
          <p className="text-xs text-slate-500">{pattern.symbol} · {pattern.interval}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold px-2 py-1 rounded-lg border ${DIR_STYLE[pattern.direction]}`}>
            {pattern.direction}
          </span>
          <span className={`text-xs font-bold px-2 py-1 rounded-lg border ${STATUS_STYLE[pattern.status]}`}>
            {pattern.status}
          </span>
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-[#0f1117] rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500" style={{ width: `${pattern.confidence}%` }} />
        </div>
        <span className="text-sm font-semibold text-indigo-400">{pattern.confidence.toFixed(1)}%</span>
      </div>

      {/* Levels */}
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Breakout" value={fmt(pattern.breakout_level)} />
        <Stat label="Invalidation" value={fmt(pattern.invalidation_level)} color="text-red-400" />
        <Stat label="Current Price" value={fmt(pattern.current_price)} />
        <Stat label="Entry Zone" value={
          pattern.entry_zone_low !== undefined ? `${fmt(pattern.entry_zone_low)} – ${fmt(pattern.entry_zone_high)}` : '—'
        } />
        <Stat label="Stop Loss" value={fmt(pattern.stop_loss)} color="text-red-400" />
        <Stat label="Risk/Reward" value={pattern.risk_reward ? `1:${pattern.risk_reward.toFixed(2)}` : '—'} />
        <Stat label="Target 1" value={fmt(pattern.target_1)} color="text-green-400" />
        <Stat label="Target 2" value={fmt(pattern.target_2)} color="text-green-400" />
        <Stat label="Target 3" value={fmt(pattern.target_3)} color="text-green-400" />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
        <p>Formed: {pattern.formation_start.slice(0, 16).replace('T', ' ')} → {pattern.formation_end.slice(0, 16).replace('T', ' ')}</p>
        <p>Probability of success: {pattern.probability_of_success?.toFixed(1) ?? '—'}%</p>
      </div>

      {/* AI Explanation */}
      {aiLoading && (
        <div className="border-t border-[#2a2d3e] pt-4">
          <p className="text-xs text-slate-500">Generating AI analysis for this pattern…</p>
        </div>
      )}
      {!aiLoading && ai && !ai.error && (
        <div className="border-t border-[#2a2d3e] pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-indigo-300">AI Analysis</h4>
            <div className="flex items-center gap-2">
              {ai.strength && <span className="text-xs text-slate-400">Strength: {ai.strength}</span>}
              {ai.reliability_score !== undefined && (
                <span className="text-xs text-slate-400">Reliability: {ai.reliability_score.toFixed(0)}%</span>
              )}
            </div>
          </div>

          {ai.recommendation && (
            <div className={`text-sm font-bold px-3 py-2 rounded-lg border ${REC_STYLE[ai.recommendation]}`}>
              {ai.recommendation} — <span className="font-normal">{ai.recommendation_reason}</span>
            </div>
          )}

          <div className="space-y-2 text-xs text-slate-400">
            {ai.why_detected && <p><span className="text-slate-500 font-semibold">Why detected: </span>{ai.why_detected}</p>}
            {ai.why_valid && <p><span className="text-slate-500 font-semibold">Why valid: </span>{ai.why_valid}</p>}
            {ai.market_psychology && <p><span className="text-slate-500 font-semibold">Market psychology: </span>{ai.market_psychology}</p>}
            {ai.buyer_seller_behavior && <p><span className="text-slate-500 font-semibold">Buyers/Sellers: </span>{ai.buyer_seller_behavior}</p>}
            {ai.alternative_scenario && <p><span className="text-slate-500 font-semibold">If it fails: </span>{ai.alternative_scenario}</p>}
          </div>
        </div>
      )}
      {!aiLoading && ai?.error && (
        <p className="text-xs text-slate-600 border-t border-[#2a2d3e] pt-3">AI explanation unavailable ({ai.error.slice(0, 120)})</p>
      )}
    </div>
  )
}
