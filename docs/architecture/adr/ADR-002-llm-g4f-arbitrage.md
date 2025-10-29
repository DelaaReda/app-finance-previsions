# ADR-002 — LLM via g4f (GPT4Free) avec Arbitrage Multi-Agents

**Date**: 2025-10-29
**Statut**: ✅ Accepté (Implémenté Sprint Sonnet-2)
**Décideurs**: Reda + Équipe Dev
**Révision**: —

---

## Contexte

L'application génère **forecasts multi-sources** (momentum, macro, sentiment). Problème: **synthétiser** ces signaux pour investisseur non-expert (Reda).

**Besoins**:
1. Résumer 50+ forecasts en **3-5 recommandations claires** (FR)
2. Expliquer **pourquoi** (drivers technique/macro/sentiment)
3. Identifier **tensions** (ex: technique bullish mais macro bearish)
4. Coût **zéro** (budget limité)

**Options LLM**:
- **OpenAI GPT-4**: $0.03/1k tokens → ~$50/mois (1500 calls/jour) ❌ Coût
- **Claude Sonnet**: $0.015/1k tokens → ~$25/mois ❌ Coût
- **Ollama local**: Gratuit mais GPU RTX 3090 requis (~$1500) ❌ Hardware
- **g4f (GPT4Free)**: Gratuit, multi-models, pas de GPU ✅

**Questions**:
1. g4f assez **robuste** pour production?
2. Quel **pattern** LLM (single prompt vs multi-agents)?
3. Comment garantir **explicabilité**?

---

## Décision

### 1. Provider: g4f (GPT4Free)
Utiliser **g4f** comme provider LLM principal.

**Justifications**:
- **Coût zéro**: Proxies gratuits vers models (DeepSeek R1, Qwen, GLM, Llama)
- **Multi-models**: 50+ models disponibles → fallback si 1 down
- **Anonyme**: Pas de tracking, pas de clés API
- **Communauté active**: Repo GitHub 60k+ stars, updates régulières

**Mitigations instabilité**:
- **Retry automatique**: 2 retries avec backoff (2s, 4s)
- **Model fallback**: DeepSeek R1 → Qwen 2.5 → GLM-4
- **Timeout**: 30s max par requête
- **Monitoring**: Logs success/failure → alert si taux échec > 30%

### 2. Pattern: Multi-Agents → Arbitre
Adopter **pattern ensemble** au lieu de prompt monolithique:

```
Agent Technique → \
Agent Macro     →  → Arbitre LLM → Synthèse JSON (Pydantic validé)
Agent Sentiment → /
Agent Qualité   → /
```

**Justifications**:
- **Explicabilité**: Chaque agent identifié dans `contributors` (source, rationale)
- **Robustesse**: Si 1 agent échoue, arbitre peut compenser avec 3 autres
- **Testabilité**: Chaque agent testable unitairement (mock LLM)
- **Évolutivité**: Ajouter agents (ex: Agent Sectoriel) sans changer arbitre

**Agents**:
1. **Technique**: Analyse Top-50 forecasts (momentum, scores)
2. **Macro**: Analyse régime (expansion/contraction, risque)
3. **Sentiment**: Agrège news 7j par ticker
4. **Qualité**: Pénalise données périmées (freshness > 48h)

**Arbitre**:
- **Rôle**: Réconcilier 4 agents → synthèse consensuelle
- **Prompt**: "Tu es comité investissement, réconcilie ces 4 analyses..."
- **Output**: JSON conformant schema `LLMEnsembleSummary` (Pydantic)

### 3. Schema: Pydantic Strict
Forcer **validation Pydantic** sur output LLM.

**Schema**:
```python
class LLMEnsembleSummary(BaseModel):
    regime: Literal["expansion_modérée", "désinflation", "contraction", "incertain"]
    risk_level: Literal["low", "medium", "high"]
    outlook_days_7: Literal["positive", "neutral", "negative"]
    outlook_days_30: Literal["positive", "neutral", "negative"]
    key_drivers: List[str] = Field(min_items=3, max_items=5)
    contributors: List[Contributor]  # source, model, horizon, symbol, score, prediction, rationale
    limits: List[str]  # Ex: "Données macro H-48", "Faible couverture utilities"
```

