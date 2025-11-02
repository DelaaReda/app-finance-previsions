// webapp/src/components/news/NewsFeed.tsx
import React, { Suspense } from "react";
import NewsCard from "./NewsCard";
import { useNews } from "@/hooks/useNews";
const NewsFilters = React.lazy(() => import("./NewsFilters"));

export default function NewsFeed() {
  const { items, filters, setFilters, loading, error, hasMore, loadMore } = useNews();

  return (
    <section>
      {/* Filtres */}
      <div className="mb-4">
        <Suspense fallback={null}>
          <NewsFilters value={filters} onChange={setFilters} />
        </Suspense>
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
