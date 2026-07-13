import { LineStyle } from 'lightweight-charts'
import type { ISeriesApi, IPriceLine } from 'lightweight-charts'
import type { TradingSignal } from '../api/client'

/** Draw a signal's Entry / Stop / Target as labelled horizontal price lines
 *  on a candlestick series. Returns the created lines so the caller can
 *  remove them later (toggle / symbol change). */
export function drawSignalLines(
  series: ISeriesApi<'Candlestick'>,
  signal: TradingSignal,
): IPriceLine[] {
  const mk = (price: number, title: string, color: string) =>
    series.createPriceLine({
      price,
      title,
      color,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
    })
  const lines: IPriceLine[] = []
  if (signal.entry) lines.push(mk(signal.entry, 'ENTRY', '#f5a623'))
  if (signal.stop_loss) lines.push(mk(signal.stop_loss, 'STOP', '#f6465d'))
  if (signal.take_profit) lines.push(mk(signal.take_profit, 'TARGET', '#2ebd85'))
  return lines
}

export function clearSignalLines(
  series: ISeriesApi<'Candlestick'> | null,
  lines: IPriceLine[],
): void {
  if (!series) return
  for (const l of lines) {
    try { series.removePriceLine(l) } catch { /* chart may be disposed */ }
  }
}
