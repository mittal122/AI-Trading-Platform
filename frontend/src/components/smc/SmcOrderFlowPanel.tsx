import type { SmcOrderFlow } from '../../api/client'

const PRESSURE_STYLE: Record<string, string> = {
  buy: 'text-green-400 bg-green-500/10 border-green-500/30',
  sell: 'text-red-400 bg-red-500/10 border-red-500/30',
  balanced: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
}

// A -1..+1 value drawn as a centered meter (green right / red left).
function Meter({ label, value, help }: { label: string; value: number; help: string }) {
  const pct = Math.min(50, Math.abs(value) * 50)
  const pos = value >= 0
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className={pos ? 'text-green-400' : 'text-red-400'}>
          {value >= 0 ? '+' : ''}{value.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2 bg-[#0f1117] rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 h-full w-px bg-[#2a2d3e]" />
        <div className={`absolute top-0 h-full ${pos ? 'bg-green-500/70' : 'bg-red-500/70'}`}
          style={pos ? { left: '50%', width: `${pct}%` } : { right: '50%', width: `${pct}%` }} />
      </div>
      <p className="text-[10px] text-slate-600 mt-0.5">{help}</p>
    </div>
  )
}

// Order flow is live microstructure (§8) — not part of the frozen snapshot's
// structure. Present here as the "who's pressing right now" read.
export default function SmcOrderFlowPanel({ of }: { of: SmcOrderFlow }) {
  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs uppercase tracking-widest text-slate-500">Order Flow</p>
        <span className={`text-xs font-bold px-2 py-1 rounded-lg border ${PRESSURE_STYLE[of.pressure]}`}>
          {of.pressure}
        </span>
      </div>
      <div className="space-y-3">
        <Meter label="Book imbalance" value={of.imbalance} help="Resting bids vs asks near price" />
        <Meter label="Taker delta (CVD)" value={of.cvd_ratio} help="Aggressive buys vs sells" />
      </div>
      {(of.bid_walls.length > 0 || of.ask_walls.length > 0) && (
        <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="text-slate-600 mb-1">Bid walls</p>
            {of.bid_walls.length
              ? of.bid_walls.map((w, i) => (
                  <p key={i} className="text-green-400/80">{w.price.toPrecision(6)} <span className="text-slate-600">({w.distance_pct.toFixed(2)}%)</span></p>))
              : <p className="text-slate-700">—</p>}
          </div>
          <div>
            <p className="text-slate-600 mb-1">Ask walls</p>
            {of.ask_walls.length
              ? of.ask_walls.map((w, i) => (
                  <p key={i} className="text-red-400/80">{w.price.toPrecision(6)} <span className="text-slate-600">({w.distance_pct.toFixed(2)}%)</span></p>))
              : <p className="text-slate-700">—</p>}
          </div>
        </div>
      )}
    </div>
  )
}
