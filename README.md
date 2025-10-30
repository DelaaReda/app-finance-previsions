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


## 👨‍💻 Guide Agent LLM

Les consignes, routes, conventions et objectifs pour tout agent/IA qui code ici : voir **`docs/AGENT_GUIDE.md`**.

Schéma d'archi, modules et flux de données : **`docs/ARCHITECTURE.md`**.

Vision détaillée, KPIs et roadmap : **`docs/VISION.md`**.
