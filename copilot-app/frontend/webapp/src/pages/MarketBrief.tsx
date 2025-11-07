/**
 * Page Market Brief
 * Daily/Weekly briefs avec Top 3 signaux/risques
 * Refactorisé avec Mantine pour un look professionnel
 */

import { useState } from 'react'
import { Container, Stack, Group, SegmentedControl, Select, Alert, Button, Badge, Text, SimpleGrid, Skeleton } from '@mantine/core'
import { IconRefresh, IconAlertTriangle, IconFileText, IconTrendingUp, IconTrendingDown } from '@tabler/icons-react'
import { useLatestBriefWithFallback } from '@/hooks/useBriefs'
import { Card, Title, Heading } from '@/ui'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import TopSignals from '@/components/signals/TopSignals'
import TopRisks from '@/components/signals/TopRisks'
import FreshnessBadge from '@/components/ui/FreshnessBadge'
import PageHeader from '@/components/layout/PageHeader'
import { BriefSkeleton } from '@/components/ui/Skeletons'
import EmptyState from '@/components/ui/EmptyState'
import { ProgressRing } from '@/components/visualizations'
import { ensureArray } from '@/lib/safe'

const UNIVERSE_OPTIONS = [
  { value: 'SPY,QQQ', label: 'SPY,QQQ (Défaut)' },
  { value: 'SPY,AAPL,NVDA,MSFT', label: 'SPY,AAPL,NVDA,MSFT' },
  { value: 'QQQ,AAPL,GOOGL,AMZN', label: 'QQQ,AAPL,GOOGL,AMZN' },
  { value: 'SPY,TSLA,META,NVDA', label: 'SPY,TSLA,META,NVDA' },
]

