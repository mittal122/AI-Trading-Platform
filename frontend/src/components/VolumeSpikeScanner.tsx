import { useCallback, useEffect, useRef, useState } from 'react'
import { Info, RefreshCw, ArrowUp, ArrowDown, X } from 'lucide-react'
import { getVolumeScan, getVolumeScanMarket } from '../api/client'
import type { VolumeScanRow } from '../api/client'
import { usePersistedState } from '../hooks/usePersistedState'

const INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d'] as const
const REFRESH_MS = 20_000
const MARKET_TOP = 300
const MARKET_LIMIT = 40
type Mode = 'watchlist' | 'market'

// Compact count/volume formatting — base-asset volume and raw order counts,
// not USD, so no "$" prefix (unlike the movers cards).
function fmtNum(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`
  return v.toFixed(v >= 1 ? 0 : 2)
}

function fmtPrice(p: number): string {
  return p >= 1000 ? p.toLocaleString(undefined, { maximumFractionDigits: 2 })
    : p >= 1 ? p.toFixed(2) : p.toFixed(6)
}

function fmtTime(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '—'
    : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

// Spike-ratio intensity ramp: >=3x is a hard spike, >=2x notable, >=1.5x warming.
function spikeCls(r: number): string {
  if (r >= 3) return 'chip-warn font-bold'
  if (r >= 2) return 'chip-warn'
  if (r >= 1.5) return 'chip-muted !text-accent'
  return 'chip-muted'
}

// Buy/sell classification of the spike candle from its taker-buy share.
// >55% aggressive buyers, <45% aggressive sellers, else a balanced tug-of-war.
function FlowBadge({ buyRatio }: { buyRatio: number }) {
  const pct = Math.round(buyRatio * 100)
  const title = `${pct}% of this candle's volume was aggressive buying`
  if (buyRatio >= 0.55) {
    return (
      <span className="chip chip-up num" title={title}>
        <ArrowUp size={10} aria-label="aggressive buying" />Buy {pct}%
      </span>
    )
  }
  if (buyRatio <= 0.45) {
    return (
      <span className="chip chip-down num" title={title}>
        <ArrowDown size={10} aria-label="aggressive selling" />Sell {100 - pct}%
      </span>
    )
  }
  return <span className="chip chip-muted num" title={title}>Mixed {pct}%</span>
}

