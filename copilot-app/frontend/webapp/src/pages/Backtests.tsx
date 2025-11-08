import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Container, Stack, Group, Text, Title, Card, Skeleton, SimpleGrid } from '@mantine/core';
import { IconChartBar, IconTrendingUp, IconTarget, IconShield, IconActivity } from '@tabler/icons-react';
import { useBacktests } from '@/hooks/useBacktests';
import { RobustnessScoreCard } from '@/components/metrics/RobustnessScoreCard';
import { PresetTunerPanel } from '@/components/tuner/PresetTunerPanel';
import { ExportReportButton } from '@/components/report/ExportReportButton';
import { FreshnessBadge } from '@/components/ui/FreshnessBadge';
import PageHeader from '@/components/layout/PageHeader';
import { TableSkeleton } from '@/components/ui/Skeletons';
import EmptyState from '@/components/ui/EmptyState';
import { ProgressRing, StatsGrid, MetricCard } from '@/components/visualizations';
import { calculateRobustnessScore } from '@/lib/robustScore';

export default function BacktestsPage() {
  const [params] = useSearchParams();
  const { data, isLoading, error, refetch } = useBacktests();

  const query = useMemo(() => ({
    strategy: params.get('strategy') ?? 'long_top_score',
    universe: params.get('universe') ?? undefined,
    benchmark: params.get('benchmark') ?? undefined,
    horizon: params.get('horizon') ?? undefined,
  }), [params]);

  // Calculate robustness score if available (gérer différentes structures)
  const resultsForScore = data?.results || data?.overall_metrics || null;
  const robustnessScore = resultsForScore ? calculateRobustnessScore(resultsForScore) : null;

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Backtests"
        icon={<IconChartBar size={28} />}
        description="Performance historique des stratégies Finance Copilot. Métriques de robustesse et validation statistique des prévisions."
        actions={
          <Group gap="md">
            <FreshnessBadge freshness={data?.freshness} />
            <ExportReportButton 
              elementId="backtests-content" 
              fileName={`backtest-report-${new Date().toISOString().slice(0, 10)}.pdf`} 
              title="Finance Copilot - Backtest Report"
              label="Export PDF"
            />
          </Group>
        }
        onRefresh={() => refetch()}
      />
      
      <Stack gap="xl" mt="xl">
        {/* Parameter tuning section */}
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
        
        {/* Robustness Score Card */}
        {robustnessScore && (
          <RobustnessScoreCard
            score={robustnessScore.score}
            grade={robustnessScore.grade}
            metrics={robustnessScore.metrics}
            title="Robustness Score"
            showDetails={true}
          />
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
      </Stack>
    </Container>
  );
}

function BacktestContent({ strategy, universe, benchmark, horizon, data, isLoading, error }: any) {
  if (isLoading) {
    return (
      <Stack gap="xl">
        <TableSkeleton rows={3} />
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} height={150} />
          ))}
        </SimpleGrid>
      </Stack>
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={<IconChartBar size={48} />}
        title="Erreur de chargement"
        description={error instanceof Error ? error.message : "Impossible de charger les backtests. Veuillez réessayer."}
        action={{
          label: "Rafraîchir",
          onClick: () => window.location.reload()
        }}
      />
    );
  }

  // Vérifier si data.results existe (structure peut varier selon le hook)
  const results = data?.results || data?.overall_metrics || null;
  
  if (!data || !results) {
    return (
      <EmptyState
        icon={<IconChartBar size={48} />}
        title="Aucun backtest disponible"
        description="Le système de backtesting est en cours de calcul. Les résultats seront disponibles une fois les calculs terminés."
        action={{
          label: "Rafraîchir",
          onClick: () => window.location.reload()
        }}
      />
    );
  }

  // Gérer différentes structures de données (results ou overall_metrics)
  // Essayer d'abord overall_metrics, puis results, puis valeurs par défaut
  const metrics = data?.overall_metrics || results || {};
  const hitRate = (metrics.hit_rate ?? results?.hit_rate ?? 0) * 100;
  const cagr = (metrics.cagr ?? metrics.avg_return ?? results?.cagr ?? results?.avg_return ?? 0) * 100;
  const maxDrawdown = Math.abs((metrics.max_drawdown ?? results?.max_drawdown ?? 0) * 100);
  const volatility = (metrics.volatility ?? results?.volatility ?? 0) * 100;
  const nTrades = metrics.n_trades ?? metrics.total_trades ?? results?.n_trades ?? results?.total_trades ?? 0;

  return (
    <Stack gap="xl">
      {/* Info stratégie */}
      <Card padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Title order={4}>Stratégie: {strategy}</Title>
          <Text c="dimmed" size="sm">
            Univers: {universe || 'Tous'} | Benchmark: {benchmark || 'Non spécifié'}
          </Text>
        </Stack>
      </Card>
      
      {/* Métriques visuelles principales */}
      <StatsGrid
        metrics={[
          {
            label: 'Hit Rate',
            value: `${hitRate.toFixed(1)}%`,
            icon: <IconTarget size={20} />,
            color: hitRate > 50 ? 'teal' : 'orange',
            description: 'Taux de réussite des prévisions',
          },
          {
            label: 'CAGR',
            value: `${cagr > 0 ? '+' : ''}${cagr.toFixed(2)}%`,
            change: cagr,
            icon: <IconTrendingUp size={20} />,
            color: cagr > 0 ? 'teal' : 'red',
            description: 'Croissance annuelle composée',
          },
          {
            label: 'Max Drawdown',
            value: `${maxDrawdown.toFixed(2)}%`,
            icon: <IconShield size={20} />,
            color: maxDrawdown < 20 ? 'teal' : maxDrawdown < 40 ? 'orange' : 'red',
            description: 'Perte maximale observée',
          },
          {
            label: 'Volatilité',
            value: `${volatility.toFixed(2)}%`,
            icon: <IconActivity size={20} />,
            color: volatility < 15 ? 'teal' : volatility < 30 ? 'orange' : 'red',
            description: 'Volatilité des rendements',
          },
        ]}
      />

      {/* Rings de performance */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
        <ProgressRing
          label="Hit Rate"
          value={hitRate}
          color={hitRate > 50 ? 'teal' : 'orange'}
          subtitle={`${nTrades} trades exécutés`}
          badge={{
            label: hitRate > 50 ? 'Bon' : 'Moyen',
            color: hitRate > 50 ? 'teal' : 'orange',
          }}
          icon={<IconTarget size={16} />}
        />
        <ProgressRing
          label="CAGR"
          value={Math.min(100, Math.max(0, cagr + 50))}
          color={cagr > 0 ? 'teal' : 'red'}
          subtitle={`${cagr > 0 ? '+' : ''}${cagr.toFixed(2)}% annuel`}
          badge={{
            label: cagr > 10 ? 'Excellent' : cagr > 0 ? 'Positif' : 'Négatif',
            color: cagr > 10 ? 'teal' : cagr > 0 ? 'blue' : 'red',
          }}
          icon={<IconTrendingUp size={16} />}
        />
        <ProgressRing
          label="Risque (Drawdown)"
          value={Math.min(100, maxDrawdown)}
          color={maxDrawdown < 20 ? 'teal' : maxDrawdown < 40 ? 'orange' : 'red'}
          subtitle={`Max: ${maxDrawdown.toFixed(2)}%`}
          badge={{
            label: maxDrawdown < 20 ? 'Faible' : maxDrawdown < 40 ? 'Moyen' : 'Élevé',
            color: maxDrawdown < 20 ? 'teal' : maxDrawdown < 40 ? 'orange' : 'red',
          }}
          icon={<IconShield size={16} />}
        />
      </SimpleGrid>
    </Stack>
  );
}