import type {
  IChartApi, ISeriesApi, ISeriesPrimitive, SeriesAttachedParameter, Time,
  IPrimitivePaneView, IPrimitivePaneRenderer,
} from 'lightweight-charts'

// Minimal structural shape of fancy-canvas's rendering target — avoids
// importing from 'fancy-canvas' directly (a transitive dep of
// lightweight-charts, not declared in package.json). TypeScript matches
// this structurally against whatever the library actually passes in.
interface MediaCoordinatesRenderingScope {
  context: CanvasRenderingContext2D
  mediaSize: { width: number; height: number }
}
interface RenderingTarget2DLike {
  useMediaCoordinateSpace<T>(f: (scope: MediaCoordinatesRenderingScope) => T): T
}

export interface RectangleSpec {
  time1: Time
  time2: Time
  price1: number
  price2: number
  fillColor: string
  borderColor: string
  label?: string
}

class RectangleRenderer implements IPrimitivePaneRenderer {
  private _rects: RectangleSpec[]
  private _chart: IChartApi
  private _series: ISeriesApi<any>

  constructor(rects: RectangleSpec[], chart: IChartApi, series: ISeriesApi<any>) {
    this._rects = rects
    this._chart = chart
    this._series = series
  }

  draw(target: RenderingTarget2DLike): void {
    target.useMediaCoordinateSpace(scope => {
      const ctx = scope.context
      const timeScale = this._chart.timeScale()
      const width = scope.mediaSize.width

      for (const r of this._rects) {
        const y1 = this._series.priceToCoordinate(r.price1)
        const y2 = this._series.priceToCoordinate(r.price2)
        if (y1 === null || y2 === null) continue

        const x1raw = timeScale.timeToCoordinate(r.time1)
        const x2raw = timeScale.timeToCoordinate(r.time2)
        // Off-screen to one side (e.g. zone started before the visible
        // range) — clip to the canvas edge instead of skipping the zone.
        const x1 = x1raw === null ? 0 : x1raw
        const x2 = x2raw === null ? width : x2raw

        const left = Math.min(x1, x2)
        const boxWidth = Math.max(x1, x2) - left
        const top = Math.min(y1, y2)
        const boxHeight = Math.max(y1, y2) - top
        if (boxWidth <= 0 || boxHeight <= 0) continue

        ctx.fillStyle = r.fillColor
        ctx.fillRect(left, top, boxWidth, boxHeight)
        ctx.strokeStyle = r.borderColor
        ctx.lineWidth = 1
        ctx.strokeRect(left, top, boxWidth, boxHeight)

        if (r.label) {
          ctx.font = '10px sans-serif'
          ctx.fillStyle = r.borderColor
          ctx.fillText(r.label, left + 4, top + 12)
        }
      }
    })
  }
}

class RectanglePaneView implements IPrimitivePaneView {
  private _source: RectanglesPrimitive

  constructor(source: RectanglesPrimitive) {
    this._source = source
  }

  renderer(): IPrimitivePaneRenderer | null {
    if (!this._source.chart || !this._source.series) return null
    return new RectangleRenderer(this._source.rectangles, this._source.chart, this._source.series)
  }
}

/**
 * Draws filled, bordered rectangles (zones — FVGs, order blocks, entry
 * zones, etc.) between a time range and a price range. lightweight-charts
 * has no built-in "shaded box" primitive, so this hand-implements one via
 * the library's series-primitive plugin API (canvas draw callback + live
 * time/price -> pixel coordinate conversion, re-run every repaint so it
 * tracks pan/zoom automatically).
 */
export class RectanglesPrimitive implements ISeriesPrimitive<Time> {
  chart: IChartApi | null = null
  series: ISeriesApi<any> | null = null
  rectangles: RectangleSpec[] = []

  private _paneViews: RectanglePaneView[]
  private _requestUpdate?: () => void

  constructor() {
    this._paneViews = [new RectanglePaneView(this)]
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this.chart = param.chart
    this.series = param.series as ISeriesApi<any>
    this._requestUpdate = param.requestUpdate
  }

  detached(): void {
    this.chart = null
    this.series = null
  }

  updateAllViews(): void {}

  paneViews(): readonly IPrimitivePaneView[] {
    return this._paneViews
  }

  setRectangles(rects: RectangleSpec[]): void {
    this.rectangles = rects
    this._requestUpdate?.()
  }
}
