# ⚡ QUICK START MVP - App Finance Prévisions

**Objectif:** MVP fonctionnel en **2-3 jours**  
**Base:** Inspection complète révèle 78% déjà implémenté!

---

## 🎯 TL;DR - Les 3 Seules Choses à Faire

### 1. Créer `core/data_access.py` (2h)
### 2. Adapter `populate_rag_store.py` (2h)
### 3. Wrapper `llm_client.py` autour econ_llm_agent (1h)

**Total: 5h de code + 1h tests = 6h pour MVP de base!**

---

## 🚀 FAST TRACK - 6 Heures

### Heure 1-2: data_access.py

```bash
cd /Users/venom/Documents/analyse-financiere
cat > src/core/data_access.py << 'EOF'
"""Adapter accès données pour scoring."""
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta

from core.market_data import get_price_history, get_fred_series
from analytics.phase3_macro import get_us_macro_bundle
from ingestion.finnews import run_pipeline


def get_close_series(ticker: str) -> Optional[pd.Series]:
    """Série Close pour un ticker."""
    df = get_price_history(ticker, start=None, interval="1d")
    if df is None or df.empty:
        return None
    return df["Close"].dropna()


def load_macro_forecast_rows(limit: int = 1) -> Dict[str, Any]:
    """Snapshot macro actuel."""
    try:
        bundle = get_us_macro_bundle(start="2020-01-01", monthly=True)
        data = bundle.data
        
        # CPI YoY
        inflation_yoy = None
        if "CPIAUCSL" in data.columns:
            cpi = data["CPIAUCSL"].dropna()
            if len(cpi) >= 12:
                inflation_yoy = float((cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100)
        
        # Yield curve
        yield_curve_slope = None
        if "DGS10" in data.columns and "DGS2" in data.columns:
            dgs10 = data["DGS10"].dropna().iloc[-1] if not data["DGS10"].dropna().empty else None
            dgs2 = data["DGS2"].dropna().iloc[-1] if not data["DGS2"].dropna().empty else None
            if dgs10 and dgs2:
                yield_curve_slope = float(dgs10 - dgs2)
        
        # Unemployment
        unemployment = None
        try:
            unrate = get_fred_series("UNRATE", start="2020-01-01")
            if unrate is not None and not unrate.empty:
                unemployment = float(unrate.iloc[-1])
        except:
            pass
        
        # Recession prob
        recession_prob = 0.5 if yield_curve_slope and yield_curve_slope < 0 else 0.0
        
        return {
            "rows": [{
                "inflation_yoy": inflation_yoy,
                "yield_curve_slope": yield_curve_slope,
                "unemployment": unemployment,
                "recession_prob": float(recession_prob)
            }]
        }
    except:
        return {"rows": [{"inflation_yoy": None, "yield_curve_slope": None, "unemployment": None, "recession_prob": 0.0}]}


def load_news_features(limit: int = 100) -> Dict[str, Any]:
    """Features news."""
    try:
        items = run_pipeline(regions=["US", "CA"], window="last_week", query="", limit=limit)
        
        rows = []
        for item in items:
            tickers = item.get("tickers", [])
            symbol = tickers[0] if tickers else None
            
            importance = item.get("importance", 0.5)
            sentiment = item.get("sentiment", 0.0) if item.get("sentiment") else 0.0
            sentiment_norm = (sentiment + 1) / 2
            news_score_mean = importance * sentiment_norm
            
            published = item.get("published", "")
            hours_since = 24.0
            if published:
                try:
                    pub_dt = pd.to_datetime(published)
                    hours_since = (datetime.utcnow() - pub_dt).total_seconds() / 3600
                except:
                    pass
            
            rows.append({
                "symbol": symbol,
                "news_score_mean": float(news_score_mean),
                "hours_since_publish": float(hours_since)
            })
        
        return {"rows": rows}
    except:
        return {"rows": []}
EOF

# Tester
python -c "from core.data_access import *; print('✅ data_access OK')"
```

---

### Heure 3-4: RAG Ensemencement