export default function MarketBrief() {
  const [type, setType] = useState<'daily' | 'weekly'>('daily')
  const [universe, setUniverse] = useState<string[]>(['SPY', 'QQQ'])
  
  // Use the fallback-aware hook with callback for fallback detection
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null)
  const { data: briefResp, isLoading, error, refetch } = useLatestBriefWithFallback(
    type, 
    universe,
    (message) => setFallbackMessage(message)
  )
  
  const brief = briefResp?.data || briefResp || {}  // Handle both nested and flat response
  
  // Check if response contains fallback indicators
  const hasFallback = fallbackMessage != null || 
    brief.is_fallback || 
    brief.fallback || 
    brief.error || 
    ('top_signals' in brief && Array.isArray(brief.top_signals) && brief.top_signals.length === 0 && 
     'top_risks' in brief && Array.isArray(brief.top_risks) && brief.top_risks.length === 0)

  const handleUniverseChange = (value: string | null) => {
    if (value) {
      setUniverse(value.split(',').filter(Boolean))
    }
  }

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Market Brief"
        icon={<IconFileText size={28} />}
        description={`Brief ${type === 'daily' ? 'quotidien' : 'hebdomadaire'} avec top signaux et risques`}
        badge={brief?.generated_at ? { label: 'Live', color: 'green' } : undefined}
        stats={[
          { label: 'Signaux', value: ensureArray(brief?.top_signals || []).length },
          { label: 'Risques', value: ensureArray(brief?.top_risks || []).length },
        ]}
        actions={
          <Group gap="md">
            <FreshnessBadge freshness={brief?.generated_at ?? brief?.freshness ?? undefined} />
            <SegmentedControl
              value={type}
              onChange={(value) => setType(value as 'daily' | 'weekly')}
              data={[
                { label: 'Quotidien', value: 'daily' },
                { label: 'Hebdomadaire', value: 'weekly' },
              ]}
              size="md"
            />
            <Select
              label="Univers"
              placeholder="Sélectionner"
              value={universe.join(',')}
              onChange={handleUniverseChange}
              data={UNIVERSE_OPTIONS}
              style={{ minWidth: 200 }}
              size="md"
            />
          </Group>
        }
        onRefresh={() => refetch()}
      />

      {isLoading && <BriefSkeleton />}
      
      {error && <ErrorMessage message={String(error)} />}
      
      {/* Fallback banner if needed */}
      {hasFallback && fallbackMessage && (
        <Alert
          icon={<IconAlertTriangle size={20} />}
          title="Mode Fallback"
          color="yellow"
          variant="light"
          mb="lg"
        >
          <Group justify="space-between" align="center">
            <div>
              <Text fw={600} c="yellow.6">{fallbackMessage}</Text>
              <Text size="sm" c="dimmed" mt={4}>
                Dernière mise à jour: {new Date(brief?.generated_at || brief?.freshness || Date.now()).toLocaleTimeString()}
              </Text>
            </div>
            <Button
              variant="light"
              size="sm"
              onClick={() => refetch()}
              leftSection={<IconRefresh size={16} />}
            >
              Réessayer
            </Button>
          </Group>
        </Alert>
      )}
      
      {!isLoading && !error && brief && Object.keys(brief).length > 0 && (
        <Stack gap="xl">
          <Card>
            <Stack gap="md">
              <Group justify="space-between" align="flex-start">
                <div>
                  <Heading order={3} mb="xs">
                    Market Brief {brief.period === 'daily' ? 'Journalier' : 'Hebdomadaire'}
                  </Heading>
                  <Text c="dimmed" size="sm">
                    {brief.generated_at || brief.freshness ? 
                      new Date(brief.generated_at || brief.freshness).toLocaleDateString('fr-FR', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })
                    : 'Date non disponible'}
                  </Text>
                </div>
                <Badge variant="light" color="blue" size="lg">
                  {ensureArray(brief.universe || universe).join(', ')}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed">
                Analyse générée pour l'univers: {ensureArray(brief.universe || universe).join(', ')}
              </Text>
            </Stack>
          </Card>
          
          {/* Summary content if available - for better UX */}
          {(brief.summary || brief.content) && (
            <Card>
              <Stack gap="md">
                <Heading order={4}>Résumé</Heading>
                <Text style={{ lineHeight: 1.6 }}>
                  {brief.summary || brief.content}
                </Text>
              </Stack>
            </Card>
          )}

          {/* Top 3 Signaux et Top 3 Risques */}
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
            <TopSignals signals={ensureArray(brief?.top_signals || brief?.signals || [])} title="Top 3 Signaux" />
            <TopRisks risks={ensureArray(brief?.top_risks || brief?.risks || [])} title="Top 3 Risques" />
          </SimpleGrid>

          {/* Picks avec visualisations */}
          {brief?.picks && Array.isArray(brief.picks) && brief.picks.length > 0 && (
            <Card padding="lg" radius="md" withBorder>
              <Stack gap="md">
                <Heading order={4}>🎯 Picks Recommandés</Heading>
                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
                  {ensureArray(brief.picks).map((pick: any, index: number) => {
                    const action = (pick.action || pick.direction || 'HOLD').toString().toUpperCase()
                    const isBuy = action === 'BUY' || action === 'UP'
                    const isSell = action === 'SELL' || action === 'DOWN'
                    const score = (pick.composite_score || pick.score || 0) * 10; // Convertir en pourcentage si 0-1
                    const finalScore = score > 100 ? score / 10 : score; // Ajuster si déjà en pourcentage
                    
                    return (
                      <ProgressRing
                        key={index}
                        label={pick.ticker || pick.symbol || pick.asset}
                        value={Math.min(100, Math.max(0, finalScore))}
                        color={isBuy ? 'teal' : isSell ? 'red' : 'gray'}
                        subtitle={action}
                        badge={{
                          label: action,
                          color: isBuy ? 'green' : isSell ? 'red' : 'blue',
                        }}
                        icon={isBuy ? <IconTrendingUp size={16} /> : isSell ? <IconTrendingDown size={16} /> : undefined}
                        size={120}
                      />
                    )
                  })}
                </SimpleGrid>
              </Stack>
            </Card>
          )}

          {/* Sources */}
          {brief?.sources && Array.isArray(brief.sources) && brief.sources.length > 0 && (
            <Card>
              <Stack gap="md">
                <Heading order={4}>📚 Sources</Heading>
                <Group gap="sm">
                  {ensureArray(brief.sources).map((source: any, index: number) => (
                    <Badge key={index} variant="dot" size="lg">
                      {source.type || source.name || source.id || 'N/A'}: {source.series_id || source.count || source.id || 'N/A'}
                    </Badge>
                  ))}
                </Group>
              </Stack>
            </Card>
          )}

          <Text size="sm" c="dimmed" ta="center" mt="md">
            Généré le {brief?.generated_at || brief?.freshness ? new Date(brief.generated_at || brief.freshness).toLocaleString() : 'N/A'} • Période: {brief?.period || type || 'N/A'}
          </Text>
        </Stack>
      )}
      
      {/* Empty state when no data and no loading/error */}
      {!isLoading && !error && (!brief || Object.keys(brief).length === 0) && (
        <EmptyState
          icon={<IconFileText size={48} />}
          title="Aucun brief disponible"
          description="Le système est en train de générer le brief de marché"
          action={{
            label: "Rafraîchir",
            onClick: () => refetch()
          }}
        />
      )}
    </Container>
  )
}
