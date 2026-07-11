import type { PortfolioAnalytics } from '../api/client'

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card px-3 py-2.5">
      <p className="panel-title mb-1">{label}</p>
      <p className="num text-[15px] font-semibold leading-tight text-fg">{value}</p>
      {sub && <p className="num text-[10.5px] text-fg-faint mt-0.5">{sub}</p>}
    </div>
  )
}

export default function PortfolioSummary({ data }: { data: PortfolioAnalytics }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Total Return" value={`${data.total_return >= 0 ? '+' : ''}${data.total_return.toFixed(2)}%`} sub={`$${data.initial_balance.toLocaleString()} → $${data.ending_balance.toLocaleString()}`} />
        <Metric label="Win Rate" value={`${data.win_rate.toFixed(1)}%`} sub={`${data.winning_trades}W / ${data.losing_trades}L`} />
        {/* null = backend's float('inf') (no losing trades) — JSON drops Infinity */}
        <Metric label="Profit Factor" value={data.profit_factor == null ? 'inf' : data.profit_factor.toFixed(2)} />
        <Metric label="Max Drawdown" value={`${data.max_drawdown.toFixed(2)}%`} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Sharpe Ratio" value={data.sharpe_ratio.toFixed(3)} />
        <Metric label="Sortino Ratio" value={data.sortino_ratio.toFixed(3)} />
        <Metric label="Calmar Ratio" value={data.calmar_ratio.toFixed(3)} />
        <Metric label="Expectancy" value={`$${data.expectancy.toFixed(2)}`} sub="per trade" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Metric label="Total Trades" value={String(data.total_trades)} />
        <Metric label="Avg Win" value={`$${data.avg_win.toFixed(2)}`} />
        <Metric label="Avg Loss" value={`$${data.avg_loss.toFixed(2)}`} />
      </div>
    </div>
  )
}
