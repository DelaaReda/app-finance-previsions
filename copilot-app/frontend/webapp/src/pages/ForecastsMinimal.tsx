export default function ForecastsMinimal() {
  return (
    <div style={{ padding: '2rem', color: 'white' }}>
      <h1>Prévisions de marché</h1>
      <p>Page Forecasts - Version minimale fonctionnelle</p>
      <div style={{ marginTop: '2rem', display: 'grid', gap: '1rem' }}>
        <div style={{ background: '#1a1a2e', padding: '1rem', borderRadius: '8px' }}>
          <strong>AAPL</strong> - Score: 8.2/10 📈
        </div>
        <div style={{ background: '#1a1a2e', padding: '1rem', borderRadius: '8px' }}>
          <strong>MSFT</strong> - Score: 7.9/10 📈
        </div>
        <div style={{ background: '#1a1a2e', padding: '1rem', borderRadius: '8px' }}>
          <strong>GOOGL</strong> - Score: 6.1/10 📉
        </div>
      </div>
    </div>
  );
}
