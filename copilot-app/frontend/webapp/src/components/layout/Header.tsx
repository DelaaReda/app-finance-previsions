// Header principal de l'application

import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { HealthIndicator } from '../ui/HealthIndicator'
import GlobalFreshness from '../ui/GlobalFreshness'

export default function Header() {
  const [timeString, setTimeString] = useState(() => new Date().toLocaleTimeString('fr-FR'))
  
  useEffect(() => {
    // Update time every minute instead of constantly, to reduce UI flicker
    const updateTimer = setInterval(() => {
      setTimeString(new Date().toLocaleTimeString('fr-FR'))
    }, 60000)
    return () => clearInterval(updateTimer)
  }, [])

  return (
    <header style={{ backgroundColor: 'var(--surface)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      <div className="container mx-auto px-6 flex items-center justify-between py-3">
        <Link to="/" className="no-underline text-inherit">
          <h1 className="m-0 text-xl font-semibold">📊 Copilote Financier</h1>
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          <Link to="/" className="muted text-sm font-medium hover:text-white transition-colors">Dashboard</Link>
          <Link to="/macro" className="muted text-sm font-medium hover:text-white transition-colors">Macro</Link>
          <Link to="/stocks" className="muted text-sm font-medium hover:text-white transition-colors">Actions</Link>
          <Link to="/news" className="muted text-sm font-medium hover:text-white transition-colors">News</Link>
          <Link to="/copilot" className="muted text-sm font-medium hover:text-white transition-colors">Copilot</Link>
          <Link to="/brief" className="muted text-sm font-medium hover:text-white transition-colors">Brief</Link>
        </nav>

        <div className="flex items-center gap-3">
          <GlobalFreshness />
          <HealthIndicator />
          <span className="muted text-xs">Mise à jour: {timeString}</span>
        </div>
      </div>
    </header>
  )
}
