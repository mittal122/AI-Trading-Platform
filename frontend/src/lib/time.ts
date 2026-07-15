/** Backend candle timestamps are naive-UTC ISO strings ('2026-04-23T00:00:00').
 * Date.parse()/new Date() treat a timezone-less ISO string as LOCAL time,
 * shifting every derived epoch by the user's UTC offset (+5:30 in IST). The
 * shift is uniform so charts still LOOK consistent — but pagination sends
 * `end_time = firstBar - 1ms` back to Binance as a real UTC epoch, so every
 * lazy-load seam silently dropped up to a full offset's worth of candles
 * (1 candle on 4h, ~5 on 1h, 22 on 15m). Parse as UTC unless the string
 * already carries an explicit zone. */
export function parseUtcMs(iso: string): number {
  return Date.parse(/[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
}
