import type { TradeHistoryItem } from '../api/client'

export default function TradeTable({ trades }: { trades: TradeHistoryItem[] }) {
  if (!trades.length) {
    return <p className="text-slate-500 text-sm text-center py-8">No trades yet</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-500 border-b border-[#2a2d3e]">
            <th className="pb-2 pr-4">Symbol</th>
            <th className="pb-2 pr-4">Strategy</th>
            <th className="pb-2 pr-4">Mode</th>
            <th className="pb-2 pr-4">Entry</th>
            <th className="pb-2 pr-4">Exit</th>
            <th className="pb-2 pr-4">PnL</th>
            <th className="pb-2 pr-4">PnL %</th>
            <th className="pb-2 pr-4">Reason</th>
            <th className="pb-2">Date</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b border-[#2a2d3e]/50 hover:bg-[#1a1d27]/50">
              <td className="py-2 pr-4 font-medium">{t.symbol}</td>
              <td className="py-2 pr-4 text-slate-400">{t.strategy}</td>
              <td className="py-2 pr-4">
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  t.mode === 'LIVE' ? 'bg-red-500/20 text-red-400' :
                  t.mode === 'PAPER' ? 'bg-indigo-500/20 text-indigo-400' :
                  'bg-slate-500/20 text-slate-400'
                }`}>{t.mode}</span>
              </td>
              <td className="py-2 pr-4 text-slate-300">${t.entry_price.toFixed(2)}</td>
              <td className="py-2 pr-4 text-slate-300">${t.exit_price.toFixed(2)}</td>
              <td className={`py-2 pr-4 font-semibold ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
              </td>
              <td className={`py-2 pr-4 ${t.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {t.pnl_percent >= 0 ? '+' : ''}{t.pnl_percent.toFixed(2)}%
              </td>
              <td className="py-2 pr-4 text-slate-500 text-xs">{t.exit_reason}</td>
              <td className="py-2 text-slate-600 text-xs">{t.created_at.slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
