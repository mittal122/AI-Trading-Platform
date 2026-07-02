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

  function set(next: T) {
    setValue(next)
    try {
      localStorage.setItem(key, JSON.stringify(next))
    } catch {
      // storage unavailable (private mode, quota) — state still works in-memory
    }
  }

  return [value, set] as const
}
