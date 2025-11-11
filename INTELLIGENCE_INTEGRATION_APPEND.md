
---

## FC-INT-022 — Intelligence Dashboard Integration Plan
**Status**: CLAIMED by MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23

**But**: Intégration avancée des widgets existants avec les capacités LLM G4F pour créer une UI intelligente et complète qui analyse, recommande, s'adapte et explique les données.

**Fichiers**
* `backend/services/intelligence_service.py`
* `backend/services/context_service.py`
* `backend/api/routes/intelligence.py`
* `frontend/webapp/src/components/intelligence/IntelligenceDashboardWidget.tsx`
* `frontend/webapp/src/components/intelligence/SmartRecommendationsWidget.tsx`
* `frontend/webapp/src/components/intelligence/AdaptiveLayout.tsx`
* `frontend/webapp/src/hooks/useIntelligence.ts`
* `frontend/webapp/src/lib/llm_analyzer.py` (Python backend)

**Étapes**
1. **Intelligence Service**:
   - Agrège toutes les données disponibles (forecasts, macro, news, stocks)
   - Utilise LLM G4F pour analyse intelligente et insights
   - Endpoint: `/api/intelligence/snapshot` qui renvoie {insights, recommendations, market_regime, correlations}

2. **Context Service**:
   - Identifie le régime de marché (Bull, Bear, Sideways, Volatile, etc.)
   - Détermine les drivers dominants (macro vs tech vs news)
   - Recommende le layout/widget optimal à afficher selon le contexte

3. **Smart Recommendations**:
   - Génère "Top 3 actions à surveiller aujourd'hui"
   - Basé sur ML scoring + LLM ranking
   - Avec explications contextuelles

4. **Adaptive UI**:
   - Layout qui s'adapte selon le régime marché identifié
   - Widget placement dynamique (ex: Macro en avant en période volatile)
   - Priorisation automatique selon conditions actuelles

5. **Correlation Intelligence**:
   - Analyse des corrélations entre news→forecasts, macro→stocks, etc.
   - LLM explique pourquoi les actifs se comportent ensemble
   - Détecte les changements de corrélation

**DoD**
* IntelligenceDashboardWidget fonctionnel qui combine tous les widgets avec insights LLM
* Smart Recommendations avec explications contextuelles
* UI Adaptive qui change selon le régime marché
* Correlation Intelligence avec explications LLM
* Tous les services backend (intelligence/context) opérationnels
* Never-empty patterns respectés avec fallbacks intelligents
* Interface utilisateur intelligente qui "pense" et recommande