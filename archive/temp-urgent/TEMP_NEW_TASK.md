## FC-NEW-021 — Robustness Scoring & PDF Export (Frontend)

**Status**: AVAILABLE to claim

**But**: Implémenter le système de scoring robustesse avec export PDF et panel de tuning comme spécifié dans la spécification détaillée du 2025-11-05.

**Fichiers**

* `frontend/webapp/src/lib/robustScore.ts`
* `frontend/webapp/src/ui/Ring.tsx` 
* `frontend/webapp/src/components/metrics/RobustnessScoreCard.tsx`
* `frontend/webapp/src/utils/exportPdf.ts`
* `frontend/webapp/src/components/report/ExportReportButton.tsx`
* `frontend/webapp/src/components/tuner/PresetTunerPanel.tsx`
* `frontend/webapp/src/api/backtests.ts`
* `frontend/webapp/src/pages/Backtests.tsx` (intégration)

**Étapes**

1. **Implémentation du scoring robustesse**:
   - Créer `robustScore.ts` avec les fonctions de scoring CAGR, Drawdown, WinRate, Trades
   - Calculer le score total et la notation (S, A, B, C, D, E)

2. **Composant graphique Ring**:
   - Créer wrapper Mantine pour RingProgress avec style cohérent
   - Intégration avec la lib de scoring robustesse

3. **Carte de score Robustness**:
   - Créer composant RobustnessScoreCard qui affiche le ring + détails
   - Utiliser les couleurs appropriées selon le score

4. **Export PDF**:
   - Ajouter dépendances: `jspdf html2canvas`
   - Créer utilitaire `exportPdf.ts` avec html2canvas + jsPDF
   - Bouton export pour cibler n'importe quelle section

5. **Panel de Tuning**:
   - Créer PresetTunerPanel avec interface pour tester variantes backtests
   - Intégration avec API backtests
   - Affichage des résultats avec les scores de robustesse

6. **Intégration**:
   - Intégrer les composants dans la page Backtests.tsx
   - S'assurer que les patterns never-empty sont respectés

**DoD**

* Système de scoring robustesse opérationnel sur la page Backtests
* Bouton d'export PDF fonctionnel pour exporter n'importe quelle section
* Panel de tuning permettant d'explorer plusieurs variantes de paramètres
* 4 composants UI (Card, Ring, ExportButton, TunerPanel) prêts à être réutilisés
* Protection contre crashes avec helpers never-empty (ensureArray, etc.)
* UI fully responsive et accessible