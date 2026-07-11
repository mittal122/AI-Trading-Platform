import type { DetectedPattern } from '../api/client'

const DIR_CHIP: Record<string, string> = {
  BULLISH: 'chip-up',
  BEARISH: 'chip-down',
  NEUTRAL: 'chip-muted',
}

const STATUS_CHIP_CLS: Record<string, string> = {
  CONFIRMED: 'chip-up',
  DEVELOPING: 'chip-warn',
  BROKEN: 'chip-muted',
}

const REC_STYLE: Record<string, string> = {
  BUY: 'text-up bg-up-soft border-up/40',
  SELL: 'text-down bg-down-soft border-down/40',
  WAIT: 'text-accent bg-accent-soft border-accent/40',
  AVOID: 'text-fg-soft bg-raised border-line-strong',
}

function Stat({ label, value, color = 'text-fg' }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-bg rounded-md p-3 border border-line">
      <p className="text-[11px] text-fg-faint mb-1">{label}</p>
      <p className={`num text-sm font-semibold ${color}`}>{value}</p>
    </div>
  )
}

function fmt(v?: number) {
  return v === undefined || v === null ? '—' : `$${v.toFixed(2)}`
}

export default function PatternInfoPanel({ pattern, aiLoading }: { pattern: DetectedPattern; aiLoading?: boolean }) {
  const ai = pattern.ai

  return (
    <div className="card card-pad space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-[15px] font-semibold text-fg">{pattern.pattern_name}</h3>
          <p className="text-[11px] text-fg-faint">{pattern.symbol} · {pattern.interval}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`chip ${DIR_CHIP[pattern.direction] ?? 'chip-muted'}`}>
            {pattern.direction}
          </span>
          <span className={`chip ${STATUS_CHIP_CLS[pattern.status] ?? 'chip-muted'}`}>
            {pattern.status}
          </span>
        </div>
      </div>

      {/* Confidence */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-bg rounded-full overflow-hidden">
          <div className="h-full bg-accent" style={{ width: `${pattern.confidence}%` }} />
        </div>
        <span className="num text-sm font-semibold text-accent">{pattern.confidence.toFixed(1)}%</span>
      </div>

      {/* Levels */}
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Breakout" value={fmt(pattern.breakout_level)} />
        <Stat label="Invalidation" value={fmt(pattern.invalidation_level)} color="text-down" />
        <Stat label="Current Price" value={fmt(pattern.current_price)} />
        <Stat label="Entry Zone" value={
          pattern.entry_zone_low !== undefined ? `${fmt(pattern.entry_zone_low)} – ${fmt(pattern.entry_zone_high)}` : '—'
        } />
        <Stat label="Stop Loss" value={fmt(pattern.stop_loss)} color="text-down" />
        <Stat label="Risk/Reward" value={pattern.risk_reward ? `1:${pattern.risk_reward.toFixed(2)}` : '—'} />
        <Stat label="Target 1" value={fmt(pattern.target_1)} color="text-up" />
        <Stat label="Target 2" value={fmt(pattern.target_2)} color="text-up" />
        <Stat label="Target 3" value={fmt(pattern.target_3)} color="text-up" />
      </div>

      <div className="grid grid-cols-2 gap-2 text-[11px] text-fg-faint">
        <p className="num">Formed: {pattern.formation_start.slice(0, 16).replace('T', ' ')} → {pattern.formation_end.slice(0, 16).replace('T', ' ')}</p>
        <p>Probability of success: <span className="num">{pattern.probability_of_success?.toFixed(1) ?? '—'}%</span></p>
      </div>

      {/* AI Explanation */}
      {aiLoading && (
        <div className="border-t border-line pt-4">
          <p className="text-[11px] text-fg-faint">Generating AI analysis for this pattern…</p>
        </div>
      )}
      {!aiLoading && ai && !ai.error && (
        <div className="border-t border-line pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="panel-title">AI Analysis</h4>
            <div className="flex items-center gap-2">
              {ai.strength && <span className="text-[11px] text-fg-soft">Strength: {ai.strength}</span>}
              {ai.reliability_score !== undefined && (
                <span className="text-[11px] text-fg-soft">Reliability: <span className="num">{ai.reliability_score.toFixed(0)}%</span></span>
              )}
            </div>
          </div>

          {ai.recommendation && (
            <div className={`text-sm font-semibold px-3 py-2 rounded-md border ${REC_STYLE[ai.recommendation]}`}>
              {ai.recommendation} — <span className="font-normal">{ai.recommendation_reason}</span>
            </div>
          )}

          <div className="space-y-2 text-[12.5px] text-fg-soft">
            {ai.why_detected && <p><span className="text-fg-faint font-semibold">Why detected: </span>{ai.why_detected}</p>}
            {ai.why_valid && <p><span className="text-fg-faint font-semibold">Why valid: </span>{ai.why_valid}</p>}
            {ai.market_psychology && <p><span className="text-fg-faint font-semibold">Market psychology: </span>{ai.market_psychology}</p>}
            {ai.buyer_seller_behavior && <p><span className="text-fg-faint font-semibold">Buyers/Sellers: </span>{ai.buyer_seller_behavior}</p>}
            {ai.alternative_scenario && <p><span className="text-fg-faint font-semibold">If it fails: </span>{ai.alternative_scenario}</p>}
          </div>
        </div>
      )}
      {!aiLoading && ai?.error && (
        <p className="text-[11px] text-fg-faint border-t border-line pt-3">AI explanation unavailable ({ai.error.slice(0, 120)})</p>
      )}
    </div>
  )
}
