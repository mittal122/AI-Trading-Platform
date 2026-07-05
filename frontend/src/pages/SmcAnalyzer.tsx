import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart, ColorType, CandlestickSeries, LineSeries, createSeriesMarkers,
} from 'lightweight-charts'
import type {
  IChartApi, ISeriesApi, IPriceLine, ISeriesMarkersPluginApi, Time, UTCTimestamp,
  MouseEventParams,
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
import SmcScannerPanel from '../components/smc/SmcScannerPanel'
import SmcFreezeBar from '../components/smc/SmcFreezeBar'

const INTERVALS = ['5m', '15m', '30m', '1h', '4h', '1d']

type LayerKey = 'zones' | 'structure' | 'liquidity' | 'sweeps' | 'inducements' | 'equilibrium' | 'plan' | 'swings'
const LAYER_DEFS: { key: LayerKey; label: string }[] = [
  { key: 'zones', label: 'Zones' }, { key: 'structure', label: 'BOS/CHoCH' },
  { key: 'plan', label: 'Trade plan' }, { key: 'liquidity', label: 'Liquidity' },
  { key: 'equilibrium', label: 'Equilibrium' }, { key: 'sweeps', label: 'Sweeps' },
  { key: 'swings', label: 'Swings' }, { key: 'inducements', label: 'Inducements' },
]
const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  zones: true, structure: true, plan: true, liquidity: true,
  equilibrium: true, sweeps: true, swings: false, inducements: false,
}

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
  const [layers, setLayers] = usePersistedState<Record<LayerKey, boolean>>('smc.layers', DEFAULT_LAYERS)
  const toggle = (k: LayerKey) => setLayers(l => ({ ...l, [k]: !l[k] }))

  // Drawn trend lines, persisted per symbol+interval (a map keyed by both).
  type TL = { p1: { time: number; price: number }; p2: { time: number; price: number } }
  const [allTrendlines, setAllTrendlines] = usePersistedState<Record<string, TL[]>>('smc.trendlines', {})
  const tlKey = `${symbol}_${interval}`
  const trendlines = allTrendlines[tlKey] ?? []
  const [drawMode, setDrawMode] = useState(false)
  const [isFull, setIsFull] = useState(false)

  const chartCardRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<HTMLDivElement>(null)
  const chartApiRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const rectRef = useRef<RectanglesPrimitive | null>(null)
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])
  const trendSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const pendingPointRef = useRef<{ time: number; price: number } | null>(null)
  const drawModeRef = useRef(false)
  const addTrendlineRef = useRef<(tl: TL) => void>(() => {})

  drawModeRef.current = drawMode
  addTrendlineRef.current = (tl: TL) =>
    setAllTrendlines(m => ({ ...m, [tlKey]: [...(m[tlKey] ?? []), tl] }))
  const clearTrendlines = () => setAllTrendlines(m => ({ ...m, [tlKey]: [] }))

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

    // Trend-line drawing: two clicks (bar-time + price) define a segment.
    const clickHandler = (param: MouseEventParams) => {
      if (!drawModeRef.current || !param.point || param.time === undefined) return
      const price = series.coordinateToPrice(param.point.y)
      if (price === null) return
      const pt = { time: param.time as number, price: price as number }
      if (!pendingPointRef.current) { pendingPointRef.current = pt; return }
      addTrendlineRef.current({ p1: pendingPointRef.current, p2: pt })
      pendingPointRef.current = null
    }
    chart.subscribeClick(clickHandler)

    const resize = () => {
      const full = !!document.fullscreenElement
      chart.applyOptions({
        width: chartRef.current?.clientWidth ?? 600,
        height: full ? Math.max(440, window.innerHeight - 150) : 440,
      })
    }
    const onFsChange = () => { setIsFull(!!document.fullscreenElement); setTimeout(resize, 60) }
    window.addEventListener('resize', resize)
    document.addEventListener('fullscreenchange', onFsChange)
    return () => {
      window.removeEventListener('resize', resize)
      document.removeEventListener('fullscreenchange', onFsChange)
      chart.unsubscribeClick(clickHandler)
      chart.remove()
    }
  }, [])

  // Draw the analysis whenever it (or the layer toggles) change.
  useEffect(() => {
    const chart = chartApiRef.current, series = candleSeriesRef.current
    if (!chart || !series || !analysis) return
    const candles = analysis.candles
    const at = (idx: number) => toSec(candles[Math.max(0, Math.min(candles.length - 1, idx))].time)

    series.setData(candles.map(c => ({
      time: toSec(c.time), open: c.open, high: c.high, low: c.low, close: c.close,
    })))

    const lastTime = toSec(candles[candles.length - 1].time)
    const backstopTime = toSec(candles[Math.max(0, candles.length - 40)].time)

    // ── Zones (order blocks / FVGs / POIs / demand-supply) ──
    const rects: RectangleSpec[] = layers.zones
      ? (analysis.annotations?.zones ?? []).map(z => {
          let t1 = toSec(z.start_time)
          if (t1 >= lastTime) t1 = backstopTime
          const [fill, border] = zoneColors(z.label, z.bias)
          return { time1: t1, time2: lastTime, price1: z.top, price2: z.bottom, fillColor: fill, borderColor: border, label: z.label }
        })
      : []
    rectRef.current?.setRectangles(rects)

    // ── Price lines: liquidity (EQH/EQL), equilibrium, trade plan ──
    priceLinesRef.current.forEach(l => series.removePriceLine(l))
    const lines: any[] = []
    if (layers.liquidity) {
      for (const p of analysis.liquidity_pools) {
        lines.push(series.createPriceLine({
          price: p.price, color: '#64748b', lineWidth: 1, lineStyle: 2,
          axisLabelVisible: true, title: p.direction === 'BEARISH' ? 'EQH' : 'EQL',
        }))
      }
    }
    if (layers.equilibrium && analysis.dealing_range) {
      lines.push(series.createPriceLine({
        price: analysis.dealing_range.equilibrium, color: '#d4af37', lineWidth: 1,
        lineStyle: 2, axisLabelVisible: true, title: 'EQ',
      }))
    }
    if (layers.plan) {
      for (const lv of analysis.annotations?.levels ?? []) {
        const st = LEVEL_STYLE[lv.label]
        if (!st) continue   // only plan levels here (Entry/Stop/TP*)
        lines.push(series.createPriceLine({
          price: lv.price, color: st.color, lineWidth: 1,
          lineStyle: st.dashed ? 2 : 0, axisLabelVisible: true, title: lv.label,
        }))
      }
    }
    priceLinesRef.current = lines

    // ── Markers: structure, swings, sweeps, inducements ──
    const markers: any[] = []
    if (layers.structure) {
      for (const l of analysis.annotations?.labels ?? [])
        markers.push({ time: toSec(l.time), position: 'aboveBar', color: '#d4af37', shape: 'circle', text: l.text })
    }
    if (layers.swings) {
      for (const s of analysis.swings) {
        if (!s.label) continue
        const bull = s.label === 'HH' || s.label === 'HL'
        markers.push({ time: toSec(s.time), position: s.is_high ? 'aboveBar' : 'belowBar',
          color: bull ? '#22c55e' : '#ef4444', shape: 'circle', text: s.label })
      }
    }
    if (layers.sweeps) {
      for (const sw of analysis.sweeps) {
        const bull = sw.direction === 'BULLISH'
        markers.push({ time: at(sw.reversal_index), position: bull ? 'belowBar' : 'aboveBar',
          color: '#eab308', shape: 'circle', text: 'sweep' })
      }
    }
    if (layers.inducements) {
      for (const idm of analysis.inducements) {
        const bull = idm.direction === 'BULLISH'
        markers.push({ time: at(idm.index), position: bull ? 'belowBar' : 'aboveBar',
          color: '#94a3b8', shape: 'square', text: 'IDM' })
      }
    }
    markers.sort((a, b) => (a.time as number) - (b.time as number))
    markersRef.current?.setMarkers(markers)

    chart.timeScale().fitContent()
    series.priceScale().applyOptions({ autoScale: true })
  }, [analysis, layers])

  // Redraw user-drawn trend lines whenever they change (or the symbol/tf does).
  useEffect(() => {
    const chart = chartApiRef.current
    if (!chart) return
    trendSeriesRef.current.forEach(s => { try { chart.removeSeries(s) } catch { /* gone */ } })
    trendSeriesRef.current = trendlines.map(tl => {
      const s = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2, lastValueVisible: false, priceLineVisible: false })
      const pts = [
        { time: tl.p1.time as UTCTimestamp, value: tl.p1.price },
        { time: tl.p2.time as UTCTimestamp, value: tl.p2.price },
      ].sort((a, b) => (a.time as number) - (b.time as number))
      s.setData(pts)
      return s
    })
  }, [trendlines])

  async function toggleFullscreen() {
    if (document.fullscreenElement) { await document.exitFullscreen() }
    else if (chartCardRef.current) { await chartCardRef.current.requestFullscreen() }
  }

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
          <div ref={chartCardRef} className={`bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-3 ${isFull ? 'flex flex-col justify-center' : ''}`}>
            {analysis && !isFull && <SmcFreezeBar analysis={analysis} onReanalyze={run} />}
            {analysis && (
              <div className="flex items-center flex-wrap gap-1.5 px-1 pb-2">
                {analysis.htf?.available && (
                  <span className={`text-[11px] font-medium px-2 py-1 rounded-lg border mr-1 ${
                    analysis.htf.trend === 'up' ? 'text-green-400 border-green-500/30'
                      : analysis.htf.trend === 'down' ? 'text-red-400 border-red-500/30'
                      : 'text-slate-400 border-slate-500/30'}`}>
                    HTF {analysis.htf.trend}
                  </span>
                )}
                {LAYER_DEFS.map(l => (
                  <button key={l.key} onClick={() => toggle(l.key)}
                    className={`text-[11px] px-2 py-1 rounded-lg border transition-colors ${
                      layers[l.key]
                        ? 'bg-indigo-500/15 border-indigo-500/40 text-indigo-300'
                        : 'bg-[#0f1117] border-[#2a2d3e] text-slate-600 hover:text-slate-400'}`}>
                    {l.label}
                  </button>
                ))}
                <div className="ml-auto flex items-center gap-1.5">
                  <button onClick={() => setDrawMode(d => !d)}
                    className={`text-[11px] px-2 py-1 rounded-lg border ${
                      drawMode ? 'bg-sky-500/20 border-sky-500/50 text-sky-300'
                        : 'bg-[#0f1117] border-[#2a2d3e] text-slate-400 hover:text-white'}`}>
                    ✎ Trend line
                  </button>
                  {trendlines.length > 0 && (
                    <button onClick={clearTrendlines}
                      className="text-[11px] px-2 py-1 rounded-lg border bg-[#0f1117] border-[#2a2d3e] text-slate-400 hover:text-red-400">Clear</button>
                  )}
                  <button onClick={toggleFullscreen}
                    className="text-[11px] px-2 py-1 rounded-lg border bg-[#0f1117] border-[#2a2d3e] text-slate-400 hover:text-white">
                    ⛶ {isFull ? 'Exit' : 'Fullscreen'}
                  </button>
                </div>
              </div>
            )}
            {drawMode && (
              <p className="text-[11px] text-sky-300/80 px-1 pb-1">Click two points on the chart to draw a trend line.</p>
            )}
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

          {/* Fill the space under the chart with the context panels, so the
              left column keeps pace with the taller decision column at right. */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
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
            {analysis?.order_flow && <SmcOrderFlowPanel of={analysis.order_flow} />}
            {analysis?.verdict && <div className="lg:col-span-2"><SmcScoreBars v={analysis.verdict} /></div>}
          </div>
        </div>

        <div className="space-y-4">
          {analysis?.verdict && <SmcVerdictCard a={analysis} />}
          {analysis?.long_plan && <SmcTradePlanCard plan={analysis.long_plan} symbol={symbol} interval={interval} />}
          {analysis?.short_plan && <SmcTradePlanCard plan={analysis.short_plan} symbol={symbol} interval={interval} />}
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
      <SmcScannerPanel />
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
