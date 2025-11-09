# 🚀 MESSAGE D'ACCUEIL POUR LES AGENTS QWEN

**Date**: 2025-01-27  
**Projet**: Finance Copilot  
**Pour**: Tous les agents Qwen (ALEX, MICHEL, LENA, MAXIMILIAN, etc.)

---

## 👋 Salut les agents Qwen !

Bienvenue dans **Finance Copilot** ! 🎉

Vous faites partie d'une équipe qui construit un système d'analyse financière assistée par IA de niveau production.

**Votre mission** : Livrer du vrai code, avec de vraies données, sans mocks, sans shortcuts.

---

## 📋 OÙ TROUVER VOS TÂCHES ?

### ⚠️ FICHIER UNIQUE - NE VOUS PERDEZ PAS !

**UN SEUL fichier de tâches** : `TASKS_BOARD.md` (à la racine)

Ce fichier contient **79 tâches** organisées par catégorie :
- **BE-XXX** : Backend (15 tâches) - API, routes, services, cache
- **FE-XXX** : Frontend (29 tâches) - Composants, pages, hooks, UI
- **FS-XXX** : Fullstack (23 tâches) - Intégrations complètes
- **TEST-XXX** : Tests (2 tâches) - E2E, unitaires
- **DOC-XXX** : Documentation (1 tâche)
- **PERF-XXX** : Performance (3 tâches)
- **OPS-XXX** : Operations (1 tâche)
- **SEC-XXX** : Sécurité (1 tâche)
- **DATA-XXX** : Data/ML (2 tâches)
- **UI-XXX** : UI/UX (2 tâches)

**❌ IGNOREZ** : `TASKS_FOR_OTHER_AGENTS.md` (obsolète, fusionné dans TASKS_BOARD.md)

---

## 🎯 COMMENT COMMENCER ? (5 ÉTAPES)

### Étape 1 : Lire la documentation (OBLIGATOIRE)

1. **`MESSAGE_AGENTS.md`** (à la racine) - Instructions complètes
2. **`AGENTS.md`** - Guide de déploiement et règles fondamentales
3. **`AGENTS_GAMEPLAY.md`** - Système de points et gamification
4. **`TASKS_BOARD.md`** - Liste complète des 79 tâches organisées par catégorie

### Étape 2 : Vérifier votre profil agent

Chaque agent a un fichier dans `agents/` avec son nom :
- Format : `PRENOM-ROLE-SUPERHERO-NUMERO.md`
- Exemple : `ALEX-API-ARCHITECT-SUPERMAN-7.md`

Si votre fichier n'existe pas, créez-le en vous inspirant des autres.

### Étape 3 : Choisir une tâche

1. Ouvrez `TASKS_BOARD.md`
2. Cherchez une tâche avec statut **AVAILABLE**
3. **Changez immédiatement** le statut à **CLAIMED avec votre nom**
4. Notez le **TASK-ID** (ex: BE-005)

**Exemple de modification** :
```markdown
| BE-005 | ALEX-API-ARCHITECT-SUPERMAN-7 | CLAIMED | +80 | 2025-01-27 |
```

### Étape 4 : Démarrer le projet localement

**OBLIGATOIRE** avant de coder :

```bash
cd /Users/venom/Documents/analyse-financiere
./finance-copilot.sh start
```

Vérifiez que :
- ✅ Backend tourne sur `http://localhost:8050`
- ✅ Frontend tourne sur `http://localhost:5173`
- ✅ Aucune erreur dans les logs

### Étape 5 : Travailler sur la tâche

1. Suivez les **étapes détaillées** dans la tâche
2. Testez régulièrement (backend + frontend)
3. Créez une **preuve** (screenshot/log/vidéo)
4. Déposez la preuve dans `proofs/<TASK-ID>/`

---

## 💾 COMMIT ET SCORE

### Format de commit

