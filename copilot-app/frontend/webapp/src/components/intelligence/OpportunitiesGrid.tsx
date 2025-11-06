import { Card, Text, Grid, Stack, Group, RingProgress, Badge, Anchor } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import type { IntelligenceSnapshot } from '../../hooks/useIntelligence';

interface OpportunitiesGridProps {
  opportunities: IntelligenceSnapshot['insights']['opportunities'];
}

interface OpportunityCardProps {
  ticker: string;
  reasoning: string;
  confidence: number;
}

/**
 * Single Opportunity Card
 */
function OpportunityCard({ ticker, reasoning, confidence }: OpportunityCardProps) {
  const navigate = useNavigate();
  const confidencePercent = Math.round(confidence * 100);

  // Color based on confidence
  const getConfidenceColor = (conf: number): string => {
    if (conf >= 0.75) return 'green';
    if (conf >= 0.5) return 'blue';
    return 'yellow';
  };

  return (
    <Card shadow="sm" padding="md" radius="md" withBorder>
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start">
          <Anchor
            component="button"
            onClick={() => navigate(`/ticker/${ticker}`)}
            size="lg"
            fw={700}
          >
            {ticker}
          </Anchor>

          <RingProgress
            size={60}
            thickness={6}
            sections={[{ value: confidencePercent, color: getConfidenceColor(confidence) }]}
            label={
              <Text size="xs" ta="center" fw={600}>
                {confidencePercent}%
              </Text>
            }
          />
        </Group>

        <Text size="sm" c="dimmed">
          {reasoning}
        </Text>

        <Badge color={getConfidenceColor(confidence)} variant="light" size="sm">
          {confidence >= 0.75 ? 'High' : confidence >= 0.5 ? 'Medium' : 'Low'} Confidence
        </Badge>
      </Stack>
    </Card>
  );
}

/**
 * OpportunitiesGrid Component
 * 
 * Displays top opportunities identified by LLM
 * - Ticker with link to detail page
 * - LLM reasoning
 * - Confidence visualization
 * 
 * @param opportunities - Array of opportunity objects
 */
export function OpportunitiesGrid({ opportunities }: OpportunitiesGridProps) {
  if (!opportunities || opportunities.length === 0) {
    return (
      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Text size="lg" fw={700} mb="md">
          🚀 Top Opportunities
        </Text>
        <Text size="sm" c="dimmed">
          No opportunities identified at this time.
        </Text>
      </Card>
    );
  }

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text size="lg" fw={700} mb="md">
        🚀 Top Opportunities
      </Text>

      <Grid gutter="md">
        {opportunities.slice(0, 3).map((opp, index) => (
          <Grid.Col key={`${opp.ticker}-${index}`} span={{ base: 12, sm: 6, md: 4 }}>
            <OpportunityCard
              ticker={opp.ticker}
              reasoning={opp.reasoning}
              confidence={opp.confidence}
            />
          </Grid.Col>
        ))}
      </Grid>
    </Card>
  );
}
