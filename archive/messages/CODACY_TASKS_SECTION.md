
---

## 🧪 CODE QUALITY TASKS - Codacy Integration & Analysis

Suite à la mise en place de la directive qualité, voici les tâches spécifiques pour intégrer Codacy dans le workflow de développement.

---

## FC-QM-CODACY-001 — Codacy Analysis Setup & Integration

**Status**: AVAILABLE to claim

**But**: Intégrer l'analyse Codacy dans le workflow de développement pour améliorer la qualité du code et détecter les problèmes automatiquement.

**Fichiers**
* `backend/.codacy-coverage` (configuration)
* `frontend/webapp/.eslintrc.cjs` (intégration avec ESLint)
* `scripts/quality/codacy-analyze.sh` (script d'analyse)
* `docs/quality/codacy-integration.md` (documentation)

**Étapes**
1. **Setup Codacy-CLI**:
   - Installer les dépendances Codacy-CLI dans les deux environnements (backend et frontend)
   - Vérifier que `codacy-cli` est disponible dans le path
   - Créer des scripts d'analyse dans le répertoire `scripts/`

2. **Configuration outils**:
   - Configurer ESLint pour analyse avec Codacy
   - Ajouter les règles de qualité pour respecter les standards de projet (imports sûrs, never-empty, etc.)
   - Vérifier que les outils sont alignés sur les standards existants

3. **Workflow intégration**:
   - Ajouter l'analyse Codacy dans le hook pre-commit
   - Créer des scripts d'analyse par composant (backend, frontend)
   - Générer des rapports SARIF pour visualisation

4. **Documentation**:
   - Créer un guide pour les agents sur l'utilisation de `codacy-cli analyze`
   - Fournir des exemples spécifiques pour chaque type d'analyse

**DoD**
* `codacy-cli analyze` fonctionne pour analyse complète du code
* `codacy-cli analyze --tool eslint` fonctionne pour analyse spécifique
* Résultats générés au format SARIF: `codacy-cli analyze --tool eslint --format sarif -o results.sarif`
* Scripts d'analyse intégrés dans le workflow de développement
* Documentation mise en place pour l'équipe

---

## FC-QM-CODACY-002 — Analyse qualité backend + corrections

**Status**: AVAILABLE to claim

**But**: Exécuter l'analyse Codacy sur le backend et corriger les problèmes identifiés pour améliorer la qualité du code.

**Fichiers**
* Tous les fichiers Python dans `backend/`
* `backend/api/main.py`
* `backend/api/routes/*.py`
* `backend/services/*.py`
* `backend/jobs/*.py`
* `backend/storage/*.py`

**Étapes**
1. **Analyse complète du backend**:
   - Exécuter: `codacy-cli analyze backend/`
   - Sauvegarder les résultats: `codacy-cli analyze backend/ --format sarif -o backend-quality.sarif`
   - Identifier les problèmes critiques et de sécurité

2. **Corrections prioritaires**:
   - Problèmes de sécurité (SQL injection, XSS, etc.)
   - Problèmes d'accessibilité
   - Problèmes de performance
   - Problèmes de style et maintenabilité

3. **Vérification never-empty**:
   - S'assurer que les patterns never-empty sont respectés partout
   - Vérifier que les imports sont sécurisés
   - Confirmer que les protections UI/UX sont correctes

4. **Tests et validation**:
   - Vérifier que les corrections n'introduisent pas de regressions
   - S'assurer que tous les endpoints continuent à fonctionner

**DoD**
* Analyse Codacy complète exécutée sur backend
* Problèmes critiques identifiés et corrigés
* Backend continues à fonctionner avec améliorations qualité
* Rapport SARIF sauvegardé avec preuves des corrections

---

## FC-QM-CODACY-003 — Analyse qualité frontend + corrections

**Status**: AVAILABLE to claim

**But**: Exécuter l'analyse Codacy sur le frontend et corriger les problèmes identifiés pour améliorer la qualité du code UI.

**Fichiers**
* Tous les fichiers TypeScript/JSX dans `frontend/webapp/src/`
* `frontend/webapp/src/components/*.tsx`
* `frontend/webapp/src/pages/*.tsx`
* `frontend/webapp/src/api/client.ts`
* `frontend/webapp/src/ui/*.tsx`
* `frontend/webapp/src/lib/safe.ts`

**Étapes**
1. **Analyse spécifique ESLint**:
   - Exécuter: `codacy-cli analyze --tool eslint frontend/webapp/src/`
   - Sauvegarder: `codacy-cli analyze --tool eslint frontend/webapp/src/ --format sarif -o frontend-quality.sarif`
   - Identifier les problèmes de sécurité, accessibilité, performance

2. **Corrections critiques**:
   - Problèmes de gestion d'erreurs UI (erreurs jamais affichées directement)
   - Problèmes de sécurité XSS
   - Problèmes d'accessibilité (roles, aria-labels, focus management)
   - Problèmes de never-empty (gardiens manquants)

3. **Optimisation**:
   - Améliorer la performance des composants UI
   - Optimiser les imports et dépendances
   - Vérifier les patterns de sécurité (safe access helpers)

4. **Validation UI**:
   - Confirmer que toutes les pages continuent à charger
   - Tester les 4 états UI (loading, empty, error, fresh data)
   - Vérifier que les data-testid sont corrects

**DoD**
* Analyse Codacy + ESLint exécutée sur frontend
* Problèmes critiques identifiés et corrigés
* UI continues à fonctionner avec améliorations qualité
* Rapport SARIF sauvegardé avec preuves des corrections
* Protection never-empty renforcée

---

## FC-QM-CODACY-004 — Analyse fichier spécifique + corrections ciblées

**Status**: AVAILABLE to claim

**But**: Exécuter l'analyse Codacy sur des fichiers spécifiques identifiés comme problématiques et corriger les points critiques.

**Fichiers**
* `backend/src/api/main.py` (fichier central avec imports critiques)
* `frontend/webapp/src/api/client.ts` (communication API, sécurité)
* `frontend/webapp/src/components/ErrorBoundary.tsx` (gestion des erreurs)
* `backend/storage/io.py` (sécurité I/O, never-empty)
* `backend/services/cache_layer.py` (gestion du cache, fallbacks)

**Étapes**
1. **Analyse fichier par fichier**:
   - `codacy-cli analyze --tool eslint backend/src/api/main.py`
   - `codacy-cli analyze --tool eslint frontend/webapp/src/api/client.ts`
   - `codacy-cli analyze --tool eslint frontend/webapp/src/components/ErrorBoundary.tsx`
   - etc.

2. **Corrections ciblées**:
   - Corriger les problèmes d'imports (ModuleNotFoundError)
   - Corriger les problèmes de sécurité (injection, etc.)
   - Corriger les problèmes de gestion d'erreurs
   - Renforcer les patterns never-empty

3. **Améliorations spécifiques**:
   - Assurer la cohérence des contrats API ({ok, data})
   - Vérifier les fallbacks en cas d'erreur
   - Optimiser les performances des composants critiques

4. **Tests unitaires**:
   - Vérifier que les corrections n'affectent pas la fonctionnalité
   - Tester spécifiquement les cas d'erreur et empty-states

**DoD**
* Fichiers critiques analysés un par un avec Codacy
* Problèmes identifiés et corrigés dans chaque fichier
* Fonctionnalité des composants critiques maintenue ou améliorée
* Rapports SARIF générés par fichier avec preuves des corrections