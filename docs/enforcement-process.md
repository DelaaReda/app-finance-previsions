# Finance Copilot - Processus d'application des règles

Ce document décrit les mécanismes de contrôle qualité et d'application des règles pour garantir une qualité élevée des livraisons.

## 🔒 Hooks Git - Contrôle automatique

### 1. Hook `commit-msg` - Format de commit
- **Fichier**: `.git/hooks/commit-msg`
- **Vérifie**:
  - Présence du trailer `Task: FC-XXXX` 
  - Présence du trailer `Agent: @handle`
  - Présence du trailer `Proofs: proofs/...`
  - Présence de `(+points)` dans le sujet pour les commits "done"

### 2. Hook `pre-push` - Tests de fumée
- **Fichier**: `.git/hooks/pre-push`
- **Vérifie**:
  - Le backend est démarré sur le port 8050
  - Tous les endpoints critiques répondent correctement:
    - `/api/health` - retourne `{ok: true}`
    - `/api/news/feed` - contient `"articles"`
    - `/api/forecasts` - contient `"rows"`
    - `/api/brief/weekly` - répond avec `{ok: ...}`
    - `/api/backtests` - répond avec `{ok: ...}`

## 🛠️ Processus de développement

### 1. Avant de commencer une tâche
1. Vérifier que le backend est opérationnel
2. Lire la tâche dans `TASKS_BOARD.md`
3. Créer un lock: `echo "owner=@handle" > .locks/TASK-ID.lock`
4. Faire un `git pull` récent

### 2. Pendant le développement
- Suivre le format d'import absolu: `from api.core.middleware import ...`
- Assurer la structure de package avec `__init__.py`
- Utiliser les patterns never-empty: `{rows: [], freshness: "...", source: [...]}`

### 3. Avant de pousser (push)
1. Démarrer le backend avec `./finance-copilot.sh start`
2. Exécuter `scripts/smoke.sh` pour tester manuellement
3. Le hook `pre-push` exécutera automatiquement les tests

## ⚠️ Contournements (à utiliser avec précaution)

Pour contourner le smoke test en cas d'urgence:
```bash
BYPASS_SMOKE=1 git push
```

## 📊 Métriques de qualité

### Endpoints critiques
- `/api/health` - Doit toujours retourner `{ok: true}`
- `/api/news/feed` - Doit toujours retourner `{ok: true, data: {articles: []}}`
- `/api/forecasts` - Doit toujours retourner `{ok: true, data: {rows: []}}`

### Patterns UI
- `data?.rows ?? []` pour sécuriser les listes
- `data?.articles ?? []` pour sécuriser les articles
- Affichage de l'état vide (EmptyState)
- Affichage de la fraîcheur (freshness badge)

## 🧭 Best practices
- Un agent = une tâche à la fois
- Petits commits atomiques
- Preuves ajoutées dans `proofs/TASK-ID/handle/`
- Lock supprimé dans le commit "done"
- Respect du format `{ok, data}` partout