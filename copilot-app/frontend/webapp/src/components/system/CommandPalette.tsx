/**
 * Command Palette Component
 * 
 * Global command palette for navigation, search, and actions.
 * Activated with Ctrl+K / Cmd+K.
 * 
 * Author: ELENA-39
 * Task: FC-UX-001
 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Modal,
  Stack,
  TextInput,
  ScrollArea,
  UnstyledButton,
  Group,
  Text,
  Kbd,
  Divider,
} from '@mantine/core';
import {
  IconDashboard,
  IconChartLine,
  IconNews,
  IconChartCandle,
  IconRefresh,
  IconMoon,
  IconBriefcase,
  IconMacro,
  IconRocket,
  IconSearch,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useDrillDown } from '../../contexts/DrillDownContext';
import { useForecasts } from '../../hooks/useForecasts';
import { usePortfolios } from '../../hooks/usePortfolios';

interface CommandPaletteProps {
  opened: boolean;
  close: () => void;
}

type CommandAction = {
  id: string;
  label: string;
  description?: string;
  keywords?: string[];
  onClick: () => void;
  leftSection?: ReactNode;
};

function matchesQuery(action: CommandAction, query: string) {
  if (!query) return true;
  const haystack = `${action.label} ${action.description ?? ''} ${(action.keywords ?? []).join(' ')}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

/**
 * Command Palette
 * 
 * Provides instant access to:
 * - Navigation (pages)
 * - Tickers (dynamic from forecasts)
 * - Actions (refresh, export, etc.)
 */
