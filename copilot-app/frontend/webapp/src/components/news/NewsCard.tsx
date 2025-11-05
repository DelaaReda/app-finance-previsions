// webapp/src/components/news/NewsCard.tsx
import { NewsItem } from "@/types/news.types";
import { Card, CardContent, Typography, Chip, Link, Box, Stack } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

export default function NewsCard({ item }: { item: NewsItem }) {
  const d = new Date(item.published_at);

  // Sentiment color and icon
  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0) return 'success';
    if (sentiment < 0) return 'error';
    return 'default';
  };

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0) return <TrendingUp fontSize="small" />;
    if (sentiment < 0) return <TrendingDown fontSize="small" />;
    return null;
  };

  return (
    <Card
      data-testid="news-card"
      sx={{
        mb: 2,
        '&:hover': { bgcolor: 'action.hover' },
        transition: 'background-color 0.2s'
      }}
    >
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" mb={1}>
          {item.ticker && (
            <Chip
              label={item.ticker}
              size="small"
              sx={{ fontFamily: 'monospace' }}
            />
          )}
          <Typography variant="caption" color="text.secondary">
            {item.source}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            •
          </Typography>
          <Typography variant="caption" color="text.secondary" component="time" dateTime={item.published_at}>
            {d.toLocaleString()}
          </Typography>
          {typeof item.sentiment === "number" && (
            <Chip
              icon={getSentimentIcon(item.sentiment)}
              label={item.sentiment.toFixed(2)}
              size="small"
              color={getSentimentColor(item.sentiment)}
              variant="outlined"
            />
          )}
        </Stack>

        <Link
          href={item.url}
          target="_blank"
          rel="noreferrer"
          underline="hover"
          sx={{
            display: 'block',
            mb: 1,
            fontWeight: 600,
            fontSize: '1.1rem'
          }}
        >
          {item.title}
        </Link>

        {item.text && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
            }}
          >
            {item.text}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