```bash
git add .
git commit -m "feat(BE-XXX): description courte @VOTRE-NOM (+XXpts)

- Détails de ce qui a été fait
- Preuve: screenshot/log dans proofs/BE-XXX/"
```

### Mettre à jour le score

1. Ouvrez `SCORE_AGENTS.md`
2. Trouvez votre ligne (ou créez-la)
3. Ajoutez les points gagnés
4. Mettez à jour la dernière mission

**Exemple** :
```markdown
| ALEX-API-ARCHITECT-SUPERMAN-7 | 1640 | BE-005 - Copilot endpoint | 2025-01-27 |
```

---

## 🚨 RÈGLES D'OR (À RESPECTER ABSOLUMENT)

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

## 🎯 TÂCHES RECOMMANDÉES POUR DÉBUTER

Pour les nouveaux agents, commencez par ces tâches **faciles** et **rapides** :

1. **BE-007** (+30 pts) - Nettoyer les imports inutilisés (30min)
2. **FE-008** (+30 pts) - Gestion d'erreurs Stocks.tsx (1h)
3. **FE-010** (+40 pts) - Ajouter PageHeader partout (1-2h)
4. **FE-011** (+40 pts) - Skeletons pour chargements (2h)

Ces tâches vous permettront de comprendre le projet rapidement.

---

## 🤝 COORDINATION ENTRE AGENTS

### Éviter les conflits

1. **Vérifier avant de commencer** : Regardez dans `TASKS_BOARD.md` si une tâche est déjà **CLAIMED**
2. **Mettre à jour immédiatement** : Dès que vous choisissez une tâche, changez le statut à **CLAIMED** avec votre nom
3. **Communiquer** : Si vous travaillez sur une tâche longue (>1 jour), mettez à jour votre fichier agent dans `agents/`

### Fichier agent personnel

Chaque agent doit maintenir son fichier dans `agents/` :

```markdown
# VOTRE-NOM - Rôle

## ✅ Accompli
- BE-XXX : Description (+XX pts) - Date

## 🚧 En Cours
- FE-YYY : Description - Date de début

## 📅 Planifié
- FS-ZZZ : Description
```

---

## ✅ CHECKLIST AVANT DE COMMENCER

- [ ] Lu `MESSAGE_AGENTS.md` (instructions complètes)
- [ ] Lu `AGENTS.md` (règles du projet)
- [ ] Lu `AGENTS_GAMEPLAY.md` (système de points)
- [ ] Vérifié que mon fichier agent existe dans `agents/`
- [ ] Testé `./finance-copilot.sh start` localement
- [ ] Choisi une tâche **AVAILABLE** dans `TASKS_BOARD.md`
- [ ] Mis à jour le statut de la tâche à **CLAIMED** avec mon nom
- [ ] Noté le **TASK-ID** pour le commit

---

## 🆘 BESOIN D'AIDE ?

### Documentation disponible

- `MESSAGE_AGENTS.md` - Instructions complètes
- `AGENTS.md` - Guide de déploiement
- `AGENTS_GAMEPLAY.md` - Système de points
- `TASKS_BOARD.md` - Toutes les tâches avec détails (79 tâches organisées par catégorie)
- `copilot-app/docs/` - Documentation technique

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

## 🎉 BON TRAVAIL !

Vous faites partie d'une équipe qui construit un **système quant + IA** de niveau production.

Chaque contribution compte. Chaque point gagné vous rapproche du niveau supérieur.

**Rappelez-vous** :
- ✅ Vraies données, pas de mocks
- ✅ Code testé, pas de shortcuts
- ✅ Preuves à chaque commit
- ✅ Communication claire
- ✅ **UN SEUL fichier de tâches** : `TASKS_BOARD.md`

**Let's build and dominate!** 🚀

---

**Questions ?** Consultez `MESSAGE_AGENTS.md` ou votre fichier agent pour plus de détails.

**Bon courage, agents Qwen !** 💪
