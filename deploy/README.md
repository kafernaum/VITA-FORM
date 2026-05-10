# VITA-FORM — Déploiement VPS

Stack containerisée pour exposer VITA-FORM sur **port 8005** derrière Nginx + SSL Let's Encrypt sur un sous-domaine de `vitae-publica.tech`.

## Pré-requis VPS (Ubuntu 22.04+)
```bash
sudo apt update && sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx
sudo systemctl enable --now docker
```

## 1. Cloner le code et configurer
```bash
git clone <repo> /opt/vita-form
cd /opt/vita-form
cp deploy/.env.production.example deploy/.env.production
nano deploy/.env.production   # remplir les vraies clés
```

## 2. Lancer la stack (frontend, backend, mongo)
```bash
cd /opt/vita-form/deploy
docker-compose --env-file .env.production up -d --build
docker-compose ps
```
Le backend FastAPI écoute en interne sur `8001`, le frontend buildé sur `3000`. Nginx (conteneur) les route et expose le **port 8005** sur l'hôte.

## 3. Reverse-proxy système Nginx + SSL Certbot
Le reverse-proxy *à l'intérieur* du conteneur écoute en HTTP. On ajoute un proxy Nginx **hôte** qui termine TLS sur 443 et forwarde vers `localhost:8005`.

```bash
sudo cp deploy/nginx-host.conf /etc/nginx/sites-available/vita-form
sudo ln -s /etc/nginx/sites-available/vita-form /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Certificat Let's Encrypt
sudo certbot --nginx -d formation.vitae-publica.tech --redirect --agree-tos -m admin@vitae-publica.tech
```

## 4. Mise à jour
```bash
cd /opt/vita-form && git pull
cd deploy && docker-compose --env-file .env.production up -d --build
```

## 5. Logs
```bash
docker-compose -f deploy/docker-compose.yml logs -f backend
docker-compose -f deploy/docker-compose.yml logs -f frontend
sudo journalctl -u nginx -f
```

## Sécurité production
- Régénérer `JWT_SECRET` (32+ caractères aléatoires).
- Régénérer `ADMIN_PASSWORD`.
- Remplacer `STRIPE_API_KEY=sk_test_emergent` par `sk_live_…` du compte production.
- Ajouter un secret webhook Stripe `STRIPE_WEBHOOK_SECRET` et configurer le webhook dans le dashboard Stripe vers `https://formation.vitae-publica.tech/api/webhook/stripe`.
- Domaine vérifié dans Resend pour envoyer depuis `noreply@vitae-publica.tech`.
- Sauvegarde Mongo : `docker exec vita-mongo mongodump -o /backup/$(date +%F)` planifié via cron.