```bash
cd /Users/venom/Documents/analyse-financiere

# Backup original
cp scripts/populate_rag_store.py scripts/populate_rag_store_ORIGINAL.py

# Modifier (ou créer nouveau script)
cat > scripts/populate_rag_real_data.py << 'EOF'
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
from research.rag_store import RAGStore
from core.market_data import get_fred_series, get_price_history
from ingestion.finnews import run_pipeline

def populate_real_data():
    print("🚀 Ensemencement RAG avec données réelles...")
    rag = RAGStore()
    
    # 1. Macro 5 ans (échantillon trimestriel)
    print("📊 Macro data...")
    start = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    
    for series_id, name in [
        ("CPIAUCSL", "CPI"),
        ("UNRATE", "Unemployment"),
        ("DGS10", "10Y Treasury"),
        ("DGS2", "2Y Treasury"),
        ("FEDFUNDS", "Fed Funds")
    ]:
        try:
            series = get_fred_series(series_id, start=start)
            if series is not None and not series.empty:
                # Échantillon trimestriel
                for i, (date, value) in enumerate(series.items()):
                    if i % 3 == 0:  # Tous les 3 mois
                        rag.add_series_fact(series_id, name, float(value), date.strftime("%Y-%m-%d"))
                print(f"  ✅ {series_id}: {len(series)//3} points")
        except Exception as e:
            print(f"  ⚠️ {series_id}: {e}")
    
    # 2. Prix 5 ans (hebdo)
    print("📈 Prix actions...")
    for ticker in ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"]:
        try:
            df = get_price_history(ticker, start=start, interval="1wk")
            if df is not None and not df.empty:
                for date, row in df.iterrows():
                    rag.add_series_fact(
                        f"{ticker}_CLOSE",
                        f"{ticker} Weekly Close",
                        float(row["Close"]),
                        date.strftime("%Y-%m-%d")
                    )
                print(f"  ✅ {ticker}: {len(df)} weeks")
        except Exception as e:
            print(f"  ⚠️ {ticker}: {e}")
    
    # 3. News 3 derniers mois (top 500)
    print("📰 News récentes...")
    try:
        items = run_pipeline(
            regions=["US", "CA", "INTL"],
            window="last_month",
            query="",
            limit=500
        )
        
        added = 0
        for item in items:
            if item.get("score", 0) > 0.5:
                rag.add_news_item(item)
                added += 1
        print(f"  ✅ News: {added} items")
    except Exception as e:
        print(f"  ⚠️ News: {e}")
    
    # Stats finales
    stats = rag.stats()
    print(f"\n✅ Ensemencement terminé!")
    print(f"   Total chunks: {stats['total']}")
    print(f"   News: {stats.get('news_count', 0)}")
    print(f"   Series: {stats.get('facts_count', 0)}")

if __name__ == "__main__":
    populate_real_data()
EOF

chmod +x scripts/populate_rag_real_data.py

# Exécuter
python scripts/populate_rag_real_data.py
```

---

### Heure 5: LLM Wrapper

```bash
cat > src/research/llm_client.py << 'EOF'
"""Client LLM générique - Wrapper G4F + OpenAI."""
import os
import re
from typing import List, Dict, Any

# Essayer G4F
try:
    from analytics.econ_llm_agent import POWER_NOAUTH_MODELS
    from g4f.client import Client as G4FClient
    HAS_G4F = True
except:
    HAS_G4F = False
    POWER_NOAUTH_MODELS = []

# Essayer OpenAI
try:
    import openai
    HAS_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
except:
    HAS_OPENAI = False


def ask_llm(question: str, context_chunks: List[Dict], max_tokens=1000) -> Dict[str, Any]:
    """
    Interroge LLM avec contexte RAG.
    Fallback chain: G4F → OpenAI → Heuristique
    """
    # Construire contexte
    context = "\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(context_chunks[:10])])
    
    # 1. Essayer G4F (gratuit)
    if HAS_G4F:
        result = _try_g4f(question, context, max_tokens)
        if result:
            return {"answer": result, "citations": _extract_citations(result, context_chunks), "model": "g4f"}
    
    # 2. Essayer OpenAI
    if HAS_OPENAI:
        result = _try_openai(question, context, max_tokens)
        if result:
            return {"answer": result, "citations": _extract_citations(result, context_chunks), "model": "openai"}
    
    # 3. Fallback heuristique
    return _fallback(context_chunks)


def _try_g4f(question, context, max_tokens):
    try:
        client = G4FClient()
        for model in POWER_NOAUTH_MODELS[:3]:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": f"Contexte:\n{context}\n\nQuestion: {question}\n\nRéponds avec citations [1], [2]:"}],
                    max_tokens=max_tokens,
                    temperature=0.3
                )
                return response.choices[0].message.content
            except:
                continue
    except:
        pass
    return None


def _try_openai(question, context, max_tokens):
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Tu es un analyste financier. Cite tes sources [1], [2]."},
                {"role": "user", "content": f"Contexte:\n{context}\n\nQuestion: {question}"}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content
    except:
        return None


def _extract_citations(answer: str, chunks: List[Dict]) -> List[Dict]:
    """Extrait numéros [N] et retourne chunks correspondants."""
    cited = [int(m.group(1))-1 for m in re.finditer(r'\[(\d+)\]', answer)]
    return [
        {
            "index": i+1,
            "type": chunks[i]["meta"]["type"],
            "url": chunks[i]["meta"].get("url", ""),
            "date": chunks[i]["meta"].get("date", ""),
            "excerpt": chunks[i]["text"][:150] + "..."
        }
        for i in cited if i < len(chunks)
    ]


def _fallback(chunks: List[Dict]) -> Dict[str, Any]:
    """Fallback si aucun LLM disponible."""
    summary = "⚠️ LLM indisponible. Résumé des sources:\n\n"
    for i, c in enumerate(chunks[:5]):
        summary += f"[{i+1}] {c['text'][:150]}...\n\n"
    
    return {
        "answer": summary,
        "citations": [],
        "model": "fallback"
    }
EOF

# Tester
python -c "from research.llm_client import ask_llm; print('✅ llm_client OK')"
```

