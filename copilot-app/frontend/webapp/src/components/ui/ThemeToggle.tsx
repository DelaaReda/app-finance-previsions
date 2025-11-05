import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { Brightness4 as DarkModeIcon, Brightness7 as LightModeIcon } from '@mui/icons-material';
import { useThemeMode } from '../../context/ThemeContext';

const ThemeToggle: React.FC = () => {
  const { mode, toggleMode } = useThemeMode();

  return (
    <Tooltip title={`Passer en mode ${mode === 'light' ? 'sombre' : 'clair'}`}>
      <IconButton 
        onClick={toggleMode}
        color="inherit"
        aria-label={`Basculer en mode ${mode === 'light' ? 'sombre' : 'clair'}`}
      >
        {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
      </IconButton>
    </Tooltip>
  );
};

export default ThemeToggle;