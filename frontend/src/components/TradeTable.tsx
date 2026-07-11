import type { TradeHistoryItem } from '../api/client'

const MODE_CHIP: Record<string, string> = {
  LIVE: 'chip-warn',
  PAPER: 'chip-muted',
}

export default function TradeTable({ trades }: { trades: TradeHistoryItem[] }) {
  if (!trades.length) {
    return <p className="text-fg-faint text-sm text-center py-8">No trades yet</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left">
            <th className="th">Symbol</th>
            <th className="th">Strategy</th>
            <th className="th">Mode</th>
            <th className="th">Entry</th>
            <th className="th">Exit</th>
            <th className="th">PnL</th>
            <th className="th">PnL %</th>
            <th className="th">Reason</th>
            <th className="th">Duration</th>
            <th className="th">Date</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="row-hover">
              <td className="td font-medium text-fg">{t.symbol}</td>
              <td className="td">{t.strategy}</td>
              <td className="td">
                <span className={`chip ${MODE_CHIP[t.mode] ?? 'chip-muted'}`}>{t.mode}</span>
              </td>
              <td className="td num">${t.entry_price.toFixed(2)}</td>
              <td className="td num">${t.exit_price.toFixed(2)}</td>
              <td className={`td num font-semibold ${t.pnl >= 0 ? 'text-up' : 'text-down'}`}>
                {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
              </td>
              <td className={`td num ${t.pnl_percent >= 0 ? 'text-up' : 'text-down'}`}>
                {t.pnl_percent >= 0 ? '+' : ''}{t.pnl_percent.toFixed(2)}%
              </td>
              <td className="td text-xs text-fg-faint">{t.exit_reason}</td>
              <td className="td num text-xs text-fg-faint">{t.duration_display || '—'}</td>
              <td className="td num text-xs text-fg-faint">{t.created_at.slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
