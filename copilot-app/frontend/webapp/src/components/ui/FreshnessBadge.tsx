import { IconClock, IconAlertTriangle, IconCircleCheck, IconAlertCircle } from '@tabler/icons-react';
import { Badge, Group, Stack, Text, Tooltip } from '@/ui';
import { formatDistanceStrict } from 'date-fns';
import { fr } from 'date-fns/locale';
import { isValid } from 'date-fns';

export interface FreshnessBadgeProps {
  freshness?: string | number | null;
  maxAgeFreshMinutes?: number;
  maxAgeStaleMinutes?: number;
  dataTestId?: string;
  labelPrefix?: string;
  showDetailedTime?: boolean;
}

const toDateTime = (value?: string | number | null) => {
  if (!value) return null;
  if (typeof value === 'number') {
    // Assume Unix timestamp in seconds if it's a number
    if (value.toString().length === 10) {
      // Unix timestamp in seconds
      return new Date(value * 1000);
    } else {
      // Unix timestamp in milliseconds
      return new Date(value);
    }
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) || !isValid(date) ? null : date;
};

const minutesDiff = (value?: string | number | null) => {
  const date = toDateTime(value);
  if (!date) return null;
  const diffMs = Date.now() - date.getTime();
  return Math.round(diffMs / 60000);
};

function FreshnessBadge({
  freshness,
  maxAgeFreshMinutes = 60,   // Fresh if < 1 hour
  maxAgeStaleMinutes = 360, // Stale if > 6 hours (360 mins)
  dataTestId = 'freshness-badge',
  labelPrefix = 'Mis à jour',
  showDetailedTime = true,
}: FreshnessBadgeProps) {
  const diffMinutes = minutesDiff(freshness);

  if (!freshness || diffMinutes === null) {
    return (
      <Badge data-testid={dataTestId} color="gray" variant="light">
        <Group gap="xs">
          <IconClock size={14} />
          <Text fz="xs" fw={600}>Données indisponibles</Text>
        </Group>
      </Badge>
    );
  }

  const isFresh = diffMinutes <= maxAgeFreshMinutes;
  const isStale = diffMinutes > maxAgeStaleMinutes;
  const isOld = diffMinutes > maxAgeFreshMinutes && diffMinutes <= maxAgeStaleMinutes;

  let color = 'teal';
  let icon = <IconCircleCheck size={14} />;
  let statusLabel = 'Fraîche';

  if (isFresh) {
    color = 'teal';
    icon = <IconCircleCheck size={14} />;
    statusLabel = 'Fraîches';
  } else if (isOld) {
    color = 'orange';
    icon = <IconAlertTriangle size={14} />;
    statusLabel = 'Anciennes';
  } else { // isStale
    color = 'red';
    icon = <IconAlertCircle size={14} />;
    statusLabel = 'Périmées';
  }

  // Format as "Il y a X min/heure/jour"
  const timeAgo = formatDistanceStrict(
    toDateTime(freshness)!,
    new Date(),
    { addSuffix: true, locale: fr }
  );

  const detailedTime = showDetailedTime 
    ? new Date(freshness).toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    : '';

  return (
    <Tooltip label={detailedTime || "Donnée sans horodatage"}>
      <Badge data-testid={dataTestId} color={color} variant="light" style={{ cursor: 'help' }}>
        <Group gap="xs">
          {icon}
          <Stack gap={0}>
            <Text fz="xs" fw={600}>{timeAgo}</Text>
            <Text fz="10px" c="dimmed">{statusLabel} • {diffMinutes} min</Text>
          </Stack>
        </Group>
      </Badge>
    </Tooltip>
  );
}

// Named and default export for compatibility
export { FreshnessBadge };
export default FreshnessBadge;