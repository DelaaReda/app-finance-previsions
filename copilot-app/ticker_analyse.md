# 📊 Equity Snapshot – Vue d’ensemble des couches

> Objectif : définir un **snapshot d’analyse complet pour UNE action**, structuré en couches.
>  
> L’idée : tout ce qu’un **Warren Buffett + macro trader + quant** voudraient voir **avant de prendre une décision** se trouve ici, déjà calculé, déjà nettoyé.  
> Le LLM ne sert qu’à **interpréter**, pas à calculer.

---

## 🧱 Architecture globale des couches

Pour **UNE** action, le snapshot est structuré en **9 couches** :

0. `core` – **Core & métadonnées** (ce qu’on “regarde” et dans quel contexte)
1. `instrument` – **Instrument & trading** (comment l’action se trade)
2. `company` – **Compagnie (micro)** (ce qu’un acheteur de business veut savoir)
3. `peers_sector` – **Pairs, secteur, industrie** (sa “tribu”)
4. `market_country` – **Marché & pays de cotation** (le terrain de jeu local)
5. `country_macro` – **Macro du pays principal** (ex : économie US)
6. `global_macro` – **Macro & flux globaux** (monde & grandes zones)
7. `geopolitics_regulation` – **Géopolitique & régulation**
8. `factors_cross_asset` – **Facteurs, thèmes & cross-asset**

> Chaque couche =  
> - **données brutes** (`raw`)  
> - **indicateurs dérivés** (`derived`)  
> - **scores / labels** (`scores`)  
> Dans le JSON tu peux structurer comme :  
> `layer.raw`, `layer.derived`, `layer.scores`.

---

## 0. `core` – Core & métadonnées (couche racine)

### 0.1. Identité de l’instrument

**Objectif :** être sûr à 100% de ce qu’on regarde.

Exemples de clés :

- `core.instrument_id`  
  - `ticker`  
  - `isin`  
  - `cusip`  
  - `name_full`  
  - `exchange` (ex : `"NASDAQ"`, `"NYSE"`)  
  - `currency` (ex : `"USD"`, `"CAD"`)  
  - `instrument_type` (ex : `"common_stock"`, `"adr"`, `"etf"`, `"preferred"`)

- `core.classification`
  - `sector_gics`
  - `industry_gics`
  - `sub_industry_gics`
  - `sector_icb` (optionnel)
  - `industry_icb`

- `core.indices_membership` (liste)
  - `[ { "index": "SP500", "weight": 0.0045 }, ... ]`

- `core.company_country`
  - `domicile_country`
  - `primary_listing_country`

### 0.2. Contexte du snapshot

**Objectif :** situer le snapshot dans le temps et dans le cycle de news.

- `core.snapshot_ts`
  - `utc` (ISO)
  - `exchange_local_time`

- `core.market_session`
  - `session_state` : `"pre_market" | "regular" | "after_hours" | "holiday"`
  - `is_trading_day` : true/false

- `core.event_context`
  - `relative_to_earnings` : `"pre_earnings" | "post_earnings" | "none"`
  - `is_macro_event_day` :
    - `fed_decision`, `cpi_release`, `jobs_report`, etc.
  - `notes` : champ texte

- `core.analysis_profile`
  - `profile_id` : `"buffett_long_term"`, `"swing_trader"`, `"macro_overlay"`, etc.
  - `version` : version du format de snapshot
  - `locale` : `"en-US"`, `"fr-CA"`, etc.

---

## 1. `instrument` – Instrument & trading (l’action elle-même)

### 1.1. Prix & performance

#### 1.1.1. Données brutes

- `instrument.price.raw`
  - `last`
  - `open`
  - `high`
  - `low`
  - `previous_close`
  - `intraday_high`
  - `intraday_low`
  - `market_cap`
  - `enterprise_value`
  - `shares_outstanding`
  - `free_float`
  - `restricted_shares`

#### 1.1.2. Retours multi-horizons

Horizon typiques : `1d`, `5d`, `1m`, `3m`, `6m`, `1y`, `3y`, `5y`, `10y`.

- `instrument.performance.raw`
  - `returns` :
    - `{ "horizon": "1m", "price_return": ..., "total_return": ..., "vs_benchmark": ... }[]`

- `instrument.performance.derived`
  - `cumulative_return_since_ceo`
  - `annualized_return_3y`, `5y`, `10y`
  - `alpha_vs_benchmark` (par horizon)

- `instrument.performance.scores`
  - `trend_regime` : `"uptrend" | "downtrend" | "range" | "volatile"`
  - `momentum_score` (0–100)

