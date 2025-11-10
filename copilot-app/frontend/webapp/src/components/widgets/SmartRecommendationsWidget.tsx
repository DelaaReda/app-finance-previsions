import { Stack, Text, Group, ActionIcon, Alert, Badge, Skeleton, Card } from '@mantine/core';
import { IconRefresh, IconAlertCircle, IconSparkles, IconLoader, IconArrowUpRight, IconShieldCheck } from '@tabler/icons-react';
import { useRecommendations } from '../../hooks/useRecommendations';
import { RecommendationCard } from '../recommendations/RecommendationCard';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import classes from './SmartRecommendationsWidget.module.css';

interface SmartRecommendationsWidgetProps {
  universe?: string[];
  limit?: number;
}

/**
 * SmartRecommendationsWidget
 * 
 * Displays daily smart recommendations powered by ML + LLM.
 * 
 * Features:
 * - Top 3 actionable recommendations
 * - ML scoring + LLM reasoning
 * - Catalysts identification
 * - Risk assessment
 * - Auto-refresh (hourly)
 * - Drill-down navigation
 * 
 * @param universe - Optional list of tickers to consider
 * @param limit - Number of recommendations to display (default 3)
 * 
 * @example
 * ```tsx
 * <SmartRecommendationsWidget limit={3} />
 * ```
 */
export function SmartRecommendationsWidget({ 
  universe, 
  limit = 3 
}: SmartRecommendationsWidgetProps) {
  const { data, isLoading, error, refetch, isFetching } = useRecommendations(universe, limit);

  const glassWrapper = (children: React.ReactNode) => (
    <Card padding="lg" radius="xl" className={`${sharedStyles.glassCard} ${classes.widgetCard}`}>
      {children}
    </Card>
  );

  if (isLoading) {
    return glassWrapper(
      <Stack gap="md">
        <Group justify="space-between">
          <Group gap="xs">
            <IconSparkles size={24} />
            <Text size="lg" fw={700}>Sélections du Jour</Text>
          </Group>
        </Group>
        <Stack gap="md">
          {[...Array(3)].map((_, idx) => (
            <Card key={idx} padding="md" radius="lg" className={`${sharedStyles.skeletonCard} ${classes.skeletonCard}`}>
              <Stack gap="sm">
                <Skeleton height={18} width="40%" radius="xl" />
                <Skeleton height={28} width="50%" />
                <Skeleton height={12} width="60%" />
                <Skeleton height={12} width="50%" />
                <Skeleton height={12} width="70%" />
              </Stack>
            </Card>
          ))}
        </Stack>
      </Stack>
    );
  }
  
  // Error state
  if (error) {
    return glassWrapper(
      <Alert
        icon={<IconAlertCircle size={20} />}
        title="Échec du chargement des recommandations"
        color="red"
        variant="light"
        action={
          <Button size="xs" variant="light" onClick={() => refetch()}>
            Réessayer
          </Button>
        }
      >
        <Text size="sm">
          Impossible de récupérer les recommandations quotidiennes. Veuillez réessayer plus tard.
        </Text>
        {error && (
          <Text size="xs" c="dimmed" mt="xs">
            Erreur: {error.message}
          </Text>
        )}
      </Alert>
    );
  }
  
  // Empty state
  if (!data || !data.recommendations || data.recommendations.length === 0) {
    return glassWrapper(
      <Alert
        icon={<IconAlertCircle size={20} />}
        title="Aucune recommandation disponible"
        color="yellow"
        variant="light"
        action={
          <Button size="xs" variant="light" onClick={() => refetch()}>
            Actualiser
          </Button>
        }
      >
        <Text size="sm">
          No recommendations for today. The system is analyzing market conditions.
        </Text>
      </Alert>
    );
  }
  
  // Calculate time remaining
  const validUntil = new Date(data.valid_until);
  const now = new Date();
  const hoursRemaining = Math.max(0, Math.round((validUntil.getTime() - now.getTime()) / (60 * 60 * 1000)));
  
  // Success state
  return glassWrapper(
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between" align="center">
          <Group gap="xs">
            <div className={sharedStyles.sparkIcon}>
              <IconSparkles size={18} />
            </div>
          <Text size="lg" fw={700}>Today's Smart Picks</Text>
          <Badge variant="light" color="blue">
            {data.recommendations.length} {data.recommendations.length === 1 ? 'pick' : 'picks'}
          </Badge>
        </Group>
        
        <ActionIcon
          variant="light"
          onClick={() => refetch()}
          loading={isFetching}
          aria-label="Refresh recommendations"
          className={sharedStyles.actionIcon}
        >
          {isFetching ? <IconLoader size={18} /> : <IconRefresh size={18} />}
        </ActionIcon>
      </Group>
      
      {/* Market Context Badge */}
      <div className={sharedStyles.contextPill}>
        <Badge size="xs" variant="dot" color="cyan">
          {data.market_context.regime}
        </Badge>
        <Text size="sm" c="dimmed">
          Valid for {hoursRemaining}h
        </Text>
      </div>
      
      {/* Recommendations List */}
      <Stack gap="md" className={classes.recommendationsList}>
        {data.recommendations.map((rec, index) => (
          <RecommendationCard key={`${rec.ticker}-${index}`} recommendation={rec} />
        ))}
      </Stack>
      
      {/* Footer */}
      <Text size="xs" c="dimmed" ta="center">
        Powered by ML + LLM • Updated {new Date(data.generated_at).toLocaleString()}
      </Text>
    </Stack>
  );
}
