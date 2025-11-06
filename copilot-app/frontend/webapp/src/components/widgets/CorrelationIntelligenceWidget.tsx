/**
 * Correlation Intelligence Widget
 * 
 * Displays correlation analysis with LLM explanations:
 * - Correlation matrix (heatmap)
 * - Top correlation pairs
 * - Actionable insights
 * - Market context
 * 
 * Author: ELENA-39
 * Task: FC-INT-025
 */

import { Stack, Text, Group, Alert, Badge, Card, Grid, ActionIcon, Skeleton, Divider, List } from '@mantine/core';
import { IconRefresh, IconAlertCircle, IconLoader, IconChartDots, IconArrowsMaximize, IconArrowsMinimize, IconShieldCheck, IconEye } from '@tabler/icons-react';
import { useCorrelationIntelligence, type CorrelationPair } from '../../hooks/useCorrelationIntelligence';

interface CorrelationIntelligenceWidgetProps {
  universe?: string[];
  window?: string;
  threshold?: number;
}

/**
 * Correlation Matrix Heatmap Component
 */
function CorrelationMatrixHeatmap({ 
  matrix, 
  tickers 
}: { 
  matrix: number[][], 
  tickers: string[] 
}) {
  const getColorForCorr = (corr: number): string => {
    const absCorr = Math.abs(corr);
    if (absCorr >= 0.9) return corr > 0 ? '#1e40af' : '#991b1b';
    if (absCorr >= 0.7) return corr > 0 ? '#3b82f6' : '#dc2626';
    if (absCorr >= 0.5) return corr > 0 ? '#60a5fa' : '#ef4444';
    return '#94a3b8';
  };

  return (
    <Card withBorder padding="md">
      <Stack gap="xs">
        <Group gap="xs">
          <IconChartDots size={20} color="#4169E1" />
          <Text size="sm" fw={600}>Correlation Matrix</Text>
          <Badge size="xs" variant="light">
            {tickers.length}x{tickers.length}
          </Badge>
        </Group>

        {/* Simplified heatmap visualization */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: `60px repeat(${tickers.length}, 1fr)`,
          gap: '2px',
          fontSize: '11px'
        }}>
          {/* Header row */}
          <div></div>
          {tickers.map((ticker) => (
            <div key={ticker} style={{ 
              textAlign: 'center', 
              fontWeight: 600,
              fontSize: '10px',
              padding: '2px'
            }}>
              {ticker}
            </div>
          ))}

          {/* Matrix rows */}
          {matrix.map((row, i) => (
            <>
              <div key={`label-${i}`} style={{ 
                textAlign: 'right', 
                fontWeight: 600,
                padding: '2px 4px',
                fontSize: '10px'
              }}>
                {tickers[i]}
              </div>
              {row.map((corr, j) => (
                <div
                  key={`cell-${i}-${j}`}
                  style={{
                    backgroundColor: getColorForCorr(corr),
                    color: Math.abs(corr) > 0.6 ? 'white' : '#1e293b',
                    textAlign: 'center',
                    padding: '4px 2px',
                    borderRadius: '2px',
                    fontWeight: i === j ? 700 : 400,
                    fontSize: i === j ? '10px' : '9px'
                  }}
                  title={`${tickers[i]} vs ${tickers[j]}: ${corr.toFixed(2)}`}
                >
                  {corr.toFixed(2)}
                </div>
              ))}
            </>
          ))}
        </div>

        {/* Legend */}
        <Group gap="xs" justify="center" mt="xs">
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{ width: 12, height: 12, backgroundColor: '#1e40af', borderRadius: 2 }} />
            <Text size="xs" c="dimmed">Strong +</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{ width: 12, height: 12, backgroundColor: '#60a5fa', borderRadius: 2 }} />
            <Text size="xs" c="dimmed">Moderate +</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{ width: 12, height: 12, backgroundColor: '#ef4444', borderRadius: 2 }} />
            <Text size="xs" c="dimmed">Negative</Text>
          </div>
        </Group>
      </Stack>
    </Card>
  );
}

/**
 * Correlation Pair Card Component
 */
