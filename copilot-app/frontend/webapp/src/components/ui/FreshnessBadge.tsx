import { IconClock, IconExclamationMark, IconCheck } from '@tabler/icons-react';
import { Badge, Group, Stack, Text } from '@/ui';

export interface FreshnessBadgeProps {
  freshness?: string | null;
  maxAgeHours?: number;
  maxAgeCriticalHours?: number;
  dataTestId?: string;
  labelPrefix?: string;
}

const toDate = (value?: string | null) => {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

const minutesDiff = (value?: string | null) => {
  const date = toDate(value);
  if (!date) return null;
  const diffMs = Date.now() - date.getTime();
  return Math.round(diffMs / 60000);
};

export default function FreshnessBadge({
  freshness,
  maxAgeHours = 24,
  maxAgeCriticalHours = 48,
  dataTestId = 'freshness-badge',
  labelPrefix = 'Mise à jour',
}: FreshnessBadgeProps) {
  const diffMinutes = minutesDiff(freshness);

  if (!freshness || diffMinutes === null) {
    return (
      <Badge data-testid={dataTestId} color="gray" variant="light">
        <Group gap="xs">
          <IconClock size={14} />
          <Text fz="xs">{labelPrefix}: inconnue</Text>
        </Group>
      </Badge>
    );
  }

  const hours = diffMinutes / 60;
  const isFresh = hours <= maxAgeHours;
  const isCritical = hours > maxAgeCriticalHours;

  let color = 'indigo';
  let icon = <IconClock size={14} />;
  let label = 'À jour';

  if (isFresh) {
    color = 'teal';
    icon = <IconCheck size={14} />;
    label = 'Fraîche';
  } else if (isCritical) {
    color = 'red';
    icon = <IconExclamationMark size={14} />;
    label = 'Critique';
  } else {
    color = 'orange';
    label = 'Ancienne';
  }

  const formattedDate = new Date(freshness).toLocaleString('fr-FR');

  return (
    <Badge data-testid={dataTestId} color={color} variant="light">
      <Group gap="xs">
        {icon}
        <Stack gap={0}>
          <Text fz="xs" fw={600}>{labelPrefix}: {formattedDate}</Text>
          <Text fz="10px" c="dimmed">{label} • {diffMinutes} min</Text>
        </Stack>
      </Group>
    </Badge>
  );
}
