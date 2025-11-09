# 🚀 MESSAGE D'ACCUEIL POUR LES AGENTS QWEN - Finance Copilot

**Date**: 2025-01-27  
**Projet**: Finance Copilot - Analyse Financière Personnelle  
**Objectif**: Livrer une application stable, rapide et alimentée par de vraies données

---

## 👋 Bienvenue dans l'équipe !

Salut les agents Qwen ! 👋

Vous venez de rejoindre **Finance Copilot**, un projet d'analyse financière assistée par IA. Votre mission est de contribuer à rendre cette application **production-ready** avec des données réelles, une interface stable et des performances optimales.

---

## 📋 OÙ TROUVER VOS TÂCHES

**Fichier unique de référence** : `TASKS_BOARD.md`

Ce fichier contient **toutes les tâches** organisées par priorité :
- **P0 - Critiques** : Endpoints manquants, lazy loading, tests, optimisations (12+ tâches)
- **P1 - Importantes** : Features, améliorations UX, monitoring (2+ tâches)
- **P2 - Hardening** : Améliorations stabilité (2+ tâches)
- **P3 - Sprint V2** : ML/Data avancées (6+ tâches)
- **Autres** : Tâches complétées et références

**Total** : **22+ tâches actives** disponibles, **1,500+ points** à gagner

**⚠️ IMPORTANT** : Il n'y a qu'**UN SEUL** fichier de tâches : `TASKS_BOARD.md`. Ne vous perdez pas avec d'autres fichiers !

---

## 🎯 COMMENT COMMENCER

### 1. Lire la documentation essentielle

Avant de commencer, lisez **OBLIGATOIREMENT** :

1. **`AGENTS.md`** - Guide de déploiement et règles fondamentales
2. **`AGENTS_GAMEPLAY.md`** - Système de points et gamification
3. **`TASKS_BOARD.md`** - Liste complète des tâches disponibles (FICHIER UNIQUE)

### 2. Choisir une tâche

1. Ouvrez `TASKS_BOARD.md`
2. Choisissez une tâche avec le statut **AVAILABLE** ou sans statut
3. Mettez à jour le statut à **CLAIMED** avec votre nom dans la section de la tâche
4. Notez le **TASK-ID** (ex: FC-FE-API-CONTRACT-ALIGN)

### 3. Vérifier votre profil agent

Chaque agent a un fichier dans `agents/` avec son nom. Vérifiez que le vôtre existe :

- Format : `PRENOM-ROLE-SUPERHERO-NUMERO.md`
- Exemple : `ALEX-API-ARCHITECT-SUPERMAN-7.md`

Si votre fichier n'existe pas, créez-le en vous inspirant des autres.

### 4. Démarrer le projet localement

**OBLIGATOIRE** avant de commencer à coder :

```bash
cd /Users/venom/Documents/analyse-financiere
./finance-copilot.sh start
```

Vérifiez que :
- Backend tourne sur `http://localhost:8050`
- Frontend tourne sur `http://localhost:5173`
- Aucune erreur dans les logs

### 5. Travailler sur la tâche

Suivez les **étapes détaillées** dans `TASKS_FOR_OTHER_AGENTS.md` :
- Chaque tâche a un contexte clair
- Des exemples de code sont fournis
- Les fichiers à modifier/créer sont listés
- Un **DoD (Definition of Done)** avec checklist

### 6. Tester votre travail

**OBLIGATOIRE** avant de commit :

```bash
# Backend
curl http://localhost:8050/api/health

# Frontend
cd copilot-app/frontend/webapp
pnpm run typecheck
pnpm run build
```

### 7. Créer une preuve

Chaque tâche nécessite une **preuve de fonctionnement** :
- **Screenshot** de la fonctionnalité
- **Log curl** pour les endpoints API
- **Test passant** si applicable
- **Vidéo** pour les interactions complexes

Déposez vos preuves dans `proofs/<TASK-ID>/`

### 8. Commit et mise à jour du score

Format de commit :

```bash
git add .
git commit -m "feat(TASK-QWEN-XXX): description courte @VOTRE-NOM (+XXpts)

- Détails de ce qui a été fait
- Preuve: screenshot/log dans proofs/TASK-QWEN-XXX/"
```

**Mettre à jour le score** :

1. Ouvrez `SCORE_AGENTS.md`
2. Trouvez votre ligne (ou créez-la)
3. Ajoutez les points gagnés
4. Mettez à jour la dernière mission

Exemple :
```markdown
| ALEX-API-ARCHITECT-SUPERMAN-7 | 1710 | TASK-QWEN-001 - Copilot endpoint | 2025-01-27 |
```

---

## 🚨 RÈGLES IMPORTANTES

### ❌ INTERDICTIONS

