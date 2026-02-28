# API Endpoint Best Practices (Reference)

## Objectif
Standardiser tous les endpoints avec le même niveau de qualité que les endpoints robustes du projet (cache, fallback, payload utile, contrat stable).

## Architecture (obligatoire)
- Les routes API sont des orchestrateurs:
  - validation des paramètres,
  - auth/permissions,
  - appel d'un service métier réutilisable,
  - mapping de réponse (`ok/data`) + fallback de dernier niveau.
- Toute logique métier (filtres, scoring, cache/single-flight, intégrations externes, LLM pipelines) doit vivre dans les modules métier du domaine.
- Les routes ne doivent pas contenir de logique métier longue.
- Utiliser le module standard de services pour éviter la duplication:
  - `apps/api/src/platform/legacy/services/service_standard.py`
  - helpers clés: `utc_now_iso`, `safe_int`, `safe_float`, `ensure_source_list`, `append_source_tag`, `unwrap_storage_payload`, `service_response`, `never_empty_payload`.

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

## Endpoints LLM (pattern Judge à copier)
Référence:
- route orchestrateur: `apps/api/src/domains/judge/api/judge.py`
- service endpoint: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- logique métier: `apps/api/src/domains/judge/application/judge_pipeline.py` + `apps/api/src/domains/judge/application/g4f_client.py`

Règles supplémentaires:
- Le service endpoint ne doit pas importer dynamiquement la route.
  - Pour les endpoints template volumineux (ex: verdict judge), la route passe explicitement une fonction de compute au service (`compute_verdicts_fn`) pour garder le découplage.
- Point d'entrée **canonique** pour tous les appels LLM backend:
  - `apps/api/src/domains/judge/application/g4f_client.call_llm(...)`
  - facade équivalente stable selon le contexte du module
  - modes supportés:
    - `mode="dev"`: modèles rapides + timeout court + peu d'essais
    - `mode="best"`: meilleur modèle testé + fallback chain complète
  - ne pas appeler les providers g4f directement dans les modules métier.
- Ajouter `debug=true` (query) qui:
  - désactive le cache,
  - expose `debug_pipeline` (traces) + `debug_payload` + `debug_llm_res` (jamais en nominal).
- Forcer un format de réponse LLM strict:
  - dernière ligne = JSON (une seule ligne),
  - validation Pydantic avant/après si possible,
  - parsing tolérant (dernière ligne puis extraction du plus gros bloc `{...}`).
- Multi-provider fallback (ordre recommandé):
  1. provider principal (ex: OpenRouter via agent)
  2. g4f no-auth via `apps/api/src/domains/judge/application/g4f_client.py` (`mode="best"` en prod)
  3. Codestral (`services/codestral_client.call_codestral`) si `CODESTRAL_API_KEY`
  4. Groq (`services/groq_client.call_groq`) si `GROQ_API_KEY`
  - exposer explicitement `fallback_used` et `model/provider` en debug.
- Ne jamais casser le contrat "never-empty": si le LLM échoue, retourner `data` vide mais valide + `error` + `source[]=*_fallback`.

## Template réutilisable (style Judge)
- Module template backend: `apps/api/src/platform/legacy/api/templates/judge_like_endpoint.py`
  - `stable_cache_key(...)`
  - `response_cache_get(...)`
  - `response_cache_set(...)`
  - `compute_singleflight(...)`
  - `append_source_tag(...)`
- Endpoint de référence template appliqué:
  - route orchestrateur: `apps/api/src/domains/forecasts/api/forecasts.py`
  - logique métier réutilisable: `apps/api/src/domains/forecasts/application/forecasts_service.py`

## Tests minimum requis
- Test de contrat endpoint:
  - structure stable (`ok`, `data`, champs critiques),
  - types attendus (`items` list, `stats` dict, etc.).
- Test de cache:
  - 2e appel même params => `cache.hit == true`.
- Test de fallback:
  - erreur simulée => payload never-empty conforme.
- Test de parité template:
  - OpenAPI doit exposer un schéma 200 non vide + enums stricts,
  - `debug=true` bypass cache et expose `debug_pipeline`,
  - single-flight doit exécuter 1 seul compute sur appels concurrents identiques.
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