#### 1.1.3. Drawdowns & régimes

- `instrument.drawdowns.raw`
  - `max_drawdown_1m`, `3m`, `6m`, `1y`, `3y`, `5y`

- `instrument.drawdowns.scores`
  - `stress_level` : `"low" | "medium" | "high"`

---

### 1.2. Volatilité & risque de marché

#### 1.2.1. Volatilité réalisée

- `instrument.volatility.raw`
  - `realized_vol_10d`
  - `realized_vol_20d`
  - `realized_vol_60d`
  - `realized_vol_250d`
  - `rel_vol_vs_index_20d`, `60d`, `250d` (ratio vs indice de référence)

#### 1.2.2. Queue risk / extrêmes

- `instrument.volatility.raw`
  - `skew_realized_1y`
  - `kurtosis_1y`
  - `extreme_up_days_count` (> +3σ, 1y)
  - `extreme_down_days_count` (< –3σ, 1y)

- `instrument.volatility.derived`
  - `worst_days` : [ date, return, linked_news_id? ]

- `instrument.volatility.scores`
  - `tail_risk_score` (0–100)

---

### 1.3. Liquidité & microstructure

#### 1.3.1. Volume & turnover

- `instrument.liquidity.raw`
  - `avg_volume_1d`, `5d`, `1m`, `3m`, `6m`, `1y`
  - `avg_dollar_volume_1m`
  - `turnover_1m` (volume / free_float)

#### 1.3.2. Bid-ask & profondeur

- `instrument.liquidity.raw`
  - `avg_spread_bp_1m`
  - `min_spread_bp_1m`
  - `max_spread_bp_1m`
  - `top_of_book_depth` : `{ "bid_size": ..., "ask_size": ... }`
  - `depth_5_levels`
  - `depth_10_levels`

#### 1.3.3. Qualité d’exécution

- `instrument.liquidity.derived`
  - `avg_slippage_vs_mid`
  - `%trades_at_bid`
  - `%trades_at_ask`

- `instrument.liquidity.scores`
  - `liquidity_score` (0–100)
  - `microstructure_risk` : `"low" | "medium" | "high"`

---

### 1.4. Dérivés & structure d’options

#### 1.4.1. Vol implicite (IV)

- `instrument.options.iv.raw`
  - par horizon : `1w`, `1m`, `3m`
    - `atm_iv`
    - `otm_put_10_iv`, `otm_put_20_iv`
    - `otm_call_10_iv`, `otm_call_20_iv`

#### 1.4.2. Skew & smile

- `instrument.options.iv.derived`
  - `skew_1m` = iv(put OTM) – iv(call OTM)
  - `skew_percentile_1y`
  - `term_structure_slope` (iv_1w → iv_3m)

#### 1.4.3. Flux options & positioning

- `instrument.options.flow.raw`
  - `oi_calls_total`
  - `oi_puts_total`
  - `put_call_oi_ratio`
  - `put_call_volume_ratio`
  - `top_strikes_oi` : [ strike, type, expiry, oi ]

- `instrument.options.flow.derived`
  - `call_wall_strikes`
  - `put_floor_strikes`

#### 1.4.4. Gamma & vanna (optionnel)

- `instrument.options.greeks.derived`
  - `total_gamma_exposure`
  - `gamma_flip_zones`
  - `vanna_exposure` (si tu vas aussi loin)

---

### 1.5. Short interest & prêt de titres

- `instrument.short.raw`
  - `short_shares`
  - `short_float_pct`
  - `days_to_cover`
  - `borrow_rate`
  - `history_short_interest` (1m, 3m, 6m)

- `instrument.short.scores`
  - `squeeze_risk` : `"low" | "medium" | "high"`
  - `short_crowding_score` (0–100)

---

### 1.6. Dividendes & corporate actions

- `instrument.dividends.raw`
  - `dividend_yield`
  - `payout_ratio`
  - `dividend_history` : [ date, amount, growth_yoy ]
  - `dividend_cuts` : bool + années

- `instrument.corporate_actions.raw`
  - `splits` : [ date, ratio ]
  - `spin_offs` (détails simplifiés)

- `instrument.dividends.scores`
  - `dividend_stability_score`

---

## 2. `company` – Compagnie (micro, business & finances)

### 2.1. Identité & business model

- `company.identity`
  - `legal_name`
  - `hq_location`
  - `incorporation_country`
  - `founded_year`

