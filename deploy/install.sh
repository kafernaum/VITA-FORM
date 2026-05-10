#!/usr/bin/env bash
###############################################################################
#                                                                             #
#   VITA-FORM — Installateur interactif de production                         #
#   Cible : Ubuntu 22.04+ ou Debian 12+ (root requis)                         #
#   Répertoire d'installation : /opt/vita-form                                #
#                                                                             #
#   Usage : sudo bash deploy/install.sh                                       #
#                                                                             #
###############################################################################

set -Eeuo pipefail

###############################################################################
# Constantes & helpers
###############################################################################
APP_DIR="/opt/vita-form"
DEPLOY_DIR="$APP_DIR/deploy"
ENV_FILE="$DEPLOY_DIR/.env.production"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
LOG_FILE="/var/log/vita-form-install.log"
STEP=0
TOTAL_STEPS=10

# Couleurs ANSI
if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'
    C_GOLD=$'\033[38;5;220m'; C_CYAN=$'\033[36m'
    C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
else
    C_RESET=""; C_BOLD=""; C_DIM=""; C_GOLD=""; C_CYAN=""
    C_GREEN=""; C_RED=""; C_YELLOW=""
fi

banner() {
    cat <<EOF
${C_GOLD}${C_BOLD}
   ╔═══════════════════════════════════════════════════════════════╗
   ║            VITA-FORM · DOCTRINA VITALIS                       ║
   ║            Installateur interactif — production VPS           ║
   ║            Pr. Ahmed ELY Mustapha                             ║
   ╚═══════════════════════════════════════════════════════════════╝
${C_RESET}
EOF
}

step() {
    STEP=$((STEP + 1))
    echo
    echo "${C_GOLD}${C_BOLD}━━━ Étape ${STEP}/${TOTAL_STEPS} : $1 ━━━${C_RESET}"
}
info()    { echo "${C_CYAN}ℹ${C_RESET}  $*"; }
success() { echo "${C_GREEN}✓${C_RESET}  $*"; }
warn()    { echo "${C_YELLOW}⚠${C_RESET}  $*"; }
fail()    { echo "${C_RED}✗${C_RESET}  $*" >&2; }
fatal()   { fail "$*"; exit 1; }

trap 'fail "Erreur ligne $LINENO. Logs : $LOG_FILE"; exit 1' ERR

# Capture stdout/stderr dans le log
exec > >(tee -a "$LOG_FILE") 2>&1

###############################################################################
# Saisies utilisateur
###############################################################################
ask() {
    # ask "Question ?" "valeur_par_défaut" "VAR_NAME"
    local prompt="$1" default="$2" varname="$3" reply
    if [[ -n "$default" ]]; then
        read -rp "${C_BOLD}${prompt}${C_RESET} ${C_DIM}[$default]${C_RESET} : " reply
        reply="${reply:-$default}"
    else
        while true; do
            read -rp "${C_BOLD}${prompt}${C_RESET} : " reply
            [[ -n "$reply" ]] && break
            warn "Une valeur est requise."
        done
    fi
    printf -v "$varname" '%s' "$reply"
}

ask_secret() {
    local prompt="$1" varname="$2" reply
    while true; do
        read -rsp "${C_BOLD}${prompt}${C_RESET} : " reply
        echo
        [[ -n "$reply" ]] && break
        warn "Une valeur est requise."
    done
    printf -v "$varname" '%s' "$reply"
}

ask_yesno() {
    # ask_yesno "Question ?" "y|n" → 0 si yes
    local prompt="$1" default="${2:-n}" reply hint
    if [[ "$default" == "y" ]]; then hint="[O/n]"; else hint="[o/N]"; fi
    read -rp "${C_BOLD}${prompt}${C_RESET} ${hint} : " reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[OoYy]$ ]]
}

###############################################################################
# 1. Pré-requis système
###############################################################################
check_prereqs() {
    step "Vérification des pré-requis"

    [[ $EUID -eq 0 ]] || fatal "Ce script doit être exécuté en root (sudo bash $0)."

    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        info "OS détecté : $PRETTY_NAME"
        case "$ID" in
            ubuntu|debian) success "Distribution compatible." ;;
            *) warn "Distribution non testée. Le script peut nécessiter des adaptations." ;;
        esac
    fi

    if ! ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
        fatal "Aucune connexion Internet détectée."
    fi
    success "Connexion Internet OK."

    info "Mémoire : $(free -h | awk '/^Mem:/ {print $2}') totale, $(free -h | awk '/^Mem:/ {print $7}') disponible"
    info "Disque  : $(df -h / | awk 'NR==2 {print $4}') libres sur /"
}

