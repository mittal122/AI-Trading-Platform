import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  createChart, ColorType, CandlestickSeries, LineSeries, createSeriesMarkers,
} from 'lightweight-charts'
import type {
  IChartApi, ISeriesApi, IPriceLine, ISeriesMarkersPluginApi, LogicalRange, Time, UTCTimestamp,
} from 'lightweight-charts'
import {
  Check, Clock, X, Eye, EyeOff, Crosshair, Maximize2, Minimize2,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  getMarket, getLiveMarket, scanPatterns, explainPattern, scanAnalysisTools, explainAnalysisTools,
} from '../api/client'
import type {
  Candle, DetectedPattern, AIPatternExplanation, AnalysisToolResult, AIToolExplanation, ChartAnnotations,
} from '../api/client'
import IndicatorSettings from '../components/IndicatorSettings'
import type { IndicatorConfig } from '../components/IndicatorSettings'
import { computeEma, fibLevels } from '../lib/indicators'
import { parseUtcMs } from '../lib/time'
import { drawSignalLines, clearSignalLines } from '../lib/signalLines'
import PatternInfoPanel from '../components/PatternInfoPanel'
import SignalsSection from '../components/SignalsSection'
import SymbolSearchInput from '../components/SymbolSearchInput'
import ToolToggleBar from '../components/ToolToggleBar'
import { usePersistedState } from '../hooks/usePersistedState'
import { RectanglesPrimitive } from '../lib/rectanglePrimitive'
import type { RectangleSpec } from '../lib/rectanglePrimitive'

const INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']

const INITIAL_CANDLES = 500
const PAGE_CANDLES = 500
const LOAD_MORE_THRESHOLD_BARS = 20
// Every detector's own lookback config caps out here too (see pattern_config.py
// / analysis_config.py) — matches Binance/backend's own per-request ceiling,
// so this is the real, honest limit of "how much loaded history gets analyzed."
const MAX_SCAN_LIMIT = 1000
// Analysis tools (no auto-AI) rescan as more history loads, but debounced —
// don't fire a network call on every single scroll tick.
const TOOL_RESCAN_DEBOUNCE_MS = 1200
// Periodic pattern re-detection cadence — keeps detections current as new
// candles close, without hammering the backend (scan is algorithmic-only).
const AUTO_RESCAN_MS = 60_000
// Window to disambiguate a single click (hide/show) from a double click
// (select for detail) on a pattern row.
const PATTERN_CLICK_DELAY_MS = 220
// How often the chart's last (possibly still-forming) candle is refreshed.
// Only updates the visible bar via series.update() — does NOT re-trigger
// pattern/tool scans (those stay on their existing triggers) to avoid the
// same AI rate-limit problem re-scanning on a timer would cause.
const LIVE_POLL_MS = 5000

const DIR_DOT: Record<string, string> = {
  BULLISH: 'bg-up', BEARISH: 'bg-down', NEUTRAL: 'bg-fg-faint',
}

// Beginner-readable status wording — CONFIRMED means "the pattern triggered
// (price actually broke out afterwards)", DEVELOPING means "still open at
// the live edge", BROKEN means "failed or expired without triggering".
const STATUS_CHIP: Record<string, { label: string; cls: string; Icon: LucideIcon }> = {
  CONFIRMED:  { label: 'Confirmed', cls: 'chip-up', Icon: Check },
  DEVELOPING: { label: 'Forming',   cls: 'chip-warn', Icon: Clock },
  BROKEN:     { label: 'Failed',    cls: 'chip-muted', Icon: X },
}

// Distinct, non-market colors for user-added EMA lines (green/red are
// reserved for direction; indexes cycle if more periods than colors).
const EMA_COLORS = ['#f5a623', '#a78bfa', '#e8ecf4', '#c2703d', '#d4af37']

const TOOL_LINE_COLORS: Record<string, string> = {
  ema20: '#22c55e', ema50: '#3b82f6', sma50: '#f59e0b', sma200: '#ef4444',
  daily_vwap: '#818cf8', anchored_vwap: '#c084fc',
  trend_line: '#fbbf24', trend_resistance: '#ef4444', trend_support: '#22c55e',
}

const indicatorPill = (active: boolean) =>
  `text-[11px] px-2 py-1 rounded-md border cursor-pointer transition-colors ${
    active ? 'bg-accent-soft text-accent border-accent/30'
      : 'bg-raised border-line text-fg-faint hover:text-fg-soft'}`

function toBarTime(timestamp: string): UTCTimestamp {
  return Math.floor(parseUtcMs(timestamp) / 1000) as UTCTimestamp
}

function toBar(c: Candle) {
  return { time: toBarTime(c.timestamp), open: c.open, high: c.high, low: c.low, close: c.close }
}

