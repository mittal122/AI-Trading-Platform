import { useState } from 'react'
import { getSignal } from '../api/client'
import type { TradingSignal } from '../api/client'
import SignalCard from '../components/SignalCard'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']
const INTERVALS  = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']

export default function Signals() {
  const [strategy, setStrategy] = useState('rsi')
  const [symbol, setSymbol]     = useState('BTCUSDT')
  const [interval, setInterval] = useState('5m')
  const [signal, setSignal]     = useState<TradingSignal | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  async function run() {
    setLoading(true); setError('')
    try {
      const res = await getSignal(strategy, symbol.toUpperCase(), interval)
      setSignal(res.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to get signal')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-white">Signals</h1>

      {/* Controls */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Symbol</label>
            <input
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Strategy</label>
            <select
              value={strategy}
              onChange={e => setStrategy(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none"
            >
              {STRATEGIES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Interval</label>
            <select
              value={interval}
              onChange={e => setInterval(e.target.value)}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none"
            >
              {INTERVALS.map(i => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={run}
              disabled={loading}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {signal && <SignalCard signal={signal} />}
    </div>
  )
}