###############################################################################
# 2. Installation des paquets
###############################################################################
install_packages() {
    step "Installation des paquets système (Docker, Nginx, Certbot, utilitaires)"

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y --no-install-recommends \
        ca-certificates curl wget gnupg lsb-release \
        ufw nginx certbot python3-certbot-nginx \
        git jq openssl

    if ! command -v docker >/dev/null 2>&1; then
        info "Installation de Docker Engine officiel…"
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$ID/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
              https://download.docker.com/linux/$ID $(lsb_release -cs) stable" \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -y
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi

    systemctl enable --now docker
    success "Docker $(docker --version | awk '{print $3}' | tr -d ',') opérationnel."
    success "Docker Compose $(docker compose version --short)"

    # Pare-feu
    if ask_yesno "Configurer le pare-feu UFW (autoriser SSH, 80, 443) ?" y; then
        ufw allow OpenSSH 2>/dev/null || true
        ufw allow 80/tcp
        ufw allow 443/tcp
        echo "y" | ufw enable >/dev/null 2>&1 || true
        success "UFW activé : 22 (SSH), 80, 443 ouverts. Le port 8005 reste interne."
    fi
}

###############################################################################
# 3. Récupération du code source
###############################################################################
fetch_source() {
    step "Préparation du dossier d'installation $APP_DIR"

    if [[ -d "$APP_DIR/.git" ]]; then
        info "Dépôt déjà présent dans $APP_DIR — git pull."
        git -C "$APP_DIR" pull --ff-only || warn "git pull a échoué, on conserve l'existant."
    elif [[ -d "$APP_DIR" && -f "$APP_DIR/backend/server.py" ]]; then
        info "Code déjà présent dans $APP_DIR (sans git)."
    else
        local default_repo="https://github.com/votre-orga/vita-form.git"
        ask "URL du dépôt git VITA-FORM" "$default_repo" GIT_URL
        if [[ "$GIT_URL" =~ ^skip$ ]]; then
            warn "Saut du clonage. Veuillez avoir copié les sources dans $APP_DIR avant de relancer."
        else
            mkdir -p "$(dirname "$APP_DIR")"
            git clone "$GIT_URL" "$APP_DIR"
        fi
    fi

    [[ -f "$APP_DIR/backend/server.py" ]] || fatal "Sources VITA-FORM introuvables dans $APP_DIR."
    [[ -f "$COMPOSE_FILE" ]] || fatal "$COMPOSE_FILE introuvable."
    success "Sources prêtes dans $APP_DIR."
}