**Justifications**:
- **Type safety**: Python runtime valide types (pas de "regime": 123)
- **Contraintes**: `min_items=3` garantit ≥ 3 key_drivers
- **Sérialisation**: `.model_dump_json()` génère JSON propre
- **Documentation**: Schema = contrat API (autogen docs OpenAPI possible)

### 4. Orchestration: Horaire + Manuel
**Horaire**:
- **Scheduler**: APScheduler (top of every hour)
- **Make target**: `llm-summary-run`
- **Output**: `data/llm_summary/dt=YYYYMMDDHH/summary.json`

**Manuel**:
- **UI**: Bouton "Relancer maintenant" sur `/llm_summary`
- **Callback**: `run_make("llm-summary-run")` + affichage logs
- **Lock**: Anti collision (1 run à la fois, TTL 1h)

---

## Conséquences

### ✅ Positives
1. **Coût zéro**: Aucun abonnement LLM (vs $25-50/mois OpenAI/Claude)
2. **Explicabilité**: Chaque contributor identifié (source, rationale) → confiance Reda
3. **Robustesse**: Fallback multi-models → uptime ~95% (vs 99.9% OpenAI mais payant)
4. **Historisation**: Partitions `dt=YYYYMMDDHH` → audit trail complet
5. **Testabilité**: Mock LLMClient → tests reproductibles, CI rapide
6. **Évolutivité**: Ajouter agents sans toucher arbitre

### ⚠️ Négatives
1. **Instabilité g4f**: Providers parfois down/rate-limited → retries requis
2. **Latency**: 30-60s total (4 agents séquentiels) vs 5-10s OpenAI
3. **Qualité variable**: DeepSeek R1 > Qwen > GLM (pas uniforme)
4. **Pas de streaming**: Réponses complètes seulement (pas de UX "typing...")
5. **Dépendance communauté**: Si g4f repo abandonné → migration vers Ollama/OpenRouter

### 🔧 Mitigations Négatives
- **Retry + fallback**: Si DeepSeek down → Qwen (latency +5s acceptable)
- **Parallel agents**: Async calls (4 agents en parallèle) → réduire 60s → 20s (future)
- **Cache LLM**: Si inputs identiques dernière heure → réutiliser réponse (future)
- **Monitoring**: Dashboard Observability affiche taux succès/failure LLM
- **Plan B**: Ollama local (Llama 3.3 70B) si g4f instable > 50% échecs/semaine

---

## Alternatives Rejetées

### Alternative 1: OpenAI GPT-4
**Approche**: API officielle OpenAI

**Rejet**:
- **Coût**: $50/mois inacceptable pour budget Reda
- **Tracking**: OpenAI log prompts/outputs (confidentialité)
- **Lock-in**: Dépendance fournisseur unique

### Alternative 2: Claude Sonnet via API
**Approche**: Anthropic API officielle

**Rejet**:
- **Coût**: $25/mois (meilleur que GPT-4 mais still payant)
- **Rate limits**: 50 req/min (vs g4f illimité)

### Alternative 3: Ollama Local (Llama 3.3 70B)
**Approche**: Run LLM localement (GPU)

**Rejet**:
- **Hardware**: GPU RTX 3090/4090 requis (~$1500)
- **RAM**: 48 GB+ pour 70B model
- **Électricité**: 350W GPU 24/7 → ~$30/mois
- **Note**: Gardé comme **Plan B** si g4f instable long terme

### Alternative 4: Prompt monolithique (single LLM call)
**Approche**: 1 seul prompt "résume tout"

**Rejet**:
- **Explicabilité**: Impossible identifier sources (black box)
- **Robustesse**: Si LLM hallucine, pas de cross-check
- **Testabilité**: Difficile mocker/valider

---

## Implémentation

