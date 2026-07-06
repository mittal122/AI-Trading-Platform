import { useCallback, useEffect, useRef, useState } from 'react'
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

// Spike-ratio colour ramp: >=3x is a hard spike, >=2x notable, >=1.5x warming.
function spikeCls(r: number): string {
  if (r >= 3) return 'text-red-400 bg-red-500/10 border-red-500/40'
  if (r >= 2) return 'text-amber-400 bg-amber-500/10 border-amber-500/30'
  if (r >= 1.5) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
  return 'text-slate-400 bg-slate-500/10 border-slate-500/20'
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
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold text-slate-300">Volume Spike Scanner</h2>
        <button onClick={() => setShowHelp(v => !v)}
          className="text-slate-600 hover:text-slate-300 text-xs" title="What am I looking at?">ⓘ</button>

        {/* Mode toggle */}
        <div className="flex rounded-lg overflow-hidden border border-[#2a2d3e] ml-1">
          {(['watchlist', 'market'] as const).map(m => (
            <button key={m} onClick={() => setMode(m)}
              className={`text-xs px-2.5 py-1 transition-colors ${
                mode === m ? 'bg-indigo-500/20 text-indigo-300' : 'bg-[#0f1117] text-slate-500 hover:text-white'}`}>
              {m === 'watchlist' ? 'Watchlist' : 'Whole market (top 300)'}
            </button>
          ))}
        </div>
        <span className="text-[10px] text-slate-600">
          {isMarket ? 'ranked by surge × liquidity — where the order flow just jumped' : 'order push across your watchlist · hottest first'}
        </span>

        <div className="ml-auto flex items-center gap-2">
          <select value={interval} onChange={e => setInterval_(e.target.value)}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg text-xs text-slate-300 px-2 py-1">
            {INTERVALS.map(iv => <option key={iv} value={iv}>{iv}</option>)}
          </select>
          <label className="text-[10px] text-slate-600">window
            <input type="number" min={5} max={200} value={window}
              onChange={e => setWindow(Math.max(5, Math.min(200, Number(e.target.value) || 20)))}
              className="ml-1 w-14 bg-[#0f1117] border border-[#2a2d3e] rounded-lg text-xs text-slate-300 px-2 py-1" />
          </label>
          <button onClick={rescan} disabled={loading}
            className="text-xs px-2.5 py-1 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-500/30 disabled:opacity-50">
            {loading ? (isMarket ? 'Scanning…' : '…') : isMarket ? 'Scan market' : '↻'}
          </button>
        </div>
      </div>

      {showHelp && (
        <div className="mb-3 text-[11px] text-slate-400 bg-[#0f1117] border border-[#2a2d3e] rounded-lg p-3 space-y-1">
          <p><span className="text-slate-300">Whole market</span> — scans the 300 most-liquid coins and ranks by <span className="text-slate-300">Score = surge × liquidity</span>, so coins whose order flow just jumped (and that you can actually trade) float to the top.</p>
          <p><span className="text-slate-300">Vol (window)</span> — the last closed candle's traded volume: how much got pushed right now.</p>
          <p><span className="text-slate-300">Avg Vol</span> — mean volume over the previous {window} candles (the "normal" for this coin/timeframe).</p>
          <p><span className="text-slate-300">Spike×</span> — Vol ÷ Avg Vol. Above 2× means a real surge; 3×+ is a hard spike.</p>
          <p><span className="text-slate-300">Orders</span> — number of trades that printed on that candle (how many orders were placed).</p>
          <p><span className="text-slate-300">Max Push</span> — the single biggest candle's volume in the window (largest order push), as a × of the average.</p>
          <p className="text-slate-600">Uses the last <em>closed</em> candle — the live candle's volume is partial and would hide real spikes. The market scan is heavy (300 calls) so it runs on demand, not on a timer.</p>
        </div>
      )}

      {(!isMarket && symbols.length === 0) ? (
        <p className="text-xs text-slate-600 text-center py-4">Add coins to your watchlist above to scan them.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-600 text-left border-b border-[#2a2d3e]">
                <th className="py-2 pr-3 font-medium">Time</th>
                <th className="py-2 pr-3 font-medium">Symbol</th>
                <th className="py-2 pr-3 font-medium text-right">LTP</th>
                <th className="py-2 pr-3 font-medium">TF</th>
                <th className="py-2 pr-3 font-medium text-right">Vol (window)</th>
                <th className="py-2 pr-3 font-medium text-right">Avg Vol</th>
                <th className="py-2 pr-3 font-medium text-right">Spike×</th>
                <th className="py-2 pr-3 font-medium text-right">Orders</th>
                <th className="py-2 pr-3 font-medium text-right">Max Push</th>
                {isMarket && <th className="py-2 font-medium text-right">Score</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.symbol}
                  onClick={() => !r.error && onSelect?.(r.symbol)}
                  className={`border-b border-[#20232f] ${r.error ? '' : 'cursor-pointer hover:bg-[#232736]'} transition-colors`}>
                  {r.error ? (
                    <>
                      <td className="py-2 pr-3 text-slate-600 tabular-nums">—</td>
                      <td className="py-2 pr-3 font-medium text-slate-400">{r.symbol.replace('USDT', '')}</td>
                      <td className="py-2 pr-3 text-red-400/70" colSpan={isMarket ? 8 : 7}>✕ {r.error}</td>
                    </>
                  ) : (
                    <>
                      <td className="py-2 pr-3 text-slate-500 tabular-nums">{fmtTime(r.time)}</td>
                      <td className="py-2 pr-3 font-medium text-white">{r.symbol.replace('USDT', '')}</td>
                      <td className="py-2 pr-3 text-right text-slate-300 tabular-nums">{fmtPrice(r.ltp)}</td>
                      <td className="py-2 pr-3 text-slate-500">{r.interval}</td>
                      <td className="py-2 pr-3 text-right text-slate-300 tabular-nums">{fmtNum(r.volume_window)}</td>
                      <td className="py-2 pr-3 text-right text-slate-500 tabular-nums">{fmtNum(r.volume_average)}</td>
                      <td className="py-2 pr-3 text-right">
                        <span className={`inline-block px-2 py-0.5 rounded-md border font-semibold tabular-nums ${spikeCls(r.spike_ratio)}`}>
                          {r.spike_ratio.toFixed(2)}×
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-right text-slate-300 tabular-nums">{fmtNum(r.orders)}</td>
                      <td className="py-2 pr-3 text-right text-slate-400 tabular-nums" title={`peak candle volume ${fmtNum(r.max_push_volume)}`}>
                        {r.max_push_ratio.toFixed(1)}×
                      </td>
                      {isMarket && (
                        <td className="py-2 text-right font-semibold text-indigo-300 tabular-nums"
                          title={`24h volume $${(r.quote_volume_24h ?? 0).toLocaleString()}`}>
                          {(r.blended_score ?? 0).toFixed(2)}
                        </td>
                      )}
                    </>
                  )}
                </tr>
              ))}
              {rows.length === 0 && !loading && (
                <tr><td colSpan={isMarket ? 10 : 9} className="py-4 text-center text-slate-600">
                  {isMarket ? 'Click “Scan market” to rank the top 300 coins.' : 'No data.'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {updatedAt && (
        <p className="text-[10px] text-slate-600 mt-2 text-right">
          {isMarket
            ? `scanned ${scanned ?? '—'} coins · updated ${updatedAt} · on demand`
            : `updated ${updatedAt} · auto every 20s`}
        </p>
      )}
    </div>
  )
}
