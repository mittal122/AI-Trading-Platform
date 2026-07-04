import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'
import type { ISeriesApi, LogicalRange, UTCTimestamp } from 'lightweight-charts'
import {
  getMarket, getLiveMarket, getIndicators, getSignal,
  getMarketOverview, getWatchlistTickers, getDepthPressure, getBuyPressure, getFunding,
} from '../api/client'
import type {
  Candle, TradingSignal, Indicators, MarketOverview, Ticker24h, DepthPressure, BuyPressure, Funding,
} from '../api/client'
import SignalCard from '../components/SignalCard'
import IndicatorPanel from '../components/IndicatorPanel'
import RegimeBadge from '../components/RegimeBadge'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { usePersistedState } from '../hooks/usePersistedState'

const INTERVAL = '5m'
const INITIAL_CANDLES = 500
const PAGE_CANDLES = 500
const LOAD_MORE_THRESHOLD_BARS = 20
const LIVE_POLL_MS = 5000
// Overview + watchlist ticker refresh (server caches the underlying Binance
// pull for 30s, so polling faster than this buys nothing).
const OVERVIEW_POLL_MS = 20_000
// Order-flow widgets for the selected coin (depth / taker flow / funding).
const FLOW_POLL_MS = 10_000
// Per-coin Signal Radar (full strategy run per coin — keep it slow).
const RADAR_POLL_MS = 60_000

const DEFAULT_WATCHLIST = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT']

function toBarTime(timestamp: string): UTCTimestamp {
  return Math.floor(new Date(timestamp).getTime() / 1000) as UTCTimestamp
}

function toBar(c: Candle) {
  return { time: toBarTime(c.timestamp), open: c.open, high: c.high, low: c.low, close: c.close }
}

function fmtPrice(p: number): string {
  return p >= 1000 ? p.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : p >= 1 ? p.toFixed(2)
    : p.toFixed(6)
}

