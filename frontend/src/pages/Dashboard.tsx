import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'
import type { ISeriesApi, LogicalRange, UTCTimestamp } from 'lightweight-charts'
import { getMarket, getLiveMarket, getIndicators, getSignal } from '../api/client'
import type { Candle, TradingSignal, Indicators } from '../api/client'
import SignalCard from '../components/SignalCard'
import IndicatorPanel from '../components/IndicatorPanel'
import RegimeBadge from '../components/RegimeBadge'

const SYMBOL = 'BTCUSDT'
const INTERVAL = '5m'
const INITIAL_CANDLES = 500
const PAGE_CANDLES = 500
// Start fetching more history once the visible chart is within this many
// bars of the oldest candle currently loaded ("scrolled near the left edge").
const LOAD_MORE_THRESHOLD_BARS = 20
// How often the chart's last (possibly still-forming) candle is refreshed —
// without this the chart was a one-time static snapshot that never moved.
const LIVE_POLL_MS = 5000

function toBarTime(timestamp: string): UTCTimestamp {
  return Math.floor(new Date(timestamp).getTime() / 1000) as UTCTimestamp
}

function toBar(c: Candle) {
  return { time: toBarTime(c.timestamp), open: c.open, high: c.high, low: c.low, close: c.close }
}

export default function Dashboard() {
  const chartRef = useRef<HTMLDivElement>(null)
  const [signal, setSignal] = useState<TradingSignal | null>(null)
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [historyExhausted, setHistoryExhausted] = useState(false)

  async function load() {
    try {
      setRefreshing(true)
      const [sigRes, indRes] = await Promise.all([
        getSignal('rsi', SYMBOL, INTERVAL),
        getIndicators(SYMBOL, INTERVAL),
      ])
      setSignal(sigRes.data)
      setIndicators(indRes.data.indicators)
      setError('')
    } catch {
      setError('Failed to load data — is the backend running?')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // TradingView chart
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0f1117' }, textColor: '#64748b' },
      grid: { vertLines: { color: '#1a1d27' }, horzLines: { color: '#1a1d27' } },
      timeScale: { borderColor: '#2a2d3e' },
      rightPriceScale: { borderColor: '#2a2d3e' },
      width: chartRef.current.clientWidth,
      height: 320,
    })

    const candleSeries: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    })

    // Ascending by time, deduped — the full history loaded so far.
    let allCandles: Candle[] = []
    let hasMore = true
    let loadingMore = false

    async function loadOlder() {
      if (loadingMore || !hasMore || allCandles.length === 0) return
      loadingMore = true
      setLoadingOlder(true)
      try {
        const oldest = allCandles[0]
        const endTime = new Date(oldest.timestamp).getTime() - 1
        const res = await getMarket(SYMBOL, INTERVAL, PAGE_CANDLES, endTime)
        const older = res.data.candles

        if (!Array.isArray(older) || older.length === 0) {
          hasMore = false
          setHistoryExhausted(true)
          return
        }

        const existingTimes = new Set(allCandles.map((c) => c.timestamp))
        const newOnes = older.filter((c) => !existingTimes.has(c.timestamp))
        if (newOnes.length === 0) {
          hasMore = false
          setHistoryExhausted(true)
          return
        }

        const addedCount = newOnes.length
        allCandles = [...newOnes, ...allCandles]

        const prevRange = chart.timeScale().getVisibleLogicalRange()
        candleSeries.setData(allCandles.map(toBar))
        if (prevRange) {
          chart.timeScale().setVisibleLogicalRange({
            from: prevRange.from + addedCount,
            to: prevRange.to + addedCount,
          })
        }

        if (older.length < PAGE_CANDLES) hasMore = false
      } catch {
        // leave hasMore as-is — next scroll near the edge retries
      } finally {
        loadingMore = false
        setLoadingOlder(false)
      }
    }

    function onVisibleRangeChange(range: LogicalRange | null) {
      if (range && range.from <= LOAD_MORE_THRESHOLD_BARS) {
        loadOlder()
      }
    }

    getMarket(SYMBOL, INTERVAL, INITIAL_CANDLES).then((res) => {
      const candles = res.data.candles
      if (Array.isArray(candles) && candles.length > 0) {
        allCandles = candles
        candleSeries.setData(allCandles.map(toBar))
        if (candles.length < INITIAL_CANDLES) hasMore = false
      } else {
        hasMore = false
      }
    }).catch(() => {})

    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRangeChange)

    const liveTimer = window.setInterval(async () => {
      if (allCandles.length === 0) return
      try {
        const res = await getLiveMarket(SYMBOL, INTERVAL)
        const live = res.data
        candleSeries.update(toBar(live))

        const lastIdx = allCandles.length - 1
        if (allCandles[lastIdx].timestamp === live.timestamp) {
          allCandles[lastIdx] = live
        } else if (new Date(live.timestamp) > new Date(allCandles[lastIdx].timestamp)) {
          allCandles = [...allCandles, live]
        }
      } catch {
        // transient network hiccup — next tick retries
      }
    }, LIVE_POLL_MS)

    const resize = () => chart.applyOptions({ width: chartRef.current!.clientWidth })
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      window.clearInterval(liveTimer)
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRangeChange)
      chart.remove()
    }
  }, [])

  useEffect(() => { load() }, [])

  // Auto-refresh every 60s
  useEffect(() => {
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-500 text-sm">{SYMBOL} · {INTERVAL} · RSI Strategy</p>
        </div>
        <div className="flex items-center gap-3">
          {signal && <RegimeBadge regime={signal.regime} />}
          <button
            onClick={load}
            disabled={refreshing}
            className="text-xs px-3 py-1.5 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30 hover:bg-indigo-500/30 disabled:opacity-50"
          >
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-slate-500">{SYMBOL} Price (TradingView Lightweight Charts)</p>
          {loadingOlder && <p className="text-xs text-indigo-400">Loading older candles…</p>}
          {!loadingOlder && historyExhausted && <p className="text-xs text-slate-600">Full history loaded</p>}
        </div>
        <div ref={chartRef} />
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-slate-500 text-sm">Loading signals…</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            {signal && <SignalCard signal={signal} />}
          </div>
          <div>
            {indicators && <IndicatorPanel ind={indicators} symbol={SYMBOL} />}
          </div>
        </div>
      )}
    </div>
  )
}
