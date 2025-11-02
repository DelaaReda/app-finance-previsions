// webapp/src/services/news.service.ts
import { apiGet } from "@/api/client";
import { NewsFeedResponse } from "@/types/news.types";

export async function getNewsFeed(params: {
  ticker?: string; q?: string; start?: string; end?: string;
  page?: number; limit?: number;
}) {
  const p = { ...params };
  if (!p.limit) p.limit = 50;
  return apiGet<NewsFeedResponse>("/news/feed", p);
}

export async function getNewsFeaturesDaily(ticker: string) {
  return apiGet<Array<{ date: string; news_count: number; sent_mean: number; novelty?: number; tier1_share?: number; impact_proxy_mean?: number }>>(
    "/news/features/daily",
    { ticker }
  );
}
