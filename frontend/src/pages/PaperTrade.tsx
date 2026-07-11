import { useEffect, useRef, useState } from 'react'
import { RadioTower, RefreshCw, AlertTriangle, Check, ArrowRight, X } from 'lucide-react'
import { getPaperStatus, startPaper, stopPaper, getManualOrders, getTradeHistory, getLiveMarket, placePaperOrder, closeManualOrder } from '../api/client'
import type { PaperStatus, ManualPaperStatus, ManualOrder, TradeHistoryItem } from '../api/client'
import SymbolSearchInput from '../components/SymbolSearchInput'
import { usePersistedState } from '../hooks/usePersistedState'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']

/** Risk = |entry - stop|, reward = |target - entry| — direction-agnostic magnitude ratio. */
function calcRR(entry: number, stopLoss: number, target: number): number | null {
  if (!Number.isFinite(entry) || !Number.isFinite(stopLoss) || !Number.isFinite(target)) return null
  const risk = Math.abs(entry - stopLoss)
  if (risk <= 0) return null
  return Math.abs(target - entry) / risk
}

/** Generic P&L % — works for both BUY/SELL since pnl is already correctly signed by the backend. */
function pnlPercent(o: ManualOrder, pnl: number): number {
  const basis = o.entry * o.quantity
  return basis > 0 ? (pnl / basis) * 100 : 0
}

const pnlCls = (v: number) => (v >= 0 ? 'text-up' : 'text-down')
const dirCls = (d: string) => (d === 'BUY' ? 'text-up' : 'text-down')

