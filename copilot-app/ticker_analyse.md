{
  "worlds_index": [
    {
      "world_id": "W0_META_ENGINES",
      "name": "Meta & Engines",
      "role": "Cerveau central : contexte, timeline, scénarios, synthèse systémique et qualité de la donnée.",
      "primary_time_horizons": ["intraday", "1-3 mois", "1-3 ans"],
      "key_risk_questions": [
        "Dans quel régime de marché et de volatilité sommes-nous ?",
        "Quels événements récents ou à venir changent le sens des autres layers ?",
        "Quels scénarios globaux doivent être testés en priorité sur ce titre/portefeuille ?",
        "À quel point je peux faire confiance aux données utilisées dans l’analyse ?"
      ],
      "grey_zones_covered": [
        "Éviter d’interpréter un move de prix sans savoir si c’est un jour Fed/CPI/jobs.",
        "Détecter les changements de régime (risk-on/off, panique, euphories) qui ne se voient pas dans une seule série.",
        "Identifier les zones où la donnée est trop pauvre ou trop révisable pour faire des conclusions fortes.",
        "S’assurer que tous les autres mondes utilisent la même chronologie et les mêmes hypothèses de scénario."
      ],
      "layers": [
        "L0_META_CORE",
        "L9_EVENTS_TIMELINE",
        "L10_SCENARIO_ENGINE",
        "L11_SYSTEMIC_RISK_ENGINE",
        "L12_DATA_QUALITY"
      ]
    },

    {
      "world_id": "W1_COMPANY",
      "name": "Company",
      "role": "Machine microéconomique pure : comment la boîte transforme inputs → cash-flows, et son risque de crédit.",
      "primary_time_horizons": ["1-3 ans", "3-10 ans"],
      "key_risk_questions": [
        "Est-ce une bonne entreprise, indépendamment du prix de l’action ?",
        "Comment résiste-t-elle aux chocs : inflation, récession, énergie, guerre commerciale ?",
        "Risque-t-elle réellement de faire défaut ou de devoir se recapitaliser dans de mauvaises conditions ?",
        "A-t-elle du pricing power, une vraie moat, ou elle vit de rentes fragiles ?"
      ],
      "grey_zones_covered": [
        "Cas où le titre est à la mode (bulle) alors que les fondamentaux sont mauvais ou inverses.",
        "Risque de refinancement silencieux : mur de dette dans 2-3 ans alors que le marché regarde seulement le prochain trimestre.",
        "Dépendance extrême à quelques clients, quelques régions, ou un seul produit (concentration cachée).",
        "Qualité comptable douteuse (accruals, restatements) qui peut exploser au prochain ralentissement."
      ],
      "layers": [
        "L1_COMPANY_CORE",
        "L1B_COMPANY_CREDIT_RISK"
      ]
    },

    {
      "world_id": "W2_INSTRUMENT_MARKET",
      "name": "Instrument & Market",
      "role": "Comment le marché price, traite, manipule ou squeeze la coquille financière (l’action/le titre).",
      "primary_time_horizons": ["intraday", "1-10 jours", "1-6 mois"],
      "key_risk_questions": [
        "Le prix actuel reflète-t-il un consensus sain ou une distorsion (flux, squeezes, manip, manque de liquidité) ?",
        "Que se passe-t-il si j’entre ou sors avec une taille institutionnelle ?",
        "Dans quels facteurs / styles / thèmes ce titre est-il réellement embed ?",
        "Quelle est sa fragilité à un changement brutal de régime (vol, facteurs, flux passifs) ?"
      ],
      "grey_zones_covered": [
        "Titres qui ont l’air calmes en daily mais sont en réalité dominés par la microstructure ou les dark pools.",
        "Rallyes ou sell-off principalement portés par des flux passifs / options plutôt que par l’info fondamentale.",
        "Situations de crowding extrême (long ou short) invisibles si tu ne regardes pas le positioning et les options.",
        "Risque de trou de liquidité (air pocket) en cas de stress global ou de retrait des market makers."
      ],
      "layers": [
        "L2_INSTRUMENT_MARKET",
        "L2B_MARKET_MICROSTRUCTURE",
        "L8_FACTORS_CROSS_ASSET",
        "L8B_MONETARY_EXPOSURE",
        "L940_MARKET_STRUCTURE_MANIPULATION_RISK",
        "L941_FLOW_AND_POSITIONING_EXTREMES",
        "L942_LIQUIDITY_CRASH_RISK"
      ]
    },

    {
      "world_id": "W3_SECTOR_COUNTRY",
      "name": "Sector & Country",
      "role": "Écosystème sectoriel + terrain de jeu domestique (économie & marché du pays).",
      "primary_time_horizons": ["6-24 mois", "3-5 ans"],
      "key_risk_questions": [
        "Est-ce un bon business dans un bon secteur, dans un bon pays… ou l’inverse ?",
        "Le secteur est-il en phase de disruption, de surcapacité ou de régulation agressive ?",
        "L’économie locale est-elle soutenable (croissance, crédit, immo, finances publiques) ?",
        "Quel est le risque social/labour dans ce pays/secteur (grèves, populisme, tensions IA/chômage) ?"
      ],
      "grey_zones_covered": [
        "Cas où l’entreprise est excellente mais prisonnière d’un secteur en déclin ou sur-régulé.",
        "Pays avec façade macro ok mais bombe à retardement : immo, crédit, chômage jeunes, polarisation politique.",
        "Chocs sectoriels type ‘régulation surprise’ (banques, big tech, pharma) qui ne se voient pas en regardant seulement un titre.",
        "Pressions sociales / labour (IA, automatisation) qui créent des risques de grèves, taxes ciblées ou backlash politique."
      ],
      "layers": [
        "L3_SECTOR_PEERS",
        "L3B_LABOUR_SOCIAL",
        "L4_MARKET_COUNTRY",
        "L5_COUNTRY_MACRO"
      ]
    },

    {
      "world_id": "W4_GLOBAL_SYSTEMS",
      "name": "Global Systems & Planet",
      "role": "Fond de décor du film : macro globale, système monétaire, planète, énergie, techno, santé, knowledge.",
      "primary_time_horizons": ["1-10 ans", "10-30 ans"],
      "key_risk_questions": [
        "Sommes-nous en phase d’expansion globale, de ralentissement ou de crise de liquidité ?",
        "Le système dollar / dettes / BRICS-or-stablecoins est-il stable ou en transition de régime ?",
        "Quelles contraintes viennent du climat, de l’énergie, des ressources critiques et de la démographie ?",
        "Qui contrôle la techno, les datas, les semi-conducteurs, la puissance IA et la capacité d’innovation ?",
        "Quels risques pandémiques ou sanitaires systémiques peuvent rebattre les cartes ?"
      ],
      "grey_zones_covered": [
        "Crises qui ne partent pas d’un pays ou d’un secteur mais du ‘plumbing’ global : dollar funding, collatéral, shadow banking.",
        "Transitions lentes mais explosives (climat, énergie, eau, métaux critiques) qui finissent par percuter certains secteurs/pays.",
        "Chocs IA / compute : pays ou blocs dépendants de stacks technos non souverains (cloud US, chips taïwanais, modèles étrangers).",
        "Pandémies ou risques sanitaires où le choc initial n’est pas économique, mais bascule tout le système.",
        "Désalignement entre là où se situe la recherche/innovation et là où sont listées les boîtes (risque de disruption exogène)."
      ],
      "layers": [
        "L6_GLOBAL_MACRO_SYSTEM",
        "L6B_HARD_MONEY_AND_MONETARY_RAILS",
        "L300_CLIMATE_PLANETARY_BOUNDARIES",
        "L310_GLOBAL_ENERGY_RESOURCES_SYSTEM",
        "L320_POPULATION_EDUCATION_MIGRATION",
        "L330_CULTURE_BELIEFS_SOCIAL_NORMS",
        "L340_GLOBAL_TECH_STACK_AND_PROTOCOLS",
        "L350_AI_COMPUTE_AND_DATA_INFRASTRUCTURE",
        "L360_GLOBAL_HEALTH_AND_PANDEMIC_RISK",
        "L370_GLOBAL_KNOWLEDGE_AND_RESEARCH_SYSTEM"
      ]
    },

    {
      "world_id": "W5_POWER_SOVEREIGN",
      "name": "Power, Politics & Sovereign",
      "role": "Qui a le pouvoir ? Qui écrit les règles ? Qui contrôle le narratif et les flux publics / souverains ?",
      "primary_time_horizons": ["2-10 ans", "10-30 ans"],
      "key_risk_questions": [
        "Cette entreprise/secteur est-il protégé par le pouvoir ou exposé à un backlash futur ?",
        "Est-ce que cet investissement est aligné avec la stratégie d’un État / fonds souverain ?",
        "Quels risques réputationnels, normatifs (religieux, ESG, droits humains) peuvent faire dérailler le case ?",
        "Quels sont les risques de sanctions, de régulation extraterritoriale ou de guerre de blocs ?"
      ],
      "grey_zones_covered": [
        "Business model qui tient uniquement parce que la régulation est laxiste… jusqu’au jour où tout change.",
        "Boîtes dépendantes de contrats publics/militaires/infra qui basculent si le pouvoir politique tourne.",
        "Conflits entre valeurs locales (religieuses, éthiques, politiques) et perception internationale (ONG, médias, ESG).",
        "Usage massif du lobbying et des liens politiques comme ‘moat’ fragile : risque de scandale, d’enquête ou de retournement politique."
      ],
      "layers": [
        "L7_GEOPOLITICS_REGULATION",
        "L900_POLITICAL_INFLUENCE_NETWORKS",
        "L910_REGULATORY_CAPTURE_RISK",
        "L920_MEDIA_NARRATIVE_IMPACT",
        "L930_SOVEREIGN_STRATEGIC_ALIGNMENT",
        "L931_LOCAL_DEVELOPMENT_IMPACT",
        "L932_VALUES_NORMS_ALIGNMENT"
      ]
    },

    {
      "world_id": "W6_PORTFOLIO",
      "name": "Portfolio View",
      "role": "Interface avec la vraie vie du PM : PnL, risques, liquidité, décisions concrètes, et robustesse des signaux.",
      "primary_time_horizons": ["intraday", "1-3 mois", "1-3 ans"],
      "key_risk_questions": [
        "Où je gagne/perds de l’argent aujourd’hui, ce mois-ci, cette année, et pourquoi ?",
        "Quels sont les vrais drivers de mon risque (facteurs, pays, thèmes, liquidité) et dépassent-ils le budget ?",
        "Que se passe-t-il sur mes positions si les principaux scénarios (W0/W4/W5) se matérialisent ?",
        "Quelles décisions concrètes sont prioritaires maintenant, avec quel impact et quelle confiance ?"
      ],
      "grey_zones_covered": [
        "Portefeuille qui a l’air diversifié en nombre de lignes mais en réalité ultra concentré sur 2-3 facteurs ou thèmes.",
        "Risque de liquidité et de fire sale sous-estimé : tout le monde détient les mêmes trucs ‘faciles à vendre’.",
        "Décisions prises sur des signaux statistiques jolis mais basés sur de la donnée fragile ou biaisée.",
        "Déconnexion entre la vue top-down (monde en crise/régime changeant) et la vue bottom-up (bon stock picking) non intégrée dans les trades."
      ],
      "layers": [
        "L1000_PORTFOLIO_CORE_OVERVIEW",
        "L1010_PORTFOLIO_RISK_ATTRIBUTION",
        "L1020_PORTFOLIO_MORNING_MOVERS",
        "L1030_PORTFOLIO_FACTOR_ROTATION",
        "L1040_PORTFOLIO_LIQUIDITY_AND_STRESS",
        "L1050_PORTFOLIO_DECISION_SUGGESTIONS",
        "L1090_PORTFOLIO_DATA_HEALTH"
      ]
    }
  ]
}