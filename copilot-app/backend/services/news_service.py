def compute_news_feed():
    # TODO: remplacer par l'ingest réelle RSS (P1)
    return {"articles": []}

def get_news_feed(cache):
    return cache("news_feed", compute_news_feed, source=["bootstrap"])