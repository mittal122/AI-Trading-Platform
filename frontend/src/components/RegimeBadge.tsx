const COLORS: Record<string, string> = {
  STRONG_BULL: 'chip-up',
  WEAK_BULL:   'chip-up',
  STRONG_BEAR: 'chip-down',
  WEAK_BEAR:   'chip-down',
  SIDEWAYS:    'chip-warn',
}

export default function RegimeBadge({ regime }: { regime?: string }) {
  if (!regime) return null
  const cls = COLORS[regime] ?? 'chip-muted'
  return (
    <span className={`chip ${cls}`}>
      {regime.replace('_', ' ')}
    </span>
  )
}
