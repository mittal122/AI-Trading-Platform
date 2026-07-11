import { Fragment, useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Play, Trash2 } from 'lucide-react'
import {
  getBacktestHistory, runAndRecordBacktest, getPortfolioAnalytics,
  deleteBacktestRun, deleteAllBacktestRuns,
} from '../api/client'
import type { BacktestRunItem, PortfolioAnalytics } from '../api/client'
import PortfolioSummary from '../components/PortfolioSummary'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { usePersistedState } from '../hooks/usePersistedState'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']
const INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
const PAGE_SIZE_OPTIONS = [
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: 'All', value: 1000 },
]

const signCls = (v: number) => (v >= 0 ? 'text-up' : 'text-down')

function DetailRow({ r }: { r: BacktestRunItem }) {
  return (
    <tr className="bg-raised">
      <td colSpan={12} className="px-4 py-3">
        <div className="grid grid-cols-3 md:grid-cols-7 gap-3 text-xs">
          <div><p className="text-fg-faint">Winning</p><p className="num text-up font-medium">{r.winning_trades}</p></div>
          <div><p className="text-fg-faint">Losing</p><p className="num text-down font-medium">{r.losing_trades}</p></div>
          <div><p className="text-fg-faint">Avg Win</p><p className="num text-fg font-medium">${r.avg_win.toFixed(2)}</p></div>
          <div><p className="text-fg-faint">Avg Loss</p><p className="num text-fg font-medium">${r.avg_loss.toFixed(2)}</p></div>
          <div><p className="text-fg-faint">Expectancy</p><p className="num text-fg font-medium">${r.expectancy.toFixed(2)}</p></div>
          <div><p className="text-fg-faint">Sortino</p><p className="num text-fg font-medium">{r.sortino_ratio.toFixed(3)}</p></div>
          <div><p className="text-fg-faint">Calmar</p><p className="num text-fg font-medium">{r.calmar_ratio.toFixed(3)}</p></div>
        </div>
      </td>
    </tr>
  )
}

