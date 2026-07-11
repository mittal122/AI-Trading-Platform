/** Standard EMA: SMA-seeded at index period-1, nulls before that. */
export function computeEma(closes: number[], period: number): (number | null)[] {
  const out: (number | null)[] = new Array(closes.length).fill(null)
  if (period < 1 || closes.length < period) return out
  const k = 2 / (period + 1)
  let seed = 0
  for (let i = 0; i < period; i++) seed += closes[i]
  let prev = seed / period
  out[period - 1] = prev
  for (let i = period; i < closes.length; i++) {
    prev = closes[i] * k + prev * (1 - k)
    out[i] = prev
  }
  return out
}

/** Fibonacci retracement prices: level 0 = the high, 1 = the low. */
export function fibLevels(hi: number, lo: number, levels: number[]): { level: number; price: number }[] {
  return levels.map(level => ({ level, price: hi - (hi - lo) * level }))
}