### Modules
- **`src/agents/llm/runtime.py`**: LLMClient wrapper g4f
  ```python
  class LLMClient:
      def __init__(self, provider: str = "g4f", model: str = "deepseek-ai/DeepSeek-R1-0528"):
          self.provider = provider
          self.model = model

      def generate(self, messages: List[Dict], json_mode: bool = True, temperature: float = 0.2, max_tokens: int = 2048, retries: int = 2) -> str:
          """Generate response with retry logic."""
          for attempt in range(retries + 1):
              try:
                  if self.provider == "g4f":
                      response = g4f.ChatCompletion.create(
                          model=self.model,
                          messages=messages,
                          temperature=temperature,
                          max_tokens=max_tokens
                      )
                      return response
              except Exception as e:
                  if attempt == retries:
                      raise
                  time.sleep(2 ** attempt)  # Backoff 2s, 4s
          raise RuntimeError("LLM generation failed after retries")
  ```

- **`src/agents/llm/toolkit.py`**: Functions pour agents
  ```python
  @toolkit_function
  def analyze_technique(top_n: int = 50) -> str:
      df = read_parquet_latest("data/forecast", "final.parquet")
      top = df.nlargest(top_n, "final_score")
      return json.dumps(top.to_dict("records"), ensure_ascii=False)

  @toolkit_function
  def analyze_macro() -> str:
      df = read_parquet_latest("data/macro/forecast", "macro_forecast.parquet")
      return json.dumps(df.tail(1).to_dict("records")[0], ensure_ascii=False)
  ```

- **`src/agents/llm/arbiter_agent.py`**: Main arbiter
  ```python
  def run_llm_summary() -> Dict:
      client = LLMClient(model="deepseek-ai/DeepSeek-R1-0528")

      prompt = f"""
      Tu es comité investissement. Réconcilie ces 4 analyses:

      1. Technique: {analyze_technique()}
      2. Macro: {analyze_macro()}
      3. Sentiment: {analyze_sentiment()}
      4. Qualité: {analyze_quality()}

      Génère JSON conformant schema LLMEnsembleSummary.
      """

      response = client.generate([{"role": "user", "content": prompt}], json_mode=True)
      summary = LLMEnsembleSummary(**json.loads(response))

      # Write partition
      dt = datetime.utcnow().strftime("%Y%m%d%H")
      outdir = Path("data/llm_summary") / f"dt={dt}"
      outdir.mkdir(parents=True, exist_ok=True)
      (outdir / "summary.json").write_text(summary.model_dump_json(indent=2))

      return summary.model_dump()
  ```

### Tests
- **`tests/llm/test_llm_summary.py`**: Mock LLMClient
  ```python
  def test_arbiter_with_mock():
      with patch("src.agents.llm.runtime.LLMClient.generate") as mock_gen:
          mock_gen.return_value = json.dumps({
              "regime": "expansion_modérée",
              "risk_level": "medium",
              "outlook_days_7": "positive",
              "outlook_days_30": "neutral",
              "key_drivers": ["Driver 1", "Driver 2", "Driver 3"],
              "contributors": [],
              "limits": []
          })

          summary = run_llm_summary()
          assert summary["regime"] == "expansion_modérée"
          mock_gen.assert_called_once()
  ```

---

## Validation

### Critères de Succès
1. **Taux succès > 90%**: Monitoring logs → alert si < 90% last 7 days
2. **Latency < 90s**: P95 latency < 90s (4 agents + arbitre)
3. **Explicabilité**: Chaque summary.json contient ≥ 3 contributors avec rationales
4. **Validation schema**: 100% summaries passent Pydantic validation

### Monitoring
- **Logs**: `artifacts/logs/llm_summary.log` (JSON lines)
- **Metrics**: Prometheus-style (duration, success/failure, model)
- **UI**: `/observability` affiche derniers 10 runs (timestamps, status, durée)

### Rollback Plan
Si taux échec g4f > 50% pendant 7 jours:
1. Migrate vers **OpenRouter** (g4f-like mais plus stable, ~$5/mois)
2. Long terme: Setup **Ollama local** (Llama 3.3 70B) si budget GPU acceptable

---

## Références

- **g4f Repo**: https://github.com/xtekky/gpt4free
- **DeepSeek R1**: https://huggingface.co/deepseek-ai/DeepSeek-R1
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Issue initiale**: #78 "LLM summary MVP"

---

**Révisions**:
- **v1.0** (2025-10-29): Décision initiale
