#!/usr/bin/env bash
###############################################################################
# VITA-FORM — Helper de gestion (logs, restart, backup, update, status)
#
# Usage : sudo bash deploy/manage.sh [logs|restart|stop|start|backup|
#                                     update|status|shell-backend|shell-mongo]
###############################################################################

set -Eeuo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/vita-form}"

[[ -f "$ENV_FILE" ]]      || { echo "✗ $ENV_FILE introuvable. Lancer install.sh d'abord."; exit 1; }
[[ -f "$COMPOSE_FILE" ]]  || { echo "✗ $COMPOSE_FILE introuvable."; exit 1; }

dc() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

cmd="${1:-status}"
case "$cmd" in
    logs)
        shift || true
        dc logs -f --tail "${1:-200}"
        ;;
    restart)
        dc restart
        ;;
    stop)
        dc stop
        ;;
    start)
        dc up -d
        ;;
    status)
        dc ps
        echo
        echo "── Backend health ──"
        curl -s http://127.0.0.1:8005/api/ || echo "(no response)"
        echo
        ;;
    backup)
        ts="$(date +%Y%m%d-%H%M%S)"
        dest="$BACKUP_DIR/$ts"
        mkdir -p "$dest"
        echo "→ MongoDB dump → $dest/mongo"
        dc exec -T mongo sh -c "rm -rf /backup/_tmp && mongodump --quiet -o /backup/_tmp"
        docker cp vita-mongo:/backup/_tmp "$dest/mongo"
        cp "$ENV_FILE" "$dest/env.production.bak"
        chmod 600 "$dest/env.production.bak"
        echo "✓ Backup terminé : $dest"
        ;;
    update)
        if [[ -d "$DEPLOY_DIR/../.git" ]]; then
            git -C "$DEPLOY_DIR/.." pull --ff-only
        fi
        dc build --pull
        dc up -d --remove-orphans
        echo "✓ Mise à jour appliquée."
        ;;
    shell-backend)
        dc exec backend bash || dc exec backend sh
        ;;
    shell-mongo)
        dc exec mongo mongosh
        ;;
    *)
        cat <<EOF
Usage : sudo bash $(basename "$0") <commande>

  logs [N]         Suit les logs (N lignes en historique, défaut 200).
  restart          Redémarre tous les conteneurs.
  start | stop     Démarre / arrête la stack.
  status           État + ping API.
  backup           Dump MongoDB + sauvegarde de .env.production dans
                   $BACKUP_DIR/<timestamp>/
  update           git pull + rebuild + relance.
  shell-backend    Shell dans le conteneur backend.
  shell-mongo      Lance mongosh dans Mongo.
EOF
        exit 1
        ;;
esac
