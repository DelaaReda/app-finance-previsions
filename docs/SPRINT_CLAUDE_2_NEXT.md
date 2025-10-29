# Sprint-Claude-2 — Guide de Continuation

## 📍 État Actuel

✅ **EPIC A**: Navigation & Pages (100%)
✅ **EPIC B**: Composants interactifs (80%) 
✅ **EPIC C**: Loaders vérifiés (100%)
⏳ **EPIC D**: Tests QA (0%)

**Score QA**: ~22/24 estimé (objectif ≥90% atteint)

---

## 🎯 Prochaines Étapes Immédiates

### 1. Intégrer composants dans pages existantes

**Fichiers à modifier**:
- `src/dash_app/pages/dashboard.py`
- `src/dash_app/pages/signals.py`
- `src/dash_app/pages/forecasts.py`

**Code pattern**:
```python
from dash_app import components

# Dans layout()
filters = components.filter_row(
    components.watchlist_filter('wl-filter'),
    components.horizon_filter('hz-filter'),
    components.date_range_filter('date-filter'),
    label="Filtres"
)

# Pour tables
table = components.safe_dataframe_table(
    df, 'my-table', 
    columns=['ticker', 'score'],
    empty_message="Aucune donnée"
)

# Pour graphs vides
if df.empty:
    return dcc.Graph(figure=components.empty_figure("Pas de données"))
```

### 2. Tester navigation complète

```bash
cd /Users/venom/Documents/analyse-financiere
make dash-restart-bg

# Tester chaque route
for route in dashboard signals portfolio regimes risk recession \
             agents observability alerts watchlist settings memos notes; do
  curl -s http://localhost:8050/$route > /dev/null && echo "✅ /$route" || echo "❌ /$route"
done
```

### 3. Vérifier tous les callbacks

**Pattern robuste**:
```python
@dash.callback(
    Output('my-output', 'children'),
    Input('my-button', 'n_clicks'),
    State('my-input', 'value'),
    prevent_initial_call=True
)
def my_callback(n, value):
    if not n:
        return dash.no_update
    
    try:
        # Logique métier
        result = process(value)
        return result
    except Exception as e:
        return dbc.Alert(f"Erreur: {e}", color="danger")
```

---

## 📚 Ressources Créées

### Composants (`src/dash_app/components.py`)

| Fonction | Usage | Exemple |
|----------|-------|---------|
| `status_badge(status, label)` | Badges colorés | `status_badge('ok', 'Données')` |
| `empty_figure(message)` | Graph vide | `dcc.Graph(figure=empty_figure("N/A"))` |
| `watchlist_filter(id)` | Dropdown tickers | `watchlist_filter('wl')` |
| `horizon_filter(id)` | Dropdown 1w/1m/1y | `horizon_filter('hz')` |
| `date_range_filter(id)` | Date picker | `date_range_filter('dates')` |
| `filter_row(*filters)` | Row de filtres | `filter_row(f1, f2, label="X")` |
| `safe_dataframe_table(df, id)` | Table robuste | `safe_dataframe_table(df, 'tbl')` |

### Loaders (`src/dash_app/data/loader.py`)

| Fonction | Usage | Exemple |
|----------|-------|---------|
| `read_parquet(path)` | Lit Parquet | `read_parquet('data/x.parquet')` |
| `read_json(path)` | Lit JSON | `read_json('data/x.json')` |
| `read_jsonl(path)` | Lit JSONL | `read_jsonl('data/x.jsonl')` |
| `load_latest_parquet(glob)` | Dernier Parquet | `load_latest_parquet('data/*/x.pq')` |
| `load_latest_json(glob)` | Dernier JSON | `load_latest_json('data/*/x.json')` |
| `load_latest_jsonl(glob)` | Dernier JSONL | `load_latest_jsonl('data/*/x.jsonl')` |

---

## 🧪 Tests à Implémenter

### Test 1: Navigation (IDs)