- `company.business_model.raw`
  - `business_description` (texte factuel)
  - `revenue_by_segment` : [ segment_name, pct ]
  - `revenue_by_geography` : [ region, pct ]
  - `customer_concentration` : `% top10_clients` (si dispo)
  - `suppliers_concentration` (optionnel)

- `company.business_model.scores`
  - `moat_tags` : [ `"network_effects"`, `"scale"`, `"switching_costs"`, … ]
  - `moat_strength_score` (0–100)

---

### 2.2. Management & gouvernance

- `company.management.raw`
  - `ceo` : name, age, since
  - `cfo`, `coo`, `cto` (le cas échéant)
  - `c_suite_avg_tenure`

- `company.management.derived`
  - `performance_since_ceo` (annualized return)

- `company.governance.raw`
  - `board_size`
  - `independent_directors_pct`
  - `dual_class_shares` : bool + détails
  - `compensation_structure` :
    - `fixed_pct`, `variable_pct`, `equity_pct`
  - `major_legal_cases` : [ year, type, severity ]

- `company.governance.scores`
  - `governance_risk_score` (0–100)
  - `accounting_red_flags` : liste de tags

---

### 2.3. Insiders & ownership

- `company.ownership.raw`
  - `insider_ownership_pct`
  - `institutional_ownership_pct`
  - `etf_index_ownership_pct`
  - `top_institutional_holders` : [ name, pct ]

- `company.insiders.raw`
  - par horizon (`1w`, `1m`, `3m`, `6m`, `1y`, `2y`, `5y`, `10y`) :
    - `shares_bought`
    - `shares_sold`
    - `net_value_usd`
    - `buyers_count`
    - `sellers_count`

- `company.insiders.scores`
  - `insider_sentiment_1m`, `3m`, `6m`, `1y` (–1 à +1)
  - `insider_confidence_score` (0–100)

---

### 2.4. Fundamentals – P&L, bilan, cash-flow

#### 2.4.1. P&L

- `company.financials.income_statement.raw`
  - séries annuelles + trimestrielles :
    - `revenue`
    - `gross_profit`
    - `operating_income`
    - `net_income`
    - `eps_basic`, `eps_diluted`
    - `gross_margin`
    - `operating_margin`
    - `net_margin`

- `company.financials.income_statement.derived`
  - `revenue_cagr_3y`, `5y`, `10y`
  - `eps_cagr_3y`, `5y`, `10y`
  - `margin_stability_score`

#### 2.4.2. Bilan

- `company.financials.balance_sheet.raw`
  - `total_assets`
  - `total_liabilities`
  - `equity`
  - `cash_and_equivalents`
  - `total_debt`
  - `short_term_debt`
  - `long_term_debt`
  - `net_debt`

- `company.financials.balance_sheet.derived`
  - `net_debt_to_ebitda`
  - `debt_to_equity`
  - `interest_coverage`

#### 2.4.3. Cash-flow

- `company.financials.cash_flow.raw`
  - `cfo`
  - `capex`
  - `fcf`
  - `fcf_to_net_income`
  - `capex_to_revenue`
  - `rnd_to_revenue`

- `company.financials.profitability.derived`
  - `roe_ttm`, `roe_avg_5y`
  - `roa_ttm`
  - `roic_ttm`, `roic_avg_5y`
  - `roic_minus_wacc`

- `company.financials.profitability.scores`
  - `quality_score` (0–100)

---

### 2.5. Capital allocation

- `company.capital_allocation.raw`
  - `dividends_policy_summary`
  - `dividends_history` : [ year, amount, growth ]
  - `buybacks_history` : [ year, amount, pct_shares_reduced ]
  - `mna_history` : [ year, deal_size, type, notes ]

- `company.capital_allocation.scores`
  - `capital_allocation_skill_score` (0–100)

---

### 2.6. Valuation (intrinsèque & relative)

- `company.valuation.raw`
  - `pe_ttm`, `pe_forward`
  - `peg_ratio`
  - `ev_to_ebitda`
  - `ev_to_sales`
  - `price_to_sales`
  - `price_to_book`
  - `fcf_yield`
  - `earnings_yield`

- `company.valuation.derived`
  - `pe_percentile_5y`, `10y`
  - `pb_percentile_5y`
  - `ev_ebitda_percentile_5y`

- `company.valuation.relative`
  - `premium_discount_pe_vs_sector`
  - `premium_discount_ev_ebitda_vs_sector`

- `company.valuation.scores`
  - `valuation_attractiveness_score` (0–100)

---

### 2.7. Analystes, attentes & guidance

