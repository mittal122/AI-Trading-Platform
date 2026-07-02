const COLORS: Record<string, string> = {
  STRONG_BULL: 'bg-green-500/20 text-green-400 border-green-500/30',
  WEAK_BULL:   'bg-green-500/10 text-green-500 border-green-500/20',
  STRONG_BEAR: 'bg-red-500/20 text-red-400 border-red-500/30',
  WEAK_BEAR:   'bg-red-500/10 text-red-500 border-red-500/20',
  SIDEWAYS:    'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
}

export default function RegimeBadge({ regime }: { regime?: string }) {
  if (!regime) return null
  const cls = COLORS[regime] ?? 'bg-slate-500/10 text-slate-400 border-slate-500/20'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cls}`}>
      {regime.replace('_', ' ')}
    </span>
  )
}
