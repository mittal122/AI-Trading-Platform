import { useEffect, useRef, useState } from 'react'
import { Settings2, X } from 'lucide-react'

export interface IndicatorConfig {
  emaPeriods: number[]
  fibLevels: number[]
  fibLookback: number
}

const CANONICAL_FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
const MAX_EMA_PERIODS = 5

/** Gear button + popover for chart-indicator configuration (EMA periods, fib levels). */
export default function IndicatorSettings({ showEma, value, onChange }: {
  showEma?: boolean
  value: IndicatorConfig
  onChange: (v: IndicatorConfig) => void
}) {
  const [open, setOpen] = useState(false)
  const [periodInput, setPeriodInput] = useState('')
  const [lookbackInput, setLookbackInput] = useState(String(value.fibLookback))
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function addPeriod() {
    const p = Number(periodInput)
    if (!Number.isInteger(p) || p < 2 || p > 500) return
    if (value.emaPeriods.includes(p) || value.emaPeriods.length >= MAX_EMA_PERIODS) return
    onChange({ ...value, emaPeriods: [...value.emaPeriods, p].sort((a, b) => a - b) })
    setPeriodInput('')
  }

  function toggleFibLevel(level: number) {
    const on = value.fibLevels.includes(level)
    onChange({
      ...value,
      fibLevels: on
        ? value.fibLevels.filter(l => l !== level)
        : [...value.fibLevels, level].sort((a, b) => a - b),
    })
  }

  function commitLookback() {
    const n = Number(lookbackInput)
    if (!Number.isFinite(n)) { setLookbackInput(String(value.fibLookback)); return }
    const clamped = Math.min(1000, Math.max(20, Math.round(n)))
    setLookbackInput(String(clamped))
    onChange({ ...value, fibLookback: clamped })
  }

  return (
    <div ref={wrapRef} className="relative">
      <button onClick={() => setOpen(o => !o)} aria-label="Indicator settings"
        className={`text-[11px] px-2 py-1 rounded-md border cursor-pointer transition-colors ${
          open ? 'bg-accent-soft text-accent border-accent/30'
            : 'bg-raised border-line text-fg-faint hover:text-fg-soft'}`}>
        <Settings2 size={12} aria-hidden />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 z-30 w-64 card p-3 space-y-3">
          {showEma && (
            <section>
              <p className="panel-title mb-2">EMA Periods</p>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {value.emaPeriods.length === 0 && (
                  <span className="text-[11px] text-fg-faint">No EMAs added.</span>
                )}
                {value.emaPeriods.map(p => (
                  <span key={p} className="chip chip-muted">
                    <span className="num">{p}</span>
                    <button
                      onClick={() => onChange({ ...value, emaPeriods: value.emaPeriods.filter(x => x !== p) })}
                      aria-label={`Remove EMA ${p}`}
                      className="cursor-pointer text-fg-faint hover:text-down">
                      <X size={10} aria-hidden />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-1.5">
                <input type="number" min={2} max={500} value={periodInput}
                  onChange={e => setPeriodInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') addPeriod() }}
                  placeholder="Period" aria-label="New EMA period"
                  className="input w-20 text-xs" />
                <button onClick={addPeriod}
                  disabled={value.emaPeriods.length >= MAX_EMA_PERIODS}
                  className="btn h-7 text-[11px]">Add</button>
              </div>
            </section>
          )}
          <section>
            <p className="panel-title mb-2">Fibonacci Levels</p>
            <div className="grid grid-cols-2 gap-1">
              {CANONICAL_FIB_LEVELS.map(l => (
                <label key={l} className="flex items-center gap-1.5 text-[12px] text-fg-soft cursor-pointer">
                  <input type="checkbox" checked={value.fibLevels.includes(l)}
                    onChange={() => toggleFibLevel(l)}
                    className="accent-accent cursor-pointer" />
                  <span className="num">{l}</span>
                </label>
              ))}
            </div>
            <div className="mt-2">
              <label htmlFor="fib-lookback" className="field-label">Anchor lookback (bars)</label>
              <input id="fib-lookback" type="number" min={20} max={1000} value={lookbackInput}
                onChange={e => setLookbackInput(e.target.value)}
                onBlur={commitLookback}
                onKeyDown={e => { if (e.key === 'Enter') commitLookback() }}
                className="input w-24 text-xs" />
              <p className="text-[10.5px] text-fg-faint mt-1">
                Only applies where auto-anchoring uses a rolling window.
              </p>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