function fmtVolume(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`
  return `$${(v / 1e3).toFixed(0)}K`
}

const pctCls = (p: number) => (p >= 0 ? 'text-green-400' : 'text-red-400')
const pctText = (p: number) => `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`

export default function Dashboard() {
  const chartRef = useRef<HTMLDivElement>(null)
  const [symbol, setSymbol] = usePersistedState('dashboard.symbol', 'BTCUSDT')
  const [watchlist, setWatchlist] = usePersistedState<string[]>('dashboard.watchlist', DEFAULT_WATCHLIST)

  const [signal, setSignal] = useState<TradingSignal | null>(null)
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [historyExhausted, setHistoryExhausted] = useState(false)

  const [overview, setOverview] = useState<MarketOverview | null>(null)
  const [watchTickers, setWatchTickers] = useState<Ticker24h[]>([])
  const [depth, setDepth] = useState<DepthPressure | null>(null)
  const [flow, setFlow] = useState<BuyPressure | null>(null)
  const [funding, setFunding] = useState<Funding | null>(null)
  const [radar, setRadar] = useState<Record<string, TradingSignal>>({})
  const [moversTab, setMoversTab] = useState<'gainers' | 'losers' | 'volume'>('gainers')

  async function load() {
    try {
      setRefreshing(true)
      const [sigRes, indRes] = await Promise.all([
        getSignal('rsi', symbol, INTERVAL),
        getIndicators(symbol, INTERVAL),
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

  // ── Market overview + watchlist tickers ──────────────────────────────────
  useEffect(() => {
    let cancelled = false
    async function tick() {
      try {
        const [ov, wl] = await Promise.all([
          getMarketOverview(),
          watchlist.length > 0 ? getWatchlistTickers(watchlist) : Promise.resolve({ data: { tickers: [] } }),
        ])
        if (cancelled) return
        setOverview(ov.data)
        setWatchTickers(wl.data.tickers)
      } catch { /* transient — next tick retries */ }
    }
    tick()
    const id = setInterval(tick, OVERVIEW_POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [watchlist])

  // ── Order-flow widgets for the selected coin ─────────────────────────────
  useEffect(() => {
    let cancelled = false
    setDepth(null); setFlow(null); setFunding(null)
    async function tick() {
      try {
        const [d, f, fu] = await Promise.all([
          getDepthPressure(symbol), getBuyPressure(symbol, INTERVAL), getFunding(symbol),
        ])
        if (cancelled) return
        setDepth(d.data); setFlow(f.data); setFunding(fu.data)
      } catch { /* transient */ }
    }
    tick()
    const id = setInterval(tick, FLOW_POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [symbol])

  // ── Signal Radar — one full strategy signal per watchlist coin ───────────
  useEffect(() => {
    let cancelled = false
    async function tick() {
      const results = await Promise.allSettled(
        watchlist.map(s => getSignal('rsi', s, '15m')),
      )
      if (cancelled) return
      const next: Record<string, TradingSignal> = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') next[watchlist[i]] = r.value.data
      })
      setRadar(next)
    }
    tick()
    const id = setInterval(tick, RADAR_POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [watchlist])

  // ── TradingView chart (selected coin) ────────────────────────────────────
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#0f1117' }, textColor: '#64748b' },
      grid: { vertLines: { color: '#1a1d27' }, horzLines: { color: '#1a1d27' } },
      timeScale: { borderColor: '#2a2d3e' },
      rightPriceScale: { borderColor: '#2a2d3e' },
      handleScale: { axisPressedMouseMove: { time: true, price: false } },
      width: chartRef.current.clientWidth,
      height: 340,
    })

    const candleSeries: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
      autoscaleInfoProvider: (original: () => any) => {
        const res = original()
        if (res?.priceRange) {
          return { ...res, priceRange: { ...res.priceRange, minValue: Math.max(0, res.priceRange.minValue) } }
        }
        return res
      },
    })

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
        const res = await getMarket(symbol, INTERVAL, PAGE_CANDLES, endTime)
        const older = res.data.candles
        if (!Array.isArray(older) || older.length === 0) {
          hasMore = false; setHistoryExhausted(true); return
        }
        const existingTimes = new Set(allCandles.map((c) => c.timestamp))
        const newOnes = older.filter((c) => !existingTimes.has(c.timestamp))
        if (newOnes.length === 0) { hasMore = false; setHistoryExhausted(true); return }
        const addedCount = newOnes.length
        allCandles = [...newOnes, ...allCandles]
        const prevRange = chart.timeScale().getVisibleLogicalRange()
        candleSeries.setData(allCandles.map(toBar))
        if (prevRange) {
          chart.timeScale().setVisibleLogicalRange({
            from: prevRange.from + addedCount, to: prevRange.to + addedCount,
          })
        }
        if (older.length < PAGE_CANDLES) hasMore = false
      } catch { /* retried on next scroll */ } finally {
        loadingMore = false
        setLoadingOlder(false)
      }
    }

    function onVisibleRangeChange(range: LogicalRange | null) {
      if (range && range.from <= LOAD_MORE_THRESHOLD_BARS) loadOlder()
    }

    getMarket(symbol, INTERVAL, INITIAL_CANDLES).then((res) => {
      const candles = res.data.candles
      if (Array.isArray(candles) && candles.length > 0) {
        allCandles = candles
        candleSeries.setData(allCandles.map(toBar))
        chart.timeScale().fitContent()
        if (candles.length < INITIAL_CANDLES) hasMore = false
      } else {
        hasMore = false
      }
    }).catch(() => {})

    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRangeChange)

    const liveTimer = window.setInterval(async () => {
      if (allCandles.length === 0) return
      try {
        const res = await getLiveMarket(symbol, INTERVAL)
        const live = res.data
        candleSeries.update(toBar(live))
        const lastIdx = allCandles.length - 1
        if (allCandles[lastIdx].timestamp === live.timestamp) {
          allCandles[lastIdx] = live
        } else if (new Date(live.timestamp) > new Date(allCandles[lastIdx].timestamp)) {
          allCandles = [...allCandles, live]
        }
      } catch { /* next tick retries */ }
    }, LIVE_POLL_MS)

    const resize = () => chart.applyOptions({ width: chartRef.current!.clientWidth })
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      window.clearInterval(liveTimer)
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRangeChange)
      chart.remove()
    }
  }, [symbol])

  useEffect(() => { load() }, [symbol])
  useEffect(() => {
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [symbol])

  function addToWatchlist(s: string) {
    const next = s.trim().toUpperCase()
    if (next && !watchlist.includes(next)) setWatchlist([...watchlist, next])
  }
  function removeFromWatchlist(s: string) {
    setWatchlist(watchlist.filter(w => w !== s))
  }

  const movers = overview
    ? moversTab === 'gainers' ? overview.top_gainers
      : moversTab === 'losers' ? overview.top_losers
      : overview.volume_leaders
    : []

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Market Dashboard</h1>
          <p className="text-slate-500 text-sm">Live market overview, watchlist, order flow, and instant signals</p>
        </div>
        <div className="flex items-center gap-3">
          <SymbolSearchInput value={symbol} onCommit={setSymbol} className="w-40" />
          {signal && <RegimeBadge regime={signal.regime} />}
          <button onClick={load} disabled={refreshing}
            className="text-xs px-3 py-1.5 bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/30 hover:bg-indigo-500/30 disabled:opacity-50">
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Market overview strip — the "risk-on or risk-off" read at a glance */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {overview.btc && (
            <OverviewCard label="BTC" value={`$${fmtPrice(overview.btc.last_price)}`}
              sub={pctText(overview.btc.price_change_pct)} subCls={pctCls(overview.btc.price_change_pct)} />
          )}
          {overview.eth && (
            <OverviewCard label="ETH" value={`$${fmtPrice(overview.eth.last_price)}`}
              sub={pctText(overview.eth.price_change_pct)} subCls={pctCls(overview.eth.price_change_pct)} />
          )}
          <OverviewCard label={`Breadth (${overview.counted_pairs} liquid pairs)`}
            value={`${overview.advancers} ▲ / ${overview.decliners} ▼`}
            sub={overview.advancers >= overview.decliners ? 'risk-on tilt' : 'risk-off tilt'}
            subCls={overview.advancers >= overview.decliners ? 'text-green-400' : 'text-red-400'} />
          <OverviewCard label="Avg 24h move" value={pctText(overview.avg_change_pct)}
            valueCls={pctCls(overview.avg_change_pct)} sub="across liquid USDT pairs" />
          <OverviewCard label="24h volume (liquid pairs)" value={fmtVolume(overview.total_quote_volume)} sub="quote turnover" />
        </div>
      )}

      {/* Watchlist + selected-coin panel */}
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,380px)_1fr] gap-4 items-start">
        {/* Watchlist */}
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-300">Watchlist</h2>
            <span className="text-xs text-slate-600">{watchlist.length} coins</span>
          </div>
          <div className="mb-3">
            <SymbolSearchInput value="" onCommit={addToWatchlist} />
          </div>
          <div className="space-y-1">
            {watchTickers.map(t => {
              const range = t.high - t.low
              const pos = range > 0 ? Math.min(1, Math.max(0, (t.last_price - t.low) / range)) : 0.5
              const r = radar[t.symbol]
              return (
                <div key={t.symbol}
                  onClick={() => setSymbol(t.symbol)}
                  className={`rounded-lg px-3 py-2 cursor-pointer transition-colors border ${
                    t.symbol === symbol ? 'bg-indigo-500/15 border-indigo-500/30' : 'border-transparent hover:bg-[#0f1117]'
                  }`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-white">{t.symbol.replace('USDT', '')}</span>
                    <span className="flex items-center gap-2">
                      {r && r.direction !== 'FLAT' && (
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                          r.direction === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>{r.direction}</span>
                      )}
                      <span className="text-sm text-slate-300 tabular-nums">${fmtPrice(t.last_price)}</span>
                      <span className={`text-xs font-semibold tabular-nums w-16 text-right ${pctCls(t.price_change_pct)}`}>
                        {pctText(t.price_change_pct)}
                      </span>
                      <button onClick={e => { e.stopPropagation(); removeFromWatchlist(t.symbol) }}
                        title="Remove from watchlist"
                        className="text-slate-600 hover:text-red-400 text-xs px-1">✕</button>
                    </span>
                  </div>
                  {/* 24h range position — where price sits between today's low and high */}
                  <div className="mt-1.5 flex items-center gap-2">
                    <span className="text-[9px] text-slate-600 tabular-nums">L</span>
                    <div className="relative flex-1 h-1 bg-[#0f1117] rounded-full">
                      <div className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-indigo-400"
                        style={{ left: `calc(${(pos * 100).toFixed(1)}% - 3px)` }} />
                    </div>
                    <span className="text-[9px] text-slate-600 tabular-nums">H</span>
                    <span className="text-[9px] text-slate-600 tabular-nums w-14 text-right">{fmtVolume(t.quote_volume)}</span>
                  </div>
                </div>
              )
            })}
            {watchTickers.length === 0 && (
              <p className="text-xs text-slate-600 text-center py-4">Loading watchlist…</p>
            )}
          </div>
        </div>

        {/* Selected coin: chart + order-flow row */}
        <div className="space-y-3 min-w-0">
          <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs text-slate-500">{symbol} · {INTERVAL} — live chart</p>
              {loadingOlder && <p className="text-xs text-indigo-400">Loading older candles…</p>}
              {!loadingOlder && historyExhausted && <p className="text-xs text-slate-600">Full history loaded</p>}
            </div>
            <div ref={chartRef} />
          </div>

          {/* Order-flow widgets — what the big players are doing right now */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Order-book pressure */}
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
              <p className="text-xs text-slate-500 mb-2" title="Resting bid vs ask notional in the top of the order book — more bid-side depth means buyers are defending below price">
                Order-Book Pressure ⓘ
              </p>
              {depth ? (
                <>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-green-400">Bids {(depth.bid_ratio * 100).toFixed(0)}%</span>
                    <span className="text-red-400">{((1 - depth.bid_ratio) * 100).toFixed(0)}% Asks</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden bg-[#0f1117] flex">
                    <div className="bg-green-500/70" style={{ width: `${depth.bid_ratio * 100}%` }} />
                    <div className="bg-red-500/70 flex-1" />
                  </div>
                  <p className="text-[10px] text-slate-600 mt-2">
                    Biggest walls: <span className="text-green-400">${fmtPrice(depth.biggest_bid_wall_price)}</span> ({fmtVolume(depth.biggest_bid_wall_notional)})
                    {' · '}<span className="text-red-400">${fmtPrice(depth.biggest_ask_wall_price)}</span> ({fmtVolume(depth.biggest_ask_wall_notional)})
                  </p>
                </>
              ) : <p className="text-xs text-slate-600">Loading…</p>}
            </div>

            {/* Taker flow */}
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
              <p className="text-xs text-slate-500 mb-2" title="Share of traded volume where the BUYER was the aggressor (market orders hitting the ask) over the last 20 candles — above 50% means buyers are attacking">
                Aggressive Buy Flow ⓘ
              </p>
              {flow ? (
                <>
                  <p className={`text-lg font-bold ${flow.buy_ratio >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                    {(flow.buy_ratio * 100).toFixed(1)}% buyers
                  </p>
                  <div className="flex items-end gap-0.5 h-8 mt-2">
                    {flow.recent_ratios.map((r, i) => (
                      <div key={i} className={`flex-1 rounded-sm ${r >= 0.5 ? 'bg-green-500/60' : 'bg-red-500/60'}`}
                        style={{ height: `${Math.max(10, r * 100)}%` }} />
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-600 mt-1">last 10 candles · {flow.interval}</p>
                </>
              ) : <p className="text-xs text-slate-600">Loading…</p>}
            </div>

            {/* Funding */}
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
              <p className="text-xs text-slate-500 mb-2" title="Perpetual futures funding rate — positive means longs pay shorts (crowded long positioning), negative means shorts pay longs. The classic institutional leverage/positioning read">
                Funding (Perps) ⓘ
              </p>
              {funding ? (
                <>
                  <p className={`text-lg font-bold ${funding.funding_rate >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(funding.funding_rate * 100).toFixed(4)}%
                  </p>
                  <p className="text-[10px] text-slate-600 mt-1">
                    ≈ {funding.funding_rate_annualized_pct.toFixed(1)}% annualized ·
                    {funding.funding_rate >= 0 ? ' longs paying (crowded long)' : ' shorts paying (crowded short)'}
                  </p>
                  <p className="text-[10px] text-slate-600 mt-1">mark ${fmtPrice(funding.mark_price)}</p>
                </>
              ) : <p className="text-xs text-slate-600">No perp market / loading…</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Top movers */}
      {overview && (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-sm font-semibold text-slate-300 mr-2">Market Movers</h2>
            {(['gainers', 'losers', 'volume'] as const).map(tab => (
              <button key={tab} onClick={() => setMoversTab(tab)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  moversTab === tab
                    ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                    : 'bg-[#0f1117] text-slate-500 border-[#2a2d3e] hover:text-white'
                }`}>
                {tab === 'gainers' ? 'Top Gainers' : tab === 'losers' ? 'Top Losers' : 'Volume Leaders'}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-slate-600">liquid USDT pairs only · click a row to load it</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {movers.map(t => (
              <div key={t.symbol} onClick={() => setSymbol(t.symbol)}
                className="bg-[#0f1117] rounded-lg px-3 py-2 cursor-pointer hover:bg-[#232736] transition-colors">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-white">{t.symbol.replace('USDT', '')}</span>
                  <span className={`text-xs font-bold tabular-nums ${pctCls(t.price_change_pct)}`}>{pctText(t.price_change_pct)}</span>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-xs text-slate-500 tabular-nums">${fmtPrice(t.last_price)}</span>
                  <span className="text-[10px] text-slate-600 tabular-nums">{fmtVolume(t.quote_volume)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}

      {/* Selected-coin deep dive: full signal + indicators */}
      {loading ? (
        <p className="text-slate-500 text-sm">Loading signals…</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            {signal && <SignalCard signal={signal} />}
          </div>
          <div>
            {indicators && <IndicatorPanel ind={indicators} symbol={symbol} />}
          </div>
        </div>
      )}
    </div>
  )
}

function OverviewCard({ label, value, valueCls, sub, subCls }: {
  label: string; value: string; valueCls?: string; sub?: string; subCls?: string
}) {
  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-lg font-semibold tabular-nums ${valueCls ?? 'text-white'}`}>{value}</p>
      {sub && <p className={`text-xs mt-0.5 ${subCls ?? 'text-slate-600'}`}>{sub}</p>}
    </div>
  )
}
