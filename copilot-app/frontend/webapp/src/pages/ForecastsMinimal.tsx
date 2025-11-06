import { DEFAULT_DASHBOARD_TICKERS, getTickerName, getTickerCategory } from '../config/tickers';

/**
 * Prévisions avec tickers diversifiés réels
 * Intégration: Crypto, Gold, Tech, International, Indices
 * Optimisation: Données préchargées pour navigation rapide
 */
export default function ForecastsMinimal() {
  // Sample data avec tickers réels (sera remplacé par vraies données API)
  const mockForecasts = DEFAULT_DASHBOARD_TICKERS.slice(0, 12).map((ticker, i) => ({
    ticker,
    name: getTickerName(ticker),
    category: getTickerCategory(ticker),
    score: (8.5 - i * 0.3).toFixed(1),
    trend: i < 7 ? '📈' : '📉',
  }));

  return (
    <div data-testid="forecasts-pro" style={{ padding: '2rem', color: 'white' }}>
      <h1>Prévisions de marché</h1>
      <p>Univers complet: Crypto, Gold, Tech, International, Indices</p>

      <div data-testid="forecasts-grid" style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
        {mockForecasts.map(({ ticker, name, category, score, trend }) => (
          <div
            key={ticker}
            style={{
              background: '#1a1a2e',
              padding: '1.5rem',
              borderRadius: '12px',
              border: '1px solid #2a2a3e',
              transition: 'transform 0.2s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
              <div>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{ticker}</div>
                <div style={{ fontSize: '0.85rem', color: '#888', marginTop: '0.25rem' }}>{name}</div>
              </div>
              <span style={{ fontSize: '1.5rem' }}>{trend}</span>
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.9rem', color: '#888', background: '#2a2a3e', padding: '0.25rem 0.75rem', borderRadius: '6px' }}>
                {category}
              </span>
              <span style={{ fontSize: '1.1rem', fontWeight: 'bold', color: trend === '📈' ? '#4ade80' : '#f87171' }}>
                {score}/10
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
