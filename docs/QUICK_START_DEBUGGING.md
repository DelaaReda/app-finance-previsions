# 🚀 DÉMARRAGE RAPIDE - DÉBOGAGE REACT

## 🎯 OBJECTIF
Apprendre à utiliser React Developer Tools pour déboguer l'application Finance Copilot en 10 minutes.

## ⏱️ ÉTAPES (10 MINUTES)

### Minute 1-2: Installation
```bash
# Vérifier l'installation
python scripts/debug_react.py check
```

**✅ Résultat attendu** : Instructions pour vérifier l'extension dans le navigateur

### Minute 3-4: Lancer l'Application
```bash
# Lancer avec conseils de débogage
python scripts/debug_react.py launch
```

**✅ Résultat attendu** : 
- API Backend sur http://localhost:8050
- Frontend React sur http://localhost:5173
- Navigateur ouvert automatiquement

### Minute 5-6: Explorer Components
1. Ouvrir **Outils Développeur** (`F12`)
2. Cliquer sur l'onglet **Components**
3. Explorer l'arbre :
   ```
   App
   └── MainLayout
       └── Dashboard
           ├── Filters
           ├── KPIsGrid
           ├── TopSignals
           └── TopRisks
   ```

### Minute 7-8: Déboguer un Composant
1. Dans **Components**, cliquer sur `Dashboard`
2. Voir les **Props** :
   ```javascript
   {
     title: "Market Dashboard",
     filters: { sectors: [], horizons: [], themes: [] }
   }
   ```
3. Voir l'**État** :
   ```javascript
   {
     sectors: [],
     horizons: [],
     themes: [],
     selectedTickers: ["SPY", "QQQ"]
   }
   ```

### Minute 9-10: Profiler les Performances
1. Cliquer sur l'onglet **Profiler**
2. Cliquer sur ⚫️ **Record**
3. Interagir avec l'application (changer de filtre, cliquer)
4. Cliquer sur **Stop**
5. Analyser les résultats :
   - Durée des commits
   - Composants rendus
   - Raisons des re-rendus

## 🧪 SCÉNARIOS COURANTS

### Problème: Données non affichées
1. **Components** → Trouver composant concerné
2. Vérifier **Props** - sont-elles vides ?
3. Vérifier **State** - y a-t-il des erreurs ?
4. **Network** → Voir erreurs API

### Problème: Application lente
1. **Profiler** → Record → Interagir → Stop
2. Identifier commits lents
3. Trouver composants qui re-rendent inutilement
4. Vérifier **Why did this render?**

### Problème: Filtres ne fonctionnent pas
1. **Components** → Trouver composant de filtre
2. Surveiller changements d'état
3. Vérifier handlers d'événements
4. **Network** → Vérifier requêtes API

## 🔍 RACCOURCIS UTILES

| Action | Raccourci |
|--------|-----------|
| Ouvrir DevTools | `F12` |
| Rechercher composant | `Ctrl+F` |
| Commencer profilage | `Ctrl+P` |
| Sélection visuelle | `Ctrl+Shift+C` |
| Rafraîchir arbre | `Ctrl+Shift+R` |

## 📚 RESSOURCES

- **Guide complet** : `docs/REACT_DEVELOPER_TOOLS_GUIDE.md`
- **Documentation officielle** : https://react.dev/learn/react-developer-tools
- **Aide** : `python scripts/debug_react.py help`

## ✅ VALIDATION

À la fin de ces 10 minutes, vous devriez être capable de :

1. ✅ Ouvrir React Developer Tools dans votre navigateur
2. ✅ Explorer l'arbre des composants
3. ✅ Voir les props et l'état des composants
4. ✅ Profiler les performances de l'application
5. ✅ Déboguer les problèmes courants

## 🎯 PROCHAINE ÉTAPE

Maintenant que vous maîtrisez les bases, explorez le guide complet :
```bash
cat docs/REACT_DEVELOPER_TOOLS_GUIDE.md
```

Et pratiquez avec des scénarios réels en utilisant l'application Finance Copilot !