- `company.analysts.raw`
  - `coverage_count`
  - `consensus_estimates` : [ year/quarter, revenue, eps ]
  - `estimate_revisions_1m`, `3m`, `6m`
  - `target_price_mean`, `median`, `min`, `max`
  - `implied_upside_pct`

- `company.analysts.scores`
  - `street_sentiment_score` (0–100)
  - `earnings_revision_score` (0–100)

---

### 2.8. ESG & réputation

- `company.esg.raw`
  - `score_e`, `score_s`, `score_g`, `score_overall`
  - `main_controversies` : [ year, type, severity ]

- `company.esg.scores`
  - `esg_risk_score` (0–100)
  - `reputation_risk_score` (0–100)

---

## 3. `peers_sector` – Pairs, secteur & industrie

### 3.1. Univers de pairs

- `peers_sector.peers.raw`
  - `[ { ticker, name, country, sector, industry }, ... ]`
  - `peer_selection_method` : `"gics" | "manual" | "cluster_model"`

---

### 3.2. Agrégats secteur / industrie

- `peers_sector.sector_aggregates.raw`
  - `sector_performance` : returns `1m`, `3m`, `6m`, `1y`, `3y`, `5y`
  - `sector_volatility`
  - `sector_drawdown`

- `peers_sector.sector_fundamentals.raw`
  - `revenue_growth_mean`, `median`
  - `margins_mean`
  - `leverage_mean`
  - `roe_mean`, `roic_mean`
  - `pct_profitable_companies`

- `peers_sector.sector_valuation.raw`
  - `pe_mean`, `median`
  - `ev_ebitda_mean`, `median`
  - `ps_mean`, `pb_mean`

---

### 3.3. Comparaison relative

- `peers_sector.relative_ranks.derived`
  - `growth_rank`
  - `margin_rank`
  - `leverage_rank`
  - `valuation_rank`
  - `quality_rank`

- `peers_sector.relative_ranks.scores`
  - `overall_peer_rank_score` (0–100)

---

### 3.4. Sentiment & news secteur / pairs

- `peers_sector.sentiment.raw`
  - `sector_news_sentiment_24h`, `7d`, `30d`
  - `sector_news_volume_7d`, `30d`
  - `peers_average_sentiment`

- `peers_sector.sentiment.derived`
  - `stock_vs_peers_sentiment_spread`

---

### 3.5. Risques & thèmes sectoriels

- `peers_sector.risks.raw`
  - `sector_risk_tags` : ex `"regulatory_pressure"`, `"disruption"`, `"cyclical_demand"`

- `peers_sector.themes.raw`
  - `[ { theme: "AI", exposure: "high" }, { theme: "energy_transition", exposure: "medium" } ]`

---

## 4. `market_country` – Marché & pays de cotation

### 4.1. Indice local & breadth

- `market_country.benchmark.raw`
  - `index_name`
  - `index_returns` : `1m`, `3m`, `6m`, `1y`, `3y`, `5y`, `10y`
  - `index_volatility`
  - `index_drawdown`

- `market_country.breadth.raw`
  - `pct_stocks_above_200dma`
  - `pct_new_52w_highs`
  - `pct_new_52w_lows`
  - `advance_decline_ratio`

---

### 4.2. Flows & structure

- `market_country.flows.raw`
  - `etf_flows_1m`, `3m`
  - `foreign_investor_net_flows`
  - `index_concentration_top10`

---

### 4.3. Country risk & FX

- `market_country.country_risk.raw`
  - `sovereign_rating`
  - `cds_spread_5y`

- `market_country.fx.raw`
  - `fx_pair_vs_usd`
  - `fx_return_1m`, `6m`, `1y`
  - `fx_volatility_1y`
  - `fx_regime` : `"appreciating" | "depreciating" | "range"`

---

## 5. `country_macro` – Macro du pays

### 5.1. Croissance & cycle

- `country_macro.growth.raw`
  - `gdp_yoy`
  - `gdp_qoq_annualized`
  - `pmi_manufacturing`
  - `pmi_services`
  - `leading_indicators_index`
  - `output_gap_proxy`

### 5.2. Consommation & emploi

- `country_macro.consumption_labour.raw`
  - `retail_sales_growth`
  - `unemployment_rate`
  - `labour_participation_rate`
  - `wage_growth_yoy`
  - `consumer_confidence_index`

### 5.3. Inflation

- `country_macro.inflation.raw`
  - `cpi_headline_yoy`
  - `cpi_core_yoy`
  - `pce_headline_yoy` (US)
  - `pce_core_yoy`
  - `distance_from_central_bank_target`

