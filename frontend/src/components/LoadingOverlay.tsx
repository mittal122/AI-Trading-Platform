/** Full-panel loading state: blurs the content beneath and shows one
 * unmissable centered progress bar — no hunting for a tiny corner spinner.
 * Parent container must be `relative`. */
export default function LoadingOverlay({ show, label }: { show: boolean; label?: string }) {
  if (!show) return null
  return (
    <div
      role="status"
      aria-live="polite"
      className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 rounded-lg bg-bg/55 backdrop-blur-[3px]"
    >
      <div className="w-64 h-1.5 rounded-full bg-line overflow-hidden">
        <div className="tool-scan-bar h-full w-1/3 rounded-full bg-accent" />
      </div>
      <p className="text-xs font-medium text-fg-soft">{label ?? 'Loading…'}</p>
    </div>
  )
}
