import { Stack, Title, Text, Group, Alert, Badge, Skeleton } from '@mantine/core';
import { IconSparkles, IconInfoCircle, IconRadar2, IconTrendingUp, IconNews, IconActivity } from '@tabler/icons-react';
import HealthBar from '@/components/widgets/HealthBar';
import { AdaptiveLayoutProvider } from '@/contexts/AdaptiveLayoutContext';
import classes from './dashboard.module.css';
import { useDashboardKPIs } from '@/hooks/useDashboardKPIs';

// NOTE: These components MUST be non-lazy because they use useAdaptiveLayout hook
// which requires AdaptiveLayoutProvider context. Lazy loading breaks context access.
// Import directly instead of lazy loading for context-dependent components.
import { RegimeBadgeAdaptive } from '@/components/adaptive/RegimeBadgeAdaptive';
import { LayoutModeToggle } from '@/components/adaptive/LayoutModeToggle';
import { DynamicWidgetGrid } from '@/components/adaptive/DynamicWidgetGrid';

/**
 * Dashboard - Adaptive Layout
 * 
 * Dashboard that automatically adapts its layout based on market regime.
 * Surfaces the most relevant widgets first according to market context.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 * Optimized: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 * Task: TASK-1.3 - Lazy loading for initial load optimization
 */
