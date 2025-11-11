/**
 * TimelineEvents - Timeline avec événements de marché
 * Earnings, annonces, événements macro, etc.
 */

import { Card, Stack, Title, Text, Group, Badge, Timeline as MantineTimeline } from '@mantine/core';
import { IconCircle, IconTrendingUp, IconTrendingDown, IconAlertCircle } from '@tabler/icons-react';

interface TimelineEvent {
  date: string;
  title: string;
  description?: string;
  type: 'earnings' | 'announcement' | 'macro' | 'news' | 'alert';
  impact?: 'positive' | 'negative' | 'neutral';
  ticker?: string;
}

interface TimelineEventsProps {
  /** Titre */
  title?: string;
  /** Description */
  description?: string;
  /** Événements */
  events: TimelineEvent[];
}

export function TimelineEvents({
  title = 'Timeline Événements',
  description,
  events,
}: TimelineEventsProps) {
  const getIcon = (type: TimelineEvent['type'], impact?: string) => {
    if (impact === 'positive') return <IconTrendingUp size={16} />;
    if (impact === 'negative') return <IconTrendingDown size={16} />;
    if (type === 'alert') return <IconAlertCircle size={16} />;
    return <IconCircle size={16} />;
  };

  const getColor = (type: TimelineEvent['type'], impact?: string) => {
    if (impact === 'positive') return 'teal';
    if (impact === 'negative') return 'red';
    if (type === 'alert') return 'orange';
    if (type === 'earnings') return 'blue';
    if (type === 'macro') return 'indigo';
    return 'gray';
  };

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <MantineTimeline active={-1} bulletSize={24} lineWidth={2}>
          {events.map((event, index) => (
            <MantineTimeline.Item
              key={index}
              bullet={getIcon(event.type, event.impact)}
              title={
                <Group gap="xs" align="center">
                  <Text fw={600} size="sm">{event.title}</Text>
                  {event.ticker && (
                    <Badge size="xs" variant="light">
                      {event.ticker}
                    </Badge>
                  )}
                  <Badge
                    size="xs"
                    color={getColor(event.type, event.impact)}
                    variant="light"
                  >
                    {event.type}
                  </Badge>
                </Group>
              }
            >
              <Text size="xs" c="dimmed" mt={4}>
                {new Date(event.date).toLocaleDateString('fr-FR', {
                  day: 'numeric',
                  month: 'short',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </Text>
              {event.description && (
                <Text size="sm" mt={4}>
                  {event.description}
                </Text>
              )}
            </MantineTimeline.Item>
          ))}
        </MantineTimeline>
      </Stack>
    </Card>
  );
}

