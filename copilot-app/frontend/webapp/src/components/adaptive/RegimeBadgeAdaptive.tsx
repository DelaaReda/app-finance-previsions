/**
 * Regime Badge (Adaptive)
 * 
 * Displays current market regime with confidence and theme.
 * Provides quick visual feedback about market context.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 */

import { Badge, Group, Text, Tooltip, RingProgress } from '@mantine/core';
import { useAdaptiveLayout } from '../../contexts/AdaptiveLayoutContext';

export function RegimeBadgeAdaptive() {
  const { currentRegime, confidence, regimeTheme, layoutDescription } = useAdaptiveLayout();

  const confidencePercent = Math.round(confidence * 100);

  return (
    <Tooltip
      label={
        <div>
          <Text size="sm" fw={600}>
            {layoutDescription}
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            Confidence: {confidencePercent}%
          </Text>
        </div>
      }
      position="bottom"
      withArrow
    >
      <Badge
        size="lg"
        variant="light"
        color={regimeTheme.color}
        style={{
          cursor: 'pointer',
          borderLeft: `4px solid ${regimeTheme.accentColor}`,
        }}
      >
        <Group gap="xs">
          <Text size="sm">{regimeTheme.icon}</Text>
          <Text size="sm" fw={600}>
            {currentRegime.replace(/_/g, ' ')}
          </Text>
          <RingProgress
            size={20}
            thickness={3}
            sections={[{ value: confidencePercent, color: regimeTheme.color }]}
          />
        </Group>
      </Badge>
    </Tooltip>
  );
}
