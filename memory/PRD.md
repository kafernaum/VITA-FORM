# VITA-FORM — Plateforme Pédagogique Vitaliste

## Problème original
Plateforme EdTech full-stack qui génère des parcours de formation académiques (cours, TD, études de cas, simulations) en droit et finances publiques, tous passés au crible de la **Théorie Vitaliste des Finances Publiques** du Pr. Ahmed ELY Mustapha. Cible : ENA, ENFIP, INSP de Mauritanie, Tunisie, Maroc, Algérie, Libye et France.

## Architecture
- **Frontend** : React 19 + React Router 7 + Tailwind + Shadcn/UI + **react-i18next (FR/AR bilingue)**, fontes Cormorant Garamond / Outfit / JetBrains Mono + Noto Naskh Arabic / Amiri (RTL), thème dark academia (deep blue `#0A1128` + or `#D4AF37`).
- **Backend (refactoré 10/02)** : FastAPI éclaté en modules `core/` (config, database, security, models, helpers, bootstrap) et `routers/` (auth, meta, generations, sources, rag, payments, admin). Motor (MongoDB) + JWT auth + bcrypt, Claude Sonnet 4.5 via `emergentintegrations`, ReportLab (PDF AR/FR via arabic-reshaper + python-bidi + NotoNaskhArabic) + python-docx (DOCX RTL) + HTML slides bilingues.
- **Database** : MongoDB (`users`, `generations` [+ champ `language`], `payment_transactions`, `institutions`, `jurisprudences`, `bank_accounts`, `sources`).
- **Déploiement** : Docker Compose (mongo + backend + frontend + nginx) + Nginx hôte + Let's Encrypt + script `install.sh` v2.0 interactif robuste + `manage.sh` helper.

## Personas
1. **Apprenant / fonctionnaire** : génère gratuitement des parcours en FR ou AR, paie 14,90 € pour télécharger PDF/Word/Slides.
2. **Formateur d'ENA / professeur** : utilise les TD et études de cas générés pour ses promotions.
3. **SuperAdmin** : gère utilisateurs (VIP bypass), institutions, comptes bancaires, virements pendants, revenus.

## Core requirements (MVP)
- Inscription/Connexion JWT ✅
- Page d'accueil héro + théorie + page auteur (Amazon + LinkedIn) ✅
- Générateur de cours bilingue FR/AR ✅
- Module Analyse Vitaliste (Valeur-Vie) bilingue FR/AR ✅
- Upload sources (PDF/DOCX/TXT) + extraction texte ✅
- RAG jurisprudentiel (22 entrées seedées) ✅
- Paiement PayPal (Merchant `ely.mustapha@yahoo.ca`) + IPN webhook ✅
- Paiement par virement bancaire (déclaration + validation admin) ✅
- Aperçu watermarqué + paywall PDF/DOCX/Slides ✅
- Email transactionnel Resend après paiement ✅
- Tableau de bord SuperAdmin (users + VIP + institutions + jurisprudences + comptes bancaires + virements pendants + recettes) ✅

## Implémenté (chronologie)

### 10/02/2026 — Session courante
- ♻️  **Refactor backend** : `server.py` (1189 → 60 lignes) éclaté en `core/` + `routers/`. Tous les endpoints conservés à l'identique.
- 🌍 **Bilingue FR/AR complet** :
  - i18n côté frontend (react-i18next + LanguageDetector + persistance localStorage)
  - Sélecteur de langue dans le Navbar (FR / AR pill)
  - Application automatique de `dir="rtl"` + `lang="ar"` sur `<html>`
  - Polices Noto Naskh Arabic + Amiri chargées via Google Fonts
  - CSS RTL : navbar miroir, listes/blockquotes inversées, watermark traduit
  - Pages traduites : Navbar, Footer, Landing, Auth, Generator, Library, Preview
  - Generator : sélecteur de langue de génération (FR/AR — activable pour MR/TN/MA/DZ/LY)
  - Backend : `build_course_prompt(language='ar')` ajoute instruction de rédaction en arabe littéraire moderne
  - `build_vitalist_analysis_prompt(language='ar')` idem
  - Exporters bilingues :
    - PDF : enregistrement police NotoNaskhArabic + arabic_reshaper + python-bidi pour rendu RTL correct
    - DOCX : flag `w:bidi` + alignement RTL + police Arial pour script complexe
    - HTML Slides : `dir="rtl"` + import Google Fonts Amiri/Naskh
- 🚀 **Nouveau `install.sh` v2.0** robuste pour premier déploiement :
  - Modes : `install` | `--update` | `--reconfigure` | `--skip-ssl` | `--skip-dns` | `--non-interactive`
  - Validation entrées (email, domaine, mot de passe ≥8 caractères)
  - Pre-flight checks (RAM, disque, ports 80/443/8005)
  - Logs horodatés dans `/var/log/vita-form/install-*.log`
  - Backups automatiques avant chaque `git pull` ou rewrite de `.env`
  - Healthchecks Docker pour mongo + backend
  - shellcheck-clean
- 🚀 **Nouveau `manage.sh`** : helper de production (`logs`, `restart`, `backup`, `update`, `status`, `shell-backend`, `shell-mongo`)
- 🔧 **Fix Dockerfiles** : contextes de build corrigés (root project) + ajout fonts-noto-core dans l'image backend pour rendu PDF arabe
- 🔧 **Nginx container** lié à `127.0.0.1:8005` au lieu de `0.0.0.0:8005` (sécurité — n'est plus accessible directement depuis Internet)

### 10/02/2026 — Sessions précédentes
- 22 institutions seedées (MR, TN, MA, DZ, LY, FR)
- 22 jurisprudences seedées (RAG full-text MongoDB)
- Compte admin auto-créé : `admin@vita-form.com / VitaForm2026!Admin` (VIP)
- Object Storage pour uploads de sources (Emergent)
- Resend pour emails post-paiement
- PayPal Merchant + IPN webhook
- Wire transfer flow complet
- Tableau de bord recettes
- Stripe complètement retiré

## ⚠️ État connu
- **Crédit Emergent LLM épuisé** sur le projet de preview pendant les tests du 10/02 — recharger via Profile → Universal Key → Add Balance. Le backend détecte proprement la situation et renvoie HTTP 402 avec message FR explicite.

## P0/P1/P2 backlog

**P0** : aucun.

**P1**
- [ ] Notification email Admin sur virement initié (Resend → `ely.mustapha@yahoo.ca` quand un user clique « Signaler le virement »). Enhancement proposé non encore confirmé par l'utilisateur — différé après validation P3.

**P2**
- [ ] Compléter la traduction AR sur les pages : `Theorie`, `Auteur`, `Analyse`, `PaymentSuccess`, `Admin` (clés i18n existent dans `fr.json`/`ar.json` à enrichir).
- [ ] Tableau de bord utilisateur affichant l'historique de ses paiements (PayPal + virements) en temps réel.

**Refactoring**
- [x] ✅ Split `server.py` en `core/` + `routers/`.
- [ ] Tests pytest dans `/app/backend/tests/` pour les routers (auth, generations, payments, admin).

## Clés et secrets
- Admin : `admin@vita-form.com / VitaForm2026!Admin` (cf `/app/memory/test_credentials.md`)
- `EMERGENT_LLM_KEY` dans `/app/backend/.env`
- `RESEND_API_KEY` dans `/app/backend/.env`
- PayPal merchant : `ely.mustapha@yahoo.ca` (Merchant ID `XGYL8NPMKHDUY`)
