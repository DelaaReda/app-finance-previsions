// Guard for NewsFeed.tsx
type NewsPayload = {
  last_update?: string;
  status?: string;
  data: { articles: any[] };
};

export function NewsFeedGuard({ payload }: { payload: NewsPayload }) {
  const articles = payload?.data?.articles ?? [];
  if (!articles.length) {
    return <div className='text-sm text-amber-600'>Aucun article disponible. Ingestion en cours…</div>;
  }
  return <div>{articles.length} articles</div>;
}
