import { Container, Stack, SimpleGrid, Badge, Group, Title, Tabs } from '@mantine/core';
import { IconChartLine, IconTrendingUp, IconTrendingDown, IconMinus, IconRadar, IconSparkles } from '@tabler/icons-react';
import { useForecasts } from '@/hooks/useForecasts';
import PageHeader from '@/components/layout/PageHeader';
import { ForecastsSkeleton } from '@/components/ui/Skeletons';
import EmptyState from '@/components/ui/EmptyState';
import { ProgressRing, StatsGrid, ComparisonChart, RadarChart, SparklineCard, DistributionChart } from '@/components/visualizations';
import { useMemo } from 'react';

/**
 * Prévisions avec visualisations riches
 * Graphiques, métriques visuelles, comparaisons
 */
export default function ForecastsMinimal() {
  const { data, isLoading, error } = useForecasts({ limit: 50 });

  const forecasts = data?.rows || [];
  
  // Calculer statistiques pour visualisations
  const stats = useMemo(() => {
    if (forecasts.length === 0) return null;
    
    const upCount = forecasts.filter(f => f.direction === 'up').length;
    const downCount = forecasts.filter(f => f.direction === 'down').length;
    const avgConfidence = forecasts.reduce((sum, f) => sum + (f.confidence || 0), 0) / forecasts.length;
    const avgReturn = forecasts.reduce((sum, f) => sum + (f.expected_return || 0), 0) / forecasts.length;
    
    return {
      total: forecasts.length,
      upCount,
      downCount,
      avgConfidence: avgConfidence * 100,
      avgReturn: avgReturn * 100,
    };
  }, [forecasts]);

  // Données pour graphique de comparaison
  const chartData = useMemo(() => {
    const byHorizon = forecasts.reduce((acc, f) => {
      const horizon = f.horizon || '1d';
      if (!acc[horizon]) {
        acc[horizon] = { up: 0, down: 0, flat: 0 };
      }
      acc[horizon][f.direction || 'flat']++;
      return acc;
    }, {} as Record<string, { up: number; down: number; flat: number }>);

    return Object.entries(byHorizon).map(([horizon, counts]) => ({
      horizon,
      'Hausse': counts.up,
      'Baisse': counts.down,
      'Neutre': counts.flat,
    }));
  }, [forecasts]);

  // Top forecasts pour visualisation
  const topForecasts = useMemo(() => {
    return forecasts
      .filter(f => f.confidence && f.confidence > 0.6)
      .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
      .slice(0, 12);
  }, [forecasts]);

  // Données pour RadarChart (scores multi-dimensionnels)
  const radarData = useMemo(() => {
    return topForecasts.slice(0, 4).map(forecast => ({
      ticker: forecast.ticker,
      Confiance: (forecast.confidence || 0) * 100,
      Rendement: Math.abs((forecast.expected_return || 0) * 100),
      Momentum: forecast.direction === 'up' ? 80 : forecast.direction === 'down' ? 20 : 50,
      Stabilité: (forecast.confidence || 0) * 100 * 0.8,
    }));
  }, [topForecasts]);

  // Données pour DistributionChart (distribution des confiances)
  const confidenceDistribution = useMemo(() => {
    const bins = [
      { bin: '0-20', count: 0 },
      { bin: '20-40', count: 0 },
      { bin: '40-60', count: 0 },
      { bin: '60-80', count: 0 },
      { bin: '80-100', count: 0 },
    ];
    
    forecasts.forEach(f => {
      const conf = (f.confidence || 0) * 100;
      if (conf < 20) bins[0].count++;
      else if (conf < 40) bins[1].count++;
      else if (conf < 60) bins[2].count++;
      else if (conf < 80) bins[3].count++;
      else bins[4].count++;
    });
    
    return bins;
  }, [forecasts]);

  // Données pour Sparklines (tendances par ticker)
  const sparklineData = useMemo(() => {
    const tickerGroups = forecasts.reduce((acc, f) => {
      if (!acc[f.ticker]) acc[f.ticker] = [];
      acc[f.ticker].push({
        date: f.calculation_timestamp || new Date().toISOString(),
        value: (f.expected_return || 0) * 100,
      });
      return acc;
    }, {} as Record<string, Array<{ date: string; value: number }>>);
    
    return Object.entries(tickerGroups)
      .map(([ticker, data]) => ({
        ticker,
        data: data.sort((a, b) => a.date.localeCompare(b.date)).slice(-10), // Derniers 10 points
        latestValue: data[data.length - 1]?.value || 0,
        change: data.length > 1 ? data[data.length - 1].value - data[0].value : 0,
      }))
      .slice(0, 8); // Top 8 tickers
  }, [forecasts]);

  if (isLoading) {
    return (
      <Container size="xl" py="xl" data-testid="forecasts-pro">
        <PageHeader
          title="Prévisions de marché"
          icon={<IconChartLine size={28} />}
          description="Analyse prédictive avec ML + LLM"
        />
        <ForecastsSkeleton />
      </Container>
    );
  }

  // Gérer les cas d'erreur ou de données vides
  if (error) {
    return (
      <Container size="xl" py="xl">
        <PageHeader
          title="Prévisions de marché"
          icon={<IconChartLine size={28} />}
          description="Analyse prédictive avec ML + LLM"
        />
        <EmptyState
          icon={<IconChartLine size={48} />}
          title="Erreur de chargement"
          description={error instanceof Error ? error.message : "Impossible de charger les prévisions. Veuillez réessayer."}
          action={{
            label: "Rafraîchir",
            onClick: () => window.location.reload()
          }}
        />
      </Container>
    );
  }

  // Si pas d'erreur mais pas de données
  if (!isLoading && forecasts.length === 0) {
    return (
      <Container size="xl" py="xl">
        <PageHeader
          title="Prévisions de marché"
          icon={<IconChartLine size={28} />}
          description="Analyse prédictive avec ML + LLM"
        />
        <EmptyState
          icon={<IconChartLine size={48} />}
          title="Aucune prévision disponible"
          description="Les prévisions seront générées toutes les 6h. Le système est en train de calculer les premières prévisions."
          action={{
            label: "Rafraîchir",
            onClick: () => window.location.reload()
          }}
        />
      </Container>
    );
  }

  // Si pas de stats calculables (données invalides)
  if (!stats) {
    return (
      <Container size="xl" py="xl">
        <PageHeader
          title="Prévisions de marché"
          icon={<IconChartLine size={28} />}
          description="Analyse prédictive avec ML + LLM"
        />
        <EmptyState
          icon={<IconChartLine size={48} />}
          title="Données invalides"
          description="Les prévisions chargées ne sont pas dans un format valide. Veuillez réessayer plus tard."
        />
      </Container>
    );
  }

  return (
    <Container size="xl" py="xl" data-testid="forecasts-pro">
      <PageHeader
        title="Prévisions de marché"
        icon={<IconChartLine size={28} />}
        description="Analyse prédictive avec ML + LLM"
        stats={[
          { label: 'Prévisions', value: stats.total },
          { label: 'Confiance moy.', value: `${stats.avgConfidence.toFixed(1)}%` },
        ]}
      />

      <Stack gap="xl" mt="xl">
        {/* Métriques visuelles */}
        <StatsGrid
          metrics={[
            {
              label: 'Hausse attendue',
              value: stats.upCount,
              change: (stats.upCount / stats.total) * 100,
              icon: <IconTrendingUp size={20} />,
              color: 'teal',
              description: `${((stats.upCount / stats.total) * 100).toFixed(1)}% des prévisions`,
            },
            {
              label: 'Baisse attendue',
              value: stats.downCount,
              change: -(stats.downCount / stats.total) * 100,
              icon: <IconTrendingDown size={20} />,
              color: 'red',
              description: `${((stats.downCount / stats.total) * 100).toFixed(1)}% des prévisions`,
            },
            {
              label: 'Confiance moyenne',
              value: `${stats.avgConfidence.toFixed(1)}%`,
              icon: <IconChartLine size={20} />,
              color: 'blue',
              description: 'Niveau de confiance global',
            },
            {
              label: 'Rendement moyen',
              value: `${stats.avgReturn > 0 ? '+' : ''}${stats.avgReturn.toFixed(2)}%`,
              change: stats.avgReturn,
              icon: <IconMinus size={20} />,
              color: stats.avgReturn > 0 ? 'teal' : 'red',
              description: 'Rendement attendu moyen',
            },
          ]}
        />

        {/* Graphique de comparaison par horizon */}
        {chartData.length > 0 && (
          <ComparisonChart
            title="Répartition des prévisions par horizon"
            description="Distribution des signaux haussiers, baissiers et neutres"
            data={chartData}
            index="horizon"
            categories={['Hausse', 'Baisse', 'Neutre']}
            colors={['teal', 'red', 'gray']}
            type="bar"
          />
        )}

        {/* Tabs pour différentes vues */}
        <Tabs defaultValue="rings" mt="xl">
          <Tabs.List>
            <Tabs.Tab value="rings" leftSection={<IconSparkles size={16} />}>
              Rings de Confiance
            </Tabs.Tab>
            <Tabs.Tab value="radar" leftSection={<IconRadar size={16} />}>
              Scores Multi-Dimensionnels
            </Tabs.Tab>
            <Tabs.Tab value="sparklines" leftSection={<IconChartLine size={16} />}>
              Tendances
            </Tabs.Tab>
            <Tabs.Tab value="distribution" leftSection={<IconChartLine size={16} />}>
              Distribution
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="rings" pt="xl">
            <Group justify="space-between" mb="lg">
              <Title order={3}>Top Prévisions (Confiance ≥ 60%)</Title>
              <Badge variant="light" size="lg">
                {topForecasts.length} prévisions
              </Badge>
            </Group>
            {topForecasts.length > 0 ? (
              <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing="lg" data-testid="forecasts-grid">
                {topForecasts.map((forecast) => {
                  const confidence = (forecast.confidence || 0) * 100;
                  const expectedReturn = (forecast.expected_return || 0) * 100;
                  const isUp = forecast.direction === 'up';
                  const isDown = forecast.direction === 'down';
                  
                  return (
                    <ProgressRing
                      key={`${forecast.ticker}-${forecast.horizon}`}
                      label={forecast.ticker}
                      value={confidence}
                      color={isUp ? 'teal' : isDown ? 'red' : 'gray'}
                      subtitle={`${expectedReturn > 0 ? '+' : ''}${expectedReturn.toFixed(2)}% attendu`}
                      badge={{
                        label: forecast.horizon || '1d',
                        color: isUp ? 'teal' : isDown ? 'red' : 'gray',
                      }}
                      icon={isUp ? <IconTrendingUp size={16} /> : isDown ? <IconTrendingDown size={16} /> : <IconMinus size={16} />}
                      size={120}
                    />
                  );
                })}
              </SimpleGrid>
            ) : (
              <EmptyState
                icon={<IconSparkles size={48} />}
                title="Aucune prévision avec confiance élevée"
                description="Il n'y a pas de prévisions avec une confiance ≥ 60%. Réduisez le seuil ou attendez de nouvelles prévisions."
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="radar" pt="xl">
            {radarData.length > 0 ? (
              <RadarChart
                title="Scores Multi-Dimensionnels - Top 4 Prévisions"
                description="Analyse complète : Confiance, Rendement, Momentum, Stabilité"
                data={radarData}
                index="ticker"
                categories={['Confiance', 'Rendement', 'Momentum', 'Stabilité']}
                colors={['teal', 'blue', 'orange', 'indigo']}
              />
            ) : (
              <EmptyState
                icon={<IconRadar size={48} />}
                title="Pas de données pour le radar"
                description="Il faut au moins 4 prévisions avec confiance élevée pour afficher le graphique radar"
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="sparklines" pt="xl">
            <Title order={3} mb="lg">Tendances par Ticker</Title>
            {sparklineData.length > 0 ? (
              <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
                {sparklineData.map(({ ticker, data, latestValue, change }) => (
                  <SparklineCard
                    key={ticker}
                    label={ticker}
                    value={`${latestValue > 0 ? '+' : ''}${latestValue.toFixed(2)}%`}
                    change={change}
                    data={data}
                    color={change >= 0 ? 'teal' : 'red'}
                    icon={change >= 0 ? <IconTrendingUp size={16} /> : <IconTrendingDown size={16} />}
                  />
                ))}
              </SimpleGrid>
            ) : (
              <EmptyState
                icon={<IconChartLine size={48} />}
                title="Pas de données de tendances"
                description="Il faut au moins une prévision avec historique pour afficher les tendances"
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="distribution" pt="xl">
            <DistributionChart
              title="Distribution des Niveaux de Confiance"
              description="Répartition des prévisions par niveau de confiance"
              data={confidenceDistribution}
              color="blue"
            />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
