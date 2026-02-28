# Security Allowlist - Analyse Financière

## Date: 2026-02-23
## Statut: ACTIF

---

## 1. DÉPENDANCES PYTHON AUTORISÉES

### Core (validées)
```
requests>=2.28.0          # HTTP - source: pypi.org
numpy>=1.21.0             # Calcul - source: pypi.org
pandas>=1.3.0             # Data - source: pypi.org
scikit-learn>=1.0.0       # ML - source: pypi.org
yfinance>=0.2.0           # Données financières - source: pypi.org
python-dotenv>=0.19.0     # Env vars - source: pypi.org
```

### Analyse technique (validées)
```
ta-lib                      # Technical analysis
pandas-ta                   # pandas technical analysis
```

---

## 2. SCRIPTS AUTORISÉS À L'EXÉCUTION

| Script | Hash SHA256 | Permissions | Usage |
|--------|-------------|-------------|-------|
| finance-copilot.sh | À VÉRIFIER | 755 | Wrapper principal |
| copilot-app/copilot.sh | À VÉRIFIER | 755 | Application copilot |

---

## 3. COMPOSANTS MÉTIER VALIDÉS

### Modules analysis/
```
analysis/shared/data_access_io.py           # OK - Accès données
analysis/shared/config_loader.py            # OK - Configuration
analysis/shared/logging_utils.py            # OK - Logging
```

### Pipelines
```
pipelines/single_name_equity_full_analysis_pipeline.py
pipelines/country_and_sector_risk_monitoring_pipeline.py
```

---

## 4. SOURCES DE DONNÉES AUTORISÉES

| Source | Type | Validation |
|--------|------|------------|
| Yahoo Finance | API publique | ✅ OK |
| FRED (Federal Reserve) | API publique | ✅ OK |
| OpenRouter (LLM) | API payante | ⚠️ Clé requise |

---

## 5. BLOQUÉ PAR DÉFAUT

- Installation pip sans --require-hashes
- Exécution de code distant non vérifié
- Scripts non listés ci-dessus
- Connexions sortantes non whitelistées

---

## 6. PROCÉDURE D'AJOUT

1. Vérifier la provenance (PyPI officiel, GitHub officiel)
2. Vérifier les dépendances transitives
3. Ajouter hash SHA256 dans requirements.txt
4. Tester en environnement isolé
5. Commit avec signature
