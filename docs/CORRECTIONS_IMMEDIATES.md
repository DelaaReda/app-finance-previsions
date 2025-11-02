# 🔧 CORRECTIONS IMMÉDIATES - Post-Livraison Agents

**Date:** 2 novembre 2025, 12h00  
**Context:** Validation commits agents (dernières 2h)  
**Effort Total:** 1h30 pour perfection

---

## ✅ VALIDATION GLOBALE

### Travail Agents: **95/100** 🎉

- ✅ 8 fichiers livrés correctement
- ✅ 0 duplications détectées
- ✅ Imports cohérents
- ✅ +3096 lignes ajoutées
- ✅ -278 lignes nettoyées (refactor api/main.py)
- ⚠️ 3 corrections mineures requises (1h30)

---

## 🔧 CORRECTION #1: Retirer sys.path.insert (5min)

### Fichiers Concernés
```python
src/core/data_access.py:12-13
src/research/llm_client.py:9-10
src/ops/daily_rag_refresh.py:11
```

### Problème
```python
# Modifie sys.path globalement
sys.path.insert(0, str(Path(__file__).parent.parent))
```

**Impact:** 🟡 Peut causer conflits imports

### Solution
```bash
cd /Users/venom/Documents/analyse-financiere

# Automatique
for file in src/core/data_access.py src/research/llm_client.py src/ops/daily_rag_refresh.py; do
  # Retirer sys.path.insert et commentaire associé
  sed -i.bak '/# Add src to path/d' "$file"
  sed -i.bak '/sys.path.insert/d' "$file"
  sed -i.bak '/^$/N;/^\n$/d' "$file"  # Retirer lignes vides doubles
  
  # Backup créé en .bak (supprimer après vérif)
  rm "${file}.bak"
done

# Vérifier
git diff src/core/data_access.py
```

### Validation
```bash
# Tester imports toujours fonctionnels
python -c "
import sys
sys.path.insert(0, 'src')  # Seulement ici
from core.data_access import get_close_series
from research.llm_client import ask_llm
print('✅ Imports OK après cleanup')
"
```

---

## 🔧 CORRECTION #2: Ajouter G4F Fallback (15min)

### Fichier: `src/research/llm_client.py`

### Problème
- Seulement OpenAI supporté
- Nécessite clé API payante
- `econ_llm_agent.py` a G4F gratuit mais pas utilisé

### Solution

**Ajouter après ligne 10:**
```python
# Essayer G4F (gratuit)
try:
    from analytics.econ_llm_agent import POWER_NOAUTH_MODELS
    from g4f.client import Client as G4FClient
    HAS_G4F = True
except ImportError:
    HAS_G4F = False
    POWER_NOAUTH_MODELS = []
```

**Modifier ask_llm (après ligne 56):**
```python
def ask_llm(
    question: str,
    context_chunks: List[Dict[str, Any]],
    model: str = None,
    max_tokens: int = 1000
) -> Dict[str, Any]:
    if not model:
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Construire contexte
    context_text = "\n\n".join([
        f"[{i+1}] {chunk['text']}\nSource: {chunk['meta'].get('url', 'N/A')}"
        for i, chunk in enumerate(context_chunks[:10])
    ])
    
    # System/User prompts (garder existant)
    system_prompt = """..."""
    user_prompt = f"""..."""
    
    # ✅ AJOUTER: Essayer G4F d'abord (gratuit)
    if HAS_G4F:
        g4f_result = _try_g4f(question, context_text, system_prompt, max_tokens)
        if g4f_result:
            # Extraire citations
            cited_indices = _extract_citation_indices(g4f_result["answer"])
            citations = _build_citations(cited_indices, context_chunks)
            
            return {
                "answer": g4f_result["answer"],
                "citations": citations,
                "model": g4f_result["model"],
                "tokens": 0  # G4F ne retourne pas token count
            }
    
    # Essayer OpenAI (code existant ligne 76+)
    client = get_llm_client()
    if client is not None:
        # ... (garder code existant)
    
    # Fallback final
    return _fallback_heuristic(context_chunks)

# ✅ AJOUTER fonctions helper
def _try_g4f(question: str, context: str, system_prompt: str, max_tokens: int) -> Optional[Dict]:
    """Essaye G4F avec top 3 modèles."""
    try:
        client = G4FClient()
        
        for model in POWER_NOAUTH_MODELS[:3]:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{context}\n\nQuestion: {question}\n\nRéponds avec citations [1], [2]:"}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.3
                )
                
                return {
                    "answer": response.choices[0].message.content,
                    "model": f"g4f/{model}"
                }
            except Exception as e:
                print(f"G4F {model} failed: {e}")
                continue
    except Exception as e:
        print(f"G4F unavailable: {e}")
    
    return None

def _extract_citation_indices(answer: str) -> set:
    """Extrait [1], [2] de la réponse."""
    import re
    return set(int(m.group(1)) - 1 for m in re.finditer(r'\[(\d+)\]', answer))

def _build_citations(indices: set, chunks: List[Dict]) -> List[Dict]:
    """Construit liste citations."""
    return [
        {
            "index": i + 1,
            "type": chunks[i]["meta"]["type"],
            "url": chunks[i]["meta"].get("url", ""),
            "date": chunks[i]["meta"].get("date", ""),
            "excerpt": chunks[i]["text"][:200] + "..."
        }
        for i in indices
        if i < len(chunks)
    ]

def _fallback_heuristic(chunks: List[Dict]) -> Dict:
    """Fallback si aucun LLM."""
    answer = "⚠️ LLM indisponible. Résumé des sources:\n\n"
    for i, c in enumerate(chunks[:5]):
        answer += f"[{i+1}] {c['text'][:150]}...\n\n"
    
    return {
        "answer": answer,
        "citations": [],
        "model": "fallback",
        "tokens": 0
    }
```

