# App Finance Prévisions

> Un copilote financier personnel qui agrège macro, marchés, et actualités, les transforme en insights actionnables (CT/MT/LT), et permet d'interroger des LLM avec un contexte de données historisées (≥5 ans).


## 📚 Vision

**Objectif**

Offrir un poste d'observation complet (macro, actions, news) + un copilote LLM, pour passer du bruit au signal et soutenir des décisions court, moyen et long terme.

**Proposition de valeur**
- **Tout-en-un** : macro (FRED, indices, cycles), actions (prix, indicateurs), news (RSS/curation), Q&A LLM.
- **Signal > Bruit** : tri, dédup, scoring → *Top 3 signaux* / *Top 3 risques*.
- **Réponses citées** : le LLM renvoie faits + graphiques + sources.
- **Mémoire** : news/données/notes historisées pour donner du contexte au LLM (RAG).

**Piliers**
1. Macro (FRED, VIX, GSCPI, GPR, tendances inflation/emploi/liquidité)
2. Actions (yfinance, SMA/RSI/MACD, comparaisons secteurs)
3. News (RSS robuste + scoring fraîcheur/source/pertinence)
4. LLM Copilot (Q&A + what-if avec retrieval sur 5+ ans)
5. Mémoire & traçabilité (sources, timestamps, params)

**Sorties**
- Daily/Weekly **Market Brief** (HTML/PDF)
- **Fiches Ticker** : techniques + news + niveaux
- **Réponses LLM citées** avec limites explicites

**KPIs**
- Couverture ≥ 90% tickers ≤ 24h
- Fraîcheur news médiane < 10 min
- Brief ≤ 2 pages (annexes à part)
- 100% graphiques avec **source+timestamp**
- 80% réponses LLM avec ≥2 sources

**Garde-fous**
- Explainable-first, contre-arguments, opt-in Internet pour tests, citations obligatoires.

**MVP**
- Ingestion macro (FRED), prix (yfinance), RSS robuste + dédup
- Scoring simple **macro(40)/tech(40)/news(20)**
- Market Brief hebdo via `make`
- Q&A LLM avec **RAG** (5 ans de séries + 12-24 mois news)

**Non-objectifs**
- Pas d'ordres de bourse, pas d'alpha opaque, pas de données payantes non conformes


## 🛠️ Prise en main rapide

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env  # édite les clés
make smoke   # test rapide
make test    # unit tests
make it-integration  # tests réseau (AF_ALLOW_INTERNET=1)
```

## 🚀 Déploiement Production

### Configuration Requise
```bash
# Copier et configurer l'environnement
cp .env.sample .env
# Éditer .env avec vos clés API (FRED, OpenAI, etc.)
```

### Lancement en Développement
```bash
# API Backend
make run-api

# Frontend React (dans un autre terminal)
make run-webapp

# Stack complète
make fullstack
```

### Lancement en Production
```bash
# API avec configuration production
API_ENV=production python run_api.py --host 0.0.0.0 --port 8050

# Avec process manager (systemd, pm2, etc.)
# Exemple systemd service:
# [Unit]
# Description=Finance Copilot API
# After=network.target
# 
# [Service]
# Type=simple
# User=finance
# WorkingDirectory=/opt/finance-copilot
# Environment=API_ENV=production
# EnvironmentFile=/opt/finance-copilot/.env
# ExecStart=/opt/finance-copilot/.venv/bin/python run_api.py --host 0.0.0.0 --port 8050
# Restart=always
# 
# [Install]
# WantedBy=multi-user.target
```

### Surveillance & Monitoring
```bash
# Health check
curl http://localhost:8050/health

# API metrics
curl http://localhost:8050/metrics

# Logs
tail -f logs/api.log
```

### Sauvegarde & Maintenance
```bash
# Backup manuel
make backup

# Restore depuis backup
make restore-backup BACKUP_FILE=backup_20251102.tar.gz

# Nettoyage périodique
make clean-cache
```

## 🛡️ Sécurité & Performance

### Rate Limiting
- Copilot Q&A: 10 requêtes/minute
- Market Brief: 30 requêtes/heure
- News Feed: 100 requêtes/heure

### CORS Configuration
En production, seuls les origines autorisées peuvent accéder à l'API.

### Secrets Management
Les clés API et secrets doivent être configurés via variables d'environnement, jamais dans le code.

## 📊 Monitoring & Alerting

### Endpoints de Santé
- `/health` - Statut général de l'API
- `/metrics` - Métriques Prometheus
- `/api/rag/stats` - Statistiques RAG

### Logs Structurés
Tous les logs sont au format JSON avec timestamp, niveau, et contexte pour intégration ELK/Splunk.

## 🔄 CI/CD & Déploiement Automatisé

### Pipeline GitHub Actions
Le dépôt inclut des workflows pour:
- Tests unitaires et d'intégration
- Analyse de code (linting, sécurité)
- Déploiement sur serveur de staging
- Déploiement sur production (tagged releases)

### Docker (Optionnel)
```dockerfile
# Dockerfile disponible dans le dépôt
docker build -t finance-copilot .
docker run -p 8050:8050 --env-file .env finance-copilot
```


## 👨‍💻 Guide Agent LLM

Les consignes, routes, conventions et objectifs pour tout agent/IA qui code ici : voir **`docs/AGENT_GUIDE.md`**.

Schéma d'archi, modules et flux de données : **`docs/ARCHITECTURE.md`**.

Vision détaillée, KPIs et roadmap : **`docs/VISION.md`**.
