// webapp/src/pages/News.tsx
import NewsFeed from "@/components/news/NewsFeed";

export default function NewsPage() {
  return (
    <main className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-3">News</h1>
      <NewsFeed />
    </main>
  );
}
