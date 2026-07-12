import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries, createSeriesMarkers,
} from 'lightweight-charts'
import type {
  IChartApi, ISeriesApi, IPriceLine, ISeriesMarkersPluginApi, LogicalRange, Time, UTCTimestamp,
} from 'lightweight-charts'
import { Circle, Maximize2, Minimize2, Pencil } from 'lucide-react'
import { RectanglesPrimitive } from '../lib/rectanglePrimitive'
import type { RectangleSpec } from '../lib/rectanglePrimitive'
import { getSmcAnalysis, getLiveMarket, getMarket } from '../api/client'
import type { SmcAnalysis } from '../api/client'
import SymbolSearchInput from '../components/SymbolSearchInput'
import IndicatorSettings from '../components/IndicatorSettings'
import type { IndicatorConfig } from '../components/IndicatorSettings'
import { bestPivotTrendline, fibLevels } from '../lib/indicators'
import { usePersistedState } from '../hooks/usePersistedState'
import SmcVerdictCard from '../components/smc/SmcVerdictCard'
import SmcScoreBars from '../components/smc/SmcScoreBars'
import SmcTradePlanCard from '../components/smc/SmcTradePlanCard'
import SmcOrderFlowPanel from '../components/smc/SmcOrderFlowPanel'
import SmcBacktestPanel from '../components/smc/SmcBacktestPanel'
import SmcScannerPanel from '../components/smc/SmcScannerPanel'
import SmcFreezeBar from '../components/smc/SmcFreezeBar'

const INTERVALS = ['5m', '15m', '30m', '1h', '4h', '1d']

type LayerKey = 'zones' | 'structure' | 'liquidity' | 'sweeps' | 'inducements' | 'equilibrium' | 'plan' | 'swings' | 'volume' | 'fib' | 'autotrend'
const LAYER_DEFS: { key: LayerKey; label: string }[] = [
  { key: 'zones', label: 'Zones' }, { key: 'structure', label: 'BOS/CHoCH' },
  { key: 'plan', label: 'Trade plan' }, { key: 'liquidity', label: 'Liquidity' },
  { key: 'equilibrium', label: 'Equilibrium' }, { key: 'volume', label: 'Volume' },
  { key: 'sweeps', label: 'Sweeps' },
  { key: 'swings', label: 'Swings' }, { key: 'inducements', label: 'Inducements' },
  { key: 'fib', label: 'Fibonacci' },
  { key: 'autotrend', label: 'Auto Trend' },
]
const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  zones: true, structure: true, plan: true, liquidity: true,
  equilibrium: true, sweeps: true, swings: false, inducements: false,
  volume: true, fib: false, autotrend: false,
}

const toSec = (iso: string) => Math.floor(Date.parse(iso) / 1000) as UTCTimestamp

// How often the chart's last (still-forming) candle is refreshed from Binance.
const LIVE_POLL_MS = 5000

// Zone colouring: POIs (the double-confluence signature zone) in gold, everything
// else by directional bias.
function zoneColors(label: string, bias?: string): [string, string] {
  if (label === 'POI') return ['rgba(212,175,55,0.12)', 'rgba(212,175,55,0.65)']
  if (bias === 'BULLISH') return ['rgba(34,197,94,0.10)', 'rgba(34,197,94,0.5)']
  if (bias === 'BEARISH') return ['rgba(239,68,68,0.10)', 'rgba(239,68,68,0.5)']
  return ['rgba(148,163,184,0.08)', 'rgba(148,163,184,0.4)']
}

const LEVEL_STYLE: Record<string, { color: string; dashed?: boolean }> = {
  Entry: { color: '#e2e8f0' }, Stop: { color: '#f6465d' },
  TP1: { color: '#2ebd85' }, TP2: { color: '#2ebd85' },
  EQH: { color: '#5c6475', dashed: true }, EQL: { color: '#5c6475', dashed: true },
}

const HTF_CHIP: Record<string, string> = { up: 'chip-up', down: 'chip-down' }

