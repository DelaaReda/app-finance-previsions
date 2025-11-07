/**
 * EmptyState - Composant réutilisable pour états vides
 * Design professionnel avec icône, message et CTA
 */

import { Card, Stack, Text, Title, Button, Group } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  /** Icône à afficher */
  icon?: ReactNode;
  /** Titre principal */
  title: string;
  /** Description */
  description?: string;
  /** Action principale (bouton) */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Actions secondaires */
  secondaryActions?: Array<{
    label: string;
    onClick: () => void;
  }>;
}

export default function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryActions,
}: EmptyStateProps) {
  return (
    <Card padding="xl" radius="md" withBorder>
      <Stack gap="md" align="center" py="xl">
        {icon && <div>{icon}</div>}
        <div style={{ textAlign: 'center' }}>
          <Title order={4} mb="xs">{title}</Title>
          {description && (
            <Text c="dimmed" size="sm" ta="center">
              {description}
            </Text>
          )}
        </div>
        {(action || secondaryActions) && (
          <Group gap="sm" mt="md">
            {action && (
              <Button
                variant="light"
                onClick={action.onClick}
                leftSection={<IconRefresh size={16} />}
              >
                {action.label}
              </Button>
            )}
            {secondaryActions?.map((secondary, index) => (
              <Button
                key={index}
                variant="subtle"
                onClick={secondary.onClick}
              >
                {secondary.label}
              </Button>
            ))}
          </Group>
        )}
      </Stack>
    </Card>
  );
}
