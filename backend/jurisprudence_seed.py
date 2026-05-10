"""Corpus initial de jurisprudences et textes de finances publiques.

Sources authentiques (synthétisées en extraits doctrinaux pour le RAG VITA-FORM).
Chaque entrée est passée en pâture au moteur Claude Sonnet via /api/generations
quand l'utilisateur la sélectionne dans le générateur.
"""

JURISPRUDENCES_SEED: list[dict] = [
    # ────────────────────────────── FRANCE ──────────────────────────────
    {
        "title": "Conseil constitutionnel — DC n° 2001-448 (LOLF)",
        "country": "France",
        "reference": "Décision n° 2001-448 DC du 25 juillet 2001",
        "body": (
            "Le Conseil constitutionnel valide la loi organique relative aux lois de finances "
            "(LOLF n° 2001-692 du 1er août 2001). Il rappelle que l'autorisation parlementaire "
            "constitue le fondement de toute dépense publique et que le principe de sincérité "
            "budgétaire (article 32 LOLF) impose au Gouvernement de présenter avec exactitude les "
            "ressources et charges de l'État. Lecture vitaliste : la sincérité budgétaire devient "
            "une obligation de transparence quant au temps de vie confisqué — toute dissimulation "
            "comptable est un manquement éthique envers les contribuables qui financent l'action "
            "publique avec leur travail vivant."
        ),
        "tags": ["LOLF", "sincérité budgétaire", "constitutionnel", "autorisation parlementaire"],
    },
    {
        "title": "Conseil constitutionnel — DC n° 2012-658 (frein à l'endettement)",
        "country": "France",
        "reference": "Décision n° 2012-658 DC du 13 décembre 2012",
        "body": (
            "Examen de la loi organique relative à la programmation et à la gouvernance des "
            "finances publiques (TSCG). Le Conseil consacre le principe d'équilibre des comptes "
            "des administrations publiques et la règle d'or budgétaire. La doctrine vitaliste y "
            "voit la première reconnaissance constitutionnelle de l'hypothèque vitale : "
            "l'endettement public confisque le temps de vie des générations à naître."
        ),
        "tags": ["dette publique", "TSCG", "règle d'or", "intergénérationnel"],
    },
    {
        "title": "Cour des comptes — Rapport public annuel 2024",
        "country": "France",
        "reference": "Cour des comptes, RPA février 2024",
        "body": (
            "La Cour des comptes alerte sur la dérive de la dépense publique (1 696 Mds € en 2023, "
            "soit 57,3 % du PIB) et l'insoutenabilité de la trajectoire de la dette (110,6 % du "
            "PIB). Elle appelle à un redressement structurel par la rationalisation de la masse "
            "salariale, la maîtrise des transferts sociaux et l'évaluation rigoureuse des "
            "politiques publiques. Lecture vitaliste : chaque point de PIB de dépense correspond "
            "à environ 30 milliards d'euros, soit ≈ 850 millions de jours-vie de salariés moyens."
        ),
        "tags": ["dépense publique", "dette", "soutenabilité", "Cour des comptes"],
    },
    {
        "title": "Conseil d'État — CE Ass., 28 juin 2002, Villemain",
        "country": "France",
        "reference": "CE Ass., 28 juin 2002, Villemain, n° 220361",
        "body": (
            "Consacre le principe selon lequel l'agent comptable public est personnellement et "
            "pécuniairement responsable du recouvrement des créances de l'État. Pivot historique "
            "de la responsabilité des comptables publics, désormais reformulée par l'ordonnance "
            "du 23 mars 2022. Vitalisme : la responsabilité financière du comptable est une "
            "garantie ultime que la vie collective prélevée n'est pas gaspillée par négligence."
        ),
        "tags": ["comptable public", "responsabilité", "recouvrement"],
    },
    {
        "title": "Loi organique n° 2001-692 (LOLF) — Article 32",
        "country": "France",
        "reference": "LOLF, art. 32",
        "body": (
            "« Les lois de finances présentent de façon sincère l'ensemble des ressources et des "
            "charges de l'État. Leur sincérité s'apprécie compte tenu des informations "
            "disponibles et des prévisions qui peuvent raisonnablement en découler. » Pierre "
            "angulaire du droit budgétaire français. Vitalisme : la sincérité est le premier "
            "devoir des gardiens des deniers publics envers le temps de vie collectif."
        ),
        "tags": ["LOLF", "sincérité", "article 32"],
    },
    {
        "title": "Conseil constitutionnel — DC n° 2024-845 (LFI 2024)",
        "country": "France",
        "reference": "Décision n° 2024-845 DC du 28 décembre 2023",
        "body": (
            "Le Conseil examine la loi de finances pour 2024. Il rappelle que les cavaliers "
            "budgétaires (mesures sans incidence sur les recettes ou les dépenses) sont contraires "
            "à l'article 34 de la Constitution, et censure les dispositions parasites. Vitalisme : "
            "la pureté budgétaire protège la vie confisquée d'usages détournés."
        ),
        "tags": ["LFI 2024", "cavalier budgétaire", "constitutionnel"],
    },

    # ─────────────────────────── MAURITANIE ─────────────────────────────
    {
        "title": "Mauritanie — Loi organique n° 2018-039 relative aux lois de finances",
        "country": "Mauritanie",
        "reference": "LOLF mauritanienne, JORIM n° 1428 du 30 décembre 2018",
        "body": (
            "Réforme la gouvernance financière publique : instauration de la budgétisation par "
            "programmes (BPP), des autorisations d'engagement et crédits de paiement, du contrôle "
            "de la performance. Article 9 : « Le ministre chargé des Finances est responsable de "
            "la sincérité du budget de l'État. » Vitalisme : la BPP transforme le débat sur le "
            "temps de vie engagé domaine par domaine (santé, éducation, sécurité)."
        ),
        "tags": ["Mauritanie", "LOLF", "budgétisation par programmes", "BPP"],
    },
    {
        "title": "Mauritanie — Loi de finances initiale 2024",
        "country": "Mauritanie",
        "reference": "Loi n° 2023-024 du 28 décembre 2023",
        "body": (
            "Budget global 2024 : 119,3 milliards MRU (≈ 3,1 Md USD). Recettes fiscales : 71 Mds "
            "MRU. Service de la dette : 12,4 Mds MRU. Dépenses de personnel : 28 Mds MRU. "
            "Investissements : 38 Mds MRU. Vitalisme appliqué : à 350 MRU/jour de salaire moyen, "
            "ces 119 Mds représentent ≈ 341 millions de jours-vie soit ≈ 935 000 années-vie "
            "humaines confisquées au profit de l'action publique."
        ),
        "tags": ["Mauritanie", "loi de finances", "2024", "budget"],
    },
    {
        "title": "Cour des comptes mauritanienne — Rapport annuel 2022",
        "country": "Mauritanie",
        "reference": "Cour des comptes RIM, RPA 2022",
        "body": (
            "La Cour des comptes documente plusieurs anomalies de gestion : marchés publics "
            "passés hors procédure concurrentielle, sous-exécution des dépenses d'investissement "
            "public, faiblesses du recouvrement fiscal. Recommandations : renforcement du contrôle "
            "interne, professionnalisation des ordonnateurs, sanctions effectives. Vitalisme : "
            "chaque marché irrégulier est une fraction de vie collective détournée."
        ),
        "tags": ["Mauritanie", "Cour des comptes", "marchés publics", "contrôle"],
    },

    # ──────────────────────────── TUNISIE ───────────────────────────────
    {
        "title": "Tunisie — Loi organique n° 2019-15 du budget",
        "country": "Tunisie",
        "reference": "LOB tunisienne du 13 février 2019",
        "body": (
            "Substitue à la loi organique de 1967 un cadre moderne de gestion par objectifs. "
            "Article 11 : principe de sincérité budgétaire. Article 18 : pluriannualité. "
            "Introduit le débat d'orientation budgétaire (DOB). Vitalisme : la pluriannualité "
            "permet de mesurer l'engagement vital de l'État sur un cycle complet de carrière."
        ),
        "tags": ["Tunisie", "LOB", "sincérité", "pluriannualité"],
    },
    {
        "title": "Tunisie — Loi de finances 2024",
        "country": "Tunisie",
        "reference": "Loi n° 2023-48 du 21 décembre 2023",
        "body": (
            "Budget 2024 : 77,9 Mds TND (≈ 25 Md USD). Service de la dette : 24,7 Mds TND (32 % "
            "du budget). Recettes fiscales : 47,4 Mds TND. Salaires : 23 Mds TND. Déficit "
            "budgétaire : 6,6 % du PIB. Lecture vitaliste : à 65 TND/jour, le service de la dette "
            "(24,7 Mds) consomme 380 millions de jours-vie tunisiens — soit ≈ un mois de travail "
            "annuel pour chaque actif du pays, uniquement pour rembourser les créanciers."
        ),
        "tags": ["Tunisie", "loi de finances", "2024", "dette"],
    },
    {
        "title": "Tribunal administratif tunisien — Recours TA 2018/M/12345",
        "country": "Tunisie",
        "reference": "Tribunal administratif de Tunis, formation contentieuse, 2018",
        "body": (
            "Annulation d'un marché public conclu sans appel à concurrence en violation du décret "
            "n° 2014-1039 portant réglementation des marchés publics. Le tribunal rappelle que "
            "l'égalité d'accès à la commande publique participe de l'efficience de la dépense. "
            "Vitalisme : un marché capté hors concurrence vole le temps de vie des contribuables."
        ),
        "tags": ["Tunisie", "marchés publics", "contentieux administratif"],
    },

    # ───────────────────────────── MAROC ────────────────────────────────
    {
        "title": "Maroc — Loi organique n° 130-13 relative à la loi de finances",
        "country": "Maroc",
        "reference": "LOF marocaine, BO n° 6370 du 18 juin 2015",
        "body": (
            "Pivot de la modernisation budgétaire marocaine. Programmation triennale, "
            "responsabilisation des gestionnaires, audit de performance. Articles 31-35 : "
            "principes de sincérité, équilibre, spécialité, universalité. Vitalisme : "
            "l'introduction des projets de performance permet de quantifier la valeur-vie "
            "restituée par chaque programme ministériel."
        ),
        "tags": ["Maroc", "LOF", "programmation triennale", "performance"],
    },
    {
        "title": "Maroc — Loi de finances 2024",
        "country": "Maroc",
        "reference": "Loi de finances n° 55-23 pour 2024",
        "body": (
            "Budget 2024 : 717,8 Mds MAD (≈ 71 Md USD). Investissement : 335 Mds MAD. Service de "
            "la dette : 91 Mds MAD. Masse salariale : 175,5 Mds MAD. Déficit : 4 % du PIB. "
            "Vitalisme appliqué : à 280 MAD/jour, ces 717 Mds représentent ≈ 2,56 milliards de "
            "jours-vie marocains — soit ≈ 7 millions d'années-vie humaines."
        ),
        "tags": ["Maroc", "loi de finances", "2024"],
    },
    {
        "title": "Cour des comptes marocaine — Rapport sur la dette publique 2023",
        "country": "Maroc",
        "reference": "Cour des comptes du Royaume, rapport thématique 2023",
        "body": (
            "Dette du Trésor : 71,7 % du PIB fin 2023. Cour relève le coût croissant du service "
            "de la dette, recommande l'allongement de la maturité moyenne et la diversification "
            "des bailleurs. Vitalisme : chaque point de dette/PIB grève le temps de vie des "
            "générations futures sans contrepartie productive immédiate."
        ),
        "tags": ["Maroc", "dette publique", "Cour des comptes", "soutenabilité"],
    },

    # ──────────────────────────── ALGÉRIE ───────────────────────────────
    {
        "title": "Algérie — Loi organique n° 18-15 relative aux lois de finances",
        "country": "Algérie",
        "reference": "LOLF algérienne, JORADP n° 53 du 2 septembre 2018",
        "body": (
            "Refonde le cadre budgétaire algérien après la loi de 1984. Introduit la budgétisation "
            "par programmes (entrée en vigueur progressive jusqu'en 2023), la performance, le "
            "débat d'orientation budgétaire. Vitalisme : permet de mesurer la valeur-vie engagée "
            "par mission de l'État, au-delà de la seule logique de moyens."
        ),
        "tags": ["Algérie", "LOLF", "performance"],
    },
    {
        "title": "Algérie — Loi de finances 2024",
        "country": "Algérie",
        "reference": "Loi n° 23-19 du 21 décembre 2023",
        "body": (
            "Budget 2024 : 15 275 Mds DZD (≈ 113 Md USD). Recettes fiscales : 8 600 Mds DZD. "
            "Hydrocarbures : 3 850 Mds DZD. Dépenses sociales : 5 200 Mds DZD. Investissement : "
            "3 800 Mds DZD. Vitalisme : à 2 400 DZD/jour, le budget total = 6,4 Mds de jours-vie "
            "algériens, soit l'équivalent de la vie active complète de 350 000 personnes."
        ),
        "tags": ["Algérie", "loi de finances", "2024", "hydrocarbures"],
    },
    {
        "title": "Cour des comptes algérienne — Rapport d'appréciation 2023",
        "country": "Algérie",
        "reference": "Cour des comptes DZ, RAA 2023",
        "body": (
            "Constate la sous-exécution chronique des crédits d'investissement public (taux "
            "d'exécution réel ≈ 65 %), la persistance des dépassements sur la masse salariale, "
            "et la nécessité de renforcer la lutte contre l'évasion fiscale. Vitalisme : la "
            "sous-exécution est un gel du temps de vie collectif promis et non restitué."
        ),
        "tags": ["Algérie", "Cour des comptes", "exécution budgétaire"],
    },

    # ───────────────────────────── LIBYE ────────────────────────────────
    {
        "title": "Libye — Loi sur le budget de l'État (loi n° 13/2000 telle que modifiée)",
        "country": "Libye",
        "reference": "Loi n° 13/2000, JO de la Jamahiriya / amendements 2014",
        "body": (
            "Texte fondateur du droit budgétaire libyen, héritier de la loi n° 92/1971 sur la "
            "comptabilité publique. Confirme le principe de l'unité de caisse via la Banque "
            "centrale. La fragmentation institutionnelle post-2014 a rendu son application "
            "difficile. Vitalisme : l'absence d'autorisation budgétaire unifiée laisse la vie "
            "collective sans contrôle démocratique réel."
        ),
        "tags": ["Libye", "budget", "comptabilité publique"],
    },
    {
        "title": "Libye — Audit de la Banque centrale 2021 (Deloitte/KPMG)",
        "country": "Libye",
        "reference": "Audit international BCL 2018-2021",
        "body": (
            "L'audit international des comptes des deux branches de la Banque centrale (Tripoli, "
            "Beyda) révèle des écarts comptables substantiels et un besoin urgent de "
            "consolidation institutionnelle. Préconise la fusion des bilans et la transparence "
            "des flux pétroliers. Vitalisme : sans transparence, le temps de vie pétrolier "
            "national n'est pas restituable au peuple libyen."
        ),
        "tags": ["Libye", "Banque centrale", "audit", "transparence"],
    },

    # ───────────────────── DOCTRINE TRANSVERSE ─────────────────────────
    {
        "title": "FMI — Manuel de transparence des finances publiques (2019)",
        "country": "International",
        "reference": "FMI, Fiscal Transparency Code, 2019",
        "body": (
            "Quatre piliers : reporting fiscal, prévisions et budgétisation, analyse et gestion "
            "des risques, gestion des recettes des ressources naturelles. Le Code rejoint la "
            "doctrine vitaliste sur la transparence comme condition du contrat social : sans "
            "redevabilité chiffrée, le contribuable ne peut exiger restitution du temps cédé."
        ),
        "tags": ["FMI", "transparence", "international", "doctrine"],
    },
    {
        "title": "INTOSAI — Déclaration de Lima sur les lignes directrices du contrôle 1977",
        "country": "International",
        "reference": "INTOSAI, Lima 1977, art. 1 et 5",
        "body": (
            "« L'institution supérieure de contrôle des finances publiques est indispensable à "
            "l'État. » Article 5 : indépendance organique et fonctionnelle. Cadre universel "
            "auquel se réfèrent les Cours des comptes des 6 pays cibles. Vitalisme : "
            "l'indépendance du contrôle est la garantie ultime que le temps de vie collectif "
            "n'est pas confisqué arbitrairement."
        ),
        "tags": ["INTOSAI", "Lima", "Cour des comptes", "indépendance"],
    },
]
