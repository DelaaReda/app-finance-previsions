# ADR-001 — Partitions Temporelles Immutables

**Date**: 2025-10-29
**Statut**: ✅ Accepté (Implémenté Sprint 1)
**Décideurs**: Équipe Dev + Reda
**Révision**: —

---

## Contexte

L'application génère des **forecasts quotidiens** (equity, commodities, macro) et des **synthèses LLM horaires**. Problèmes identifiés avec approche initiale "fichier unique":

1. **Perte d'historique**: Réécriture `forecast.parquet` → données précédentes perdues
2. **Impossibilité backtests**: Besoin historique 252+ jours pour valider stratégies
3. **Concurrence agents**: 2 agents écrivent simultanément → corruption fichier
4. **Debugging difficile**: Si bug, impossible savoir quand données générées

**Question**: Comment stocker données temporelles de façon **robuste, auditable, et extensible**?

---

## Décision

Adopter **partitions temporelles immutables** avec convention:

```
data/<domain>/dt=YYYYMMDD[HH]/<files>
```

### Règles
1. **Immutabilité**: Une fois partition `dt=YYYYMMDD` écrite, **JAMAIS réécrire**
2. **Granularité**:
   - **Quotidienne** (`YYYYMMDD`): forecasts, macro, quality, backtest
   - **Horaire** (`YYYYMMDDHH`): llm_summary (synthèses horaires)
3. **Lecture UI**: Toujours **dernière partition** (`latest_partition()` helper)
4. **Création agents**: `mkdir -p data/<domain>/dt={datetime.utcnow().strftime("%Y%m%d")}` avant écriture
5. **Nettoyage**: Optionnel, via cron (garder 90 derniers jours, archiver reste S3/glacier)

### Structure Type
```
data/
├── forecast/
│   ├── dt=20251027/
│   │   ├── forecasts.parquet
│   │   ├── final.parquet
│   │   └── commodities.parquet
│   ├── dt=20251028/
│   │   ├── forecasts.parquet
│   │   ├── final.parquet
│   │   └── commodities.parquet
│   └── dt=20251029/
│       └── ...
├── macro/
│   └── forecast/
│       ├── dt=20251027/
│       │   ├── macro_forecast.json
│       │   └── macro_forecast.parquet
│       └── dt=20251028/
│           └── ...
├── llm_summary/
│   ├── dt=2025102914/  # 29 Oct 2025, 14h
│   │   ├── summary.json
│   │   └── trace_raw.json
│   └── dt=2025102915/  # 15h
│       └── ...
├── quality/
│   ├── dt=20251027/
│   │   ├── freshness.json
│   │   └── report.json
│   └── dt=20251028/
│       └── ...
└── prices/
    └── ticker=NVDA/  # Partition par ticker (pas dt, car historique 5y fixe)
        └── prices.parquet
```

---

## Conséquences

### ✅ Positives
1. **Historique complet**: Backtests précis, évaluation forecasts vs réalisations
2. **Auditabilité**: Savoir exactement quand données générées (`dt=YYYYMMDD`)
3. **Concurrence safe**: Chaque agent écrit sa propre partition → pas de collision
4. **Rollback facile**: Si bug détecté, ignorer partition fautive, relancer agent
5. **Scaling**: Partitions facilement parallélisables (Spark, Dask si croissance data)
6. **Tests reproductibles**: Fixtures pointent vers partitions spécifiques (ex: `dt=20250101`)

### ⚠️ Négatives
1. **Stockage croissant**: ~50 MB/jour forecasts → 1.8 GB/an → **acceptable** (disque 1 TB = 500 ans)
2. **Nettoyage requis**: Cron mensuel pour archiver/supprimer vieilles partitions (> 90j)
3. **Complexité lecture**: UI doit toujours lire "dernière partition" (helpers `read_parquet_latest()` requis)
4. **Partitions vides**: Si agent échoue, partition dt créée mais vide → UI doit gérer gracefully

### 🔧 Mitigations Négatives
- **Helper `latest_partition()`**: Trouve automatiquement dernière partition (tri lexicographique `dt=` fonctionne)
- **Empty state UI**: Tous callbacks Dash gèrent `df is None or df.empty` → Alert FR ("Aucune donnée...")
- **Archivage automatique**: `make archive-old-partitions` (cron mensuel) → S3 Glacier (coût < $1/an)
- **Validation partition**: Agents écrivent `.SUCCESS` flag après écriture complète → UI ignore partitions sans flag

