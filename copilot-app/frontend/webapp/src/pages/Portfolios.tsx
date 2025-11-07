/**
 * Portfolios Page - Manage watchlists and portfolios
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-002 - Frontend integration
 * Refactorisé avec PageHeader pour cohérence UI
 * Enhanced with SectorWheel, TreemapChart, EfficientFrontier
 * Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 */
import { Container, Stack, Tabs, SimpleGrid, Skeleton } from '@mantine/core'
import { IconBriefcase, IconChartPie, IconChartBar, IconTrendingUp } from '@tabler/icons-react'
import { PortfolioManagerWidget } from '@/components/widgets/PortfolioManagerWidget'
import PageHeader from '@/components/layout/PageHeader'
import { SectorWheel, TreemapChart, EfficientFrontier } from '@/components/visualizations'
import { useSectorAllocation, useEfficientFrontier } from '@/hooks'
import { EmptyState } from '@/components/ui/EmptyState'
import { IconChartLine } from '@tabler/icons-react'

export default function Portfolios() {
  const { data: sectorData, isLoading: sectorLoading, error: sectorError } = useSectorAllocation()
  const { data: frontierData, isLoading: frontierLoading, error: frontierError } = useEfficientFrontier()

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Portfolios & Watchlists"
        icon={<IconBriefcase size={28} />}
        description="Create and manage custom watchlists to organize your tickers"
      />

      <Stack gap="xl" mt="xl">
        <PortfolioManagerWidget />

        <Tabs defaultValue="sectors">
          <Tabs.List>
            <Tabs.Tab value="sectors" leftSection={<IconChartPie size={16} />}>
              Allocation par Secteur
            </Tabs.Tab>
            <Tabs.Tab value="treemap" leftSection={<IconChartBar size={16} />}>
              Treemap
            </Tabs.Tab>
            <Tabs.Tab value="frontier" leftSection={<IconTrendingUp size={16} />}>
              Frontière Efficiente
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="sectors" pt="xl">
            {sectorLoading ? (
              <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
                <Skeleton height={400} radius="md" />
                <Skeleton height={400} radius="md" />
              </SimpleGrid>
            ) : sectorError ? (
              <EmptyState
                icon={<IconChartPie size={48} />}
                title="Erreur de chargement"
                description={sectorError instanceof Error ? sectorError.message : "Impossible de charger l'allocation par secteur"}
              />
            ) : sectorData && sectorData.sectors.length > 0 ? (
              <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
                <SectorWheel
                  title="Allocation par Secteur"
                  description="Répartition du portfolio par secteur d'activité"
                  data={sectorData.sectors.map(s => ({
                    id: s.id,
                    label: s.label,
                    value: s.value,
                    color: s.color,
                  }))}
                />
                <TreemapChart
                  title="Treemap d'Allocation"
                  description="Visualisation hiérarchique de l'allocation"
                  data={sectorData.sectors.map(s => ({
                    id: s.id,
                    label: s.label,
                    value: s.value,
                    color: s.color || '#3b82f6',
                  }))}
                  size={600}
                />
              </SimpleGrid>
            ) : (
              <EmptyState
                icon={<IconChartPie size={48} />}
                title="Aucune donnée disponible"
                description="Les données d'allocation par secteur seront disponibles une fois les portfolios configurés"
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="treemap" pt="xl">
            {sectorLoading ? (
              <Skeleton height={600} radius="md" />
            ) : sectorError ? (
              <EmptyState
                icon={<IconChartBar size={48} />}
                title="Erreur de chargement"
                description={sectorError instanceof Error ? sectorError.message : "Impossible de charger le treemap"}
              />
            ) : sectorData && sectorData.sectors.length > 0 ? (
              <TreemapChart
                title="Treemap d'Allocation Portfolio"
                description="Visualisation hiérarchique complète de l'allocation par secteur"
                data={sectorData.sectors.map(s => ({
                  id: s.id,
                  label: s.label,
                  value: s.value,
                  color: s.color || '#3b82f6',
                }))}
                size={800}
              />
            ) : (
              <EmptyState
                icon={<IconChartBar size={48} />}
                title="Aucune donnée disponible"
                description="Les données de treemap seront disponibles une fois les portfolios configurés"
              />
            )}
          </Tabs.Panel>

          <Tabs.Panel value="frontier" pt="xl">
            {frontierLoading ? (
              <Skeleton height={500} radius="md" />
            ) : frontierError ? (
              <EmptyState
                icon={<IconTrendingUp size={48} />}
                title="Erreur de chargement"
                description={frontierError instanceof Error ? frontierError.message : "Impossible de charger la frontière efficiente"}
              />
            ) : frontierData && frontierData.frontier.length > 0 ? (
              <EfficientFrontier
                title="Frontière Efficiente"
                description="Optimisation de portfolio selon Modern Portfolio Theory"
                frontier={frontierData.frontier.map(f => ({
                  risk: f.risk,
                  return: f.return,
                  sharpe: f.sharpe,
                }))}
                portfolios={[]}
                height={500}
              />
            ) : (
              <EmptyState
                icon={<IconTrendingUp size={48} />}
                title="Aucune donnée disponible"
                description="La frontière efficiente sera calculée une fois les données de marché disponibles"
              />
            )}
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  )
}
