import { Stack, Group, Alert, Text } from '@mantine/core';
import { IconAlertCircle, IconLoader } from '@tabler/icons-react';
import { useIntelligence } from '../../hooks/useIntelligence';
import { useMarketContext } from '../../hooks/useMarketContext';
import { RegimeBadge } from '../intelligence/RegimeBadge';
import { InsightsPanel } from '../intelligence/InsightsPanel';
import { OpportunitiesGrid } from '../intelligence/OpportunitiesGrid';
import { RisksPanel } from '../intelligence/RisksPanel';
import { DriversChips } from '../intelligence/DriversChips';

/**
 * IntelligenceDashboardWidget
 * 
 * "Chef d'orchestre" widget that combines Intelligence and Context services
 * to provide an intelligent market overview.
 * 
 * Features:
 * - Market regime classification with confidence
 * - LLM-generated market insights
 * - Top opportunities identified
 * - Key risks highlighted
 * - Market drivers display
 * 
 * This widget is the central intelligence hub of the dashboard,
 * providing users with immediate understanding of:
 * - What's happening in the market (regime + insights)
 * - Where the opportunities are (top picks)
 * - What to watch out for (risks)
 * - What's driving the market (key drivers)
 * 
 * @example
 * ```tsx
 * <IntelligenceDashboardWidget />
 * ```
 */
export function IntelligenceDashboardWidget() {
  // Fetch intelligence data
  const {
    data: intelligence,
    isLoading: isLoadingIntel,
    error: errorIntel,
  } = useIntelligence();

  // Fetch market context data
  const {
    data: context,
    isLoading: isLoadingContext,
    error: errorContext,
  } = useMarketContext();

  // Loading state
  if (isLoadingIntel || isLoadingContext) {
    return (
      <Alert
        icon={<IconLoader size={20} />}
        title="Loading Market Intelligence..."
        color="blue"
        variant="light"
      >
        <Text size="sm">Fetching latest market data and insights...</Text>
      </Alert>
    );
  }

  // Error state
  if (errorIntel || errorContext) {
    return (
      <Alert
        icon={<IconAlertCircle size={20} />}
        title="Failed to Load Intelligence Data"
        color="red"
        variant="light"
      >
        <Text size="sm">
          Unable to fetch market intelligence. Please try again later.
        </Text>
        {errorIntel && (
          <Text size="xs" c="dimmed" mt="xs">
            Intelligence Error: {errorIntel.message}
          </Text>
        )}
        {errorContext && (
          <Text size="xs" c="dimmed" mt="xs">
            Context Error: {errorContext.message}
          </Text>
        )}
      </Alert>
    );
  }

  // Empty state (no data)
  if (!intelligence || !context) {
    return (
      <Alert
        icon={<IconAlertCircle size={20} />}
        title="No Intelligence Data Available"
        color="yellow"
        variant="light"
      >
        <Text size="sm">
          Intelligence data is not yet available. The system is still analyzing market
          conditions.
        </Text>
      </Alert>
    );
  }

  // Success state - Render full intelligence dashboard
  return (
    <Stack gap="lg">
      {/* Market Regime Section */}
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <RegimeBadge regime={context.regime} confidence={context.confidence} />
        <DriversChips drivers={context.key_drivers} />
      </Group>

      {/* LLM Insights Section */}
      <InsightsPanel insights={intelligence.insights} />

      {/* Opportunities and Risks Section */}
      <Group align="flex-start" grow preventGrowOverflow={false} wrap="wrap">
        <OpportunitiesGrid opportunities={intelligence.insights.opportunities} />
        <RisksPanel risks={intelligence.insights.risks} />
      </Group>

      {/* Data Freshness Indicator */}
      <Alert color="gray" variant="light" styles={{ root: { marginTop: 'auto' } }}>
        <Text size="xs" c="dimmed">
          Last updated: {new Date(intelligence.timestamp).toLocaleString()} | Data freshness:{' '}
          Forecasts ({intelligence.data_freshness.forecasts_age}), Macro (
          {intelligence.data_freshness.macro_age}), News (
          {intelligence.data_freshness.news_age})
        </Text>
      </Alert>
    </Stack>
  );
}
