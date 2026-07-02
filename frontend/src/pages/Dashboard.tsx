import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'
import type { UTCTimestamp } from 'lightweight-charts'
import { getMarket, getIndicators, getSignal } from '../api/client'
import type { TradingSignal, Indicators } from '../api/client'
import SignalCard from '../components/SignalCard'
import IndicatorPanel from '../components/IndicatorPanel'
import RegimeBadge from '../components/RegimeBadge'

const SYMBOL = 'BTCUSDT'
const INTERVAL = '5m'

export default function Dashboard() {
  const chartRef = useRef<HTMLDivElement>(null)
  const [signal, setSignal] = useState<TradingSignal | null>(null)
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

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

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    })

    getMarket(SYMBOL, INTERVAL, 150).then((res) => {
      const candles = res.data.candles
      if (Array.isArray(candles)) {
        candleSeries.setData(candles.map((c) => ({
          time: Math.floor(new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
          open: c.open, high: c.high, low: c.low, close: c.close,
        })))
      }
    }).catch(() => {})

    const resize = () => chart.applyOptions({ width: chartRef.current!.clientWidth })
    window.addEventListener('resize', resize)
    return () => { window.removeEventListener('resize', resize); chart.remove() }
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
        <p className="text-xs text-slate-500 mb-3">{SYMBOL} Price (TradingView Lightweight Charts)</p>
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
