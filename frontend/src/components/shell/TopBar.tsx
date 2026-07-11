import { useEffect, useState } from 'react'
import { Activity } from 'lucide-react'
import { getMarketOverview } from '../../api/client'
import type { Ticker24h } from '../../api/client'

const OVERVIEW_POLL_MS = 20_000

/** Command bar: brand mark, scrolling market tape, backend status, UTC clock. */
export default function TopBar() {
  const [tape, setTape] = useState<Ticker24h[]>([])
  const [online, setOnline] = useState<boolean | null>(null)
  const [clock, setClock] = useState(() => utcNow())

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const { data } = await getMarketOverview()
        if (!alive) return
        const seen = new Set<string>()
        const rows = [data.btc, data.eth, ...data.volume_leaders, ...data.top_gainers]
          .filter((t): t is Ticker24h => !!t)
          .filter(t => !seen.has(t.symbol) && seen.add(t.symbol) !== undefined)
          .slice(0, 12)
        setTape(rows)
        setOnline(true)
      } catch {
        if (alive) setOnline(false)
      }
    }
    load()
    const id = window.setInterval(load, OVERVIEW_POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [])

  useEffect(() => {
    const id = window.setInterval(() => setClock(utcNow()), 1000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <header className="h-11 shrink-0 bg-surface border-b border-line flex items-center gap-4 pl-4 pr-3 select-none">
      <div className="flex items-center gap-2 shrink-0">
        <Activity size={16} strokeWidth={2.25} className="text-accent" aria-hidden />
        <span className="text-[13px] font-semibold tracking-[0.14em] text-fg">TERMINAL</span>
        <span className="text-[10px] font-medium tracking-widest text-fg-faint mt-px">AI TRADING</span>
      </div>

      {/* Market tape — duplicated content for a seamless loop */}
      <div className="flex-1 overflow-hidden relative h-full" aria-hidden={tape.length === 0}>
        {tape.length > 0 && (
          <div className="tape-scroll absolute inset-y-0 flex items-center gap-6 whitespace-nowrap will-change-transform">
            {[...tape, ...tape].map((t, i) => (
              <TapeItem key={`${t.symbol}-${i}`} t={t} />
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <span className="flex items-center gap-1.5 text-[11px] text-fg-soft" title="Backend connection">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              online === null ? 'bg-fg-faint' : online ? 'bg-up' : 'bg-down'
            }`}
          />
          {online === null ? 'connecting' : online ? 'live' : 'offline'}
        </span>
        <span className="num text-[11px] text-fg-faint border-l border-line pl-3">{clock} UTC</span>
      </div>
    </header>
  )
}

function TapeItem({ t }: { t: Ticker24h }) {
  const up = t.price_change_pct >= 0
  return (
    <span className="flex items-center gap-1.5 text-[11px]">
      <span className="font-medium text-fg-soft">{t.symbol.replace('USDT', '')}</span>
      <span className="num text-fg">{fmtPrice(t.last_price)}</span>
      <span className={`num font-medium ${up ? 'text-up' : 'text-down'}`}>
        {up ? '+' : ''}{t.price_change_pct.toFixed(2)}%
      </span>
    </span>
  )
}

function fmtPrice(p: number): string {
  if (p >= 1000) return p.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (p >= 1) return p.toFixed(2)
  return p.toPrecision(3)
}

function utcNow(): string {
  return new Date().toISOString().slice(11, 19)
}