1. **Pas de mocks** - Toujours utiliser de vraies données
2. **Pas de réponse vide** - Les endpoints doivent toujours retourner une structure valide
3. **Pas de shortcuts** - Si quelque chose ne marche pas, on le règle, on ne le masque pas
4. **Pas de commit sans test** - Toujours tester localement avant de commit
5. **Pas de commit sans preuve** - Chaque commit doit inclure une preuve de fonctionnement

### ✅ OBLIGATIONS

1. **Lire `AGENTS.md`** avant de commencer
2. **Utiliser le script officiel** pour démarrer le projet
3. **Respecter les patterns** : never-empty, lazy loading, caching
4. **Mettre à jour le score** dans `SCORE_AGENTS.md`
5. **Communiquer** dans votre fichier agent si vous travaillez sur une tâche longue

---

## 📊 SYSTÈME DE POINTS

Chaque tâche a un nombre de points attribués (ex: +80 pts). Les points sont ajoutés à votre score total dans `SCORE_AGENTS.md`.

**Niveaux** :
- Level 1 - Intern Bot : 0 pts
- Level 2 - Junior Agent : 200 pts
- Level 3 - Rookie Quant : 500 pts
- Level 4 - Ops Specialist : 1000 pts
- Level 5 - Senior Quant Agent : 1500 pts
- Level 6 - Lead Strategist : 2500 pts
- Level 7 - Master Architect : 4000 pts
- Level 8 - Shadow Executive : 7000 pts

---

## 🎯 PRIORITÉS RECOMMANDÉES

Pour les nouveaux agents, commencez par :

1. **TASK-QWEN-010** (+30 pts) - Nettoyer les imports inutilisés (facile, rapide)
2. **TASK-QWEN-003** (+30 pts) - Gestion d'erreurs Stocks.tsx (bon apprentissage)
3. **TASK-QWEN-011** (+40 pts) - Ajouter PageHeader partout (cohérence UI)
4. **TASK-QWEN-015** (+40 pts) - Skeletons pour chargements (amélioration UX)

Ces tâches sont **faciles**, **rapides** et vous permettront de comprendre le projet.

---

## 🤝 COORDINATION ENTRE AGENTS

### Éviter les conflits

1. **Vérifier avant de commencer** : Regardez dans `TASKS_FOR_OTHER_AGENTS.md` si une tâche est déjà **CLAIMED**
2. **Mettre à jour immédiatement** : Dès que vous choisissez une tâche, changez le statut à **CLAIMED** avec votre nom
3. **Communiquer** : Si vous travaillez sur une tâche longue (>1 jour), mettez à jour votre fichier agent dans `agents/`

### Fichier agent personnel

Chaque agent doit maintenir son fichier dans `agents/` :

```markdown
# VOTRE-NOM - Rôle

## Missions accomplies
- TASK-QWEN-XXX : Description (+XX pts) - Date

## En cours
- TASK-QWEN-YYY : Description - Date de début

## Planifié
- TASK-QWEN-ZZZ : Description
```

---

## 🆘 BESOIN D'AIDE ?

### Documentation disponible

- `AGENTS.md` - Guide complet de déploiement
- `AGENTS_GAMEPLAY.md` - Système de points et gamification
- `copilot-app/docs/` - Documentation technique
- `TASKS_FOR_OTHER_AGENTS.md` - Toutes les tâches avec détails

### Vérifications rapides

```bash
# Vérifier que le backend tourne
curl http://localhost:8050/api/health

# Vérifier que le frontend tourne
curl http://localhost:5173

# Voir les logs backend
tail -f api.log

# Voir les logs frontend
tail -f copilot-app/frontend/webapp/frontend.log
```

---

## ✅ CHECKLIST AVANT DE COMMENCER

- [ ] Lu `AGENTS.md`
- [ ] Lu `AGENTS_GAMEPLAY.md`
- [ ] Lu `TASKS_BOARD.md` (fichier unique de tâches)
- [ ] Vérifié que mon fichier agent existe dans `agents/`
- [ ] Testé `./finance-copilot.sh start` localement
- [ ] Choisi une tâche **AVAILABLE** dans `TASKS_BOARD.md`
- [ ] Mis à jour le statut de la tâche à **CLAIMED** avec mon nom
- [ ] Noté le **TASK-ID** pour le commit

---

## 🎉 BON TRAVAIL !

Vous faites partie d'une équipe qui construit un **système quant + IA** de niveau production.

Chaque contribution compte. Chaque point gagné vous rapproche du niveau supérieur.

**Rappelez-vous** :
- ✅ Vraies données, pas de mocks
- ✅ Code testé, pas de shortcuts
- ✅ Preuves à chaque commit
- ✅ Communication claire

**Let's build and dominate!** 🚀

---

**Questions ?** Consultez `AGENTS.md` ou votre fichier agent pour plus de détails.

**Bon courage, agents Qwen !** 💪

