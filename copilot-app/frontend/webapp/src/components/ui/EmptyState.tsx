import { Box, Typography } from '@mui/material';

interface EmptyStateProps {
  title?: string;
  hint?: string;
}

export default function EmptyState({ title = 'Aucune donnée', hint }: EmptyStateProps) {
  return (
    <Box sx={{ textAlign: 'center', py: 6, opacity: 0.8 }}>
      <Typography variant="h6">{title}</Typography>
      {hint && <Typography variant="body2" sx={{ mt: 1 }}>{hint}</Typography>}
    </Box>
  );
}