function HistoryTable({ rows, onDeleteRow, expanded, toggleExpand }: {
  rows: BacktestRunItem[]
  onDeleteRow: (id: number) => void
  expanded: Set<number>
  toggleExpand: (id: number) => void
}) {
  if (!rows.length) return <p className="text-fg-faint text-sm text-center py-6">No runs yet</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12.5px]">
        <thead>
          <tr>
            <th className="th w-4"></th>
            <th className="th">Strategy</th><th className="th">Symbol</th>
            <th className="th">Interval</th><th className="th">Candles</th>
            <th className="th">Return</th><th className="th">Trades</th>
            <th className="th">Win%</th><th className="th">Avg Time to Win</th>
            <th className="th">Sharpe</th>
            <th className="th">Time</th><th className="th"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <Fragment key={r.id}>
              <tr className="row-hover border-b border-line/50">
                <td className="td pr-2">
                  <button onClick={() => toggleExpand(r.id)}
                    aria-label={expanded.has(r.id) ? 'Collapse detail' : 'Expand detail'}
                    className="text-fg-faint hover:text-accent w-5 cursor-pointer">
                    {expanded.has(r.id) ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                  </button>
                </td>
                <td className="td font-medium text-fg">{r.strategy}</td>
                <td className="td text-fg-soft">{r.symbol}</td>
                <td className="td num text-fg-soft">{r.interval}</td>
                <td className="td num text-fg-soft">{r.limit}</td>
                <td className={`td num font-semibold ${signCls(r.total_return)}`}>
                  {r.total_return >= 0 ? '+' : ''}{r.total_return.toFixed(2)}%
                </td>
                <td className="td num text-fg-soft">{r.total_trades}</td>
                <td className={`td num ${signCls(r.win_rate - 50)}`}>{r.win_rate.toFixed(1)}%</td>
                <td className="td num text-fg-soft">{r.avg_time_to_win_display || '—'}</td>
                <td className="td num text-fg-soft">{r.sharpe_ratio.toFixed(2)}</td>
                <td className="td num text-fg-faint text-xs">{new Date(r.created_at).toLocaleString()}</td>
                <td className="td">
                  <button onClick={() => onDeleteRow(r.id)} aria-label="Delete run"
                    className="text-fg-faint hover:text-down px-1.5 py-0.5 cursor-pointer">
                    <Trash2 size={13} />
                  </button>
                </td>
              </tr>
              {expanded.has(r.id) && <DetailRow r={r} />}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Backtest() {
  const [strategy, setStrategy] = usePersistedState('backtest.strategy', 'rsi')
  const [symbol, setSymbol]     = usePersistedState('backtest.symbol', 'BTCUSDT')
  const [interval, setInterval] = usePersistedState('backtest.interval', '5m')
  const [limit, setLimit]       = usePersistedState('backtest.limit', '300')
  const [pageSize, setPageSize] = usePersistedState('backtest.pageSize', 50)

  const [running, setRunning]   = useState(false)
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null)
  const [history, setHistory]   = useState<BacktestRunItem[]>([])
  const [total, setTotal]       = useState(0)
  const [error, setError]       = useState('')
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false)

  const [multiRunning, setMultiRunning] = useState(false)
  const [multiProgress, setMultiProgress] = useState('')
  const [multiResults, setMultiResults] = useState<BacktestRunItem[]>([])
  const [multiExpanded, setMultiExpanded] = useState<Set<number>>(new Set())

  async function loadHistory() {
    try {
      const res = await getBacktestHistory({ limit: pageSize })
      setHistory(res.data.runs)
      setTotal(res.data.total)
    } catch {}
  }

  async function run() {
    setRunning(true); setError(''); setAnalytics(null)
    try {
      await runAndRecordBacktest({ strategy, symbol: symbol.toUpperCase(), interval, limit: Number(limit) })
      const res = await getPortfolioAnalytics(strategy, symbol.toUpperCase(), interval, Number(limit))
      setAnalytics(res.data)
      await loadHistory()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Backtest failed')
    } finally {
      setRunning(false)
    }
  }

  async function runAllTimeframes() {
    setMultiRunning(true); setError(''); setMultiResults([])
    const results: BacktestRunItem[] = []
    for (let i = 0; i < INTERVALS.length; i++) {
      const tf = INTERVALS[i]
      setMultiProgress(`Running ${tf} (${i + 1}/${INTERVALS.length})…`)
      try {
        const res = await runAndRecordBacktest({ strategy, symbol: symbol.toUpperCase(), interval: tf, limit: Number(limit) })
        results.push(res.data)
      } catch {
        // skip timeframes that fail (e.g. not enough candles) — continue with the rest
      }
    }
    setMultiResults(results.sort((a, b) => b.total_return - a.total_return))
    setMultiProgress('')
    setMultiRunning(false)
    await loadHistory()
  }

  async function handleDeleteRow(id: number) {
    try {
      await deleteBacktestRun(id)
      await loadHistory()
    } catch {}
  }

  async function handleDeleteAll() {
    if (!confirmDeleteAll) {
      setConfirmDeleteAll(true)
      setTimeout(() => setConfirmDeleteAll(false), 4000)
      return
    }
    try {
      await deleteAllBacktestRuns()
      setConfirmDeleteAll(false)
      await loadHistory()
    } catch {}
  }

  function toggleExpand(id: number) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleMultiExpand(id: number) {
    setMultiExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  useEffect(() => { loadHistory() }, [pageSize])

  return (
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* Config toolbar */}
      <div className="card card-pad">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div>
            <label className="field-label mb-1 block">Symbol</label>
            <SymbolSearchInput value={symbol} onCommit={setSymbol} />
          </div>
          <div>
            <label className="field-label mb-1 block">Strategy</label>
            <select value={strategy} onChange={e => setStrategy(e.target.value)} className="input w-full">
              {STRATEGIES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="field-label mb-1 block">Interval</label>
            <select value={interval} onChange={e => setInterval(e.target.value)} className="input w-full">
              {INTERVALS.map(i => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div>
            <label className="field-label mb-1 block">Candles</label>
            <input type="number" value={limit} onChange={e => setLimit(e.target.value)} className="input input-mono w-full" />
          </div>
          <div className="flex items-end gap-2">
            <button onClick={run} disabled={running || multiRunning}
              className="btn btn-primary flex-1">
              <Play size={13} aria-label="Run backtest" />
              {running ? 'Running…' : 'Run Backtest'}
            </button>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-line">
          <button onClick={runAllTimeframes} disabled={running || multiRunning}
            className="btn w-full">
            {multiRunning ? multiProgress : `Backtest All Timeframes (${strategy} · ${symbol.toUpperCase()})`}
          </button>
          <p className="text-xs text-fg-faint mt-1">Runs {strategy} on {symbol.toUpperCase()} across every interval — see which timeframe performs best.</p>
        </div>
      </div>

      {error && (
        <div className="card card-pad border-down/40 text-down text-sm">{error}</div>
      )}

      {analytics && (
        <div className="card">
          <header className="flex items-center justify-between px-3 pt-3 pb-2">
            <h2 className="panel-title">Results</h2>
          </header>
          <div className="px-3 pb-3">
            <PortfolioSummary data={analytics} />
          </div>
        </div>
      )}

      {/* Multi-timeframe results */}
      {multiResults.length > 0 && (
        <div className="card">
          <header className="px-3 pt-3 pb-2">
            <h2 className="panel-title">All-Timeframe Results — {strategy} on {symbol.toUpperCase()}</h2>
            <p className="text-xs text-fg-faint mt-0.5">Sorted by return. Click a row to expand full detail.</p>
          </header>
          <div className="px-3 pb-3">
            <HistoryTable rows={multiResults} onDeleteRow={() => {}} expanded={multiExpanded} toggleExpand={toggleMultiExpand} />
          </div>
        </div>
      )}

      {/* History */}
      <div className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2 flex-wrap gap-3">
          <h2 className="panel-title">Recent Runs <span className="num text-fg-faint">({total} total)</span></h2>
          <div className="flex items-center gap-2">
            <label className="field-label">Show:</label>
            <select value={pageSize} onChange={e => setPageSize(Number(e.target.value))}
              className="input !h-6 !px-2 text-xs">
              {PAGE_SIZE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <button onClick={handleDeleteAll} disabled={total === 0}
              className={`btn btn-danger-outline !h-6 text-xs ${confirmDeleteAll ? '!bg-down !text-fg' : ''}`}>
              <Trash2 size={12} aria-label="Delete all history" />
              {confirmDeleteAll ? 'Click again to confirm' : 'Delete All History'}
            </button>
          </div>
        </header>
        <div className="px-3 pb-3">
          <HistoryTable rows={history} onDeleteRow={handleDeleteRow} expanded={expanded} toggleExpand={toggleExpand} />
        </div>
      </div>
    </div>
  )
}
