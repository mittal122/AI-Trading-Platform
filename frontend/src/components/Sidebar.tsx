import { NavLink } from 'react-router-dom'

const LINKS = [
  { to: '/',          label: 'Dashboard',  icon: '⬡' },
  { to: '/backtest',  label: 'Backtest',   icon: '↺'  },
  { to: '/portfolio', label: 'Portfolio',  icon: '◈'  },
  { to: '/paper',     label: 'Paper Trade',icon: '◻'  },
  { to: '/chat',      label: 'AI Chat',    icon: '✦'  },
  { to: '/patterns',  label: 'Retail Dashboard', icon: '◭'  },
  { to: '/patterns/dashboard', label: 'Pattern Dashboard', icon: '☰'  },
  { to: '/settings',  label: 'Settings',   icon: '⚙'  },
]

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-[#1a1d27] border-r border-[#2a2d3e] flex flex-col">
      <div className="px-5 py-5 border-b border-[#2a2d3e]">
        <p className="text-indigo-400 font-bold text-sm tracking-widest uppercase">AI Trading</p>
        <p className="text-slate-600 text-xs mt-0.5">Platform v1.0</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {LINKS.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-indigo-500/20 text-indigo-300 font-medium'
                  : 'text-slate-400 hover:text-white hover:bg-[#2a2d3e]'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-[#2a2d3e]">
        <p className="text-xs text-slate-600">API: localhost:8000</p>
      </div>
    </aside>
  )
}