### Validation
```bash
# Tester G4F disponible
python -c "from analytics.econ_llm_agent import POWER_NOAUTH_MODELS; from g4f.client import Client; print(f'✅ G4F OK, {len(POWER_NOAUTH_MODELS)} models')"

# Tester nouveau llm_client
python -c "
from src.research.llm_client import ask_llm
result = ask_llm('Test', [{'text': 'Context test', 'meta': {'type': 'test'}}])
print(f'✅ Model: {result[\"model\"]}')
print(f'✅ Answer: {result[\"answer\"][:50]}...')
"
```

---

## 🔧 CORRECTION #3: Adapter populate_rag_store.py (1h)

### Fichier: `scripts/populate_rag_store.py`

### Problème
- Données 100% synthetic (random values)
- Pas de vraies données FRED/yfinance

### Solution: Créer Version Réelle

```bash
cd /Users/venom/Documents/analyse-financiere

# Backup synthetic
cp scripts/populate_rag_store.py scripts/populate_rag_SYNTHETIC_backup.py

# Créer version réelle
cat > scripts/populate_rag_real_data.py << 'EOF'
#!/usr/bin/env python3
"""
Ensemencement RAG avec VRAIES données historiques (5+ ans).
Usage: python scripts/populate_rag_real_data.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
from research.rag_store import RAGStore
from core.market_data import get_fred_series, get_price_history
from ingestion.finnews import run_pipeline

def populate_real_data():
    """Populate RAG with real historical data."""
    print("🚀 RAG Ensemencement avec données réelles...")
    rag = RAGStore()
    
    # ========== 1. MACRO 5 ANS (échantillon trimestriel) ==========
    print("\n📊 Macro data (FRED)...")
    start_date = (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    
    macro_series = {
        "CPIAUCSL": "Consumer Price Index (CPI)",
        "CPILFESL": "Core CPI",
        "UNRATE": "Unemployment Rate",
        "DGS10": "10-Year Treasury Yield",
        "DGS2": "2-Year Treasury Yield",
        "FEDFUNDS": "Federal Funds Rate",
        "INDPRO": "Industrial Production Index",
        "PAYEMS": "Nonfarm Payrolls"
    }
    
    for series_id, name in macro_series.items():
        try:
            print(f"  Fetching {series_id}...", end=" ")
            series = get_fred_series(series_id, start=start_date)
            
            if series is not None and not series.empty:
                # Échantillonner tous les 3 mois (trimestriel)
                count = 0
                for i, (date, value) in enumerate(series.items()):
                    if i % 3 == 0:  # Every 3 months
                        rag.add_series_fact(
                            series_id=series_id,
                            name=name,
                            value=float(value),
                            date=date.strftime("%Y-%m-%d")
                        )
                        count += 1
                
                print(f"✅ {count} points (sampled quarterly)")
            else:
                print(f"⚠️ No data")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # ========== 2. PRIX ACTIONS 5 ANS (hebdomadaire) ==========
    print("\n📈 Stock prices (weekly)...")
    tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    for ticker in tickers:
        try:
            print(f"  Fetching {ticker}...", end=" ")
            df = get_price_history(ticker, start=start_date, interval="1wk")
            
            if df is not None and not df.empty:
                for date, row in df.iterrows():
                    rag.add_series_fact(
                        series_id=f"{ticker}_CLOSE",
                        name=f"{ticker} Weekly Close",
                        value=float(row["Close"]),
                        date=date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                    )
                
                print(f"✅ {len(df)} weeks")
            else:
                print(f"⚠️ No data")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # ========== 3. NEWS RÉCENTES (3 derniers mois, top 500) ==========
    print("\n📰 Recent news (3 months, top 500)...")
    
    try:
        items = run_pipeline(
            regions=["US", "CA", "INTL"],
            window="last_month",  # Finnews supporte: last_day, last_week, last_month
            query="",
            tgt_ticker=None,
            per_source_cap=None,
            limit=500
        )
        
        added = 0
        for item in items:
            score = item.get("score", 0)
            if score > 0.5:  # Seulement news de qualité
                rag.add_news_item(item)
                added += 1
        
        print(f"  ✅ Added {added} news items (score > 0.5)")
    
    except Exception as e:
        print(f"  ❌ News error: {e}")
    
    # ========== STATS FINALES ==========
    print("\n" + "="*60)
    stats = rag.stats()
    print(f"✅ RAG Ensemencement terminé!")
    print(f"   Total chunks: {stats['total']}")
    print(f"   News: {stats.get('news_count', 0)}")
    print(f"   Series facts: {stats.get('facts_count', 0)}")
    print("="*60)
    
    # Validation threshold
    if stats['total'] < 100:
        print("⚠️  WARNING: < 100 chunks, RAG insuffisant pour MVP")
        return False
    
    print("🎉 RAG prêt pour MVP!")
    return True

if __name__ == "__main__":
    success = populate_real_data()
    sys.exit(0 if success else 1)
EOF

chmod +x scripts/populate_rag_real_data.py

# Tester (dry run)
python scripts/populate_rag_real_data.py
```

