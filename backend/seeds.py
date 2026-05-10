"""Seed data: Écoles Nationales d'Administration Publique (ENA) et ENFIP."""

INSTITUTIONS_SEED = [
    # Mauritanie
    {"name": "École Nationale d'Administration, de Journalisme et de Magistrature (ENAJM)", "country": "Mauritanie", "country_code": "MR", "city": "Nouakchott", "type": "ENA"},
    {"name": "Institut Supérieur de Comptabilité et d'Administration des Entreprises (ISCAE)", "country": "Mauritanie", "country_code": "MR", "city": "Nouakchott", "type": "ENFIP"},
    {"name": "Université de Nouakchott Al-Aasriya — Faculté de Sciences Juridiques et Économiques", "country": "Mauritanie", "country_code": "MR", "city": "Nouakchott", "type": "Université"},
    # Tunisie
    {"name": "École Nationale d'Administration de Tunis (ENA Tunis)", "country": "Tunisie", "country_code": "TN", "city": "Tunis", "type": "ENA"},
    {"name": "Institut Supérieur de Finances et de Fiscalité de Sousse (ISFFS)", "country": "Tunisie", "country_code": "TN", "city": "Sousse", "type": "ENFIP"},
    {"name": "École Supérieure de Commerce de Tunis (ESCT)", "country": "Tunisie", "country_code": "TN", "city": "Tunis", "type": "Institut"},
    # Maroc
    {"name": "École Nationale Supérieure d'Administration (ENSA Rabat)", "country": "Maroc", "country_code": "MA", "city": "Rabat", "type": "ENA"},
    {"name": "Institut Supérieur de l'Administration (ISA)", "country": "Maroc", "country_code": "MA", "city": "Rabat", "type": "ENA"},
    {"name": "École Nationale des Finances Publiques du Maroc", "country": "Maroc", "country_code": "MA", "city": "Rabat", "type": "ENFIP"},
    {"name": "Institut des Finances (Ministère de l'Économie et des Finances)", "country": "Maroc", "country_code": "MA", "city": "Rabat", "type": "Institut"},
    # Algérie
    {"name": "École Nationale d'Administration d'Alger (ENA Alger)", "country": "Algérie", "country_code": "DZ", "city": "Alger", "type": "ENA"},
    {"name": "École Supérieure de la Sécurité Sociale", "country": "Algérie", "country_code": "DZ", "city": "Alger", "type": "Institut"},
    {"name": "Institut Supérieur de Gestion et de Planification (ISGP)", "country": "Algérie", "country_code": "DZ", "city": "Alger", "type": "ENFIP"},
    # Libye
    {"name": "Institut National d'Administration Publique de Tripoli", "country": "Libye", "country_code": "LY", "city": "Tripoli", "type": "ENA"},
    {"name": "Académie Libyenne des Études Supérieures", "country": "Libye", "country_code": "LY", "city": "Tripoli", "type": "Institut"},
    # France
    {"name": "Institut National du Service Public (INSP, ex-ENA)", "country": "France", "country_code": "FR", "city": "Strasbourg", "type": "ENA"},
    {"name": "École Nationale des Finances Publiques (ENFiP Noisy-Vincennes)", "country": "France", "country_code": "FR", "city": "Noisy-le-Grand", "type": "ENFIP"},
    {"name": "École Nationale des Finances Publiques (ENFiP Lyon-Clermont)", "country": "France", "country_code": "FR", "city": "Lyon", "type": "ENFIP"},
    {"name": "École Nationale des Finances Publiques (ENFiP Toulouse)", "country": "France", "country_code": "FR", "city": "Toulouse", "type": "ENFIP"},
    {"name": "École de Guerre Économique (EGE)", "country": "France", "country_code": "FR", "city": "Paris", "type": "Institut"},
    {"name": "Institut de Hautes Études de Défense Nationale (IHEDN)", "country": "France", "country_code": "FR", "city": "Paris", "type": "Institut"},
    {"name": "École des Hautes Études en Sciences Sociales (EHESS)", "country": "France", "country_code": "FR", "city": "Paris", "type": "Université"},
]

CYCLES = ["Licence (L3)", "Master 1", "Master 2", "Doctorat", "Formation continue", "Cycle préparatoire ENA", "Cycle supérieur"]

DURATIONS = ["1 mois", "3 mois", "6 mois", "9 mois", "1 an", "2 ans"]

DAILY_SALARIES = {
    "MR": {"label": "Mauritanie (MRU)", "value": 350.0, "currency": "MRU"},
    "TN": {"label": "Tunisie (TND)", "value": 65.0, "currency": "TND"},
    "MA": {"label": "Maroc (MAD)", "value": 280.0, "currency": "MAD"},
    "DZ": {"label": "Algérie (DZD)", "value": 2400.0, "currency": "DZD"},
    "LY": {"label": "Libye (LYD)", "value": 95.0, "currency": "LYD"},
    "FR": {"label": "France (EUR)", "value": 130.0, "currency": "EUR"},
}
