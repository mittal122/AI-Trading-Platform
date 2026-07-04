import { useEffect, useState } from 'react'
import { getSignal, scanAllStrategies, getMultiTimeframeSignals } from '../api/client'
import type { TradingSignal } from '../api/client'
import SignalCard from './SignalCard'
import SignalScanTable from './SignalScanTable'
import { usePersistedState } from '../hooks/usePersistedState'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']
const INTERVALS  = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
const SCAN_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']

// TradingSignal.strategy is a human-readable label (e.g. "RSI Strategy") —
// map it back to the factory key used everywhere else (getSignal, dropdowns).
const STRATEGY_LABEL_TO_KEY: Record<string, string> = {
  'RSI Strategy': 'rsi',
  'EMA Crossover': 'ema',
  'MACD Crossover': 'macd',
  'Bollinger Breakout': 'breakout',
  'Supertrend': 'supertrend',
  'CTA Trend': 'cta_trend',
  'Turtle Trading': 'turtle',
  'Engulfing Scalp': 'engulfing_scalp',
}

/**
 * Market Scan + Multi-Timeframe scan + signal detail — formerly the
 * standalone Signals page, now embedded in Retail Dashboard (below the
 * Analysis Tools section) and driven by the parent page's own symbol.
 */
export default function SignalsSection({ symbol }: { symbol: string }) {
  const [strategy, setStrategy] = usePersistedState('retailDashboard.strategy', 'rsi')
  const [interval, setInterval] = usePersistedState('retailDashboard.interval', '5m')

  const [signal, setSignal]     = useState<TradingSignal | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')

  const [scanResults, setScanResults] = useState<TradingSignal[]>([])
  const [scanLoading, setScanLoading] = useState(false)

  const [tfResults, setTfResults] = useState<TradingSignal[]>([])
  const [tfLoading, setTfLoading] = useState(false)

  async function runDetail() {
    setLoading(true); setError('')
    try {
      const res = await getSignal(strategy, symbol, interval)
      setSignal(res.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to get signal')
    } finally {
      setLoading(false)
    }
  }

  async function runScan() {
    setScanLoading(true)
    try {
      const res = await scanAllStrategies(symbol, interval)
      setScanResults(res.data)
    } catch {
      setScanResults([])
    } finally {
      setScanLoading(false)
    }
  }

  async function runTimeframes() {
    setTfLoading(true)
    try {
      const res = await getMultiTimeframeSignals(strategy, symbol, SCAN_TIMEFRAMES)
      setTfResults(res.data)
    } catch {
      setTfResults([])
    } finally {
      setTfLoading(false)
    }
  }

  // Every strategy analyzes the market on its own — auto-runs whenever the
  // symbol or the scan timeframe changes, no manual "open each strategy" step.
  useEffect(() => { runScan() }, [symbol, interval])
  // Same strategy, every timeframe independently — auto-runs on strategy/symbol change.
  useEffect(() => { runTimeframes() }, [strategy, symbol])
  useEffect(() => { runDetail() }, [strategy, symbol, interval])

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-slate-300">Signals</h2>

      {/* Market Scan — every strategy, one timeframe */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="flex items-center justify-between mb-1 flex-wrap gap-3">
          <h3 className="text-sm font-semibold text-slate-300">
            Market Scan — every strategy on {symbol} · {interval}
          </h3>
          <select value={interval} onChange={e => setInterval(e.target.value)}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1 text-xs text-white outline-none">
            {INTERVALS.map(i => <option key={i}>{i}</option>)}
          </select>
        </div>
        <p className="text-xs text-slate-600 mb-4">All 8 strategies analyze independently — click a row to open its full detail below.</p>
        {scanLoading ? (
          <p className="text-slate-500 text-sm text-center py-6">Scanning…</p>
        ) : (
          <SignalScanTable
            signals={scanResults}
            labelKey="strategy"
            onRowClick={s => setStrategy(STRATEGY_LABEL_TO_KEY[s.strategy] ?? strategy)}
          />
        )}
      </div>

      {/* Multi-timeframe — one strategy, every timeframe */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="flex items-center justify-between mb-1 flex-wrap gap-3">
          <h3 className="text-sm font-semibold text-slate-300">
            Multi-Timeframe — {strategy} on {symbol}
          </h3>
          <select value={strategy} onChange={e => setStrategy(e.target.value)}
            className="bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-2 py-1 text-xs text-white outline-none">
            {STRATEGIES.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <p className="text-xs text-slate-600 mb-4">Same strategy, every timeframe analyzed independently — compare which one it currently suits.</p>
        {tfLoading ? (
          <p className="text-slate-500 text-sm text-center py-6">Scanning timeframes…</p>
        ) : (
          <SignalScanTable
            signals={tfResults}
            labelKey="interval"
            onRowClick={s => setInterval(s.interval)}
          />
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Detail — the exact strategy/interval selected above */}
      {loading ? (
        <p className="text-slate-500 text-sm text-center py-6">Loading detail…</p>
      ) : signal && <SignalCard signal={signal} />}
    </div>
  )
}
