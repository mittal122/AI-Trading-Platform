import { useState } from 'react'
import { Check, Dot, X, Zap } from 'lucide-react'
import { placePaperOrder } from '../../api/client'
import type { SmcTradePlan } from '../../api/client'

const STRENGTH_CHIP: Record<string, string> = {
  STRONG: 'chip-up', MODERATE: 'chip-warn', WEAK: 'chip-muted', REJECTED: 'chip-down',
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
    <div className="bg-raised border border-line rounded-md p-2.5">
      <p className="field-label">{label}</p>
      <p className={`num text-sm font-semibold ${color}`}>{fmt(value)}</p>
    </div>
  )
}

export default function SmcTradePlanCard({ plan, symbol, interval, onCardClick, chartActive }: {
  plan: SmcTradePlan; symbol?: string; interval?: string
  /** When set, clicking the card body toggles this plan's Entry/Stop/TP1/TP2
   *  lines on the SMC chart (inner buttons are excluded). */
  onCardClick?: (plan: SmcTradePlan) => void
  chartActive?: boolean
}) {
  const isLong = plan.side === 'long'
  const sideColor = isLong ? 'text-up' : 'text-down'
  const conf = plan.confluence
  const [placing, setPlacing] = useState(false)
  const [placed, setPlaced] = useState<string | null>(null)

  function handleCardClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!onCardClick) return
    if ((e.target as HTMLElement).closest('button, a, summary, details')) return
    onCardClick(plan)
  }

  async function paperTrade() {
    if (!symbol) return
    setPlacing(true); setPlaced(null)
    try {
      const { data } = await placePaperOrder({
        symbol, strategy: 'smc', direction: isLong ? 'BUY' : 'SELL',
        entry: plan.entry, stop_loss: plan.stop_loss, take_profit: plan.take_profit_1,
        interval: interval ?? '1h', risk_percent: 2,
      })
      setPlaced(`Paper order #${data.id} opened`)
    } catch (e: any) {
      setPlaced(e?.response?.data?.detail ?? 'Could not place order')
    } finally {
      setPlacing(false)
    }
  }

  return (
    <div
      className={`card p-4 ${onCardClick ? 'cursor-pointer' : ''} ${chartActive ? '!border-accent/50' : plan.fired ? (isLong ? '!border-up/40' : '!border-down/40') : ''}`}
      onClick={handleCardClick}
      title={onCardClick ? (chartActive ? 'Click to remove levels from chart' : 'Click to plot Entry / Stop / TP levels on the chart') : undefined}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold uppercase ${sideColor}`}>{plan.side}</span>
          <span className="text-[11px] text-fg-faint">from {plan.source.replace('_', ' ')}</span>
          {chartActive && <span className="text-[11px] text-accent font-medium">● on chart</span>}
        </div>
        <span className={`chip ${STRENGTH_CHIP[plan.strength]}`}>
          {plan.fired && <Zap size={10} aria-label="fired" />}
          {plan.fired ? 'FIRED' : plan.strength} · <span className="num">{plan.strength_score}/110</span>
        </span>
      </div>

      <div className="grid grid-cols-4 gap-2">
        <Level label="Entry" value={plan.entry} color="text-fg" />
        <Level label="Stop" value={plan.stop_loss} color="text-down" />
        <Level label="TP1" value={plan.take_profit_1} color="text-up" />
        <Level label="TP2" value={plan.take_profit_2} color="text-up" />
      </div>
      <p className="mt-2 text-xs text-fg-faint">
        Reward:risk <span className="num text-fg-soft font-medium">{plan.risk_reward.toFixed(2)}:1</span>
        <span> · {plan.note}</span>
      </p>

      {conf && (
        <div className="mt-3 border-t border-line pt-3">
          <p className="field-label mb-2">Confluence</p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            {conf.factors.map(f => (
              <div key={f.name} className="flex items-center gap-1.5 text-xs">
                {f.hit
                  ? <Check size={12} className="text-up shrink-0" aria-label="met" />
                  : <Dot size={12} className="text-fg-faint shrink-0" aria-label="not met" />}
                <span className={f.hit ? 'text-fg-soft' : 'text-fg-faint'}>
                  {FACTOR_LABEL[f.name] ?? f.name}
                </span>
                <span className="num text-fg-faint ml-auto">+{f.points}</span>
              </div>
            ))}
          </div>
          {conf.reject_reasons.length > 0 && (
            <div className="mt-2 space-y-1">
              {conf.reject_reasons.map((r, i) => (
                <p key={i} className="text-xs text-down/80 flex items-center gap-1">
                  <X size={11} className="shrink-0" aria-label="rejected" /> {r}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {symbol && (
        <div className="mt-3 flex items-center gap-3">
          <button onClick={paperTrade} disabled={placing}
            className={`btn !h-7 !text-xs ${isLong ? 'btn-buy' : 'btn-sell'}`}>
            {placing ? 'Placing…' : 'Paper-trade this plan'}
          </button>
          {placed && <span className="text-xs text-fg-soft">{placed}</span>}
        </div>
      )}
    </div>
  )
}
