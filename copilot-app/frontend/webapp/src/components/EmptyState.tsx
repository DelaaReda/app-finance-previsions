/**
 * EmptyState component - Never crash on empty data
 * Task: FC-UI-HELPERS-001
 */
import { Box, Typography } from '@mui/material';
import { InboxOutlined } from '@mui/icons-material';

interface EmptyStateProps {
  title?: string;
  subtitle?: string;
}

export function EmptyState({
  title = "No data available",
  subtitle = "Data will appear here once available"
}: EmptyStateProps) {
  return (
    <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight={300} p={4}>
      <InboxOutlined sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
      <Typography variant="h6" color="text.secondary">{title}</Typography>
      <Typography variant="body2" color="text.disabled">{subtitle}</Typography>
    </Box>
  );
}
