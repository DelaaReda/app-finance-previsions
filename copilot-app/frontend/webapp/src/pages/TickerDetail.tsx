/**
 * Ticker Detail Page
 * 
 * Displays comprehensive information about a specific ticker.
 * Preserves drill-down context and provides smart navigation.
 * 
 * Author: ELENA-39
 * Task: FC-INT-027
 */

import { useParams, useLocation } from 'react-router-dom';
import { Stack, Title, Text, Group, Badge, Button, Tabs, Grid, Alert, Breadcrumbs, Anchor, Card } from '@mantine/core';
import { IconArrowLeft, IconSparkles, IconChartLine, IconNews, IconNetwork, IconTarget } from '@tabler/icons-react';
import { useDrillDown, type DrillDownState } from '../contexts/DrillDownContext';
import { useForecasts } from '../hooks/useForecasts';
import { ForecastCardsWidget } from '../components/widgets/ForecastCardsWidget';

/**
 * Context Breadcrumb Component
 */
function ContextBreadcrumb({ ticker, drillDown }: { ticker: string; drillDown: DrillDownState | null }) {
  const { goBack } = useDrillDown();
  
  if (!drillDown) {
    return (
      <Breadcrumbs>
        <Anchor onClick={() => window.history.back()}>Dashboard</Anchor>
        <Text>{ticker}</Text>
      </Breadcrumbs>
    );
  }
  
  const sourceLabels: Record<string, string> = {
    recommendations: 'Recommendations',
    forecasts: 'Forecasts',
    intelligence: 'Intelligence',
    correlations: 'Correlations',
    news: 'News',
    opportunities: 'Opportunities',
    risks: 'Risks',
    dashboard: 'Dashboard',
    unknown: 'Previous',
  };
  
  const sourceLabel = sourceLabels[drillDown.source] || 'Previous';
  
  return (
    <Breadcrumbs>
      <Anchor onClick={() => window.location.href = '/'}>Dashboard</Anchor>
      <Anchor onClick={goBack}>{sourceLabel}</Anchor>
      <Text>{ticker}</Text>
    </Breadcrumbs>
  );
}

/**
 * Context Badge Component
 */
function ContextBadge({ drillDown }: { drillDown: DrillDownState | null }) {
  const { getContextDescription } = useDrillDown();
  
  if (!drillDown) return null;
  
  const description = getContextDescription();
  
  const colorMap: Record<string, string> = {
    recommendations: 'blue',
    forecasts: 'indigo',
    intelligence: 'violet',
    correlations: 'grape',
    news: 'cyan',
    opportunities: 'green',
    risks: 'red',
    dashboard: 'gray',
    unknown: 'gray',
  };
  
  const color = colorMap[drillDown.source] || 'gray';
  
  return (
    <Badge
      size="lg"
      variant="light"
      color={color}
      leftSection={<IconSparkles size={16} />}
    >
      {description}
    </Badge>
  );
}

/**
 * Smart Back Button Component
 */
function SmartBackButton({ drillDown }: { drillDown: DrillDownState | null }) {
  const { goBack } = useDrillDown();
  
  if (!drillDown) {
    return (
      <Button
        variant="light"
        leftSection={<IconArrowLeft size={18} />}
        onClick={() => window.history.back()}
      >
        Back
      </Button>
    );
  }
  
  const sourceLabels: Record<string, string> = {
    recommendations: 'Recommendations',
    forecasts: 'Forecasts',
    intelligence: 'Intelligence Dashboard',
    correlations: 'Correlations',
    news: 'News',
    opportunities: 'Opportunities',
    risks: 'Risks',
    dashboard: 'Dashboard',
    unknown: 'Previous Page',
  };
  
  const sourceLabel = sourceLabels[drillDown.source] || 'Back';
  
  return (
    <Button
      variant="light"
      leftSection={<IconArrowLeft size={18} />}
      onClick={goBack}
    >
      Back to {sourceLabel}
    </Button>
  );
}

/**
 * Ticker Overview Tab
 */