###############################################################################
# 4. Configuration interactive
###############################################################################
configure_env() {
    step "Configuration de l'environnement de production"

    # Si déjà configuré, demander confirmation
    if [[ -f "$ENV_FILE" ]]; then
        warn "$ENV_FILE existe déjà."
        if ask_yesno "Le réutiliser tel quel (aucune question posée) ?" y; then
            success "Configuration existante conservée."
            return 0
        fi
        cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%s)"
        info "Sauvegarde de l'ancienne configuration créée."
    fi

    echo
    info "Renseignez les paramètres de votre déploiement :"
    echo

    ask "Nom de domaine public" "vita-form.vitae-publica.tech" DOMAIN_NAME
    ask "Email pour Let's Encrypt / contact admin" "admin@vitae-publica.tech" LETSENCRYPT_EMAIL

    echo
    info "${C_BOLD}Compte SuperAdmin VITA-FORM${C_RESET} (créé au premier démarrage)"
    ask "Email admin" "admin@vitae-publica.tech" ADMIN_EMAIL
    ask_secret "Mot de passe admin (minimum 8 caractères)" ADMIN_PASSWORD
    while [[ ${#ADMIN_PASSWORD} -lt 8 ]]; do
        warn "Mot de passe trop court."
        ask_secret "Mot de passe admin (minimum 8 caractères)" ADMIN_PASSWORD
    done

    echo
    info "${C_BOLD}Clé Universal Emergent${C_RESET} (https://emergent.sh → Profile → Universal Key)"
    ask_secret "EMERGENT_LLM_KEY (sk-emergent-...)" EMERGENT_LLM_KEY

    echo
    info "${C_BOLD}PayPal${C_RESET} — compte personnel ou business standard"
    info "Aucune clé API requise : seul l'email du marchand suffit."
    ask "PAYPAL_BUSINESS_EMAIL (compte recevant les paiements)" "ely.mustapha@yahoo.ca" PAYPAL_BUSINESS_EMAIL
    ask "PAYPAL_MERCHANT_ID (depuis votre profil PayPal)" "XGYL8NPMKHDUY" PAYPAL_MERCHANT_ID
    if ask_yesno "Utiliser le bac à sable PayPal Sandbox (pour tests) ?" n; then
        PAYPAL_ENV="sandbox"
    else
        PAYPAL_ENV="live"
    fi
    ask "Prix paywall en EUR (sera converti pour les autres devises)" "14.90" PAYWALL_PRICE_EUR

    echo
    info "${C_BOLD}Resend${C_RESET} (https://resend.com → API Keys)"
    ask_secret "RESEND_API_KEY (re_...)" RESEND_API_KEY
    ask "Email expéditeur (vérifié dans Resend)" "noreply@vitae-publica.tech" SENDER_EMAIL

    echo
    info "${C_BOLD}Sécurité${C_RESET}"
    JWT_SECRET="$(openssl rand -hex 32)"
    success "JWT_SECRET généré aléatoirement (64 caractères hex)."

    PUBLIC_APP_URL="https://${DOMAIN_NAME}"

    cat > "$ENV_FILE" <<EOF
# VITA-FORM — Configuration de production
# Généré par deploy/install.sh le $(date -Iseconds)
# Ne JAMAIS committer ce fichier dans git.

DB_NAME=vitaform_db
CORS_ORIGINS=${PUBLIC_APP_URL}

EMERGENT_LLM_KEY=${EMERGENT_LLM_KEY}

JWT_SECRET=${JWT_SECRET}

ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

STRIPE_API_KEY=${STRIPE_API_KEY}
PAYWALL_PRICE_EUR=${PAYWALL_PRICE_EUR}

RESEND_API_KEY=${RESEND_API_KEY}
SENDER_EMAIL=${SENDER_EMAIL}

PUBLIC_APP_URL=${PUBLIC_APP_URL}
DOMAIN_NAME=${DOMAIN_NAME}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}
EOF
    chmod 600 "$ENV_FILE"
    success "Configuration écrite dans $ENV_FILE (permissions 600)."
}

###############################################################################
# 5. Validation DNS
###############################################################################
check_dns() {
    step "Vérification DNS du domaine"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    local public_ip resolved_ip
    public_ip="$(curl -s4 https://api.ipify.org || true)"
    resolved_ip="$(dig +short "$DOMAIN_NAME" A | tail -n 1 || true)"

    info "IP publique du serveur : ${public_ip:-inconnue}"
    info "IP résolue pour ${DOMAIN_NAME} : ${resolved_ip:-aucune}"

    if [[ -n "$public_ip" && "$public_ip" == "$resolved_ip" ]]; then
        success "DNS OK — ${DOMAIN_NAME} pointe sur ce serveur."
    else
        warn "Le DNS ne pointe pas (encore) sur ce serveur."
        warn "Créez un enregistrement A : ${DOMAIN_NAME} → ${public_ip:-IP_DU_SERVEUR}"
        if ! ask_yesno "Continuer malgré tout (le SSL Certbot peut échouer) ?" n; then
            fatal "Configuration DNS requise. Relancer après propagation."
        fi
    fi
}

###############################################################################
# 6. Build & lancement Docker
###############################################################################
build_and_start() {
    step "Build des images et lancement de la stack"

    cd "$DEPLOY_DIR"
    docker compose --env-file "$ENV_FILE" pull --ignore-pull-failures || true
    docker compose --env-file "$ENV_FILE" build --pull
    docker compose --env-file "$ENV_FILE" up -d

    info "Attente de la disponibilité du backend (60s max)…"
    local i
    for i in $(seq 1 30); do
        if curl -sf http://127.0.0.1:8005/api/ >/dev/null 2>&1; then
            success "Backend opérationnel sur le port 8005."
            return 0
        fi
        sleep 2
    done
    docker compose --env-file "$ENV_FILE" logs --tail 50
    fatal "Le backend ne répond pas après 60s. Voir logs ci-dessus."
}

###############################################################################
# 7. Reverse-proxy Nginx hôte
###############################################################################
setup_nginx() {
    step "Configuration du reverse-proxy Nginx hôte"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    local conf="/etc/nginx/sites-available/vita-form"
    cat > "$conf" <<EOF
# Reverse-proxy hôte VITA-FORM (HTTP — Certbot ajoutera le bloc SSL)
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    client_max_body_size 25m;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
    }
}
EOF

    ln -sf "$conf" /etc/nginx/sites-enabled/vita-form
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl reload nginx
    success "Nginx hôte configuré pour ${DOMAIN_NAME} → 127.0.0.1:8005."
}