---

### Heure 6: Tests & Validation

```bash
# 1. Tester scoring complet
python -c "
from research.scoring import calculate_composite_score
score = calculate_composite_score('AAPL')
print(f'✅ AAPL Score: {score}')
"

# 2. Tester RAG
python -c "
from research.rag_store import RAGStore
rag = RAGStore()
stats = rag.stats()
print(f'✅ RAG Stats: {stats}')
assert stats['total'] > 100, 'RAG insuffisant'
"

# 3. Démarrer API
python run_api.py &
sleep 5

# 4. Tester endpoints
curl -s http://localhost:8050/api/health | jq
curl -s "http://localhost:8050/api/brief?period=weekly&universe=SPY&universe=QQQ" | jq '.ok'
curl -s -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Quelle est l'\''inflation actuelle?"}' | jq '.ok'

# 5. Frontend
cd webapp
npm run dev &

# Ouvrir http://localhost:5173
```

---

## 📋 CHECKLIST RAPIDE

### Setup (15min)
- [ ] `cd /Users/venom/Documents/analyse-financiere`
- [ ] `source .venv/bin/activate`  # ou créer si absent
- [ ] `pip install -r requirements-api.txt requirements-api-v2.txt`
- [ ] `cp .env.sample .env`
- [ ] Éditer `.env`: Ajouter `FRED_API_KEY` si disponible

### Core (2h)
- [ ] Créer `src/core/data_access.py` (copier code ci-dessus)
- [ ] Tester: `python -c "from core.data_access import *; print('OK')"`

### RAG (2h)
- [ ] Créer `scripts/populate_rag_real_data.py` (copier code ci-dessus)
- [ ] Exécuter: `python scripts/populate_rag_real_data.py` (30-60min)
- [ ] Vérifier: stats > 100 chunks

### LLM (1h)
- [ ] Créer `src/research/llm_client.py` (copier code ci-dessus)
- [ ] Tester: `from research.llm_client import ask_llm`

### API (30min)
- [ ] Si API v1 (api/main.py): Rien à faire (imports OK après data_access créé)
- [ ] Si API v2: Corriger imports si nécessaire

### Frontend (30min)
- [ ] Corriger `brief.service.ts` (envoyer universe)
- [ ] Corriger `api.ts` (check r.ok)

### Validation (30min)
- [ ] API démarre: `python run_api.py`
- [ ] Tous endpoints 2xx
- [ ] Frontend affiche données
- [ ] Q&A répond avec citations

---

## 🎬 COMMANDES COPY-PASTE

### Installation
```bash
cd /Users/venom/Documents/analyse-financiere
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements-api.txt -r requirements-api-v2.txt
```

### data_access.py
```bash
# Voir code complet section "Heure 1-2" ci-dessus
# Copier-coller dans terminal
```

### RAG populate
```bash
# Voir code complet section "Heure 3-4" ci-dessus
python scripts/populate_rag_real_data.py
```

### LLM client
```bash
# Voir code complet section "Heure 5" ci-dessus
```

### Démarrage Full Stack
```bash
# Terminal 1: Backend
python run_api.py

# Terminal 2: Frontend
cd webapp && npm run dev

# Browser
open http://localhost:5173
```

---

## ✅ CRITÈRES SUCCÈS MVP

