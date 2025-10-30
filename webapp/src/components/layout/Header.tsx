/**
 * Header principal de l'application
 * Navigation et titre
 */

import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header style={{
      backgroundColor: '#1a1a1a',
      borderBottom: '1px solid #333',
      padding: '1rem 2rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <Link to="/" style={{ 
          fontSize: '1.5rem', 
          fontWeight: 'bold', 
          textDecoration: 'none',
          color: '#fff',
        }}>
          📊 Copilote Financier
        </Link>
        
        <nav style={{ display: 'flex', gap: '1.5rem' }}>
          <NavLink to="/">Dashboard</NavLink>
          <NavLink to="/macro">Macro</NavLink>
          <NavLink to="/stocks">Actions</NavLink>
          <NavLink to="/news">News</NavLink>
          <NavLink to="/copilot">Copilot</NavLink>
          <NavLink to="/brief">Brief</NavLink>
        </nav>
      </div>
    </header>
  )
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link 
      to={to}
      style={{
        color: '#aaa',
        textDecoration: 'none',
        fontSize: '0.95rem',
        transition: 'color 0.2s',
      }}
      onMouseEnter={(e) => e.currentTarget.style.color = '#fff'}
      onMouseLeave={(e) => e.currentTarget.style.color = '#aaa'}
    >
      {children}
    </Link>
  )
}
