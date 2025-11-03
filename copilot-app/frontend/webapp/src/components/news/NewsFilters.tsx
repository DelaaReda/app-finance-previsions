// webapp/src/components/news/NewsFilters.tsx
import { useState } from "react";
import type { NewsFilters as NewsFiltersType } from "@/hooks/useNews";

export default function NewsFilters({ value, onChange }: { value: NewsFiltersType; onChange: (v: NewsFiltersType) => void }) {
  const [local, setLocal] = useState<NewsFiltersType>(value);
  const commit = () => onChange(local);

  return (
    <div className="flex flex-wrap gap-2 items-end mb-3">
      <div className="flex flex-col">
        <label className="text-xs">Tickers (séparés par des virgules)</label>
        <input aria-label="Ticker" className="border rounded px-2 py-1" placeholder="AAPL,NVDA"
               value={local.tickers ?? ""} onChange={e => setLocal({ ...local, tickers: e.target.value })} />
      </div>
      <div className="flex flex-col">
        <label className="text-xs">Depuis</label>
        <select className="border rounded px-2 py-1" value={local.since ?? "7d"} 
                onChange={e => setLocal({ ...local, since: e.target.value })}>
          <option value="1h">Dernière heure</option>
          <option value="6h">Dernières 6h</option>
          <option value="1d">Dernier jour</option>
          <option value="3d">3 derniers jours</option>
          <option value="7d">7 derniers jours</option>
          <option value="14d">14 derniers jours</option>
          <option value="30d">30 derniers jours</option>
          <option value="90d">90 derniers jours</option>
        </select>
      </div>
      <div className="flex flex-col">
        <label className="text-xs">Région</label>
        <select className="border rounded px-2 py-1" value={local.region ?? "all"} 
                onChange={e => setLocal({ ...local, region: e.target.value })}>
          <option value="all">Toutes</option>
          <option value="US">US</option>
          <option value="CA">Canada</option>
          <option value="EU">Europe</option>
          <option value="INTL">Internationale</option>
        </select>
      </div>
      <div className="flex flex-col">
        <label className="text-xs">Score min</label>
        <select className="border rounded px-2 py-1" value={local.score_min ?? 0.0} 
                onChange={e => setLocal({ ...local, score_min: parseFloat(e.target.value) })}>
          <option value="0.0">0.0 (tous)</option>
          <option value="0.3">0.3</option>
          <option value="0.5">0.5</option>
          <option value="0.7">0.7</option>
          <option value="0.9">0.9</option>
        </select>
      </div>
      <button onClick={commit} className="px-3 py-2 rounded bg-black text-white">Filtrer</button>
    </div>
  );
}
