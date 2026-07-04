import { useEffect, useRef, useState } from 'react'
import { getPaperStatus, startPaper, stopPaper, getManualOrders, getTradeHistory, getLiveMarket, placePaperOrder } from '../api/client'
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
  const [placeResult, setPlaceResult] = useState<{ ok: boolean; msg: string } | null>(null)

  // Live market price for the selected symbol — the Entry field auto-fills
  // and keeps tracking it until the user types their own value ("dirty");
  // the ● Live badge re-syncs it on click.
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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Paper Trading</h1>
        <span className={`text-xs px-2 py-1 rounded border ${live
          ? 'bg-green-500/10 text-green-400 border-green-500/30'
          : 'bg-slate-500/10 text-slate-500 border-slate-500/20'}`}>
          {live ? '● WebSocket live' : '○ Polling'}
        </span>
      </div>

      {/* Manual trade entry — Entry/Stop Loss/Target with a live RR ratio */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-sm font-semibold text-slate-300">Manual Trade Entry</h2>
          {livePrice !== null && (
            <span className="text-xs text-slate-500">
              {entrySymbol} live: <span className="text-white font-medium">${livePrice.toLocaleString()}</span>
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Symbol</label>
            <SymbolSearchInput value={entrySymbol} onCommit={setEntrySymbol} />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Direction</label>
            <select value={direction} onChange={e => setDirection(e.target.value as 'BUY' | 'SELL')}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none">
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 flex items-center justify-between">
              <span>Entry</span>
              {entryDirty ? (
                <button onClick={() => setEntryDirty(false)} title="Re-sync Entry to the live market price"
                  className="text-[10px] text-indigo-400 hover:text-indigo-300">↻ use live</button>
              ) : (
                <span className="text-[10px] text-green-400" title="Entry tracks the live market price until you type your own">● live</span>
              )}
            </label>
            <input type="number" value={entryPrice}
              onChange={e => { setEntryDirty(true); setEntryPrice(e.target.value) }}
              placeholder={livePrice !== null ? String(livePrice) : 'loading…'}
              className={`w-full bg-[#0f1117] border rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500 ${
                entryDirty ? 'border-[#2a2d3e]' : 'border-green-500/30'
              }`} />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Stop Loss</label>
            <input type="number" value={stopLossPrice} onChange={e => setStopLossPrice(e.target.value)} placeholder="0.00"
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-red-400 outline-none focus:border-indigo-500" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Target</label>
            <input type="number" value={targetPrice} onChange={e => setTargetPrice(e.target.value)} placeholder="0.00"
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-green-400 outline-none focus:border-indigo-500" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Risk %</label>
            <input type="number" value={riskPercent} onChange={e => setRiskPercent(e.target.value)} step="0.1" min="0.1"
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-indigo-500" />
          </div>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="bg-[#0f1117] rounded-lg px-4 py-2 border border-[#2a2d3e]">
            <span className="text-xs text-slate-500 mr-2">Risk/Reward</span>
            <span className={`text-sm font-bold ${liveRR === null ? 'text-slate-600' : liveRR >= 2 ? 'text-green-400' : liveRR >= 1 ? 'text-yellow-400' : 'text-red-400'}`}>
              {liveRR === null ? '—' : `1:${liveRR.toFixed(2)}`}
            </span>
          </div>
          <button onClick={placeManualOrder} disabled={!formValid || placing}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg">
            {placing ? 'Placing…' : `Place ${direction} Order`}
          </button>
          {allFilled && !levelsValid && (
            <span className="text-xs text-yellow-400">
              ⚠ {direction === 'BUY'
                ? 'For BUY: Stop Loss < Entry < Target'
                : 'For SELL: Target < Entry < Stop Loss'}
            </span>
          )}
          {placeResult && (
            <span className={`text-xs ${placeResult.ok ? 'text-green-400' : 'text-red-400'}`}>
              {placeResult.ok ? '✓ ' : '⚠ '}{placeResult.msg}
            </span>
          )}
        </div>
      </div>

      {/* Strategy auto-bot — the server-side engine that trades a strategy's
          signals automatically on every closed candle */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-300">Strategy Auto-Bot</h2>
          <p className="text-xs text-slate-500 mt-1">
            Watches every closed candle of the chosen symbol/interval with the selected strategy.
            When the strategy fires a BUY signal, it opens a virtual position automatically, then
            manages it hands-free (stop-loss, take-profit, trailing stop, partial exits) until close.
            Runs on the server — it keeps trading even if you close this page.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Symbol</label>
            {status?.is_running ? (
              <input value={symbol} disabled
                className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none opacity-50" />
            ) : (
              <SymbolSearchInput value={symbol} onCommit={setSymbol} />
            )}
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Strategy</label>
            <select value={strategy} onChange={e => setStrategy(e.target.value)} disabled={status?.is_running}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none disabled:opacity-50">
              {STRATEGIES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Interval</label>
            <select value={tfInterval} onChange={e => setTfInterval(e.target.value)} disabled={status?.is_running}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none disabled:opacity-50">
              {['1m','3m','5m','15m','30m','1h','4h'].map(i => <option key={i}>{i}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Balance ($)</label>
            <input type="number" value={balance} onChange={e => setBalance(e.target.value)} disabled={status?.is_running}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none disabled:opacity-50" />
          </div>
          <div className="flex items-end">
            {status?.is_running ? (
              <button onClick={handleStop} disabled={busy}
                className="w-full py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
                {busy ? 'Stopping…' : 'Stop'}
              </button>
            ) : (
              <button onClick={handleStart} disabled={busy}
                className="w-full py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg">
                {busy ? 'Starting…' : 'Start'}
              </button>
            )}
          </div>
        </div>
      </div>

      {status && (
        <>
          {/* Status banner */}
          <div className={`rounded-xl p-4 border flex items-center gap-3 ${
            status.is_running
              ? 'bg-green-500/10 border-green-500/30 text-green-400'
              : 'bg-slate-500/10 border-slate-500/20 text-slate-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${status.is_running ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`} />
            <span className="text-sm font-medium">
              {status.is_running ? `Running — ${status.symbol} ${status.interval} · ${status.strategy}` : 'Stopped (engine keeps its state — restart anytime)'}
            </span>
            {status.is_running && (
              <span className="text-xs text-slate-500">
                {status.candles_processed} candle{status.candles_processed === 1 ? '' : 's'} analyzed
                {status.last_price ? ` · last price $${status.last_price.toLocaleString()}` : ''}
                {status.candles_processed === 0 ? ' — waiting for the first candle to close…' : ''}
              </span>
            )}
            {status.last_signal && (
              <span className={`ml-auto text-xs font-bold px-2 py-0.5 rounded ${
                status.last_signal === 'BUY' ? 'bg-green-500/20 text-green-400' :
                status.last_signal === 'SELL' ? 'bg-red-500/20 text-red-400' :
                'bg-slate-500/20 text-slate-400'
              }`}>{status.last_signal}</span>
            )}
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Equity',       value: `$${status.equity.toLocaleString()}` },
              { label: 'Cash',         value: `$${status.cash.toLocaleString()}` },
              { label: 'Realized PnL', value: `$${status.realized_pnl.toFixed(2)}`, color: status.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Total Return', value: `${status.total_return >= 0 ? '+' : ''}${status.total_return.toFixed(2)}%`, color: status.total_return >= 0 ? 'text-green-400' : 'text-red-400' },
            ].map(m => (
              <div key={m.label} className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-4">
                <p className="text-xs text-slate-500 mb-1">{m.label}</p>
                <p className={`text-lg font-semibold ${m.color ?? 'text-white'}`}>{m.value}</p>
              </div>
            ))}
          </div>

          {/* Open position */}
          {status.open_position && (
            <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-indigo-300 mb-3">Open Position (auto-bot)</h3>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-3 text-sm">
                {[
                  ['Entry', `$${status.open_position.entry_price.toFixed(2)}`],
                  ['Current', `$${status.open_position.current_price.toFixed(2)}`],
                  ['Qty', status.open_position.quantity.toFixed(5)],
                  ['Stop', `$${status.open_position.stop_loss.toFixed(2)}`],
                  ['Target', `$${status.open_position.take_profit.toFixed(2)}`],
                  ['PnL', `$${status.open_position.unrealized_pnl.toFixed(2)}`],
                ].map(([l, v]) => (
                  <div key={l}>
                    <p className="text-xs text-slate-500">{l}</p>
                    <p className="text-white font-medium">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Manual paper orders — from the form above, or the "Place Paper Trade" button on Dashboard/Retail Dashboard */}
      {manual && (manual.open_orders.length > 0 || manual.closed_orders.length > 0) && (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Manual Paper Orders — Equity ${manual.equity.toLocaleString()} · Realized PnL ${manual.realized_pnl.toFixed(2)}
          </h3>
          {manual.open_orders.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-slate-500 mb-1">Open ({manual.open_orders.length})</p>
              <div className="space-y-1">
                {manual.open_orders.map(o => {
                  const rr = calcRR(o.entry, o.stop_loss, o.take_profit)
                  const pct = pnlPercent(o, o.unrealized_pnl)
                  return (
                    <div key={o.id} className="flex items-center gap-4 text-xs py-1 border-b border-[#2a2d3e]/50">
                      <span className={`font-bold w-10 ${o.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.direction}</span>
                      <span className="text-slate-300">{o.symbol}</span>
                      <span className="text-slate-500">entry ${o.entry.toFixed(2)}</span>
                      <span className="text-slate-500">now ${o.current_price.toFixed(2)}</span>
                      <span className="text-slate-600">{rr !== null ? `1:${rr.toFixed(2)}` : '—'}</span>
                      <span className={`font-medium ${o.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {o.unrealized_pnl >= 0 ? '+' : ''}${o.unrealized_pnl.toFixed(2)} ({pct >= 0 ? '+' : ''}{pct.toFixed(2)}%)
                      </span>
                      <span className="ml-auto text-indigo-400 text-xs px-1.5 py-0.5 rounded bg-indigo-500/10">MONITORING</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          {manual.closed_orders.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Closed ({manual.closed_orders.length})</p>
              <div className="space-y-1">
                {[...manual.closed_orders].reverse().slice(0, 10).map(o => {
                  const pct = pnlPercent(o, o.realized_pnl)
                  return (
                    <div key={o.id} className="flex items-center gap-4 text-xs py-1 border-b border-[#2a2d3e]/50">
                      <span className={`font-bold w-10 ${o.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.direction}</span>
                      <span className="text-slate-300">{o.symbol}</span>
                      <span className="text-slate-500">${o.entry.toFixed(2)} → ${(o.exit_price ?? o.current_price).toFixed(2)}</span>
                      <span className={`font-medium ${o.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {o.realized_pnl >= 0 ? '+' : ''}${o.realized_pnl.toFixed(2)} ({pct >= 0 ? '+' : ''}{pct.toFixed(2)}%)
                      </span>
                      <span className="text-slate-600">{o.exit_reason}</span>
                      <span className="ml-auto text-slate-700">{o.closed_at ? new Date(o.closed_at).toLocaleTimeString() : ''}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Persisted trade history — durable, survives backend restarts */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">
          Trade History ({persistedTotal} total) — auto-bot + manual, saved to DB
        </h3>
        {persistedTrades.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-6">
            No paper trades yet. Use the Manual Trade Entry form above, start the auto-bot, or use "Place Paper Trade" on a signal card (Dashboard / Retail Dashboard).
          </p>
        ) : (
          <div className="space-y-1">
            {persistedTrades.map(t => (
              <div key={t.id} className="flex items-center gap-4 text-xs py-1.5 border-b border-[#2a2d3e]/50">
                <span className={`font-bold w-10 ${t.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{t.direction}</span>
                <span className="text-slate-300 w-20">{t.symbol}</span>
                <span className="text-slate-500 w-24">{t.strategy}</span>
                <span className="text-slate-500">${t.entry_price.toFixed(2)} → ${t.exit_price.toFixed(2)}</span>
                <span className={`font-medium ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)} ({t.pnl_percent >= 0 ? '+' : ''}{t.pnl_percent.toFixed(2)}%)
                </span>
                <span className="text-slate-600">{t.exit_reason}</span>
                <span className="ml-auto text-slate-700">{new Date(t.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
