// webapp/src/components/news/NewsFeed.tsx
import NewsCard from "./NewsCard";
import { useNews } from "@/hooks/useNews";

export default function NewsFeed() {
  const { items, filters, setFilters, loading, error, hasMore, loadMore } = useNews();

  return (
    <section>
      {/* Filtres */}
      {/* @ts-ignore - simple import direct */}
      <div className="mb-4">
        {/* inline to avoid circular imports in junior setup */}
        {/* eslint-disable-next-line */}
        {require("./NewsFilters").default({ value: filters, onChange: setFilters })}
      </div>

      {/* États */}
      {error && <div role="alert" className="text-red-700">Erreur: {error}</div>}
      {loading && items.length === 0 && <div>Chargement…</div>}
      {items.length === 0 && !loading && <div>Aucune news</div>}

      {/* Liste */}
      {items.map(item => <NewsCard key={item.id} item={item} />)}

      {/* Pagination */}
      <div className="mt-4">
        {hasMore && (
          <button disabled={loading} onClick={loadMore} className="px-4 py-2 rounded border">
            {loading ? "Chargement…" : "Charger plus"}
          </button>
        )}
      </div>
    </section>
  );
}
