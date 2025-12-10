
# 📊 Equity Snapshot – Spécification “Nobel-tier” (v1)

## 0. Vue d’ensemble – Modèle d’analyse en couches

Ce document décrit la **spécification d’un snapshot d’analyse économique complet pour UNE action**.

Idée centrale :

- La **compagnie** est le **noyau** de l’oignon.
- Le **titre coté** est la peau qui interagit avec le marché.
- Autour, des **couches économiques successives** : secteur, pays, monde, géopolitique, facteurs cross-asset.
- Un **LLM** reçoit ce snapshot **déjà calculé** et se comporte comme un **analyste / gérant de portefeuille**, pas comme une calculatrice.

### 0.1. Couches principales

1. `meta_core` – identité & contexte du snapshot  
2. `layer_0_company` – l’entreprise réelle (micro, business, finances)  
3. `layer_1_instrument` – le titre coté (prix, risque, liquidité, dérivés, sentiment)  
4. `layer_2_sector_peers` – pairs, secteur & positionnement relatif  
5. `layer_3_domestic_economy` – marché local & macro du pays  
6. `layer_4_global_system` – macro & liquidité globale  
7. `layer_5_geopolitics_regulation` – géopolitique & régulation  
8. `layer_6_cross_asset_factors` – facteurs, thèmes & corrélations cross-asset  

Blocs transverses :

- `events_timeline` – ligne du temps des événements liés aux moves et aux métriques  
- `scenario_engine` – scénarios standardisés (taux, pétrole, récession, etc.)  
- `data_quality` – métadonnées de qualité / fraîcheur / complétude

> ⚠️ Règle clé : **toutes les métriques, scores et agrégations sont calculés en amont par les pipelines.**  
> Le LLM ne calcule pas, il **interprète**.

---

## 1. `meta_core` – Identité & contexte du snapshot

### 1.1. Rôle de `meta_core`

`meta_core` répond à :

> **Qu’est-ce que je regarde, où, quand, et dans quel mode d’analyse ?**

Il fournit :

- l’**identité exacte** de l’instrument (ticker, ISIN, type d’actif),
- sa **classification économique** (secteur, industrie),
- sa **géographie** (pays de domiciliation, pays de cotation, devise),
- son **rôle systémique** (appartenance à des indices, poids),
- le **contexte temporel** (date, session de marché, jour Fed/CPI/jobs, avant/après earnings),
- le **profil d’analyse** (horizon, type d’investisseur, risques à mettre en avant).

---

### 1.2. Structure globale

```jsonc
{
  "meta_core": {
    "instrument_identity": { ... },
    "economic_classification": { ... },
    "listing_and_geo": { ... },
    "index_membership": [ ... ],
    "snapshot_context": {
      "time": { ... },
      "market_session": { ... },
      "event_context": { ... }
    },
    "analysis_profile": { ... }
  }
}
```

---

### 1.3. `instrument_identity`

Identité financière de base de l’instrument.

```jsonc
"instrument_identity": {
  "ticker": "AAPL",
  "name_full": "Apple Inc.",
  "isin": "US0378331005",
  "cusip": "037833100",
  "instrument_type": "common_stock" // common_stock | adr | preferred | etf | ...
}
```

| Champ             | Type   | Obligatoire | Description                                                                 |
|-------------------|--------|------------|-----------------------------------------------------------------------------|
| `ticker`          | string | ✅         | Symbole de trading principal (ex : `"AAPL"`).                               |
| `name_full`       | string | ✅         | Nom complet coté (ex : `"Apple Inc."`).                                     |
| `isin`            | string | 🔸 fort    | Identifiant ISIN global.                                                    |
| `cusip`           | string | 🔸 fort    | Identifiant CUSIP (NA).                                                     |
| `instrument_type` | string | ✅         | `common_stock`, `adr`, `preferred`, `etf`, etc.                             |

> 🔸 *Fortement recommandé* : si non disponible, mettre la clé avec valeur `null`.

---

### 1.4. `economic_classification`

Ancrage de l’actif dans la **carte économique mondiale** (secteur / industrie).

```jsonc
"economic_classification": {
  "gics": {
    "sector": "Information Technology",
    "industry": "Technology Hardware, Storage & Peripherals",
    "sub_industry": "Technology Hardware, Storage & Peripherals"
  },
  "icb": {
    "sector": "Technology",
    "industry": "Computers"
  },
  "legacy_sector_tags": [
    "tech",
    "large_cap",
    "growth"
  ]
}
```

