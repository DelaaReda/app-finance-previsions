/**
 * ForecastTopCardsWidget Component
 * Shows Top 5 forecasts + Directional Donut distribution
 */

import { useMemo } from 'react';
import { Card as MantineCard, Stack, Title, Text, SimpleGrid, Group, RingProgress, Badge } from '@mantine/core';
import { useForecasts } from '@/hooks/useForecasts';
import { ensureArray } from '@/lib/safe';

interface ForecastItem {
  ticker: string;
  symbol?: string;
  horizon: string;
  score: number;
  confidence: number;
  direction: 'up' | 'down' | 'neutral' | 'flat';
  expected_return_pct?: number;
  expectedReturnPct?: number;
  explanation?: string;
  forecasted_at?: string;
  updatedAt?: string;
}

type Props = {
  limit?: number;  // Number of top forecasts to show (default 5)
  horizons?: string[];  // Filter by specific horizons
  title?: string;
};

export function ForecastTopCardsWidget({ 
  limit = 5, 
  horizons = ['short', 'medium', 'long'], 
  title = 'Top 5 Prévisions + Répartition Directionnelle' 
}: Props) {
  const { data, isLoading, error } = useForecasts({ 
    horizon: undefined, // Will be filtered client-side
    universe: [] 
  });

  // Get forecast data
  const forecasts: ForecastItem[] = ensureArray(data?.rows ?? data ?? []);

  // Filter by horizons if specified
  const filteredForecasts = useMemo(() => {
    if (!horizons || horizons.length === 0) return forecasts.slice(0, limit);
    
    return forecasts
      .filter(f => f.horizon && horizons.includes(f.horizon))
      .slice(0, limit);
  }, [forecasts, horizons, limit]);

  // Calculate directional distribution
  const directionalStats = useMemo(() => {
    const distribution = { up: 0, down: 0, neutral: 0, flat: 0 };
    
    forecasts.forEach(forecast => {
      const direction = forecast.direction?.toLowerCase();
      if (direction && distribution.hasOwnProperty(direction)) {
        distribution[direction as keyof typeof distribution] += 1;
      }
    });

    const total = forecasts.length;
    return {
      up: total > 0 ? Math.round((distribution.up / total) * 100) : 0,
      down: total > 0 ? Math.round((distribution.down / total) * 100) : 0,
      neutral: total > 0 ? Math.round((distribution.neutral / total) * 100) : 0,
      flat: total > 0 ? Math.round((distribution.flat / total) * 100) : 0,
      counts: distribution,
      total
    };
  }, [forecasts]);

  // Helper function to get Mantine color for direction
  const getColorForDirection = (direction: string | undefined) => {
    switch (direction?.toLowerCase()) {
      case 'up': return 'green';
      case 'down': return 'red';
      case 'neutral': return 'yellow';
      case 'flat': return 'gray';
      default: return 'gray';
    }
  };

  return (
    <MantineCard shadow="sm" padding="lg">
      <Stack gap="lg">
        <div>
          <Title order={3}>{title}</Title>
          {data && 'freshness' in data && (
            <Text c="dimmed" size="sm" mt={4}>
              Dernière mise à jour: {new Date(data.freshness as string).toLocaleString('fr-FR')}
            </Text>
          )}
        </div>

        {isLoading && (
          <Stack align="center" justify="center" style={{ padding: '20px', minHeight: '200px' }}>
            <Text>Chargement des prévisions...</Text>
          </Stack>
        )}
        
        {error && (
          <div style={{ padding: '20px', color: 'tomato' }}>
            <Text>Erreur de chargement: {String(error)}</Text>
          </div>
        )}
        
        {!isLoading && !error && forecasts.length === 0 && (
          <div style={{ padding: '20px', textAlign: 'center' }}>
            <Text>Aucune prévision disponible pour le moment.</Text>
          </div>
        )}
        
        {!isLoading && !error && forecasts.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Top N Forecasts */}
            <div>
              <Title order={4}>Top {limit} Prévisions</Title>
              <SimpleGrid cols={{ base: 1, sm: 2, md: 2, lg: 5 }} spacing="md" mt="md">
                {filteredForecasts.map((forecast, index) => (
                  <MantineCard 
                    key={`${forecast.ticker || forecast.symbol}-${index}`} 
                    withBorder 
                    padding="md" 
                    style={{ 
                      borderWidth: index < 3 ? '2px' : '1px',
                      borderColor: index < 3 ? '#4CAF50' : '#444'  // Highlight top 3
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <Title order={5} style={{ fontSize: '16px' }}>
                        {forecast.ticker || forecast.symbol}
                      </Title>
                      <Badge color={getColorForDirection(forecast.direction)}>
                        {forecast.direction?.toUpperCase() || '—'}
                      </Badge>
                    </div>
                    
                    <Text size="sm" c="dimmed" mb="xs">
                      Horizon: {forecast.horizon || 'N/A'}
                    </Text>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <RingProgress
                        size={70}
                        thickness={6}
                        sections={[{
                          value: forecast.score ? Math.min(100, Math.abs(forecast.score)) : 0,
                          color: forecast.score && forecast.score > 50 ? 'blue' : 'orange',
                        }]}
                        label={
                          <Text size="sm" align="center" fw={700}>
                            {forecast.score ? forecast.score.toFixed(0) : '—'}
                          </Text>
                        }
                      />
                      <div style={{ flex: 1 }}>
                        <Text size="sm">Conf: {(forecast.confidence ? forecast.confidence * 100 : 0).toFixed(0)}%</Text>
                        <Text size="sm">
                          ER: {(forecast.expected_return_pct || forecast.expectedReturnPct || 0).toFixed(2)}%
                        </Text>
                      </div>
                    </div>
                    
                    {forecast.explanation && (
                      <Text size="xs" c="dimmed" lineClamp={2}>
                        {forecast.explanation.substring(0, 60)}...
                      </Text>
                    )}
                  </MantineCard>
                ))}
              </SimpleGrid>
            </div>
            
            {/* Directional Distribution - Donut Chart */}
            <div>
              <Title order={4}>Distribution Directionnelle</Title>
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '16px' }}>
                <div style={{ position: 'relative', width: '180px', height: '180px' }}>
                  {/* SVG Donut Chart for Directional Distribution */}
                  <svg viewBox="0 0 100 100" width="180" height="180">
                    {/* UP direction - green */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#4CAF50"
                      strokeWidth="15"
                      strokeDasharray={`${directionalStats.up * 2.5} ${100 * 2.5 - directionalStats.up * 2.5}`}
                      strokeDashoffset="25"
                      transform="rotate(-90 50 50)"
                    />
                    
                    {/* DOWN direction - red */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#F44336"
                      strokeWidth="15"
                      strokeDasharray={`${directionalStats.down * 2.5} ${100 * 2.5 - directionalStats.down * 2.5}`}
                      strokeDashoffset={25 - directionalStats.up * 2.5}
                      transform="rotate(-90 50 50)"
                    />
                    
                    {/* NEUTRAL direction - yellow */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#FFC107"
                      strokeWidth="15"
                      strokeDasharray={`${directionalStats.neutral * 2.5} ${100 * 2.5 - directionalStats.neutral * 2.5}`}
                      strokeDashoffset={25 - (directionalStats.up + directionalStats.down) * 2.5}
                      transform="rotate(-90 50 50)"
                    />
                    
                    {/* FLAT direction - gray */}
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="none"
                      stroke="#9E9E9E"
                      strokeWidth="15"
                      strokeDasharray={`${directionalStats.flat * 2.5} ${100 * 2.5 - directionalStats.flat * 2.5}`}
                      strokeDashoffset={25 - (directionalStats.up + directionalStats.down + directionalStats.neutral) * 2.5}
                      transform="rotate(-90 50 50)"
                    />
                  </svg>
                  
                  <div style={{ 
                    position: 'absolute', 
                    top: '50%', 
                    left: '50%', 
                    transform: 'translate(-50%, -50%)', 
                    textAlign: 'center' 
                  }}>
                    <Text fw={700} size="lg">{directionalStats.total}</Text>
                    <Text size="xs">Prévisions</Text>
                  </div>
                </div>
              </div>
              
              {/* Legend */}
              <Group justify="center" gap="sm" mt="sm" wrap="wrap">
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', backgroundColor: '#4CAF50', borderRadius: '2px' }}></div>
                  <Text size="sm">Haussier: {directionalStats.counts.up} ({directionalStats.up}%)</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', backgroundColor: '#F44336', borderRadius: '2px' }}></div>
                  <Text size="sm">Baissier: {directionalStats.counts.down} ({directionalStats.down}%)</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', backgroundColor: '#FFC107', borderRadius: '2px' }}></div>
                  <Text size="sm">Neutre: {directionalStats.counts.neutral} ({directionalStats.neutral}%)</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', backgroundColor: '#9E9E9E', borderRadius: '2px' }}></div>
                  <Text size="sm">Stable: {directionalStats.counts.flat} ({directionalStats.flat}%)</Text>
                </div>
              </Group>
            </div>
          </div>
        )}
      </Stack>
    </MantineCard>
  );
}