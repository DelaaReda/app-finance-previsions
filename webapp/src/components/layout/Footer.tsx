/**
 * Footer de l'application
 * Informations de version et sources
 */

export default function Footer() {
  return (
    <footer style={{
      backgroundColor: '#1a1a1a',
      borderTop: '1px solid #333',
      padding: '1rem 2rem',
      marginTop: 'auto',
      fontSize: '0.85rem',
      color: '#777',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <div>
        Copilote Financier v0.1.0 • Données: FRED, yfinance, RSS
      </div>
      <div>
        <a 
          href="https://github.com/DelaaReda/app-finance-previsions" 
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#777', textDecoration: 'none' }}
        >
          GitHub
        </a>
      </div>
    </footer>
  )
}
