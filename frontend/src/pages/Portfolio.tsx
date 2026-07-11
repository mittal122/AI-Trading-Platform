import { useEffect, useMemo, useState } from 'react'
import { getHistoryAnalytics, getTradeHistory } from '../api/client'
import type { TradeHistoryItem, PortfolioAnalytics } from '../api/client'
import LoadingOverlay from '../components/LoadingOverlay'

const MODES = ['', 'PAPER', 'LIVE', 'BACKTEST']

const signCls = (v: number) => (v >= 0 ? 'text-up' : 'text-down')
const signed = (v: number, suffix = '') => `${v >= 0 ? '+' : ''}${v.toFixed(2)}${suffix}`

export default function Portfolio() {
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null)
  const [trades, setTrades]       = useState<TradeHistoryItem[]>([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(true)
  // '' = all strategies. The pill list is discovered from the actual trade
  // rows (real recorded values like 'smc', 'Supertrend', 'manual') — not a
  // hardcoded list that can drift from what's really in the DB.
  const [strategy, setStrategy]   = useState('')
  const [modeFilter, setModeFilter] = useState('')

  async function load() {
    setLoading(true)
    try {
      const params = {
        mode: modeFilter || undefined,
        strategy: strategy || undefined,
      }
      const [anlRes, trdRes] = await Promise.all([
        getHistoryAnalytics(params),
        getTradeHistory({ ...params, limit: 50 }),
      ])
      setAnalytics(anlRes.data)
      setTrades(trdRes.data.trades)
      setTotal(trdRes.data.total)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [strategy, modeFilter])

  const strategyOptions = useMemo(() => {
    const seen = new Set(trades.map(t => t.strategy))
    if (strategy) seen.add(strategy) // keep the active pill visible even if filtered rows shrink
    return ['', ...[...seen].sort()]
  }, [trades, strategy])

  return (
    <div className="relative p-3 space-y-3 max-w-[1800px] mx-auto">
      <LoadingOverlay show={loading} label="Loading your trading record…" />

      {/* Filters — these drive BOTH the stats and the table (real data only) */}
      <div className="card flex items-center gap-2 px-3 py-2 flex-wrap">
        <span className="panel-title mr-1">Account</span>
        {MODES.map(m => (
          <button key={m} onClick={() => setModeFilter(m)}
            className={`h-6 px-2 rounded text-[11px] font-medium cursor-pointer transition-colors ${modeFilter === m
              ? 'bg-accent-soft text-accent'
              : 'text-fg-faint hover:text-fg-soft hover:bg-raised'
            }`}>{m || 'Paper + Live'}</button>
        ))}
        <span className="panel-title ml-3 mr-1">Strategy</span>
        {strategyOptions.map(s => (
          <button key={s || 'all'} onClick={() => setStrategy(s)}
            className={`h-6 px-2 rounded text-[11px] font-medium cursor-pointer transition-colors ${strategy === s
              ? 'bg-accent-soft text-accent'
              : 'text-fg-faint hover:text-fg-soft hover:bg-raised'
            }`}>{s || 'All'}</button>
        ))}
      </div>

      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
          <Stat label="Total Return" value={signed(analytics.total_return, '%')}
            valueCls={signCls(analytics.total_return)}
            sub={`$${analytics.initial_balance.toLocaleString(undefined, { maximumFractionDigits: 2 })} → $${analytics.ending_balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`} />
          <Stat label="Realized PnL"
            value={`${analytics.ending_balance >= analytics.initial_balance ? '+' : '-'}$${Math.abs(analytics.ending_balance - analytics.initial_balance).toFixed(2)}`}
            valueCls={signCls(analytics.ending_balance - analytics.initial_balance)}
            sub={`${analytics.total_trades} closed trades`} />
          <Stat label="Win Rate" value={`${analytics.win_rate.toFixed(1)}%`}
            sub={`${analytics.winning_trades}W / ${analytics.losing_trades}L`} />
          <Stat label="Profit Factor"
            value={analytics.profit_factor == null ? 'inf' : analytics.profit_factor.toFixed(2)}
            valueCls={analytics.profit_factor == null || analytics.profit_factor >= 1 ? 'text-up' : 'text-down'} />
          <Stat label="Max Drawdown" value={`${analytics.max_drawdown.toFixed(2)}%`}
            valueCls={analytics.max_drawdown > 0 ? 'text-down' : undefined} />
          <Stat label="Expectancy" value={`$${analytics.expectancy.toFixed(2)}`}
            valueCls={signCls(analytics.expectancy)} sub="per trade" />
          <Stat label="Sharpe Ratio" value={analytics.sharpe_ratio.toFixed(3)}
            valueCls={signCls(analytics.sharpe_ratio)} />
          <Stat label="Sortino Ratio" value={analytics.sortino_ratio.toFixed(3)}
            valueCls={signCls(analytics.sortino_ratio)} />
          <Stat label="Calmar Ratio" value={analytics.calmar_ratio.toFixed(3)}
            valueCls={signCls(analytics.calmar_ratio)} />
          <Stat label="Total Trades" value={String(analytics.total_trades)} />
          <Stat label="Avg Win" value={`$${analytics.avg_win.toFixed(2)}`} valueCls="text-up" />
          <Stat label="Avg Loss" value={`$${analytics.avg_loss.toFixed(2)}`} valueCls="text-down" />
        </div>
      )}

      {/* Trade history */}
      <section className="card">
        <header className="flex items-center justify-between px-3 pt-3 pb-2">
          <h2 className="panel-title">Trade History <span className="num text-fg-faint">({total})</span></h2>
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
