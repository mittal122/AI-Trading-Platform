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
  const scanLimit = Math.min(Math.max(loadedCount, INITIAL_CANDLES), MAX_SCAN_LIMIT)

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
    if (enabledTools.length === 0) { setToolResults([]); return }
    setToolsLoading(true)
    try {
      const res = await scanAnalysisTools(symbol, interval, enabledTools, scanLimit)
      setToolResults(res.data.tools)
    } catch {
      setToolResults([])
    } finally {
      setToolsLoading(false)
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

    const resize = () => chart.applyOptions({ width: chartRef.current!.clientWidth })
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
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

  // Draw annotations — the selected pattern's + every enabled tool's, merged
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

    if (selected) {
      const a = selected.annotations
      const bullish = selected.direction !== 'BEARISH'
      drawTrendlines(chart, a, lineSeriesRef, tl =>
        tl.label.includes('resistance') ? '#ef4444' : tl.label.includes('support') ? '#22c55e' : '#818cf8')
      drawLevels(candleSeries, a, priceLinesRef, bullish)
      allRectangles.push(...zonesToRectangles(a, nowIso))
      if (selected.stop_loss) priceLinesRef.current.push(candleSeries.createPriceLine({
        price: selected.stop_loss, color: '#ef4444', lineWidth: 1, lineStyle: 2, title: 'Stop Loss',
      }))
      ;[selected.target_1, selected.target_2, selected.target_3].forEach((t, i) => {
        if (t) priceLinesRef.current.push(candleSeries.createPriceLine({
          price: t, color: '#22c55e', lineWidth: 1, lineStyle: 2, title: `Target ${i + 1}`,
        }))
      })
      a.labels.forEach(l => allLabels.push({ ...l, bullish }))
    }

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
  }, [selected, toolResults])

  function submitSymbol() {
    const next = symbolInput.trim().toUpperCase()
    if (next) { setSymbolInput(next); setSymbol(next) }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Pattern Analysis</h1>
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

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4 space-y-3">
        <p className="text-xs text-slate-500">Analysis tools — toggle individually, each with its own (ⓘ) documentation</p>
        <ToolToggleBar enabled={enabledSet} onToggle={toggleTool} />
      </div>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <p className="text-xs text-slate-500">{symbol} · {interval} — select a pattern below to draw it on the chart</p>
          <p className="text-xs text-slate-600">
            {loadedCount.toLocaleString()} candles loaded
            {loadingOlder ? ' · loading older…' : historyExhausted ? ' · full history loaded' : ' · scroll left for more'}
            {' · analyzing ' + scanLimit.toLocaleString()}
            {' · '}{fvgCount} unfilled FVG{fvgCount === 1 ? '' : 's'}{toolsLoading ? ' · loading tools…' : ''}
          </p>
        </div>
        <div ref={chartRef} />
      </div>

      {enabledTools.length > 0 && (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-sm font-semibold text-slate-300">Tool Results</h2>
            <button onClick={runAiExplain} disabled={aiLoading}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg">
              {aiLoading ? 'Analyzing…' : 'AI Confluence Analysis'}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {toolResults.map(t => (
              <div key={t.tool_key} className="bg-[#0f1117] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{t.tool_name}</span>
                  <span className={`text-xs font-bold flex items-center gap-1`}>
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
              <div className="flex items-center gap-3">
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
              <div className="flex gap-4 text-xs text-slate-400">
                {aiExplanation.entry_suggestion && <span>Entry: ${aiExplanation.entry_suggestion.toFixed(2)}</span>}
                {aiExplanation.stop_loss && <span className="text-red-400">SL: ${aiExplanation.stop_loss.toFixed(2)}</span>}
                {aiExplanation.take_profit && <span className="text-green-400">TP: ${aiExplanation.take_profit.toFixed(2)}</span>}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1 bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">
            Detected Patterns ({patterns.length})
          </h2>
          {patterns.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-6">
              {loading ? 'Scanning…' : 'No patterns detected on this timeframe right now.'}
            </p>
          ) : (
            <div className="space-y-1 max-h-[480px] overflow-y-auto">
              {patterns.map(p => (
                <button key={p.id} onClick={() => setSelectedId(p.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between transition-colors ${
                    p.id === selectedId ? 'bg-indigo-500/20 border border-indigo-500/30' : 'hover:bg-[#0f1117] border border-transparent'
                  }`}>
                  <span className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${DIR_DOT[p.direction]}`} />
                    <span className="text-white">{p.pattern_name}</span>
                  </span>
                  <span className="text-xs text-slate-500">{p.confidence.toFixed(0)}%</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          {selected ? <PatternInfoPanel pattern={selected} aiLoading={patternAiLoading && !patternAiCache[selected.id]} /> : (
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-8 text-center text-slate-500 text-sm">
              Select a detected pattern to see its full analysis
            </div>
          )}
        </div>
      </div>
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
) {
  a.levels.forEach(lv => {
    const isBreakout = lv.label === 'breakout_level'
    const isSupport = lv.label.startsWith('support')
    const isResistance = lv.label.startsWith('resistance')
    const isSR = (isSupport || isResistance) && lv.strength !== undefined

    const color = isSR
      ? srLevelColor(isSupport, lv.strength!)
      : isBreakout ? (bullish ? '#22c55e' : '#ef4444') : '#f59e0b'

    ref.current.push(candleSeries.createPriceLine({
      price: lv.price,
      color,
      lineWidth: isBreakout ? 2 : 1,
      lineStyle: isBreakout ? 0 : 2,
      title: lv.label.replace(/_/g, ' '),
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