### Backend ✅
```bash
# Health check
curl http://localhost:8050/api/health
# → {"status": "ok", "services": {...}}

# Brief
curl "http://localhost:8050/api/brief?period=weekly&universe=SPY"
# → {"ok": true, "data": {"top_signals": [...]}}

# Copilot
curl -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Inflation actuelle?"}'
# → {"ok": true, "data": {"answer": "...", "citations": [...]}}
```

### Frontend ✅
- [ ] Dashboard affiche KPIs
- [ ] MarketBrief affiche top 3 signals/risks
- [ ] Copilot répond aux questions
- [ ] Pas d'erreurs console

---

## ⚡ SI PROBLÈME

### Erreur: "No module named 'core.data_access'"
```bash
# Vérifier fichier créé
ls -la src/core/data_access.py

# Vérifier syntaxe
python -m py_compile src/core/data_access.py

# Tester import
python -c "import sys; sys.path.insert(0, 'src'); from core.data_access import get_close_series"
```

### Erreur: RAG vide
```bash
# Vérifier fichiers
ls -la data/rag/
cat data/rag/news.jsonl | wc -l
cat data/rag/facts.jsonl | wc -l

# Relancer populate
python scripts/populate_rag_real_data.py
```

### Erreur: LLM timeout
```bash
# Vérifier G4F installé
pip show g4f

# Vérifier OPENAI_API_KEY
echo $OPENAI_API_KEY

# Forcer fallback
unset OPENAI_API_KEY
# LLM client utilisera résumé heuristique
```

---

## 📊 TIMELINE RÉALISTE

### Scénario Optimiste (1.5 jours)
- **Jour 1 Matin (3h):** data_access + RAG
- **Jour 1 PM (3h):** LLM + Frontend fixes
- **Jour 2 Matin (2h):** Tests + Polish
- **12:00:** 🎉 MVP LIVE

### Scénario Réaliste (2.5 jours)
- **Jour 1 (6h):** data_access + RAG ensemencement
- **Jour 2 (4h):** LLM wrapper + Tests intégration
- **Jour 3 (2h):** Frontend fixes + Validation finale
- **Total:** 12h

### Scénario Prudent (4 jours)
- **Jour 1 (4h):** data_access + tests unitaires
- **Jour 2 (4h):** RAG ensemencement + vérifications
- **Jour 3 (4h):** LLM + API tests
- **Jour 4 (4h):** Frontend + E2E + Documentation
- **Total:** 16h

---

## 🎯 NEXT STEPS IMMÉDIAT

### MAINTENANT (5min)
```bash
# 1. Lire ce document
# 2. Décider timeline (optimiste/réaliste/prudent)
# 3. Ouvrir terminal
cd /Users/venom/Documents/analyse-financiere
source .venv/bin/activate
```

### DANS 10min
```bash
# Créer data_access.py (copier-coller code section "Heure 1-2")
```

### DANS 2h15
```bash
# Créer populate_rag_real_data.py (copier-coller code section "Heure 3-4")
# Lancer ensemencement (aller prendre café ☕)
```

### DANS 4h
```bash
# Créer llm_client.py (copier-coller code section "Heure 5")
# Démarrer API
# Tests manuels endpoints
```

### DANS 6h
```bash
# 🎉 MVP FONCTIONNEL
# Brief génère
# Copilot répond
# Frontend affiche
```

---

## 📞 SUPPORT

### Si Bloqué
1. Vérifier logs: `tail -f logs/api.log`
2. Relire sections concernées:
   - GAPS_ANALYSIS_COMPLETE.md (code détaillé)
   - INSPECTION_COMPLETE_TRIPLEX.md (architecture)
3. Tester composants isolément avant intégration

### Prochains Documents à Lire

**Si tout fonctionne:**
- `docs/ETAT_PROJET_PRIORITES.md` - Roadmap V1

**Si problèmes API:**
- `docs/RAPPORT_FINAL_INSPECTION.md` - Section API duale

**Si problèmes Frontend:**
- `docs/INSPECTION_CRITIQUE_FINALE.md` - Section Frontend

---

**🚀 BONNE CHANCE! MVP EN VUE! 🎯**

**Documents générés pour cette analyse:**
1. ✅ ETAT_PROJET_PRIORITES.md
2. ✅ GAPS_ANALYSIS_COMPLETE.md (avec code solutions)
3. ✅ INSPECTION_COMPLETE_TRIPLEX.md
4. ✅ INSPECTION_CRITIQUE_FINALE.md
5. ✅ RAPPORT_FINAL_INSPECTION.md
6. ✅ SYNTHESE_ULTIME_ACTION.md
7. ✅ QUICK_START_MVP.md ← **COMMENCER ICI!**
