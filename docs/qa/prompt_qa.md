# 🧩 **QA_GUIDE.md — Guide Qualité & Validation (App Finance Prévisions)**

> Version : `v1.1` — inclut le test automatisé MCP `web_eval_agent`
> Projet : `app-finance-previsions`
> Auteur QA : ATLAS
> Date : 2025-10-26

---

## 🎯 **Mission du QA**

Le QA Engineer garantit la **qualité fonctionnelle, visuelle et technique** de l’application **Dash – App Finance Prévisions**.
Il valide le comportement de chaque page Dash et de chaque agent de prévision via :

* Tests manuels (UI/UX)
* Tests automatisés (smoke, MCP, web_eval_agent)
* Vérifications de cohérence des données et logs

---

## 🧱 **Structure de test**

| Domaine           | Description                                  | Dossier                |
| ----------------- | -------------------------------------------- | ---------------------- |
| UI Dash           | Application web (frontend)                   | `src/dash_app/`        |
| Agents            | Scripts Python de génération de données      | `src/agents/`          |
| Monitoring        | Suivi des processus et fraîcheur des données | `/observability`       |
| Tests automatisés | Smoke + MCP + Web Eval Agent                 | `ops/ui/` + `Makefile` |

---

## 🧪 **Plan général de test QA**

### 1️⃣ Préparation de l’environnement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make dash-start-bg
make dash-status && make dash-logs
```

Vérifier :

* Port 8050 actif
* Aucun message d’erreur Dash
* Dossier `data/` bien ignoré par Git

---

### 2️⃣ Tests de base

| Commande             | Description                                |
| -------------------- | ------------------------------------------ |
| `make dash-smoke`    | Vérifie la disponibilité HTTP (routes 200) |
| `make dash-mcp-test` | Exécute le script MCP (UX automatisé)      |
| `pytest -q`          | Lancement des tests unitaires              |
| `make dash-logs`     | Vérifie les logs serveur Dash              |

---

### 3️⃣ **Test automatisé avancé : `web_eval_agent` (Cline MCP)**

#### 🔹 Description

Le **web-eval-agent** est un outil MCP qui évalue l’**expérience utilisateur** (UX/UI) de l’application Dash de manière automatisée.
Il utilise un **navigateur contrôlé** (headless ou visible) pour interagir avec l’interface, effectuer des navigations, valider les composants, et générer un rapport complet (texte + captures d’écran).

#### 🔹 Exemple d’exécution complète

```python
{
  "url": "http://localhost:8050",
  "task": "Test the financial dashboard application. Navigate through all pages (Dashboard, Signals, Portfolio, News, Deep Dive, Forecasts, Regimes, Risk, Recession, Agents Status, Observability). Check that all pages load correctly, Plotly charts are rendered with data, trend badges are visible, and the watchlist filter works. Verify no console errors and assess overall UX quality. Report any missing elements or issues.",
  "headless_browser": false
}
```

#### 🔹 Étapes QA correspondantes

1. **Démarrer Dash**

   ```bash
   make dash-start-bg
   ```

2. **Lancer l’évaluation UX :**

   * Ouvre le centre MCP (`ops/ui/mcp_dash_smoke.mjs`)
   * Configure le module `web_eval_agent`
   * Fournis l’URL locale : `http://localhost:8050`
   * Fournis la tâche : navigation complète et test des pages
   * Laisse `headless_browser: false` pour voir la session en direct

3. **Résultat attendu :**

   * Rapport généré (texte + captures d’écran)
   * Localisation : `logs/mcp_ui_test.log` et `artifacts/web_eval/`
   * Structure :

     ```
     ├── artifacts/web_eval/
     │   ├── report.json
     │   ├── screenshots/
     │   │   ├── dashboard.png
     │   │   ├── forecasts.png
     │   │   └── observability.png
     │   └── summary.txt
     ```

4. **Critères de validation :**

   * Aucune page 404
   * Aucun message “callback failed” dans la console
   * Tous les graphiques Plotly visibles
   * Filtre Watchlist fonctionnel
   * Sidebar active et navigation fluide
   * Score UX ≥ 8/10 (selon le rapport)

---

### 4️⃣ Tests UI manuels (contrôle visuel)

| Page          | Objectif                         | Validation            |
| ------------- | -------------------------------- | --------------------- |
| Dashboard     | Vérifier KPIs & badges           | Données fraîches      |
| Signals       | Vérifier filtres et tri          | Résultat rapide (<2s) |
| Deep Dive     | Vérifier graph 5 ans & news      | Aucun NaN             |
| Forecasts     | Vérifier DataTable multi-tickers | Export CSV correct    |
| Observability | Vérifier badge global 🟢         | Logs cohérents        |
| Agents Status | Vérifier fraîcheur partitions    | dt=today              |

---

### 5️⃣ Validation de données et d’agents

```bash
make equity-forecast
make forecast-aggregate
make macro-forecast
make update-monitor
```

Critères :

* Fichiers datés (`dt=YYYYMMDD`)
* Logs complets (Start / End / Warnings)
* Aucun stacktrace dans `logs/`

---

### 6️⃣ Rapport QA à produire

Créer ou mettre à jour :

#### 🗂️ `docs/QA_REPORT.md`

```markdown
### Sprint-5 — Validation QA

🗓️ Date : 2025-10-26  
👤 QA : ATLAS  
🧪 Tests : smoke, MCP, web_eval_agent  
✅ 12/12 routes HTTP 200  
✅ web_eval_agent OK – UX Score 9/10  
⚠️ Forecast export UTF-8 issue  
📁 Artifacts : logs/mcp_ui_test.log, artifacts/web_eval/
```

#### 🗂️ `docs/PROGRESS.md`

```markdown
### Sprint-5 QA Validation Summary
- [x] Smoke tests passed (12/12)
- [x] MCP UX OK
- [x] Web Eval Agent OK (UX 9/10)
- [ ] Minor CSV encoding issue
```

---

## 🧭 **Commandes QA essentielles**

| Commande               | Description          |
| ---------------------- | -------------------- |
| `make dash-start-bg`   | Démarre Dash         |
| `make dash-restart-bg` | Redémarre Dash       |
| `make dash-smoke`      | Vérifie routes 200   |
| `make dash-mcp-test`   | Lancement UX MCP     |
| `make update-monitor`  | Vérifie fraîcheur    |
| `make dash-logs`       | Vérifie logs Dash    |
| `make clean`           | Nettoie cache & logs |

---

## 🧠 **Flux de travail QA**

1️⃣ Pull le dernier code (`git pull origin main`)
2️⃣ Redémarre l’app (`make dash-restart-bg`)
3️⃣ Exécute smoke + MCP
4️⃣ Exécute **web_eval_agent**
5️⃣ Vérifie les résultats / captures
6️⃣ Corrige ou reporte dans QA_REPORT
7️⃣ Mets à jour PROGRESS.md

---

## 📘 **Définition du Done QA**

| Vérification   | Attendu                         |
| -------------- | ------------------------------- |
| UI Dash        | Zéro erreur console             |
| MCP            | Screenshots complets            |
| web_eval_agent | Rapport complet et lisible      |
| Données        | Fraîches et datées              |
| Logs           | Sans exception                  |
| Docs           | QA_REPORT + PROGRESS mis à jour |

---

## 💡 **Bonnes pratiques**

* Toujours relancer Dash avant un test MCP ou web_eval_agent
* Toujours exécuter `make update-monitor` après modification d’agent
* Utiliser un environnement Python propre (`.venv`)
* Ne jamais committer `data/` ni `logs/`
* Joindre les **captures d’écran** issues du test MCP