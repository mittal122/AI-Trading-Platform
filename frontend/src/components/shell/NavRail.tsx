import { NavLink } from 'react-router-dom'
import {
  CandlestickChart, ScanSearch, LayoutGrid, Layers,
  FlaskConical, NotebookPen, PieChart, Settings,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const LINKS: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: '/',                  label: 'Terminal',  icon: CandlestickChart, end: true },
  { to: '/patterns',          label: 'Analysis',  icon: ScanSearch },
  { to: '/patterns/dashboard', label: 'Patterns', icon: LayoutGrid },
  { to: '/smc',               label: 'SMC',       icon: Layers },
  { to: '/backtest',          label: 'Backtest',  icon: FlaskConical },
  { to: '/paper',             label: 'Paper',     icon: NotebookPen },
  { to: '/portfolio',         label: 'Portfolio', icon: PieChart },
]

export default function NavRail() {
  return (
    <aside className="w-14 shrink-0 bg-surface border-r border-line flex flex-col items-center py-2">
      <nav className="flex-1 flex flex-col items-center gap-1 w-full px-2">
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <RailLink key={to} to={to} label={label} icon={Icon} end={end} />
        ))}
      </nav>
      <div className="w-full px-2 pb-1">
        <RailLink to="/settings" label="Settings" icon={Settings} />
      </div>
    </aside>
  )
}

function RailLink({ to, label, icon: Icon, end }: { to: string; label: string; icon: LucideIcon; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      aria-label={label}
      className={({ isActive }) =>
        `group relative flex flex-col items-center gap-0.5 w-full py-2 rounded-md cursor-pointer transition-colors duration-150 ${
          isActive ? 'text-accent bg-accent-soft' : 'text-fg-faint hover:text-fg-soft hover:bg-raised'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-0.5 rounded-r bg-accent" />}
          <Icon size={18} strokeWidth={1.75} />
          <span className="text-[9px] font-medium leading-none tracking-wide">{label}</span>
        </>
      )}
    </NavLink>
  )
}
