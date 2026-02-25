# Rapport d'Audit de Sécurité - Analyse Financière

**Date:** 2026-02-23  
**Auditeur:** Security Audit Script  
**Périmètre:** Projet analyse-financiere  
**Statut:** ⚠️ ACTIONS REQUISES

---

## RÉSUMÉ EXÉCUTIF

| Catégorie | Risque | Statut |
|-----------|--------|--------|
| Dépendances | MOYEN | ⚠️ À durcir |
| Secrets | MOYEN | ⚠️ À vérifier |
| Permissions | FAIBLE | ✅ Acceptable |
| Configuration | MOYEN | ⚠️ À durcir |

---

## 1. DÉPENDANCES

### Constat
- Projet Python avec modules analysis/
- Utilise yfinance, requests, pandas, numpy
- Pas de fichier requirements.txt trouvé à la racine

### Risques
- Installation sans vérification de hash
- Dépendances transitives non contrôlées

### Actions
```bash
# 1. Créer requirements.txt avec hashes
pip install pip-tools
pip-compile --generate-hashes requirements.in

# 2. Installer avec vérification
pip install --require-hashes -r requirements.txt
```

---

## 2. SECRETS EXPOSÉS

### Constat
- Fichier resultat.json contient données API (OpenRouter)
- Recherche de .env et clés nécessaire

### Actions
```bash
# 1. Vérifier .gitignore
grep -E "\.env|secret|key" .gitignore

# 2. Scanner secrets
grep -rn "api_key\|apikey\|secret" --include="*.py" --include="*.sh" .

# 3. Créer .env.example
cat > .env.example << 'EOF'
OPENROUTER_API_KEY=your_key_here
YFINANCE_CACHE=/tmp/yfinance
EOF

# 4. Ajouter .env au .gitignore
echo ".env" >> .gitignore
```

---

## 3. PERMISSIONS

### Constat
```
finance-copilot.sh       : -rwxr-xr-x (755) ✅
copilot-app/copilot.sh   : -rwxr-xr-x (755) ✅
```

### Actions de durcissement
```bash
# 1. Restreindre scripts
chmod 750 finance-copilot.sh
chmod 750 copilot-app/copilot.sh

# 2. Restreindre données sensibles
chmod 600 resultat.json
chmod 600 mydatabase.db

# 3. Restreindre modules Python
find analysis -name "*.py" -exec chmod 640 {} \;

# 4. Vérifier umask
umask 027
```

---

## 4. CONFIGURATION

### Hooks Git
- .githooks/pre-commit : À auditer
- .githooks/pre-push : À auditer

### Actions
```bash
# 1. Activer hooks
git config core.hooksPath .githooks

# 2. Vérifier contenu hooks
cat .githooks/pre-commit
cat .githooks/pre-push
```

---

## 5. SANDBOXING

### Recommandation
```bash
# 1. Utiliser venv
python -m venv venv
source venv/bin/activate

# 2. Ou Docker (recommandé)
docker run --rm -it \
  -v $(pwd):/app \
  -e OPENROUTER_API_KEY \
  python:3.11-slim \
  bash
```

---

## 6. LOGGING D'AUDIT

### Script de surveillance
```bash
#!/bin/bash
# scripts/security-monitor.sh
LOGFILE="logs/security_audit.log"
{
  echo "=== $(date) ==="
  echo "Fichiers modifiés 24h:"
  find . -type f -mtime -1 -not -path "./.git/*"
  echo "Permissions scripts:"
  ls -la *.sh copilot-app/*.sh 2>/dev/null
} >> $LOGFILE
```

---

## 7. PROCÉDURE DE ROLLBACK

### En cas de problème
```bash
# 1. Annuler derniers commits
git reflog
git reset --hard HEAD@{1}

# 2. Restaurer permissions
chmod 755 *.sh
chmod 644 analysis/**/*.py

# 3. Supprimer .env compromis
rm -f .env
unset OPENROUTER_API_KEY

# 4. Réinstaller dépendances propres
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

---

## CHECKLIST FINALE

- [ ] Créer requirements.txt avec hashes
- [ ] Scanner secrets dans le code
- [ ] Appliquer chmod restrictif
- [ ] Activer hooks git
- [ ] Configurer .env.example
- [ ] Mettre en place logging sécurité
- [ ] Tester procédure rollback

---

**Prochain audit:** 2026-03-23