###############################################################################
# 8. Certificat SSL Let's Encrypt
###############################################################################
setup_ssl() {
    step "Émission du certificat SSL Let's Encrypt"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    if ! ask_yesno "Demander un certificat SSL maintenant pour ${DOMAIN_NAME} ?" y; then
        warn "SSL ignoré. Vous pourrez le faire plus tard avec : certbot --nginx -d ${DOMAIN_NAME}"
        return 0
    fi

    if certbot certificates 2>/dev/null | grep -q "Domains: ${DOMAIN_NAME}"; then
        info "Certificat existant détecté pour ${DOMAIN_NAME}, renouvellement uniquement."
        certbot renew --nginx --non-interactive --quiet || warn "Renouvellement échoué, certificat non expiré peut-être."
    else
        certbot --nginx \
            -d "${DOMAIN_NAME}" \
            -m "${LETSENCRYPT_EMAIL}" \
            --agree-tos --redirect --non-interactive
    fi

    systemctl enable --now certbot.timer 2>/dev/null || true
    success "SSL configuré. Renouvellement automatique via certbot.timer."
}

###############################################################################
# 9. Tests post-déploiement
###############################################################################
post_checks() {
    step "Tests fonctionnels"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    info "Test 1 — Endpoint racine API"
    if curl -sf "${PUBLIC_APP_URL}/api/" | grep -q "VITA-FORM"; then
        success "API publique accessible."
    else
        warn "API publique inaccessible — vérifier DNS / SSL."
    fi

    info "Test 2 — Login admin"
    local token
    token="$(curl -s -X POST "${PUBLIC_APP_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
        | jq -r '.access_token // empty')"
    if [[ -n "$token" ]]; then
        success "Compte admin opérationnel."
    else
        warn "Login admin échoué — vérifier les logs backend."
    fi

    info "Test 3 — Institutions seedées"
    local count
    count="$(curl -s "${PUBLIC_APP_URL}/api/institutions" | jq 'length // 0' 2>/dev/null || echo 0)"
    if [[ "$count" -ge 22 ]]; then
        success "$count institutions seedées."
    else
        warn "Seulement $count institutions (attendu ≥ 22)."
    fi

    info "Test 4 — Corpus jurisprudentiel"
    count="$(curl -s -H "Authorization: Bearer ${token}" "${PUBLIC_APP_URL}/api/jurisprudences?limit=100" | jq 'length // 0' 2>/dev/null || echo 0)"
    if [[ "$count" -ge 20 ]]; then
        success "$count jurisprudences indexées."
    else
        warn "Corpus jurisprudentiel partiel ($count entrées)."
    fi
}

###############################################################################
# 10. Résumé final
###############################################################################
final_summary() {
    step "Installation terminée"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    cat <<EOF

${C_GOLD}${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_GOLD}${C_BOLD}  VITA-FORM est déployé.${C_RESET}

  ${C_BOLD}URL publique${C_RESET}      ${PUBLIC_APP_URL}
  ${C_BOLD}Admin${C_RESET}             ${ADMIN_EMAIL}
  ${C_BOLD}Mot de passe${C_RESET}      (saisi durant l'installation)
  ${C_BOLD}Webhook Stripe${C_RESET}    ${PUBLIC_APP_URL}/api/webhook/stripe
  ${C_BOLD}Logs backend${C_RESET}      docker compose -f $COMPOSE_FILE logs -f backend
  ${C_BOLD}Configuration${C_RESET}     $ENV_FILE  (chmod 600)
  ${C_BOLD}Renouv. SSL${C_RESET}       systemctl status certbot.timer

  ${C_BOLD}Suite production :${C_RESET}
   1. Vérifier le domaine d'envoi dans Resend (DNS SPF/DKIM/DMARC)
   2. Configurer un Webhook dans le dashboard Stripe :
        URL    : ${PUBLIC_APP_URL}/api/webhook/stripe
        Events : checkout.session.completed,
                 checkout.session.async_payment_succeeded,
                 checkout.session.async_payment_failed
   3. Importer un corpus complémentaire de jurisprudences via /admin
   4. Sauvegarder MongoDB :
        docker exec vita-mongo mongodump -o /backup/\$(date +%F)
${C_GOLD}${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

EOF
}

###############################################################################
# Exécution
###############################################################################
main() {
    banner
    info "Logs : $LOG_FILE"
    if ! ask_yesno "Démarrer l'installation interactive ?" y; then
        info "Annulé par l'utilisateur."
        exit 0
    fi
    check_prereqs
    install_packages
    fetch_source
    configure_env
    check_dns
    build_and_start
    setup_nginx
    setup_ssl
    post_checks
    final_summary
}

main "$@"
