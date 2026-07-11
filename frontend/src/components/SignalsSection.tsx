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
    <div className="space-y-3">
      <h2 className="panel-title">Signals</h2>

      {/* Market Scan — every strategy, one timeframe */}
      <div className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2 flex-wrap gap-2">
          <h3 className="panel-title">
            Market Scan — every strategy on {symbol} · {interval}
          </h3>
          <select value={interval} onChange={e => setInterval(e.target.value)}
            className="input input-mono !h-6 text-[11px]">
            {INTERVALS.map(i => <option key={i}>{i}</option>)}
          </select>
        </header>
        <p className="px-3 text-[11px] text-fg-faint mb-2">All 8 strategies analyze independently — click a row to open its full detail below.</p>
        {scanLoading ? (
          <p className="text-fg-faint text-sm text-center py-6">Scanning…</p>
        ) : (
          <div className="px-3 pb-3">
            <SignalScanTable
              signals={scanResults}
              labelKey="strategy"
              onRowClick={s => setStrategy(STRATEGY_LABEL_TO_KEY[s.strategy] ?? strategy)}
            />
          </div>
        )}
      </div>

      {/* Multi-timeframe — one strategy, every timeframe */}
      <div className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2 flex-wrap gap-2">
          <h3 className="panel-title">
            Multi-Timeframe — {strategy} on {symbol}
          </h3>
          <select value={strategy} onChange={e => setStrategy(e.target.value)}
            className="input !h-6 text-[11px]">
            {STRATEGIES.map(s => <option key={s}>{s}</option>)}
          </select>
        </header>
        <p className="px-3 text-[11px] text-fg-faint mb-2">Same strategy, every timeframe analyzed independently — compare which one it currently suits.</p>
        {tfLoading ? (
          <p className="text-fg-faint text-sm text-center py-6">Scanning timeframes…</p>
        ) : (
          <div className="px-3 pb-3">
            <SignalScanTable
              signals={tfResults}
              labelKey="interval"
              onRowClick={s => setInterval(s.interval)}
            />
          </div>
        )}
      </div>

      {error && (
        <div className="card card-pad border-down/40 text-down text-sm">
          {error}
        </div>
      )}

      {/* Detail — the exact strategy/interval selected above */}
      {loading ? (
        <p className="text-fg-faint text-sm text-center py-6">Loading detail…</p>
      ) : signal && <SignalCard signal={signal} />}
    </div>
  )
}
