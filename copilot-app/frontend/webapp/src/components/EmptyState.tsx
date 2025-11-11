import { IconInbox } from '@tabler/icons-react';
import { Card, Stack, Text, ThemeIcon } from '@/ui';

interface EmptyStateProps {
  title?: string;
  subtitle?: string;
}

export function EmptyState({
  title = 'Aucune donnée disponible',
  subtitle = 'Les données apparaîtront dès qu’elles seront prêtes.'
}: EmptyStateProps) {
  return (
    <Card radius="lg" padding="xl" shadow="sm" withBorder>
      <Stack align="center" gap="xs">
        <ThemeIcon size="lg" radius="xl" color="slate">
          <IconInbox size={18} />
        </ThemeIcon>
        <Text fw={600}>{title}</Text>
        {subtitle && (
          <Text c="dimmed" ta="center">
            {subtitle}
          </Text>
        )}
      </Stack>
    </Card>
  );
}
