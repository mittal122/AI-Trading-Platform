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
  exit_timestamp: string; created_at: string
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

export const getMarket = (symbol: string, interval: string, limit = 200) =>
  api.get<{ symbol: string; interval: string; candles: Candle[] }>(
    '/market/history', { params: { symbol, interval, limit } }
  )

export const getIndicators = (symbol: string, interval: string, limit = 200) =>
  api.get<{ symbol: string; interval: string; indicators: Indicators }>(
    '/indicator', { params: { symbol, interval, limit } }
  )

export const getSignal = (strategy: string, symbol: string, interval: string) =>
  api.get<TradingSignal>('/strategy/signal', {
    params: { strategy, symbol, interval }
  })

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
