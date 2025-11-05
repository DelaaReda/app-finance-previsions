import React from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';

interface EmptyStateMuiProps {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  showAction?: boolean;
}

const EmptyStateMui: React.FC<EmptyStateMuiProps> = ({
  title = 'Aucune donnée disponible',
  message = 'Aucun élément à afficher pour le moment.',
  icon,
  action,
  showAction = true
}) => {
  return (
    <Paper 
      elevation={0} 
      sx={{ 
        p: 4, 
        textAlign: 'center', 
        border: '1px dashed',
        borderColor: 'divider',
        borderRadius: 2,
        backgroundColor: 'background.default'
      }}
    >
      {icon && (
        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
          {icon}
        </Box>
      )}
      <Typography variant="h6" component="h3" gutterBottom>
        {title}
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        {message}
      </Typography>
      {showAction && action && (
        <Button
          variant="outlined"
          color="primary"
          startIcon={<RefreshIcon />}
          onClick={action.onClick}
        >
          {action.label}
        </Button>
      )}
    </Paper>
  );
};

export default EmptyStateMui;