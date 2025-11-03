# Drop-in Pack — Finance Copilot

Ce dossier contient des **fichiers prêts à déposer** dans ton repo pour activer :
- persistance + cache snapshot
- jobs de calcul en arrière-plan
- endpoints “never-empty”
- templates d’issues & PR
- garde-fous UI

## Où déposer ?

```
repo-root/
├── backend/
│   ├── storage/base.py
│   ├── services/cache_layer.py
│   ├── services/compute_runner.py
│   ├── scheduler/schedule.py
│   └── jobs/
│       ├── job_forecasts.py
│       ├── job_news.py
│       ├── job_weekly_brief.py
│       └── job_backtests.py
├── api/routes/forecasts.py
├── frontend/snippets/
│   ├── Forecasts_guard.tsx
│   ├── NewsFeed_guard.tsx
│   └── api_client.ts
└── .github/
    ├── ISSUE_TEMPLATE.md
    └── PULL_REQUEST_TEMPLATE.md
```

> Intègre ensuite les routes à FastAPI et le scheduler (ex: event startup).
> Côté UI, appelle les guards quand `payload.data` est vide au lieu de faire `.map` direct.
