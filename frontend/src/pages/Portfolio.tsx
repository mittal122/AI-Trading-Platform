import { useEffect, useState } from 'react'
import { getPortfolioAnalytics, getTradeHistory } from '../api/client'
import type { TradeHistoryItem, PortfolioAnalytics } from '../api/client'

const STRATEGIES = ['rsi', 'ema', 'macd', 'breakout', 'supertrend', 'cta_trend', 'turtle', 'engulfing_scalp']
const MODES = ['', 'PAPER', 'LIVE', 'BACKTEST']

const signCls = (v: number) => (v >= 0 ? 'text-up' : 'text-down')
const signed = (v: number, suffix = '') => `${v >= 0 ? '+' : ''}${v.toFixed(2)}${suffix}`

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
    <div className="p-3 space-y-3 max-w-[1800px] mx-auto">
      {/* Strategy selector toolbar */}
      <div className="card flex items-center gap-2 px-3 py-2 flex-wrap">
        <span className="panel-title mr-1">Strategy</span>
        {STRATEGIES.map(s => (
          <button key={s} onClick={() => setStrategy(s)}
            className={`h-6 px-2 rounded text-[11px] font-medium cursor-pointer transition-colors ${strategy === s
              ? 'bg-accent-soft text-accent'
              : 'text-fg-faint hover:text-fg-soft hover:bg-raised'
            }`}>{s}</button>
        ))}
      </div>

      {loading ? (
        <p className="text-fg-faint text-xs px-1">Loading analytics…</p>
      ) : analytics ? (
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          <Stat label="Total Return" value={signed(analytics.total_return, '%')}
            valueCls={signCls(analytics.total_return)}
            sub={`$${analytics.initial_balance.toLocaleString()} → $${analytics.ending_balance.toLocaleString()}`} />
          <Stat label="Win Rate" value={`${analytics.win_rate.toFixed(1)}%`}
            sub={`${analytics.winning_trades}W / ${analytics.losing_trades}L`} />
          <Stat label="Profit Factor"
            value={analytics.profit_factor === Infinity ? 'inf' : analytics.profit_factor.toFixed(2)}
            valueCls={analytics.profit_factor >= 1 ? 'text-up' : 'text-down'} />
          <Stat label="Max Drawdown" value={`${analytics.max_drawdown.toFixed(2)}%`}
            valueCls={analytics.max_drawdown > 0 ? 'text-down' : undefined} />
          <Stat label="Sharpe Ratio" value={analytics.sharpe_ratio.toFixed(3)}
            valueCls={signCls(analytics.sharpe_ratio)} />
          <Stat label="Sortino Ratio" value={analytics.sortino_ratio.toFixed(3)}
            valueCls={signCls(analytics.sortino_ratio)} />
          <Stat label="Calmar Ratio" value={analytics.calmar_ratio.toFixed(3)}
            valueCls={signCls(analytics.calmar_ratio)} />
          <Stat label="Expectancy" value={`$${analytics.expectancy.toFixed(2)}`}
            valueCls={signCls(analytics.expectancy)} sub="per trade" />
          <Stat label="Total Trades" value={String(analytics.total_trades)} />
          <Stat label="Avg Win" value={`$${analytics.avg_win.toFixed(2)}`} valueCls="text-up" />
          <Stat label="Avg Loss" value={`$${analytics.avg_loss.toFixed(2)}`} valueCls="text-down" />
        </div>
      ) : null}

      {/* Trade history */}
      <section className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2">
          <h2 className="panel-title">Trade History <span className="num text-fg-faint">({total})</span></h2>
          <div className="flex items-center gap-1">
            {MODES.map(m => (
              <button key={m} onClick={() => setModeFilter(m)}
                className={`h-5 px-1.5 rounded text-[10px] font-medium cursor-pointer transition-colors ${modeFilter === m
                  ? 'bg-accent-soft text-accent'
                  : 'text-fg-faint hover:text-fg-soft'
                }`}>{m || 'All'}</button>
            ))}
          </div>
        </header>
        <div className="overflow-x-auto pb-1.5">
          {trades.length === 0 ? (
            <p className="text-fg-faint text-xs text-center py-6">No trades yet</p>
          ) : (
            <table className="w-full text-[12.5px]">
              <thead>
                <tr>
                  <th className="th pl-3">Symbol</th>
                  <th className="th">Strategy</th>
                  <th className="th">Mode</th>
                  <th className="th">Entry</th>
                  <th className="th">Exit</th>
                  <th className="th">PnL</th>
                  <th className="th">PnL %</th>
                  <th className="th">Reason</th>
                  <th className="th">Duration</th>
                  <th className="th pr-3">Date</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id} className="row-hover">
                    <td className="td pl-3 font-medium text-fg">{t.symbol}</td>
                    <td className="td text-fg-soft">{t.strategy}</td>
                    <td className="td">
                      <span className={`chip ${t.mode === 'LIVE' ? 'chip-warn' : 'chip-muted'}`}>{t.mode}</span>
                    </td>
                    <td className="td num text-fg-soft">${t.entry_price.toFixed(2)}</td>
                    <td className="td num text-fg-soft">${t.exit_price.toFixed(2)}</td>
                    <td className={`td num font-semibold ${signCls(t.pnl)}`}>
                      {t.pnl >= 0 ? '+' : '-'}${Math.abs(t.pnl).toFixed(2)}
                    </td>
                    <td className={`td num ${signCls(t.pnl_percent)}`}>
                      {signed(t.pnl_percent, '%')}
                    </td>
                    <td className="td text-fg-faint text-[11px]">{t.exit_reason}</td>
                    <td className="td num text-fg-faint text-[11px]">{t.duration_display || '—'}</td>
                    <td className="td num pr-3 text-fg-faint text-[11px]">{t.created_at.slice(0, 10)}</td>
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

function Stat({ label, value, valueCls, sub }: {
  label: string; value: string; valueCls?: string; sub?: string
}) {
  return (
    <div className="card px-3 py-2.5">
      <p className="panel-title mb-1">{label}</p>
      <p className={`num text-[15px] font-semibold leading-tight ${valueCls ?? 'text-fg'}`}>{value}</p>
      {sub && <p className="num text-[10.5px] text-fg-faint mt-0.5">{sub}</p>}
    </div>
  )
}