export function CommandPalette({ opened, close }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { navigateToTicker } = useDrillDown();
  const { data: forecasts } = useForecasts();
  const { data: portfolios = [] } = usePortfolios();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Build dynamic command list
  const actions = useMemo<CommandAction[]>(() => {
    const commands: CommandAction[] = [];
    
    // === NAVIGATION COMMANDS ===
    commands.push(
      {
        id: 'nav-dashboard',
        label: 'Dashboard',
        description: 'Go to main dashboard',
        onClick: () => {
          navigate('/');
          close();
        },
        leftSection: <IconDashboard size={20} />,
      },
      {
        id: 'nav-forecasts',
        label: 'Forecasts',
        description: 'View all forecasts',
        onClick: () => {
          navigate('/forecasts');
          close();
        },
        leftSection: <IconChartLine size={20} />,
      },
      {
        id: 'nav-news',
        label: 'News',
        description: 'View news feed',
        onClick: () => {
          navigate('/news');
          close();
        },
        leftSection: <IconNews size={20} />,
      },
      {
        id: 'nav-macro',
        label: 'Macro',
        description: 'Macro indicators',
        onClick: () => {
          navigate('/macro');
          close();
        },
        leftSection: <IconMacro size={20} />,
      },
      {
        id: 'nav-stocks',
        label: 'Stocks',
        description: 'Stock analysis',
        onClick: () => {
          navigate('/stocks');
          close();
        },
        leftSection: <IconChartCandle size={20} />,
      },
      {
        id: 'nav-backtests',
        label: 'Backtests',
        description: 'Strategy backtests',
        onClick: () => {
          navigate('/backtests');
          close();
        },
        leftSection: <IconRocket size={20} />,
      },
      {
        id: 'nav-brief',
        label: 'Market Brief',
        description: 'Daily & weekly briefs',
        onClick: () => {
          navigate('/brief');
          close();
        },
        leftSection: <IconBriefcase size={20} />,
      }
    );
    
    // === TICKER COMMANDS (Dynamic) ===
    const tickers = forecasts?.rows?.map((f: any) => f.ticker).filter(Boolean) || [];
    const uniqueTickers = [...new Set(tickers)].slice(0, 20); // Top 20
    
    uniqueTickers.forEach((ticker) => {
      commands.push({
        id: `ticker-${ticker}`,
        label: `View ${ticker}`,
        description: `Go to ${ticker} ticker page`,
        onClick: () => {
          navigateToTicker(ticker as string, {
            source: 'unknown',
            reason: `Searched via command palette`,
          });
          close();
        },
        leftSection: <IconChartCandle size={20} />,
        keywords: [ticker as string, `${ticker} stock`, `${ticker} forecast`],
      });
    });
    
    // === PORTFOLIO COMMANDS (Dynamic) ===
    portfolios.forEach((portfolio) => {
      commands.push({
        id: `portfolio-${portfolio.id}`,
        label: `📂 ${portfolio.name}`,
        description: `View ${portfolio.tickers.length} tickers: ${portfolio.tickers.slice(0, 3).join(', ')}${portfolio.tickers.length > 3 ? '...' : ''}`,
        onClick: () => {
          // For now, navigate to Dashboard with portfolio filter
          // TODO: Create dedicated portfolio detail page
          navigate(`/dashboard?portfolio=${portfolio.id}`);
          close();
        },
        leftSection: <IconBriefcase size={20} />,
        keywords: [portfolio.name, ...portfolio.tickers, 'portfolio', 'watchlist'],
      });
    });
    
    // === ACTION COMMANDS ===
    commands.push(
      {
        id: 'action-refresh',
        label: 'Refresh Data',
        description: 'Refresh all data',
        onClick: () => {
          window.location.reload();
          close();
        },
        leftSection: <IconRefresh size={20} />,
      },
      {
        id: 'action-theme',
        label: 'Toggle Theme',
        description: 'Switch dark/light mode',
        onClick: () => {
          // Theme toggle logic here
          close();
        },
        leftSection: <IconMoon size={20} />,
      }
    );

    return commands;
  }, [navigate, navigateToTicker, forecasts, portfolios, close]);

  const filteredActions = useMemo(() => {
    return actions.filter((action) => matchesQuery(action, query)).slice(0, 10);
  }, [actions, query]);

  useEffect(() => {
    if (opened) {
      // focus input and reset query on open
      setQuery('');
      const id = window.setTimeout(() => inputRef.current?.focus(), 10);
      return () => window.clearTimeout(id);
    }
    return undefined;
  }, [opened]);

  const handleClose = () => {
    setQuery('');
    close();
  };

  const handleSubmit = () => {
    const first = filteredActions[0];
    if (first) {
      first.onClick();
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      size="lg"
      radius="lg"
      padding="lg"
      centered
      withCloseButton={false}
      styles={{
        content: {
          background: 'var(--mantine-color-dark-7)',
        },
      }}
    >
      <Stack gap="md">
        <TextInput
          inputRef={inputRef}
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
          placeholder="Rechercher pages, tickers, actions..."
          leftSection={<IconSearch size={18} />}
          rightSectionWidth={90}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              handleSubmit();
            }
          }}
          rightSection={
            <Group gap={4}>
              <Kbd>↵</Kbd>
              <Text size="xs" c="dimmed">
                Valider
              </Text>
            </Group>
          }
        />

        <Divider color="var(--mantine-color-dark-4)" />

        <ScrollArea h={360} type="hover">
          <Stack gap="xs">
            {filteredActions.length === 0 ? (
              <Text size="sm" c="dimmed">
                Aucun résultat{query ? ` pour « ${query} »` : ''}.
              </Text>
            ) : (
              filteredActions.map((action) => (
                <UnstyledButton
                  key={action.id}
                  onClick={() => action.onClick()}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '12px',
                    background: 'var(--mantine-color-dark-6)',
                  }}
                >
                  <Group align="flex-start" gap="md">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {action.leftSection}
                    </div>
                    <Stack gap={4} style={{ flex: 1 }}>
                      <Text size="sm" fw={600}>
                        {action.label}
                      </Text>
                      {action.description && (
                        <Text size="xs" c="dimmed">
                          {action.description}
                        </Text>
                      )}
                    </Stack>
                  </Group>
                </UnstyledButton>
              ))
            )}
          </Stack>
        </ScrollArea>
      </Stack>
    </Modal>
  );
}
