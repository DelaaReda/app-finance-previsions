import { Stack, Title, Text, Card, Grid, Badge, Group, Loader, Alert } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconClock } from '@tabler/icons-react';

export default function ForecastsSimple() {
  // Mock data pour démo
  const mockForecasts = [
    { ticker: 'AAPL', direction: 'up', score: 8.2, horizon: 'short', confidence: 85 },
    { ticker: 'MSFT', direction: 'up', score: 7.9, horizon: 'medium', confidence: 78 },
    { ticker: 'GOOGL', direction: 'down', score: 6.1, horizon: 'long', confidence: 72 },
    { ticker: 'TSLA', direction: 'up', score: 7.5, horizon: 'short', confidence: 80 },
    { ticker: 'NVDA', direction: 'up', score: 8.8, horizon: 'medium', confidence: 92 },
    { ticker: 'META', direction: 'down', score: 5.8, horizon: 'short', confidence: 68 },
  ];

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>Prévisions de marché</Title>
        <Text c="dimmed" mt={4}>
          Analyse temps réel des signaux quantitatifs multi-horizons
        </Text>
      </div>

      <Alert color="blue" title="Données de démonstration">
        Cette page affiche des données simulées. L'intégration backend complète est en cours.
      </Alert>

      <Grid>
        {mockForecasts.map((f, i) => (
          <Grid.Col key={i} span={{ base: 12, sm: 6, md: 4 }}>
            <Card shadow="md" padding="lg" withBorder>
              <Stack gap="sm">
                <Group justify="space-between">
                  <Title order={3}>{f.ticker}</Title>
                  {f.direction === 'up' ? (
                    <IconTrendingUp color="teal" size={24} />
                  ) : (
                    <IconTrendingDown color="red" size={24} />
                  )}
                </Group>

                <Group gap="xs">
                  <Badge color={f.direction === 'up' ? 'teal' : 'red'} variant="light">
                    Score: {f.score}/10
                  </Badge>
                  <Badge color="blue" variant="light">
                    {f.horizon}
                  </Badge>
                </Group>

                <Text size="sm" c="dimmed">
                  Confiance: {f.confidence}%
                </Text>
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>
    </Stack>
  );
}
