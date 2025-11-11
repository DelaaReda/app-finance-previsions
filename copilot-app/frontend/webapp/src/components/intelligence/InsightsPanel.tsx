import { Card, Text, Divider, Stack } from '@mantine/core';
import type { IntelligenceSnapshot } from '../../hooks/useIntelligence';

interface InsightsPanelProps {
  insights: IntelligenceSnapshot['insights'];
}

/**
 * InsightsPanel Component
 * 
 * Displays LLM-generated market intelligence insights
 * - Summary of market conditions
 * - Market regime explanation
 * - Contextual analysis
 * 
 * @param insights - Intelligence insights object
 */
export function InsightsPanel({ insights }: InsightsPanelProps) {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Text size="lg" fw={700}>
          📊 Market Intelligence
        </Text>

        <Text size="md" c="dark">
          {insights.summary}
        </Text>

        <Divider />

        <Stack gap="xs">
          <Text size="sm" fw={600} c="dimmed">
            Market Regime Analysis
          </Text>
          <Text size="sm" c="dimmed">
            {insights.market_regime.explanation}
          </Text>
        </Stack>
      </Stack>
    </Card>
  );
}
