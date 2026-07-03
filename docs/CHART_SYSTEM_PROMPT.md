# Prompt: Live Candlestick Chart System (Binance → FastAPI → React)

Paste everything below into an AI coding assistant, in a project that has a
Python backend and a React (or similar) frontend, to replicate this exact
chart pipeline.

---

## System Prompt

I want to add a live-updating candlestick chart to my app, using the exact
architecture below. Implement it end to end: backend market-data service,
REST endpoints, and a React chart component with infinite scroll + live
updates.

### 1. Data source

Use Binance's public REST API via the `python-binance` package
(`pip install python-binance`) — **no API key needed** for market data
(klines are public). Do not use websockets for this — plain polling is
simpler and sufficient.

```python
from binance.client import Client
client = Client()  # no keys required for public market data

klines = client.get_klines(
    symbol="BTCUSDT",          # uppercase
    interval=Client.KLINE_INTERVAL_1HOUR,  # or _1MINUTE, _5MINUTE, _1DAY, etc.
    limit=500,                 # max 1000 per Binance's own API limit
    endTime=None,              # optional: unix ms, for backward pagination
)
```

Each kline row is a 12-element list:
`[open_time, open, high, low, close, volume, close_time, quote_asset_volume, number_of_trades, taker_buy_base, taker_buy_quote, ignore]`

Keep only: `open_time` (rename → `timestamps`), `open`, `high`, `low`,
`close`, `volume`, `quote_asset_volume` (rename → `amount`). Convert
`open_time` from unix-ms to a real timestamp, cast price/volume columns to
float.

### 2. Backend service layer (Python / FastAPI)

Build one small service class wrapping the client, with a single method:

```python
def get_market_data(symbol: str, interval: str, limit: int, end_time: int | None = None) -> pd.DataFrame:
    kwargs = {"endTime": end_time} if end_time is not None else {}
    klines = client.get_klines(symbol=symbol.upper(), interval=INTERVAL_MAP[interval], limit=limit, **kwargs)
    df = pd.DataFrame(klines, columns=[...12 columns above...])
    df = df[["open_time","open","high","low","close","volume","quote_asset_volume"]]
    df.rename(columns={"open_time": "timestamps", "quote_asset_volume": "amount"}, inplace=True)
    df["timestamps"] = pd.to_datetime(df["timestamps"], unit="ms")
    df[["open","high","low","close","volume","amount"]] = df[["open","high","low","close","volume","amount"]].astype(float)
    return df
```

`INTERVAL_MAP` maps your own interval strings (`"1m"`, `"5m"`, `"15m"`,
`"1h"`, `"4h"`, `"1d"`, `"1w"`, etc.) to Binance's `Client.KLINE_INTERVAL_*`
constants — this is the only place interval strings get translated.

### 3. REST endpoints (expose exactly 2)

**`GET /market/history`** — historical candles for the chart's initial load
and for scroll-back pagination.
- Query params: `symbol` (default e.g. `BTCUSDT`), `interval` (default e.g.
  `5m`), `limit` (default 500, max 1000), `end_time` (optional, unix ms).
- When `end_time` is given, return `limit` candles ending at/before that
  timestamp instead of the most recent ones — this is what makes
  "scroll left to load more history" possible, and Binance's own `endTime`
  kline param already supports it natively, so no custom logic is needed
  beyond passing it through.
- Response: `{ symbol, interval, candles: [{ timestamp, open, high, low, close, volume, amount }, ...] }`
  (candles ascending by time).

**`GET /market/live`** — the single latest (possibly still-forming) candle.
- Same `symbol`/`interval` params, no `limit`/`end_time`.
- Internally just calls the same service method with `limit=1` and returns
  the last row.
- Response: same single-candle shape as above (not wrapped in a list).
- This is the endpoint that makes the chart feel "live" — Binance's most
  recent kline updates in place (open/high/low/close/volume change) until
  the candle closes, so polling this and pushing the result into the chart
  makes the current candle visibly move tick-to-tick.

### 4. Frontend chart (React + TypeScript + `lightweight-charts` v5)

`npm install lightweight-charts`

Core setup, once per mount (empty dependency array — do not re-create the
chart on every render):

```tsx
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'
import type { ISeriesApi, LogicalRange, UTCTimestamp } from 'lightweight-charts'

const chart = createChart(containerRef.current, {
  layout: { background: { type: ColorType.Solid, color: '#0f1117' }, textColor: '#64748b' },
  width: containerRef.current.clientWidth,
  height: 320,
})
const candleSeries: ISeriesApi<'Candlestick'> = chart.addSeries(CandlestickSeries, {
  upColor: '#22c55e', downColor: '#ef4444',
  borderUpColor: '#22c55e', borderDownColor: '#ef4444',
  wickUpColor: '#22c55e', wickDownColor: '#ef4444',
})
```

Convert your API candle shape to lightweight-charts' bar shape:

```ts
const toBarTime = (ts: string): UTCTimestamp => Math.floor(new Date(ts).getTime() / 1000) as UTCTimestamp
const toBar = (c) => ({ time: toBarTime(c.timestamp), open: c.open, high: c.high, low: c.low, close: c.close })
```

**Initial load**: fetch `/market/history?limit=500`, `candleSeries.setData(candles.map(toBar))`,
keep the full loaded array in a plain closure variable (not React state — it's mutated on every
scroll/tick and doesn't need to trigger re-renders).

**Infinite scroll (load older history on scroll-left)**:
```ts
chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
  if (range && range.from <= 20) loadOlder()  // within 20 bars of the oldest loaded candle
})

async function loadOlder() {
  const oldest = allCandles[0]
  const endTime = new Date(oldest.timestamp).getTime() - 1  // avoid re-fetching the same boundary candle
  const res = await api.getMarket(symbol, interval, 500, endTime)
  if (res.data.candles.length === 0) { hasMore = false; return }
  const addedCount = res.data.candles.length
  allCandles = [...res.data.candles, ...allCandles]
  const prevRange = chart.timeScale().getVisibleLogicalRange()
  candleSeries.setData(allCandles.map(toBar))
  // setData() resets scroll position — restore it, shifted by how many bars we just prepended
  if (prevRange) chart.timeScale().setVisibleLogicalRange({ from: prevRange.from + addedCount, to: prevRange.to + addedCount })
}
```

**Live updates (make the current candle move)**:
```ts
setInterval(async () => {
  const res = await api.getLiveMarket(symbol, interval)
  candleSeries.update(toBar(res.data))  // update() patches the last bar in place, or appends a new one — no setData() needed
  const last = allCandles[allCandles.length - 1]
  if (last.timestamp === res.data.timestamp) allCandles[allCandles.length - 1] = res.data
  else allCandles.push(res.data)
}, 5000)  // 5s poll interval is plenty for a REST-polling chart
```

Clean up on unmount: clear the interval, unsubscribe the range-change
callback, `chart.remove()`.

### Key gotchas worth calling out up front
- Binance `get_klines` caps `limit` at 1000 per call — pagination via
  `end_time`/`endTime` is required for anything beyond that, there's no
  single bigger call.
- `lightweight-charts` `setData()` resets the visible scroll range — always
  save/restore `getVisibleLogicalRange()` around it, shifted by however many
  bars you just added, or every "load more" jolts the user's scroll position.
- `series.update()` (not `setData()`) is the correct call for live ticks —
  it patches only the last bar and is cheap; calling `setData()` on every
  poll tick is wasteful and can also fight with scroll position.
- No API key/auth needed anywhere in this pipeline — it's 100% public
  Binance market data.
