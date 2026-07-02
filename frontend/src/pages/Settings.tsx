export default function Settings() {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">API Connection</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Backend URL</label>
            <input defaultValue="http://localhost:8000"
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none" />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Default Symbol</label>
            <input defaultValue="BTCUSDT"
              className="w-full bg-[#0f1117] border border-[#2a2d3e] rounded-lg px-3 py-2 text-sm text-white outline-none" />
          </div>
        </div>
      </div>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-300">Environment Variables Required</h2>
        {[
          ['NVIDIA_API_KEY', 'Required for all AI features — routes to NVIDIA NIM (chat, analyst, validator, etc.)'],
          ['BINANCE_API_KEY', 'Required for live trading only'],
          ['BINANCE_SECRET', 'Required for live trading only'],
          ['DATABASE_URL', 'Optional — defaults to SQLite (trading.db)'],
          ['MARKET_ANALYST_MODEL', 'Optional — defaults to nemotron-3-super'],
          ['CHAT_ASSISTANT_MODEL', 'Optional — defaults to kimi-k2.5'],
        ].map(([k, v]) => (
          <div key={k} className="flex items-start gap-3 py-2 border-b border-[#2a2d3e]/50 last:border-0">
            <code className="text-xs text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded shrink-0">{k}</code>
            <p className="text-xs text-slate-500">{v}</p>
          </div>
        ))}
      </div>

      <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-3">Phase Completion</h2>
        {[
          ['Phase 1', 'Core Infrastructure', true],
          ['Phase 2', 'Professional Strategy System', true],
          ['Phase 3', 'Advanced Risk Management', true],
          ['Phase 4', 'Portfolio Analytics', true],
          ['Phase 5', 'AI Integration', true],
          ['Phase 6', 'Paper Trading', true],
          ['Phase 7', 'Live Trading', true],
          ['Phase 8', 'Database Integration', true],
          ['Phase 9', 'Frontend Dashboard', true],
          ['Phase 10', 'SaaS Platform', true],
        ].map(([phase, label, done]) => (
          <div key={String(phase)} className="flex items-center gap-3 py-2 border-b border-[#2a2d3e]/50 last:border-0">
            <span className={`text-sm ${done ? 'text-green-400' : 'text-slate-600'}`}>{done ? '✓' : '○'}</span>
            <span className="text-xs text-slate-500 w-16">{phase}</span>
            <span className={`text-sm ${done ? 'text-slate-300' : 'text-slate-600'}`}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