**Effort:** 1h (30min code + 30min exécution)

---

## 🔧 CORRECTION #4: Cleanup api/main.py (OPTIONNEL)

### Vérification Actuelle

**Commit 84ddcb2 a déjà nettoyé!**
```diff
# RETIRÉ (-278 lignes):
- from analytics.phase2_technical import load_prices, technical_signals  # ❌ Non utilisés
- from ingestion.finnews import list_sources  # ❌ Non utilisé

# GARDÉ:
+ from analytics.phase2_technical import compute_indicators  # ✅ Utilisé ligne 324
+ from ingestion.finnews import run_pipeline as run_news_pipeline  # ✅ Utilisé ligne 213
```

**Validation:** ✅ Déjà fait! Rien à corriger.

---

## ✅ VALIDATION FONCTIONNELLE

### Test 1: data_access.py Fonctionne

```bash
# Test intégré
python -m src.core.data_access

# Attendu:
# Testing core.data_access functions...
# ✓ get_close_series('SPY'): 252 rows, last value: 573.21
# ✓ load_macro_forecast_rows(): 1 rows
#   - inflation_yoy: 3.7
#   - yield_curve_slope: 0.32
#   - unemployment: 3.8
# ✓ load_news_features(): 10 rows
```

---

### Test 2: scoring.py compute_composite_brief

```bash
# Test fonction
python -c "
import sys
sys.path.insert(0, 'src')
from research.scoring import compute_composite_brief

brief = compute_composite_brief('weekly', ['SPY', 'QQQ', 'AAPL'])
print(f'✅ Brief generated')
print(f'   Top signals: {len(brief[\"top_signals\"])}')
print(f'   Top risks: {len(brief[\"top_risks\"])}')
print(f'   Picks: {len(brief[\"picks\"])}')
print(f'   Sources: {len(brief[\"sources\"])}')
"
```

---

### Test 3: llm_client.py Q&A