export default function PatternAnalysis() {
  const [searchParams] = useSearchParams()
  const [symbolInput, setSymbolInput] = usePersistedState(
    'patterns.symbol', searchParams.get('symbol') ?? 'BTCUSDT',
  )
  const [symbol, setSymbol] = useState(searchParams.get('symbol')?.toUpperCase() ?? symbolInput)
  const [interval, setInterval] = usePersistedState(
    'patterns.interval', searchParams.get('interval') ?? '1h',
  )

  const [patterns, setPatterns] = useState<DetectedPattern[]>([])
  const [fvgCount, setFvgCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  // Display quality gate — defaults tuned for a clean chart: only
  // high-confidence patterns, and failed/expired (BROKEN) setups hidden.
  const [minConfidence, setMinConfidence] = usePersistedState('patterns.minConf', 70)
  const [showBroken, setShowBroken] = usePersistedState('patterns.showBroken', false)
  // Every detected pattern is drawn on the chart by default — the eye button
  // per row opts a specific one OUT (hides it), rather than an opt-in list,
  // so newly-found patterns from a rescan show up without extra clicks.
  const [hiddenPatternIds, setHiddenPatternIds] = useState<Set<string>>(new Set())
  // AI explanation is on-demand per selected pattern (not auto-generated for
  // every pattern in a scan — that's what made scans take 50-90s+). Cached
  // by pattern id so re-selecting an already-explained pattern is instant.
  const [patternAiCache, setPatternAiCache] = useState<Record<string, AIPatternExplanation>>({})
  const [patternAiLoading, setPatternAiLoading] = useState(false)

  const [enabledTools, setEnabledTools] = usePersistedState<string[]>('patterns.enabledTools', [])
  const [indicatorConfig, setIndicatorConfig] = usePersistedState<IndicatorConfig>('patterns.indicators', {
    emaPeriods: [20, 50, 200], fibLevels: [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1], fibLookback: 200,
  })
  const [showEma, setShowEma] = usePersistedState<boolean>('patterns.showEma', false)
  const [showFib, setShowFib] = usePersistedState<boolean>('patterns.showFib', false)
  const [toolResults, setToolResults] = useState<AnalysisToolResult[]>([])
  const [toolsLoading, setToolsLoading] = useState(false)

  const [aiExplanation, setAiExplanation] = useState<AIToolExplanation | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')

  const [loadedCount, setLoadedCount] = useState(0)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [historyExhausted, setHistoryExhausted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  // Secondary content (pattern list vs. tool results/AI confluence) is tabbed
  // rather than always-stacked — keeps the chart the dominant element and
  // avoids a long scroll past everything at once.
  const [sidebarTab, setSidebarTab] = useState<'patterns' | 'tools'>('patterns')
  // selectedId always tracks "which pattern is emphasized on chart / has its
  // AI explanation fetched" (auto-set to the top result on every scan). The
  // detail MODAL is a separate, explicit visibility flag — opened only by a
  // double-click, never automatically by a rescan re-picking selectedId.
  const [showDetailModal, setShowDetailModal] = useState(false)

  const chartRef = useRef<HTMLDivElement>(null)
  const chartApiRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const lineSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const priceLinesRef = useRef<IPriceLine[]>([])
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)
  const rectPrimitiveRef = useRef<RectanglesPrimitive | null>(null)
  // Indicator overlays (EMA lines + fib price lines) live in their OWN refs —
  // pattern redraws (lineSeriesRef/priceLinesRef) and indicator redraws must
  // never delete each other's chart objects.
  const emaSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const fibLinesRef = useRef<IPriceLine[]>([])
  // Entry/Stop/Target lines toggled by clicking the signal detail card below —
  // separate ref so pattern/indicator redraws never delete them (and vice versa).
  const signalLinesRef = useRef<IPriceLine[]>([])
  const [signalOnChart, setSignalOnChart] = useState(false)

  const allCandlesRef = useRef<Candle[]>([])
  const hasMoreRef = useRef(true)
  const loadingMoreRef = useRef(false)
  // In-memory page cache — re-scrolling over an already-visited range (back
  // and forth) reuses the cached page instead of re-hitting Binance.
  const pageCacheRef = useRef(new Map<string, Candle[]>())
  const toolRescanTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Disambiguates single vs. double click on a pattern row: a single click
  // is deferred behind this timer (toggles hide/show if nothing else
  // happens); a genuine double-click cancels the pending timer and selects
  // the pattern for the detail panel instead.
  const patternClickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const chartWrapperRef = useRef<HTMLDivElement>(null)
  // Guards against out-of-order responses: if the tool selection changes
  // again while a scan is in flight, a slower earlier request can resolve
  // after a faster later one and overwrite it with stale results (e.g. a
  // tool that was just disabled "reappearing"). Only the response matching
  // the latest-fired request is allowed to update state.
  const toolScanSeqRef = useRef(0)
  // The chart-setup effect below only runs once (mount) — its loadOlder()
  // closure would otherwise capture the symbol/interval from that first
  // render forever. Read the live values through these refs instead.
  const symbolRef = useRef(symbol)
  const intervalRef = useRef(interval)
  useEffect(() => { symbolRef.current = symbol; intervalRef.current = interval }, [symbol, interval])

  const selectedRaw = patterns.find(p => p.id === selectedId) ?? null
  const selected = selectedRaw
    ? { ...selectedRaw, ai: patternAiCache[selectedRaw.id] ?? selectedRaw.ai }
    : null
  const enabledSet = new Set(enabledTools)
  const toolResultKeys = new Set(toolResults.map(t => t.tool_key))
  const toolsLastUpdated = toolResults.reduce<string | null>(
    (latest, t) => (!latest || t.last_updated > latest ? t.last_updated : latest), null,
  )
  const scanLimit = Math.min(Math.max(loadedCount, INITIAL_CANDLES), MAX_SCAN_LIMIT)
  // Quality gate for what's SHOWN (list + chart). The Min-conf slider only
  // applies to CANDLESTICK patterns — they're the noisy family (hundreds
  // per scan). Chart shapes (staircases, triangles, wedges, double tops,
  // H&S, cups…) and SMC structures are rare and explicitly wanted visible,
  // so they always show unless BROKEN is hidden.
  const filteredPatterns = patterns.filter(p =>
    (showBroken || p.status !== 'BROKEN')
    && ((p.category ?? 'candlestick') !== 'candlestick' || p.confidence >= minConfidence))
  // Chart shapes first (the reference patterns), then candlesticks, then
  // Smart Money — confidence-sorted within each group.
  const CATEGORY_RANK: Record<string, number> = { chart: 0, candlestick: 1, smc: 2 }
  const sortedPatterns = [...filteredPatterns].sort((a, b) => {
    const ra = CATEGORY_RANK[a.category ?? 'candlestick'] ?? 1
    const rb = CATEGORY_RANK[b.category ?? 'candlestick'] ?? 1
    return ra !== rb ? ra - rb : b.confidence - a.confidence
  })
  const topPatternId = sortedPatterns[0]?.id ?? null

  async function fetchCandlesCached(sym: string, itv: string, limit: number, endTime?: number): Promise<Candle[]> {
    const cacheKey = `${sym}|${itv}|${endTime ?? 'latest'}|${limit}`
    const cached = pageCacheRef.current.get(cacheKey)
    if (cached) return cached
    const res = await getMarket(sym, itv, limit, endTime)
    const candles = Array.isArray(res.data.candles) ? res.data.candles : []
    pageCacheRef.current.set(cacheKey, candles)
    return candles
  }

  // Recomputes EMA line series + fib retracement price lines from whatever
  // candles are currently loaded. Called on: initial load, older-history
  // prepend, a NEW live candle appending (not every tick), and config/toggle
  // changes. Mount-only effects call it through refreshIndicatorsRef so they
  // always see the latest config instead of the first render's closure.
  function refreshIndicators() {
    const chart = chartApiRef.current
    const candleSeries = candleSeriesRef.current
    if (!chart || !candleSeries) return
    emaSeriesRef.current.forEach(s => { try { chart.removeSeries(s) } catch { /* already gone */ } })
    emaSeriesRef.current = []
    fibLinesRef.current.forEach(l => { try { candleSeries.removePriceLine(l) } catch { /* already gone */ } })
    fibLinesRef.current = []
    const candles = allCandlesRef.current
    if (candles.length === 0) return
    if (showEma) {
      const closes = candles.map(c => c.close)
      indicatorConfig.emaPeriods.forEach((period, i) => {
        const ema = computeEma(closes, period)
        const data: { time: UTCTimestamp; value: number }[] = []
        for (let j = 0; j < ema.length; j++) {
          const v = ema[j]
          if (v !== null) data.push({ time: toBarTime(candles[j].timestamp), value: v })
        }
        const series = chart.addSeries(LineSeries, {
          color: EMA_COLORS[i % EMA_COLORS.length], lineWidth: 1,
          lastValueVisible: false, priceLineVisible: false,
        })
        series.setData(data)
        emaSeriesRef.current.push(series)
      })
    }
    if (showFib) {
      const window = candles.slice(-indicatorConfig.fibLookback)
      const hi = Math.max(...window.map(c => c.high))
      const lo = Math.min(...window.map(c => c.low))
      fibLinesRef.current = fibLevels(hi, lo, indicatorConfig.fibLevels).map(({ level, price }) =>
        candleSeries.createPriceLine({
          price, color: '#d4af37', lineWidth: 1, lineStyle: 2,
          axisLabelVisible: true, title: `Fib ${level}`,
        }))
    }
  }
  const refreshIndicatorsRef = useRef(refreshIndicators)
  refreshIndicatorsRef.current = refreshIndicators

  // Redraw indicators when their config or visibility toggles change.
  useEffect(() => { refreshIndicatorsRef.current() }, [indicatorConfig, showEma, showFib])

  async function runScan() {
    setLoading(true); setError(''); setAiExplanation(null)
    try {
      const res = await scanPatterns(symbol, interval, scanLimit)
      const fresh = res.data.patterns
      setPatterns(fresh)
      setFvgCount(res.data.fvgs.filter(f => !f.filled).length)
      // Keep the user's current selection across rescans (auto-rescan runs
      // every minute — yanking the selection away mid-read would be hostile);
      // only when it's gone does the top displayable pattern get selected.
      setSelectedId(prev => {
        if (prev && fresh.some(p => p.id === prev)) return prev
        const displayable = fresh.filter(p =>
          (showBroken || p.status !== 'BROKEN')
          && ((p.category ?? 'candlestick') !== 'candlestick' || p.confidence >= minConfidence))
        // Prefer a chart shape as the default selection when one exists.
        const charts = displayable.filter(p => p.category === 'chart')
        const pool = charts.length > 0 ? charts : displayable
        return pool.sort((a, b) => b.confidence - a.confidence)[0]?.id ?? null
      })
      if (res.data.error) setError(res.data.error)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Pattern scan failed')
      setPatterns([])
    } finally {
      setLoading(false)
    }
  }

  async function runToolScan() {
    const seq = ++toolScanSeqRef.current
    if (enabledTools.length === 0) {
      setToolResults([])
      return
    }
    setToolsLoading(true)
    try {
      const res = await scanAnalysisTools(symbol, interval, enabledTools, scanLimit)
      if (seq !== toolScanSeqRef.current) return // a newer toggle superseded this request
      setToolResults(res.data.tools)
    } catch {
      if (seq === toolScanSeqRef.current) setToolResults([])
    } finally {
      if (seq === toolScanSeqRef.current) setToolsLoading(false)
    }
  }

  async function runAiExplain() {
    if (enabledTools.length === 0) return
    setAiLoading(true); setAiError(''); setAiExplanation(null)
    try {
      const res = await explainAnalysisTools(symbol, interval, enabledTools, scanLimit)
      setAiExplanation(res.data.explanation)
    } catch (e: any) {
      setAiError(e?.response?.data?.detail ?? 'AI analysis failed')
    } finally {
      setAiLoading(false)
    }
  }

  function toggleTool(key: string) {
    setEnabledTools(
      enabledTools.includes(key) ? enabledTools.filter(k => k !== key) : [...enabledTools, key],
    )
    setAiExplanation(null)
  }

  function togglePatternVisibility(id: string) {
    setHiddenPatternIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  // Fetch AI explanation for whichever pattern is selected — on demand, one
  // pattern at a time, not auto-generated for the whole scan.
  useEffect(() => {
    if (!selectedRaw || patternAiCache[selectedRaw.id]) return
    let cancelled = false
    setPatternAiLoading(true)
    explainPattern(selectedRaw).then(res => {
      if (cancelled) return
      setPatternAiCache(prev => ({ ...prev, [selectedRaw.id]: res.data }))
    }).catch(() => {
      if (cancelled) return
      const failed: AIPatternExplanation = {
        why_detected: '', why_valid: '', market_psychology: '', buyer_seller_behavior: '',
        strength: '', alternative_scenario: '', recommendation_reason: '',
        error: 'AI explanation failed',
      }
      setPatternAiCache(prev => ({ ...prev, [selectedRaw.id]: failed }))
    }).finally(() => { if (!cancelled) setPatternAiLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  // Chart setup — once
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#11141b' }, textColor: '#5c6475', attributionLogo: false },
      grid: { vertLines: { color: '#1a1f2b' }, horzLines: { color: '#1a1f2b' } },
      timeScale: { borderColor: '#232837', fixRightEdge: true },
      rightPriceScale: { borderColor: '#232837' },
      crosshair: {
        vertLine: { color: '#3d465c', labelBackgroundColor: '#303748' },
        horzLine: { color: '#3d465c', labelBackgroundColor: '#303748' },
      },
      // Free zooming everywhere (wheel/pinch/drag on either axis). Getting
      // "lost" is always one action from recovery: double-click either axis
      // resets it (axisDoubleClickReset), the Reset view button restores
      // auto-fit, and every symbol/interval load forces the price scale
      // back to autoScale (see the load effect) — that last one is what
      // fixes switching BTC (~61k) → ETH (~1.5k) leaving the view stuck at
      // the old price range with the new candles off-screen.
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        axisDoubleClickReset: { time: true, price: true },
        mouseWheel: true,
        pinch: true,
      },
      width: chartRef.current.clientWidth,
      height: 420,
    })
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#2ebd85', downColor: '#f6465d',
      borderUpColor: '#2ebd85', borderDownColor: '#f6465d',
      wickUpColor: '#2ebd85', wickDownColor: '#f6465d',
      // Price can never be negative — clamp autoScale's padded range at 0
      // (matters for low-priced altcoins, where default padding can dip
      // below zero).
      autoscaleInfoProvider: (original: () => any) => {
        const res = original()
        if (res?.priceRange) {
          return { ...res, priceRange: { ...res.priceRange, minValue: Math.max(0, res.priceRange.minValue) } }
        }
        return res
      },
    })
    chartApiRef.current = chart
    candleSeriesRef.current = candleSeries
    markersPluginRef.current = createSeriesMarkers(candleSeries, [])
    const rectPrimitive = new RectanglesPrimitive()
    candleSeries.attachPrimitive(rectPrimitive)
    rectPrimitiveRef.current = rectPrimitive

    async function loadOlder() {
      if (loadingMoreRef.current || !hasMoreRef.current || allCandlesRef.current.length === 0) return
      loadingMoreRef.current = true
      setLoadingOlder(true)
      const fetchedFor = symbolRef.current
      const fetchedInterval = intervalRef.current
      try {
        const oldest = allCandlesRef.current[0]
        const endTime = parseUtcMs(oldest.timestamp) - 1
        const older = await fetchCandlesCached(fetchedFor, fetchedInterval, PAGE_CANDLES, endTime)

        // Symbol/interval changed while this fetch was in flight — the candle
        // array has already been reset for the new one, discard this result
        // rather than splicing stale-symbol candles into it.
        if (symbolRef.current !== fetchedFor || intervalRef.current !== fetchedInterval) return

        if (older.length === 0) {
          hasMoreRef.current = false
          setHistoryExhausted(true)
          return
        }

        const existingTimes = new Set(allCandlesRef.current.map(c => c.timestamp))
        const newOnes = older.filter(c => !existingTimes.has(c.timestamp))
        if (newOnes.length === 0) {
          hasMoreRef.current = false
          setHistoryExhausted(true)
          return
        }

        const addedCount = newOnes.length
        allCandlesRef.current = [...newOnes, ...allCandlesRef.current]
        setLoadedCount(allCandlesRef.current.length)

        const prevRange = chart.timeScale().getVisibleLogicalRange()
        candleSeries.setData(allCandlesRef.current.map(toBar))
        if (prevRange) {
          chart.timeScale().setVisibleLogicalRange({
            from: prevRange.from + addedCount, to: prevRange.to + addedCount,
          })
        }
        refreshIndicatorsRef.current()
        if (older.length < PAGE_CANDLES) hasMoreRef.current = false
      } catch {
        // leave hasMoreRef as-is — next scroll near the edge retries
      } finally {
        loadingMoreRef.current = false
        setLoadingOlder(false)
      }
    }

    function onVisibleRangeChange(range: LogicalRange | null) {
      if (range && range.from <= LOAD_MORE_THRESHOLD_BARS) loadOlder()
    }
    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRangeChange)

    // Fullscreen shows the same chart instance stretched to fill the
    // screen — resize on every window resize AND whenever fullscreen is
    // entered/exited (the wrapper's available height changes, but its own
    // width/height CSS doesn't fire a plain 'resize' event on some browsers).
    const applySize = () => {
      if (!chartRef.current) return
      const fs = document.fullscreenElement === chartWrapperRef.current
      chart.applyOptions({
        width: chartRef.current.clientWidth,
        height: fs ? window.innerHeight - 140 : 420,
      })
    }
    const onFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === chartWrapperRef.current)
      applySize()
    }
    window.addEventListener('resize', applySize)
    document.addEventListener('fullscreenchange', onFullscreenChange)
    return () => {
      window.removeEventListener('resize', applySize)
      document.removeEventListener('fullscreenchange', onFullscreenChange)
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRangeChange)
      chart.remove()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Initial candle load whenever symbol/interval changes — resets accumulated
  // history, the page cache doesn't need clearing (keyed by symbol+interval).
  useEffect(() => {
    if (!candleSeriesRef.current) return
    allCandlesRef.current = []
    hasMoreRef.current = true
    loadingMoreRef.current = false
    setHistoryExhausted(false)
    setLoadedCount(0)
    // Signal levels belong to the previous symbol/interval — drop them.
    clearSignalLines(candleSeriesRef.current, signalLinesRef.current)
    signalLinesRef.current = []
    setSignalOnChart(false)

    const requestedSymbol = symbol
    const requestedInterval = interval
    fetchCandlesCached(symbol, interval, INITIAL_CANDLES).then(candles => {
      // A newer symbol/interval change already reset state by the time this
      // resolves — discard rather than overwrite with stale-symbol data.
      if (symbolRef.current !== requestedSymbol || intervalRef.current !== requestedInterval) return
      if (candles.length > 0) {
        allCandlesRef.current = candles
        candleSeriesRef.current!.setData(candles.map(toBar))
        // A symbol/interval change loads a dataset with a completely
        // different time span AND price range — the chart instance is
        // reused across switches, so both scales must be reset:
        // - fitContent() re-fits the TIME axis (otherwise the view can
        //   point at empty space and look frozen/blank);
        // - autoScale:true re-fits the PRICE axis. Any manual price
        //   zoom/drag puts the scale into manual mode permanently, so
        //   switching BTC (~$61k) → ETH (~$1.5k) kept showing the $61k
        //   range with ETH's candles far off-screen until the user
        //   scrolled down and hunted for them.
        chartApiRef.current?.priceScale('right').applyOptions({ autoScale: true })
        chartApiRef.current?.timeScale().fitContent()
        refreshIndicatorsRef.current()
        setLoadedCount(candles.length)
        if (candles.length < INITIAL_CANDLES) hasMoreRef.current = false
      } else {
        hasMoreRef.current = false
      }
    }).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval])

  // Keep the chart's last (possibly still-forming) candle live — the
  // history/scroll effects above only ever fetch once per action, so
  // without this the chart was a static snapshot that never moved.
  useEffect(() => {
    const id = window.setInterval(async () => {
      if (!candleSeriesRef.current || allCandlesRef.current.length === 0) return
      try {
        const res = await getLiveMarket(symbolRef.current, intervalRef.current)
        const live = res.data
        const bar = toBar(live)
        // A single bar with a NaN time (bad/missing timestamp in a glitched
        // response) permanently poisons the series: update() accepts it, then
        // every repaint throws "Value is null" until the page dies. Validate
        // before it can enter the chart.
        if (!Number.isFinite(bar.time) || !Number.isFinite(bar.close)) return
        candleSeriesRef.current.update(bar)

        const candles = allCandlesRef.current
        const lastIdx = candles.length - 1
        if (candles[lastIdx].timestamp === live.timestamp) {
          candles[lastIdx] = live
        } else if (parseUtcMs(live.timestamp) > parseUtcMs(candles[lastIdx].timestamp)) {
          allCandlesRef.current = [...candles, live]
          setLoadedCount(allCandlesRef.current.length)
          // Only on a NEW candle appending — not every live tick.
          refreshIndicatorsRef.current()
        }
      } catch {
        // transient network hiccup — next tick retries, nothing to surface
      }
    }, LIVE_POLL_MS)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => { runScan() }, [symbol, interval])

  // Real-time: re-detect on a steady cadence so fresh candles get scanned
  // without a manual Rescan click. Algorithmic-only (no AI calls), so a
  // periodic scan is cheap (~2-4s server-side).
  useEffect(() => {
    const id = window.setInterval(() => { runScan() }, AUTO_RESCAN_MS)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval, scanLimit])

  // Pattern detail is a modal (double-click a row to open it) — Escape
  // closes it, matching standard dialog behavior.
  useEffect(() => {
    if (!showDetailModal) return
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setShowDetailModal(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [showDetailModal])

  // Analysis tools (pure algorithmic, no auto-AI) rescan as more history
  // loads — debounced so scrolling doesn't fire a burst of network calls.
  // Pattern detection deliberately does NOT auto-rescan on scroll (it
  // auto-generates AI per pattern — see pattern_scanner.py — so re-running
  // it on every scroll tick would repeat the NVIDIA rate-limit problem from
  // an earlier build). Click "Rescan" to pick up newly-loaded history there.
  useEffect(() => {
    if (toolRescanTimerRef.current) clearTimeout(toolRescanTimerRef.current)
    toolRescanTimerRef.current = setTimeout(() => { runToolScan() }, TOOL_RESCAN_DEBOUNCE_MS)
    return () => { if (toolRescanTimerRef.current) clearTimeout(toolRescanTimerRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval, enabledTools.join(','), scanLimit])

  // Draw annotations — every VISIBLE detected pattern (eye button controls
  // this per-row) + every enabled tool's, all merged onto the chart at once.
  // The currently-selected pattern (shown in the detail panel) is drawn with
  // heavier lines so it's easy to spot among the rest.
  useEffect(() => {
    const chart = chartApiRef.current
    const candleSeries = candleSeriesRef.current
    if (!chart || !candleSeries) return

    lineSeriesRef.current.forEach(s => chart.removeSeries(s))
    lineSeriesRef.current = []
    priceLinesRef.current.forEach(l => candleSeries.removePriceLine(l))
    priceLinesRef.current = []
    markersPluginRef.current?.setMarkers([])

    const allLabels: { time: string; price: number; text: string; bullish: boolean }[] = []
    const allRectangles: RectangleSpec[] = []
    const nowIso = new Date().toISOString()

    const visiblePatterns = filteredPatterns.filter(p => !hiddenPatternIds.has(p.id))

    // Priority rule: every visible pattern is DRAWN via its formation zone
    // (a filled, direction-colored box around the exact candles that form
    // it, with the pattern name at the box corner — see formation_zone()
    // backend-side). Text markers + the full price-line read-out
    // (breakout/invalidation/SL/targets) are selected-only, so many visible
    // patterns can't bury the chart under overlapping text again.
    visiblePatterns.forEach(p => {
      const a = p.annotations
      const bullish = p.direction !== 'BEARISH'
      const isSelected = p.id === selectedId
      drawTrendlines(chart, a, lineSeriesRef, tl =>
        tl.label === 'staircase_up' ? '#22c55e'
          : tl.label === 'staircase_down' ? '#ef4444'
          : tl.label === 'cup_curve' ? '#fbbf24'
          : tl.label.includes('resistance') ? '#ef4444'
          : tl.label.includes('support') ? '#22c55e'
          : '#818cf8')
      allRectangles.push(...zonesToRectangles(a, nowIso))

      if (!isSelected) return
      a.labels.forEach(l => allLabels.push({ ...l, bullish }))

      drawLevels(candleSeries, a, priceLinesRef, bullish, {
        emphasize: true, titlePrefix: p.pattern_name,
      })
      if (p.stop_loss) priceLinesRef.current.push(candleSeries.createPriceLine({
        price: p.stop_loss, color: '#ef4444', lineWidth: 2, lineStyle: 2,
        title: `${p.pattern_name} Stop Loss`,
      }))
      ;[p.target_1, p.target_2, p.target_3].forEach((t, i) => {
        if (t) priceLinesRef.current.push(candleSeries.createPriceLine({
          price: t, color: '#22c55e', lineWidth: 2, lineStyle: 2,
          title: `${p.pattern_name} Target ${i + 1}`,
        }))
      })
    })

    toolResults.forEach(tool => {
      if (tool.error) return
      const bullish = tool.bias !== 'BEARISH'
      drawTrendlines(chart, tool.annotations, lineSeriesRef, tl => TOOL_LINE_COLORS[tl.label] ?? '#94a3b8')
      drawLevels(candleSeries, tool.annotations, priceLinesRef, bullish)
      allRectangles.push(...zonesToRectangles(tool.annotations, nowIso))
      tool.annotations.labels.forEach(l => allLabels.push({ ...l, bullish }))
    })

    markersPluginRef.current?.setMarkers(allLabels.map(l => ({
      time: toBarTime(l.time), position: 'atPriceMiddle' as const, price: l.price,
      color: l.bullish ? '#22c55e' : '#ef4444', shape: 'circle' as const, text: l.text,
    })))
    rectPrimitiveRef.current?.setRectangles(allRectangles)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patterns, hiddenPatternIds, selectedId, toolResults, minConfidence, showBroken])

  function resetChartView() {
    // One-click recovery from any zoom/pan state: price axis back to
    // auto-fit, time axis back to the full loaded range (ends at the live
    // candle) — same reset the symbol/interval load performs.
    chartApiRef.current?.priceScale('right').applyOptions({ autoScale: true })
    chartApiRef.current?.timeScale().fitContent()
  }

  function toggleFullscreen() {
    if (!chartWrapperRef.current) return
    if (document.fullscreenElement) {
      document.exitFullscreen()
    } else {
      chartWrapperRef.current.requestFullscreen()
    }
  }

  function handlePatternRowClick(id: string) {
    if (patternClickTimerRef.current) return // a dblclick is already pending
    patternClickTimerRef.current = setTimeout(() => {
      togglePatternVisibility(id)
      patternClickTimerRef.current = null
    }, PATTERN_CLICK_DELAY_MS)
  }

  function handlePatternRowDoubleClick(id: string) {
    if (patternClickTimerRef.current) {
      clearTimeout(patternClickTimerRef.current)
      patternClickTimerRef.current = null
    }
    setSelectedId(id)
    setShowDetailModal(true)
  }

  return (
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* Toolbar — primary controls, kept slim so the chart below is the first big thing on screen */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="chip chip-warn">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" /> LIVE
        </span>
        <div className="flex items-center gap-2">
          <SymbolSearchInput value={symbolInput} onCommit={s => { setSymbolInput(s); setSymbol(s) }} className="w-40" />
          <select value={interval} onChange={e => setInterval(e.target.value)}
            className="input w-20 cursor-pointer">
            {INTERVALS.map(i => <option key={i}>{i}</option>)}
          </select>
          <button onClick={() => setShowEma(!showEma)} className={indicatorPill(showEma)}>EMA</button>
          <button onClick={() => setShowFib(!showFib)} className={indicatorPill(showFib)}>Fib</button>
          <IndicatorSettings showEma value={indicatorConfig} onChange={setIndicatorConfig} />
          <button onClick={runScan} disabled={loading} className="btn btn-primary">
            {loading ? 'Scanning…' : 'Rescan'}
          </button>
        </div>
      </div>

      {error && <div className="card card-pad border-down/40 text-down text-sm">{error}</div>}

      {/* Priority layout: the chart is the single dominant element (left,
          widest column); everything secondary (patterns, tools, AI) lives in
          a narrower sticky sidebar so it never outweighs the chart, and is
          tabbed rather than stacked so the page doesn't turn into a long
          scroll of equally-weighted sections. */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-3 items-start">
        <div className="space-y-3 min-w-0">
          <div ref={chartWrapperRef} className={`card card-pad ${isFullscreen ? 'flex flex-col bg-surface' : ''}`}>
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <p className="text-[11px] text-fg-faint"><span className="num">{symbol} · {interval}</span> — click a pattern once to hide it, double-click to view details</p>
              <div className="flex items-center gap-3">
                <p className="num text-[10.5px] text-fg-faint">
                  {loadedCount.toLocaleString()} candles loaded
                  {loadingOlder ? ' · loading older…' : historyExhausted ? ' · full history loaded' : ' · scroll left for more'}
                  {' · analyzing ' + scanLimit.toLocaleString()}
                  {' · '}{fvgCount} unfilled FVG{fvgCount === 1 ? '' : 's'}{toolsLoading ? ' · loading tools…' : ''}
                </p>
                <button onClick={resetChartView}
                  title="Snap back to the latest candles with an auto-fitted price axis (also: double-click either chart axis)"
                  aria-label="Reset chart view"
                  className="btn h-6 !px-2 text-[11px]">
                  <Crosshair size={12} /> Reset view
                </button>
                <button onClick={toggleFullscreen}
                  title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                  aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                  className="btn h-6 !px-2 text-[11px]">
                  {isFullscreen ? <><Minimize2 size={12} /> Exit Fullscreen</> : <><Maximize2 size={12} /> Fullscreen</>}
                </button>
              </div>
            </div>
            <div ref={chartRef} className={isFullscreen ? 'flex-1' : ''} />
          </div>

          <div className="card p-3">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <p className="text-[11px] text-fg-faint">Analysis tools — toggle individually, each with its own info panel</p>
              {enabledTools.length > 0 && (
                toolsLoading ? (
                  <span className="text-[11px] text-accent flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" /> Scanning…
                  </span>
                ) : toolsLastUpdated ? (
                  <span className="text-[11px] text-up flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-up" /> Live — updated <span className="num">{new Date(toolsLastUpdated).toLocaleTimeString()}</span>
                  </span>
                ) : null
              )}
            </div>
            {toolsLoading && (
              <div className="relative h-1 w-full bg-bg rounded-full overflow-hidden mb-2">
                <div className="tool-scan-bar absolute inset-y-0 w-1/3 bg-accent rounded-full" />
              </div>
            )}
            <ToolToggleBar enabled={enabledSet} onToggle={toggleTool} loading={toolsLoading} readyKeys={toolResultKeys} />
          </div>

          {/* Signals — merged in from the standalone Signals page, placed
              directly below Analysis Tools, sharing this page's symbol. */}
          <SignalsSection
            symbol={symbol}
            signalOnChart={signalOnChart}
            onSignalCardClick={(sig) => {
              const series = candleSeriesRef.current
              if (!series) return
              if (signalLinesRef.current.length) {
                clearSignalLines(series, signalLinesRef.current)
                signalLinesRef.current = []
                setSignalOnChart(false)
              } else {
                signalLinesRef.current = drawSignalLines(series, sig)
                setSignalOnChart(true)
              }
            }}
          />
        </div>

        <div className="space-y-3 xl:sticky xl:top-6">
          <div className="flex gap-1 card p-1">
            <button onClick={() => setSidebarTab('patterns')}
              className={`flex-1 text-xs font-semibold py-2 rounded-md transition-colors cursor-pointer ${
                sidebarTab === 'patterns' ? 'bg-accent-soft text-accent' : 'text-fg-faint hover:text-fg'
              }`}>
              Patterns (<span className="num">{filteredPatterns.length}</span>)
            </button>
            <button onClick={() => setSidebarTab('tools')}
              className={`flex-1 text-xs font-semibold py-2 rounded-md transition-colors cursor-pointer ${
                sidebarTab === 'tools' ? 'bg-accent-soft text-accent' : 'text-fg-faint hover:text-fg'
              }`}>
              Tools & AI{enabledTools.length > 0 ? ` (${enabledTools.length})` : ''}
            </button>
          </div>

          {sidebarTab === 'patterns' ? (
            <div className="card card-pad">
              <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                <h2 className="panel-title">
                  Detected Patterns
                  {hiddenPatternIds.size > 0 && <span className="text-fg-faint normal-case"> · {hiddenPatternIds.size} hidden</span>}
                </h2>
                <div className="flex items-center gap-3">
                  {hiddenPatternIds.size < filteredPatterns.length && filteredPatterns.length > 0 && (
                    <button onClick={() => setHiddenPatternIds(new Set(filteredPatterns.map(p => p.id)))}
                      className="text-xs text-accent hover:underline cursor-pointer">
                      Hide all
                    </button>
                  )}
                  {hiddenPatternIds.size > 0 && (
                    <button onClick={() => setHiddenPatternIds(new Set())}
                      className="text-xs text-accent hover:underline cursor-pointer">
                      Show all
                    </button>
                  )}
                </div>
              </div>

              {/* Quality filters — what counts as worth showing */}
              <div className="flex items-center gap-3 mb-3 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] text-fg-faint">Min conf.</span>
                  <input type="range" min={55} max={90} step={5} value={minConfidence}
                    onChange={e => setMinConfidence(Number(e.target.value))}
                    className="w-20 accent-accent cursor-pointer" />
                  <span className="num text-[11px] text-fg-soft w-7">{minConfidence}%</span>
                </div>
                <button onClick={() => setShowBroken(!showBroken)}
                  className={`chip cursor-pointer transition-colors ${showBroken ? 'chip-down' : 'chip-muted'}`}>
                  {showBroken ? 'Failed shown' : 'Failed hidden'}
                </button>
                <span className="num text-[11px] text-fg-faint">
                  {filteredPatterns.length} of {patterns.length}
                </span>
              </div>

              {filteredPatterns.length === 0 ? (
                <p className="text-fg-faint text-sm text-center py-6">
                  {loading ? 'Scanning…'
                    : patterns.length > 0 ? 'No patterns pass the current filters — lower Min conf. to see weaker matches.'
                    : 'No patterns detected on this timeframe right now.'}
                </p>
              ) : (
                <div className="space-y-1 max-h-[65vh] overflow-y-auto">
                  {sortedPatterns.map((p, i) => {
                    const hidden = hiddenPatternIds.has(p.id)
                    const cat = p.category ?? 'candlestick'
                    const prevCat = i > 0 ? (sortedPatterns[i - 1].category ?? 'candlestick') : null
                    const groupHeader = cat !== prevCat
                      ? { chart: 'Chart Patterns', candlestick: 'Candlestick Patterns', smc: 'Smart Money' }[cat]
                      : null
                    return (
                      <div key={p.id}>
                      {groupHeader && (
                        <p className="panel-title pt-2 pb-1 px-2">
                          {groupHeader}
                        </p>
                      )}
                      <div
                        onClick={() => handlePatternRowClick(p.id)}
                        onDoubleClick={() => handlePatternRowDoubleClick(p.id)}
                        title="Click to hide/show · double-click for details"
                        className={`row-hover w-full flex items-center gap-1 rounded-md text-sm transition-colors cursor-pointer select-none ${
                          p.id === selectedId ? 'bg-accent-soft border border-accent/40' : 'border border-transparent'
                        }`}>
                        <span className={`px-2 py-2 shrink-0 ${hidden ? 'text-fg-faint' : 'text-accent'}`}
                          aria-label={hidden ? 'Hidden on chart' : 'Visible on chart'}>
                          {hidden ? <EyeOff size={13} /> : <Eye size={13} />}
                        </span>
                        <span className={`flex-1 text-left py-1.5 pr-3 flex items-center justify-between gap-2 ${hidden ? 'opacity-40' : ''}`}>
                          <span className="flex items-center gap-2 min-w-0">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${DIR_DOT[p.direction]}`} />
                            <span className="text-[12.5px] text-fg truncate">{p.pattern_name}</span>
                            {p.id === topPatternId && (
                              <span className="chip chip-warn shrink-0 !h-4 !px-1.5 !text-[9px]">
                                TOP
                              </span>
                            )}
                          </span>
                          <span className="flex items-center gap-2 shrink-0">
                            {(() => {
                              const chip = STATUS_CHIP[p.status]
                              return (
                                <span className={`chip !h-4 !px-1.5 !text-[9px] ${chip?.cls ?? 'chip-muted'}`}>
                                  {chip && <chip.Icon size={9} />}
                                  {chip?.label ?? p.status}
                                </span>
                              )
                            })()}
                            <span className="num text-[11px] text-fg-faint">{p.confidence.toFixed(0)}%</span>
                          </span>
                        </span>
                      </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {enabledTools.length === 0 ? (
                <div className="card p-6 text-center text-fg-faint text-sm">
                  Toggle an analysis tool below the chart to see its results here.
                </div>
              ) : (
                <div className="card card-pad space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h2 className="panel-title">Tool Results</h2>
                    <button onClick={runAiExplain} disabled={aiLoading}
                      className="btn btn-primary h-7 text-xs">
                      {aiLoading ? 'Analyzing…' : 'AI Confluence'}
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {toolResults.map(t => (
                      <div key={t.tool_key} className="bg-bg border border-line rounded-md p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[12.5px] font-medium text-fg">{t.tool_name}</span>
                          <span className="text-[11px] font-semibold text-fg-soft flex items-center gap-1">
                            <span className={`w-1.5 h-1.5 rounded-full ${DIR_DOT[t.bias]}`} />
                            {t.bias}
                          </span>
                        </div>
                        <p className="text-[11px] text-fg-faint">{t.error ? `Error: ${t.error}` : t.summary}</p>
                      </div>
                    ))}
                  </div>

                  {aiError && <p className="text-xs text-down">{aiError}</p>}
                  {aiExplanation && !aiExplanation.error && (
                    <div className="border-t border-line pt-3 space-y-2">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-sm font-semibold text-accent">{aiExplanation.market_bias ?? 'N/A'}</span>
                        {aiExplanation.confidence_score !== undefined && (
                          <span className="text-[11px] text-fg-faint">Confidence: <span className="num">{aiExplanation.confidence_score.toFixed(0)}%</span></span>
                        )}
                        {aiExplanation.probability_of_success !== undefined && (
                          <span className="text-[11px] text-fg-faint">Probability: <span className="num">{aiExplanation.probability_of_success?.toFixed(0)}%</span></span>
                        )}
                      </div>
                      <p className="text-xs text-fg-soft">{aiExplanation.reasoning}</p>
                      <p className="text-xs text-fg-soft"><span className="text-fg-faint font-medium">Confluence: </span>{aiExplanation.confluence_notes}</p>
                      <p className="text-xs text-fg-soft"><span className="text-fg-faint font-medium">Risk: </span>{aiExplanation.risk_analysis}</p>
                      <div className="flex flex-col gap-1 text-xs text-fg-soft">
                        {aiExplanation.entry_suggestion && <span className="num">Entry: ${aiExplanation.entry_suggestion.toFixed(2)}</span>}
                        {aiExplanation.stop_loss && <span className="num text-down">SL: ${aiExplanation.stop_loss.toFixed(2)}</span>}
                        {aiExplanation.take_profit && <span className="num text-up">TP: ${aiExplanation.take_profit.toFixed(2)}</span>}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Pattern detail — a modal (opened by double-click) rather than a
          permanently-reserved column, so the chart stays the widest, most
          prominent element regardless of whether anything is selected. */}
      {showDetailModal && selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => setShowDetailModal(false)}
        >
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-end mb-2">
              <button onClick={() => setShowDetailModal(false)} aria-label="Close pattern details"
                className="btn h-6 !px-2 text-[11px] bg-surface border-line">
                <X size={12} /> Close
              </button>
            </div>
            <PatternInfoPanel pattern={selected} aiLoading={patternAiLoading && !patternAiCache[selected.id]} />
          </div>
        </div>
      )}
    </div>
  )
}

function drawTrendlines(
  chart: IChartApi,
  a: ChartAnnotations,
  ref: React.MutableRefObject<ISeriesApi<'Line'>[]>,
  colorFor: (tl: ChartAnnotations['trendlines'][number]) => string,
) {
  a.trendlines.forEach(tl => {
    const series = chart.addSeries(LineSeries, {
      color: colorFor(tl), lineWidth: 2, lastValueVisible: false, priceLineVisible: false,
    })
    series.setData(tl.points.map(p => ({ time: toBarTime(p.time), value: p.price })))
    ref.current.push(series)
  })
}

// Support/Resistance strength -> color: light (weak, few touches) to dark
// (strong, many touches) so the strongest levels stand out at a glance.
const SR_MIN_TOUCHES_SHADE = 2   // lightest shade
const SR_MAX_TOUCHES_SHADE = 6   // darkest shade, capped here (6+ touches all max-dark)

function srLevelColor(isSupport: boolean, strength: number): string {
  const hue = isSupport ? 142 : 0 // green / red
  const clamped = Math.min(Math.max(strength, SR_MIN_TOUCHES_SHADE), SR_MAX_TOUCHES_SHADE)
  const t = (clamped - SR_MIN_TOUCHES_SHADE) / (SR_MAX_TOUCHES_SHADE - SR_MIN_TOUCHES_SHADE)
  const lightness = 68 - t * 38 // 68% (light, weak) down to 30% (dark, strong)
  return `hsl(${hue}, 72%, ${lightness}%)`
}

function drawLevels(
  candleSeries: ISeriesApi<'Candlestick'>,
  a: ChartAnnotations,
  ref: React.MutableRefObject<IPriceLine[]>,
  bullish: boolean,
  opts: { emphasize?: boolean; titlePrefix?: string } = {},
) {
  const prefix = opts.titlePrefix ? `${opts.titlePrefix} ` : ''
  a.levels.forEach(lv => {
    const isBreakout = lv.label === 'breakout_level'
    const isSupport = lv.label.startsWith('support')
    const isResistance = lv.label.startsWith('resistance')
    const isSR = (isSupport || isResistance) && lv.strength !== undefined

    const color = isSR
      ? srLevelColor(isSupport, lv.strength!)
      : isBreakout ? (bullish ? '#22c55e' : '#ef4444') : '#f59e0b'

    const width: 1 | 2 | 3 = isBreakout ? (opts.emphasize ? 3 : 2) : (opts.emphasize ? 2 : 1)
    ref.current.push(candleSeries.createPriceLine({
      price: lv.price,
      color,
      lineWidth: width,
      lineStyle: isBreakout ? 0 : 2,
      title: `${prefix}${lv.label.replace(/_/g, ' ')}`,
    }))
  })
}

function zonesToRectangles(a: ChartAnnotations, lastTime: string): RectangleSpec[] {
  return a.zones.map(z => {
    const isBearish = z.bias === 'BEARISH'
    const isBullish = z.bias === 'BULLISH'
    const border = isBearish ? '#ef4444' : isBullish ? '#22c55e' : '#818cf8'
    const fill = isBearish ? 'rgba(239,68,68,0.15)' : isBullish ? 'rgba(34,197,94,0.15)' : 'rgba(129,140,248,0.15)'
    return {
      time1: toBarTime(z.start_time),
      time2: toBarTime(z.end_time || lastTime),
      price1: z.top,
      price2: z.bottom,
      fillColor: fill,
      borderColor: border,
      label: z.label.replace(/_/g, ' '),
    }
  })
}
