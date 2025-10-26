import inspect
from dash import html
from src.dash_app.pages import news, deep_dive


def _find_ids(component):
    """Recursively collect ids from Dash component tree (simple heuristic)."""
    ids = set()

    def _walk(obj):
        if hasattr(obj, 'id') and getattr(obj, 'id') is not None:
            ids.add(getattr(obj, 'id'))
        # children
        children = getattr(obj, 'children', None)
        if children is None:
            return
        if isinstance(children, (list, tuple)):
            for c in children:
                _walk(c)
        else:
            _walk(children)

    _walk(component)
    return ids


def test_news_layout_has_table_id():
    comp = news.layout()
    ids = _find_ids(comp)
    assert 'news-table' in ids


def test_deep_dive_layout_has_content_id():
    comp = deep_dive.layout()
    ids = _find_ids(comp)
    assert 'deep-dive-content' in ids