export default function SmcAnalyzer() {
  const [symbol, setSymbol] = usePersistedState('smc.symbol', 'BTCUSDT')
  const [interval, setInterval] = usePersistedState('smc.interval', '1h')
  const [analysis, setAnalysis] = useState<SmcAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [layers, setLayers] = usePersistedState<Record<LayerKey, boolean>>('smc.layers', DEFAULT_LAYERS)
  // Persisted layer maps from before a key existed won't have it — fall back
  // to the default so a newly added layer (e.g. volume) still shows/toggles.
  const layerOn = (k: LayerKey) => layers[k] ?? DEFAULT_LAYERS[k]
  const toggle = (k: LayerKey) => setLayers(l => ({ ...l, [k]: !(l[k] ?? DEFAULT_LAYERS[k]) }))
  const [indicatorConfig, setIndicatorConfig] = usePersistedState<IndicatorConfig>('smc.indicators', {
    emaPeriods: [], fibLevels: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1], fibLookback: 200,
  })

  // Drawn trend lines, persisted per symbol+interval (a map keyed by both).
  type TL = { p1: { time: number; price: number }; p2: { time: number; price: number } }
  const [allTrendlines, setAllTrendlines] = usePersistedState<Record<string, TL[]>>('smc.trendlines', {})
  const tlKey = `${symbol}_${interval}`
  const trendlines = allTrendlines[tlKey] ?? []
  const [drawMode, setDrawMode] = useState(false)
  const [pendingSet, setPendingSet] = useState(false)
  const [isFull, setIsFull] = useState(false)

  const chartCardRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<HTMLDivElement>(null)
  const chartApiRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const rectRef = useRef<RectanglesPrimitive | null>(null)
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])
  const fibLinesRef = useRef<IPriceLine[]>([])
  const trendSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const autoTrendSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const pendingPointRef = useRef<{ time: number; price: number } | null>(null)
  const drawModeRef = useRef(false)
  const addTrendlineRef = useRef<(tl: TL) => void>(() => {})

  drawModeRef.current = drawMode
  addTrendlineRef.current = (tl: TL) =>
    setAllTrendlines(m => ({ ...m, [tlKey]: [...(m[tlKey] ?? []), tl] }))
  const clearTrendlines = () => setAllTrendlines(m => ({ ...m, [tlKey]: [] }))

  // quiet=true refreshes the analysis without the loading state — used by the
  // live poll when a candle closes, so the page doesn't flash every refresh.
  const run = useCallback(async (quiet?: unknown) => {
    const isQuiet = quiet === true
    if (!isQuiet) setLoading(true)
    setError(null)
    try {
      const { data } = await getSmcAnalysis(symbol, interval, 500)
      setAnalysis(data)
    } catch (e: any) {
      if (!isQuiet) {
        setError(e?.response?.data?.detail ?? 'Analysis failed. Is the backend running?')
        setAnalysis(null)
      }
    } finally {
      if (!isQuiet) setLoading(false)
    }
  }, [symbol, interval])

  useEffect(() => { run() }, [run])

  // Live updates: the analysis itself is frozen by design (see SmcFreezeBar),
  // but the chart's last candle must track the real market — and once a new
  // candle closes, the frozen analysis is re-run quietly so zones/structure/
  // trade plans reflect real data instead of going stale forever.
  const runRef = useRef(run); runRef.current = run
  const chartSymbolRef = useRef<string | null>(null)
  const chartIntervalRef = useRef<string | null>(null)
  const lastCandleTimeRef = useRef<number | null>(null)
  const refreshingRef = useRef(false)

  // ── Scroll-back pagination state ──
  // The analysis ships only its own 500-candle window; panning left past it
  // showed a blank chart. Older candles are lazy-loaded from /market/history
  // as the user scrolls (same mechanism as the Terminal/Analysis charts).
  type Bar = { time: UTCTimestamp; open: number; high: number; low: number; close: number; volume: number }
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const allBarsRef = useRef<Bar[]>([])
  const hasMoreRef = useRef(true)
  const loadingMoreRef = useRef(false)
  const [loadingOlder, setLoadingOlder] = useState(false)

  const volBar = (b: Bar) => ({
    time: b.time, value: b.volume,
    color: b.close >= b.open ? '#2ebd8566' : '#f6465d66',
  })

  async function loadOlder() {
    const chart = chartApiRef.current, series = candleSeriesRef.current
    const sym = chartSymbolRef.current, itv = chartIntervalRef.current
    const bars = allBarsRef.current
    if (!chart || !series || !sym || !itv || bars.length === 0) return
    if (loadingMoreRef.current || !hasMoreRef.current) return
    loadingMoreRef.current = true
    setLoadingOlder(true)
    try {
      const endTime = (bars[0].time as number) * 1000 - 1
      const res = await getMarket(sym, itv, 500, endTime)
      const older = res.data.candles
      if (!Array.isArray(older) || older.length === 0) { hasMoreRef.current = false; return }
      const firstTime = bars[0].time as number
      const newBars: Bar[] = older
        .map(c => ({
          time: toSec(c.timestamp), open: c.open, high: c.high, low: c.low, close: c.close,
          volume: c.volume,
        }))
        .filter(b => Number.isFinite(b.time as number) && (b.time as number) < firstTime)
      if (newBars.length === 0) { hasMoreRef.current = false; return }
      allBarsRef.current = [...newBars, ...bars]
      const prev = chart.timeScale().getVisibleLogicalRange()
      series.setData(allBarsRef.current)
      volumeSeriesRef.current?.setData(allBarsRef.current.map(volBar))
      // setData resets the viewport — shift the visible range by the number
      // of prepended bars so the user's scroll position doesn't jump.
      if (prev) {
        chart.timeScale().setVisibleLogicalRange({
          from: prev.from + newBars.length, to: prev.to + newBars.length,
        })
      }
      if (older.length < 500) hasMoreRef.current = false
    } catch { /* retried on next scroll */ } finally {
      loadingMoreRef.current = false
      setLoadingOlder(false)
    }
  }
  const loadOlderRef = useRef(loadOlder); loadOlderRef.current = loadOlder
  useEffect(() => {
    const id = window.setInterval(async () => {
      const series = candleSeriesRef.current
      const sym = chartSymbolRef.current, itv = chartIntervalRef.current
      const last = lastCandleTimeRef.current
      if (!series || !sym || !itv || last === null) return
      try {
        const { data: live } = await getLiveMarket(sym, itv)
        const t = toSec(live.timestamp)
        // A NaN-time or stale bar must never reach update() — one bad bar
        // permanently breaks the series' rendering ("Value is null" on every
        // repaint until remount).
        if (!Number.isFinite(t) || !Number.isFinite(live.close) || t < last) return
        const bar = { time: t, open: live.open, high: live.high, low: live.low, close: live.close, volume: live.volume }
        series.update(bar)
        volumeSeriesRef.current?.update(volBar(bar))
        const bars = allBarsRef.current
        if (bars.length > 0) {
          if ((bars[bars.length - 1].time as number) === (t as number)) bars[bars.length - 1] = bar
          else if ((t as number) > (bars[bars.length - 1].time as number)) bars.push(bar)
        }
        if (t > last && !refreshingRef.current) {
          refreshingRef.current = true
          try { await runRef.current(true) } finally { refreshingRef.current = false }
        }
      } catch { /* transient network hiccup — next tick retries */ }
    }, LIVE_POLL_MS)
    return () => window.clearInterval(id)
  }, [])

  // Create the chart once.
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#11141b' }, textColor: '#5c6475', attributionLogo: false },
      grid: { vertLines: { color: '#1a1f2b' }, horzLines: { color: '#1a1f2b' } },
      timeScale: { borderColor: '#232837' },
      rightPriceScale: { borderColor: '#232837' },
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        axisDoubleClickReset: { time: true, price: true },
        mouseWheel: true, pinch: true,
      },
      crosshair: {
        vertLine: { color: '#3d465c', labelBackgroundColor: '#303748' },
        horzLine: { color: '#3d465c', labelBackgroundColor: '#303748' },
      },
      width: chartRef.current.clientWidth, height: 440,
    })
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#2ebd85', downColor: '#f6465d',
      borderUpColor: '#2ebd85', borderDownColor: '#f6465d',
      wickUpColor: '#2ebd85', wickDownColor: '#f6465d',
    })
    chartApiRef.current = chart
    candleSeriesRef.current = series
    markersRef.current = createSeriesMarkers(series, [])
    const rect = new RectanglesPrimitive()
    series.attachPrimitive(rect)
    rectRef.current = rect

    // Volume histogram pinned to the bottom ~18% of the pane, on its own
    // hidden price scale so it never distorts the candle scale.
    const vol = chart.addSeries(HistogramSeries, {
      priceScaleId: 'vol',
      priceFormat: { type: 'volume' },
      lastValueVisible: false,
      priceLineVisible: false,
    })
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      visible: false,
    })
    volumeSeriesRef.current = vol

    // Lazy-load older candles when the user pans near the left edge.
    const onRange = (range: LogicalRange | null) => {
      if (range && range.from <= 20) loadOlderRef.current()
    }
    chart.timeScale().subscribeVisibleLogicalRangeChange(onRange)

    // Trend-line drawing: two clicks (bar-time + price) define a segment.
    // Uses raw DOM pointer events on the chart container, NOT the library's
    // subscribeClick: lightweight-charts swallows a second click that lands
    // within its double-click window at a different spot (verified live —
    // neither a click nor a dblclick event fires), which made fast two-click
    // drawing silently impossible. A <=5px move threshold keeps chart
    // panning from registering as a draw click.
    const container = chartRef.current
    let downPos: { x: number; y: number } | null = null
    const onPointerDown = (e: PointerEvent) => { downPos = { x: e.clientX, y: e.clientY } }
    const onPointerUp = (e: PointerEvent) => {
      const start = downPos
      downPos = null
      if (!drawModeRef.current || !start) return
      if (Math.hypot(e.clientX - start.x, e.clientY - start.y) > 5) return  // drag, not click
      const rect = container.getBoundingClientRect()
      const t = chart.timeScale().coordinateToTime(e.clientX - rect.left)
      const price = series.coordinateToPrice(e.clientY - rect.top)
      if (t === null || price === null) return
      const pt = { time: t as number, price: price as number }
      if (!pendingPointRef.current) {
        pendingPointRef.current = pt
        setPendingSet(true)   // visible "point 1 placed" feedback
        return
      }
      if (pt.time === pendingPointRef.current.time) return  // zero-length line
      addTrendlineRef.current({ p1: pendingPointRef.current, p2: pt })
      pendingPointRef.current = null
      setPendingSet(false)
    }
    container.addEventListener('pointerdown', onPointerDown)
    container.addEventListener('pointerup', onPointerUp)

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
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onRange)
      container.removeEventListener('pointerdown', onPointerDown)
      container.removeEventListener('pointerup', onPointerUp)
      chart.remove()
    }
  }, [])

  // Draw the analysis whenever it (or the layer toggles) change.
  useEffect(() => {
    const chart = chartApiRef.current, series = candleSeriesRef.current
    if (!chart || !series || !analysis) return
    const candles = analysis.candles
    const at = (idx: number) => toSec(candles[Math.max(0, Math.min(candles.length - 1, idx))].time)

    // Merge the analysis window with any older candles already lazy-loaded
    // by scrolling — a quiet re-analyze must not wipe scrolled-back history.
    const analysisBars = candles.map(c => ({
      time: toSec(c.time), open: c.open, high: c.high, low: c.low, close: c.close,
      volume: c.volume,
    }))
    const sameChart = chartSymbolRef.current === analysis.symbol
      && chartIntervalRef.current === analysis.interval
    const firstAnalysisTime = analysisBars[0]?.time as number
    const olderPrefix = sameChart
      ? allBarsRef.current.filter(b => (b.time as number) < firstAnalysisTime)
      : []
    if (!sameChart) hasMoreRef.current = true
    allBarsRef.current = [...olderPrefix, ...analysisBars]

    series.setData(allBarsRef.current)
    volumeSeriesRef.current?.setData(allBarsRef.current.map(volBar))
    volumeSeriesRef.current?.applyOptions({ visible: layerOn('volume') })

    const lastTime = toSec(candles[candles.length - 1].time)
    const backstopTime = toSec(candles[Math.max(0, candles.length - 40)].time)

    // Tell the live poll what's actually on the chart now.
    chartSymbolRef.current = analysis.symbol
    chartIntervalRef.current = analysis.interval
    lastCandleTimeRef.current = lastTime

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
          price: p.price, color: '#5c6475', lineWidth: 1, lineStyle: 2,
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

    // ── Auto trend line — classical rules: a straight line through swing
    // pivots (rising lows = up line, falling highs = down line), at least 2
    // touches, and price never closing through it. Best candidate = most
    // pivot touches, then most recent anchor. Tolerance is ATR-scaled so
    // wicks don't disqualify an otherwise perfect line.
    autoTrendSeriesRef.current.forEach(sr => { try { chart.removeSeries(sr) } catch { /* gone */ } })
    autoTrendSeriesRef.current = []
    if (layerOn('autotrend')) {
      const tol = (analysis.atr || 0) * 0.25
      const barsForFit = candles.map(c => ({ high: c.high, low: c.low }))
      const lowPivots = analysis.swings.filter(sw => !sw.is_high).map(sw => ({ index: sw.index, price: sw.price }))
      const highPivots = analysis.swings.filter(sw => sw.is_high).map(sw => ({ index: sw.index, price: sw.price }))
      const drawFit = (fit: ReturnType<typeof bestPivotTrendline>, color: string) => {
        if (!fit) return
        const sr = chart.addSeries(LineSeries, {
          color, lineWidth: 2, lastValueVisible: false, priceLineVisible: false,
        })
        // Two points only — a perfectly straight line, extended from the
        // first anchor all the way to the latest candle.
        sr.setData([
          { time: toSec(candles[fit.i1].time), value: fit.price1 },
          { time: toSec(candles[candles.length - 1].time), value: fit.endValue },
        ])
        autoTrendSeriesRef.current.push(sr)
      }
      drawFit(bestPivotTrendline(barsForFit, lowPivots, 'support', tol), '#2ebd85')
      drawFit(bestPivotTrendline(barsForFit, highPivots, 'resistance', tol), '#f6465d')
    }

    // ── Fibonacci retracement: most recent swing high → most recent swing low ──
    fibLinesRef.current.forEach(l => series.removePriceLine(l))
    fibLinesRef.current = []
    if (layerOn('fib')) {
      const highs = analysis.swings.filter(s => s.is_high)
      const lows = analysis.swings.filter(s => !s.is_high)
      const hi = highs[highs.length - 1]?.price
      const lo = lows[lows.length - 1]?.price
      if (hi !== undefined && lo !== undefined) {
        fibLinesRef.current = fibLevels(hi, lo, indicatorConfig.fibLevels).map(({ level, price }) =>
          series.createPriceLine({
            price, color: '#d4af37', lineWidth: 1, lineStyle: 2,
            axisLabelVisible: true, title: `Fib ${level}`,
          }))
      }
    }

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
          color: bull ? '#2ebd85' : '#f6465d', shape: 'circle', text: s.label })
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

    // Reset the viewport only when the chart actually changed coin/timeframe.
    // Quiet per-candle re-analyses and layer toggles must NOT yank the user's
    // scroll/zoom (fitContent over lazy-loaded history would zoom out to
    // thousands of bars).
    if (!sameChart) {
      chart.timeScale().fitContent()
      series.priceScale().applyOptions({ autoScale: true })
    }
  }, [analysis, layers, indicatorConfig])

  // Redraw user-drawn trend lines whenever they change (or the symbol/tf does).
  useEffect(() => {
    const chart = chartApiRef.current
    if (!chart) return
    trendSeriesRef.current.forEach(s => { try { chart.removeSeries(s) } catch { /* gone */ } })
    trendSeriesRef.current = trendlines.map(tl => {
      const s = chart.addSeries(LineSeries, { color: '#f5a623', lineWidth: 2, lastValueVisible: false, priceLineVisible: false })
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

  const pill = (active: boolean) =>
    `text-[11px] px-2 py-1 rounded-md border cursor-pointer transition-colors ${
      active ? 'bg-accent-soft text-accent border-accent/30'
        : 'bg-raised border-line text-fg-faint hover:text-fg-soft'}`

  return (
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* Toolbar (no hero — the nav rail says where we are) */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-baseline gap-2">
          <h2 className="panel-title">SMC Analyzer</h2>
          <span className="text-[11px] text-fg-faint">structure, zones & a rules-based trade plan</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-44"><SymbolSearchInput value={symbol} onCommit={setSymbol} /></div>
          <select value={interval} onChange={e => setInterval(e.target.value)}
            className="input w-20 text-xs">
            {INTERVALS.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
          <button onClick={run} disabled={loading} className="btn btn-primary">
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
      </div>

      {error && <div className="card card-pad border-down/40 text-down text-sm">{error}</div>}

      {/* Hero: the one thing a user needs — is there a signal, and which way? */}
      {analysis && (
        <SignalBanner analysis={analysis} />
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-3 items-start">
        <div className="space-y-3">
          <div ref={chartCardRef} className={`card p-3 ${isFull ? 'flex flex-col justify-center' : ''}`}>
            {analysis && !isFull && <SmcFreezeBar analysis={analysis} onReanalyze={run} />}
            {analysis && (
              <div className="flex items-center flex-wrap gap-1.5 px-1 pb-2">
                {analysis.htf?.available && (
                  <span className={`chip mr-1 ${HTF_CHIP[analysis.htf.trend] ?? 'chip-muted'}`}>
                    HTF {analysis.htf.trend}
                  </span>
                )}
                {LAYER_DEFS.map(l => (
                  <button key={l.key} onClick={() => toggle(l.key)} className={pill(layerOn(l.key))}>
                    {l.label}
                  </button>
                ))}
                <IndicatorSettings value={indicatorConfig} onChange={setIndicatorConfig} />
                {loadingOlder && <span className="text-[10px] text-accent ml-1">loading history…</span>}
                <div className="ml-auto flex items-center gap-1.5">
                  <button onClick={() => { setDrawMode(d => !d); pendingPointRef.current = null; setPendingSet(false) }} className={pill(drawMode)}>
                    <span className="flex items-center gap-1"><Pencil size={10} aria-label="draw" /> Trend line</span>
                  </button>
                  {trendlines.length > 0 && (
                    <button onClick={clearTrendlines}
                      className="text-[11px] px-2 py-1 rounded-md border cursor-pointer bg-raised border-line text-fg-faint hover:text-down transition-colors">Clear</button>
                  )}
                  <button onClick={toggleFullscreen}
                    className="text-[11px] px-2 py-1 rounded-md border cursor-pointer bg-raised border-line text-fg-faint hover:text-fg transition-colors">
                    <span className="flex items-center gap-1">
                      {isFull ? <Minimize2 size={10} aria-label="exit fullscreen" /> : <Maximize2 size={10} aria-label="fullscreen" />}
                      {isFull ? 'Exit' : 'Fullscreen'}
                    </span>
                  </button>
                </div>
              </div>
            )}
            {drawMode && (
              <p className="text-[11px] text-accent/80 px-1 pb-1">{pendingSet ? 'Point 1 placed — click the second point to finish the line.' : 'Click two points on the chart to draw a trend line.'}</p>
            )}
            <div ref={chartRef} />
            {analysis && (
              <>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 pt-2 text-[11px] text-fg-faint">
                  <LegendSwatch color="#d4af37" label="POI" />
                  <LegendSwatch color="#2ebd85" label="Bullish OB / demand / FVG" />
                  <LegendSwatch color="#f6465d" label="Bearish OB / supply / FVG" />
                  <LegendSwatch color="#d4af37" label="BOS / CHoCH" round />
                  <span className="num ml-auto">
                    Frozen {new Date(analysis.frozen_at).toLocaleTimeString()} · ATR {analysis.atr.toFixed(2)}
                  </span>
                </div>
                <div className="num flex flex-wrap gap-x-3 gap-y-1 px-2 pt-1 text-[11px] text-fg-faint">
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
            {analysis && analysis.reasons.length > 0 && (
              <div className="card card-pad">
                <p className="panel-title mb-2">Why this read</p>
                <ul className="space-y-1">
                  {analysis.reasons.map((r, i) => (
                    <li key={i} className="text-[12.5px] text-fg-soft flex gap-2">
                      <span className="text-fg-faint">·</span>{r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis?.order_flow && <SmcOrderFlowPanel of={analysis.order_flow} />}
            {analysis?.verdict && <div className="lg:col-span-2"><SmcScoreBars v={analysis.verdict} /></div>}
          </div>
        </div>

        <div className="space-y-3">
          {analysis?.verdict && <SmcVerdictCard a={analysis} />}
          {analysis?.long_plan && <SmcTradePlanCard plan={analysis.long_plan} symbol={symbol} interval={interval} />}
          {analysis?.short_plan && <SmcTradePlanCard plan={analysis.short_plan} symbol={symbol} interval={interval} />}
          {analysis && (
            <p className="text-[11px] text-fg-faint leading-relaxed px-1">
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

function LegendSwatch({ color, label, round }: { color: string; label: string; round?: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block w-2 h-2 ${round ? 'rounded-full' : 'rounded-[2px]'}`}
        style={{ background: color }} aria-hidden />
      {label}
    </span>
  )
}

function SignalBanner({ analysis }: { analysis: SmcAnalysis }) {
  const primary = analysis.primary
  if (primary === 'neutral') {
    return (
      <div className="card px-4 py-3 flex items-center gap-3">
        <Circle size={16} className="text-fg-faint shrink-0" aria-label="no setup" />
        <div>
          <p className="text-sm font-medium text-fg-soft">No high-confidence setup right now
            <span className="chip chip-muted ml-2">NO TRADE</span></p>
          <p className="text-xs text-fg-faint">Neither side cleared the confluence checklist. Strong SMC signals are intentionally rare — wait for one.</p>
        </div>
      </div>
    )
  }
  const plan = primary === 'long' ? analysis.long_plan! : analysis.short_plan!
  const isLong = primary === 'long'
  // Static class strings — Tailwind v4 JIT can't see interpolated class names.
  const wrap = isLong ? 'bg-up-soft border-up/40' : 'bg-down-soft border-down/40'
  const text = isLong ? 'text-up' : 'text-down'
  const badge = isLong ? 'chip-up' : 'chip-down'
  return (
    <div className={`${wrap} border rounded-lg px-4 py-3`}>
      <div className="flex items-center flex-wrap gap-x-6 gap-y-2">
        <div className="flex items-center gap-2">
          <span className={`${text} text-xl font-bold uppercase`}>{primary} signal</span>
          <span className={`chip ${badge}`}>
            <span className="num">{plan.strength_score}/110</span> · {plan.strength}
          </span>
        </div>
        <div className="flex gap-5 text-sm">
          <span className="text-fg-soft">Entry <span className="num text-fg font-medium">{plan.entry.toPrecision(6)}</span></span>
          <span className="text-fg-soft">Stop <span className="num text-down font-medium">{plan.stop_loss.toPrecision(6)}</span></span>
          <span className="text-fg-soft">TP1 <span className="num text-up font-medium">{plan.take_profit_1.toPrecision(6)}</span></span>
          <span className="text-fg-soft">R:R <span className="num text-fg font-medium">{plan.risk_reward.toFixed(2)}:1</span></span>
        </div>
      </div>
    </div>
  )
}
