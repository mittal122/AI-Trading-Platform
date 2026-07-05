import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart, ColorType, CandlestickSeries, createSeriesMarkers,
} from 'lightweight-charts'
import type {
  IChartApi, ISeriesApi, IPriceLine, ISeriesMarkersPluginApi, Time, UTCTimestamp,
} from 'lightweight-charts'
import { RectanglesPrimitive } from '../lib/rectanglePrimitive'
import type { RectangleSpec } from '../lib/rectanglePrimitive'
import { getSmcAnalysis } from '../api/client'
import type { SmcAnalysis } from '../api/client'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { usePersistedState } from '../hooks/usePersistedState'
import SmcVerdictCard from '../components/smc/SmcVerdictCard'
import SmcScoreBars from '../components/smc/SmcScoreBars'
import SmcTradePlanCard from '../components/smc/SmcTradePlanCard'
import SmcOrderFlowPanel from '../components/smc/SmcOrderFlowPanel'
import SmcBacktestPanel from '../components/smc/SmcBacktestPanel'

const INTERVALS = ['5m', '15m', '30m', '1h', '4h', '1d']

const toSec = (iso: string) => Math.floor(Date.parse(iso) / 1000) as UTCTimestamp

// Zone colouring: POIs (the double-confluence signature zone) in gold, everything
// else by directional bias.
function zoneColors(label: string, bias?: string): [string, string] {
  if (label === 'POI') return ['rgba(212,175,55,0.12)', 'rgba(212,175,55,0.65)']
  if (bias === 'BULLISH') return ['rgba(34,197,94,0.10)', 'rgba(34,197,94,0.5)']
  if (bias === 'BEARISH') return ['rgba(239,68,68,0.10)', 'rgba(239,68,68,0.5)']
  return ['rgba(148,163,184,0.08)', 'rgba(148,163,184,0.4)']
}

const LEVEL_STYLE: Record<string, { color: string; dashed?: boolean }> = {
  Entry: { color: '#e2e8f0' }, Stop: { color: '#ef4444' },
  TP1: { color: '#22c55e' }, TP2: { color: '#22c55e' },
  EQH: { color: '#64748b', dashed: true }, EQL: { color: '#64748b', dashed: true },
}

