import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Menu, 
  X, 
  Search, 
  Bell, 
  User, 
  Settings, 
  LogOut,
  ChevronDown,
  Sun,
  Moon,
  Activity,
  TrendingUp,
  DollarSign
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';

export interface HeaderProps {
  onToggleSidebar: () => void;
  isSidebarOpen: boolean;
}

const Header: React.FC<HeaderProps> = ({ onToggleSidebar, isSidebarOpen }) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);

  const notifications = [
    {
      id: 1,
      type: 'success',
      title: 'Portfolio Update',
      message: 'Your portfolio has gained 2.3% this week',
      time: '2 hours ago',
      icon: <TrendingUp className="w-4 h-4" />,
    },
    {
      id: 2,
      type: 'warning',
      title: 'Market Alert',
      message: 'High volatility detected in tech stocks',
      time: '4 hours ago',
      icon: <Activity className="w-4 h-4" />,
    },
    {
      id: 3,
      type: 'info',
      title: 'New Feature',
      message: 'Advanced forecasting tools now available',
      time: '1 day ago',
      icon: <DollarSign className="w-4 h-4" />,
    },
  ];

  const userMenuItems = [
    { label: 'Profile', icon: <User className="w-4 h-4" />, action: () => {} },
    { label: 'Settings', icon: <Settings className="w-4 h-4" />, action: () => {} },
    { label: 'Sign Out', icon: <LogOut className="w-4 h-4" />, action: () => {} },
  ];

  return (
    <header className="bg-surface border-b border-border sticky top-0 z-50">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left Section */}
        <div className="flex items-center gap-4">
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-2 rounded-lg hover:bg-surface-elevated transition-colors"
          >
            {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          
          <div className="hidden lg:flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold gradient-text">FinanceHub</h1>
          </div>
        </div>

        {/* Center Section - Search */}
        <div className="flex-1 max-w-md mx-8">
          <AnimatePresence>
            {isSearchOpen ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="relative"
              >
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-muted" />
                <input
                  type="text"
                  placeholder="Search markets, stocks, forecasts..."
                  className="w-full pl-10 pr-10 py-2 bg-surface-elevated border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-primary"
                  autoFocus
                />
                <button
                  onClick={() => setIsSearchOpen(false)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 hover:bg-surface rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            ) : (
              <button
                onClick={() => setIsSearchOpen(true)}
                className="w-full flex items-center gap-3 px-4 py-2 bg-surface-elevated border border-border rounded-lg text-muted hover:text-text transition-colors"
              >
                <Search className="w-5 h-5" />
                <span className="text-left">Search...</span>
              </button>
            )}
          </AnimatePresence>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-3">
          {/* Theme Toggle */}
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-2 rounded-lg hover:bg-surface-elevated transition-colors"
          >
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
              className="p-2 rounded-lg hover:bg-surface-elevated transition-colors relative"
            >
              <Bell className="w-5 h-5" />
              {notifications.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-danger rounded-full" />
              )}
            </button>

            <AnimatePresence>
              {isNotificationsOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 mt-2 w-80 bg-surface border border-border rounded-lg shadow-xl z-50"
                >
                  <div className="p-4 border-b border-border">
                    <h3 className="font-semibold text-text">Notifications</h3>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className="p-4 border-b border-border hover:bg-surface-elevated transition-colors cursor-pointer"
                      >
                        <div className="flex items-start gap-3">
                          <div className={cn(
                            'w-8 h-8 rounded-lg flex items-center justify-center',
                            notification.type === 'success' && 'bg-success/10 text-success',
                            notification.type === 'warning' && 'bg-warning/10 text-warning',
                            notification.type === 'info' && 'bg-primary/10 text-primary'
                          )}>
                            {notification.icon}
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium text-text">{notification.title}</h4>
                            <p className="text-sm text-muted mt-1">{notification.message}</p>
                            <p className="text-xs text-muted mt-2">{notification.time}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="p-4 border-t border-border">
                    <button className="w-full text-center text-primary hover:text-primary/80 transition-colors">
                      View all notifications
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 p-2 rounded-lg hover:bg-surface-elevated transition-colors"
            >
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
              <ChevronDown className={cn(
                'w-4 h-4 transition-transform',
                isUserMenuOpen && 'rotate-180'
              )} />
            </button>

            <AnimatePresence>
              {isUserMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 mt-2 w-56 bg-surface border border-border rounded-lg shadow-xl z-50"
                >
                  <div className="p-4 border-b border-border">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
                        <User className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-text">John Doe</h3>
                        <p className="text-sm text-muted">john.doe@example.com</p>
                      </div>
                    </div>
                  </div>
                  <div className="py-2">
                    {userMenuItems.map((item) => (
                      <button
                        key={item.label}
                        onClick={() => {
                          item.action();
                          setIsUserMenuOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-surface-elevated transition-colors"
                      >
                        {item.icon}
                        <span className="text-text">{item.label}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;