import { useEffect, useRef, useState } from 'react'
import { RefreshCw, TriangleAlert } from 'lucide-react'
import { getLiveMarket } from '../../api/client'
import type { SmcAnalysis } from '../../api/client'

// The "freeze" concept made visible (doc §15.5): the analysis is a frozen
// snapshot at cutoff_price; the live price streams separately and this bar
// surfaces the DRIFT between them rather than silently mutating the plan. When
// the live price crosses a plan level (entry/SL/TP), it flags a re-analysis.
export default function SmcFreezeBar({ analysis, onReanalyze }: {
  analysis: SmcAnalysis; onReanalyze: () => void
}) {
  const [live, setLive] = useState<number>(analysis.cutoff_price)
  const crossedRef = useRef(false)

  useEffect(() => {
    setLive(analysis.cutoff_price)
    crossedRef.current = false
    let alive = true
    const poll = async () => {
      try {
        const { data } = await getLiveMarket(analysis.symbol, analysis.interval)
        if (alive && typeof data.close === 'number') setLive(data.close)
      } catch { /* transient */ }
    }
    poll()
    const t = window.setInterval(poll, 5000)
    return () => { alive = false; window.clearInterval(t) }
  }, [analysis.symbol, analysis.interval, analysis.cutoff_price])

  const frozen = analysis.cutoff_price
  const drift = frozen > 0 ? (live - frozen) / frozen * 100 : 0
  const plan = analysis.primary === 'long' ? analysis.long_plan
    : analysis.primary === 'short' ? analysis.short_plan : null

  // Level cross: has live moved through the plan's SL or TP1 vs the frozen side?
  let crossed: string | null = null
  if (plan) {
    if (plan.side === 'long') {
      if (live <= plan.stop_loss) crossed = 'stop-loss'
      else if (live >= plan.take_profit_1) crossed = 'take-profit'
    } else {
      if (live >= plan.stop_loss) crossed = 'stop-loss'
      else if (live <= plan.take_profit_1) crossed = 'take-profit'
    }
  }

  const ageSec = Math.max(0, Math.round((Date.now() - Date.parse(analysis.frozen_at)) / 1000))
  const age = ageSec < 60 ? `${ageSec}s` : `${Math.round(ageSec / 60)}m`
  const driftColor = drift >= 0 ? 'text-up' : 'text-down'

  return (
    <div className={`flex items-center flex-wrap gap-x-5 gap-y-1 px-3 py-1.5 rounded-md mb-2 text-[11.5px] border ${
      crossed ? 'bg-accent-soft border-accent/40' : 'bg-raised border-line'}`}>
      <span className="text-fg-faint">Frozen <span className="num text-fg-soft font-medium">{frozen.toPrecision(6)}</span>
        <span className="num text-fg-faint"> · {age} ago</span></span>
      <span className="text-fg-faint">Live <span className="num text-fg font-medium">{live.toPrecision(6)}</span></span>
      <span className="text-fg-faint">Drift <span className={`num font-medium ${driftColor}`}>{drift >= 0 ? '+' : ''}{drift.toFixed(2)}%</span></span>
      {crossed && (
        <span className="text-accent font-medium flex items-center gap-1">
          <TriangleAlert size={12} aria-label="warning" /> Live price crossed the {crossed} — plan is stale
        </span>
      )}
      <button onClick={onReanalyze}
        className={`btn !h-6 !px-2 !text-[11px] ml-auto ${crossed ? 'btn-primary' : ''}`}>
        <RefreshCw size={11} aria-label="Re-analyze" /> Re-analyze
      </button>
    </div>
  )
}
