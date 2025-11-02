// webapp/src/components/news/NewsCard.tsx
import { NewsItem } from "@/types/news.types";

export default function NewsCard({ item }: { item: NewsItem }) {
  const d = new Date(item.published_at);
  return (
    <article data-testid="news-card" className="border rounded-lg p-3 mb-3 hover:bg-neutral-50">
      <div className="text-sm text-neutral-500 flex gap-2">
        {item.ticker && <span className="font-mono px-2 py-0.5 rounded bg-neutral-200">{item.ticker}</span>}
        <span>{item.source}</span>
        <span>•</span>
        <time dateTime={item.published_at}>{d.toLocaleString()}</time>
        {typeof item.sentiment === "number" && (
          <span className={item.sentiment > 0 ? "text-green-600" : item.sentiment < 0 ? "text-red-600" : "text-neutral-600"}>
            {item.sentiment.toFixed(2)}
          </span>
        )}
      </div>
      <a href={item.url} target="_blank" rel="noreferrer" className="block mt-1 text-lg font-semibold text-blue-700 underline">
        {item.title}
      </a>
      {item.text && <p className="mt-1 text-sm text-neutral-700 line-clamp-3">{item.text}</p>}
    </article>
  );
}
