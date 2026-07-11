import type { SmcOrderFlow } from '../../api/client'

const PRESSURE_CHIP: Record<string, string> = {
  buy: 'chip-up', sell: 'chip-down', balanced: 'chip-muted',
}

// A -1..+1 value drawn as a centered meter (up-green right / down-red left).
function Meter({ label, value, help }: { label: string; value: number; help: string }) {
  const pct = Math.min(50, Math.abs(value) * 50)
  const pos = value >= 0
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-fg-soft">{label}</span>
        <span className={`num ${pos ? 'text-up' : 'text-down'}`}>
          {value >= 0 ? '+' : ''}{value.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2 bg-line rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 h-full w-px bg-line-strong" />
        <div className={`absolute top-0 h-full ${pos ? 'bg-up/70' : 'bg-down/70'}`}
          style={pos ? { left: '50%', width: `${pct}%` } : { right: '50%', width: `${pct}%` }} />
      </div>
      <p className="text-[10px] text-fg-faint mt-0.5">{help}</p>
    </div>
  )
}

// Order flow is live microstructure (§8) — not part of the frozen snapshot's
// structure. Present here as the "who's pressing right now" read.
export default function SmcOrderFlowPanel({ of }: { of: SmcOrderFlow }) {
  return (
    <div className="card card-pad">
      <div className="flex items-center justify-between mb-3">
        <p className="panel-title">Order Flow</p>
        <span className={`chip ${PRESSURE_CHIP[of.pressure]}`}>{of.pressure}</span>
      </div>
      <div className="space-y-3">
        <Meter label="Book imbalance" value={of.imbalance} help="Resting bids vs asks near price" />
        <Meter label="Taker delta (CVD)" value={of.cvd_ratio} help="Aggressive buys vs sells" />
      </div>
      {(of.bid_walls.length > 0 || of.ask_walls.length > 0) && (
        <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="text-fg-faint mb-1">Bid walls</p>
            {of.bid_walls.length
              ? of.bid_walls.map((w, i) => (
                  <p key={i} className="num text-up/80">{w.price.toPrecision(6)} <span className="text-fg-faint">({w.distance_pct.toFixed(2)}%)</span></p>))
              : <p className="text-fg-faint">—</p>}
          </div>
          <div>
            <p className="text-fg-faint mb-1">Ask walls</p>
            {of.ask_walls.length
              ? of.ask_walls.map((w, i) => (
                  <p key={i} className="num text-down/80">{w.price.toPrecision(6)} <span className="text-fg-faint">({w.distance_pct.toFixed(2)}%)</span></p>))
              : <p className="text-fg-faint">—</p>}
          </div>
        </div>
      )}
    </div>
  )
}
