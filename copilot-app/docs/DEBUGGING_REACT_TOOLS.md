# 🛠️ OUTILS DE DÉBOGAGE - REACT DEVELOPER TOOLS

## 📋 PRÉREQUIS

Avant d'utiliser ces outils, assurez-vous que :

1. **Extension React Developer Tools installée** :
   - Chrome : [Lien](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)
   - Firefox : [Lien](https://addons.mozilla.org/firefox/addon/react-devtools/)
   - Edge : [Lien](https://microsoftedge.microsoft.com/addons/detail/react-developer-tools/gpphkfbcpidddadnkolkpfckpihlkkil)

2. **Application Finance Copilot en cours d'exécution** :
   ```bash
   # Terminal 1 : API Backend
   python run_api.py
   
   # Terminal 2 : Frontend React
   cd webapp && npm run dev
   ```

## 🚀 GUIDE D'UTILISATION RAPIDE

### 1. **Ouvrir React Developer Tools**
1. Allez sur http://localhost:5173
2. Ouvrez les Outils Développeur (F12)
3. Cliquez sur l'onglet **Components** ou **Profiler**

### 2. **Explorer l'Arbre des Composants**
- Utilisez l'arbre pour naviguer dans la hiérarchie des composants
- Cliquez sur un composant pour voir ses **props** et **state**
- Utilisez la barre de recherche pour trouver des composants spécifiques

### 3. **Déboguer les États**
- Modifiez les valeurs de **state** directement pour tester différents scénarios
- Voyez les changements en temps réel dans l'interface
- Utilisez **Trace updates** pour voir quand les états changent

### 4. **Profiler les Performances**
1. Cliquez sur l'onglet **Profiler**
2. Cliquez sur ⚫️ **Record**
3. Interagissez avec l'application
4. Cliquez sur **Stop**
5. Analysez les commits et les durées de rendu

## 📊 COMMANDES UTILES

### Vérifier l'installation de React DevTools
```bash
python scripts/debug_react.py check
```

### Lancer l'application avec conseils de débogage
```bash
python scripts/debug_react.py launch
```

### Guide pour les problèmes courants
```bash
python scripts/debug_react.py issues
```

### Voir la hiérarchie des composants
```bash
python scripts/debug_react.py hierarchy
```

## 🔍 DÉBOGAGE COURANT

### Problèmes de Données
1. **Dans Components**, trouvez le composant concerné
2. Vérifiez les **props** - sont-elles correctement passées ?
3. Vérifiez l'**état** - y a-t-il des erreurs ?
4. Dans **Network**, regardez les erreurs réseau
5. Testez l'API directement :
   ```bash
   curl http://localhost:8050/api/brief/weekly
   ```

### Problèmes de Performance
1. **Profiler** → Record → Interagir → Stop
2. Analysez les commits avec les temps les plus longs
3. Identifiez les composants qui re-rendent inutilement
4. Vérifiez **Why did this render?** pour chaque composant

### Problèmes de Filtres
1. Dans **Components**, trouvez le composant de filtre
2. Surveillez les changements d'état lors des interactions
3. Vérifiez que les handlers d'événements sont attachés
4. Dans **Network**, vérifiez les requêtes API

## 🎯 CONSEILS POUR FINANCE COPILOT

### Dashboard
- **Composant** : `Dashboard` → `KPIsGrid` → `Card`
- **Props à surveiller** : `kpis`, `last_forecast_dt`, `tickers`
- **State à vérifier** : Filtres (sectors, horizons, themes)

### Market Brief
- **Composant** : `MarketBrief` → `TopSignals`/`TopRisks`
- **Props à surveiller** : `signals`, `risks`, `period`
- **State à vérifier** : `selectedPeriod`, `universe`

### Copilot
- **Composant** : `Copilot` → `ChatInterface`
- **Props à surveiller** : `messages`, `isLoading`
- **State à vérifier** : `question`, `sessionId`

## 📚 DOCUMENTATION COMPLÈTE

Pour une documentation complète sur React Developer Tools :
- Guide détaillé : `docs/REACT_DEVELOPER_TOOLS_GUIDE.md`
- Documentation officielle : https://react.dev/learn/react-developer-tools

## ⚡ ASTUCES RAPIDES

1. **Sélection Visuelle** : Cliquez sur 🔍 pour sélectionner un élément sur la page
2. **Recherche** : Tapez le nom d'un composant dans la barre de recherche
3. **Hotkeys** :
   - `Ctrl+F` : Rechercher un composant
   - `Ctrl+P` : Profiler
   - `Ctrl+Shift+R` : Rafraîchir l'arbre des composants

4. **Export** : Cliquez sur les icônes d'export pour sauvegarder les données