---

## Alternatives Rejetées

### Alternative 1: Fichier unique avec timestamp
**Approche**: `forecast_20251029.parquet`

**Rejet**:
- Impossible trouver "dernière version" efficacement (nécessite ls + tri)
- Pas de structure hiérarchique (tous fichiers même niveau → 365 fichiers/an)

### Alternative 2: Base de données SQL
**Approche**: PostgreSQL avec colonnes `generated_at TIMESTAMP`

**Rejet**:
- **Overhead**: Setup/maintenance DB
- **Dépendance externe**: Agents doivent connect DB (vs simple write parquet)
- **Perf**: Pandas → SQL slower que direct parquet write
- **Backup**: DB backup complexe vs simple `cp -r data/` ou S3 sync

### Alternative 3: Hive-style partitions (date/hour/)
**Approche**: `data/forecast/date=2025-10-29/hour=14/`

**Rejet**:
- Trop verbeux (2 niveaux vs 1)
- Format `date=YYYY-MM-DD` pas lexicographiquement triable (nécessite parsing)
- `dt=YYYYMMDDHH` plus compact, triable directement

---

## Implémentation

### Modules
- **`src/tools/parquet_io.py`**: Helpers lecture partitions
  ```python
  def latest_partition(base_dir: str) -> Optional[Path]:
      """Trouve dernière partition dt= dans base_dir."""
      partitions = sorted([p for p in Path(base_dir).glob("dt=*") if p.is_dir()], reverse=True)
      return partitions[0] if partitions else None

  def read_parquet_latest(base_dir: str, filename: str) -> Optional[pd.DataFrame]:
      """Lit fichier parquet depuis dernière partition."""
      latest = latest_partition(base_dir)
      if latest and (latest / filename).exists():
          return pd.read_parquet(latest / filename)
      return None
  ```

### Pattern Agent (écriture)
```python
from datetime import datetime
from pathlib import Path

def run_once():
    dt = datetime.utcnow().strftime("%Y%m%d")  # ou %Y%m%d%H si horaire
    outdir = Path("data/forecast") / f"dt={dt}"
    outdir.mkdir(parents=True, exist_ok=True)

    # Compute forecasts
    df = generate_forecasts()

    # Write parquet
    (outdir / "forecasts.parquet").write_parquet(df)

    # Success flag
    (outdir / ".SUCCESS").touch()
```

### Pattern UI (lecture)
```python
from src.tools.parquet_io import read_parquet_latest

def layout():
    df = read_parquet_latest("data/forecast", "final.parquet")
    if df is None or df.empty:
        return dbc.Alert("Aucune donnée de forecast disponible.", color="info")

    # Render table
    return dbc.Table.from_dataframe(df.head(10))
```

---

## Validation

### Tests
- **`tests/tools/test_parquet_io.py`**: Tests `latest_partition()`, `read_parquet_latest()`
  ```python
  def test_latest_partition_finds_newest(tmp_path):
      (tmp_path / "dt=20251027").mkdir()
      (tmp_path / "dt=20251029").mkdir()
      (tmp_path / "dt=20251028").mkdir()
      latest = latest_partition(str(tmp_path))
      assert latest.name == "dt=20251029"

  def test_read_parquet_latest_returns_none_if_missing(tmp_path):
      df = read_parquet_latest(str(tmp_path), "missing.parquet")
      assert df is None
  ```

### Monitoring
- **Freshness**: `data/quality/dt=*/freshness.json` track dernière partition par domain
- **UI Agents Status** (`/agents`): Affiche dernière `dt` par resource (forecasts, macro, llm_summary)

---

## Notes

- **Git ignore partitions**: `.gitignore` contient `data/*/dt=*` → pas commit données (trop lourd)
- **CI fixtures**: Tests utilisent `tests/fixtures/data/forecast/dt=20250101/` (commités, petits)
- **Nettoyage manuel**: `rm -rf data/forecast/dt={20241001..20241231}` (garde 2025 seulement)

---

## Références

- [Hive Partitioning](https://cwiki.apache.org/confluence/display/Hive/LanguageManual+DDL#LanguageManualDDL-PartitionedTables)
- [Parquet Best Practices](https://parquet.apache.org/docs/)
- Issue initiale: #42 "Historique forecasts perdu après chaque run"

---

**Révisions**:
- **v1.0** (2025-10-29): Décision initiale
