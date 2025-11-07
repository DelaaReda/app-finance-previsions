/**
 * Portfolios Page - Manage watchlists and portfolios
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-002 - Frontend integration
 * Refactorisé avec PageHeader pour cohérence UI
 */
import { Container, Stack } from '@mantine/core'
import { IconBriefcase } from '@tabler/icons-react'
import { PortfolioManagerWidget } from '@/components/widgets/PortfolioManagerWidget'
import PageHeader from '@/components/layout/PageHeader'

export default function Portfolios() {
  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Portfolios & Watchlists"
        icon={<IconBriefcase size={28} />}
        description="Create and manage custom watchlists to organize your tickers"
      />

      <Stack gap="lg" mt="xl">
        <PortfolioManagerWidget />
      </Stack>
    </Container>
  )
}
