/**
 * SentimentGauge - Gauge de sentiment avec indicateurs
 * Sentiment marché, news, social media
 */

import { Card, Stack, Title, Text, Group, Badge, RingProgress } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconMinus } from '@tabler/icons-react';

interface SentimentGaugeProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Score de sentiment (-100 à +100) */
  sentiment: number; // -100 (très négatif) à +100 (très positif)
  /** Sous-scores */
  subScores?: Array<{
    label: string;
    value: number;
    color?: string;
  }>;
  /** Taille */
  size?: number;
}

export function SentimentGauge({
  title,
  description,
  sentiment,
  subScores = [],
  size = 250,
}: SentimentGaugeProps) {
  // Normaliser sentiment de -100/+100 à 0-100 pour RingProgress
  const normalizedSentiment = ((sentiment + 100) / 200) * 100;
  
  const getColor = () => {
    if (sentiment > 50) return 'teal';
    if (sentiment > 20) return 'blue';
    if (sentiment > -20) return 'gray';
    if (sentiment > -50) return 'orange';
    return 'red';
  };

  const getLabel = () => {
    if (sentiment > 50) return 'Très Positif';
    if (sentiment > 20) return 'Positif';
    if (sentiment > -20) return 'Neutre';
    if (sentiment > -50) return 'Négatif';
    return 'Très Négatif';
  };

  const getIcon = () => {
    if (sentiment > 20) return <IconTrendingUp size={24} />;
    if (sentiment < -20) return <IconTrendingDown size={24} />;
    return <IconMinus size={24} />;
  };

  const color = getColor();
  const sections = [
    { value: normalizedSentiment, color },
    { value: 100 - normalizedSentiment, color: 'var(--mantine-color-gray-8)' },
  ];

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md" align="center">
        <div style={{ textAlign: 'center' }}>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ position: 'relative' }}>
          <RingProgress
            size={size}
            thickness={24}
            roundCaps
            sections={sections}
            label={
              <div style={{ textAlign: 'center' }}>
                <div style={{ marginBottom: '8px' }}>
                  {getIcon()}
                </div>
                <Text fw={700} fz="xl" c={color}>
                  {sentiment > 0 ? '+' : ''}{sentiment.toFixed(1)}
                </Text>
                <Text size="xs" c="dimmed">
                  / 100
                </Text>
              </div>
            }
          />
        </div>
        
        <Badge
          color={color}
          variant="light"
          size="lg"
        >
          {getLabel()}
        </Badge>
        
        {/* Sub-scores */}
        {subScores.length > 0 && (
          <Group gap="md" mt="md" wrap="wrap" justify="center">
            {subScores.map((sub, index) => (
              <div key={index} style={{ textAlign: 'center' }}>
                <Text size="xs" c="dimmed" mb={4}>{sub.label}</Text>
                <RingProgress
                  size={60}
                  thickness={6}
                  sections={[
                    { value: Math.abs(sub.value), color: sub.color || 'blue' },
                  ]}
                  label={
                    <Text size="xs" fw={600}>
                      {sub.value > 0 ? '+' : ''}{sub.value.toFixed(0)}
                    </Text>
                  }
                />
              </div>
            ))}
          </Group>
        )}
      </Stack>
    </Card>
  );
}

