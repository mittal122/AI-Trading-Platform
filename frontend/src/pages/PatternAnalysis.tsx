import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  createChart, ColorType, CandlestickSeries, LineSeries, createSeriesMarkers,
} from 'lightweight-charts'
import type {
  IChartApi, ISeriesApi, IPriceLine, ISeriesMarkersPluginApi, Time, UTCTimestamp,
} from 'lightweight-charts'
import {
  getMarket, scanPatterns, scanAnalysisTools, explainAnalysisTools,
} from '../api/client'
import type { DetectedPattern, AnalysisToolResult, AIToolExplanation, ChartAnnotations } from '../api/client'
import PatternInfoPanel from '../components/PatternInfoPanel'
import ToolToggleBar from '../components/ToolToggleBar'
import { usePersistedState } from '../hooks/usePersistedState'

const INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']

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

  const [enabledTools, setEnabledTools] = usePersistedState<string[]>('patterns.enabledTools', [])
  const [toolResults, setToolResults] = useState<AnalysisToolResult[]>([])
  const [toolsLoading, setToolsLoading] = useState(false)

  const [aiExplanation, setAiExplanation] = useState<AIToolExplanation | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')

  const chartRef = useRef<HTMLDivElement>(null)
  const chartApiRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const lineSeriesRef = useRef<ISeriesApi<'Line'>[]>([])
  const priceLinesRef = useRef<IPriceLine[]>([])
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null)

  const selected = patterns.find(p => p.id === selectedId) ?? null
  const enabledSet = new Set(enabledTools)

  async function runScan() {
    setLoading(true); setError(''); setAiExplanation(null)
    try {
      const res = await scanPatterns(symbol, interval, 400)
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
      const res = await scanAnalysisTools(symbol, interval, enabledTools, 400)
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
      const res = await explainAnalysisTools(symbol, interval, enabledTools, 400)
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

    const resize = () => chart.applyOptions({ width: chartRef.current!.clientWidth })
    window.addEventListener('resize', resize)
    return () => { window.removeEventListener('resize', resize); chart.remove() }
  }, [])

  // Load candles whenever symbol/interval changes
  useEffect(() => {
    if (!candleSeriesRef.current) return
    getMarket(symbol, interval, 400).then(res => {
      const candles = res.data.candles
      if (Array.isArray(candles)) {
        candleSeriesRef.current!.setData(candles.map(c => ({
          time: toBarTime(c.timestamp), open: c.open, high: c.high, low: c.low, close: c.close,
        })))
      }
    }).catch(() => {})
  }, [symbol, interval])

  useEffect(() => { runScan() }, [symbol, interval])
  useEffect(() => { runToolScan() }, [symbol, interval, enabledTools.join(',')])

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

    if (selected) {
      const a = selected.annotations
      const bullish = selected.direction !== 'BEARISH'
      drawTrendlines(chart, a, lineSeriesRef, tl =>
        tl.label.includes('resistance') ? '#ef4444' : tl.label.includes('support') ? '#22c55e' : '#818cf8')
      drawLevelsAndZones(candleSeries, a, priceLinesRef, bullish)
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
      drawLevelsAndZones(candleSeries, tool.annotations, priceLinesRef, bullish)
      tool.annotations.labels.forEach(l => allLabels.push({ ...l, bullish }))
    })

    markersPluginRef.current?.setMarkers(allLabels.map(l => ({
      time: toBarTime(l.time), position: 'atPriceMiddle' as const, price: l.price,
      color: l.bullish ? '#22c55e' : '#ef4444', shape: 'circle' as const, text: l.text,
    })))
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
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-slate-500">{symbol} · {interval} — select a pattern below to draw it on the chart</p>
          <p className="text-xs text-slate-600">
            {fvgCount} unfilled FVG{fvgCount === 1 ? '' : 's'}{toolsLoading ? ' · loading tools…' : ''}
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
          {selected ? <PatternInfoPanel pattern={selected} /> : (
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

function drawLevelsAndZones(
  candleSeries: ISeriesApi<'Candlestick'>,
  a: ChartAnnotations,
  ref: React.MutableRefObject<IPriceLine[]>,
  bullish: boolean,
) {
  a.levels.forEach(lv => {
    const isBreakout = lv.label === 'breakout_level'
    ref.current.push(candleSeries.createPriceLine({
      price: lv.price,
      color: isBreakout ? (bullish ? '#22c55e' : '#ef4444') : '#f59e0b',
      lineWidth: isBreakout ? 2 : 1,
      lineStyle: isBreakout ? 0 : 2,
      title: lv.label.replace(/_/g, ' '),
    }))
  })
  a.zones.forEach(z => {
    const color = z.bias === 'BEARISH' ? '#ef4444' : z.bias === 'BULLISH' ? '#22c55e' : '#818cf8'
    ref.current.push(candleSeries.createPriceLine({ price: z.top, color, lineWidth: 1, lineStyle: 3, title: `${z.label} top` }))
    ref.current.push(candleSeries.createPriceLine({ price: z.bottom, color, lineWidth: 1, lineStyle: 3, title: `${z.label} bottom` }))
  })
}