function CorrelationPairCard({ pair }: { pair: CorrelationPair }) {
  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'DIVERSIFY': return IconArrowsMaximize;
      case 'HEDGE': return IconShieldCheck;
      case 'ARBITRAGE': return IconArrowsMinimize;
      case 'MONITOR': return IconEye;
      default: return IconEye;
    }
  };

  const getActionColor = (actionType: string): string => {
    switch (actionType) {
      case 'DIVERSIFY': return 'orange';
      case 'HEDGE': return 'green';
      case 'ARBITRAGE': return 'violet';
      case 'MONITOR': return 'blue';
      default: return 'gray';
    }
  };

  const ActionIconComponent = getActionIcon(pair.action_type);

  return (
    <Card withBorder padding="md" radius="md" style={{ height: '100%' }}>
      <Stack gap="xs">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <Group gap="xs">
            <Text size="md" fw={700}>{pair.ticker1}</Text>
            <Text size="sm" c="dimmed">↔</Text>
            <Text size="md" fw={700}>{pair.ticker2}</Text>
          </Group>
          <Badge
            color={pair.direction === 'positive' ? 'blue' : 'red'}
            variant="light"
            size="lg"
          >
            {pair.correlation > 0 ? '+' : ''}{pair.correlation.toFixed(2)}
          </Badge>
        </Group>

        <Badge 
          color={pair.strength === 'strong' ? 'indigo' : 'gray'} 
          variant="dot" 
          size="sm"
        >
          {pair.strength} {pair.direction}
        </Badge>

        <Divider />

        {/* Explanation */}
        <Text size="sm" c="dimmed">
          {pair.explanation}
        </Text>

        {/* Drivers */}
        <Stack gap={4}>
          <Text size="xs" fw={600} c="dimmed">Key Drivers:</Text>
          <Group gap="xs">
            {pair.drivers.map((driver, idx) => (
              <Badge key={idx} size="xs" variant="light" color="gray">
                {driver}
              </Badge>
            ))}
          </Group>
        </Stack>

        <Divider />

        {/* Action */}
        <Card withBorder padding="xs" radius="sm" style={{ backgroundColor: '#f8fafc' }}>
          <Group gap="xs">
            <ActionIconComponent size={18} color={getActionColor(pair.action_type)} />
            <div style={{ flex: 1 }}>
              <Text size="xs" fw={600} c={getActionColor(pair.action_type)}>
                {pair.action_type}
              </Text>
              <Text size="xs" c="dimmed" lineClamp={2}>
                {pair.action_description}
              </Text>
            </div>
          </Group>
        </Card>

        {/* Implications */}
        {pair.implications && pair.implications.length > 0 && (
          <Stack gap={2}>
            <Text size="xs" fw={600} c="dimmed">Implications:</Text>
            <List size="xs" spacing={2} withPadding>
              {pair.implications.slice(0, 2).map((impl, idx) => (
                <List.Item key={idx}>
                  <Text size="xs" c="dimmed">{impl}</Text>
                </List.Item>
              ))}
            </List>
          </Stack>
        )}
      </Stack>
    </Card>
  );
}

/**
 * Main Correlation Intelligence Widget
 */
export function CorrelationIntelligenceWidget({
  universe,
  window = '30d',
  threshold = 0.7
}: CorrelationIntelligenceWidgetProps) {
  const { data, isLoading, error, refetch, isFetching } = useCorrelationIntelligence({
    universe,
    window,
    threshold
  });

  // Loading state
  if (isLoading) {
    return (
      <Stack gap="md">
        <Group justify="space-between">
          <Skeleton height={30} width={200} />
          <Skeleton height={30} width={100} />
        </Group>
        <Skeleton height={300} />
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Skeleton height={250} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Skeleton height={250} />
          </Grid.Col>
        </Grid>
      </Stack>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert color="red" icon={<IconAlertCircle size={20} />} title="Error loading correlations">
        <Text size="sm">
          {error instanceof Error ? error.message : 'Failed to load correlation intelligence'}
        </Text>
      </Alert>
    );
  }

  // Empty state
  if (!data || !data.interesting_pairs || data.interesting_pairs.length === 0) {
    return (
      <Alert color="blue" icon={<IconAlertCircle size={20} />} title="No strong correlations detected">
        <Text size="sm">
          No significant correlations found above threshold {threshold}. Try lowering the threshold or expanding the universe.
        </Text>
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      {/* Header */}
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <IconChartDots size={28} color="#4169E1" />
          <Text size="xl" fw={700}>Correlation Intelligence</Text>
          <Badge variant="light" color="blue">
            {data.tickers.length} assets
          </Badge>
          <Badge variant="light" color="indigo">
            {data.interesting_pairs.length} pairs
          </Badge>
        </Group>
        <ActionIcon
          variant="light"
          onClick={() => refetch()}
          loading={isFetching}
          aria-label="Refresh correlations"
        >
          {isFetching ? <IconLoader size={18} /> : <IconRefresh size={18} />}
        </ActionIcon>
      </Group>

      {/* Market Context */}
      <Group gap="xs">
        <Badge color="violet" variant="light">
          {data.market_context?.regime || 'Unknown Regime'}
        </Badge>
        <Text size="xs" c="dimmed">
          Window: {window} | Threshold: {threshold}
        </Text>
      </Group>

      {/* Summary */}
      <Alert color="blue" variant="light" styles={{ root: { borderLeft: '4px solid #4169E1' } }}>
        <Text size="sm" fw={500}>
          {data.summary}
        </Text>
      </Alert>

      {/* Correlation Matrix */}
      <CorrelationMatrixHeatmap matrix={data.matrix} tickers={data.tickers} />

      {/* Interesting Pairs */}
      <Stack gap="xs">
        <Text size="lg" fw={600}>Top Correlation Pairs</Text>
        <Grid>
          {data.interesting_pairs.map((pair, index) => (
            <Grid.Col key={`${pair.ticker1}-${pair.ticker2}-${index}`} span={{ base: 12, md: 6 }}>
              <CorrelationPairCard pair={pair} />
            </Grid.Col>
          ))}
        </Grid>
      </Stack>

      {/* Footer */}
      <Text size="xs" c="dimmed" ta="center">
        🧠 Powered by ML correlation analysis + LLM explanations | Last updated:{' '}
        {new Date(data.generated_at).toLocaleString()}
      </Text>
    </Stack>
  );
}