export default function PaperTrade() {
  const [status, setStatus] = useState<PaperStatus | null>(null)
  const [strategy, setStrategy] = usePersistedState('paper.strategy', 'rsi')
  const [symbol, setSymbol]     = usePersistedState('paper.symbol', 'BTCUSDT')
  const [tfInterval, setTfInterval] = usePersistedState('paper.interval', '5m')
  const [balance, setBalance]   = usePersistedState('paper.balance', '10000')
  const [busy, setBusy]         = useState(false)
  const [live, setLive]         = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const [manual, setManual] = useState<ManualPaperStatus | null>(null)
  const [persistedTrades, setPersistedTrades] = useState<TradeHistoryItem[]>([])
  const [persistedTotal, setPersistedTotal] = useState(0)

  // Manual entry form — Entry/Stop Loss/Target with a live-calculated RR.
  const [entrySymbol, setEntrySymbol] = usePersistedState('paper.manual.symbol', 'BTCUSDT')
  const [direction, setDirection] = useState<'BUY' | 'SELL'>('BUY')
  const [entryPrice, setEntryPrice] = useState('')
  const [stopLossPrice, setStopLossPrice] = useState('')
  const [targetPrice, setTargetPrice] = useState('')
  const [riskPercent, setRiskPercent] = useState('1.0')
  const [placing, setPlacing] = useState(false)
  const [closingId, setClosingId] = useState<number | null>(null)
  const [placeResult, setPlaceResult] = useState<{ ok: boolean; msg: string } | null>(null)

  // Live market price for the selected symbol — the Entry field auto-fills
  // and keeps tracking it until the user types their own value ("dirty");
  // the Live badge re-syncs it on click.
  const [livePrice, setLivePrice] = useState<number | null>(null)
  const [entryDirty, setEntryDirty] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLivePrice(null)
    setEntryDirty(false)  // new symbol — hand Entry back to the live feed
    async function tick() {
      try {
        const res = await getLiveMarket(entrySymbol, '1m')
        if (!cancelled) setLivePrice(res.data.close)
      } catch { /* transient — next tick retries */ }
    }
    tick()
    const id = setInterval(tick, 5_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [entrySymbol])

  useEffect(() => {
    if (!entryDirty && livePrice !== null) setEntryPrice(String(livePrice))
  }, [livePrice, entryDirty])

  const entryNum = parseFloat(entryPrice)
  const stopLossNum = parseFloat(stopLossPrice)
  const targetNum = parseFloat(targetPrice)
  const liveRR = calcRR(entryNum, stopLossNum, targetNum)
  const allFilled = Number.isFinite(entryNum) && Number.isFinite(stopLossNum) && Number.isFinite(targetNum)
  // Same ordering rule the backend enforces — surfaced here so the user sees
  // WHY the button is disabled instead of a rejected request after the fact.
  const levelsValid = direction === 'BUY'
    ? stopLossNum < entryNum && entryNum < targetNum
    : targetNum < entryNum && entryNum < stopLossNum
  const formValid = allFilled && levelsValid && liveRR !== null

  async function placeManualOrder() {
    setPlacing(true); setPlaceResult(null)
    try {
      const res = await placePaperOrder({
        symbol: entrySymbol.toUpperCase(), strategy: 'manual', direction,
        entry: entryNum, stop_loss: stopLossNum, take_profit: targetNum,
        risk_percent: Number(riskPercent) || 1.0, interval: '1m',
      })
      setPlaceResult({ ok: true, msg: `Order #${res.data.id} placed — ${res.data.quantity.toFixed(6)} ${entrySymbol} @ $${res.data.entry.toFixed(2)}` })
      setStopLossPrice(''); setTargetPrice('')
      setEntryDirty(false)  // hand Entry back to the live feed for the next order
      await refreshManual()
    } catch (e: any) {
      setPlaceResult({ ok: false, msg: e?.response?.data?.detail ?? 'Failed to place order' })
    } finally {
      setPlacing(false)
    }
  }

  async function refresh() {
    try { setStatus((await getPaperStatus()).data) } catch {}
  }

  async function refreshManual() {
    try { setManual((await getManualOrders()).data) } catch {}
  }

  async function handleCloseOrder(id: number) {
    setClosingId(id)
    try {
      await closeManualOrder(id)
      await Promise.all([refreshManual(), refreshPersistedHistory()])
    } catch { /* order may have just closed itself — the refresh shows reality */ }
    setClosingId(null)
  }

  async function refreshPersistedHistory() {
    // Durable source of truth — survives backend restarts, includes both the
    // auto-bot's closed trades AND one-click manual orders (mode=PAPER covers both).
    try {
      const res = await getTradeHistory({ mode: 'PAPER', limit: 50 })
      setPersistedTrades(res.data.trades)
      setPersistedTotal(res.data.total)
    } catch {}
  }

  async function handleStart() {
    setBusy(true)
    try {
      await startPaper({ symbol: symbol.toUpperCase(), interval: tfInterval, strategy, initial_balance: Number(balance) })
      await refresh()
    } catch {}
    setBusy(false)
  }

  async function handleStop() {
    setBusy(true)
    try { await stopPaper(); await refresh() } catch {}
    setBusy(false)
  }

  // Real-time status via WebSocket, with polling fallback if WS drops.
  // The paper engine itself is a server-side singleton — it keeps running
  // regardless of this browser tab; refreshing the page just reconnects to it.
  useEffect(() => {
    let pollId: ReturnType<typeof setInterval> | undefined
    let closed = false

    function startPolling() {
      if (pollId) return
      refresh()
      pollId = setInterval(refresh, 15_000)
    }

    try {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/api/v1/paper/ws`)
      wsRef.current = ws

      ws.onopen = () => setLive(true)
      ws.onmessage = (ev) => {
        try { setStatus(JSON.parse(ev.data) as PaperStatus) } catch {}
      }
      ws.onclose = () => {
        setLive(false)
        if (!closed) startPolling()
      }
      ws.onerror = () => { setLive(false); startPolling() }
    } catch {
      startPolling()
    }

    // Fetch immediately so the page never shows a blank flash before the
    // first WS/poll tick arrives.
    refresh()
    refreshManual()
    refreshPersistedHistory()

    const manualPoll = setInterval(refreshManual, 10_000)
    const historyPoll = setInterval(refreshPersistedHistory, 15_000)

    return () => {
      closed = true
      if (pollId) clearInterval(pollId)
      clearInterval(manualPoll)
      clearInterval(historyPoll)
      wsRef.current?.close()
    }
  }, [])

  return (
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* Manual trade entry — order-ticket card with a live RR ratio */}
      <div className="card">
        <header className="flex items-center justify-between flex-wrap gap-2 px-3 pt-3 pb-2">
          <h2 className="panel-title">Manual Trade Entry</h2>
          {livePrice !== null && (
            <span className="text-[11px] text-fg-faint">
              {entrySymbol} live <span className="num text-fg font-medium">${livePrice.toLocaleString()}</span>
            </span>
          )}
        </header>
        <div className="px-3 pb-3 space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div>
              <label className="field-label mb-1 block">Symbol</label>
              <SymbolSearchInput value={entrySymbol} onCommit={setEntrySymbol} />
            </div>
            <div>
              <label className="field-label mb-1 block">Direction</label>
              <div className="grid grid-cols-2 gap-1">
                <button onClick={() => setDirection('BUY')}
                  className={direction === 'BUY' ? 'btn btn-buy' : 'btn btn-ghost'}>
                  BUY
                </button>
                <button onClick={() => setDirection('SELL')}
                  className={direction === 'SELL' ? 'btn btn-sell' : 'btn btn-ghost'}>
                  SELL
                </button>
              </div>
            </div>
            <div>
              <label className="field-label mb-1 flex items-center justify-between">
                <span>Entry</span>
                {entryDirty ? (
                  <button onClick={() => setEntryDirty(false)} title="Re-sync Entry to the live market price"
                    className="flex items-center gap-0.5 text-[10px] text-accent hover:text-fg cursor-pointer">
                    <RefreshCw size={9} aria-label="Re-sync Entry to live price" /> use live
                  </button>
                ) : (
                  <span className="flex items-center gap-0.5 text-[10px] text-up"
                    title="Entry tracks the live market price until you type your own">
                    <RadioTower size={9} aria-label="Entry tracks live price" /> live
                  </span>
                )}
              </label>
              <input type="number" value={entryPrice}
                onChange={e => { setEntryDirty(true); setEntryPrice(e.target.value) }}
                placeholder={livePrice !== null ? String(livePrice) : 'loading…'}
                className={`input input-mono w-full ${entryDirty ? '' : 'border-up/40'}`} />
            </div>
            <div>
              <label className="field-label mb-1 block">Stop Loss</label>
              <input type="number" value={stopLossPrice} onChange={e => setStopLossPrice(e.target.value)} placeholder="0.00"
                className="input input-mono w-full text-down" />
            </div>
            <div>
              <label className="field-label mb-1 block">Target</label>
              <input type="number" value={targetPrice} onChange={e => setTargetPrice(e.target.value)} placeholder="0.00"
                className="input input-mono w-full text-up" />
            </div>
            <div>
              <label className="field-label mb-1 block">Risk %</label>
              <input type="number" value={riskPercent} onChange={e => setRiskPercent(e.target.value)} step="0.1" min="0.1"
                className="input input-mono w-full" />
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="bg-raised rounded-md px-3 py-1.5 border border-line flex items-baseline gap-2">
              <span className="field-label">R/R</span>
              <span className={`num text-xl font-semibold leading-none ${
                liveRR === null ? 'text-fg-faint' : liveRR >= 2 ? 'text-up' : liveRR >= 1 ? 'text-accent' : 'text-down'}`}>
                {liveRR === null ? '—' : `1:${liveRR.toFixed(2)}`}
              </span>
            </div>
            <button onClick={placeManualOrder} disabled={!formValid || placing}
              className={`btn ${direction === 'BUY' ? 'btn-buy' : 'btn-sell'} disabled:opacity-40 disabled:cursor-not-allowed`}>
              {placing ? 'Placing…' : `Place ${direction} Order`}
            </button>
            {allFilled && !levelsValid && (
              <span className="flex items-center gap-1 text-[11px] text-accent">
                <AlertTriangle size={11} aria-label="Invalid levels" />
                {direction === 'BUY'
                  ? 'For BUY: Stop Loss < Entry < Target'
                  : 'For SELL: Target < Entry < Stop Loss'}
              </span>
            )}
            {placeResult && (
              <span className={`flex items-center gap-1 text-[11px] ${placeResult.ok ? 'text-up' : 'text-down'}`}>
                {placeResult.ok
                  ? <Check size={11} aria-label="Order placed" />
                  : <AlertTriangle size={11} aria-label="Order failed" />}
                {placeResult.msg}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Paper account — the wallet behind ALL manual/one-click/auto-test
          orders (ManualPaperTrader). This is where "did my paper trades make
          money" actually lives; the auto-bot below has its own wallet. */}
      {manual && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(() => {
            const start = manual.balance - manual.realized_pnl
            const ret = start > 0 ? ((manual.equity - start) / start) * 100 : 0
            return [
              { label: 'Account Equity', value: `$${manual.equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}` },
              { label: 'Account Balance', value: `$${manual.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}` },
              { label: 'Total Realized PnL', value: `${manual.realized_pnl >= 0 ? '+' : '-'}$${Math.abs(manual.realized_pnl).toFixed(2)}`, color: pnlCls(manual.realized_pnl) },
              { label: 'Total Return', value: `${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%`, color: pnlCls(ret) },
            ].map(m => (
              <div key={m.label} className="card px-3 py-2.5">
                <p className="panel-title mb-1">{m.label}</p>
                <p className={`num text-[15px] font-semibold leading-tight ${m.color ?? 'text-fg'}`}>{m.value}</p>
              </div>
            ))
          })()}
        </div>
      )}

      {/* Strategy auto-bot — the server-side engine that trades a strategy's
          signals automatically on every closed candle */}
      <div className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2">
          <h2 className="panel-title">Strategy Auto-Bot</h2>
          <span className={`chip ${live ? 'chip-up' : 'chip-muted'}`}>
            {live && <RadioTower size={9} aria-label="WebSocket connected" />}
            {live ? 'WebSocket live' : 'Polling'}
          </span>
        </header>
        <div className="px-3 pb-3 space-y-3">
          <p className="text-[11px] text-fg-faint leading-relaxed">
            Watches every closed candle of the chosen symbol/interval with the selected strategy.
            When the strategy fires a BUY signal, it opens a virtual position automatically, then
            manages it hands-free (stop-loss, take-profit, trailing stop, partial exits) until close.
            Runs on the server — it keeps trading even if you close this page.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div>
              <label className="field-label mb-1 block">Symbol</label>
              {status?.is_running ? (
                <input value={symbol} disabled className="input w-full opacity-50" />
              ) : (
                <SymbolSearchInput value={symbol} onCommit={setSymbol} />
              )}
            </div>
            <div>
              <label className="field-label mb-1 block">Strategy</label>
              <select value={strategy} onChange={e => setStrategy(e.target.value)} disabled={status?.is_running}
                className="input w-full disabled:opacity-50">
                {STRATEGIES.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label mb-1 block">Interval</label>
              <select value={tfInterval} onChange={e => setTfInterval(e.target.value)} disabled={status?.is_running}
                className="input w-full disabled:opacity-50">
                {['1m','3m','5m','15m','30m','1h','4h'].map(i => <option key={i}>{i}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label mb-1 block">Balance ($)</label>
              <input type="number" value={balance} onChange={e => setBalance(e.target.value)} disabled={status?.is_running}
                className="input input-mono w-full disabled:opacity-50" />
            </div>
            <div className="flex items-end">
              {status?.is_running ? (
                <button onClick={handleStop} disabled={busy} className="btn btn-danger-outline w-full disabled:opacity-50">
                  {busy ? 'Stopping…' : 'Stop'}
                </button>
              ) : (
                <button onClick={handleStart} disabled={busy} className="btn btn-primary w-full disabled:opacity-50">
                  {busy ? 'Starting…' : 'Start'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {status && (
        <>
          {/* Status banner */}
          <div className={`card px-3 py-2.5 flex items-center gap-3 ${
            status.is_running ? 'border-up/40 text-up' : 'text-fg-faint'}`}>
            <span className={`w-2 h-2 rounded-full shrink-0 ${status.is_running ? 'bg-up animate-pulse' : 'bg-fg-faint'}`} />
            <span className="text-[12.5px] font-medium">
              {status.is_running ? `Running — ${status.symbol} ${status.interval} · ${status.strategy}` : 'Stopped (engine keeps its state — restart anytime)'}
            </span>
            {status.is_running && (
              <span className="num text-[11px] text-fg-faint">
                {status.candles_processed} candle{status.candles_processed === 1 ? '' : 's'} analyzed
                {status.last_price ? ` · last price $${status.last_price.toLocaleString()}` : ''}
                {status.candles_processed === 0 ? ' — waiting for the first candle to close…' : ''}
              </span>
            )}
            {status.last_signal && (
              <span className={`ml-auto chip ${
                status.last_signal === 'BUY' ? 'chip-up' :
                status.last_signal === 'SELL' ? 'chip-down' : 'chip-muted'
              }`}>{status.last_signal}</span>
            )}
          </div>

          {/* Metrics — the BOT's own wallet only (separate from the paper
              account strip above), so an idle bot showing $10,000 / $0.00 is
              expected, not a bug. */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Bot Equity',       value: `$${status.equity.toLocaleString()}` },
              { label: 'Bot Cash',         value: `$${status.cash.toLocaleString()}` },
              { label: 'Bot Realized PnL', value: `$${status.realized_pnl.toFixed(2)}`, color: pnlCls(status.realized_pnl) },
              { label: 'Bot Return', value: `${status.total_return >= 0 ? '+' : ''}${status.total_return.toFixed(2)}%`, color: pnlCls(status.total_return) },
            ].map(m => (
              <div key={m.label} className="card px-3 py-2.5">
                <p className="panel-title mb-1">{m.label}</p>
                <p className={`num text-[15px] font-semibold leading-tight ${m.color ?? 'text-fg'}`}>{m.value}</p>
              </div>
            ))}
          </div>

          {/* Open position */}
          {status.open_position && (
            <div className="card border-accent/40">
              <header className="px-3 pt-3 pb-2">
                <h3 className="panel-title text-accent">Open Position (auto-bot)</h3>
              </header>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-3 px-3 pb-3">
                {[
                  ['Entry', `$${status.open_position.entry_price.toFixed(2)}`],
                  ['Current', `$${status.open_position.current_price.toFixed(2)}`],
                  ['Qty', status.open_position.quantity.toFixed(5)],
                  ['Stop', `$${status.open_position.stop_loss.toFixed(2)}`],
                  ['Target', `$${status.open_position.take_profit.toFixed(2)}`],
                  ['PnL', `$${status.open_position.unrealized_pnl.toFixed(2)}`],
                ].map(([l, v]) => (
                  <div key={l}>
                    <p className="field-label">{l}</p>
                    <p className={`num text-[12.5px] font-medium ${
                      l === 'PnL' ? pnlCls(status.open_position!.unrealized_pnl) : 'text-fg'}`}>{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Manual paper orders — from the form above, or the "Place Paper Trade" button on Dashboard/Retail Dashboard */}
      {manual && (manual.open_orders.length > 0 || manual.closed_orders.length > 0) && (
        <div className="card">
          <header className="flex items-center justify-between flex-wrap gap-2 px-3 pt-3 pb-2">
            <h3 className="panel-title">Manual Paper Orders</h3>
            <span className="num text-[11px] text-fg-faint">
              Equity ${manual.equity.toLocaleString()} · Realized PnL{' '}
              <span className={pnlCls(manual.realized_pnl)}>${manual.realized_pnl.toFixed(2)}</span>
            </span>
          </header>
          <div className="px-3 pb-3 space-y-3">
            {manual.open_orders.length > 0 && (
              <div>
                <p className="field-label mb-1">Open ({manual.open_orders.length})</p>
                <table className="w-full text-[12.5px]">
                  <thead>
                    <tr>
                      <th className="th text-left">Dir</th>
                      <th className="th text-left">Symbol</th>
                      <th className="th text-right">Entry</th>
                      <th className="th text-right">Now</th>
                      <th className="th text-right">R/R</th>
                      <th className="th text-right">PnL</th>
                      <th className="th text-right">Status</th>
                      <th className="th text-right">Close</th>
                    </tr>
                  </thead>
                  <tbody>
                    {manual.open_orders.map(o => {
                      const rr = calcRR(o.entry, o.stop_loss, o.take_profit)
                      const pct = pnlPercent(o, o.unrealized_pnl)
                      return (
                        <tr key={o.id} className="row-hover">
                          <td className={`td font-semibold ${dirCls(o.direction)}`}>{o.direction}</td>
                          <td className="td text-fg">{o.symbol}</td>
                          <td className="td num text-right text-fg-soft">${o.entry.toFixed(2)}</td>
                          <td className="td num text-right text-fg-soft">${o.current_price.toFixed(2)}</td>
                          <td className="td num text-right text-fg-faint">{rr !== null ? `1:${rr.toFixed(2)}` : '—'}</td>
                          <td className={`td num text-right font-medium ${pnlCls(o.unrealized_pnl)}`}>
                            {o.unrealized_pnl >= 0 ? '+' : ''}${o.unrealized_pnl.toFixed(2)} ({pct >= 0 ? '+' : ''}{pct.toFixed(2)}%)
                          </td>
                          <td className="td text-right"><span className="chip chip-warn">MONITORING</span></td>
                          <td className="td text-right">
                            <button onClick={() => handleCloseOrder(o.id)} disabled={closingId === o.id}
                              aria-label={`Close order ${o.id} at market price`}
                              title="Close now at market price"
                              className="btn btn-danger-outline !h-6 !px-1.5">
                              <X size={12} aria-hidden />
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {manual.closed_orders.length > 0 && (
              <div>
                <p className="field-label mb-1">Closed ({manual.closed_orders.length})</p>
                <table className="w-full text-[12.5px]">
                  <thead>
                    <tr>
                      <th className="th text-left">Dir</th>
                      <th className="th text-left">Symbol</th>
                      <th className="th text-right">Entry / Exit</th>
                      <th className="th text-right">PnL</th>
                      <th className="th text-left">Reason</th>
                      <th className="th text-right">Closed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...manual.closed_orders].reverse().slice(0, 10).map(o => {
                      const pct = pnlPercent(o, o.realized_pnl)
                      return (
                        <tr key={o.id} className="row-hover">
                          <td className={`td font-semibold ${dirCls(o.direction)}`}>{o.direction}</td>
                          <td className="td text-fg">{o.symbol}</td>
                          <td className="td num text-right text-fg-soft">
                            <span className="inline-flex items-center gap-1">
                              ${o.entry.toFixed(2)}
                              <ArrowRight size={10} aria-label="to" className="text-fg-faint" />
                              ${(o.exit_price ?? o.current_price).toFixed(2)}
                            </span>
                          </td>
                          <td className={`td num text-right font-medium ${pnlCls(o.realized_pnl)}`}>
                            {o.realized_pnl >= 0 ? '+' : ''}${o.realized_pnl.toFixed(2)} ({pct >= 0 ? '+' : ''}{pct.toFixed(2)}%)
                          </td>
                          <td className="td text-fg-faint">{o.exit_reason}</td>
                          <td className="td num text-right text-fg-faint">{o.closed_at ? new Date(o.closed_at).toLocaleTimeString() : ''}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Persisted trade history — durable, survives backend restarts */}
      <div className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2">
          <h3 className="panel-title">Trade History</h3>
          <span className="num text-[11px] text-fg-faint">{persistedTotal} total · auto-bot + manual, saved to DB</span>
        </header>
        <div className="px-3 pb-3">
          {persistedTrades.length === 0 ? (
            <p className="text-fg-faint text-[12.5px] text-center py-6">
              No paper trades yet. Use the Manual Trade Entry form above, start the auto-bot, or use "Place Paper Trade" on a signal card (Dashboard / Retail Dashboard).
            </p>
          ) : (
            <table className="w-full text-[12.5px]">
              <thead>
                <tr>
                  <th className="th text-left">Dir</th>
                  <th className="th text-left">Symbol</th>
                  <th className="th text-left">Strategy</th>
                  <th className="th text-right">Entry / Exit</th>
                  <th className="th text-right">PnL</th>
                  <th className="th text-left">Reason</th>
                  <th className="th text-right">Time</th>
                </tr>
              </thead>
              <tbody>
                {persistedTrades.map(t => (
                  <tr key={t.id} className="row-hover">
                    <td className={`td font-semibold ${dirCls(t.direction)}`}>{t.direction}</td>
                    <td className="td text-fg">{t.symbol}</td>
                    <td className="td text-fg-faint">{t.strategy}</td>
                    <td className="td num text-right text-fg-soft">
                      <span className="inline-flex items-center gap-1">
                        ${t.entry_price.toFixed(2)}
                        <ArrowRight size={10} aria-label="to" className="text-fg-faint" />
                        ${t.exit_price.toFixed(2)}
                      </span>
                    </td>
                    <td className={`td num text-right font-medium ${pnlCls(t.pnl)}`}>
                      {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)} ({t.pnl_percent >= 0 ? '+' : ''}{t.pnl_percent.toFixed(2)}%)
                    </td>
                    <td className="td text-fg-faint">{t.exit_reason}</td>
                    <td className="td num text-right text-fg-faint">{new Date(t.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
