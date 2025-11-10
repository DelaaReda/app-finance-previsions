import { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  AppShell as MantineAppShell,
  Box,
  Burger,
  Group,
  ScrollArea,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconLayoutDashboard,
  IconNotebook,
  IconBuildingBank,
  IconTrendingUp,
  IconArticle,
  IconMessages,
  IconChartDots3,
  IconChartHistogram,
  IconArrowsShuffle,
  IconScaleOutline,
} from '@tabler/icons-react';
import { HealthStatusBadge } from '@/components/ui/HealthStatusBadge';
import ThemeToggle from '@/components/ui/ThemeToggle';
import classes from './AppShell.module.css';

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<any>;
  gradient: { from: string; to: string };
}

const navItems: NavItem[] = [
  { label: 'dashboard', to: '/', icon: IconLayoutDashboard, gradient: { from: 'indigo', to: 'cyan' } },
  { label: 'brief', to: '/brief', icon: IconNotebook, gradient: { from: 'grape', to: 'pink' } },
  { label: 'macro', to: '/macro', icon: IconBuildingBank, gradient: { from: 'teal', to: 'lime' } },
  { label: 'stocks', to: '/stocks', icon: IconTrendingUp, gradient: { from: 'orange', to: 'yellow' } },
  { label: 'news', to: '/news', icon: IconArticle, gradient: { from: 'red', to: 'orange' } },
  { label: 'copilot', to: '/copilot', icon: IconMessages, gradient: { from: 'violet', to: 'cyan' } },
  { label: 'forecasts', to: '/forecasts', icon: IconChartDots3, gradient: { from: 'blue', to: 'green' } },
  { label: 'backtests', to: '/backtests', icon: IconChartHistogram, gradient: { from: 'cyan', to: 'lime' } },
  { label: 'compare', to: '/compare', icon: IconArrowsShuffle, gradient: { from: 'purple', to: 'teal' } },
  { label: 'judge', to: '/judge', icon: IconScaleOutline, gradient: { from: 'gray', to: 'indigo' } },
];

function NavLink({ item, active, onNavigate }: { item: NavItem; active: boolean; onNavigate: () => void }) {
  const Icon = item.icon;
  return (
    <Group
      data-testid={`nav-${item.label}`}
      onClick={onNavigate}
      className={`${classes.navCard} ${active ? classes.navCardActive : ''}`}
    >
      <Group gap="sm">
        <ThemeIcon
          size="lg"
          radius="md"
          variant="gradient"
          gradient={item.gradient}
          className={classes.navIcon}
        >
          <Icon size={18} />
        </ThemeIcon>
        <Text tt="uppercase" fw={600} fz="xs" c={active ? 'indigo.2' : 'gray.3'} className={classes.navLabel}>
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
      styles={{
        header: {
          background: 'rgba(9, 15, 30, 0.75)',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          backdropFilter: 'blur(16px)',
        },
        navbar: {
          background: 'rgba(7, 11, 24, 0.85)',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          backdropFilter: 'blur(18px)',
        },
        main: {
          background: 'radial-gradient(circle at 20% 20%, rgba(76,110,245,0.18), transparent 45%), radial-gradient(circle at 80% 10%, rgba(20,184,166,0.2), transparent 35%), #050910',
        },
      }}
    >
      <MantineAppShell.Header withBorder={false} p="md">
        <Group justify="space-between" align="center">
          <Group gap="sm">
            <Burger opened={opened} onClick={toggle} size="sm" hiddenFrom="md" color="white" />
            <Stack gap={0}>
              <Text fw={700} fz="lg">Finance Copilot</Text>
              <Text c="gray.3" fz="xs">Systèmes d'intelligence de marché</Text>
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
        <Box
          component="section"
          style={{
            minHeight: '100vh',
            padding: '24px',
            maxWidth: 1440,
            margin: '0 auto',
          }}
        >
          {children}
        </Box>
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
