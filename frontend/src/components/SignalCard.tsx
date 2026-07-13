import { useState } from 'react'
import { ArrowUpRight, ArrowDownRight, Minus, Check, AlertTriangle, ChevronDown } from 'lucide-react'
import type { TradingSignal } from '../api/client'
import { placePaperOrder } from '../api/client'
import RegimeBadge from './RegimeBadge'

const DIR_CHIP: Record<string, string> = {
  BUY:  'chip-up',
  SELL: 'chip-down',
  FLAT: 'chip-muted',
}

const GRADE_COLOR: Record<string, string> = {
  'A+': 'text-up', A: 'text-up', B: 'text-accent',
  C: 'text-accent', D: 'text-down', F: 'text-down',
}

export default function SignalCard({ signal, onCardClick, chartActive }: {
  signal: TradingSignal
  /** When set, clicking the card body toggles the signal's Entry/Stop/Target
   *  lines on the page's chart (inner buttons/links are excluded). */
  onCardClick?: (signal: TradingSignal) => void
  chartActive?: boolean
}) {
  const dir = signal.direction
  const dirChip = DIR_CHIP[dir] ?? DIR_CHIP.FLAT

  const [placing, setPlacing] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const tradeable = dir === 'BUY' || dir === 'SELL'

  async function placeTrade() {
    setPlacing(true)
    setResult(null)
    try {
      const res = await placePaperOrder({
        symbol: signal.symbol,
        strategy: signal.strategy,
        direction: dir,
        entry: signal.entry,
        stop_loss: signal.stop_loss,
        take_profit: signal.take_profit,
        interval: '1m',
      })
      setResult({ ok: true, msg: `Paper trade #${res.data.id} placed — ${res.data.quantity.toFixed(6)} ${signal.symbol} @ $${res.data.entry.toFixed(2)}. Monitoring for SL/TP.` })
    } catch (e: any) {
      setResult({ ok: false, msg: e?.response?.data?.detail ?? 'Failed to place paper trade' })
    } finally {
      setPlacing(false)
    }
  }

  function handleCardClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!onCardClick) return
    // Inner interactive elements (paper-trade button, explanation toggle)
    // keep their own behavior — only clicks on the card body toggle the chart.
    if ((e.target as HTMLElement).closest('button, summary, a, details')) return
    onCardClick(signal)
  }

  return (
    <div
      className={`card ${onCardClick ? 'cursor-pointer' : ''} ${chartActive ? '!border-accent/50' : ''}`}
      onClick={handleCardClick}
      title={onCardClick ? (chartActive ? 'Click to remove levels from chart' : 'Click to plot Entry / Stop / Target on the chart') : undefined}
    >
      {/* Direction hero */}
      <header className="flex items-center justify-between px-3 pt-3 pb-2">
        <div className="flex items-center gap-2">
          <span className={`chip ${dirChip} !h-7 !px-2.5 !text-[14px]`}>
            {dir === 'BUY' && <ArrowUpRight size={15} aria-label="buy signal" />}
            {dir === 'SELL' && <ArrowDownRight size={15} aria-label="sell signal" />}
            {dir === 'FLAT' && <Minus size={13} aria-label="no signal" />}
            {dir}
          </span>
          {signal.quality_grade && (
            <span className={`num text-[14px] font-bold ${GRADE_COLOR[signal.quality_grade] ?? 'text-fg-soft'}`}
              title="Trade quality grade">
              {signal.quality_grade}
            </span>
          )}
        </div>
        <RegimeBadge regime={signal.regime} />
      </header>
      <p className="px-3 pb-2 text-[11px] text-fg-faint">
        {signal.symbol} · {signal.interval} · {signal.strategy}
      </p>

      <div className="px-3 pb-3 space-y-3">
        {/* Entry / SL / TP */}
        <div className="grid grid-cols-3 gap-px rounded-md overflow-hidden border border-line bg-line">
          <PriceCell label="Entry" value={signal.entry.toFixed(2)} />
          <PriceCell label="Stop" value={signal.stop_loss.toFixed(2)} cls="text-down" />
          <PriceCell label="Target" value={signal.take_profit.toFixed(2)} cls="text-up" />
        </div>

        {/* Compact stats */}
        <div className="flex items-center gap-4 text-[11px]">
          <span className="text-fg-faint">Conf <span className="num font-semibold text-fg">{signal.confidence.toFixed(1)}%</span></span>
          <span className="text-fg-faint">R:R <span className="num font-semibold text-fg">1:{signal.risk_reward.toFixed(2)}</span></span>
          {signal.eta_display && (
            <span className="text-fg-faint">ETA <span className="num font-semibold text-accent">{signal.eta_display}</span></span>
          )}
          {chartActive && <span className="text-accent font-medium">● on chart</span>}
        </div>

        {/* Reasons */}
        {signal.reasons.length > 0 && (
          <ul className="space-y-0.5">
            {signal.reasons.map((r, i) => (
              <li key={i} className="text-[11px] text-fg-soft pl-2 border-l border-line-strong">{r}</li>
            ))}
          </ul>
        )}

        {/* Explanation — collapsed by default */}
        {signal.explanation && (
          <details className="border-t border-line pt-2 group">
            <summary className="flex items-center gap-1 text-[11px] text-fg-faint cursor-pointer list-none select-none">
              <ChevronDown size={12} aria-label="toggle explanation" className="transition-transform group-open:rotate-180" />
              Explanation
            </summary>
            <p className="text-[11px] text-fg-faint mt-1.5 whitespace-pre-line leading-relaxed">
              {signal.explanation.slice(0, 300)}
            </p>
          </details>
        )}

        {/* Place Paper Trade */}
        <div className="border-t border-line pt-3 space-y-2">
          <button
            onClick={placeTrade}
            disabled={!tradeable || placing}
            className={`btn w-full ${dir === 'BUY' ? 'btn-buy' : dir === 'SELL' ? 'btn-sell' : ''}`}
          >
            {!tradeable
              ? 'No trade — signal is FLAT'
              : placing
                ? 'Placing…'
                : <>Place Paper Trade <span className="num">({dir} @ ${signal.entry.toFixed(2)})</span></>}
          </button>
          {result && (
            <p className={`flex items-start gap-1 text-xs ${result.ok ? 'text-up' : 'text-down'}`}>
              {result.ok
                ? <Check size={13} aria-label="success" className="shrink-0 mt-px" />
                : <AlertTriangle size={13} aria-label="error" className="shrink-0 mt-px" />}
              {result.msg}
            </p>
          )}
        </div>

        <p className="num text-[10px] text-fg-faint">{signal.timestamp}</p>
      </div>
    </div>
  )
}

function PriceCell({ label, value, cls = 'text-fg' }: {
  label: string; value: string; cls?: string
}) {
  return (
    <div className="bg-bg px-2 py-1.5">
      <p className="text-[9.5px] uppercase tracking-wider text-fg-faint mb-0.5">{label}</p>
      <p className={`num text-[13px] font-semibold ${cls}`}>{value}</p>
    </div>
  )
}
