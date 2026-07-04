import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  createChart, ColorType, CandlestickSeries, LineSeries, createSeriesMarkers,
} from 'lightweight-charts'
import type {
  IChartApi, ISeriesApi, IPriceLine, ISeriesMarkersPluginApi, LogicalRange, Time, UTCTimestamp,
} from 'lightweight-charts'
import {
  getMarket, getLiveMarket, scanPatterns, explainPattern, scanAnalysisTools, explainAnalysisTools,
} from '../api/client'
import type {
  Candle, DetectedPattern, AIPatternExplanation, AnalysisToolResult, AIToolExplanation, ChartAnnotations,
} from '../api/client'
import PatternInfoPanel from '../components/PatternInfoPanel'
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
// Window to disambiguate a single click (hide/show) from a double click
// (select for detail) on a pattern row.
const PATTERN_CLICK_DELAY_MS = 220
// How often the chart's last (possibly still-forming) candle is refreshed.
// Only updates the visible bar via series.update() — does NOT re-trigger
// pattern/tool scans (those stay on their existing triggers) to avoid the
// same AI rate-limit problem re-scanning on a timer would cause.
const LIVE_POLL_MS = 5000

const DIR_DOT: Record<string, string> = {
  BULLISH: 'bg-green-400', BEARISH: 'bg-red-400', NEUTRAL: 'bg-slate-400',
}

const TOOL_LINE_COLORS: Record<string, string> = {
  ema20: '#22c55e', ema50: '#3b82f6', sma50: '#f59e0b', sma200: '#ef4444',
  daily_vwap: '#818cf8', anchored_vwap: '#c084fc',
  trend_line: '#fbbf24', trend_resistance: '#ef4444', trend_support: '#22c55e',
}

