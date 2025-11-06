import { Stack, Text, Group, ActionIcon, Alert, Badge, Skeleton } from '@mantine/core';
import { IconRefresh, IconAlertCircle, IconSparkles, IconLoader } from '@tabler/icons-react';
import { useRecommendations } from '../../hooks/useRecommendations';
import { RecommendationCard } from '../recommendations/RecommendationCard';

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
  
  // Loading state
  if (isLoading) {
    return (
      <Stack gap="md">
        <Group justify="space-between">
          <Group gap="xs">
            <IconSparkles size={24} />
            <Text size="lg" fw={700}>Today's Smart Picks</Text>
          </Group>
        </Group>
        <Stack gap="md">
          <Skeleton height={200} radius="md" />
          <Skeleton height={200} radius="md" />
          <Skeleton height={200} radius="md" />
        </Stack>
      </Stack>
    );
  }
  
  // Error state
  if (error) {
    return (
      <Alert
        icon={<IconAlertCircle size={20} />}
        title="Failed to Load Recommendations"
        color="red"
        variant="light"
      >
        <Text size="sm">
          Unable to fetch daily recommendations. Please try again later.
        </Text>
        {error && (
          <Text size="xs" c="dimmed" mt="xs">
            Error: {error.message}
          </Text>
        )}
      </Alert>
    );
  }
  
  // Empty state
  if (!data || !data.recommendations || data.recommendations.length === 0) {
    return (
      <Alert
        icon={<IconAlertCircle size={20} />}
        title="No Recommendations Available"
        color="yellow"
        variant="light"
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
  return (
    <Stack gap="md">
      {/* Header */}
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <IconSparkles size={24} color="#4169E1" />
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
        >
          {isFetching ? <IconLoader size={18} /> : <IconRefresh size={18} />}
        </ActionIcon>
      </Group>
      
      {/* Market Context Badge */}
      <Group gap="xs">
        <Text size="sm" c="dimmed">Market:</Text>
        <Badge variant="light" color="gray">
          {data.market_context.regime}
        </Badge>
        <Text size="sm" c="dimmed">•</Text>
        <Text size="sm" c="dimmed">
          Valid for {hoursRemaining}h
        </Text>
      </Group>
      
      {/* Recommendations List */}
      <Stack gap="md">
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
