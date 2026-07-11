import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavRail from './components/shell/NavRail'
import TopBar from './components/shell/TopBar'
import Terminal   from './pages/Terminal'
import Backtest   from './pages/Backtest'
import Portfolio  from './pages/Portfolio'
import PaperTrade from './pages/PaperTrade'
import PatternAnalysis  from './pages/PatternAnalysis'
import PatternDashboard from './pages/PatternDashboard'
import SmcAnalyzer from './pages/SmcAnalyzer'
import SmcAutoTest from './pages/SmcAutoTest'
import Settings   from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen overflow-hidden bg-bg">
        <TopBar />
        <div className="flex flex-1 overflow-hidden">
          <NavRail />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/"          element={<Terminal />} />
              <Route path="/backtest"  element={<Backtest />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/paper"     element={<PaperTrade />} />
              <Route path="/patterns"           element={<PatternAnalysis />} />
              <Route path="/patterns/dashboard" element={<PatternDashboard />} />
              <Route path="/smc"       element={<SmcAnalyzer />} />
              <Route path="/smc/autotest" element={<SmcAutoTest />} />
              <Route path="/settings"  element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