---

### 5.4. Immobilier & crédit

- `country_macro.housing_credit.raw`
  - `house_price_index_yoy`
  - `mortgage_rates`
  - `housing_starts`
  - `building_permits`
  - `credit_growth`
  - `non_performing_loans_ratio` (si dispo)

---

### 5.5. Budget & finances publiques

- `country_macro.fiscal.raw`
  - `budget_deficit_pct_gdp`
  - `public_debt_pct_gdp`
  - `major_fiscal_programs_summary`
  - `election_calendar`

---

### 5.6. Politique monétaire locale

- `country_macro.monetary_policy.raw`
  - `policy_rate_current`
  - `recent_rate_changes` : [ date, change_bps ]
  - `yield_curve` : `y2`, `y10`, `y30`, `slope_2_10`

---

## 6. `global_macro` – Macro & flux globaux

### 6.1. Croissance globale & zones

- `global_macro.growth.raw`
  - `world_gdp_growth`
  - `us_growth`
  - `europe_growth`
  - `china_growth`
  - `emerging_markets_growth`
  - `global_pmi`

---

### 6.2. Liquidité globale & risk appetite

- `global_macro.liquidity.raw`
  - `global_financial_conditions_index`
  - `global_credit_impulse`
  - `vix`
  - `move_index`
  - `fx_vol_index` (si dispo)

---

### 6.3. Banques centrales majeures

- `global_macro.central_banks.raw`
  - pour chaque : `fed`, `ecb`, `boj`, `boe`, etc.
    - `policy_rate`
    - `balance_sheet_size`
    - `last_decisions` : [ date, action ]
    - `market_implied_probs` (hike/cut)

---

## 7. `geopolitics_regulation` – Géopolitique & régulation

### 7.1. Géopolitique

- `geopolitics_regulation.geopolitics.raw`
  - `ongoing_conflicts` : [ region, intensity, notes ]
  - `us_china_tensions_score`
  - `company_revenue_in_risk_zones_pct`
  - `supply_chain_risk_regions`

---

### 7.2. Régulation

- `geopolitics_regulation.regulation.raw`
  - `sector_regulations_current` : [ name, desc, impact_level ]
  - `upcoming_regulations_risk` : [ description, probability, impact ]
  - `sanctions_risk` : [ country, type, exposure ]

- `geopolitics_regulation.regulation.scores`
  - `regulatory_risk_score` (0–100)

---

## 8. `factors_cross_asset` – Facteurs, thèmes & cross-asset

### 8.1. Facteurs de style

- `factors_cross_asset.style_factors.raw`
  - `beta_market`
  - `size_factor_exposure`
  - `value_factor_exposure`
  - `growth_factor_exposure`
  - `quality_factor_exposure`
  - `momentum_factor_exposure`
  - `low_vol_factor_exposure`

- `factors_cross_asset.style_factors.scores`
  - `factor_risk_concentration_score`

---

### 8.2. Thèmes

- `factors_cross_asset.themes.raw`
  - `[ { theme: "AI", exposure: "high" }, { theme: "defense", exposure: "low" } ]`
  - `theme_exposure_method` : `"revenue_based" | "index_membership" | "nlp_mapping"`

---

### 8.3. Cross-asset & corrélations

- `factors_cross_asset.correlations.raw`
  - `equity_indices` : [ index, corr_6m, corr_1y ]
  - `rates` : [ tenor (ex "US10Y"), corr_6m, corr_1y ]
  - `commodities` : [ "WTI", "GOLD", … ]
  - `fx_pairs` : [ pair, corr_6m, corr_1y ]

- `factors_cross_asset.sensitivities.derived`
  - `sensitivity_to_rates_10y`
  - `sensitivity_to_oil`
  - `sensitivity_to_key_fx_pair`

---

## 🧠 Comment utiliser ce snapshot avec un LLM

1. **Tout ce qui est chiffres / historique / macro est calculé avant.**
2. Le LLM reçoit **le snapshot complet** (ou une vue compressée).
3. Tu peux ensuite lui demander :
   - “Explique-moi le profil risque/rendement de ce titre.”
   - “Comment il se compare à ses pairs sur 5 ans, fondamentalement ?”
   - “Qu’est-ce qui pourrait casser ce titre à court/moyen/long terme ?”
   - “Quelles conditions macro/marché sont favorables ou défavorables ?”

Et là, le modèle agit comme **un vrai analyste** avec un **dossier ultra-complet** sur la table – sans halluciner des chiffres.

---