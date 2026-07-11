import { useState } from 'react'

/** useState that survives a page refresh via localStorage, scoped by key. */
export function usePersistedState<T>(key: string, defaultValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key)
      return stored !== null ? (JSON.parse(stored) as T) : defaultValue
    } catch {
      return defaultValue
    }
  })

  function set(next: T | ((prev: T) => T)) {
    setValue(prev => {
      // Resolve functional updaters HERE so the persisted value is the real
      // next state — passing the updater function itself to JSON.stringify
      // wrote the string "undefined" and silently killed persistence for
      // every functional set (e.g. the SMC layer toggles).
      const resolved = typeof next === 'function' ? (next as (prev: T) => T)(prev) : next
      try {
        localStorage.setItem(key, JSON.stringify(resolved))
      } catch {
        // storage unavailable (private mode, quota) — state still works in-memory
      }
      return resolved
    })
  }

  return [value, set] as const
}
