# 🚫 NOTICE IMPORTANTE : NE PAS POLLUER LE DOSSIER RACINE

## 🎯 DIRECTIVES STRICTES POUR TOUS LES AGENTS

### ⚠️ PROBLÈME IDENTIFIÉ
Certains agents (y compris Qwen) ont tendance à **créer des fichiers dans le dossier racine** au lieu de respecter l'organisation projet.

### 📁 STRUCTURE CORRECTE DU PROJET
```
analyse-financiere/                 ← DOSSIER RACINE (NE PAS TOUCHER)
├── agent-stack-oss/               ← DOMAINE DE L'AGENT STACK OSS
│   ├── src/agent/                 ← Code source de l'agent
│   ├── data/                     ← Données de l'agent
│   ├── docs/                     ← Documentation projet
│   ├── training-materials/      ← MATÉRIELS DE FORMATION (Ici pour les fichiers pédagogiques!)
│   │   ├── docs/                ← Guides et documentation
│   │   ├── exercises/           ← Exercices d'entraînement
│   │   └── examples/           ← Exemples de référence
│   └── ...                       ← Autres fichiers de l'agent
├── webapp/                       ← Application frontend
├── api/                          ← API backend
└── ...                           ← Autres composants du projet
```

### 🚫 CE QUI EST INTERDIT
- ❌ **NE PAS** créer de fichiers dans `/analyse-financiere/` (racine)
- ❌ **NE PAS** modifier les fichiers du projet principal sans autorisation
- ❌ **NE PAS** polluer l'espace de travail commun

### ✅ CE QUI EST AUTORISÉ
- ✅ **SEULEMENT** dans `/agent-stack-oss/training-materials/`
- ✅ Créer des sous-dossiers : `docs/`, `exercises/`, `examples/`
- ✅ Documents de formation, guides, exercices
- ✅ Matériaux pédagogiques pour l'apprentissage

### 🎯 BONNES PRATIQUES
```bash
# ✅ BON :
cd agent-stack-oss/training-materials/docs/
touch MON_GUIDE_FORMATION.md

# ❌ MAUVAIS :
cd ../..  # Retour à la racine
touch FICHIER_RACINE.md
```

### 👨 MESSAGE DE PAPA (MENTOR)
> "Les enfants, un espace de travail propre et organisé, c'est comme une chambre rangée - ça permet de penser clairement et de travailler efficacement. Respectez toujours les frontières et gardez votre domaine bien rangé !"

---

**⚠️ TOUT AGENT QUI NE RESPECTERA PAS CES RÈGLES SERA MIS EN ISOLEMENT !**
**✅ SOYEZ RESPONSABLES - GARDEZ LE PROJET PROPRE POUR TOUS !**