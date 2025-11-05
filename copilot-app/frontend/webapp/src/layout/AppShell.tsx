import { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AppShell as MantineAppShell, Box, Burger, Group, ScrollArea, Stack, Text, ThemeIcon, Tooltip } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconGauge,
  IconPresentationAnalytics,
  IconBuildingBank,
  IconChartHistogram,
  IconNews,
  IconRobot,
  IconChartDots,
  IconChartBubble,
} from '@tabler/icons-react';
import { HealthStatusBadge } from '@/components/ui/HealthStatusBadge';
import ThemeToggle from '@/components/ui/ThemeToggle';

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<any>;
}

const navItems: NavItem[] = [
  { label: 'dashboard', to: '/', icon: IconGauge },
  { label: 'brief', to: '/brief', icon: IconPresentationAnalytics },
  { label: 'macro', to: '/macro', icon: IconBuildingBank },
  { label: 'stocks', to: '/stocks', icon: IconChartHistogram },
  { label: 'news', to: '/news', icon: IconNews },
  { label: 'copilot', to: '/copilot', icon: IconRobot },
  { label: 'forecasts', to: '/forecasts', icon: IconChartDots },
  { label: 'backtests', to: '/backtests', icon: IconChartBubble },
  { label: 'judge', to: '/judge', icon: IconRobot },
];

function NavLink({ item, active, onNavigate }: { item: NavItem; active: boolean; onNavigate: () => void }) {
  const Icon = item.icon;
  return (
    <Group
      data-testid={`nav-${item.label}`}
      onClick={onNavigate}
      gap="sm"
      px="md"
      py="sm"
      justify="space-between"
      style={{
        borderRadius: '12px',
        background: active ? 'rgba(76,110,245,0.15)' : 'transparent',
        cursor: 'pointer',
        transition: 'background 150ms ease',
      }}
    >
      <Group gap="sm">
        <ThemeIcon variant={active ? 'gradient' : 'light'} gradient={{ from: 'indigo', to: 'teal' }}>
          <Icon size={16} />
        </ThemeIcon>
        <Text tt="uppercase" fw={600} fz="xs" c={active ? 'indigo.4' : 'slate.6'}>
          {item.label}
        </Text>
      </Group>
    </Group>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [opened, { toggle, close }] = useDisclosure(false);

  const handleNavigate = (to: string) => {
    navigate(to);
    close();
  };

  return (
    <MantineAppShell
      layout="alt"
      header={{ height: 72 }}
      navbar={{ width: 260, breakpoint: 'md', collapsed: { mobile: !opened } }}
      padding="xl"
    >
      <MantineAppShell.Header withBorder={false} p="md">
        <Group justify="space-between" align="center">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} size="sm" hiddenFrom="md" color="white" />
            <Stack gap={0}>
              <Text fw={700} fz="lg">Finance Copilot</Text>
              <Text c="dimmed" fz="xs">Systèmes d’intelligence de marché</Text>
            </Stack>
          </Group>
          <Group gap="md">
            <Tooltip label="État du backend">
              <Box>
                <HealthStatusBadge />
              </Box>
            </Tooltip>
            <ThemeToggle />
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="md" withBorder={false}>
        <ScrollArea style={{ height: '100%' }}>
          <Stack gap="sm">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                item={item}
                active={location.pathname === item.to}
                onNavigate={() => handleNavigate(item.to)}
              />
            ))}
          </Stack>
        </ScrollArea>
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>
        <Box component="section" style={{ minHeight: '100vh' }}>
          {children}
        </Box>
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