```bash
# Test basique (sans API key = fallback)
python -c "
import sys
sys.path.insert(0, 'src')
from research.llm_client import ask_llm

context = [
    {
        'text': 'L'\''inflation CPI est à 3.7% en octobre 2025',
        'meta': {'type': 'series', 'date': '2025-10-01', 'url': 'https://fred.stlouisfed.org/series/CPIAUCSL'}
    }
]

result = ask_llm('Quelle est l'\''inflation ?', context, max_tokens=200)
print(f'✅ Model: {result[\"model\"]}')
print(f'✅ Answer: {result[\"answer\"][:100]}...')
print(f'✅ Citations: {len(result[\"citations\"])}')
"
```

---

### Test 4: API Endpoints

```bash
# Démarrer API
python run_api.py &
API_PID=$!
sleep 5

# Test /api/brief (utilise compute_composite_brief)
curl -s "http://localhost:8050/api/brief?period=weekly&universe=SPY&universe=QQQ" | jq '{
  ok,
  top_signals: .data.top_signals | length,
  top_risks: .data.top_risks | length,
  picks: .data.picks | length
}'

# Test /api/copilot/ask (utilise llm_client)
curl -s -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Test question"}' | jq '{ok, has_answer: .data.answer != null}'

# Arrêter API
kill $API_PID
```

---

## 📋 CHECKLIST CORRECTIONS

### Correction #1: sys.path.insert ⏱️ 5min
- [ ] Retirer de `data_access.py`
- [ ] Retirer de `llm_client.py`
- [ ] Retirer de `daily_rag_refresh.py`
- [ ] Tester imports OK
- [ ] Commit: "fix: remove sys.path.insert from modules"

### Correction #2: G4F Fallback ⏱️ 15min
- [ ] Ajouter import G4F dans `llm_client.py`
- [ ] Ajouter fonction `_try_g4f()`
- [ ] Intégrer dans `ask_llm()` avant OpenAI
- [ ] Tester avec/sans OPENAI_API_KEY
- [ ] Commit: "feat: add G4F fallback to llm_client"

### Correction #3: RAG Real Data ⏱️ 1h
- [ ] Créer `populate_rag_real_data.py`
- [ ] Tester fetch FRED (5 séries minimum)
- [ ] Tester fetch prix (3 tickers minimum)
- [ ] Tester fetch news (10 items minimum)
- [ ] Exécuter full populate (30-60min)
- [ ] Vérifier `stats['total'] > 1000`
- [ ] Commit: "feat: real data RAG population script"

### Validation Finale ⏱️ 10min
- [ ] API démarre sans erreurs
- [ ] Tous endpoints 2xx
- [ ] Frontend affiche données
- [ ] Tests manuels passed

---

## 🚀 COMMANDES RAPIDES

### Quick Fix (5min)
```bash
cd /Users/venom/Documents/analyse-financiere

# 1. Cleanup sys.path
for f in src/core/data_access.py src/research/llm_client.py src/ops/daily_rag_refresh.py; do
  sed -i '' '/sys.path.insert/d; /# Add src to path/d' "$f"
done

# 2. Commit
git add src/core/ src/research/ src/ops/
git commit -m "fix: remove sys.path.insert from modules"
```

### Add G4F (15min)
```bash
# Éditer src/research/llm_client.py
# Copier code section "CORRECTION #2" ci-dessus

# Tester
python -c "from src.research.llm_client import ask_llm; print('OK')"

# Commit
git add src/research/llm_client.py
git commit -m "feat: add G4F fallback to llm_client"
```

### Populate Real (1h)
```bash
# Créer script
# Copier code section "CORRECTION #3" ci-dessus

# Exécuter
python scripts/populate_rag_real_data.py

# Commit
git add scripts/populate_rag_real_data.py data/rag/
git commit -m "feat: populate RAG with real FRED/yfinance data"
```

---

## ✅ APRÈS CORRECTIONS

### État Attendu
```
✅ api/main.py imports OK
✅ scoring.py compute_composite_brief OK
✅ data_access.py sans sys.path
✅ llm_client.py avec G4F fallback
✅ RAG > 1000 chunks (vraies données)
✅ Tous endpoints fonctionnels
```

### MVP Ready
- Brief génère < 30s
- Copilot répond (G4F gratuit OU OpenAI)
- Frontend affiche données
- Tests manuels passent

---

**Temps Total Corrections:** 1h30  
**Après Corrections:** 🎉 **MVP COMPLET!**
