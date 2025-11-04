from storage.io import load_json, save_json

def load_or_compute(key: str, compute_fn, source: list = None):
    snap = load_json(key)
    if snap and snap.get("payload") is not None:
        return snap
    data = compute_fn()
    return save_json(key, data, source=source)