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

// ── Automatic trend line — the classical charting rules ──────────────────────
//
// A valid trend line, by the universal textbook definition:
//   1. UP trend line: a RISING straight line connecting swing LOWS, drawn
//      under price. DOWN trend line: a FALLING line connecting swing HIGHS,
//      drawn above price.
//   2. It needs at least 2 pivot touches (3+ makes it a strong line).
//   3. Price must never CUT THROUGH it between the first anchor and now —
//      a line that price closed beyond is broken, not a trend line.
//   4. Among all valid candidate lines, the best one touches the most pivots.
//
// The algorithm tries every pair of pivots as anchors, rejects any candidate
// that rule 3 invalidates (with a small ATR-based wick tolerance), and scores
// the survivors by touches first, then recency of the second anchor.

export interface PivotPoint { index: number; price: number }
export interface TrendlineFit {
  i1: number; price1: number   // first anchor (bar index into `bars`)
  i2: number; price2: number   // second anchor
  endValue: number             // line projected to the last bar
  touches: number
}

export function bestPivotTrendline(
  bars: { high: number; low: number }[],
  pivots: PivotPoint[],
  kind: 'support' | 'resistance',
  tolerance: number,
): TrendlineFit | null {
  const n = bars.length
  if (n < 3 || pivots.length < 2) return null
  const isSupport = kind === 'support'

  let best: TrendlineFit | null = null
  let bestScore = -Infinity

  for (let a = 0; a < pivots.length - 1; a++) {
    for (let b = a + 1; b < pivots.length; b++) {
      const p1 = pivots[a], p2 = pivots[b]
      if (p2.index <= p1.index) continue
      const slope = (p2.price - p1.price) / (p2.index - p1.index)
      // Rule 1: up trend lines rise, down trend lines fall.
      if (isSupport ? slope <= 0 : slope >= 0) continue

      const lineAt = (i: number) => p1.price + slope * (i - p1.index)

      // Rule 3: no bar between the first anchor and the live edge may close
      // through the line (wicks get the tolerance; bodies get none).
      let violated = false
      for (let i = p1.index; i < n; i++) {
        const v = lineAt(i)
        if (isSupport ? bars[i].low < v - tolerance : bars[i].high > v + tolerance) {
          violated = true
          break
        }
      }
      if (violated) continue

      // Rule 2/4: count pivot touches within tolerance.
      let touches = 0
      for (const p of pivots) {
        if (p.index < p1.index) continue
        if (Math.abs(p.price - lineAt(p.index)) <= tolerance) touches++
      }
      if (touches < 2) continue

      // More touches wins; ties go to the line anchored closest to now,
      // then to the longer base.
      const score = touches * 10_000 + p2.index + (p2.index - p1.index) * 0.01
      if (score > bestScore) {
        bestScore = score
        best = {
          i1: p1.index, price1: p1.price,
          i2: p2.index, price2: p2.price,
          endValue: lineAt(n - 1),
          touches,
        }
      }
    }
  }
  return best
}