function toBarTime(timestamp: string): UTCTimestamp {
  return Math.floor(new Date(timestamp).getTime() / 1000) as UTCTimestamp
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
  // Highest-confidence pattern first — the list's own priority ranking.
  const sortedPatterns = [...patterns].sort((a, b) => b.confidence - a.confidence)
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

  async function runScan() {
    setLoading(true); setError(''); setAiExplanation(null)
    try {
      const res = await scanPatterns(symbol, interval, scanLimit)
      setPatterns(res.data.patterns)
      setFvgCount(res.data.fvgs.filter(f => !f.filled).length)
      setSelectedId(res.data.patterns[0]?.id ?? null)
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
      layout: { background: { type: ColorType.Solid, color: '#0f1117' }, textColor: '#64748b' },
      grid: { vertLines: { color: '#1a1d27' }, horzLines: { color: '#1a1d27' } },
      timeScale: { borderColor: '#2a2d3e' },
      rightPriceScale: { borderColor: '#2a2d3e' },
      width: chartRef.current.clientWidth,
      height: 420,
    })
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
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
        const endTime = new Date(oldest.timestamp).getTime() - 1
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
        // different time span — without this, the chart keeps whatever
        // zoom/pan range was visible before, which can point at empty space
        // in the new data and make the chart look frozen/blank.
        chartApiRef.current?.timeScale().fitContent()
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
        candleSeriesRef.current.update(toBar(live))

        const candles = allCandlesRef.current
        const lastIdx = candles.length - 1
        if (candles[lastIdx].timestamp === live.timestamp) {
          candles[lastIdx] = live
        } else if (new Date(live.timestamp) > new Date(candles[lastIdx].timestamp)) {
          allCandlesRef.current = [...candles, live]
          setLoadedCount(allCandlesRef.current.length)
        }
      } catch {
        // transient network hiccup — next tick retries, nothing to surface
      }
    }, LIVE_POLL_MS)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => { runScan() }, [symbol, interval])

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

    const visiblePatterns = patterns.filter(p => !hiddenPatternIds.has(p.id))

    // Priority rule: EVERY visible pattern always gets its text label marker
    // on the chart — candlestick patterns are a single point in time, so
    // without a label there's nothing to see at all for a non-selected one
    // (unlike chart-shape patterns' trendlines/zones, which still show
    // structure on their own). The SELECTED pattern additionally gets the
    // full read-out: breakout/invalidation levels + SL/targets as price
    // lines — kept selected-only so many visible patterns don't bury the
    // chart under dozens of overlapping horizontal lines.
    visiblePatterns.forEach(p => {
      const a = p.annotations
      const bullish = p.direction !== 'BEARISH'
      const isSelected = p.id === selectedId
      drawTrendlines(chart, a, lineSeriesRef, tl =>
        tl.label.includes('resistance') ? '#ef4444' : tl.label.includes('support') ? '#22c55e' : '#818cf8')
      allRectangles.push(...zonesToRectangles(a, nowIso))
      a.labels.forEach(l => allLabels.push({ ...l, bullish }))

      if (!isSelected) return

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
  }, [patterns, hiddenPatternIds, selectedId, toolResults])

  function submitSymbol() {
    const next = symbolInput.trim().toUpperCase()
    if (next) { setSymbolInput(next); setSymbol(next) }
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
    <div className="p-6 space-y-4">
      {/* Header — identity + primary controls, kept slim so the chart below is the first big thing on screen */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            Pattern Analysis
            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-green-400 bg-green-500/10 border border-green-500/30 rounded-full px-2 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /> LIVE
            </span>
          </h1>
          <p className="text-slate-500 text-sm">Automatic chart pattern detection, FVGs, Smart Money structure, and toggleable analysis tools — AI-explained</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={symbolInput} onChange={e => setSymbolInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submitSymbol()} onBlur={submitSymbol}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500 w-32"
          />
          <select value={interval} onChange={e => setInterval(e.target.value)}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none">
            {INTERVALS.map(i => <option key={i}>{i}</option>)}
          </select>
          <button onClick={runScan} disabled={loading}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
            {loading ? 'Scanning…' : 'Rescan'}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>}

      {/* Priority layout: the chart is the single dominant element (left,
          widest column); everything secondary (patterns, tools, AI) lives in
          a narrower sticky sidebar so it never outweighs the chart, and is
          tabbed rather than stacked so the page doesn't turn into a long
          scroll of equally-weighted sections. */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-4 items-start">
        <div className="space-y-4 min-w-0">
          <div ref={chartWrapperRef} className={`bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4 ${isFullscreen ? 'flex flex-col' : ''}`}>
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <p className="text-xs text-slate-500">{symbol} · {interval} — click a pattern once to hide it, double-click to view details</p>
              <div className="flex items-center gap-3">
                <p className="text-xs text-slate-600">
                  {loadedCount.toLocaleString()} candles loaded
                  {loadingOlder ? ' · loading older…' : historyExhausted ? ' · full history loaded' : ' · scroll left for more'}
                  {' · analyzing ' + scanLimit.toLocaleString()}
                  {' · '}{fvgCount} unfilled FVG{fvgCount === 1 ? '' : 's'}{toolsLoading ? ' · loading tools…' : ''}
                </p>
                <button onClick={toggleFullscreen}
                  title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                  className="text-xs px-2 py-1 bg-[#0f1117] border border-[#2a2d3e] rounded-lg text-slate-400 hover:text-white hover:border-indigo-500/40">
                  {isFullscreen ? '⤡ Exit Fullscreen' : '⤢ Fullscreen'}
                </button>
              </div>
            </div>
            <div ref={chartRef} className={isFullscreen ? 'flex-1' : ''} />
          </div>

          <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-3">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <p className="text-xs text-slate-500">Analysis tools — toggle individually, each with its own (ⓘ) documentation</p>
              {enabledTools.length > 0 && (
                toolsLoading ? (
                  <span className="text-xs text-amber-400 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" /> Scanning…
                  </span>
                ) : toolsLastUpdated ? (
                  <span className="text-xs text-green-400 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400" /> Live — updated {new Date(toolsLastUpdated).toLocaleTimeString()}
                  </span>
                ) : null
              )}
            </div>
            {toolsLoading && (
              <div className="relative h-1 w-full bg-[#0f1117] rounded-full overflow-hidden mb-2">
                <div className="tool-scan-bar absolute inset-y-0 w-1/3 bg-indigo-500 rounded-full" />
              </div>
            )}
            <ToolToggleBar enabled={enabledSet} onToggle={toggleTool} loading={toolsLoading} readyKeys={toolResultKeys} />
          </div>
        </div>

        <div className="space-y-3 xl:sticky xl:top-6">
          <div className="flex gap-1 bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-1">
            <button onClick={() => setSidebarTab('patterns')}
              className={`flex-1 text-xs font-semibold py-2 rounded-lg transition-colors ${
                sidebarTab === 'patterns' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}>
              Patterns ({patterns.length})
            </button>
            <button onClick={() => setSidebarTab('tools')}
              className={`flex-1 text-xs font-semibold py-2 rounded-lg transition-colors ${
                sidebarTab === 'tools' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}>
              Tools & AI{enabledTools.length > 0 ? ` (${enabledTools.length})` : ''}
            </button>
          </div>

          {sidebarTab === 'patterns' ? (
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
              <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                <h2 className="text-sm font-semibold text-slate-300">
                  Detected Patterns
                  {hiddenPatternIds.size > 0 && <span className="text-slate-600"> · {hiddenPatternIds.size} hidden</span>}
                </h2>
                <div className="flex items-center gap-3">
                  {hiddenPatternIds.size < patterns.length && patterns.length > 0 && (
                    <button onClick={() => setHiddenPatternIds(new Set(patterns.map(p => p.id)))}
                      className="text-xs text-indigo-400 hover:text-indigo-300">
                      Hide all
                    </button>
                  )}
                  {hiddenPatternIds.size > 0 && (
                    <button onClick={() => setHiddenPatternIds(new Set())}
                      className="text-xs text-indigo-400 hover:text-indigo-300">
                      Show all
                    </button>
                  )}
                </div>
              </div>
              {patterns.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-6">
                  {loading ? 'Scanning…' : 'No patterns detected on this timeframe right now.'}
                </p>
              ) : (
                <div className="space-y-1 max-h-[65vh] overflow-y-auto">
                  {sortedPatterns.map(p => {
                    const hidden = hiddenPatternIds.has(p.id)
                    return (
                      <div key={p.id}
                        onClick={() => handlePatternRowClick(p.id)}
                        onDoubleClick={() => handlePatternRowDoubleClick(p.id)}
                        title="Click to hide/show · double-click for details"
                        className={`w-full flex items-center gap-1 rounded-lg text-sm transition-colors cursor-pointer select-none ${
                          p.id === selectedId ? 'bg-indigo-500/20 border border-indigo-500/30' : 'hover:bg-[#0f1117] border border-transparent'
                        }`}>
                        <span className={`px-2 py-2 shrink-0 ${hidden ? 'text-slate-600' : 'text-indigo-400'}`}>
                          {hidden ? '🙈' : '👁'}
                        </span>
                        <span className={`flex-1 text-left py-2 pr-3 flex items-center justify-between gap-2 ${hidden ? 'opacity-40' : ''}`}>
                          <span className="flex items-center gap-2 min-w-0">
                            <span className={`w-2 h-2 rounded-full shrink-0 ${DIR_DOT[p.direction]}`} />
                            <span className="text-white truncate">{p.pattern_name}</span>
                            {p.id === topPatternId && (
                              <span className="shrink-0 text-[9px] font-bold text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded-full px-1.5 py-0.5">
                                TOP
                              </span>
                            )}
                          </span>
                          <span className="text-xs text-slate-500 shrink-0">{p.confidence.toFixed(0)}%</span>
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {enabledTools.length === 0 ? (
                <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-6 text-center text-slate-500 text-sm">
                  Toggle an analysis tool below the chart to see its results here.
                </div>
              ) : (
                <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h2 className="text-sm font-semibold text-slate-300">Tool Results</h2>
                    <button onClick={runAiExplain} disabled={aiLoading}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg">
                      {aiLoading ? 'Analyzing…' : 'AI Confluence'}
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {toolResults.map(t => (
                      <div key={t.tool_key} className="bg-[#0f1117] rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-white">{t.tool_name}</span>
                          <span className="text-xs font-bold flex items-center gap-1">
                            <span className={`w-1.5 h-1.5 rounded-full ${DIR_DOT[t.bias]}`} />
                            {t.bias}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">{t.error ? `Error: ${t.error}` : t.summary}</p>
                      </div>
                    ))}
                  </div>

                  {aiError && <p className="text-xs text-red-400">{aiError}</p>}
                  {aiExplanation && !aiExplanation.error && (
                    <div className="border-t border-[#2a2d3e] pt-3 space-y-2">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-sm font-bold text-indigo-300">{aiExplanation.market_bias ?? 'N/A'}</span>
                        {aiExplanation.confidence_score !== undefined && (
                          <span className="text-xs text-slate-500">Confidence: {aiExplanation.confidence_score.toFixed(0)}%</span>
                        )}
                        {aiExplanation.probability_of_success !== undefined && (
                          <span className="text-xs text-slate-500">Probability: {aiExplanation.probability_of_success?.toFixed(0)}%</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{aiExplanation.reasoning}</p>
                      <p className="text-xs text-slate-400"><span className="text-slate-500 font-medium">Confluence: </span>{aiExplanation.confluence_notes}</p>
                      <p className="text-xs text-slate-400"><span className="text-slate-500 font-medium">Risk: </span>{aiExplanation.risk_analysis}</p>
                      <div className="flex flex-col gap-1 text-xs text-slate-400">
                        {aiExplanation.entry_suggestion && <span>Entry: ${aiExplanation.entry_suggestion.toFixed(2)}</span>}
                        {aiExplanation.stop_loss && <span className="text-red-400">SL: ${aiExplanation.stop_loss.toFixed(2)}</span>}
                        {aiExplanation.take_profit && <span className="text-green-400">TP: ${aiExplanation.take_profit.toFixed(2)}</span>}
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
              <button onClick={() => setShowDetailModal(false)}
                className="text-xs text-slate-400 hover:text-white bg-[#1a1d27] border border-[#2a2d3e] rounded-lg px-2 py-1">
                ✕ Close
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