| Champ                      | Type     | Obligatoire | Description                                                                                       |
|----------------------------|----------|------------|---------------------------------------------------------------------------------------------------|
| `gics.sector`             | string   | ✅         | Secteur GICS.                                                                                     |
| `gics.industry`           | string   | ✅         | Industrie GICS.                                                                                   |
| `gics.sub_industry`       | string   | 🔸 fort    | Sous-industrie GICS.                                                                              |
| `icb.sector`              | string   | 🔸 fort    | Secteur ICB.                                                                                      |
| `icb.industry`           | string   | 🔸 fort    | Industrie ICB.                                                                                    |
| `legacy_sector_tags`      | string[] | optionnel  | Tags maison : `"tech"`, `"value"`, `"quality"`, `"defensive"`, etc.                              |

---

### 1.5. `listing_and_geo`

Répond à : *“Où vit juridiquement la boîte, et où se trade l’action ?”*

```jsonc
"listing_and_geo": {
  "primary_listing": {
    "exchange": "NASDAQ",
    "mic": "XNAS",
    "country": "US",
    "currency": "USD"
  },
  "company_geo": {
    "domicile_country": "US",
    "hq_country": "US",
    "hq_city": "Cupertino",
    "hq_region": "California"
  },
  "multi_listing_flags": {
    "has_secondary_listings": true,
    "secondary_listings": [
      { "exchange": "XETR", "country": "DE", "currency": "EUR", "mic": "XETR" }
    ]
  }
}
```

| Champ                                   | Type    | Obligatoire | Description                                                                                           |
|-----------------------------------------|---------|------------|-------------------------------------------------------------------------------------------------------|
| `primary_listing.exchange`              | string  | ✅         | Bourse principale (`"NASDAQ"`, `"NYSE"`, `"TSX"`, etc.).                                             |
| `primary_listing.mic`                   | string  | 🔸 fort    | MIC standard (XNAS, XNYS, XETR, …).                                                                  |
| `primary_listing.country`               | string  | ✅         | Pays de cotation principal (ISO 2 ou 3).                                                             |
| `primary_listing.currency`              | string  | ✅         | Devise de cotation principale.                                                                       |
| `company_geo.domicile_country`          | string  | ✅         | Pays de domiciliation légale de la société.                                                          |
| `company_geo.hq_country`                | string  | 🔸 fort    | Pays du siège social.                                                                                |
| `company_geo.hq_city`                   | string  | optionnel  | Ville du siège.                                                                                      |
| `company_geo.hq_region`                 | string  | optionnel  | Région / État / province.                                                                            |
| `multi_listing_flags.has_secondary_listings` | bool | ✅   | L’action possède-t-elle des listings secondaires ?                                                   |
| `secondary_listings[]`                  | array   | optionnel  | Détails des autres bourses si `has_secondary_listings = true`.                                      |

---

### 1.6. `index_membership`

Permet d’évaluer l’**importance systémique** de l’actif via les indices où il est présent.

```jsonc
"index_membership": [
  { "index": "SP500", "weight": 0.045 },
  { "index": "NASDAQ100", "weight": 0.085 },
  { "index": "MSCI_WORLD", "weight": 0.012 }
]
```

| Champ    | Type   | Obligatoire | Description                                                  |
|----------|--------|------------|--------------------------------------------------------------|
| `index`  | string | ✅         | Nom de l’indice (SP500, STOXX600, MSCI_WORLD, etc.).        |
| `weight` | number | ✅         | Poids dans l’indice (0.045 = 4.5 %).                        |

---

### 1.7. `snapshot_context.time`

Contexte temporel précis du snapshot.

```jsonc
"snapshot_context": {
  "time": {
    "snapshot_ts_utc": "2025-01-10T20:15:00Z",
    "exchange_local_time": "2025-01-10T15:15:00-05:00"
  },
  ...
}
```

| Champ               | Type   | Obligatoire | Description                                                      |
|---------------------|--------|------------|------------------------------------------------------------------|
| `snapshot_ts_utc`   | string | ✅         | Timestamp ISO 8601 en UTC.                                      |
| `exchange_local_time` | string | 🔸 fort  | Timestamp dans le fuseau de la bourse principale.               |

