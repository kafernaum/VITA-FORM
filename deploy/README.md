# VITA-FORM — Déploiement VPS

Déploiement containerisé exposant VITA-FORM sur **port 8005** (interne) avec Nginx hôte + SSL Let's Encrypt sur le sous-domaine **`vita-form.vitae-publica.tech`**.

> Répertoire d'installation cible : **`/opt/vita-form`**

## 🚀 Installation one-click (recommandée)

Sur un VPS Ubuntu 22.04+ ou Debian 12+ frais :

```bash
# 1. Cloner les sources
sudo git clone https://github.com/<votre-orga>/vita-form.git /opt/vita-form

# 2. Lancer l'installateur interactif
cd /opt/vita-form
sudo bash deploy/install.sh
```

Le script `install.sh` réalise automatiquement :
1. Vérification des pré-requis (root, OS, Internet, RAM/disque).
2. Installation de **Docker Engine officiel**, Docker Compose plugin, **Nginx**, **Certbot**, UFW, jq, openssl.
3. Configuration du pare-feu UFW (22/80/443).
4. Récupération/mise à jour du code source.
5. **Saisies interactives** : domaine, email admin, mot de passe admin, clés Emergent / Stripe / Resend, email expéditeur.
6. Génération automatique du `JWT_SECRET` (openssl rand -hex 32).
7. Vérification que le DNS du domaine pointe sur l'IP du serveur.
8. Build et lancement de la stack Docker (mongo + backend + frontend + nginx interne).
9. Configuration du **reverse-proxy Nginx hôte** sur le sous-domaine cible.
10. **Émission du certificat SSL Let's Encrypt** via Certbot + auto-renouvellement.
11. Tests fonctionnels (API, login admin, institutions, jurisprudences).
12. Résumé final avec URL, identifiants, étapes de production restantes.

Logs complets : `/var/log/vita-form-install.log`.

## 🔧 Mise à jour
```bash
cd /opt/vita-form
sudo git pull
sudo bash deploy/install.sh   # idempotent : conserve la config existante si vous le souhaitez
```

## 📁 Contenu du dossier `deploy/`
| Fichier | Rôle |
|---|---|
| `install.sh` | **Installateur interactif principal** (one-click) |
| `deploy.sh` | Script court : build + up de la stack uniquement |
| `docker-compose.yml` | Définition des 4 services (mongo, backend, frontend, nginx interne) |
| `Dockerfile.backend` | Image FastAPI + ReportLab + python-docx + emergentintegrations |
| `Dockerfile.frontend` | Build React multi-stage + Nginx Alpine |
| `nginx-container.conf` | Reverse-proxy interne (port 80 du conteneur Nginx) |
| `nginx-frontend.conf` | Servir le SPA React buildé |
| `nginx-host.conf` | Modèle pour le Nginx hôte (généré par `install.sh`) |
| `.env.production.example` | Template des variables d'environnement |
| `README.md` | Ce fichier |

## 🔐 Sécurité production
- Le `.env.production` est créé en `chmod 600` (lisible root uniquement).
- `JWT_SECRET` régénéré aléatoirement à chaque installation.
- Mot de passe admin choisi par l'utilisateur, jamais loggé en clair.
- Stripe : passez en `sk_live_…` une fois en production réelle.
- PayPal : utiliser un compte business si possible (limites plus élevées) ; activer l'IPN dans le profil PayPal (URL : `https://vita-form.vitae-publica.tech/api/webhook/paypal`).
- Resend : vérifiez votre domaine d'envoi (DNS SPF/DKIM/DMARC).

## 📜 Manuel — Configuration PayPal IPN (à faire après installation)
Le webhook est automatique : VITA-FORM passe le `notify_url` à chaque
transaction, mais PayPal expose aussi un panneau IPN global :
**Compte PayPal → Profil → Notifications de paiement instantané (IPN)** :
- **URL** : `https://vita-form.vitae-publica.tech/api/webhook/paypal`
- **Statut** : Activé (Receive IPN messages)

Le compte marchand par défaut est `ely.mustapha@yahoo.ca` (Merchant ID
`XGYL8NPMKHDUY`). Modifiable via les variables `PAYPAL_BUSINESS_EMAIL` et
`PAYPAL_MERCHANT_ID` dans `.env.production`.

## 🧰 Commandes utiles
```bash
# Logs
docker compose -f /opt/vita-form/deploy/docker-compose.yml logs -f backend
docker compose -f /opt/vita-form/deploy/docker-compose.yml logs -f frontend
sudo journalctl -u nginx -f

# Sauvegarde MongoDB
sudo docker exec vita-mongo mongodump -o /backup/$(date +%F)

# Redémarrer la stack
cd /opt/vita-form/deploy && sudo docker compose --env-file .env.production restart

# Renouveler le SSL manuellement
sudo certbot renew --nginx
```

## 🆘 Dépannage
| Symptôme | Solution |
|---|---|
| DNS ne pointe pas sur le serveur | Créer un enregistrement A `vita-form.vitae-publica.tech` → IP du VPS, attendre propagation |
| Port 8005 déjà utilisé | `sudo lsof -i :8005` puis libérer le port |
| Certbot échoue | Vérifier que le port 80 est ouvert et que le DNS est propagé ; relancer `sudo certbot --nginx -d vita-form.vitae-publica.tech` |
| Backend ne démarre pas | Vérifier `EMERGENT_LLM_KEY` valide et budget non épuisé, voir logs |
