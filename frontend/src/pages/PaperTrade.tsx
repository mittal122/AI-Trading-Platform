import { useEffect, useRef, useState } from 'react'
import { getPaperStatus, startPaper, stopPaper, getManualOrders, getTradeHistory } from '../api/client'
import type { PaperStatus, ManualPaperStatus, TradeHistoryItem } from '../api/client'
import { usePersistedState } from '../hooks/usePersistedState'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']

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

      {/* Config */}
      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Symbol</label>
            <input value={symbol} onChange={e => setSymbol(e.target.value)} disabled={status?.is_running}
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none disabled:opacity-50" />
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

      {/* Manual paper orders — from the "Place Paper Trade" button on Dashboard/Signals */}
      {manual && (manual.open_orders.length > 0 || manual.closed_orders.length > 0) && (
        <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Manual Paper Orders — Equity ${manual.equity.toLocaleString()} · Realized PnL ${manual.realized_pnl.toFixed(2)}
          </h3>
          {manual.open_orders.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-slate-500 mb-1">Open ({manual.open_orders.length})</p>
              <div className="space-y-1">
                {manual.open_orders.map(o => (
                  <div key={o.id} className="flex items-center gap-4 text-xs py-1 border-b border-[#2a2d3e]/50">
                    <span className={`font-bold w-10 ${o.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.direction}</span>
                    <span className="text-slate-300">{o.symbol}</span>
                    <span className="text-slate-500">entry ${o.entry.toFixed(2)}</span>
                    <span className="text-slate-500">now ${o.current_price.toFixed(2)}</span>
                    <span className={`font-medium ${o.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${o.unrealized_pnl.toFixed(2)}</span>
                    <span className="ml-auto text-indigo-400 text-xs px-1.5 py-0.5 rounded bg-indigo-500/10">MONITORING</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {manual.closed_orders.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1">Closed ({manual.closed_orders.length})</p>
              <div className="space-y-1">
                {[...manual.closed_orders].reverse().slice(0, 10).map(o => (
                  <div key={o.id} className="flex items-center gap-4 text-xs py-1 border-b border-[#2a2d3e]/50">
                    <span className={`font-bold w-10 ${o.direction === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.direction}</span>
                    <span className="text-slate-300">{o.symbol}</span>
                    <span className="text-slate-500">${o.entry.toFixed(2)} → ${(o.exit_price ?? o.current_price).toFixed(2)}</span>
                    <span className={`font-medium ${o.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>${o.realized_pnl.toFixed(2)}</span>
                    <span className="text-slate-600">{o.exit_reason}</span>
                    <span className="ml-auto text-slate-700">{o.closed_at ? new Date(o.closed_at).toLocaleTimeString() : ''}</span>
                  </div>
                ))}
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
            No paper trades yet. Start the auto-bot above, or use "Place Paper Trade" on a signal card (Dashboard / Signals).
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
