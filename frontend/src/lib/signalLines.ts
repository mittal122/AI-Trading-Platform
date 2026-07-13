import { LineStyle } from 'lightweight-charts'
import type { ISeriesApi, IPriceLine } from 'lightweight-charts'
import type { TradingSignal } from '../api/client'

export interface LevelSpec { price: number; title: string; color: string }

/** Draw arbitrary labelled horizontal price lines on a candlestick series.
 *  Returns the created lines so the caller can remove them later
 *  (toggle / symbol change). Falsy prices are skipped. */
export function drawLevels(
  series: ISeriesApi<'Candlestick'>,
  levels: LevelSpec[],
): IPriceLine[] {
  return levels
    .filter(l => l.price)
    .map(l => series.createPriceLine({
      price: l.price,
      title: l.title,
      color: l.color,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
    }))
}

/** A strategy signal's Entry / Stop / Target. */
export function drawSignalLines(
  series: ISeriesApi<'Candlestick'>,
  signal: TradingSignal,
): IPriceLine[] {
  return drawLevels(series, [
    { price: signal.entry, title: 'ENTRY', color: '#f5a623' },
    { price: signal.stop_loss, title: 'STOP', color: '#f6465d' },
    { price: signal.take_profit, title: 'TARGET', color: '#2ebd85' },
  ])
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
