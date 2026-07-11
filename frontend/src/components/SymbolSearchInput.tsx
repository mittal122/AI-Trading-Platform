import { useEffect, useRef, useState } from 'react'
import { getSymbols } from '../api/client'
import type { ExchangeSymbol } from '../api/client'

// Module-level cache — every screen embeds this component, but the ~1,300
// tradeable symbols only need to be fetched once per page load, not once
// per screen.
let symbolsCache: ExchangeSymbol[] | null = null
let symbolsPromise: Promise<ExchangeSymbol[]> | null = null

function loadSymbols(): Promise<ExchangeSymbol[]> {
  if (symbolsCache) return Promise.resolve(symbolsCache)
  if (!symbolsPromise) {
    symbolsPromise = getSymbols()
      .then(res => { symbolsCache = res.data.symbols; return symbolsCache })
      .catch(() => [])
  }
  return symbolsPromise
}

const MAX_SUGGESTIONS = 30

export default function SymbolSearchInput({ value, onCommit, className }: {
  value: string
  /** Called once a symbol is chosen — via dropdown click, Enter, or blur (typed text, uppercased). */
  onCommit: (symbol: string) => void
  className?: string
}) {
  const [symbols, setSymbols] = useState<ExchangeSymbol[]>(symbolsCache ?? [])
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => { loadSymbols().then(setSymbols) }, [])
  useEffect(() => { setQuery(value) }, [value])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const q = query.trim().toUpperCase()
  const filtered = (q ? symbols.filter(s => s.symbol.includes(q)) : symbols).slice(0, MAX_SUGGESTIONS)

  function commit(raw: string) {
    const next = raw.trim().toUpperCase()
    if (next) onCommit(next)
    setOpen(false)
  }

  return (
    <div ref={boxRef} className={`relative ${className ?? ''}`}>
      <input
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true); setHighlight(0) }}
        onFocus={() => setOpen(true)}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            const picked = open && filtered[highlight] ? filtered[highlight].symbol : query
            commit(picked)
          } else if (e.key === 'ArrowDown') {
            e.preventDefault(); setHighlight(h => Math.min(h + 1, filtered.length - 1))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault(); setHighlight(h => Math.max(h - 1, 0))
          } else if (e.key === 'Escape') {
            setOpen(false)
          }
        }}
        onBlur={() => window.setTimeout(() => { if (!boxRef.current?.contains(document.activeElement)) commit(query) }, 120)}
        placeholder="Search symbol…"
        className="input input-mono w-full"
      />
      {open && filtered.length > 0 && (
        <div className="absolute z-20 mt-1 w-full max-h-64 overflow-y-auto bg-surface border border-line rounded-lg shadow-lg">
          {filtered.map((s, i) => (
            <button
              key={s.symbol}
              type="button"
              onMouseDown={e => e.preventDefault()}
              onClick={() => commit(s.symbol)}
              className={`w-full flex items-center justify-between px-3 py-1.5 text-left text-[12.5px] cursor-pointer ${
                i === highlight ? 'bg-accent-soft text-accent' : 'text-fg-soft hover:bg-raised'
              }`}
            >
              <span className="num font-medium">{s.symbol}</span>
              <span className="text-[11px] text-fg-faint">{s.base_asset}/{s.quote_asset}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