export default function SmcAnalyzer() {
  const [symbol, setSymbol] = usePersistedState('smc.symbol', 'BTCUSDT')
  const [interval, setInterval] = usePersistedState('smc.interval', '1h')
  const [analysis, setAnalysis] = useState<SmcAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const chartRef = useRef<HTMLDivElement>(null)
  const chartApiRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const rectRef = useRef<RectanglesPrimitive | null>(null)
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])

  const run = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const { data } = await getSmcAnalysis(symbol, interval, 500)
      setAnalysis(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Analysis failed. Is the backend running?')
      setAnalysis(null)
    } finally {
      setLoading(false)
    }
  }, [symbol, interval])

  useEffect(() => { run() }, [run])

  // Create the chart once.
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0f1117' }, textColor: '#64748b' },
      grid: { vertLines: { color: '#1a1d27' }, horzLines: { color: '#1a1d27' } },
      timeScale: { borderColor: '#2a2d3e' },
      rightPriceScale: { borderColor: '#2a2d3e' },
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        axisDoubleClickReset: { time: true, price: true },
        mouseWheel: true, pinch: true,
      },
      width: chartRef.current.clientWidth, height: 440,
    })
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    })
    chartApiRef.current = chart
    candleSeriesRef.current = series
    markersRef.current = createSeriesMarkers(series, [])
    const rect = new RectanglesPrimitive()
    series.attachPrimitive(rect)
    rectRef.current = rect

    const onResize = () => chart.applyOptions({ width: chartRef.current?.clientWidth ?? 600 })
    window.addEventListener('resize', onResize)
    return () => { window.removeEventListener('resize', onResize); chart.remove() }
  }, [])

  // Draw the analysis whenever it changes.
  useEffect(() => {
    const chart = chartApiRef.current, series = candleSeriesRef.current
    if (!chart || !series || !analysis) return

    series.setData(analysis.candles.map(c => ({
      time: toSec(c.time), open: c.open, high: c.high, low: c.low, close: c.close,
    })))

    const lastTime = toSec(analysis.candles[analysis.candles.length - 1].time)
    const backstopTime = toSec(analysis.candles[Math.max(0, analysis.candles.length - 40)].time)

    const rects: RectangleSpec[] = (analysis.annotations?.zones ?? []).map(z => {
      let t1 = toSec(z.start_time)
      const t2 = lastTime
      if (t1 >= t2) t1 = backstopTime
      const [fill, border] = zoneColors(z.label, z.bias)
      return { time1: t1, time2: t2, price1: z.top, price2: z.bottom, fillColor: fill, borderColor: border, label: z.label }
    })
    rectRef.current?.setRectangles(rects)

    priceLinesRef.current.forEach(l => series.removePriceLine(l))
    priceLinesRef.current = (analysis.annotations?.levels ?? []).map(lv => {
      const st = LEVEL_STYLE[lv.label] ?? { color: '#64748b' }
      return series.createPriceLine({
        price: lv.price, color: st.color, lineWidth: 1,
        lineStyle: st.dashed ? 2 : 0, axisLabelVisible: true, title: lv.label,
      })
    })

    markersRef.current?.setMarkers((analysis.annotations?.labels ?? []).map(l => ({
      time: toSec(l.time), position: 'aboveBar' as const,
      color: '#d4af37', shape: 'circle' as const, text: l.text,
    })))

    chart.timeScale().fitContent()
    series.priceScale().applyOptions({ autoScale: true })
  }, [analysis])

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">SMC Analyzer</h1>
          <p className="text-xs text-slate-500">Smart Money Concepts — structure, zones & a rules-based trade plan</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-44"><SymbolSearchInput value={symbol} onChange={setSymbol} /></div>
          <select value={interval} onChange={e => setInterval(e.target.value)}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-2 text-xs text-white outline-none">
            {INTERVALS.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
          <button onClick={run} disabled={loading}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg px-4 py-3">{error}</div>}

      {/* Hero: the one thing a user needs — is there a signal, and which way? */}
      {analysis && (
        <SignalBanner analysis={analysis} />
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-4 items-start">
        <div className="space-y-4">
          <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-3">
            <div ref={chartRef} />
            {analysis && (
              <>
                <div className="flex flex-wrap gap-x-4 gap-y-1 px-2 pt-2 text-[11px] text-slate-500">
                  <span><span className="text-amber-400">▢</span> POI</span>
                  <span><span className="text-green-400">▢</span> Bullish OB / demand / FVG</span>
                  <span><span className="text-red-400">▢</span> Bearish OB / supply / FVG</span>
                  <span><span className="text-amber-400">●</span> BOS / CHoCH</span>
                  <span className="ml-auto text-slate-600">
                    Frozen {new Date(analysis.frozen_at).toLocaleTimeString()} · ATR {analysis.atr.toFixed(2)}
                  </span>
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 px-2 pt-1 text-[11px] text-slate-600">
                  <span>Live structure:</span>
                  <span>{analysis.order_blocks.filter(o => !o.mitigated).length} order blocks</span>
                  <span>· {analysis.fvgs.filter(f => !f.filled).length} open FVGs</span>
                  <span>· {analysis.pois.length} POIs</span>
                  <span>· {analysis.supply_demand.filter(z => !z.mitigated).length} demand/supply</span>
                  <span>· {analysis.sweeps.filter(s => s.recent).length} recent sweeps</span>
                </div>
              </>
            )}
          </div>

          {analysis && analysis.reasons.length > 0 && (
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
              <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Why this read</p>
              <ul className="space-y-1">
                {analysis.reasons.map((r, i) => (
                  <li key={i} className="text-sm text-slate-300 flex gap-2">
                    <span className="text-slate-600">·</span>{r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="space-y-4">
          {analysis?.verdict && <SmcVerdictCard a={analysis} />}
          {analysis?.long_plan && <SmcTradePlanCard plan={analysis.long_plan} />}
          {analysis?.short_plan && <SmcTradePlanCard plan={analysis.short_plan} />}
          {analysis?.verdict && <SmcScoreBars v={analysis.verdict} />}
          {analysis?.order_flow && <SmcOrderFlowPanel of={analysis.order_flow} />}
          {analysis && (
            <p className="text-[11px] text-slate-600 leading-relaxed px-1">
              For research and education only — not financial advice. This is a
              deterministic rules-based read of past price action; markets can and
              do move against any setup. Size and manage risk yourself.
            </p>
          )}
        </div>
      </div>

      <SmcBacktestPanel symbol={symbol} interval={interval} />
    </div>
  )
}

function SignalBanner({ analysis }: { analysis: SmcAnalysis }) {
  const primary = analysis.primary
  if (primary === 'neutral') {
    return (
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl px-5 py-4 flex items-center gap-3">
        <span className="text-slate-500 text-lg">○</span>
        <div>
          <p className="text-sm font-medium text-slate-300">No high-confidence setup right now</p>
          <p className="text-xs text-slate-500">Neither side cleared the confluence checklist. Strong SMC signals are intentionally rare — wait for one.</p>
        </div>
      </div>
    )
  }
  const plan = primary === 'long' ? analysis.long_plan! : analysis.short_plan!
  const isLong = primary === 'long'
  // Static class strings — Tailwind v4 JIT can't see interpolated class names.
  const wrap = isLong ? 'bg-green-500/10 border-green-500/40' : 'bg-red-500/10 border-red-500/40'
  const text = isLong ? 'text-green-400' : 'text-red-400'
  const badge = isLong ? 'text-green-400 border-green-500/40' : 'text-red-400 border-red-500/40'
  return (
    <div className={`${wrap} border rounded-xl px-5 py-4`}>
      <div className="flex items-center flex-wrap gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <span className={`${text} text-2xl font-bold uppercase`}>{primary} signal</span>
          <span className={`text-xs font-bold px-2 py-1 rounded-lg border ${badge}`}>
            {plan.strength_score}/110 · {plan.strength}
          </span>
        </div>
        <div className="flex gap-5 text-sm">
          <span className="text-slate-400">Entry <span className="text-white font-medium">{plan.entry.toPrecision(6)}</span></span>
          <span className="text-slate-400">Stop <span className="text-red-400 font-medium">{plan.stop_loss.toPrecision(6)}</span></span>
          <span className="text-slate-400">TP1 <span className="text-green-400 font-medium">{plan.take_profit_1.toPrecision(6)}</span></span>
          <span className="text-slate-400">R:R <span className="text-white font-medium">{plan.risk_reward.toFixed(2)}:1</span></span>
        </div>
      </div>
    </div>
  )
}
