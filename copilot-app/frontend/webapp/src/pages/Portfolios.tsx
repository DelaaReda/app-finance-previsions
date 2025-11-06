/**
 * Portfolios Page - Manage watchlists and portfolios
 * Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
 * Task: API-PORTFOLIO-002 - Frontend integration
 */
import { Stack, Title, Text, Group } from '@mantine/core'
import { IconBriefcase } from '@tabler/icons-react'
import { PortfolioManagerWidget } from '@/components/widgets/PortfolioManagerWidget'

export default function Portfolios() {
  return (
    <Stack gap="lg">
      {/* Header */}
      <div>
        <Group gap="xs" align="center">
          <IconBriefcase size={28} color="#4169E1" />
          <Title order={2}>Portfolios & Watchlists</Title>
        </Group>
        <Text c="dimmed" size="sm" mt={4}>
          Create and manage custom watchlists to organize your tickers
        </Text>
      </div>

      {/* Portfolio Manager Widget */}
      <PortfolioManagerWidget />
    </Stack>
  )
}
