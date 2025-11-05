# Template de Tâche - À utiliser pour CHAQUE task

## 🎯 Phase 1: COMPRENDRE (5 min max)

### Checklist Compréhension
- [ ] Lire la task ID et titre
- [ ] Identifier les fichiers concernés (chercher avec `grep` ou `find`)
- [ ] Lire les 20 premières lignes des fichiers concernés
- [ ] Noter les dépendances (imports, API calls)
- [ ] **STOP** et valider compréhension avant de coder

### Questions à se poser AVANT de coder:
1. Quel est le problème EXACT à résoudre?
2. Quels fichiers je dois modifier? (max 3-5 fichiers)
3. Est-ce que je comprends l'architecture autour?
4. Y a-t-il des tests existants à regarder?

## 🔨 Phase 2: PLANIFIER (2 min max)

### Checklist Planification
- [ ] Créer une todo list avec TodoWrite (3-7 items max)
- [ ] Identifier les risques (breaking changes, API changes)
- [ ] Vérifier si backend ET frontend doivent changer
- [ ] **STOP** si tâche > 1h, découper en sous-tâches

### Plan minimal:
```
1. Modifier fichier X (ligne Y) - ajouter fonction Z
2. Modifier fichier A (ligne B) - appeler fonction Z
3. Tester manuellement avec curl/browser
4. Créer proof avec screenshot/log
5. Commit avec trailers
```

## 💻 Phase 3: IMPLÉMENTER (max 30-45 min)

### Checklist Implémentation
- [ ] **TOUJOURS** utiliser Read avant Edit/Write
- [ ] **TOUJOURS** marquer todo "in_progress" avant de commencer
- [ ] **TOUJOURS** marquer todo "completed" DÈS que terminé
- [ ] **JAMAIS** faire 2 tâches en parallèle
- [ ] **JAMAIS** laisser du code commenté
- [ ] **JAMAIS** créer des fichiers .bak ou .backup

### Patterns à utiliser:
```typescript
// ✅ BON: Safety helpers
const items = safeArray(data?.items)
if (!hasItems(items)) return <EmptyState />

// ❌ MAUVAIS: Assume data exists
const items = data.items
return items.map(...)
```

```python
# ✅ BON: Never-empty pattern
def get_forecasts():
    try:
        data = load_json("forecasts")
        return _ok({"rows": data.get("rows", []), "count": len(data.get("rows", []))})
    except Exception as e:
        return _ok({"rows": [], "count": 0, "error": str(e)})

# ❌ MAUVAIS: Can return None
def get_forecasts():
    data = load_json("forecasts")
    return data
```

### Material-UI Standards (Frontend):
```typescript
// ✅ BON: Use MUI components
import { Container, Box, Typography, Card, CardContent } from '@mui/material'

return (
  <Container maxWidth="lg">
    <Card>
      <CardContent>
        <Typography variant="h5">Title</Typography>
      </CardContent>
    </Card>
  </Container>
)

// ❌ MAUVAIS: Inline styles
return (
  <div style={{padding: 20}}>
    <h1 style={{fontSize: 24}}>Title</h1>
  </div>
)
```

## 🧪 Phase 4: TESTER (10 min)

### Checklist Tests
- [ ] Backend: `curl` l'endpoint et vérifier JSON valide
- [ ] Frontend: Ouvrir dans browser, vérifier pas d'erreurs console
- [ ] Tester cas edge: données vides, erreur réseau, etc.
- [ ] Screenshot ou copier output pour proof
- [ ] **CRITICAL**: Run `pnpm build` (frontend) ou `pytest` (backend)

### Commandes de test rapides:
```bash
# Backend
curl http://localhost:8050/api/forecasts | jq '.'

# Frontend (build check)
cd copilot-app/frontend/webapp
pnpm build

# Tests Python
cd copilot-app/backend
.venv/bin/pytest tests/
```

## 📝 Phase 5: DOCUMENTER (5 min)

### Checklist Documentation
- [ ] Créer dossier proof: `proofs/FC-XXX-YYY/AGENT-NAME/`
- [ ] Créer PROOF.md ou FIX-REPORT.md avec:
  - ✅ Problème (1-2 lignes)
  - ✅ Solution (2-3 bullet points)
  - ✅ Test result (screenshot ou log)
  - ✅ Impact (1 ligne)

### Template Proof Minimal:
```markdown
✅ FC-XXX: Brief title

**Problem**: One sentence

**Solution**:
- Changed file X line Y
- Added function Z

**Test**:
curl ... | jq
-> Returns 200 OK with 50 items

**Impact**: Feature now works
```

## 💾 Phase 6: COMMIT (5 min)

### Checklist Commit
- [ ] `git add` seulement fichiers modifiés (pas .bak, .lock)
- [ ] Message commit avec format exact (voir ci-dessous)
- [ ] **TOUS** les trailers présents (Task, Agent, Domain, Proofs, TimeSpent)
- [ ] Relire message avant commit
- [ ] Si hook échoue, lire l'erreur et corriger

### Template Commit EXACT:
```bash
git commit -m "$(cat <<'EOF'
[feat|fix|chore]: FC-XXX-YYY – Brief title (+points if applicable)

1-3 lines describing what was done.

**Changes**:
- File X: did Y
- File Z: did W

**Impact**: One line impact

Task: FC-XXX-YYY
Agent: @YOUR-NAME-HERE
Domain: Frontend | Backend | API | etc
Proofs: proofs/FC-XXX-YYY/YOUR-NAME/
TimeSpent: XXmin

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

## ⚠️ ANTI-PATTERNS À ÉVITER

### ❌ Ne JAMAIS faire:
1. Coder sans lire le code existant d'abord
2. Créer 10+ todos (max 7)
3. Laisser une todo "in_progress" sans la compléter
4. Commit sans proof
5. Commit sans tester
6. Utiliser inline styles au lieu de MUI
7. Créer des fichiers temporaires (.bak, .backup)
8. Oublier de mettre à jour SCORE_AGENTS.md
9. Créer des exports dupliqués (toujours run `pnpm build`)
10. Assumer que data existe (toujours `safeArray()`)

### ✅ Toujours faire:
1. Utiliser safety helpers (`safeArray`, `hasItems`, `safeGet`)
2. Patterns never-empty (toujours retourner structure valide)
3. Material-UI pour tout le frontend
4. Tester AVANT de commit
5. Créer proof avec evidence
6. Marquer todos completed immédiatement
7. Un seul focus à la fois

## 📊 Estimation Points

- Fix bug critique: +100
- Endpoint never-empty: +120
- Page MUI complète: +80
- Component MUI: +40-60
- Fix build/imports: +50
- Documentation: +30

**Total session cible: 200-400 points**
