# VITA-FORM — Plateforme Pédagogique Vitaliste

## Problème original
Plateforme EdTech full-stack qui génère des parcours de formation académiques (cours, TD, études de cas, simulations) en droit et finances publiques, tous passés au crible de la **Théorie Vitaliste des Finances Publiques** du Pr. Ahmed ELY Mustapha. Cible : ENA, ENFIP, INSP de Mauritanie, Tunisie, Maroc, Algérie, Libye et France.

## Architecture
- **Frontend** : React 19 + React Router 7 + Tailwind + Shadcn/UI, fontes Cormorant Garamond + Outfit + JetBrains Mono, thème dark academia (deep blue `#0A1128` + or `#D4AF37`).
- **Backend** : FastAPI + Motor (MongoDB) + JWT auth + bcrypt, Claude Sonnet 4.5 via `emergentintegrations`, ReportLab (PDF) + python-docx (DOCX) + HTML slides.
- **Database** : MongoDB (collections `users`, `generations`, `payments`, `institutions`).

## Personas
1. **Apprenant / fonctionnaire** : génère gratuitement des parcours, paie 14,90 € pour télécharger PDF/Word/Slides.
2. **Formateur d'ENA / professeur** : utilise les TD et études de cas générés pour ses promotions.
3. **SuperAdmin** : gère utilisateurs (VIP bypass), institutions et stats.

## Core requirements (MVP)
- Inscription/Connexion JWT ✅
- Page d'accueil héro + théorie ✅
- Page `/theorie` (doctrine vitaliste) ✅
- Page `/auteur` (bio Pr. Mustapha + photo + Amazon + LinkedIn bleu/vert) ✅
- Générateur de cours (institution, cycle, durée, sources) ✅
- Module Analyse Vitaliste (Valeur-Vie = Montant ÷ Salaire Journalier) ✅
- Aperçu watermarqué + paywall PDF/DOCX/Slides ✅
- Bibliothèque utilisateur ✅
- Tableau de bord SuperAdmin (users + VIP toggle + institutions CRUD + stats) ✅

## Implémenté (10/02/2026)
- 22 institutions seedées (MR, TN, MA, DZ, LY, FR — ENA/ENFIP/Universités/Instituts).
- Compte admin auto-créé : `admin@vita-form.com / VitaForm2026!Admin` (VIP).
- Prompt système doctrinal vitaliste ingérant les concepts du livre du Pr. Mustapha.
- Exports PDF (ReportLab), DOCX (python-docx), HTML-slides académiques.
- Paywall hermétique côté API (HTTP 402 si non-VIP non-payé).
- Mock checkout (carte/PayPal) pour MVP.

## ⚠️ MOCKED / TODO
- **Paiement** : actuellement MOCK (`/api/payments/mock-checkout`). Il faut intégrer Stripe (clé test disponible) et/ou PayPal (compte cible `ely.mustapha@yahoo.ca`, Merchant ID `XGYL8NPMKHDUY`).
- **RAG juridique** : pas encore connecté à une base de jurisprudence — le LLM s'appuie sur ses connaissances + le corpus doctrinal vitaliste.
- **Upload de PDF/sources** : pour le moment l'utilisateur colle ses sources en texte. À enrichir avec object storage + parsing.
- **Déploiement VPS port 8005 + Nginx + Certbot** : non scripté (la plateforme Emergent gère le déploiement).
- **Crédit Emergent LLM** : ⚠️ épuisé pendant les tests — recharger via Profile → Universal Key → Add Balance.

## P0/P1/P2 backlog
**P0**
- [ ] Recharger crédit Emergent LLM ou injecter la clé Anthropic du client.
- [ ] Intégration Stripe + PayPal réelle (remplacer le mock).

**P1**
- [ ] Upload de fichiers (PDF/DOCX/TXT) avec extraction texte (object storage + emergentintegrations).
- [ ] Module RAG : index Mongo Atlas Search ou Chroma sur lois/jurisprudences.
- [ ] Email transactionnel (Resend) à l'inscription et après paiement.

**P2**
- [ ] Génération multilingue (arabe pour MR/TN/MA/DZ/LY).
- [ ] Statistiques pédagogiques (progression de l'apprenant).
- [ ] Système d'invitation pour les institutions (codes promo).
- [ ] Docker-compose + script Nginx/Certbot pour VPS port 8005.

## Routes Frontend
`/`, `/auth`, `/theorie`, `/auteur`, `/generator`, `/analyse`, `/library`, `/preview/:id`, `/admin`.

## Endpoints clés
`POST /api/auth/{register,login}`, `GET /api/auth/me`, `GET /api/meta/options`, `GET /api/institutions`, `POST /api/generations`, `GET /api/generations[/:id]`, `GET /api/generations/:id/download/{pdf,docx,slides}`, `POST /api/vitalist/analyze`, `POST /api/payments/mock-checkout`, `GET/POST/DELETE /api/admin/{users,stats,generations,institutions}`.
