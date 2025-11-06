/**
 * Command Palette Component
 * 
 * Global command palette for navigation, search, and actions.
 * Activated with Ctrl+K / Cmd+K.
 * 
 * Author: ELENA-39
 * Task: FC-UX-001
 */

import { Spotlight, type SpotlightActionData } from '@mantine/spotlight';
import { 
  IconDashboard, IconChartLine, IconNews, IconChartCandle, 
  IconRefresh, IconMoon, IconSun, IconDownload, IconAlertTriangle,
  IconBriefcase, IconMacro, IconRocket, IconNetwork, IconSearch
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useDrillDown } from '../../contexts/DrillDownContext';
import { useForecasts } from '../../hooks/useForecasts';
import { useMemo } from 'react';

interface CommandPaletteProps {
  opened: boolean;
  close: () => void;
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
  
  // Build dynamic command list
  const actions = useMemo<SpotlightActionData[]>(() => {
    const commands: SpotlightActionData[] = [];
    
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
  }, [navigate, navigateToTicker, forecasts, close]);
  
  return (
    <Spotlight
      actions={actions}
      opened={opened}
      onClose={close}
      searchProps={{
        leftSection: <IconSearch size={20} />,
        placeholder: 'Search pages, tickers, actions...',
      }}
      nothingFound="Nothing found..."
      highlightQuery
      limit={10}
      shortcut={['mod + K']}
    />
  );
}
