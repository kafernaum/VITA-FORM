#!/usr/bin/env bash
# VITA-FORM — déploiement one-click sur un VPS Ubuntu 22.04+
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f deploy/.env.production ]; then
  echo "✗ deploy/.env.production manquant. Copiez .env.production.example et remplissez les clés."
  exit 1
fi

echo "▶ Build & lancement des conteneurs (mongo, backend, frontend, nginx)…"
docker-compose -f deploy/docker-compose.yml --env-file deploy/.env.production up -d --build

echo "▶ Vérification santé backend…"
sleep 5
curl -sf http://127.0.0.1:8005/api/ && echo "  ✓ backend OK" || echo "  ✗ backend KO (voir logs)"

echo "▶ Stack disponible sur http://127.0.0.1:8005 (à mapper en SSL via Nginx + Certbot)."
echo "  Voir deploy/README.md pour le reverse-proxy hôte et le certificat Let's Encrypt."
