from fastapi import APIRouter
from core.response import ok
from services.news_service import get_news_feed
from services.cache_layer import load_or_compute

router = APIRouter()

@router.get("/news/feed")
def news_feed():
    snap = get_news_feed(lambda key,fn,source=None: load_or_compute(key,fn,source))
    payload = snap["payload"]
    payload["freshness"] = snap["last_update"]
    payload["source"] = snap["source"]
    return ok(payload)