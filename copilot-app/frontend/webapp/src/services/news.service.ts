// webapp/src/services/news.service.ts
import { apiGet } from "@/api/client";
import { NewsFeedResponse } from "@/types/news.types";

export async function getNewsFeed(params: {
  tickers?: string[]; since?: string; region?: string; score_min?: number;
  page?: number; limit?: number;
}) {
  const p = { ...params };
  if (!p.limit) p.limit = 50;
  // Backend validation requires limit <= 200
  if (p.limit && p.limit > 200) p.limit = 200;
  return apiGet<NewsFeedResponse>("/api/news/feed", p);
}

export async function getNewsFeaturesDaily(ticker: string) {
  return apiGet<Array<{ date: string; news_count: number; sent_mean: number; novelty?: number; tier1_share?: number; impact_proxy_mean?: number }>>(
    "/api/news/features/daily",
    { ticker }
  );
}
