## 🎯 Objet de la PR
<!-- Résumé clair : quoi / pourquoi. Lier l'issue (#123) et/ou sprint. -->
- Sprint: `Sprint-<N>`
- Issue(s) liée(s): #<id> (Story/Bug)

## ✅ Critères d’acceptation (DoD)
- [ ] Tests unitaires verts (CI)
- [ ] Lint/format/typage OK (pre-commit / CI)
- [ ] Pas de régression sur Dash/Streamlit (smoke)
- [ ] Docs/PROGRESS.md mis à jour si nécessaire
- [ ] Données sensibles exclues (gitignore)

## 🔍 Portée & risques
- Surface touchée : `src/apps/<dash|streamlit>`, `src/agents`, `tests`, …
- Risques / impacts :
  - (ex.) callback Dash affecté ?
  - (ex.) compatibilité Python 3.11/3.12 ?

## 🧪 Tests
- Étapes de test manuel (si pertinent) :
  1. `make dash-start` / `make ui-restart-bg`
  2. Vérifier pages : Dashboard / Signals / Observability / Quality
  3. …

## 📸 Captures (optionnel)
<!-- Ajoute un GIF/image si UI -->

## 📝 Notes
<!-- Décisions d’architecture, TODOs ultérieurs, dettes techniques -->

