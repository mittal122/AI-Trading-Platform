import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Admin token for money-critical endpoints (exchange keys, live trading,
// delete-all). Only needed when the deployment sets ADMIN_API_TOKEN; on a
// single-operator localhost instance those endpoints are open and this stays
// empty. Stored locally and attached to every request so the whole UI keeps
// working once entered — never sent anywhere but this backend.
const ADMIN_TOKEN_KEY = 'admin.apiToken'
export function getAdminToken(): string {
  try { return localStorage.getItem(ADMIN_TOKEN_KEY) ?? '' } catch { return '' }
}
export function setAdminToken(token: string) {
  try {
    if (token) localStorage.setItem(ADMIN_TOKEN_KEY, token)
    else localStorage.removeItem(ADMIN_TOKEN_KEY)
  } catch { /* storage unavailable */ }
}
api.interceptors.request.use(config => {
  const token = getAdminToken()
  if (token) config.headers['X-Admin-Token'] = token
  return config
})

// ── Types ────────────────────────────────────────────────────────────────────

export interface ExchangeSymbol {
  symbol: string; base_asset: string; quote_asset: string
}

export interface SymbolsResponse {
  provider: string; symbols: ExchangeSymbol[]
}

export const getSymbols = () => api.get<SymbolsResponse>('/market/symbols')

// ── Market overview / order-flow (advanced Dashboard) ───────────────────────

export interface Ticker24h {
  symbol: string; last_price: number; price_change_pct: number
  high: number; low: number; quote_volume: number; trades: number
}

export interface MarketOverview {
  btc: Ticker24h | null; eth: Ticker24h | null
  advancers: number; decliners: number; avg_change_pct: number
  total_quote_volume: number; counted_pairs: number
  top_gainers: Ticker24h[]; top_losers: Ticker24h[]; volume_leaders: Ticker24h[]
}

export interface DepthPressure {
  symbol: string; bid_notional: number; ask_notional: number; bid_ratio: number
  best_bid: number; best_ask: number
  biggest_bid_wall_price: number; biggest_bid_wall_notional: number
  biggest_ask_wall_price: number; biggest_ask_wall_notional: number; levels: number
}

export interface BuyPressure {
  symbol: string; interval: string; candles: number
  buy_ratio: number; recent_ratios: number[]
}

export interface Funding {
  symbol: string; funding_rate: number; funding_rate_annualized_pct: number
  mark_price: number; next_funding_time: number
}

export interface VolumeScanRow {
  symbol: string; interval: string; time: string; ltp: number
  volume_window: number; volume_average: number; spike_ratio: number
  orders: number; avg_orders: number
  max_push_volume: number; max_push_ratio: number
  error: string | null
}
export interface VolumeScanResponse {
  interval: string; window: number; rows: VolumeScanRow[]
}

export const getMarketOverview = () => api.get<MarketOverview>('/market/overview')
export const getWatchlistTickers = (symbols: string[]) =>
  api.get<{ tickers: Ticker24h[] }>('/market/watchlist', { params: { symbols: symbols.join(',') } })
export const getDepthPressure = (symbol: string) =>
  api.get<DepthPressure>('/market/depth-pressure', { params: { symbol } })
export const getBuyPressure = (symbol: string, interval = '5m') =>
  api.get<BuyPressure>('/market/buy-pressure', { params: { symbol, interval } })
export const getFunding = (symbol: string) =>
  api.get<Funding | null>('/market/funding', { params: { symbol } })
export const getVolumeScan = (symbols: string[], interval = '5m', window = 20) =>
  api.get<VolumeScanResponse>('/market/volume-scan', {
    params: { symbols: symbols.join(','), interval, window },
  })

export interface Indicators {
  price: number; sma20: number; ema20: number; rsi14: number
  macd: number; signal: number; histogram: number
  bb_upper: number; bb_middle: number; bb_lower: number
  atr14: number; vwap: number
}

export interface TradingSignal {
  strategy: string; symbol: string; interval: string; timestamp: string
  direction: 'BUY' | 'SELL' | 'FLAT'
  confidence: number; entry: number; stop_loss: number
  take_profit: number; risk_reward: number; reasons: string[]
  regime?: string; quality_score?: number; quality_grade?: string
  explanation?: string
  eta_candles?: number; eta_display?: string
}

export interface PortfolioAnalytics {
  initial_balance: number; ending_balance: number; total_return: number
  total_trades: number; winning_trades: number; losing_trades: number
  win_rate: number; avg_win: number; avg_loss: number
  profit_factor: number; expectancy: number
  sharpe_ratio: number; sortino_ratio: number; calmar_ratio: number
  max_drawdown: number
}

export interface TradeHistoryItem {
  id: number; symbol: string; strategy: string; direction: string
  mode: string; entry_price: number; exit_price: number
  quantity: number; pnl: number; pnl_percent: number
  exit_reason: string; entry_timestamp: string
  exit_timestamp: string; created_at: string; duration_display?: string
}

export interface TradeHistoryResponse {
  total: number; limit: number; offset: number
  trades: TradeHistoryItem[]
}

export interface BacktestRunItem {
  id: number; strategy: string; symbol: string; interval: string
  limit: number; initial_balance: number; final_balance: number
  total_return: number; total_trades: number; win_rate: number
  profit_factor: number; sharpe_ratio: number; max_drawdown: number
  winning_trades: number; losing_trades: number; avg_win: number
  avg_loss: number; expectancy: number; sortino_ratio: number
  calmar_ratio: number; created_at: string
  avg_candles_to_win?: number; avg_time_to_win_display?: string
}

export interface BacktestHistoryResponse {
  total: number; limit: number; offset: number; runs: BacktestRunItem[]
}

export interface PaperStatus {
  is_running: boolean; symbol: string; interval: string; strategy: string
  started_at?: string; initial_balance: number; cash: number
  equity: number; realized_pnl: number; unrealized_pnl: number
  total_return: number; open_position?: {
    symbol: string; direction: string; entry_price: number
    quantity: number; current_price: number; stop_loss: number
    take_profit: number; unrealized_pnl: number; candles_held: number
  }
  trade_count: number; recent_trades: Array<{
    side: string; price: number; quantity: number
    pnl: number; reason: string; timestamp: string
  }>
  last_signal?: string; last_price?: number; candles_processed: number
}

// ── API calls ────────────────────────────────────────────────────────────────

export interface Candle {
  timestamp: string; open: number; high: number
  low: number; close: number; volume: number; amount: number
}

export const getMarket = (symbol: string, interval: string, limit = 200, endTime?: number) =>
  api.get<{ symbol: string; interval: string; candles: Candle[] }>(
    '/market/history', { params: { symbol, interval, limit, end_time: endTime } }
  )

// The current (possibly still-forming) candle — Binance's kline stream keeps
// updating this bar's high/low/close/volume until it closes. Poll this to
// keep a chart's last bar live instead of a one-time static snapshot.
export const getLiveMarket = (symbol: string, interval: string) =>
  api.get<Candle>('/market/live', { params: { symbol, interval } })

export const getIndicators = (symbol: string, interval: string, limit = 200) =>
  api.get<{ symbol: string; interval: string; indicators: Indicators }>(
    '/indicator', { params: { symbol, interval, limit } }
  )

export const getSignal = (strategy: string, symbol: string, interval: string) =>
  api.get<TradingSignal>('/strategy/signal', {
    params: { strategy, symbol, interval }
  })

export const scanAllStrategies = (symbol: string, interval: string, limit = 250) =>
  api.get<TradingSignal[]>('/strategy/scan', { params: { symbol, interval, limit } })

export const getMultiTimeframeSignals = (
  strategy: string, symbol: string, intervals?: string[], limit = 250
) =>
  api.get<TradingSignal[]>('/strategy/multi-timeframe', {
    params: { strategy, symbol, limit, intervals: intervals?.join(',') }
  })

// ── Pattern Analysis ────────────────────────────────────────────────────────

export interface ChartPoint { time: string; price: number }
export interface TrendlineAnnotation { label: string; points: ChartPoint[] }
export interface ZoneAnnotation {
  label: string; start_time: string; end_time: string
  top: number; bottom: number; bias?: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
}
export interface LevelAnnotation { label: string; price: number; strength?: number }
export interface LabelAnnotation { text: string; time: string; price: number }
export interface ChartAnnotations {
  trendlines: TrendlineAnnotation[]; zones: ZoneAnnotation[]
  levels: LevelAnnotation[]; labels: LabelAnnotation[]
}

export interface AIPatternExplanation {
  why_detected: string; why_valid: string; market_psychology: string
  buyer_seller_behavior: string; strength: string
  reliability_score?: number; alternative_scenario: string
  recommendation?: 'BUY' | 'SELL' | 'WAIT' | 'AVOID'
  recommendation_reason: string; error?: string
}

export interface DetectedPattern {
  id: string; pattern_type: string; pattern_name: string
  category?: 'chart' | 'candlestick' | 'smc'
  symbol: string; interval: string
  direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  confidence: number
  status: 'DEVELOPING' | 'CONFIRMED' | 'BROKEN'
  formation_start: string; formation_end: string; current_price: number
  breakout_level?: number; invalidation_level?: number
  entry_zone_low?: number; entry_zone_high?: number
  stop_loss?: number; target_1?: number; target_2?: number; target_3?: number
  risk_reward?: number; probability_of_success?: number
  historical_success_rate?: number; expected_time_to_target?: string
  pullback_zone_low?: number; pullback_zone_high?: number
  annotations: ChartAnnotations
  ai?: AIPatternExplanation
  last_updated: string
}

export interface FairValueGap {
  id: string; symbol: string; interval: string
  type: 'BULLISH' | 'BEARISH'
  top: number; bottom: number; formed_at: string
  filled: boolean; filled_at?: string; strength: number; last_updated: string
}

export interface PatternScanResponse {
  symbol: string; interval: string
  patterns: DetectedPattern[]; fvgs: FairValueGap[]
  scanned_at: string; error?: string
}

export interface PatternDashboardRow {
  symbol: string; interval: string; pattern_name: string; pattern_type: string
  confidence: number; direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  current_price: number
  entry_zone_low?: number; entry_zone_high?: number
  stop_loss?: number; target_1?: number; risk_reward?: number
  status: 'DEVELOPING' | 'CONFIRMED' | 'BROKEN'; last_updated: string
}

export interface PatternDashboardResponse {
  rows: PatternDashboardRow[]; scanned_at: string
}

export const scanPatterns = (symbol: string, interval: string, limit = 300) =>
  api.get<PatternScanResponse>('/patterns/scan', { params: { symbol, interval, limit } })

// On-demand AI explanation for ONE pattern — scan() itself is fast/algorithmic
// only by default (see /patterns/scan's include_ai param); call this for
// whichever pattern the user actually selects instead of auto-explaining
// every pattern in a scan (that's what made scans routinely take 50-90s+).
export const explainPattern = (pattern: DetectedPattern) =>
  api.post<AIPatternExplanation>('/patterns/explain', pattern)

export const scanPatternsMultiTimeframe = (symbol: string, intervals?: string[], limit = 300) =>
  api.get<PatternScanResponse[]>('/patterns/multi-timeframe', {
    params: { symbol, limit, intervals: intervals?.join(',') }
  })

export const getPatternDashboard = (symbol: string, intervals?: string[], limit = 300) =>
  api.get<PatternDashboardResponse>('/patterns/dashboard', {
    params: { symbol, limit, intervals: intervals?.join(',') }
  })

// ── Analysis Tools ──────────────────────────────────────────────────────────

export interface AnalysisToolResult {
  tool_key: string; tool_name: string; symbol: string; interval: string
  bias: 'BULLISH' | 'BEARISH' | 'NEUTRAL'; summary: string
  data: Record<string, any>; annotations: ChartAnnotations
  last_updated: string; error?: string
}

export interface AnalysisScanResponse {
  symbol: string; interval: string; tools: AnalysisToolResult[]; scanned_at: string
}

export interface AIToolExplanation {
  confidence_score?: number; market_bias?: string; reasoning: string
  expected_behavior: string; entry_suggestion?: number; stop_loss?: number
  take_profit?: number; probability_of_success?: number
  risk_analysis: string; confluence_notes: string; error?: string
}

export interface AnalysisExplainResponse {
  symbol: string; interval: string; tool_keys: string[]
  explanation: AIToolExplanation; tools: AnalysisToolResult[]
}

export const getAvailableAnalysisTools = () =>
  api.get<{ tools: string[] }>('/analysis/available')

export const scanAnalysisTools = (symbol: string, interval: string, tools?: string[], limit = 300) =>
  api.get<AnalysisScanResponse>('/analysis/scan', {
    params: { symbol, interval, limit, tools: tools?.join(',') }
  })

export const explainAnalysisTools = (symbol: string, interval: string, toolKeys: string[], limit = 300) =>
  api.post<AnalysisExplainResponse>('/analysis/explain', { symbol, interval, tool_keys: toolKeys, limit })

export const getPortfolioAnalytics = (
  strategy: string, symbol: string, interval: string, limit = 300
) =>
  api.get<PortfolioAnalytics>('/portfolio/analytics', {
    params: { strategy, symbol, interval, limit }
  })

export const getTradeHistory = (params: {
  symbol?: string; strategy?: string; mode?: string
  limit?: number; offset?: number
}) => api.get<TradeHistoryResponse>('/trades/history', { params })

export const getBacktestHistory = (params: {
  strategy?: string; symbol?: string; limit?: number; offset?: number
}) => api.get<BacktestHistoryResponse>('/trades/backtest-history', { params })

export const deleteBacktestRun = (id: number) =>
  api.delete<{ deleted: number }>(`/trades/backtest-history/${id}`)

export const deleteAllBacktestRuns = () =>
  api.delete<{ deleted: number }>('/trades/backtest-history')

export const runAndRecordBacktest = (params: {
  strategy: string; symbol: string; interval: string; limit: number
}) => api.post<BacktestRunItem>('/trades/backtest-record', null, { params })

export const getPaperStatus = () => api.get<PaperStatus>('/paper/status')

export const startPaper = (body: {
  symbol: string; interval: string; strategy: string; initial_balance: number
}) => api.post<PaperStatus>('/paper/start', body)

export const stopPaper = () => api.post('/paper/stop')

// ── Manual one-click paper trade ─────────────────────────────────────────────

export interface ManualOrder {
  id: number; symbol: string; strategy: string; direction: string
  entry: number; stop_loss: number; take_profit: number; quantity: number
  status: string; current_price: number; unrealized_pnl: number
  realized_pnl: number; exit_price?: number; exit_reason?: string
  opened_at: string; closed_at?: string
}

export interface ManualPaperStatus {
  balance: number; equity: number; realized_pnl: number
  open_count: number; open_orders: ManualOrder[]; closed_orders: ManualOrder[]
}

export const placePaperOrder = (body: {
  symbol: string; strategy: string; direction: string
  entry: number; stop_loss: number; take_profit: number; interval?: string; risk_percent?: number
}) => api.post<ManualOrder>('/paper/order', body)

export const getManualOrders = () =>
  api.get<ManualPaperStatus>('/paper/orders')

// ── Exchange credentials (Settings page) ────────────────────────────────────

export interface BinanceKeyStatus {
  configured: boolean
  key_preview: string | null
}

export const getBinanceKeyStatus = () =>
  api.get<BinanceKeyStatus>('/settings/binance-keys/status')

export const saveBinanceKeys = (body: { api_key: string; api_secret: string }) =>
  api.post<BinanceKeyStatus>('/settings/binance-keys', body)

export const deleteBinanceKeys = () =>
  api.delete<BinanceKeyStatus>('/settings/binance-keys')

// ── SMC Analyzer ─────────────────────────────────────────────────────────────
// Faithful client types for the SMC engine (backend/app/schemas/smc.py). One
// GET returns the full frozen analysis: candles + every detection + both scoring
// systems + both trade plans + order flow, so the chart and plan never drift.

export type SmcDir = 'BULLISH' | 'BEARISH' | 'NEUTRAL'
export type SmcSide = 'long' | 'short'
export type SmcStrength = 'STRONG' | 'MODERATE' | 'WEAK' | 'REJECTED'

export interface SmcCandle {
  time: string; open: number; high: number; low: number; close: number; volume: number
}
export interface SmcSwing { index: number; time: string; price: number; is_high: boolean; label?: string }
export interface SmcStructureEvent { index: number; time: string; price: number; type: string }
export interface SmcOrderBlock { index: number; time: string; top: number; bottom: number; direction: SmcDir; mitigated: boolean }
export interface SmcFVG { index: number; time: string; top: number; bottom: number; direction: SmcDir; filled: boolean }
export interface SmcLiquidityPool { price: number; direction: SmcDir; swing_indices: number[] }
export interface SmcSweep { pool_price: number; direction: SmcDir; sweep_index: number; reversal_index: number; recent: boolean }
export interface SmcDealingRange { range_hi: number; range_lo: number; equilibrium: number; position: number; zone: string }
export interface SmcVolume { ratio: number; trend_vol: number; spike: boolean }
export interface SmcPOI { top: number; bottom: number; direction: SmcDir; has_liquidity: boolean }
export interface SmcInducement { index: number; time: string; price: number; direction: SmcDir; atr_distance: number }
export interface SmcSupplyDemand { index: number; time: string; top: number; bottom: number; direction: SmcDir; mitigated: boolean }
export interface SmcHTF { available: boolean; trend: 'up' | 'down' | 'neutral'; htf_bars: number }

export interface SmcScoreComponent { name: string; raw: number; weight: number; contribution: number }
export interface SmcVerdict {
  label: SmcDir; total: number; confidence: number
  confidence_label: 'high' | 'medium' | 'low'
  breakdown: { components: SmcScoreComponent[]; total: number }
}
export interface SmcConfluenceFactor { name: string; points: number; hit: boolean; detail: string }
export interface SmcSideConfluence {
  side: SmcSide; total: number; fired: boolean; strength: SmcStrength
  factors: SmcConfluenceFactor[]; reject_reasons: string[]
}
export interface SmcTradePlan {
  side: SmcSide; entry: number; stop_loss: number
  take_profit_1: number; take_profit_2: number; risk_reward: number; atr: number
  source: string; zone_top?: number; zone_bottom?: number
  strength: SmcStrength; strength_score: number; fired: boolean; note: string
  confluence?: SmcSideConfluence
}
export interface SmcOrderFlow {
  imbalance: number; cvd_ratio: number
  pressure: 'buy' | 'sell' | 'balanced'
  bid_notional: number; ask_notional: number
  bid_walls: { price: number; qty: number; distance_pct: number }[]
  ask_walls: { price: number; qty: number; distance_pct: number }[]
}

export interface SmcAnalysis {
  symbol: string; interval: string; frozen_at: string; cutoff_price: number; atr: number
  candles: SmcCandle[]
  swings: SmcSwing[]; structure: SmcStructureEvent[]; trend: 'up' | 'down' | 'neutral'
  order_blocks: SmcOrderBlock[]; fvgs: SmcFVG[]
  liquidity_pools: SmcLiquidityPool[]; sweeps: SmcSweep[]
  dealing_range?: SmcDealingRange; volume?: SmcVolume
  pois: SmcPOI[]; inducements: SmcInducement[]; supply_demand: SmcSupplyDemand[]
  htf?: SmcHTF
  verdict?: SmcVerdict
  long_plan?: SmcTradePlan; short_plan?: SmcTradePlan; primary: string
  order_flow?: SmcOrderFlow
  reasons: string[]
  annotations?: ChartAnnotations
}

export const getSmcAnalysis = (symbol: string, interval: string, limit = 500) =>
  api.get<SmcAnalysis>(`/smc/analyze/${symbol}/${interval}`, { params: { limit } })

// ── SMC Backtest ─────────────────────────────────────────────────────────────
export interface SmcBacktestTrade {
  side: SmcSide; entry: number; stop_loss: number; take_profit: number; qty: number
  entry_index: number; exit_index: number; entry_time: string; exit_time: string
  exit_price: number; pnl: number; pnl_pct: number
  exit_reason: 'STOP_LOSS' | 'TAKE_PROFIT' | 'TIME_EXIT' | 'END_OF_DATA'
  strength_score: number
}
export interface SmcBacktestResult {
  symbol: string; interval: string; candles: number
  initial_capital: number; final_capital: number
  total_trades: number; wins: number; losses: number
  long_trades: number; short_trades: number
  win_rate: number; avg_win: number; avg_loss: number
  profit_factor: number; max_drawdown: number
  total_pnl: number; roi: number; sharpe_ratio: number
  equity_curve: number[]; trades: SmcBacktestTrade[]
}
export const runSmcBacktest = (body: {
  symbol: string; interval: string; limit?: number
  capital?: number; risk_pct?: number; max_trades?: number; cooldown?: number
}) => api.post<SmcBacktestResult>('/smc/backtest', body)

// ── SMC Signal Scanner ───────────────────────────────────────────────────────
export interface SmcWatchItem {
  id: number; symbol: string; interval: string; active: boolean
  last_scanned_candle_time?: string | null
}
export interface SmcScannerSettings { enabled: boolean; max_signals_per_week: number }
export interface SmcSignal {
  id: number; symbol: string; interval: string; side: SmcSide
  entry: number; stop_loss: number; take_profit_1: number; take_profit_2: number
  score: number; reason_note: string; candle_time: string
  status: 'new' | 'accepted' | 'dismissed'; paired_trade_id?: number | null; created_at: string
}

export const getSmcWatchlist = () => api.get<SmcWatchItem[]>('/smc/watchlist')
export const addSmcWatch = (symbol: string, interval: string) =>
  api.post<SmcWatchItem>('/smc/watchlist', { symbol, interval })
export const toggleSmcWatch = (id: number, active: boolean) =>
  api.patch(`/smc/watchlist/${id}`, null, { params: { active } })
export const removeSmcWatch = (id: number) => api.delete(`/smc/watchlist/${id}`)
export const getScannerSettings = () => api.get<SmcScannerSettings>('/smc/scanner/settings')
export const updateScannerSettings = (s: SmcScannerSettings) =>
  api.put<SmcScannerSettings>('/smc/scanner/settings', s)
export const scanSmcNow = () => api.post('/smc/scanner/scan')
export const getSmcSignals = (limit = 100) => api.get<SmcSignal[]>('/smc/signals', { params: { limit } })
export const acceptSmcSignal = (id: number, capital = 1000, risk_pct = 2) =>
  api.post<SmcSignal>(`/smc/signals/${id}/accept`, { capital, risk_pct })
export const dismissSmcSignal = (id: number) => api.patch<SmcSignal>(`/smc/signals/${id}/dismiss`)