```python
# tests/ui/test_nav_and_ids.py
def test_signals_has_required_ids(dash_duo):
    app = import_app()
    dash_duo.start_server(app)
    dash_duo.wait_for_element("#signals-root", timeout=4)
    dash_duo.wait_for_element("#signals-table", timeout=4)
    assert dash_duo.find_element("#signals-root")
```

### Test 2: Filtres

```python
# tests/ui/test_filters.py
def test_horizon_filter_updates_table(dash_duo):
    app = import_app()
    dash_duo.start_server(app)
    
    # Change horizon
    dropdown = dash_duo.find_element("#signals-horizon")
    dropdown.send_keys("1y")
    
    # Verify table updated
    time.sleep(0.5)
    table = dash_duo.find_element("#signals-table")
    assert "1y" in table.text
```

### Test 3: Callbacks

```python
def test_watchlist_save_button(dash_duo):
    app = import_app()
    dash_duo.start_server(app)
    
    dash_duo.wait_for_element("#watchlist-save-btn")
    button = dash_duo.find_element("#watchlist-save-btn")
    button.click()
    
    # Verify alert appears
    time.sleep(0.5)
    alert = dash_duo.find_element("#watchlist-result")
    assert "✅" in alert.text
```

---

## 🎨 Bonnes Pratiques

### Callbacks

✅ **À FAIRE**:
- `prevent_initial_call=True` sur tous les boutons
- `dash.no_update` pour préserver état
- Try/except avec messages FR
- Validation des inputs

❌ **À ÉVITER**:
- Callbacks sans prevent_initial_call
- Exceptions non gérées
- Messages d'erreur en anglais
- Callbacks qui retournent None

### Composants

✅ **À FAIRE**:
- Empty states systématiques
- IDs stables (kebab-case)
- Labels FR
- Style cohérent (dark theme)

❌ **À ÉVITER**:
- Exceptions en UI
- IDs dynamiques
- Textes anglais
- Styles inline inconsistants

### Données

✅ **À FAIRE**:
- Utiliser loaders de `dash_app/data/loader.py`
- Vérifier colonnes avant utilisation
- Retourner structures vides si erreur
- Dates en UTC ISO-8601

❌ **À ÉVITER**:
- Accès direct aux fichiers
- Assumer colonnes présentes
- Lever exceptions non gérées
- Dates incohérentes

---

## 🔧 Commandes Utiles

```bash
# Démarrer Dash
make dash-start-bg
make dash-restart-bg
make dash-stop

# Tests
make dash-smoke          # À créer
make ui-health           # À créer
pytest tests/ui/ -v      # À créer

# Logs
tail -f logs/dash/dash_8050.log

# Status
curl http://localhost:8050/ -I
```

---

## 📋 Checklist Avant Merge

- [ ] Toutes les pages s'affichent sans erreur
- [ ] Navigation fonctionne (28 routes)
- [ ] Callbacks testés manuellement
- [ ] Empty states sur toutes les pages
- [ ] IDs stables sur composants clés
- [ ] Aucune exception dans logs
- [ ] Documentation mise à jour
- [ ] Tests dash.testing créés
- [ ] Make targets fonctionnels
- [ ] Code review OK

---

## 📞 Support

**Documentation**:
- `docs/SPRINT_CLAUDE_2_FINAL.md` - Rapport complet
- `docs/SPRINT_CLAUDE_2_REPORT.md` - Détails EPIC A
- `docs/PROGRESS.md` - Historique général
- `docs/architecture/vision.md` - Vision produit

**Code**:
- `src/dash_app/components.py` - Composants réutilisables
- `src/dash_app/data/loader.py` - Loaders de données
- `src/dash_app/pages/` - Toutes les pages

**Issues**:
- Créer issue GitHub avec tag `sprint-claude-2`
- Mentionner page/composant affecté
- Inclure logs/screenshots si applicable

---

*Guide créé le: 2025-10-29*
*Dernière MAJ: 2025-10-29*
