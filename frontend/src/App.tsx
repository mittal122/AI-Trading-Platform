import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard  from './pages/Dashboard'
import Signals    from './pages/Signals'
import Backtest   from './pages/Backtest'
import Portfolio  from './pages/Portfolio'
import PaperTrade from './pages/PaperTrade'
import AIChat     from './pages/AIChat'
import Settings   from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-[#0f1117]">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/signals"   element={<Signals />} />
            <Route path="/backtest"  element={<Backtest />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/paper"     element={<PaperTrade />} />
            <Route path="/chat"      element={<AIChat />} />
            <Route path="/settings"  element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
