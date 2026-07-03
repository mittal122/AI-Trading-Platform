import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// ── Types ────────────────────────────────────────────────────────────────────

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

export interface ChatMessage { role: 'user' | 'assistant'; content: string }
export interface ChatResponse { reply: string }

// ── API calls ────────────────────────────────────────────────────────────────

export interface Candle {
  timestamp: string; open: number; high: number
  low: number; close: number; volume: number; amount: number
}

export const getMarket = (symbol: string, interval: string, limit = 200, endTime?: number) =>
  api.get<{ symbol: string; interval: string; candles: Candle[] }>(
    '/market/history', { params: { symbol, interval, limit, end_time: endTime } }
  )

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
export interface LevelAnnotation { label: string; price: number }
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

export const sendChat = (message: string, history: ChatMessage[]) =>
  api.post<ChatResponse>('/ai/chat', { message, history })

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
  entry: number; stop_loss: number; take_profit: number; interval?: string
}) => api.post<ManualOrder>('/paper/order', body)

export const getManualOrders = () =>
  api.get<ManualPaperStatus>('/paper/orders')
