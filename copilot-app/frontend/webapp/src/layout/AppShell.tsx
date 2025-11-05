import React, { useState } from 'react';
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Divider,
  useTheme,
  useMediaQuery,
  Stack
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
  Newspaper as NewsIcon,
  Description as DescriptionIcon,
  Science as ScienceIcon,
  Public as PublicIcon,
  ShowChart as ShowChartIcon,
  Chat as ChatIcon
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { HealthStatusBadge } from '../components/ui/HealthStatusBadge';

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/', icon: <DashboardIcon /> },
  { label: 'Brief', to: '/brief', icon: <DescriptionIcon /> },
  { label: 'Macro', to: '/macro', icon: <PublicIcon /> },
  { label: 'Actions', to: '/stocks', icon: <ShowChartIcon /> },
  { label: 'News', to: '/news', icon: <NewsIcon /> },
  { label: 'Copilot', to: '/copilot', icon: <ChatIcon /> },
  { label: 'Prévisions', to: '/forecasts', icon: <TrendingUpIcon /> },
  { label: 'Backtests', to: '/backtests', icon: <AssessmentIcon /> },
  { label: 'LLM Judge', to: '/judge', icon: <ScienceIcon /> },
];

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
}

export default function AppShell({ children, title = 'Finance Copilot' }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const drawer = (
    <Box onClick={() => isMobile && setMobileOpen(false)}>
      <Box sx={{ textAlign: 'center', py: 2 }}>
        <Typography variant="h6" fontWeight={700}>
          💼 {title}
        </Typography>
      </Box>
      <Divider />
      <List>
        {navItems.map((item) => (
          <ListItemButton
            key={item.to}
            selected={location.pathname === item.to}
            onClick={() => navigate(item.to)}
            sx={{
              '&.Mui-selected': {
                backgroundColor: 'primary.main',
                color: 'primary.contrastText',
                '&:hover': {
                  backgroundColor: 'primary.dark',
                },
                '& .MuiListItemIcon-root': {
                  color: 'primary.contrastText',
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* AppBar */}
  <AppBar position="fixed" sx={{ zIndex: (theme: any) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {title}
          </Typography>
          {/* Health Status Indicator in Header */}
          <Stack direction="row" spacing={1} alignItems="center">
            <HealthStatusBadge />
          </Stack>
        </Toolbar>
      </AppBar>

      {/* Mobile drawer */}
      <Box
        component="nav"
        sx={{ width: { md: 240 }, flexShrink: { md: 0 } }}
        aria-label="navigation"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 },
          }}
        >
          {drawer}
        </Drawer>
        
        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240, pt: 8 },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main content */}
      <Box component="main" sx={{ flexGrow: 1, mt: 8, ml: { md: '240px' }, width: '100%' }}>
        {children}
      </Box>
    </Box>
  );
}