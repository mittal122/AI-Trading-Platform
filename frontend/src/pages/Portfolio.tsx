import { useEffect, useState } from 'react'
import { getPortfolioAnalytics, getTradeHistory } from '../api/client'
import type { PortfolioAnalytics, TradeHistoryItem } from '../api/client'
import PortfolioSummary from '../components/PortfolioSummary'
import TradeTable from '../components/TradeTable'

export default function Portfolio() {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null)
  const [trades, setTrades]       = useState<TradeHistoryItem[]>([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(true)
  const [strategy, setStrategy]   = useState('rsi')
  const [modeFilter, setModeFilter] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [anlRes, trdRes] = await Promise.all([
        getPortfolioAnalytics(strategy, 'BTCUSDT', '5m', 300),
        getTradeHistory({ mode: modeFilter || undefined, limit: 50 }),
      ])
      setAnalytics(anlRes.data)
      setTrades(trdRes.data.trades)
      setTotal(trdRes.data.total)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [strategy, modeFilter])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Portfolio</h1>
        <div className="flex gap-2">
          {['rsi','ema','macd','breakout','supertrend','cta_trend','turtle','engulfing_scalp'].map(s => (
            <button key={s} onClick={() => setStrategy(s)}
              className={`text-xs px-3 py-1 rounded-lg border transition-colors ${strategy === s
                ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
                : 'text-slate-400 border-[#2a2d3e] hover:border-indigo-500/30'
              }`}>{s}</button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-slate-500 text-sm">Loading analytics…</p>
      ) : analytics ? (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
          <PortfolioSummary data={analytics} />
        </div>
      ) : null}

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Trade History ({total})</h2>
          <div className="flex gap-2">
            {['', 'PAPER', 'LIVE', 'BACKTEST'].map(m => (
              <button key={m} onClick={() => setModeFilter(m)}
                className={`text-xs px-2 py-1 rounded border transition-colors ${modeFilter === m
                  ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
                  : 'text-slate-500 border-[#2a2d3e]'
                }`}>{m || 'All'}</button>
            ))}
          </div>
        </div>
        <TradeTable trades={trades} />
      </div>
    </div>
  )
}
