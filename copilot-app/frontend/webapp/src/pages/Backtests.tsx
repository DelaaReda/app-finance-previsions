import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useBacktests } from '@/hooks/useBacktests';
import { RobustnessScoreCard } from '@/components/metrics/RobustnessScoreCard';
import { PresetTunerPanel } from '@/components/tuner/PresetTunerPanel';
import { ExportReportButton } from '@/components/report/ExportReportButton';
import { FreshnessBadge } from '@/components/ui/FreshnessBadge';
import { calculateRobustnessScore } from '@/lib/robustScore';

export default function BacktestsPage() {
  const [params] = useSearchParams();
  const { data, isLoading, error } = useBacktests();

  const query = useMemo(() => ({
    strategy: params.get('strategy') ?? 'long_top_score',
    universe: params.get('universe') ?? undefined,
    benchmark: params.get('benchmark') ?? undefined,
    horizon: params.get('horizon') ?? undefined,
  }), [params]);

  // Calculate robustness score if available
  const robustnessScore = data?.results ? calculateRobustnessScore(data.results) : null;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ margin: 0 }}>Backtests</h2>
          <p style={{ margin: '0.25rem 0 0 0', color: '#666' }}>
            Performance historique des stratégies Finance Copilot. Métriques de robustesse et validation statistique des prévisions.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <FreshnessBadge freshness={data?.freshness} />
          <ExportReportButton 
            elementId="backtests-content" 
            fileName={`backtest-report-${new Date().toISOString().slice(0, 10)}.pdf`} 
            title="Finance Copilot - Backtest Report"
            label="Export PDF"
          />
        </div>
      </div>
      
      {/* Parameter tuning section */}
      <div style={{ marginBottom: '2rem' }}>
        <PresetTunerPanel 
          initialParams={{
            confidenceThreshold: 0.6,
            timeWindow: '30d'
          }}
          onParamsChange={(params) => {
            // Handle parameter changes
            console.log("Parameters changed:", params);
          }}
          showRunButton={false}
        />
      </div>
      
      {/* Robustness Score Card */}
      {robustnessScore && (
        <div style={{ marginBottom: '2rem' }}>
          <RobustnessScoreCard
            score={robustnessScore.score}
            grade={robustnessScore.grade}
            metrics={robustnessScore.metrics}
            title="Robustness Score"
            showDetails={true}
          />
        </div>
      )}
      
      {/* Main backtest panel content */}
      <div id="backtests-content">
        <BacktestContent 
          strategy={query.strategy}
          universe={query.universe}
          benchmark={query.benchmark}
          horizon={query.horizon}
          data={data}
          isLoading={isLoading}
          error={error}
        />
      </div>
    </div>
  );
}

function BacktestContent({ strategy, universe, benchmark, horizon, data, isLoading, error }: any) {
  if (isLoading) {
    return <div>Chargement des backtests...</div>;
  }

  if (error) {
    return <div>Erreur: {String(error)}</div>;
  }

  if (!data || !data.results) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        padding: '40px 20px',
        textAlign: 'center',
        border: '1px dashed #ddd',
        borderRadius: '8px',
        backgroundColor: '#fafafa',
        minHeight: '200px',
        marginTop: '20px'
      }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#666' }}>Aucun backtest disponible</h3>
        <p style={{ margin: '5px 0 0 0', color: '#888' }}>Le système de backtesting est en cours de calcul</p>
      </div>
    );
  }

  return (
    <div>
      <h3>Stratégie: {strategy}</h3>
      <p>Univers: {universe || 'Tous'} | Benchmark: {benchmark || 'Non spécifié'}</p>
      
      {/* Display the backtest results */}
      <div>
        <h4>Métriques de Performance</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
          <thead>
            <tr style={{ backgroundColor: '#f3f4f6' }}>
              <th style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'left' }}>Métrique</th>
              <th style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'right' }}>Valeur</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb' }}>Hit Rate</td>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'right' }}>
                {data.results.hit_rate ? (data.results.hit_rate * 100).toFixed(1) + '%' : 'N/A'}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb' }}>CAGR</td>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'right' }}>
                {data.results.cagr ? (data.results.cagr * 100).toFixed(2) + '%' : 'N/A'}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb' }}>Max Drawdown</td>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'right' }}>
                {data.results.max_drawdown ? (data.results.max_drawdown * 100).toFixed(2) + '%' : 'N/A'}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb' }}>Nombre de trades</td>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'right' }}>
                {data.results.n_trades || 'N/A'}
              </td>
            </tr>
            <tr>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb' }}>Volatilité</td>
              <td style={{ padding: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'right' }}>
                {data.results.volatility ? (data.results.volatility * 100).toFixed(2) + '%' : 'N/A'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}