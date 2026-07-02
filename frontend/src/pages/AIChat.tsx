import { useRef, useState } from 'react'
import { sendChat } from '../api/client'
import type { ChatMessage } from '../api/client'

export default function AIChat() {
  const [history, setHistory] = useState<ChatMessage[]>([])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function send() {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')
    const newHistory: ChatMessage[] = [...history, { role: 'user', content: msg }]
    setHistory(newHistory)
    setLoading(true)
    try {
      const res = await sendChat(msg, history)
      setHistory([...newHistory, { role: 'assistant', content: res.data.reply }])
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const status = err?.response?.status
      const reason = detail
        ? `${detail}${status ? ` (HTTP ${status})` : ''}`
        : err?.message ?? 'Unknown error — check the backend is running.'
      setHistory([...newHistory, { role: 'assistant', content: `⚠ ${reason}` }])
    } finally {
      setLoading(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div className="p-6 flex flex-col h-[calc(100vh-2rem)]">
      <h1 className="text-xl font-bold text-white mb-4">AI Chat</h1>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {history.length === 0 && (
          <div className="text-center py-16 text-slate-500">
            <p className="text-4xl mb-3">✦</p>
            <p className="text-sm">Ask about market signals, strategies, risk management…</p>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {[
                'What does RSI=75 mean?',
                'Explain my strategy signals',
                'What is a good risk/reward ratio?',
                'How does Kelly Criterion work?',
              ].map(s => (
                <button key={s} onClick={() => setInput(s)}
                  className="text-xs px-3 py-1.5 bg-[#1a1d27] border border-[#2a2d3e] text-slate-400 rounded-lg hover:border-indigo-500/30 hover:text-indigo-400">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
              m.role === 'user'
                ? 'bg-indigo-600 text-white'
                : 'bg-[#1a1d27] border border-[#2a2d3e] text-slate-300'
            }`}>
              {m.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl px-4 py-3 text-slate-400 text-sm">
              <span className="animate-pulse">AI is thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask the AI anything about trading…"
          className="flex-1 bg-[#1a1d27] border border-[#2a2d3e] rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 outline-none focus:border-indigo-500"
        />
        <button onClick={send} disabled={loading || !input.trim()}
          className="px-5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors">
          Send
        </button>
      </div>
    </div>
  )
}
