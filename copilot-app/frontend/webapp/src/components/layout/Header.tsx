// Header principal de l'application

import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header style={styles.header}>
      <div style={styles.container}>
        <Link to="/" style={styles.logo}>
          <h1 style={styles.logoText}>📊 Copilote Financier</h1>
        </Link>
        
        <nav style={styles.nav}>
          <Link to="/" style={styles.navLink}>Dashboard</Link>
          <Link to="/macro" style={styles.navLink}>Macro</Link>
          <Link to="/stocks" style={styles.navLink}>Actions</Link>
          <Link to="/news" style={styles.navLink}>News</Link>
          <Link to="/copilot" style={styles.navLink}>Copilot</Link>
          <Link to="/brief" style={styles.navLink}>Brief</Link>
        </nav>

        <div style={styles.actions}>
          <span style={styles.updateTime}>Mise à jour: {new Date().toLocaleTimeString('fr-FR')}</span>
        </div>
      </div>
    </header>
  )
}

const styles = {
  header: {
    backgroundColor: '#1a1a1a',
    borderBottom: '1px solid #333',
    padding: '12px 0',
  } as React.CSSProperties,
  container: {
    maxWidth: 1400,
    margin: '0 auto',
    padding: '0 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  } as React.CSSProperties,
  logo: {
    textDecoration: 'none',
    color: 'inherit',
  } as React.CSSProperties,
  logoText: {
    margin: 0,
    fontSize: 20,
    fontWeight: 600,
    color: '#fff',
  } as React.CSSProperties,
  nav: {
    display: 'flex',
    gap: 24,
  } as React.CSSProperties,
  navLink: {
    textDecoration: 'none',
    color: '#999',
    fontSize: 14,
    fontWeight: 500,
    transition: 'color 0.2s',
  } as React.CSSProperties,
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  } as React.CSSProperties,
  updateTime: {
    fontSize: 12,
    color: '#666',
  } as React.CSSProperties,
}
