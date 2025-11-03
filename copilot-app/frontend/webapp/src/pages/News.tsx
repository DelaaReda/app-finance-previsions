// webapp/src/pages/News.tsx
import NewsFeed from "@/components/news/NewsFeed";

export default function NewsPage() {
  return (
    <main className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-3">Actualités Financières</h1>
      <p className="text-sm text-gray-600 mb-4">
        Actualités financières avec score de pertinence, triées par date de publication.
      </p>
      <NewsFeed />
    </main>
  );
}
