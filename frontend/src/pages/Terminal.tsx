import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'
import type { ISeriesApi, IPriceLine, LogicalRange, UTCTimestamp } from 'lightweight-charts'
import { drawSignalLines, clearSignalLines } from '../lib/signalLines'
import { parseUtcMs } from '../lib/time'
import { Info, X, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import {
  getMarket, getLiveMarket, getIndicators, getSignal,
  getMarketOverview, getWatchlistTickers, getDepthPressure, getBuyPressure, getFunding,
} from '../api/client'
import type {
  Candle, TradingSignal, Indicators, MarketOverview, Ticker24h, DepthPressure, BuyPressure, Funding,
} from '../api/client'
import SignalCard from '../components/SignalCard'
import IndicatorPanel from '../components/IndicatorPanel'
import SymbolSearchInput from '../components/SymbolSearchInput'
import VolumeSpikeScanner from '../components/VolumeSpikeScanner'
import { usePersistedState } from '../hooks/usePersistedState'

const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d']
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
  return Math.floor(parseUtcMs(timestamp) / 1000) as UTCTimestamp
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

const pctCls = (p: number) => (p >= 0 ? 'text-up' : 'text-down')
const pctText = (p: number) => `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`

export default function Terminal() {
  const chartRef = useRef<HTMLDivElement>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const signalLinesRef = useRef<IPriceLine[]>([])
  const [signalOnChart, setSignalOnChart] = useState(false)
  const [symbol, setSymbol] = usePersistedState('dashboard.symbol', 'BTCUSDT')
  const [interval, setInterval_] = usePersistedState('terminal.interval', '5m')
  const [watchlist, setWatchlist] = usePersistedState<string[]>('dashboard.watchlist', DEFAULT_WATCHLIST)

  const [signal, setSignal] = useState<TradingSignal | null>(null)
  const [indicators, setIndicators] = useState<Indicators | null>(null)
  const [error, setError] = useState('')
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
      const [sigRes, indRes] = await Promise.all([
        getSignal('rsi', symbol, interval),
        getIndicators(symbol, interval),
      ])
      setSignal(sigRes.data)
      setIndicators(indRes.data.indicators)
      setError('')
    } catch {
      setError('Failed to load data — is the backend running?')
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
          getDepthPressure(symbol), getBuyPressure(symbol, interval), getFunding(symbol),
        ])
        if (cancelled) return
        setDepth(d.data); setFlow(f.data); setFunding(fu.data)
      } catch { /* transient */ }
    }
    tick()
    const id = setInterval(tick, FLOW_POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [symbol, interval])

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

  // ── Live chart (selected coin) ───────────────────────────────────────────
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#11141b' }, textColor: '#5c6475', attributionLogo: false },
      grid: { vertLines: { color: '#1a1f2b' }, horzLines: { color: '#1a1f2b' } },
      timeScale: { borderColor: '#232837', fixRightEdge: true },
      rightPriceScale: { borderColor: '#232837' },
      handleScale: { axisPressedMouseMove: { time: true, price: false } },
      crosshair: {
        vertLine: { color: '#3d465c', labelBackgroundColor: '#303748' },
        horzLine: { color: '#3d465c', labelBackgroundColor: '#303748' },
      },
      width: chartRef.current.clientWidth,
      height: 400,
    })

    const candleSeries: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
      upColor: '#2ebd85', downColor: '#f6465d',
      borderUpColor: '#2ebd85', borderDownColor: '#f6465d',
      wickUpColor: '#2ebd85', wickDownColor: '#f6465d',
      autoscaleInfoProvider: (original: () => any) => {
        const res = original()
        if (res?.priceRange) {
          return { ...res, priceRange: { ...res.priceRange, minValue: Math.max(0, res.priceRange.minValue) } }
        }
        return res
      },
    })
    candleSeriesRef.current = candleSeries
    signalLinesRef.current = []
    setSignalOnChart(false)

    let allCandles: Candle[] = []
    let hasMore = true
    let loadingMore = false

    async function loadOlder() {
      if (loadingMore || !hasMore || allCandles.length === 0) return
      loadingMore = true
      setLoadingOlder(true)
      try {
        const oldest = allCandles[0]
        const endTime = parseUtcMs(oldest.timestamp) - 1
        const res = await getMarket(symbol, interval, PAGE_CANDLES, endTime)
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

    getMarket(symbol, interval, INITIAL_CANDLES).then((res) => {
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
        const res = await getLiveMarket(symbol, interval)
        const live = res.data
        const bar = toBar(live)
        // NaN-time bar from a glitched response would poison the series
        // (every later repaint throws "Value is null") — validate first.
        if (!Number.isFinite(bar.time) || !Number.isFinite(bar.close)) return
        candleSeries.update(bar)
        const lastIdx = allCandles.length - 1
        if (allCandles[lastIdx].timestamp === live.timestamp) {
          allCandles[lastIdx] = live
        } else if (parseUtcMs(live.timestamp) > parseUtcMs(allCandles[lastIdx].timestamp)) {
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
      candleSeriesRef.current = null
      signalLinesRef.current = []
      chart.remove()
    }
  }, [symbol, interval])

  useEffect(() => { load() }, [symbol, interval])
  useEffect(() => {
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [symbol, interval])

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

  const selectedTicker = watchTickers.find(t => t.symbol === symbol)

  return (
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* ── Market pulse strip ── */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {overview.btc && (
            <Stat label="BTC" value={`$${fmtPrice(overview.btc.last_price)}`}
              sub={pctText(overview.btc.price_change_pct)} subCls={pctCls(overview.btc.price_change_pct)} />
          )}
          {overview.eth && (
            <Stat label="ETH" value={`$${fmtPrice(overview.eth.last_price)}`}
              sub={pctText(overview.eth.price_change_pct)} subCls={pctCls(overview.eth.price_change_pct)} />
          )}
          <Stat
            label={`Breadth · ${overview.counted_pairs} pairs`}
            value={
              <span className="flex items-center gap-2">
                <span className="text-up flex items-center gap-0.5"><ArrowUpRight size={14} aria-label="advancers" />{overview.advancers}</span>
                <span className="text-down flex items-center gap-0.5"><ArrowDownRight size={14} aria-label="decliners" />{overview.decliners}</span>
              </span>
            }
            sub={overview.advancers >= overview.decliners ? 'risk-on tilt' : 'risk-off tilt'}
            subCls={overview.advancers >= overview.decliners ? 'text-up' : 'text-down'}
          />
          <Stat label="Avg 24h move" value={pctText(overview.avg_change_pct)}
            valueCls={pctCls(overview.avg_change_pct)} sub="liquid USDT pairs" />
          <Stat label="24h turnover" value={fmtVolume(overview.total_quote_volume)} sub="liquid pairs, quote" />
        </div>
      )}

      {/* ── Main grid: watchlist · chart+flow · signal ── */}
      <div className="grid grid-cols-1 xl:grid-cols-[300px_minmax(0,1fr)_320px] gap-3 items-start">
        {/* Watchlist */}
        <section className="card">
          <header className="flex items-center justify-between px-3 pt-3 pb-2">
            <h2 className="panel-title">Watchlist</h2>
            <span className="num text-[10px] text-fg-faint">{watchlist.length}</span>
          </header>
          <div className="px-3 pb-2">
            <SymbolSearchInput value="" onCommit={addToWatchlist} />
          </div>
          <div className="pb-1.5">
            {watchTickers.map(t => {
              const range = t.high - t.low
              const pos = range > 0 ? Math.min(1, Math.max(0, (t.last_price - t.low) / range)) : 0.5
              const r = radar[t.symbol]
              const active = t.symbol === symbol
              return (
                <div key={t.symbol}
                  onClick={() => setSymbol(t.symbol)}
                  className={`group px-3 py-1.5 cursor-pointer border-l-2 transition-colors duration-100 ${
                    active ? 'border-accent bg-raised' : 'border-transparent hover:bg-raised/60'
                  }`}>
                  <div className="flex items-center justify-between gap-1.5">
                    <span className="text-[13px] font-medium text-fg">{t.symbol.replace('USDT', '')}</span>
                    <span className="flex items-center gap-1.5 min-w-0">
                      {r && r.direction !== 'FLAT' && (
                        <span className={`chip !h-4 !px-1 !text-[9px] ${r.direction === 'BUY' ? 'chip-up' : 'chip-down'}`}>
                          {r.direction}
                        </span>
                      )}
                      <span className="num text-[12.5px] text-fg">{fmtPrice(t.last_price)}</span>
                      <span className={`num text-[11.5px] font-medium w-[54px] text-right ${pctCls(t.price_change_pct)}`}>
                        {pctText(t.price_change_pct)}
                      </span>
                      <button onClick={e => { e.stopPropagation(); removeFromWatchlist(t.symbol) }}
                        aria-label={`Remove ${t.symbol} from watchlist`}
                        className="text-fg-faint hover:text-down opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                        <X size={12} />
                      </button>
                    </span>
                  </div>
                  {/* 24h range position */}
                  <div className="mt-1 flex items-center gap-1.5">
                    <div className="relative flex-1 h-0.5 bg-line rounded-full">
                      <div className="absolute top-1/2 -translate-y-1/2 w-1 h-1 rounded-full bg-accent"
                        style={{ left: `calc(${(pos * 100).toFixed(1)}% - 2px)` }} />
                    </div>
                    <span className="num text-[9px] text-fg-faint w-12 text-right">{fmtVolume(t.quote_volume)}</span>
                  </div>
                </div>
              )
            })}
            {watchTickers.length === 0 && (
              <p className="text-xs text-fg-faint text-center py-4">Loading watchlist…</p>
            )}
          </div>
        </section>

        {/* Chart + order flow */}
        <section className="space-y-3 min-w-0">
          <div className="card overflow-hidden">
            <header className="flex items-center gap-3 px-3 py-2 border-b border-line">
              <SymbolSearchInput value={symbol} onCommit={setSymbol} className="w-36" />
              {selectedTicker && (
                <>
                  <span className={`num text-lg font-semibold leading-none ${pctCls(selectedTicker.price_change_pct)}`}>
                    {fmtPrice(selectedTicker.last_price)}
                  </span>
                  <span className={`num text-xs font-medium ${pctCls(selectedTicker.price_change_pct)}`}>
                    {pctText(selectedTicker.price_change_pct)}
                  </span>
                  <span className="hidden lg:flex items-center gap-2 text-[10px] text-fg-faint num">
                    <span>H {fmtPrice(selectedTicker.high)}</span>
                    <span>L {fmtPrice(selectedTicker.low)}</span>
                    <span>{fmtVolume(selectedTicker.quote_volume)}</span>
                  </span>
                </>
              )}
              <div className="ml-auto flex items-center gap-2">
                {loadingOlder && <span className="text-[10px] text-accent">loading history…</span>}
                {!loadingOlder && historyExhausted && <span className="text-[10px] text-fg-faint">full history</span>}
                <div className="flex rounded-md border border-line overflow-hidden">
                  {INTERVALS.map(iv => (
                    <button key={iv} onClick={() => setInterval_(iv)}
                      className={`px-2 h-6 text-[11px] font-medium cursor-pointer transition-colors ${
                        iv === interval ? 'bg-accent-soft text-accent' : 'text-fg-faint hover:text-fg-soft hover:bg-raised'
                      }`}>
                      {iv}
                    </button>
                  ))}
                </div>
              </div>
            </header>
            <div ref={chartRef} />
          </div>

          {/* Order-flow row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <FlowCard title="Order-Book Pressure"
              hint="Resting bid vs ask notional at the top of the book — more bid-side depth means buyers defend below price.">
              {depth ? (
                <>
                  <div className="flex items-center justify-between text-[11px] mb-1 num">
                    <span className="text-up font-medium">Bids {(depth.bid_ratio * 100).toFixed(0)}%</span>
                    <span className="text-down font-medium">{((1 - depth.bid_ratio) * 100).toFixed(0)}% Asks</span>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden bg-bg flex">
                    <div className="bg-up" style={{ width: `${depth.bid_ratio * 100}%` }} />
                    <div className="bg-down flex-1" />
                  </div>
                  <p className="num text-[10px] text-fg-faint mt-2 leading-relaxed">
                    Walls <span className="text-up">${fmtPrice(depth.biggest_bid_wall_price)}</span> ({fmtVolume(depth.biggest_bid_wall_notional)})
                    {' · '}<span className="text-down">${fmtPrice(depth.biggest_ask_wall_price)}</span> ({fmtVolume(depth.biggest_ask_wall_notional)})
                  </p>
                </>
              ) : <Skeleton />}
            </FlowCard>

            <FlowCard title="Aggressive Buy Flow"
              hint="Share of traded volume where the buyer was the aggressor (market orders hitting the ask). Above 50% = buyers attacking.">
              {flow ? (
                <>
                  <p className={`num text-lg font-semibold leading-none ${flow.buy_ratio >= 0.5 ? 'text-up' : 'text-down'}`}>
                    {(flow.buy_ratio * 100).toFixed(1)}%<span className="text-[11px] font-normal text-fg-faint ml-1.5">buyers</span>
                  </p>
                  <div className="flex items-end gap-0.5 h-7 mt-2">
                    {flow.recent_ratios.map((r, i) => (
                      <div key={i} className={`flex-1 rounded-[1px] ${r >= 0.5 ? 'bg-up/70' : 'bg-down/70'}`}
                        style={{ height: `${Math.max(10, r * 100)}%` }} />
                    ))}
                  </div>
                  <p className="text-[10px] text-fg-faint mt-1">last 10 candles · {flow.interval}</p>
                </>
              ) : <Skeleton />}
            </FlowCard>

            <FlowCard title="Funding (Perps)"
              hint="Perpetual futures funding — positive means longs pay shorts (crowded long), negative means shorts pay longs.">
              {funding ? (
                <>
                  <p className={`num text-lg font-semibold leading-none ${funding.funding_rate >= 0 ? 'text-up' : 'text-down'}`}>
                    {(funding.funding_rate * 100).toFixed(4)}%
                  </p>
                  <p className="num text-[10px] text-fg-faint mt-2">
                    ≈ {funding.funding_rate_annualized_pct.toFixed(1)}% annualized
                    · {funding.funding_rate >= 0 ? 'longs paying' : 'shorts paying'}
                  </p>
                  <p className="num text-[10px] text-fg-faint mt-1">mark ${fmtPrice(funding.mark_price)}</p>
                </>
              ) : <Skeleton label="No perp market / loading…" />}
            </FlowCard>
          </div>
        </section>

        {/* Right column: signal + movers */}
        <section className="space-y-3">
          {signal && (
            <SignalCard
              signal={signal}
              chartActive={signalOnChart}
              onCardClick={(sig) => {
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
          )}
          {overview && (
            <div className="card">
              <header className="flex items-center gap-1 px-3 pt-3 pb-2">
                <h2 className="panel-title mr-auto">Movers</h2>
                {(['gainers', 'losers', 'volume'] as const).map(tab => (
                  <button key={tab} onClick={() => setMoversTab(tab)}
                    className={`h-5 px-1.5 rounded text-[10px] font-medium cursor-pointer transition-colors ${
                      moversTab === tab ? 'bg-accent-soft text-accent' : 'text-fg-faint hover:text-fg-soft'
                    }`}>
                    {tab === 'gainers' ? 'Gainers' : tab === 'losers' ? 'Losers' : 'Volume'}
                  </button>
                ))}
              </header>
              <div className="pb-1.5">
                {movers.slice(0, 8).map(t => (
                  <div key={t.symbol} onClick={() => setSymbol(t.symbol)}
                    className="row-hover flex items-center justify-between px-3 py-1.5 cursor-pointer">
                    <span className="text-[12.5px] font-medium text-fg">{t.symbol.replace('USDT', '')}</span>
                    <span className="flex items-center gap-2.5">
                      <span className="num text-[11px] text-fg-faint">{fmtVolume(t.quote_volume)}</span>
                      <span className="num text-[12px] text-fg-soft">${fmtPrice(t.last_price)}</span>
                      <span className={`num text-[11.5px] font-semibold w-[54px] text-right ${pctCls(t.price_change_pct)}`}>
                        {pctText(t.price_change_pct)}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* ── Volume spike scanner ── */}
      <VolumeSpikeScanner symbols={watchlist} onSelect={setSymbol} />

      {error && (
        <div className="card card-pad border-down/40 text-down text-sm">{error}</div>
      )}

      {/* ── Indicators deep-dive ── */}
      {indicators && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <IndicatorPanel ind={indicators} symbol={symbol} />
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, valueCls, sub, subCls }: {
  label: string; value: ReactNode; valueCls?: string; sub?: string; subCls?: string
}) {
  return (
    <div className="card px-3 py-2.5">
      <p className="panel-title mb-1">{label}</p>
      <div className={`num text-[15px] font-semibold leading-tight ${valueCls ?? 'text-fg'}`}>{value}</div>
      {sub && <p className={`text-[10.5px] mt-0.5 ${subCls ?? 'text-fg-faint'}`}>{sub}</p>}
    </div>
  )
}

function FlowCard({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <div className="card px-3 py-2.5">
      <p className="panel-title mb-2 flex items-center gap-1">
        {title}
        <span title={hint} className="cursor-help text-fg-faint"><Info size={11} aria-label={hint} /></span>
      </p>
      {children}
    </div>
  )
}

function Skeleton({ label }: { label?: string }) {
  return <p className="text-[11px] text-fg-faint">{label ?? 'Loading…'}</p>
}
