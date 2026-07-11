import type { Indicators } from '../api/client'

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-line/50 last:border-0">
      <span className="text-xs text-fg-faint">{label}</span>
      <span className={`num text-xs font-semibold ${color ?? 'text-fg'}`}>{value}</span>
    </div>
  )
}

export default function IndicatorPanel({ ind, symbol }: { ind: Indicators; symbol: string }) {
  const rsiColor = ind.rsi14 > 70 ? 'text-down' : ind.rsi14 < 30 ? 'text-up' : 'text-fg'
  const macdColor = ind.histogram >= 0 ? 'text-up' : 'text-down'
  const priceVsBB = ind.price > ind.bb_upper ? 'text-down' :
                    ind.price < ind.bb_lower ? 'text-up' : 'text-fg'

  return (
    <div className="card px-3 py-2.5">
      <h3 className="panel-title mb-2">
        Indicators · {symbol}
      </h3>
      <Row label="Price"      value={`$${ind.price.toFixed(2)}`} color={priceVsBB} />
      <Row label="RSI(14)"    value={ind.rsi14.toFixed(2)} color={rsiColor} />
      <Row label="MACD"       value={ind.macd.toFixed(4)} />
      <Row label="Histogram"  value={ind.histogram.toFixed(4)} color={macdColor} />
      <Row label="EMA(20)"    value={`$${ind.ema20.toFixed(2)}`} />
      <Row label="SMA(20)"    value={`$${ind.sma20.toFixed(2)}`} />
      <Row label="ATR(14)"    value={ind.atr14.toFixed(4)} />
      <Row label="VWAP"       value={`$${ind.vwap.toFixed(2)}`} />
      <Row label="BB Upper"   value={`$${ind.bb_upper.toFixed(2)}`} />
      <Row label="BB Lower"   value={`$${ind.bb_lower.toFixed(2)}`} />
    </div>
  )
}
