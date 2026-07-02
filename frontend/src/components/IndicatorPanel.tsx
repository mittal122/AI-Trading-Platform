import type { Indicators } from '../api/client'

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-[#2a2d3e]/50 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={`text-xs font-mono font-semibold ${color ?? 'text-white'}`}>{value}</span>
    </div>
  )
}

export default function IndicatorPanel({ ind, symbol }: { ind: Indicators; symbol: string }) {
  const rsiColor = ind.rsi14 > 70 ? 'text-red-400' : ind.rsi14 < 30 ? 'text-green-400' : 'text-white'
  const macdColor = ind.histogram >= 0 ? 'text-green-400' : 'text-red-400'
  const priceVsBB = ind.price > ind.bb_upper ? 'text-red-400' :
                    ind.price < ind.bb_lower ? 'text-green-400' : 'text-white'

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
      <h3 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">
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