function OverviewTab({ ticker }: { ticker: string }) {
  const { data: forecasts, isLoading, error } = useForecasts();
  
  // Filter forecasts for this ticker
  const tickerForecasts = forecasts?.rows?.filter((f: any) => f.ticker === ticker) || [];
  
  if (isLoading) {
    return <Text c="dimmed">Loading forecasts...</Text>;
  }
  
  if (error) {
    return (
      <Alert color="red" title="Error loading forecasts">
        {error instanceof Error ? error.message : 'Failed to load forecasts'}
      </Alert>
    );
  }
  
  if (tickerForecasts.length === 0) {
    return (
      <Alert color="blue" title="No forecasts available">
        No forecast data available for {ticker} at the moment.
      </Alert>
    );
  }
  
  return (
    <Stack gap="md">
      <Title order={3}>Forecasts for {ticker}</Title>
      <Grid>
        {tickerForecasts.map((forecast: any, index: number) => (
          <Grid.Col key={index} span={{ base: 12, md: 6 }}>
            <Card withBorder padding="md">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text fw={600}>{forecast.horizon || 'Short-term'}</Text>
                  <Badge color={forecast.direction === 'up' ? 'green' : forecast.direction === 'down' ? 'red' : 'gray'}>
                    {forecast.direction}
                  </Badge>
                </Group>
                <Text size="sm" c="dimmed">
                  Confidence: {((forecast.confidence || 0) * 100).toFixed(0)}%
                </Text>
                {forecast.expected_return && (
                  <Text size="sm">
                    Expected return: {(forecast.expected_return * 100).toFixed(2)}%
                  </Text>
                )}
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>
    </Stack>
  );
}

/**
 * Ticker News Tab (placeholder)
 */
function NewsTab({ ticker }: { ticker: string }) {
  return (
    <Alert color="blue" icon={<IconNews size={20} />}>
      <Text size="sm">
        News feed for {ticker} coming soon.
      </Text>
    </Alert>
  );
}

/**
 * Ticker Correlations Tab (placeholder)
 */
function CorrelationsTab({ ticker }: { ticker: string }) {
  return (
    <Alert color="blue" icon={<IconNetwork size={20} />}>
      <Text size="sm">
        Correlation analysis for {ticker} coming soon.
      </Text>
    </Alert>
  );
}

/**
 * Ticker Detail Page (Main Component)
 */
export default function TickerDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const location = useLocation();
  const { currentDrillDown } = useDrillDown();
  
  // Get drill-down state from location or context
  const drillDown = (location.state as DrillDownState) || currentDrillDown;
  
  if (!ticker) {
    return (
      <Alert color="red" title="Invalid ticker">
        No ticker specified in URL.
      </Alert>
    );
  }
  
  return (
    <Stack gap="lg" data-testid="ticker-detail-page">
      {/* Breadcrumb Navigation */}
      <ContextBreadcrumb ticker={ticker} drillDown={drillDown} />
      
      {/* Header */}
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <Stack gap="xs">
          <Group gap="md" align="center">
            <Title order={1}>{ticker}</Title>
            <ContextBadge drillDown={drillDown} />
          </Group>
          <Text c="dimmed" size="sm">
            Comprehensive ticker analysis and details
          </Text>
        </Stack>
        
        <SmartBackButton drillDown={drillDown} />
      </Group>
      
      {/* Context Alert (if reason provided) */}
      {drillDown?.reason && (
        <Alert color="blue" variant="light" icon={<IconSparkles size={20} />}>
          <Text size="sm" fw={500}>
            {drillDown.reason}
          </Text>
        </Alert>
      )}
      
      {/* Tabs */}
      <Tabs defaultValue="overview" variant="outline">
        <Tabs.List>
          <Tabs.Tab value="overview" leftSection={<IconChartLine size={18} />}>
            Overview
          </Tabs.Tab>
          <Tabs.Tab value="news" leftSection={<IconNews size={18} />}>
            News
          </Tabs.Tab>
          <Tabs.Tab value="correlations" leftSection={<IconNetwork size={18} />}>
            Correlations
          </Tabs.Tab>
        </Tabs.List>
        
        <Tabs.Panel value="overview" pt="md">
          <OverviewTab ticker={ticker} />
        </Tabs.Panel>
        
        <Tabs.Panel value="news" pt="md">
          <NewsTab ticker={ticker} />
        </Tabs.Panel>
        
        <Tabs.Panel value="correlations" pt="md">
          <CorrelationsTab ticker={ticker} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
