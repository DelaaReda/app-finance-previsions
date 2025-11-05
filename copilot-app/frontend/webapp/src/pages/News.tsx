// webapp/src/pages/News.tsx
import React from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Skeleton from '@mui/material/Skeleton';
import NewsFeed from '@/components/news/NewsFeed';

export default function NewsPage() {
  return (
    <Container maxWidth="md" sx={{ py: 3 }}>
      <Stack spacing={1} sx={{ mb: 2 }}>
        <Typography variant="h4" component="h1">Actualités Financières</Typography>
        <Typography variant="body2" color="text.secondary">
          Actualités financières avec score de pertinence, triées par date de publication.
        </Typography>
      </Stack>

      {/* NewsFeed handles its own loading / empty / error states. We keep a small skeleton as fallback. */}
      <React.Suspense fallback={<Skeleton variant="rectangular" height={220} />}> 
        <NewsFeed />
      </React.Suspense>
    </Container>
  );
}
