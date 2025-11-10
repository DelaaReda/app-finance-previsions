import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, 
  TrendingUp, 
  PieChart, 
  Bell, 
  Settings,
  HelpCircle,
  ChevronRight,
  DollarSign,
  Activity,
  BarChart3,
  FileText,
  Target,
  Users,
  Calendar,
  Shield
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useLocation, useNavigate } from 'react-router-dom';

export interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;
  children?: NavItem[];
}

const navItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <LayoutDashboard className="w-5 h-5" />,
    path: '/',
  },
  {
    id: 'forecasts',
    label: 'Forecasts',
    icon: <TrendingUp className="w-5 h-5" />,
    path: '/forecasts',
    badge: 6,
  },
  {
    id: 'portfolio',
    label: 'Portfolio',
    icon: <PieChart className="w-5 h-5" />,
    path: '/portfolios',
  },
  {
    id: 'markets',
    label: 'Markets',
    icon: <Activity className="w-5 h-5" />,
    path: '/stocks',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: <BarChart3 className="w-5 h-5" />,
    path: '/analytics',
  },
  {
    id: 'news',
    label: 'News & Insights',
    icon: <Bell className="w-5 h-5" />,
    path: '/news',
    badge: 12,
  },
  {
    id: 'macro',
    label: 'Macro Economics',
    icon: <DollarSign className="w-5 h-5" />,
    path: '/macro',
  },
  {
    id: 'reports',
    label: 'Reports',
    icon: <FileText className="w-5 h-5" />,
    path: '/reports',
  },
];

const bottomNavItems: NavItem[] = [
  {
    id: 'settings',
    label: 'Settings',
    icon: <Settings className="w-5 h-5" />,
    path: '/settings',
  },
  {
    id: 'help',
    label: 'Help & Support',
    icon: <HelpCircle className="w-5 h-5" />,
    path: '/help',
  },
];

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const isActive = (path: string) => {
    return location.pathname === path || (path === '/' && location.pathname === '/dashboard');
  };

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const handleNavClick = (item: NavItem) => {
    if (item.children && item.children.length > 0) {
      toggleExpanded(item.id);
    } else {
      navigate(item.path);
      onClose();
    }
  };

  const renderNavItem = (item: NavItem, isSubItem = false) => {
    const active = isActive(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.has(item.id);

    return (
      <div key={item.id} className="relative">
        <button
          onClick={() => handleNavClick(item)}
          className={cn(
            'w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all duration-200',
            isSubItem && 'pl-12',
            active
              ? 'bg-primary text-white shadow-lg'
              : 'text-muted hover:bg-surface-elevated hover:text-text',
            'group'
          )}
        >
          <div className="flex items-center gap-3">
            <div className={cn(
              'transition-colors',
              active ? 'text-white' : 'text-muted group-hover:text-text'
            )}>
              {item.icon}
            </div>
            <span className="font-medium">{item.label}</span>
          </div>
          
          <div className="flex items-center gap-2">
            {item.badge && (
              <span className={cn(
                'px-2 py-0.5 text-xs font-medium rounded-full',
                active ? 'bg-white/20 text-white' : 'bg-primary text-white'
              )}>
                {item.badge}
              </span>
            )}
            {hasChildren && (
              <ChevronRight className={cn(
                'w-4 h-4 transition-transform duration-200',
                isExpanded && 'rotate-90'
              )} />
            )}
          </div>
        </button>

        {hasChildren && (
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-1 space-y-1 overflow-hidden"
              >
                {item.children?.map((child) => renderNavItem(child, true))}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Overlay for mobile */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.div
        initial={{ x: '-100%' }}
        animate={{ x: isOpen ? 0 : '-100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className={cn(
          'fixed left-0 top-0 h-full w-72 bg-surface border-r border-border z-50',
          'lg:translate-x-0 lg:sticky lg:flex lg:flex-col'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold gradient-text">FinanceHub</h2>
              <p className="text-xs text-muted">Pro Edition</p>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-lg hover:bg-surface-elevated transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {navItems.map((item) => renderNavItem(item))}
          </div>
        </div>

        {/* Bottom Navigation */}
        <div className="border-t border-border p-4">
          <div className="space-y-2">
            {bottomNavItems.map((item) => renderNavItem(item))}
          </div>
          
          {/* User Profile */}
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-elevated transition-colors cursor-pointer">
              <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-text">John Doe</h3>
                <p className="text-xs text-muted">Premium User</p>
              </div>
              <ChevronRight className="w-4 h-4 text-muted" />
            </div>
          </div>
        </div>
      </motion.div>
    </>
  );
};

export default Sidebar;