---

### 1.8. `snapshot_context.market_session`

État de la journée de marché.

```jsonc
"market_session": {
  "session_state": "regular",   // pre_market | regular | after_hours | holiday | closed
  "is_trading_day": true,
  "local_calendar": {
    "is_half_day": false,
    "is_local_holiday": false
  }
}
```

| Champ             | Type   | Obligatoire | Description                                                             |
|-------------------|--------|------------|-------------------------------------------------------------------------|
| `session_state`   | string | ✅         | `pre_market`, `regular`, `after_hours`, `holiday`, `closed`.           |
| `is_trading_day`  | bool   | ✅         | Le marché est-il ouvert ce jour-là ?                                   |
| `local_calendar.*`| bool   | optionnel  | Infos complémentaires (demi-journée, jour férié local, etc.).          |

---

### 1.9. `snapshot_context.event_context`

Contexte “événementiel” : earnings, Fed, CPI, jobs, guidance…

```jsonc
"event_context": {
  "relative_to_earnings": "post_earnings", // pre_earnings | post_earnings | none
  "macro_day_flags": {
    "is_fed_day": false,
    "is_cpi_day": false,
    "is_jobs_day": false
  },
  "company_event_flags": {
    "has_earnings_in_next_7d": false,
    "has_earnings_in_next_30d": false,
    "has_recent_guidance_update_7d": true
  }
}
```

| Champ                           | Type   | Obligatoire | Description                                                                 |
|---------------------------------|--------|------------|-----------------------------------------------------------------------------|
| `relative_to_earnings`         | string | ✅         | `pre_earnings`, `post_earnings`, `none`.                                    |
| `macro_day_flags.is_fed_day`   | bool   | ✅         | Jour de décision de banque centrale (Fed) ?                                 |
| `macro_day_flags.is_cpi_day`   | bool   | ✅         | Jour de publication d’inflation CPI ?                                      |
| `macro_day_flags.is_jobs_day`  | bool   | ✅         | Jour de publication des chiffres de l’emploi (NFP / jobs report) ?         |
| `company_event_flags.*`        | bool   | optionnel  | Flags sur earnings proches, update de guidance récente, etc.               |

---

### 1.10. `analysis_profile`

Définit le **mode mental** dans lequel le LLM doit analyser l’actif.

```jsonc
"analysis_profile": {
  "profile_id": "buffett_long_term",
  "horizon_target": "5y_plus",            // 1w | 1m | 3m | 1y | 3y | 5y_plus
  "risk_focus": ["drawdown", "quality"],  // ex: ["short_term_vol", "liquidity"]
  "snapshot_schema_version": "v1.0.0",
  "locale": "fr-CA"
}
```

| Champ                     | Type     | Obligatoire | Description                                                                            |
|---------------------------|----------|------------|----------------------------------------------------------------------------------------|
| `profile_id`             | string   | ✅         | Type de profil : `buffett_long_term`, `swing_trader`, `macro_overlay`, `income_investor`, etc. |
| `horizon_target`         | string   | ✅         | Horizon : `1w`, `1m`, `3m`, `1y`, `3y`, `5y_plus`.                                    |
| `risk_focus`             | string[] | optionnel  | Axes de risque à prioriser : `drawdown`, `quality`, `liquidity`, `macro`, etc.        |
| `snapshot_schema_version`| string   | ✅         | Version du schéma de snapshot.                                                        |
| `locale`                 | string   | ✅         | Locale de présentation (`"fr-CA"`, `"en-US"`, etc.).                                  |

---

### 1.11. Ce que `meta_core` garantit au LLM

Une fois `meta_core` rempli, le LLM sait déjà :

1. **Quel actif** : identifiants, type d’instrument, secteur & industrie.  
2. **Où il vit** : pays de domiciliation, pays de cotation, devise, bourse.  
3. **Son rôle systémique** : poids dans les grands indices.  
4. **À quel moment** : timestamp précis, session de marché, jour Fed/CPI/jobs, avant/après earnings.  
5. **Dans quel mode d’analyse** : profil investisseur, horizon, axes de risque à privilégier.

Les couches suivantes (`layer_0_company`, `layer_1_instrument`, etc.) se construisent **par-dessus** ce noyau.
