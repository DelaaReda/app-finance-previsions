import { Card, Text, Stack, Alert, Badge, Group } from '@mantine/core';
import {
  IconAlertTriangle,
  IconChartLine,
  IconMoodSad,
  IconNews,
  IconChartBar,
} from '@tabler/icons-react';
import type { IntelligenceSnapshot } from '../../hooks/useIntelligence';

interface RisksPanelProps {
  risks: IntelligenceSnapshot['insights']['risks'];
}

interface RiskAlertProps {
  type: string;
  description: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
}

/**
 * Get icon for risk type
 */
function getRiskIcon(type: string) {
  const iconMap: Record<string, any> = {
    VOLATILITY: IconChartLine,
    SENTIMENT: IconMoodSad,
    NEWS: IconNews,
    MACRO: IconChartBar,
    SYSTEM: IconAlertTriangle,
  };
  const Icon = iconMap[type.toUpperCase()] || IconAlertTriangle;
  return <Icon size={20} />;
}

/**
 * Get color for severity
 */
function getSeverityColor(severity: 'HIGH' | 'MEDIUM' | 'LOW'): string {
  const colorMap = {
    HIGH: 'red',
    MEDIUM: 'yellow',
    LOW: 'blue',
  };
  return colorMap[severity] || 'gray';
}

/**
 * Single Risk Alert
 */
function RiskAlert({ type, description, severity }: RiskAlertProps) {
  const color = getSeverityColor(severity);
  const icon = getRiskIcon(type);

  return (
    <Alert
      icon={icon}
      title={
        <Group gap="xs">
          <Text fw={600}>{type}</Text>
          <Badge color={color} size="sm" variant="filled">
            {severity}
          </Badge>
        </Group>
      }
      color={color}
      variant="light"
    >
      <Text size="sm">{description}</Text>
    </Alert>
  );
}

/**
 * RisksPanel Component
 * 
 * Displays key risks identified by the system
 * - Risk type with icon
 * - Description
 * - Severity badge (HIGH/MEDIUM/LOW)
 * 
 * @param risks - Array of risk objects
 */
export function RisksPanel({ risks }: RisksPanelProps) {
  if (!risks || risks.length === 0) {
    return (
      <Card shadow="sm" padding="lg" radius="md" withBorder>
        <Text size="lg" fw={700} mb="md">
          ⚠️ Key Risks
        </Text>
        <Text size="sm" c="dimmed">
          No major risks detected at this time.
        </Text>
      </Card>
    );
  }

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text size="lg" fw={700} mb="md">
        ⚠️ Key Risks
      </Text>

      <Stack gap="md">
        {risks.map((risk, index) => (
          <RiskAlert
            key={`${risk.type}-${index}`}
            type={risk.type}
            description={risk.description}
            severity={risk.severity}
          />
        ))}
      </Stack>
    </Card>
  );
}
