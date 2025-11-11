/**
 * Diagnostics Page - Correlation Analysis
 * Visualizes correlation networks and heatmaps for portfolio analysis
 * Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 */
import { Container, Stack, Tabs, SimpleGrid, Skeleton, Slider, Text, Group } from '@mantine/core'
import { IconRadar, IconChartBar, IconNetwork } from '@tabler/icons-react'
import PageHeader from '@/components/layout/PageHeader'
import { CorrelationNetwork, CorrelationHeatmap } from '@/components/visualizations'
import { useCorrelationMatrix, useCorrelationNetwork } from '@/hooks/useCorrelationNetwork'
import EmptyState from '@/components/ui/EmptyState'
import { useState } from 'react'

export default function Diagnostics() {
  const [threshold, setThreshold] = useState(0.5)
  const { data: matrixData, isLoading: matrixLoading, error: matrixError } = useCorrelationMatrix()
  const { data: networkData, isLoading: networkLoading, error: networkError } = useCorrelationNetwork(threshold)

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Diagnostics - Corrélations"
        icon={<IconRadar size={28} />}
        description="Analyse des corrélations entre actifs pour optimisation de portfolio"
      />

      <Stack gap="xl" mt="xl">
        <Tabs defaultValue="network">
          <Tabs.List>
            <Tabs.Tab value="network" leftSection={<IconNetwork size={16} />}>
              Réseau de Corrélations
            </Tabs.Tab>
            <Tabs.Tab value="heatmap" leftSection={<IconChartBar size={16} />}>
              Matrice de Corrélations
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="network" pt="xl">
            <Stack gap="md">
              <Group justify="space-between" align="center">
                <Text size="sm" c="dimmed">
                  Seuil de corrélation minimum: <strong>{threshold.toFixed(2)}</strong>
                </Text>
                <Slider
                  value={threshold}
                  onChange={setThreshold}
                  min={0}
                  max={1}
                  step={0.05}
                  marks={[
                    { value: 0, label: '0' },
                    { value: 0.5, label: '0.5' },
                    { value: 1, label: '1' },
                  ]}
                  style={{ width: 300 }}
                />
              </Group>

              {networkLoading ? (
                <Skeleton height={600} radius="md" />
              ) : networkError ? (
                <EmptyState
                  icon={<IconNetwork size={48} />}
                  title="Erreur de chargement"
                  description={networkError instanceof Error ? networkError.message : "Impossible de charger le réseau de corrélations"}
                />
              ) : networkData && networkData.nodes.length > 0 ? (
                <CorrelationNetwork
                  title={`Réseau de Corrélations (≥ ${threshold.toFixed(2)})`}
                  description={`${networkData.nodes.length} actifs, ${networkData.links.length} liens significatifs`}
                  nodes={networkData.nodes}
                  links={networkData.links}
                  threshold={threshold}
                />
              ) : (
                <EmptyState
                  icon={<IconNetwork size={48} />}
                  title="Aucune donnée disponible"
                  description="Les données de corrélations seront disponibles une fois les calculs terminés"
                />
              )}
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="heatmap" pt="xl">
            {matrixLoading ? (
              <Skeleton height={600} radius="md" />
            ) : matrixError ? (
              <EmptyState
                icon={<IconChartBar size={48} />}
                title="Erreur de chargement"
                description={matrixError instanceof Error ? matrixError.message : "Impossible de charger la matrice de corrélations"}
              />
            ) : matrixData && matrixData.tickers.length > 0 ? (
              <CorrelationHeatmap
                title="Matrice de Corrélations"
                description={`${matrixData.tickers.length} actifs analysés sur ${matrixData.lookback_days} jours`}
                data={matrixData.matrix}
                tickers={matrixData.tickers}
              />
            ) : (
              <EmptyState
                icon={<IconChartBar size={48} />}
                title="Aucune donnée disponible"
                description="La matrice de corrélations sera disponible une fois les calculs terminés"
              />
            )}
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  )
}