export default function VolumeSpikeScanner({ symbols, onSelect }: {
  symbols: string[]; onSelect?: (symbol: string) => void
}) {
  const [mode, setMode] = usePersistedState<Mode>('dashboard.volscan.mode', 'watchlist')
  const [interval, setInterval_] = usePersistedState('dashboard.volscan.interval', '5m')
  const [window, setWindow] = usePersistedState('dashboard.volscan.window', 20)
  const [rows, setRows] = useState<VolumeScanRow[]>([])
  const [scanned, setScanned] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [updatedAt, setUpdatedAt] = useState<string>('')
  const [showHelp, setShowHelp] = useState(false)

  const isMarket = mode === 'market'
  const symbolsKey = symbols.join(',')

  const loadWatchlist = useCallback(async () => {
    if (symbols.length === 0) { setRows([]); return }
    setLoading(true)
    try {
      const { data } = await getVolumeScan(symbols, interval, window)
      setRows(data.rows); setScanned(null)
      setUpdatedAt(new Date().toLocaleTimeString())
    } catch { /* keep last-good rows on a transient error */ } finally { setLoading(false) }
  }, [symbolsKey, interval, window]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadMarket = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getVolumeScanMarket(interval, window, MARKET_TOP, MARKET_LIMIT)
      setRows(data.rows); setScanned(data.scanned ?? null)
      setUpdatedAt(new Date().toLocaleTimeString())
    } catch { /* keep last-good rows */ } finally { setLoading(false) }
  }, [interval, window])

  // Watchlist mode auto-refreshes (cheap). Market mode is heavy (one klines
  // call per coin across 300 coins) — run it once when the user switches into
  // it or changes timeframe, then leave it to the manual Scan button. Window
  // edits apply on the next Scan, not on every keystroke.
  const loadRef = useRef(loadWatchlist)
  loadRef.current = isMarket ? loadMarket : loadWatchlist
  useEffect(() => {
    setRows([]); setScanned(null)
    loadRef.current()
    if (isMarket) return                       // no polling for the market scan
    const id = setInterval(() => loadRef.current(), REFRESH_MS)
    return () => clearInterval(id)
  }, [mode, interval, symbolsKey]) // eslint-disable-line react-hooks/exhaustive-deps

  const rescan = isMarket ? loadMarket : loadWatchlist

  return (
    <div className="card card-pad">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="panel-title">Volume Spike Scanner</h2>
        <button onClick={() => setShowHelp(v => !v)} aria-label="What am I looking at?"
          className="text-fg-faint hover:text-fg-soft cursor-pointer" title="What am I looking at?">
          <Info size={12} />
        </button>

        {/* Mode toggle */}
        <div className="flex rounded-md overflow-hidden border border-line ml-1">
          {(['watchlist', 'market'] as const).map(m => (
            <button key={m} onClick={() => setMode(m)}
              className={`text-[11px] font-medium px-2.5 h-6 cursor-pointer transition-colors ${
                mode === m ? 'bg-accent-soft text-accent' : 'text-fg-faint hover:text-fg-soft hover:bg-raised'}`}>
              {m === 'watchlist' ? 'Watchlist' : 'Whole market (top 300)'}
            </button>
          ))}
        </div>
        <span className="text-[10px] text-fg-faint">
          {isMarket ? 'ranked by surge × liquidity — where the order flow just jumped' : 'order push across your watchlist · hottest first'}
        </span>

        <div className="ml-auto flex items-center gap-2">
          <select value={interval} onChange={e => setInterval_(e.target.value)}
            className="input input-mono !h-6 text-[11px]">
            {INTERVALS.map(iv => <option key={iv} value={iv}>{iv}</option>)}
          </select>
          <label className="text-[10px] text-fg-faint">window
            <input type="number" min={5} max={200} value={window}
              onChange={e => setWindow(Math.max(5, Math.min(200, Number(e.target.value) || 20)))}
              className="input input-mono !h-6 text-[11px] ml-1 w-14" />
          </label>
          <button onClick={rescan} disabled={loading} aria-label={isMarket ? 'Scan market' : 'Refresh scan'}
            className="btn !h-6 text-[11px]">
            {loading
              ? (isMarket ? 'Scanning…' : <RefreshCw size={12} className="animate-spin" />)
              : isMarket ? 'Scan market' : <RefreshCw size={12} />}
          </button>
        </div>
      </div>

      {showHelp && (
        <div className="mb-3 text-[11px] text-fg-soft bg-raised border border-line rounded-lg p-3 space-y-1">
          <p><span className="text-fg">Whole market</span> — scans the 300 most-liquid coins and ranks by <span className="text-fg">Score = surge × liquidity</span>, so coins whose order flow just jumped (and that you can actually trade) float to the top.</p>
          <p><span className="text-fg">Vol (window)</span> — the last closed candle's traded volume: how much got pushed right now.</p>
          <p><span className="text-fg">Avg Vol</span> — mean volume over the previous {window} candles (the "normal" for this coin/timeframe).</p>
          <p><span className="text-fg">Spike×</span> — Vol ÷ Avg Vol. Above 2× means a real surge; 3×+ is a hard spike.</p>
          <p><span className="text-fg">Flow</span> — was this candle's volume aggressive <span className="text-up">buying</span> or <span className="text-down">selling</span>? From taker-buy share: Buy ≥55%, Sell ≤45%, Mixed in between. This is who was hitting the market (impatient market orders), i.e. who drove the spike.</p>
          <p><span className="text-fg">Orders</span> — number of trades that printed on that candle (how many orders were placed).</p>
          <p><span className="text-fg">Max Push</span> — the single biggest candle's volume in the window (largest order push), as a × of the average.</p>
          <p className="text-fg-faint">Uses the last <em>closed</em> candle — the live candle's volume is partial and would hide real spikes. The market scan is heavy (300 calls) so it runs on demand, not on a timer.</p>
        </div>
      )}

      {(!isMarket && symbols.length === 0) ? (
        <p className="text-xs text-fg-faint text-center py-4">Add coins to your watchlist above to scan them.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left">
                <th className="th">Time</th>
                <th className="th">Symbol</th>
                <th className="th text-right">LTP</th>
                <th className="th">TF</th>
                <th className="th text-right">Vol (window)</th>
                <th className="th text-right">Avg Vol</th>
                <th className="th text-right">Spike×</th>
                <th className="th text-center">Flow</th>
                <th className="th text-right">Orders</th>
                <th className="th text-right">Max Push</th>
                {isMarket && <th className="th text-right">Score</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.symbol}
                  onClick={() => !r.error && onSelect?.(r.symbol)}
                  className={r.error ? '' : 'row-hover cursor-pointer'}>
                  {r.error ? (
                    <>
                      <td className="td num text-fg-faint">—</td>
                      <td className="td font-medium">{r.symbol.replace('USDT', '')}</td>
                      <td className="td text-down/70" colSpan={isMarket ? 9 : 8}>
                        <span className="inline-flex items-center gap-1">
                          <X size={11} aria-label="scan error" />{r.error}
                        </span>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="td num text-fg-faint">{fmtTime(r.time)}</td>
                      <td className="td font-medium text-fg">{r.symbol.replace('USDT', '')}</td>
                      <td className="td num text-right">{fmtPrice(r.ltp)}</td>
                      <td className="td num text-fg-faint">{r.interval}</td>
                      <td className="td num text-right">{fmtNum(r.volume_window)}</td>
                      <td className="td num text-right text-fg-faint">{fmtNum(r.volume_average)}</td>
                      <td className="td text-right">
                        <span className={`chip num ${spikeCls(r.spike_ratio)}`}>
                          {r.spike_ratio.toFixed(2)}×
                        </span>
                      </td>
                      <td className="td text-center">
                        <FlowBadge buyRatio={r.buy_ratio} />
                      </td>
                      <td className="td num text-right">{fmtNum(r.orders)}</td>
                      <td className="td num text-right text-fg-faint" title={`peak candle volume ${fmtNum(r.max_push_volume)}`}>
                        {r.max_push_ratio.toFixed(1)}×
                      </td>
                      {isMarket && (
                        <td className="td num text-right font-semibold text-accent"
                          title={`24h volume $${(r.quote_volume_24h ?? 0).toLocaleString()}`}>
                          {(r.blended_score ?? 0).toFixed(2)}
                        </td>
                      )}
                    </>
                  )}
                </tr>
              ))}
              {rows.length === 0 && !loading && (
                <tr><td colSpan={isMarket ? 11 : 10} className="td py-4 text-center text-fg-faint">
                  {isMarket ? 'Click “Scan market” to rank the top 300 coins.' : 'No data.'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {updatedAt && (
        <p className="num text-[10px] text-fg-faint mt-2 text-right">
          {isMarket
            ? `scanned ${scanned ?? '—'} coins · updated ${updatedAt} · on demand`
            : `updated ${updatedAt} · auto every 20s`}
        </p>
      )}
    </div>
  )
}
