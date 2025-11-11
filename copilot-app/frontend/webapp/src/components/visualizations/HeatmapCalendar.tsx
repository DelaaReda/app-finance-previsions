/**
 * HeatmapCalendar - Calendrier avec heatmap
 * Pour earnings, événements, volatilité, etc.
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo } from 'react';

interface CalendarEvent {
  date: string; // YYYY-MM-DD
  value: number; // 0-100 pour intensité
  label?: string;
  type?: 'earnings' | 'announcement' | 'volatility' | 'news';
  tickers?: string[];
}

interface HeatmapCalendarProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Événements */
  events: CalendarEvent[];
  /** Mois à afficher */
  month?: number; // 0-11
  /** Année */
  year?: number;
}

export function HeatmapCalendar({
  title,
  description,
  events,
  month = new Date().getMonth(),
  year = new Date().getFullYear(),
}: HeatmapCalendarProps) {
  const calendarData = useMemo(() => {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - startDate.getDay()); // Start on Sunday
    
    const days: Array<{ date: Date; event?: CalendarEvent }> = [];
    const current = new Date(startDate);
    
    // 6 weeks max
    for (let i = 0; i < 42; i++) {
      const dateStr = current.toISOString().split('T')[0];
      const event = events.find(e => e.date === dateStr);
      days.push({ date: new Date(current), event });
      current.setDate(current.getDate() + 1);
    }
    
    return days;
  }, [events, month, year]);

  const getColor = (value?: number) => {
    if (!value) return 'var(--mantine-color-gray-8)';
    if (value < 25) return '#10b981'; // Teal light
    if (value < 50) return '#3b82f6'; // Blue
    if (value < 75) return '#f59e0b'; // Orange
    return '#ef4444'; // Red
  };

  const getIntensity = (value?: number) => {
    if (!value) return 0.3;
    return Math.max(0.4, value / 100);
  };

  const monthNames = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
  const dayNames = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
          <Badge variant="light" mt={4}>
            {monthNames[month]} {year}
          </Badge>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
          {/* Day headers */}
          {dayNames.map(day => (
            <div key={day} style={{ textAlign: 'center', padding: '8px 4px' }}>
              <Text size="xs" c="dimmed" fw={600}>{day}</Text>
            </div>
          ))}
          
          {/* Calendar days */}
          {calendarData.map((day, index) => {
            const isCurrentMonth = day.date.getMonth() === month;
            const event = day.event;
            const color = getColor(event?.value);
            const intensity = getIntensity(event?.value);
            
            return (
              <Tooltip
                key={index}
                label={
                  event ? (
                    <div>
                      <Text size="sm" fw={600}>{day.date.toLocaleDateString('fr-FR')}</Text>
                      {event.label && <Text size="xs">{event.label}</Text>}
                      <Text size="xs">Intensité: {event.value}%</Text>
                      {event.tickers && event.tickers.length > 0 && (
                        <Text size="xs" c="dimmed">
                          {event.tickers.join(', ')}
                        </Text>
                      )}
                    </div>
                  ) : (
                    <Text size="xs">{day.date.toLocaleDateString('fr-FR')}</Text>
                  )
                }
                withArrow
                disabled={!event}
              >
                <div
                  style={{
                    aspectRatio: '1',
                    backgroundColor: color,
                    opacity: intensity,
                    borderRadius: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: event ? 'pointer' : 'default',
                    border: isCurrentMonth ? '1px solid var(--mantine-color-gray-6)' : '1px solid transparent',
                    minHeight: '32px',
                  }}
                  onMouseEnter={(e) => {
                    if (event) {
                      e.currentTarget.style.transform = 'scale(1.1)';
                      e.currentTarget.style.zIndex = '10';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (event) {
                      e.currentTarget.style.transform = 'scale(1)';
                      e.currentTarget.style.zIndex = '1';
                    }
                  }}
                >
                  {isCurrentMonth && (
                    <Text size="xs" c={event ? 'white' : 'dimmed'} fw={event ? 700 : 400}>
                      {day.date.getDate()}
                    </Text>
                  )}
                </div>
              </Tooltip>
            );
          })}
        </div>
        
        {/* Legend */}
        <Group gap="lg" mt="md">
          <Group gap="xs">
            <div style={{ width: 16, height: 16, backgroundColor: '#10b981', borderRadius: '4px', opacity: 0.6 }}></div>
            <Text size="xs">Faible (0-25%)</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 16, height: 16, backgroundColor: '#3b82f6', borderRadius: '4px', opacity: 0.7 }}></div>
            <Text size="xs">Moyen (25-50%)</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 16, height: 16, backgroundColor: '#f59e0b', borderRadius: '4px', opacity: 0.8 }}></div>
            <Text size="xs">Élevé (50-75%)</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 16, height: 16, backgroundColor: '#ef4444', borderRadius: '4px', opacity: 0.9 }}></div>
            <Text size="xs">Très élevé (75-100%)</Text>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}

