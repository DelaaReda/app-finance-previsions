# 🔧 Fix: Data Generation Jobs Not Running

## 🚨 Problème Identifié

Les endpoints retournent des données vides car :
1. **Les jobs ne s'exécutent pas** - dépendances manquantes (pandas, yfinance, g4f)
2. **Les fichiers de données ne sont pas générés** - `data/forecasts.json` existe mais est vide/ancien
3. **Le scheduler ne peut pas exécuter les jobs** - erreurs d'import

## ✅ Solution

### 1. Installer les dépendances manquantes

```bash
cd copilot-app/backend
source .venv/bin/activate  # ou créer le venv si nécessaire
pip install pandas yfinance g4f apscheduler
```

Si le venv est corrompu :
```bash
cd copilot-app/backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pandas yfinance g4f
```

### 2. Exécuter manuellement le job de forecasts

```bash
cd copilot-app/backend
source .venv/bin/activate
python3 scripts/run_forecasts_job.py
```

Ou directement :
```bash
cd copilot-app/backend
source .venv/bin/activate
python3 -c "from jobs.forecasts import run_forecasts_job; run_forecasts_job(['SPY', 'QQQ', 'AAPL'])"
```

### 3. Vérifier que les données sont générées

```bash
cd copilot-app/backend
python3 -c "from storage.io import load_json; data = load_json('forecasts'); print('Rows:', len(data.get('rows', [])) if data else 0)"
```

### 4. Vérifier le scheduler

Le scheduler doit être démarré avec l'API. Vérifier dans `src/api/main.py` que le scheduler est initialisé au startup.

## 📋 Jobs à Vérifier

1. **Forecasts** (`jobs/forecasts.py`)
   - Génère `data/forecasts.json`
   - Dépend de: `pandas`, `yfinance`, `g4f`
   - Exécution: quotidienne à 2h AM ou manuelle

2. **News** (`jobs/news_ingest.py`)
   - Génère `data/news_feed.json`
   - Dépend de: `feedparser`, `requests`
   - Exécution: toutes les 15 minutes

3. **Market Brief** (`jobs/market_brief.py`)
   - Génère `data/brief_daily.json`
   - Dépend de: données forecasts + news
   - Exécution: quotidienne

4. **Weekly Brief** (`jobs/weekly_brief.py`)
   - Génère `data/brief_weekly.json`
   - Exécution: dimanche 23h30

## 🔍 Diagnostic

Pour vérifier l'état des jobs :

```bash
# Vérifier les fichiers de données
ls -lh data/*.json

# Vérifier les dépendances
python3 -c "import pandas, yfinance, g4f; print('✅ All dependencies installed')"

# Tester un job
python3 -c "from jobs.forecasts import run_forecasts_job; result = run_forecasts_job(['SPY']); print(result)"
```

## 🎯 Action Immédiate

1. Installer les dépendances manquantes
2. Exécuter `scripts/run_forecasts_job.py` pour générer les données
3. Vérifier que `data/forecasts.json` contient des données
4. Redémarrer l'API pour que le scheduler fonctionne

