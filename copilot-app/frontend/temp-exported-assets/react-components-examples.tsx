// ============================================
// EXEMPLE DE COMPOSANT REACT AMÉLIORÉ
// OpportunityCard.tsx
// ============================================

import React, { useState } from 'react';
import './copilot-finance-improved.css';

interface OpportunityCardProps {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  confidence: number;
  signal: 'LOW CONFIDENCE' | 'HIGH CONFIDENCE';
}

export const OpportunityCard: React.FC<OpportunityCardProps> = ({
  symbol,
  name,
  price,
  change,
  changePercent,
  confidence,
  signal
}) => {
  const [mousePosition, setMousePosition] = useState({ x: 50, y: 50 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setMousePosition({ x, y });
  };

  const isPositive = change > 0;
  const progressColor = confidence >= 70 ? 'var(--color-success)' : 'var(--color-warning)';

  return (
    <div 
      className="glass-card hover-glow"
      onMouseMove={handleMouseMove}
      style={{
        '--mouse-x': `\${mousePosition.x}%`,
        '--mouse-y': `\${mousePosition.y}%`,
      } as React.CSSProperties}
    >
      {/* Header avec symbole et badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--color-primary)', margin: 0 }}>
            {symbol}
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-gray-500)', margin: '4px 0 0 0' }}>
            {name}
          </p>
        </div>
        <span className={\`badge \${confidence >= 70 ? 'badge-success' : 'badge-warning'}\`}>
          {signal}
        </span>
      </div>

      {/* Prix et changement */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontSize: '2rem', fontWeight: '700', color: 'white', marginBottom: '8px' }}>
          \${price.toFixed(2)}
        </div>
        <div className={\`trend \${isPositive ? 'trend-up' : 'trend-down'}\`}>
          <span>{isPositive ? '↑' : '↓'}</span>
          <span>\${Math.abs(change).toFixed(2)} ({Math.abs(changePercent).toFixed(2)}%)</span>
        </div>
      </div>

      {/* Circular progress pour la confiance */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
        <div 
          className="circular-progress"
          style={{
            '--progress': confidence,
            background: \`conic-gradient(
              \${progressColor} calc(\${confidence} * 1%),
              var(--color-gray-700) 0
            )\`
          } as React.CSSProperties}
        >
          <span className="circular-progress-value">{confidence}%</span>
        </div>
      </div>

      {/* Bouton d'action */}
      <button className="btn-primary" style={{ width: '100%' }}>
        Voir l'analyse
      </button>
    </div>
  );
};

// ============================================
// EXEMPLE D'UTILISATION DANS LE DASHBOARD
// ============================================

export const OpportunitiesSection: React.FC = () => {
  const opportunities = [
    {
      symbol: 'META',
      name: 'Meta Platforms',
      price: 523.45,
      change: 12.34,
      changePercent: 2.41,
      confidence: 85,
      signal: 'HIGH CONFIDENCE' as const
    },
    {
      symbol: 'NVDA',
      name: 'NVIDIA Corp',
      price: 875.60,
      change: 24.67,
      changePercent: 2.90,
      confidence: 78,
      signal: 'HIGH CONFIDENCE' as const
    },
    {
      symbol: 'TSLA',
      name: 'Tesla Inc',
      price: 234.56,
      change: -3.21,
      changePercent: -1.35,
      confidence: 62,
      signal: 'LOW CONFIDENCE' as const
    }
  ];

  return (
    <section>
      <h2 style={{ 
        fontSize: '1.875rem', 
        fontWeight: '700', 
        marginBottom: '24px',
        background: 'linear-gradient(135deg, #288cfa, #7ebcf9)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text'
      }}>
        🎯 Top Opportunities
      </h2>

      <div className="grid-responsive">
        {opportunities.map((opp) => (
          <OpportunityCard key={opp.symbol} {...opp} />
        ))}
      </div>
    </section>
  );
};

// ============================================
// TABLE COMPONENT AMÉLIORÉ
// StocksTable.tsx
// ============================================

interface Stock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  marketCap: string;
}

export const StocksTable: React.FC<{ stocks: Stock[] }> = ({ stocks }) => {
  return (
    <div className="glass-card">
      <h3 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '20px' }}>
        📊 Top Stocks
      </h3>

      <table className="table-modern">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Name</th>
            <th>Price</th>
            <th>Change</th>
            <th>Market Cap</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr key={stock.symbol}>
              <td>
                <strong style={{ color: 'var(--color-primary)' }}>
                  {stock.symbol}
                </strong>
              </td>
              <td>{stock.name}</td>
              <td>\${stock.price.toFixed(2)}</td>
              <td>
                <span className={\`trend \${stock.change >= 0 ? 'trend-up' : 'trend-down'}\`}>
                  {stock.change >= 0 ? '↑' : '↓'} {Math.abs(stock.changePercent).toFixed(2)}%
                </span>
              </td>
              <td>{stock.marketCap}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ============================================
// METRICS CARDS COMPONENT
// MetricsCard.tsx
// ============================================

interface MetricCardProps {
  title: string;
  value: string;
  change: number;
  icon: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({ title, value, change, icon }) => {
  const isPositive = change >= 0;

  return (
    <div className="animated-border">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-gray-500)', marginBottom: '8px' }}>
            {title}
          </p>
          <h3 style={{ fontSize: '2rem', fontWeight: '700', color: 'white', margin: 0 }}>
            {value}
          </h3>
          <div className={\`trend \${isPositive ? 'trend-up' : 'trend-down'}\`} style={{ marginTop: '8px' }}>
            {isPositive ? '↑' : '↓'} {Math.abs(change).toFixed(2)}%
          </div>
        </div>
        <div style={{ fontSize: '2rem' }}>
          {icon}
        </div>
      </div>
    </div>
  );
};

export const PerformanceMetrics: React.FC = () => {
  const metrics = [
    { title: 'Return', value: '0.00%', change: 0, icon: '💰' },
    { title: 'Win Rate', value: '0.00%', change: 0, icon: '🎯' },
    { title: 'Sharpe Ratio', value: '0.00', change: 0, icon: '📊' },
    { title: 'Max Drawdown', value: '0.00%', change: 0, icon: '📉' }
  ];

  return (
    <div className="grid-responsive">
      {metrics.map((metric) => (
        <MetricCard key={metric.title} {...metric} />
      ))}
    </div>
  );
};
