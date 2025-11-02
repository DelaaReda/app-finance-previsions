// webapp/src/components/news/NewsFilters.tsx
import { useState } from "react";
import { NewsFilters } from "@/hooks/useNews";

export default function NewsFilters({ value, onChange }: { value: NewsFilters; onChange: (v: NewsFilters) => void }) {
  const [local, setLocal] = useState<NewsFilters>(value);
  const commit = () => onChange(local);

  return (
    <div className="flex flex-wrap gap-2 items-end mb-3">
      <div className="flex flex-col">
        <label className="text-xs">Ticker</label>
        <input aria-label="Ticker" className="border rounded px-2 py-1" placeholder="AAPL"
               value={local.ticker ?? ""} onChange={e => setLocal({ ...local, ticker: e.target.value })} />
      </div>
      <div className="flex flex-col">
        <label className="text-xs">Mot-clé</label>
        <input aria-label="Keyword" className="border rounded px-2 py-1" placeholder="AI"
               value={local.q ?? ""} onChange={e => setLocal({ ...local, q: e.target.value })} />
      </div>
      <div className="flex flex-col">
        <label className="text-xs">Début</label>
        <input aria-label="Start" type="date" className="border rounded px-2 py-1"
               value={local.start ?? ""} onChange={e => setLocal({ ...local, start: e.target.value })} />
      </div>
      <div className="flex flex-col">
        <label className="text-xs">Fin</label>
        <input aria-label="End" type="date" className="border rounded px-2 py-1"
               value={local.end ?? ""} onChange={e => setLocal({ ...local, end: e.target.value })} />
      </div>
      <button onClick={commit} className="px-3 py-2 rounded bg-black text-white">Filtrer</button>
    </div>
  );
}