function DashboardContent() {
  const { data: kpis, isLoading: kpiLoading } = useDashboardKPIs();

  // Extract KPIs with proper fallbacks
  const totalForecasts = kpis?.forecasts?.total ?? kpis?.forecasts_count ?? kpis?.total_forecasts ?? 0;
  const highConv = kpis?.forecasts?.high_confidence ?? 0;
  const newsCount = kpis?.news?.recent_count ?? 0;
  // Handle hit_rate - can be 0-1 or 0-100
  const rawHitRate = kpis?.backtests?.hit_rate ?? 0;
  const hitRate = rawHitRate > 1 ? rawHitRate / 100 : rawHitRate;
  const tickersTracked = kpis?.tickers ?? kpis?.tickers_tracked ?? 0;

  const safePercent = (value: number) => {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.min(1, value));
  };

  const metrics = [
    {
      label: 'Prévisions actives',
      value: totalForecasts.toLocaleString(),
      detail: `${tickersTracked} tickers suivis`,
      accent: classes.metricAccentBlue,
      icon: <IconRadar2 size={18} />,
      progress: safePercent(totalForecasts / 500),
    },
    {
      label: 'Haute confiance',
      value: `${Math.round((highConv / Math.max(totalForecasts || 1, 1)) * 100) || 0}%`,
      detail: `${highConv.toLocaleString()} signaux`,
      accent: classes.metricAccentGreen,
      icon: <IconTrendingUp size={18} />,
      progress: safePercent(highConv / Math.max(totalForecasts || 1, 1)),
    },
    {
      label: 'Actualités récentes',
      value: newsCount.toLocaleString(),
      detail: 'Dernières 60 min',
      accent: classes.metricAccentPurple,
      icon: <IconNews size={18} />,
      progress: safePercent(newsCount / 80),
    },
    {
      label: 'Taux de réussite',
      value: `${Math.round((hitRate > 1 ? hitRate : hitRate * 100) || 0)}%`,
      detail: kpis?.backtests?.status ?? 'Surveillance en direct',
      accent: classes.metricAccentOrange,
      icon: <IconActivity size={18} />,
      progress: safePercent(hitRate > 1 ? hitRate / 100 : hitRate),
    },
  ];

  return (
    <div className={classes.dashboardRoot}>
      <div className={classes.gridOverlay} aria-hidden />
      <div className={classes.ambientOrbs} aria-hidden>
        <span className={`${classes.orb} ${classes.orbOne}`} />
        <span className={`${classes.orb} ${classes.orbTwo}`} />
        <span className={`${classes.orb} ${classes.orbThree}`} />
      </div>
      <Stack data-testid="dashboard-root" gap="xl" className={classes.inner}>
        {/* Header */}
        <div className={classes.hero}>
          <Stack gap="lg">
            <Group justify="space-between" align="flex-start">
              <div>
                <Group gap="xs" align="center" className={classes.heroHeading}>
                  <div className={classes.sparkleBadge}>
                    <IconSparkles size={20} />
                  </div>
                  <Title order={1} size="h2">Tableau de Bord Adaptatif</Title>
                </Group>
                <Text c="gray.3" size="sm" mt={4}>
                  Mise en page intelligente qui s'adapte aux conditions de marché en temps réel
                </Text>
              </div>

              <Stack gap={6} align="flex-end">
                <Badge className={classes.liveBadge} radius="xl" size="lg" variant="light" color="green">
                  Données en direct
                </Badge>
                <Group gap="md" align="center">
                  <RegimeBadgeAdaptive />
                  <LayoutModeToggle />
                </Group>
              </Stack>
            </Group>

            {/* Info Alert */}
            <Alert
              color="blue"
              variant="light"
              icon={<IconInfoCircle size={20} />}
              classNames={{ root: classes.alertGlass }}
            >
              <Group gap="xs" align="center">
                <Badge size="sm" color="blue" variant="dot">Mode Adaptatif Actif</Badge>
                <Text size="sm" c="dimmed">
                  La mise en page s'ajuste automatiquement selon le régime de marché détecté. 
                  Passez en mode Manuel pour verrouiller la mise en page actuelle.
                </Text>
              </Group>
            </Alert>

            <div className={classes.metricRow}>
              {(kpiLoading ? Array.from({ length: 4 }) : metrics).map((metric, idx) => (
                <div key={idx} className={`${classes.metricCard} ${!kpiLoading ? metric.accent : ''}`}>
                  {kpiLoading ? (
                    <Stack gap={6}>
                      <Skeleton height={18} width="60%" radius="xl" />
                      <Skeleton height={28} width="50%" />
                      <Skeleton height={8} radius="xl" />
                      <Skeleton height={12} width="70%" />
                    </Stack>
                  ) : (
                    <>
                      <Group gap={8} align="center" className={classes.metricHeader}>
                        <div className={classes.metricIcon}>{metric.icon}</div>
                        <Text size="xs" c="gray.4" fw={600} tt="uppercase" className={classes.metricLabel}>
                          {metric.label}
                        </Text>
                      </Group>
                      <Group align="flex-end" gap={6}>
                        <Text size="xl" fw={700} className={classes.metricValue}>
                          {metric.value}
                        </Text>
                      </Group>
                      <div className={classes.metricProgress}>
                        <span
                          className={classes.progressFill}
                          style={{ width: `${Math.round((metric.progress ?? 0) * 100)}%` }}
                        />
                      </div>
                      <Text size="xs" c="gray.4">{metric.detail}</Text>
                    </>
                  )}
                </div>
              ))}
            </div>
          </Stack>
        </div>

        {/* System Health Bar */}
        <div className={classes.sectionCard}>
          <HealthBar />
        </div>

        {/* Dynamic Widget Grid - Adapts to market context */}
        <div className={classes.widgetSection}>
          <div className={classes.widgetSectionHeader}>
            <Title order={3} size="h4" fw={600} c="gray.1">
              Mise en page adaptative
            </Title>
            <Text size="sm" c="gray.5" mt={4}>
              Les widgets se réorganisent automatiquement selon la confiance du régime de marché
            </Text>
          </div>
          <DynamicWidgetGrid />
        </div>
      </Stack>
    </div>
  );
}

/**
 * Dashboard with Adaptive Layout Provider
 */
export default function Dashboard() {
  return (
    <AdaptiveLayoutProvider>
      <DashboardContent />
    </AdaptiveLayoutProvider>
  );
}
