/**
 * PageHeader - Composant réutilisable pour headers de pages
 * Style professionnel cohérent avec Mantine
 */

import { Group, Stack, Title, Text, Badge, ActionIcon, Tooltip } from '@mantine/core';
import { IconRefresh, IconInfoCircle } from '@tabler/icons-react';
import type { ReactNode } from 'react';

interface PageHeaderProps {
  /** Titre principal de la page */
  title: string;
  /** Icône optionnelle (React component) */
  icon?: ReactNode;
  /** Description/sous-titre */
  description?: string;
  /** Badge optionnel (ex: "Live", "Beta") */
  badge?: {
    label: string;
    color?: string;
  };
  /** Statistiques à afficher */
  stats?: Array<{
    label: string;
    value: string | number;
  }>;
  /** Actions à droite (boutons, etc.) */
  actions?: ReactNode;
  /** Callback pour refresh */
  onRefresh?: () => void;
  /** Tooltip pour info */
  infoTooltip?: string;
}

export default function PageHeader({
  title,
  icon,
  description,
  badge,
  stats,
  actions,
  onRefresh,
  infoTooltip,
}: PageHeaderProps) {
  return (
    <Stack gap="xs" mb="xl">
      <Group justify="space-between" align="flex-start" wrap="wrap">
        <Group gap="md" align="center">
          {icon && <div>{icon}</div>}
          <div>
            <Group gap="sm" align="center" mb={4}>
              <Title order={2}>{title}</Title>
              {badge && (
                <Badge color={badge.color || 'blue'} variant="light" size="lg">
                  {badge.label}
                </Badge>
              )}
              {infoTooltip && (
                <Tooltip label={infoTooltip} withArrow>
                  <ActionIcon variant="subtle" size="sm" color="gray">
                    <IconInfoCircle size={16} />
                  </ActionIcon>
                </Tooltip>
              )}
            </Group>
            {description && (
              <Text c="dimmed" size="sm">
                {description}
              </Text>
            )}
          </div>
        </Group>

        <Group gap="md" align="center">
          {stats && stats.length > 0 && (
            <Group gap="lg">
              {stats.map((stat, index) => (
                <div key={index} style={{ textAlign: 'right' }}>
                  <Text size="xs" c="dimmed" fw={500}>
                    {stat.label}
                  </Text>
                  <Text size="lg" fw={700}>
                    {stat.value}
                  </Text>
                </div>
              ))}
            </Group>
          )}
          {onRefresh && (
            <Tooltip label="Rafraîchir">
              <ActionIcon variant="light" onClick={onRefresh} size="lg">
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
          )}
          {actions}
        </Group>
      </Group>
    </Stack>
  );
}

