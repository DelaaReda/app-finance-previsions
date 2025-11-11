/**
 * useCommandPalette Hook
 * 
 * Manages command palette state and keyboard shortcuts.
 * Opens palette with Ctrl+K / Cmd+K.
 * 
 * Author: ELENA-39
 * Task: FC-UX-001
 */

import { useState, useEffect, useCallback } from 'react';

export function useCommandPalette() {
  const [opened, setOpened] = useState(false);
  
  const open = useCallback(() => setOpened(true), []);
  const close = useCallback(() => setOpened(false), []);
  const toggle = useCallback(() => setOpened((prev) => !prev), []);
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+K or Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggle();
      }
      
      // Escape to close
      if (e.key === 'Escape' && opened) {
        e.preventDefault();
        close();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [opened, toggle, close]);
  
  return {
    opened,
    open,
    close,
    toggle,
  };
}
