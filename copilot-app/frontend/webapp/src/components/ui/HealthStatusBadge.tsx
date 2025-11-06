import { Badge, LoadingSpinner, Tooltip } from '@/ui';
import { useLegacyHealth } from '@/hooks/useHealth';

export function HealthStatusBadge() {
  const { health, loading, error, lastChecked } = useLegacyHealth();

  if (loading) {
    return <LoadingSpinner size="sm" />;
  }

  if (error || !health) {
    return (
      <Tooltip label={error ?? 'Health data unavailable'}>
        <Badge color="red" variant="light">Erreur</Badge>
      </Tooltip>
    );
  }

  const status = health.status ?? (health.backend_up ? 'up' : 'degraded');
  const labelMap: Record<string, string> = {
    up: 'Healthy',
    degraded: 'Dégradé',
    down: 'Down',
  };
  const colorMap: Record<string, string> = {
    up: 'teal',
    degraded: 'orange',
    down: 'red',
  };

  const label = labelMap[status] ?? 'Unknown';
  const color = colorMap[status] ?? 'gray';

  const titleParts: string[] = [`Status: ${label}`];
  if (health.timestamp) {
    titleParts.push(`Mise à jour: ${new Date(health.timestamp).toLocaleString('fr-FR')}`);
  } else if (lastChecked) {
    titleParts.push(`Vérifié: ${new Date(lastChecked).toLocaleString('fr-FR')}`);
  }
  if (health.message) {
    titleParts.push(`Note: ${health.message}`);
  }

  return (
    <Tooltip label={titleParts.join('\n')} position="bottom">
      <Badge color={color} variant="light">
        {label}
      </Badge>
    </Tooltip>
  );
}
