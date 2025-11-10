import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import Dashboard from '@/pages/Dashboard';
import Forecasts from '@/pages/Forecasts';
import { cn } from '@/lib/utils';

// Placeholder components for other routes
const PlaceholderPage: React.FC<{ title: string }> = ({ title }) => (
  <div className="min-h-screen bg-bg p-6">
    <div className="max-w-7xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center py-20"
      >
        <h1 className="text-4xl font-bold gradient-text mb-4">{title}</h1>
        <p className="text-muted text-lg">This page is under construction</p>
        <div className="mt-8 w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
          <div className="w-8 h-8 bg-primary rounded-full animate-pulse" />
        </div>
      </motion.div>
    </div>
  </div>
);

const App: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <Router>
      <div className="min-h-screen bg-bg">
        <Header 
          onToggleSidebar={toggleSidebar}
          isSidebarOpen={isSidebarOpen}
        />
        
        <div className="flex">
          <Sidebar 
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
          />
          
          <main className={cn(
            'flex-1 transition-all duration-300',
            'lg:ml-72'
          )}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Navigate to="/" replace />} />
              <Route path="/forecasts" element={<Forecasts />} />
              <Route path="/portfolios" element={<PlaceholderPage title="Portfolio Management" />} />
              <Route path="/stocks" element={<PlaceholderPage title="Market Analysis" />} />
              <Route path="/analytics" element={<PlaceholderPage title="Advanced Analytics" />} />
              <Route path="/news" element={<PlaceholderPage title="News & Insights" />} />
              <Route path="/macro" element={<PlaceholderPage title="Macro Economics" />} />
              <Route path="/reports" element={<PlaceholderPage title="Financial Reports" />} />
              <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
              <Route path="/help" element={<PlaceholderPage title="Help & Support" />} />
              
              {/* Catch all route */}
              <Route path="*" element={<PlaceholderPage title="Page Not Found" />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  );
};

export default App;