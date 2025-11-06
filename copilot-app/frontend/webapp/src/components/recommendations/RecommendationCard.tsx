import { Card, Group, Stack, Text, Badge, Button, RingProgress, Tooltip } from '@mantine/core';
import { IconArrowRight, IconTrendingUp, IconTrendingDown, IconMinus } from '@tabler/icons-react';
import { useDrillDown } from '../../contexts/DrillDownContext';
import { useMarketContext } from '../../hooks/useMarketContext';
import type { Recommendation } from '../../hooks/useRecommendations';

interface RecommendationCardProps {
  recommendation: Recommendation;
}

/**
 * Get action icon
 */
function getActionIcon(action: string) {
  switch (action) {
    case 'BUY':
      return <IconTrendingUp size={20} />;
    case 'SELL':
      return <IconTrendingDown size={20} />;
    default:
      return <IconMinus size={20} />;
  }
}

/**
 * Get action color
 */
function getActionColor(action: string): string {
  switch (action) {
    case 'BUY':
      return 'green';
    case 'SELL':
      return 'red';
    default:
      return 'gray';
  }
}

/**
 * Get risk color
 */
function getRiskColor(risk: string): string {
  switch (risk) {
    case 'LOW':
      return 'green';
    case 'MEDIUM':
      return 'yellow';
    case 'HIGH':
      return 'red';
    default:
      return 'gray';
  }
}

/**
 * RecommendationCard Component
 * 
 * Displays a single recommendation with:
 * - Ticker and action
 * - Score visualization
 * - Reasoning
 * - Catalysts
 * - Risk level
 * - Navigation to ticker detail
 */
export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { navigateToTicker } = useDrillDown();
  const { data: marketContext } = useMarketContext();
  
  const scorePercent = Math.round(recommendation.score * 100);
  const confidencePercent = Math.round(recommendation.confidence * 100);
  
  const handleViewDetails = () => {
    navigateToTicker(recommendation.ticker, {
      source: 'recommendations',
      reason: recommendation.reasoning,
      regime: marketContext?.regime,
      additionalData: {
        score: recommendation.score,
        action: recommendation.action,
        catalysts: recommendation.catalysts,
      },
    });
  };
  
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md">
        {/* Header: Ticker + Action + Score */}
        <Group justify="space-between" align="flex-start">
          <Group>
            <Text size="xl" fw={700}>
              {recommendation.ticker}
            </Text>
            <Badge
              color={getActionColor(recommendation.action)}
              size="lg"
              variant="filled"
              leftSection={getActionIcon(recommendation.action)}
            >
              {recommendation.action}
            </Badge>
          </Group>
          
          <Tooltip label={`Confidence: ${confidencePercent}%`}>
            <RingProgress
              size={80}
              thickness={8}
              sections={[
                { value: scorePercent, color: scorePercent > 75 ? 'green' : scorePercent > 50 ? 'blue' : 'yellow' }
              ]}
              label={
                <Text size="sm" ta="center" fw={600}>
                  {scorePercent}%
                </Text>
              }
            />
          </Tooltip>
        </Group>
        
        {/* Risk Level */}
        <Group>
          <Text size="sm" c="dimmed">Risk:</Text>
          <Badge color={getRiskColor(recommendation.risk_level)} variant="light">
            {recommendation.risk_level}
          </Badge>
        </Group>
        
        {/* Reasoning */}
        <Text size="sm">
          {recommendation.reasoning}
        </Text>
        
        {/* Catalysts */}
        {recommendation.catalysts && recommendation.catalysts.length > 0 && (
          <Stack gap="xs">
            <Text size="sm" fw={600} c="dimmed">
              Key Catalysts:
            </Text>
            {recommendation.catalysts.slice(0, 3).map((catalyst, index) => (
              <Group key={index} gap="xs">
                <Text size="sm" c="dimmed">•</Text>
                <Text size="sm">{catalyst}</Text>
              </Group>
            ))}
          </Stack>
        )}
        
        {/* View Details Button */}
        <Button
          variant="light"
          fullWidth
          rightSection={<IconArrowRight size={16} />}
          onClick={handleViewDetails}
        >
          View Details
        </Button>
      </Stack>
    </Card>
  );
}
