# API Endpoint Best Practices (Reference)

## Objectif
Standardiser tous les endpoints avec le même niveau de qualité que les endpoints robustes du projet (cache, fallback, payload utile, contrat stable).

## Contrat de réponse (non négociable)
- Toujours renvoyer une structure stable:
  - `{ "ok": true, "data": { ... } }`
- Même en cas d'erreur interne, respecter un payload `data` exploitable (never-empty contract).
- Inclure les métadonnées minimales:
  - `generated_at`
  - `source`
  - `freshness` et/ou `last_update`
  - `filters_applied`
  - `stats`
  - `warnings` (liste)

## Performance et cache
- Utiliser une clé de cache déterministe (namespace + paramètres triés).
- Configurer le TTL par variable d'environnement (pas hardcodé).
- Exposer dans la réponse:
  - `cache.hit`
  - `cache.age_seconds`
  - `cache.ttl_seconds`
- Gérer l'éviction (`max entries`) pour éviter la croissance mémoire non bornée.

## Données utiles (pas juste "ça répond")
- Appliquer réellement les filtres déclarés (`since`, `score_min`, `tickers`, etc.).
- Normaliser les entrées:
  - tickers en uppercase
  - dates en UTC ISO
  - scores en float
- Normaliser les sorties:
  - champs cohérents entre endpoints comparables
  - compatibilité legacy maintenue si nécessaire (`items` + `articles`, etc.).
- Fournir des `stats` orientées usage:
  - volumes avant/après filtre
  - couverture (tickers/sources)
  - qualité (avg score, latest timestamp, erreurs partielles)

## Fallback robuste (never-empty)
- En cas d'exception:
  - ne pas renvoyer une structure cassée,
  - renvoyer une structure vide mais valide,
  - inclure `error` + `message` + `source` explicite (`*_fallback`).
- En cas de données partielles:
  - renvoyer le partiel disponible,
  - ajouter un warning (`partial_data_*`).

## Observabilité
- Ajouter des tags source traçables:
  - ex: `endpoint_route`, `*_snapshot`, `*_live`, `*_cache_hit`, `*_fallback`.
- Logger les erreurs avec contexte utile (paramètres clés), sans fuite de secrets.
- Garder les messages de warning compréhensibles et actionnables.

## Tests minimum requis
- Test de contrat endpoint:
  - structure stable (`ok`, `data`, champs critiques),
  - types attendus (`items` list, `stats` dict, etc.).
- Test de cache:
  - 2e appel même params => `cache.hit == true`.
- Test de fallback:
  - erreur simulée => payload never-empty conforme.
- Toujours exécuter la gate backend:
  - `./scripts/backend_regression_gate.sh --no-live`
  - `./scripts/backend_regression_gate.sh` (si backend up)

## Template d'implémentation (copier/coller)
```python
@app.get("/api/example")
async def example_endpoint(param: str = Query("default")):
    now_iso = _utc_now_iso()
    filters_applied = {"param": param}
    cache_key = _response_cache_key("example_v1", {"param": param})

    cached = _response_cache_get(
        _EXAMPLE_RESPONSE_CACHE,
        cache_key,
        EXAMPLE_CACHE_TTL_SECONDS,
        "example_cache_hit",
    )
    if cached:
        return _ok(cached)

    try:
        data = compute_data(param)
        payload = {
            "items": data,
            "count": len(data),
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": ["example_route"],
            "filters_applied": filters_applied,
            "stats": {"returned_count": len(data)},
            "warnings": [],
        }
        _response_cache_set(_EXAMPLE_RESPONSE_CACHE, cache_key, payload)
        return _ok(payload)
    except Exception as e:
        return _ok({
            "items": [],
            "count": 0,
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": ["example_route", "critical_error_fallback"],
            "filters_applied": filters_applied,
            "stats": {"returned_count": 0},
            "warnings": [],
            "error": str(e),
            "message": "example endpoint fallback (never-empty contract).",
        })
```

## Définition de Done endpoint
- Contrat stable validé.
- Cache + fallback validés.
- Données utiles (filtres réels + stats exploitables).
- Tests endpoint ajoutés/mis à jour.
- Gate régression backend `PASS`.

## Exemple projet (référence actuelle)
- Endpoint `stocks/prices`: cache TTL + fallback partiel + stats + warnings.
- Endpoint `news/feed`: filtres réels (`since`, `score_min`, `tickers`) + cache + stats de qualité.
