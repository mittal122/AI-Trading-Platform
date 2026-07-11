import { useEffect, useState } from 'react'
import { Play, Square, ArrowUpRight, ArrowDownRight, Repeat2 } from 'lucide-react'
import { startAutoTest, stopAutoTest, getAutoTestStatus } from '../api/client'
import type { AutoTestStatus } from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { usePersistedState } from '../hooks/usePersistedState'

const INTERVALS = ['1m', '5m', '15m', '30m', '1h', '4h']
const STATUS_POLL_MS = 5000

const ACTION_CHIP: Record<string, string> = {
  ENTER: 'chip-up', FLIP: 'chip-warn', TARGET: 'chip-up',
  STOP: 'chip-down', HOLD: 'chip-muted', WAIT: 'chip-muted',
  START: 'chip-warn', ERROR: 'chip-down',
}

const signCls = (v: number) => (v >= 0 ? 'text-up' : 'text-down')

export default function SmcAutoTest() {
  const [symbol, setSymbol] = usePersistedState('autotest.symbol', 'BTCUSDT')
  const [interval, setInterval_] = usePersistedState('autotest.interval', '5m')
  const [riskPct, setRiskPct] = usePersistedState('autotest.risk', 1.0)
  const [minScore, setMinScore] = usePersistedState('autotest.minScore', 40)
  const [flipMargin, setFlipMargin] = usePersistedState('autotest.flipMargin', 10)

  const [st, setSt] = useState<AutoTestStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function refresh() {
    try {
      const { data } = await getAutoTestStatus()
      setSt(data)
    } catch { /* transient — next poll retries */ }
  }

  useEffect(() => {
    refresh()
    const id = window.setInterval(refresh, STATUS_POLL_MS)
    return () => window.clearInterval(id)
  }, [])

  async function onStart() {
    setBusy(true); setError('')
    try {
      const { data } = await startAutoTest({
        symbol, interval, risk_percent: riskPct, min_score: minScore, flip_margin: flipMargin,
      })
      setSt(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to start')
    } finally { setBusy(false) }
  }

  async function onStop() {
    setBusy(true); setError('')
    try {
      const { data } = await stopAutoTest()
      setSt(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to stop')
    } finally { setBusy(false) }
  }

  const order = st?.current_order ?? null
  const la = st?.last_analysis ?? null
  const running = st?.running ?? false

  return (
    <div className="relative p-3 space-y-3 max-w-[1800px] mx-auto">
      <LoadingOverlay show={st === null} label="Loading auto-test status…" />

      {/* Config + controls */}
      <div className="card card-pad">
        <div className="flex items-center gap-2 mb-3">
          <Repeat2 size={14} className="text-accent" aria-hidden />
          <h2 className="panel-title">SMC Auto-Test</h2>
          <span className="text-[11px] text-fg-faint">
            re-analyzes every candle close, paper-trades the stronger side, flips on reversal — practice money only
          </span>
          {running && st && (
            <span className="chip chip-up ml-auto">RUNNING · {st.symbol} {st.interval}</span>
          )}
        </div>
        <div className="flex items-end gap-3 flex-wrap">
          <div className="w-40">
            <label className="field-label">Symbol</label>
            <SymbolSearchInput value={symbol} onCommit={setSymbol} />
          </div>
          <div>
            <label className="field-label" htmlFor="at-interval">Re-analyze every</label>
            <select id="at-interval" value={interval} onChange={e => setInterval_(e.target.value)}
              className="input w-24">
              {INTERVALS.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
          <div className="w-24">
            <label className="field-label" htmlFor="at-risk">Risk %</label>
            <input id="at-risk" type="number" min={0.1} max={5} step={0.1} value={riskPct}
              onChange={e => setRiskPct(Number(e.target.value))} className="input input-mono" />
          </div>
          <div className="w-28">
            <label className="field-label" htmlFor="at-minscore"
              title="Don't enter unless the chosen side's confluence score reaches this (0-110)">
              Min score
            </label>
            <input id="at-minscore" type="number" min={0} max={110} value={minScore}
              onChange={e => setMinScore(Number(e.target.value))} className="input input-mono" />
          </div>
          <div className="w-28">
            <label className="field-label" htmlFor="at-flip"
              title="Opposite side must beat the current side's score by this much to trigger a flip">
              Flip margin
            </label>
            <input id="at-flip" type="number" min={0} max={60} value={flipMargin}
              onChange={e => setFlipMargin(Number(e.target.value))} className="input input-mono" />
          </div>
          <div className="ml-auto flex items-center gap-2">
            {running ? (
              <button onClick={onStop} disabled={busy} className="btn btn-danger-outline">
                <Square size={13} aria-hidden /> Stop
              </button>
            ) : (
              <button onClick={onStart} disabled={busy} className="btn btn-primary">
                <Play size={13} aria-hidden /> Start
              </button>
            )}
          </div>
        </div>
        {error && <p className="text-down text-xs mt-2">{error}</p>}
      </div>

      {/* Live position + latest analysis + stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 items-start">
        <div className="card card-pad">
          <h3 className="panel-title mb-2">Current Position</h3>
          {order ? (
            <>
              <div className="flex items-center gap-2 mb-3">
                <span className={`chip ${order.direction === 'BUY' ? 'chip-up' : 'chip-down'}`}>
                  {order.direction === 'BUY'
                    ? <><ArrowUpRight size={11} aria-hidden /> LONG</>
                    : <><ArrowDownRight size={11} aria-hidden /> SHORT</>}
                </span>
                <span className="text-[12px] text-fg font-medium">{order.symbol}</span>
                <span className="num text-[11px] text-fg-faint ml-auto">#{order.id}</span>
              </div>
              <div className="grid grid-cols-3 gap-px bg-line rounded-md overflow-hidden mb-2">
                <Cell label="Entry" value={order.entry} />
                <Cell label="Stop" value={order.stop_loss} cls="text-down" />
                <Cell label="Target" value={order.take_profit} cls="text-up" />
              </div>
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-fg-faint">Live PnL</span>
                <span className={`num font-semibold ${signCls(order.unrealized_pnl)}`}>
                  {order.unrealized_pnl >= 0 ? '+' : ''}{order.unrealized_pnl.toFixed(2)} USD
                </span>
              </div>
              <p className="num text-[10px] text-fg-faint mt-1">
                held since {new Date(order.opened_at).toLocaleTimeString('en-GB')} · price {order.current_price}
              </p>
            </>
          ) : (
            <p className="text-fg-faint text-xs py-3">
              {running ? 'Flat — waiting for a side to clear the minimum score.' : 'Not running.'}
            </p>
          )}
        </div>

        <div className="card card-pad">
          <h3 className="panel-title mb-2">Latest Analysis</h3>
          {la ? (
            <>
              <div className="flex items-center gap-2 mb-3">
                <span className={`chip ${la.primary === 'long' ? 'chip-up' : la.primary === 'short' ? 'chip-down' : 'chip-muted'}`}>
                  {la.primary.toUpperCase()}
                </span>
                <span className="num text-[10.5px] text-fg-faint ml-auto">{la.candle_time.slice(0, 16)}</span>
              </div>
              <ScoreBar label="Long" score={la.long_score} cls="bg-up" />
              <ScoreBar label="Short" score={la.short_score} cls="bg-down" />
            </>
          ) : (
            <p className="text-fg-faint text-xs py-3">No analysis yet — runs at the first candle close.</p>
          )}
        </div>

        <div className="card card-pad">
          <h3 className="panel-title mb-2">Session Stats</h3>
          {st ? (
            <div className="grid grid-cols-3 gap-2">
              <Stat label="Trades" value={String(st.stats.trades)} />
              <Stat label="Wins"
                value={st.stats.trades > 0 ? `${st.stats.wins}/${st.stats.trades}` : '0'} />
              <Stat label="Net PnL"
                value={`${st.stats.net_pnl >= 0 ? '+' : ''}$${Math.abs(st.stats.net_pnl).toFixed(2)}`}
                cls={signCls(st.stats.net_pnl)} />
            </div>
          ) : null}
          <p className="text-[10.5px] text-fg-faint mt-3">
            Closed trades also appear on the Portfolio page (strategy "smc_autotest").
          </p>
        </div>
      </div>

      {/* Event log */}
      <section className="card">
        <header className="px-3 pt-3 pb-2">
          <h2 className="panel-title">Event Log <span className="num text-fg-faint">({st?.events.length ?? 0})</span></h2>
        </header>
        <div className="overflow-x-auto pb-1.5 max-h-[420px] overflow-y-auto">
          {(st?.events.length ?? 0) === 0 ? (
            <p className="text-fg-faint text-xs text-center py-6">
              No events yet — start a session and the robot's every decision lands here.
            </p>
          ) : (
            <table className="w-full text-[12.5px]">
              <thead>
                <tr>
                  <th className="th pl-3">Time</th>
                  <th className="th">Action</th>
                  <th className="th">Detail</th>
                  <th className="th pr-3 text-right">Long / Short score</th>
                </tr>
              </thead>
              <tbody>
                {st!.events.map((e, i) => (
                  <tr key={i} className="row-hover">
                    <td className="td num pl-3 text-fg-faint">{new Date(e.time).toLocaleTimeString('en-GB')}</td>
                    <td className="td"><span className={`chip ${ACTION_CHIP[e.action] ?? 'chip-muted'}`}>{e.action}</span></td>
                    <td className="td text-fg-soft">{e.detail}</td>
                    <td className="td num pr-3 text-right text-fg-faint">
                      {e.long_score != null ? `${e.long_score} / ${e.short_score}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  )
}

function Cell({ label, value, cls }: { label: string; value: number; cls?: string }) {
  return (
    <div className="bg-surface px-2 py-1.5">
      <p className="text-[10px] text-fg-faint">{label}</p>
      <p className={`num text-[13px] font-medium ${cls ?? 'text-fg'}`}>{value}</p>
    </div>
  )
}

function ScoreBar({ label, score, cls }: { label: string; score: number; cls: string }) {
  return (
    <div className="flex items-center gap-2 mb-1.5">
      <span className="text-[11px] text-fg-soft w-10">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-line overflow-hidden">
        <div className={`h-full ${cls}`} style={{ width: `${Math.min(100, score / 110 * 100)}%` }} />
      </div>
      <span className="num text-[11px] text-fg w-8 text-right">{score}</span>
    </div>
  )
}

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <div className="bg-raised border border-line rounded-md px-2 py-1.5">
      <p className="text-[10px] text-fg-faint">{label}</p>
      <p className={`num text-[13px] font-semibold ${cls ?? 'text-fg'}`}>{value}</p>
    </div>
  )
}
