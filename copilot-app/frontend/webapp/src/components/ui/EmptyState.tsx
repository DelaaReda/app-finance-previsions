import { ReactNode } from 'react';
import { Badge, Button, Card, Chip, Heading, Stack, Text } from '@/ui';
import { IconCalendar, IconFileText, IconRefresh } from '@tabler/icons-react';

interface EmptyStateProps {
  title?: string;
  subtitle?: string;
  hint?: string;
  type?: 'data' | 'search' | 'filter' | 'initial';
  action?: {
    label: string;
    onClick: () => void;
  };
  showIcon?: boolean;
  dataTestId?: string;
}

const ICONS: Record<string, ReactNode> = {
  data: <IconFileText size={44} />,
  search: <IconFileText size={44} />,
  filter: <IconCalendar size={44} />,
  initial: <IconRefresh size={44} />,
};

export default function EmptyState({
  title = 'Aucune donnée disponible',
  subtitle,
  hint,
  type = 'data',
  action,
  showIcon = true,
  dataTestId = 'empty-state',
}: EmptyStateProps) {
  return (
    <Card data-testid={dataTestId} padding="xl" radius="lg" shadow="sm">
      <Stack gap="sm" align="center">
        {showIcon && <Chip size="lg" radius="md" variant="light">{ICONS[type] ?? ICONS.data}</Chip>}
        <Heading order={4}>{title}</Heading>
        {subtitle && <Text c="dimmed" ta="center">{subtitle}</Text>}
        {hint && <Text fz="xs" c="slate.5" ta="center">{hint}</Text>}
        {action && (
          <Button variant="light" onClick={action.onClick}>
            {action.label}
          </Button>
        )}
        <Badge color="slate" variant="light">
          {type === 'data' && 'Données en cours de calcul'}
          {type === 'search' && 'Ajustez vos critères de recherche'}
          {type === 'filter' && 'Modifiez les filtres actifs'}
          {type === 'initial' && 'Chargement initial en cours'}
        </Badge>
      </Stack>
    </Card>
  );
}
