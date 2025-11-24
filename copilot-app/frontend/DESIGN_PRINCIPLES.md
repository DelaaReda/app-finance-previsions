# 🎨 Principes de Design UI - Guide Complet

**Version:** 1.0  
**Date:** 2025-11-19  
**Projet:** Finance Copilot V16 ULTIMATE

---

## 📖 Table des Matières

1. [Hiérarchie Visuelle](#1-hiérarchie-visuelle)
2. [Espacement & Respiration](#2-espacement--respiration)
3. [Alignement & Centrage](#3-alignement--centrage)
4. [Contraste & Lisibilité](#4-contraste--lisibilité)
5. [Taille & Proportions](#5-taille--proportions)
6. [Z-Index & Superposition](#6-z-index--superposition)
7. [Responsive Design](#7-responsive-design)
8. [Cohérence Visuelle](#8-cohérence-visuelle)
9. [Tester Visuellement](#9-tester-visuellement)
10. [Attention aux Détails](#10-attention-aux-détails)

---

## 1️⃣ Hiérarchie Visuelle

**Règle :** L'information la plus importante doit être la plus visible.

### ✅ À faire

- **Valeur principale** : 56-60px, centrée, font-weight: 700
- **Labels secondaires** : 11-13px, uppercase, letter-spacing: 0.5-1px
- **Valeurs secondaires** : 18-22px, font-weight: 700
- **Headers** : 13-14px, discrets, en haut

### ❌ À éviter

- Tout mettre à la même taille
- Mettre les labels aussi gros que les valeurs
- Cacher l'information importante en bas

### 📝 Exemple

```html
<!-- ✅ BON -->
<div style="text-align: center;">
  <div style="font-size: 56px; font-weight: 700;">$127,456</div>
  <div style="font-size: 13px; text-transform: uppercase;">Portfolio Value</div>
</div>

<!-- ❌ MAUVAIS -->
<div>
  <div style="font-size: 16px;">Portfolio Value</div>
  <div style="font-size: 18px;">$127,456</div>
</div>
```

---

## 2️⃣ Espacement & Respiration

**Règle :** Chaque élément doit avoir de l'espace pour "respirer".

### ✅ À faire

- **Gap entre éléments similaires** : 12-16px minimum
- **Gap entre sections** : 20-24px minimum
- **Padding interne des cartes** : 16-20px minimum
- **Margin-bottom entre blocs** : 12-24px selon l'importance

### ❌ À éviter

- Coller les éléments ensemble (gap < 8px)
- Padding insuffisant (< 12px)
- Manque d'espace entre sections

### 📊 Échelle de Spacing (Système 4-point grid)

| Valeur | Usage |
|--------|-------|
| 4px | Micro-spacing (entre icône et texte) |
| 8px | Petit gap (entre éléments très proches) |
| 12px | Gap standard (entre éléments d'une même section) |
| 16px | Gap moyen (padding de cartes, gap entre colonnes) |
| 20px | Gap large (entre sections différentes) |
| 24px | Gap très large (margin-bottom entre blocs majeurs) |
| 32px, 40px, 48px | Espacements exceptionnels |

### 📝 Exemple

```css
/* ✅ BON - Multiples de 4 */
.card {
  padding: 20px;
  gap: 12px;
  margin-bottom: 24px;
}

/* ❌ MAUVAIS - Valeurs aléatoires */
.card {
  padding: 15px;
  gap: 10px;
  margin-bottom: 22px;
}
```

---

## 3️⃣ Alignement & Centrage

**Règle :** Tout doit être aligné sur une grille invisible.

### ✅ À faire

- **Centrer visuellement** : `text-align: center` + `display: flex; justify-content: center`
- **Aligner sur la même ligne** : `align-items: center`
- **Grilles** : toujours utiliser `display: grid` pour les layouts multi-colonnes
- **Tester visuellement** : prendre un screenshot et vérifier l'alignement

### ❌ À éviter

- Utiliser `position: absolute` sans vérifier le résultat
- Oublier de centrer horizontalement ET verticalement
- Laisser des éléments décalés de quelques pixels

### 📝 Exemple

```css
/* ✅ BON - Centrage parfait */
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* ❌ MAUVAIS - Centrage incomplet */
.container {
  text-align: center; /* Seulement horizontal */
}
```

---

## 4️⃣ Contraste & Lisibilité

**Règle :** Le texte doit être **toujours lisible** sur son fond.

### ✅ À faire

- **Texte sur fond sombre** : utiliser des couleurs vives (#F59E0B, #34D399, #FFFFFF)
- **Labels importants** : ajouter un fond coloré avec opacity (rgba(245, 158, 11, 0.2))
- **Vérifier le contraste** : ratio ≥ 4.5:1 (WCAG AA)
- **Utiliser des bordures** : `border: 1px solid` pour séparer visuellement

### ❌ À éviter

- Texte gris clair sur fond sombre (illisible)
- Utiliser `var(--color-text-secondary)` pour des infos importantes
- Oublier d'ajouter un fond pour les badges

### 🎨 Palette de Couleurs

| Couleur | Hex | Usage |
|---------|-----|-------|
| Vert (Success) | `#34D399`, `#10B981`, `#22C55E` | Valeurs positives, gains |
| Orange (Warning) | `#F59E0B`, `#FB923C` | Alertes, badges importants |
| Rouge (Danger) | `#EF4444`, `#DC2626` | Pertes, erreurs |
| Bleu (Info) | `#3B82F6`, `#2563EB` | Informations neutres |
| Gris (Neutral) | `rgba(255,255,255,0.1-0.9)` | Fonds, bordures |

### 📝 Exemple

```html
<!-- ✅ BON - Badge avec fond coloré -->
<div style="
  padding: 6px 16px;
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #F59E0B;
">
  Success Rate
</div>

<!-- ❌ MAUVAIS - Texte sans fond -->
<div style="color: var(--color-text-secondary);">
  Success Rate
</div>
```

---

## 5️⃣ Taille & Proportions

**Règle :** Les éléments doivent avoir des tailles cohérentes et proportionnelles.

### ✅ À faire

- **Canvas/Images** : toujours spécifier `width` et `height` explicitement
- **Conteneurs** : utiliser `min-height` pour garantir l'espace (ex: 220px pour le donut)
- **Vérifier que le contenu tient** : le texte ne doit jamais déborder
- **Responsive** : utiliser `minmax(280px, 1fr)` pour les grilles

### ❌ À éviter

- Laisser le navigateur deviner la taille
- Utiliser `height: auto` sans `min-height`
- Créer des conteneurs trop petits pour leur contenu

### 📏 Échelle de Tailles de Police

| Taille | Usage |
|--------|-------|
| 52-60px | Mega Values (valeurs principales) |
| 22-28px | Large Values (valeurs secondaires) |
| 13-16px | Body Text (texte normal) |
| 11-12px | Small Labels (labels uppercase) |
| 10px | Tiny Text (minimum absolu, à éviter) |

### 📝 Exemple

```html
<!-- ✅ BON - Tailles explicites -->
<div style="min-height: 220px;">
  <canvas width="180" height="180"></canvas>
</div>

<!-- ❌ MAUVAIS - Pas de taille définie -->
<div>
  <canvas></canvas>
</div>
```

---

## 6️⃣ Z-Index & Superposition

**Règle :** Les éléments superposés doivent avoir un z-index clair.

### ✅ À faire

- **Arrière-plan** : `z-index: 0` ou pas de z-index
- **Contenu principal** : `z-index: 10`
- **Overlay/Modal** : `z-index: 100`
- **Toujours utiliser `position: relative`** sur le parent si on utilise `position: absolute`

### ❌ À éviter

- Utiliser `z-index: 2` (trop faible, peut être écrasé)
- Oublier de définir `position: relative` sur le parent
- Créer des conflits de z-index

### 📝 Exemple

```html
<!-- ✅ BON - Z-index clair -->
<div style="position: relative;">
  <canvas style="position: absolute; z-index: 0; opacity: 0.4;"></canvas>
  <div style="position: relative; z-index: 10;">72%</div>
</div>

<!-- ❌ MAUVAIS - Z-index confus -->
<div>
  <canvas style="position: absolute; z-index: 2;"></canvas>
  <div style="z-index: 3;">72%</div>
</div>
```

---

## 7️⃣ Responsive Design

**Règle :** Le design doit s'adapter à toutes les tailles d'écran.

### ✅ À faire

- **Grilles flexibles** : `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))`
- **Gap contrôlé** : 16-20px entre les cartes
- **Tester sur plusieurs tailles** : desktop, tablet, mobile
- **Hauteurs égales** : `height: 100%` sur les cartes dans une grille

### ❌ À éviter

- Utiliser des largeurs fixes en pixels
- Oublier de tester le responsive
- Laisser les cartes de hauteurs différentes

### 📝 Exemple

```css
/* ✅ BON - Grid responsive */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.kpi-card {
  height: 100%; /* Égalise les hauteurs */
}

/* ❌ MAUVAIS - Largeur fixe */
.kpi-row {
  display: flex;
}

.kpi-card {
  width: 400px; /* Ne s'adapte pas */
}
```

---

## 8️⃣ Cohérence Visuelle

**Règle :** Tous les widgets doivent suivre le même design system.

### ✅ À faire

- **Même structure** : Header compact → Valeur énorme → Métriques → Contexte
- **Mêmes couleurs** : Utiliser les mêmes teintes pour les mêmes types d'info
- **Mêmes espacements** : 12px, 16px, 20px, 24px (multiples de 4)
- **Mêmes typographies** : 11px, 13px, 18px, 22px, 48px, 56px

### ❌ À éviter

- Changer le design d'un widget à l'autre
- Utiliser des espacements aléatoires (13px, 17px, 23px)
- Mélanger différents styles de badges

---

## 9️⃣ Tester Visuellement

**Règle :** TOUJOURS prendre un screenshot et vérifier le résultat.

### ✅ À faire

- **Prendre un screenshot après chaque modification**
- **Vérifier pixel par pixel** : alignement, espacement, contraste
- **Comparer avec le design précédent** : est-ce mieux ?
- **Demander confirmation** : montrer le screenshot à l'utilisateur

### ❌ À éviter

- Supposer que le code est correct sans vérifier
- Ne pas prendre de screenshot
- Ignorer les détails visuels

---

## 🔟 Attention aux Détails

### A. TYPOGRAPHIE

#### Poids de Police (Font Weights)
- **700 (Bold)** : Valeurs principales, chiffres importants
- **600 (Semi-Bold)** : Labels importants, titres de sections
- **500 (Medium)** : Texte normal, headers discrets
- **400 (Regular)** : Texte secondaire (rarement utilisé)

#### Line Height
- **1.0** : Gros chiffres (52px+), titres mega
- **1.2** : Titres moyens (18-28px)
- **1.5** : Texte normal (13-16px)

#### Letter Spacing
- **0.5-0.8px** : Texte uppercase de 11-12px
- **1-1.2px** : Texte uppercase de 10px ou moins
- **0px (normal)** : Texte normal, chiffres, valeurs

### B. COULEURS & OPACITY

#### Échelle d'Opacity
- **0.05-0.1** : Fond très subtil (hover states)
- **0.1-0.2** : Fonds de badges, cartes secondaires
- **0.3-0.4** : Overlays, éléments en arrière-plan
- **0.5-0.6** : Éléments semi-visibles
- **0.7-0.85** : Éléments visibles mais discrets
- **1.0** : Éléments pleinement visibles

#### Dégradés (Gradients)
```css
/* ✅ BON - Avec compatibilité */
background: linear-gradient(135deg, #3B82F6 0%, #34D399 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text; /* Pour la compatibilité */
```

### C. BORDURES & ARRONDIS

#### Border Radius
- **4px** : Très petit (boutons compacts)
- **6px** : Petit (barres de progression)
- **8px** : Moyen (boutons standards)
- **12px** : Large (cartes, badges)
- **16px** : Très large (cartes principales)
- **20px** : Pills (badges arrondis)
- **50%** : Cercles parfaits

#### Borders
- **1px solid** : Bordure standard
- **2px solid** : Bordure épaisse (focus states)
- **Couleur** : `rgba(255,255,255,0.1-0.3)`

### D. ANIMATIONS

#### Durées (Durations)
- **100-150ms** : Micro-interactions (hover, focus)
- **200-300ms** : Transitions standards
- **400-500ms** : Animations complexes

#### Easing Functions
- **ease-in-out** : Standard, naturel
- **ease-out** : Pour les apparitions
- **ease-in** : Pour les disparitions
- **cubic-bezier(0.4, 0, 0.2, 1)** : Material Design

---

## 📋 Checklist Complète

### Avant de Valider un Design

#### Typographie
- [ ] Tailles : 11px, 13px, 18px, 22px, 52px
- [ ] Poids : 500 (headers), 600 (labels), 700 (valeurs)
- [ ] Line-height : 1.0 (gros), 1.5 (normal)
- [ ] Letter-spacing : 0.5-1px sur uppercase

#### Couleurs
- [ ] Palette cohérente (vert, orange, rouge, bleu)
- [ ] Opacity : 0.1, 0.2, 0.4, 0.85, 1.0
- [ ] Dégradés : `background-clip: text` inclus
- [ ] Contraste : ratio ≥ 4.5:1

#### Espacements
- [ ] Multiples de 4 : 8px, 12px, 16px, 20px, 24px
- [ ] Padding : 16-20px pour les cartes
- [ ] Gap : 12-16px entre éléments
- [ ] Margin-bottom : 12-24px entre blocs

#### Bordures & Arrondis
- [ ] Border-radius : 6px, 12px, 20px
- [ ] Borders : 1px solid rgba(255,255,255,0.1-0.3)
- [ ] Radius des enfants ajusté

#### Positionnement
- [ ] Position absolute : parent a `position: relative`
- [ ] Z-index : 0 (arrière), 10 (contenu), 100 (overlay)
- [ ] Centrage : flexbox avec justify-content + align-items

#### Dimensions
- [ ] Min-height défini (220px pour donut)
- [ ] Width/Height explicites pour canvas
- [ ] Height: 100% sur cartes dans grille

#### Accessibilité
- [ ] Contraste vérifié (≥ 4.5:1)
- [ ] Aria-label sur boutons
- [ ] Tabindex sur cartes

#### Tests
- [ ] Screenshot pris et vérifié
- [ ] Testé sur plusieurs tailles d'écran
- [ ] Comparé avec design précédent
- [ ] Validation utilisateur obtenue

---

## 🎯 Résumé Rapide

**Les 3 Règles d'Or :**

1. **Hiérarchie** : La valeur principale doit être ÉNORME (56px+) et centrée
2. **Espacement** : Toujours utiliser des multiples de 4 (8px, 12px, 16px, 20px, 24px)
3. **Vérification** : TOUJOURS prendre un screenshot avant de valider

**En cas de doute :**
- Plus grand vaut mieux que plus petit (pour les valeurs importantes)
- Plus d'espace vaut mieux que moins d'espace
- Plus de contraste vaut mieux que moins de contraste

---

**Dernière mise à jour :** 2025-11-19  
**Auteur :** Finance Copilot V16 ULTIMATE Team
