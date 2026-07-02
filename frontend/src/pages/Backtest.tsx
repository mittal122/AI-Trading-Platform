import { Fragment, useEffect, useState } from 'react'
import {
  getBacktestHistory, runAndRecordBacktest, getPortfolioAnalytics,
  deleteBacktestRun, deleteAllBacktestRuns,
} from '../api/client'
import type { BacktestRunItem, PortfolioAnalytics } from '../api/client'
import PortfolioSummary from '../components/PortfolioSummary'
import { usePersistedState } from '../hooks/usePersistedState'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']
const INTERVALS = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
const PAGE_SIZE_OPTIONS = [
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: 'All', value: 1000 },
]

function DetailRow({ r }: { r: BacktestRunItem }) {
  return (
    <tr className="bg-[#0f1117]/50">
      <td colSpan={10} className="px-4 py-3">
        <div className="grid grid-cols-3 md:grid-cols-7 gap-3 text-xs">
          <div><p className="text-slate-500">Winning</p><p className="text-green-400 font-medium">{r.winning_trades}</p></div>
          <div><p className="text-slate-500">Losing</p><p className="text-red-400 font-medium">{r.losing_trades}</p></div>
          <div><p className="text-slate-500">Avg Win</p><p className="text-white font-medium">${r.avg_win.toFixed(2)}</p></div>
          <div><p className="text-slate-500">Avg Loss</p><p className="text-white font-medium">${r.avg_loss.toFixed(2)}</p></div>
          <div><p className="text-slate-500">Expectancy</p><p className="text-white font-medium">${r.expectancy.toFixed(2)}</p></div>
          <div><p className="text-slate-500">Sortino</p><p className="text-white font-medium">{r.sortino_ratio.toFixed(3)}</p></div>
          <div><p className="text-slate-500">Calmar</p><p className="text-white font-medium">{r.calmar_ratio.toFixed(3)}</p></div>
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
  if (!rows.length) return <p className="text-slate-500 text-sm text-center py-6">No runs yet</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-500 border-b border-[#2a2d3e] text-left">
            <th className="pb-2 pr-4 w-4"></th>
            <th className="pb-2 pr-4">Strategy</th><th className="pb-2 pr-4">Symbol</th>
            <th className="pb-2 pr-4">Interval</th><th className="pb-2 pr-4">Candles</th>
            <th className="pb-2 pr-4">Return</th><th className="pb-2 pr-4">Trades</th>
            <th className="pb-2 pr-4">Win%</th><th className="pb-2 pr-4">Sharpe</th>
            <th className="pb-2 pr-4">Time</th><th className="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <Fragment key={r.id}>
              <tr className="border-b border-[#2a2d3e]/50 hover:bg-[#0f1117]/30">
                <td className="py-2 pr-2">
                  <button onClick={() => toggleExpand(r.id)} className="text-slate-500 hover:text-indigo-400 w-5">
                    {expanded.has(r.id) ? '▾' : '▸'}
                  </button>
                </td>
                <td className="py-2 pr-4 font-medium">{r.strategy}</td>
                <td className="py-2 pr-4 text-slate-400">{r.symbol}</td>
                <td className="py-2 pr-4 text-slate-400">{r.interval}</td>
                <td className="py-2 pr-4 text-slate-400">{r.limit}</td>
                <td className={`py-2 pr-4 font-semibold ${r.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {r.total_return >= 0 ? '+' : ''}{r.total_return.toFixed(2)}%
                </td>
                <td className="py-2 pr-4 text-slate-400">{r.total_trades}</td>
                <td className="py-2 pr-4 text-slate-400">{r.win_rate.toFixed(1)}%</td>
                <td className="py-2 pr-4 text-slate-400">{r.sharpe_ratio.toFixed(2)}</td>
                <td className="py-2 pr-4 text-slate-600 text-xs">{new Date(r.created_at).toLocaleString()}</td>
                <td className="py-2">
                  <button onClick={() => onDeleteRow(r.id)}
                    className="text-slate-600 hover:text-red-400 text-xs px-2 py-0.5 rounded border border-transparent hover:border-red-500/30">
                    ✕
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
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-white">Backtest</h1>

      {/* Config */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Symbol</label>
            <input value={symbol} onChange={e => setSymbol(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Strategy</label>
            <select value={strategy} onChange={e => setStrategy(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none">
              {STRATEGIES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Interval</label>
            <select value={interval} onChange={e => setInterval(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none">
              {INTERVALS.map(i => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Candles</label>
            <input type="number" value={limit} onChange={e => setLimit(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none" />
          </div>
          <div className="flex items-end gap-2">
            <button onClick={run} disabled={running || multiRunning}
              className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
              {running ? 'Running…' : 'Run Backtest'}
            </button>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-[#2a2d3e]">
          <button onClick={runAllTimeframes} disabled={running || multiRunning}
            className="w-full py-2 bg-purple-600/80 hover:bg-purple-600 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
            {multiRunning ? multiProgress : `Backtest All Timeframes (${strategy} · ${symbol.toUpperCase()})`}
          </button>
          <p className="text-xs text-slate-600 mt-1">Runs {strategy} on {symbol.toUpperCase()} across every interval — see which timeframe performs best.</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>
      )}

      {analytics && (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Results</h2>
          <PortfolioSummary data={analytics} />
        </div>
      )}

      {/* Multi-timeframe results */}
      {multiResults.length > 0 && (
        <div className="bg-[#1a1d27] border border-purple-500/30 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-purple-300 mb-1">All-Timeframe Results — {strategy} on {symbol.toUpperCase()}</h2>
          <p className="text-xs text-slate-500 mb-4">Sorted by return. Click a row to expand full detail.</p>
          <HistoryTable rows={multiResults} onDeleteRow={() => {}} expanded={multiExpanded} toggleExpand={toggleMultiExpand} />
        </div>
      )}

      {/* History */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="text-sm font-semibold text-slate-300">Recent Runs ({total} total)</h2>
          <div className="flex items-center gap-3">
            <label className="text-xs text-slate-500">Show:</label>
            <select value={pageSize} onChange={e => setPageSize(Number(e.target.value))}
              className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1 text-xs text-white outline-none">
              {PAGE_SIZE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <button onClick={handleDeleteAll} disabled={total === 0}
              className={`text-xs px-3 py-1.5 rounded-lg border disabled:opacity-40 transition-colors ${
                confirmDeleteAll
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20'
              }`}>
              {confirmDeleteAll ? 'Click again to confirm' : 'Delete All History'}
            </button>
          </div>
        </div>
        <HistoryTable rows={history} onDeleteRow={handleDeleteRow} expanded={expanded} toggleExpand={toggleExpand} />
      </div>
    </div>
  )
}
