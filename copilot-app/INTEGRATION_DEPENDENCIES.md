# 📦 Dépendances pour Intégration OKComputer

**Date**: 2025-11-10

---

## 🔧 Dépendances Requises

Pour que les composants OKComputer fonctionnent avec toutes les fonctionnalités, installer :

```bash
cd copilot-app/frontend/webapp
npm install clsx tailwind-merge
```

---

## ✅ Fallback Implémenté

Un **fallback** a été implémenté dans `features/okc/utils.ts` pour que le code fonctionne même sans ces packages :

- Si `clsx` et `tailwind-merge` sont disponibles → Utilise la version améliorée
- Si non disponibles → Utilise un fallback simple

**Impact** :
- ✅ Le code fonctionne immédiatement
- ⚠️ Gestion des conflits Tailwind moins intelligente sans `twMerge`
- ✅ Recommandé d'installer pour meilleure expérience

---

## 📝 Installation

```bash
# Depuis la racine du projet
cd copilot-app/frontend/webapp
npm install clsx tailwind-merge
```

---

## 🎯 Pourquoi ces packages ?

- **clsx** : Gère conditionnellement les classes CSS
- **tailwind-merge** : Résout automatiquement les conflits Tailwind (ex: `p-4` vs `p-6`)

**Exemple** :
```tsx
// Sans twMerge
cn('p-4', 'p-6') // → 'p-4 p-6' (les deux appliqués, conflit)

// Avec twMerge
cn('p-4', 'p-6') // → 'p-6' (le dernier gagne, pas de conflit)
```

---

**Status**: ⚠️ **Recommandé mais non bloquant** (fallback en place)

