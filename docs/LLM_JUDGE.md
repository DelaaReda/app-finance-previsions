# LLM Judge Playbook

Cette note décrit comment exploiter `/api/llm/judge/run` pour injecter du raisonnement LLM (DeepSeek/Qwen/etc.) partout dans Finance Copilot. Elle couvre la collecte des données, la sélection des modèles, les paramètres d’environnement et l’intégration front/back.

---

## 1. Vue d’ensemble

Le juge assemble **3 briques** :

1. **Données déterministes** : forecasts hybrides (ML + signaux) + résumés derived (`_derive`).
2. **Pipeline LLM** : agent `EconomicAnalyst` (g4f) qui interroge les meilleurs modèles reasoning.
3. **Watcher G4F** : job `g4f_model_watcher` qui mesure en continu quels modèles répondent vite et écrit `data/llm/models/working.json`.

Quand l’endpoint est appelé :

```
- forecasts (SPY/QQQ/…) -> derived stats + context chunks
- ensemble LLM (DeepSeek, Qwen, GLM) -> réponses + adjudication
- réponse JSON avec `stdout`, `rows`, `debug`
```

---

## 2. API `/api/llm/judge/run`

### Requête

```bash
curl -X POST http://localhost:8050/api/llm/judge/run \
     -H "Content-Type: application/json" \
     -d '{
           "model": "deepseek-ai/DeepSeek-V3-0324-Turbo",
           "max_er": 0.08,
           "min_conf": 0.6,
           "tickers": "AAPL,MSFT,NGD.TO"
         }'
```

- `model` : ordre de priorité (le juge reformule la liste dynamique).  
- `tickers` : optionnel. Les placeholders (`string/ticker/example`) sont ignorés → fallback sur `SPY, QQQ, …`.
- `max_er`,`min_conf` : bornes pour filtrer les signaux haute confiance.

### Réponse (structure clef)

```jsonc
{
  "ok": true,
  "data": {
    "stdout": { "context": "...", "forecast": "..." },
    "rows": [...],                // toutes les prévisions
    "derived": { "top_buys": [...], "top_risks": [...], "stats": {...} },
    "debug": {
      "models": [
        { "model": "...", "provider": "g4f", "latency_ms": 35124,
          "ok": true, "answer": "...", "parsed": {...} },
        ...
      ],
      "adjudication": {...},
      "context": {
        "tickers": [...],
        "deterministic_summary": "...",
        "attachments_preview": [...]
      }
    }
  }
}
```

Utilisez `debug.models` pour comprendre quels providers répondent et leurs latences. `rows` et `derived` peuvent être réinjectés sur d’autres pages (brief, dashboards, alerts).

---

## 3. Config & performances

### Variables d’environnement

| Variable | Rôle |
|----------|------|
| `ECON_AGENT_TIMEOUT` (défaut `30`) | Timeout g4f par essai (secs) |
| `ECON_AGENT_MODELS` | Liste fixe de modèles prioritaires (ex: `deepseek-ai/DeepSeek-V3-0324-Turbo,deepseek-ai/DeepSeek-V3`) |
| `ECON_AGENT_DYNAMIC_MODELS` (1/0) | Autoriser ou non la fusion avec `working.json` |
| `G4F_WATCHER_INTERVAL_MINUTES` | Lance automatiquement le radar g4f via le scheduler (`120` par défaut) |
| `G4F_WATCHER_LIMIT` | Nombre de modèles testés à chaque run |
| `G4F_WATCHER_REFRESH_VERIFIED` | Utiliser les modèles “verified” (maruf009sultan) avant les officiels |

### Scheduler

- Le job `g4f_watcher_job` tourne via `backend/scheduler/app.py`.  
- On peut forcer un scan manuel : `python -m src.agents.g4f_model_watcher --refresh --limit 12`.  
- Les résultats sont loggés dans `storage` (`job_g4f_watcher*.json`) pour audit.

### Conseils pour un juge rapide

1. **Limiter la liste** : 2–3 modèles reasoning stables en tête (`ECON_AGENT_MODELS`) + watcher pour les backfills.  
2. **Timeout ≤30s** : pour éviter qu’un provider “noir” bloque toute la route.  
3. **Debug UI** : `/judge` affiche la latence et le provider en temps réel → idéal pour diagnostiquer les providers défaillants.

---

## 4. Intégration front/back

### Frontend

- Page : `copilot-app/frontend/webapp/src/pages/LLMJudge.tsx`.  
- Le bouton “Run” poste sur l’endpoint et affiche :
  - `stdout` (verdict final)
  - Progress/timeouts
  - `debug.models` détaillé (accordion)
  - Contexte (résumé déterministe, features, attachments)
- Timeout UI : 60s (`apiPost(..., { timeoutMs: 60000 })`). à ajuster selon vos besoins.

### Backend réutilisable

Pour intégrer le juge dans un autre service (alerts, dashboards, etc.) :

```python
from storage.io import load_json
import requests

payload = {"model": "deepseek-ai/DeepSeek-V3", "tickers": "AAPL,MSFT"}
r = requests.post("http://localhost:8050/api/llm/judge/run", json=payload, timeout=120)
data = r.json()["data"]
forecast_text = data["stdout"]["forecast"]
model_runs = data["debug"]["models"]
```

- On peut fusionner `rows` avec des KPIs, envoyer `forecast_text` dans des notifications, etc.  
- Pour des appels offline, pensez à déclencher le watcher juste avant (afin de disposer d’une liste fraîche).

---

## 5. Checklist pour ajouter du raisonnement ailleurs

1. ✅ Vérifier que `finance-copilot.sh start` tourne (backend + scheduler).  
2. ✅ S’assurer que `data/llm/models/working.json` est à jour (job `g4f_watcher`).  
3. ✅ Appeler `/api/llm/judge/run` depuis votre feature (même payload que décrit ci-dessus).  
4. ✅ Exploiter `stdout`, `derived`, `debug` selon votre besoin (UI, alertes, logs).  
5. ✅ Monitorer `api.log` + `job_g4f_watcher` pour détecter les modèles lents/inaccessibles.  

En suivant ces étapes, tout nouvel agent peut brancher le juge dans une page, un workflow d’alerte ou un script offline en bénéficiant des meilleurs modèles reasoning disponibles gratuitement (DeepSeek/Qwen/GLM).  
Gardez le watcher activé pour garder une latence prévisible et mettez à jour `ECON_AGENT_MODELS` si vous constatez de nouveaux modèles plus pertinents dans `working_results.txt`.
