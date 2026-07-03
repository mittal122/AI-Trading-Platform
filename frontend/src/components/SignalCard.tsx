import { useState } from 'react'
import type { TradingSignal } from '../api/client'
import { placePaperOrder } from '../api/client'
import RegimeBadge from './RegimeBadge'

const DIR_STYLE: Record<string, string> = {
  BUY:  'text-green-400 bg-green-500/10 border-green-500/30',
  SELL: 'text-red-400 bg-red-500/10 border-red-500/30',
  FLAT: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
}

const GRADE_COLOR: Record<string, string> = {
  'A+': 'text-green-400', A: 'text-green-500', B: 'text-yellow-400',
  C: 'text-orange-400', D: 'text-red-400', F: 'text-red-600',
}

export default function SignalCard({ signal }: { signal: TradingSignal }) {
  const dir = signal.direction
  const dirCls = DIR_STYLE[dir] ?? DIR_STYLE.FLAT

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

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold px-3 py-1 rounded-lg border ${dirCls}`}>
            {dir}
          </span>
          <span className="text-slate-400 text-sm">{signal.symbol} · {signal.interval}</span>
        </div>
        <div className="flex items-center gap-2">
          <RegimeBadge regime={signal.regime} />
          {signal.quality_grade && (
            <span className={`text-sm font-bold ${GRADE_COLOR[signal.quality_grade] ?? 'text-slate-400'}`}>
              {signal.quality_grade}
            </span>
          )}
        </div>
      </div>

      {/* Prices */}
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Entry" value={signal.entry.toFixed(2)} />
        <Stat label="Stop Loss" value={signal.stop_loss.toFixed(2)} color="text-red-400" />
        <Stat label="Take Profit" value={signal.take_profit.toFixed(2)} color="text-green-400" />
      </div>

      {/* Metrics */}
      <div className={`grid ${signal.eta_display ? 'grid-cols-3' : 'grid-cols-2'} gap-3`}>
        <Stat label="Confidence" value={`${(signal.confidence).toFixed(1)}%`} />
        <Stat label="Risk/Reward" value={`1:${signal.risk_reward.toFixed(2)}`} />
        {signal.eta_display && (
          <Stat label="Est. Time to Target" value={signal.eta_display} color="text-indigo-400" />
        )}
      </div>

      {/* Reasons */}
      {signal.reasons.length > 0 && (
        <div className="space-y-1">
          {signal.reasons.map((r, i) => (
            <p key={i} className="text-xs text-slate-400">• {r}</p>
          ))}
        </div>
      )}

      {/* Explanation */}
      {signal.explanation && (
        <p className="text-xs text-slate-500 border-t border-[#2a2d3e] pt-3 whitespace-pre-line">
          {signal.explanation.slice(0, 300)}
        </p>
      )}

      {/* Place Paper Trade */}
      <div className="border-t border-[#2a2d3e] pt-4 space-y-2">
        <button
          onClick={placeTrade}
          disabled={!tradeable || placing}
          className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-colors ${
            !tradeable
              ? 'bg-slate-700/40 text-slate-600 cursor-not-allowed'
              : placing
                ? 'bg-indigo-700 text-white/70'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          {!tradeable
            ? 'No trade — signal is FLAT'
            : placing
              ? 'Placing…'
              : `Place Paper Trade (${dir} @ $${signal.entry.toFixed(2)})`}
        </button>
        {result && (
          <p className={`text-xs ${result.ok ? 'text-green-400' : 'text-red-400'}`}>
            {result.ok ? '✓ ' : '⚠ '}{result.msg}
          </p>
        )}
      </div>

      <p className="text-xs text-slate-600">{signal.timestamp}</p>
    </div>
  )
}

function Stat({ label, value, color = 'text-white' }: {
  label: string; value: string; color?: string
}) {
  return (
    <div className="bg-[#0f1117] rounded-lg p-3">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-sm font-semibold ${color}`}>{value}</p>
    </div>
  )
}
