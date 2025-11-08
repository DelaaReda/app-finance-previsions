/**
 * Analytics Page - Capital Flows Analysis
 * Visualizes capital flows with SankeyDiagram
 * Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 */
import { Container, Stack, Skeleton } from '@mantine/core'
import { IconChartBar } from '@tabler/icons-react'
import PageHeader from '@/components/layout/PageHeader'
import { SankeyDiagram } from '@/components/visualizations'
import { useCapitalFlows } from '@/hooks/useCapitalFlows'
import EmptyState from '@/components/ui/EmptyState'

export default function Analytics() {
  const { data, isLoading, error } = useCapitalFlows()

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Analytics - Flux de Capitaux"
        icon={<IconChartBar size={28} />}
        description="Analyse des flux de capitaux entre sources et secteurs"
      />

      <Stack gap="xl" mt="xl">
        {isLoading ? (
          <Skeleton height={600} radius="md" />
        ) : error ? (
          <EmptyState
            icon={<IconChartBar size={48} />}
            title="Erreur de chargement"
            description={error instanceof Error ? error.message : "Impossible de charger les flux de capitaux"}
          />
        ) : data && data.nodes.length > 0 && data.links.length > 0 ? (
          <SankeyDiagram
            title="Flux de Capitaux"
            description={`${data.nodes.length} sources/cibles, ${data.links.length} flux analysés sur ${data.lookback_days} jours`}
            nodes={data.nodes}
            links={data.links}
            height={600}
          />
        ) : (
          <EmptyState
            icon={<IconChartBar size={48} />}
            title="Aucune donnée disponible"
            description="Les flux de capitaux seront disponibles une fois les calculs terminés"
          />
        )}
      </Stack>
    </Container>
  )
}

