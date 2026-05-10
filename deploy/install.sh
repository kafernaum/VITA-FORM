#!/usr/bin/env bash
###############################################################################
#                                                                             #
#   VITA-FORM — Installateur interactif de production                         #
#   Plateforme Pédagogique Vitaliste — Pr. Ahmed ELY Mustapha                 #
#                                                                             #
#   Cible      : Ubuntu 22.04+ ou Debian 12+ (root requis)                    #
#   Dossier    : /opt/vita-form                                               #
#   Domaine    : vita-form.vitae-publica.tech (par défaut, modifiable)        #
#   Port local : 127.0.0.1:8005 (mappé en 80/443 par Nginx hôte)              #
#                                                                             #
#   Usage  : sudo bash deploy/install.sh                [premier déploiement] #
#   Usage  : sudo bash deploy/install.sh --update       [mise à jour]         #
#   Usage  : sudo bash deploy/install.sh --reconfigure  [refaire la conf]     #
#   Usage  : sudo bash deploy/install.sh --skip-ssl     [sans certbot]        #
#                                                                             #
###############################################################################

set -Eeuo pipefail
IFS=$'\n\t'

###############################################################################
# Constantes
###############################################################################
APP_DIR="/opt/vita-form"
DEPLOY_DIR="$APP_DIR/deploy"
ENV_FILE="$DEPLOY_DIR/.env.production"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
LOG_DIR="/var/log/vita-form"
LOG_FILE="$LOG_DIR/install-$(date +%Y%m%d-%H%M%S).log"
DEFAULT_DOMAIN="vita-form.vitae-publica.tech"
LOCAL_PORT=8005
SCRIPT_VERSION="2.0"

# Modes
MODE="install"      # install | update | reconfigure
SKIP_SSL=0
SKIP_DNS=0
NON_INTERACTIVE=0

# Compteur d'étapes (renseigné dynamiquement par main)
STEP=0
TOTAL_STEPS=11

###############################################################################
# Couleurs & helpers d'affichage
###############################################################################
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

   ${C_GOLD}╔═══════════════════════════════════════════════════════════════╗${C_RESET}
   ${C_GOLD}║                                                               ║${C_RESET}
   ${C_GOLD}║       V I T A - F O R M   ·   D O C T R I N A   V I T A L I S ║${C_RESET}
   ${C_GOLD}║                                                               ║${C_RESET}
   ${C_GOLD}║       Installateur interactif de production VPS              ║${C_RESET}
   ${C_GOLD}║       Pr. Ahmed ELY Mustapha    —    v${SCRIPT_VERSION}                      ║${C_RESET}
   ${C_GOLD}║                                                               ║${C_RESET}
   ${C_GOLD}╚═══════════════════════════════════════════════════════════════╝${C_RESET}

EOF
}

step()    { STEP=$((STEP + 1)); echo; echo "${C_GOLD}${C_BOLD}━━━ Étape ${STEP}/${TOTAL_STEPS} : $* ━━━${C_RESET}"; }
info()    { echo "${C_CYAN}ℹ${C_RESET}  $*"; }
success() { echo "${C_GREEN}✓${C_RESET}  $*"; }
warn()    { echo "${C_YELLOW}⚠${C_RESET}  $*"; }
fail()    { echo "${C_RED}✗${C_RESET}  $*" >&2; }
fatal()   { fail "$*"; echo "${C_DIM}Logs : $LOG_FILE${C_RESET}" >&2; exit 1; }

# Trap erreurs avec numéro de ligne
on_error() {
    local exit_code=$?
    local line=$1
    fail "Erreur à la ligne $line (code $exit_code)."
    fail "Consultez $LOG_FILE pour le détail."
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

###############################################################################
# Helpers de saisie
###############################################################################
ask() {
    local prompt="$1" default="${2:-}" varname="$3" reply
    if [[ $NON_INTERACTIVE -eq 1 ]]; then
        printf -v "$varname" '%s' "$default"
        return 0
    fi
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
    local prompt="$1" varname="$2" min="${3:-8}" reply
    while true; do
        read -rsp "${C_BOLD}${prompt}${C_RESET} : " reply
        echo
        if [[ ${#reply} -lt $min ]]; then
            warn "Au moins $min caractères requis."
            continue
        fi
        break
    done
    printf -v "$varname" '%s' "$reply"
}

ask_yesno() {
    local prompt="$1" default="${2:-n}" reply hint
    if [[ $NON_INTERACTIVE -eq 1 ]]; then
        [[ "$default" == "y" ]] && return 0 || return 1
    fi
    if [[ "$default" == "y" ]]; then hint="[O/n]"; else hint="[o/N]"; fi
    read -rp "${C_BOLD}${prompt}${C_RESET} $hint : " reply
    reply="${reply:-$default}"
    [[ "$reply" =~ ^[OoYy]$ ]]
}

validate_email()  { [[ "$1" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; }
validate_domain() { [[ "$1" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; }

ask_email() {
    local prompt="$1" default="$2" varname="$3"
    while true; do
        ask "$prompt" "$default" "$varname"
        local val="${!varname}"
        validate_email "$val" && break
        warn "Format email invalide : $val"
    done
}

ask_domain() {
    local prompt="$1" default="$2" varname="$3"
    while true; do
        ask "$prompt" "$default" "$varname"
        local val="${!varname}"
        validate_domain "$val" && break
        warn "Format domaine invalide : $val"
    done
}

###############################################################################
# Parse arguments
###############################################################################
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --update)         MODE="update" ;;
            --reconfigure)    MODE="reconfigure" ;;
            --skip-ssl)       SKIP_SSL=1 ;;
            --skip-dns)       SKIP_DNS=1 ;;
            --non-interactive) NON_INTERACTIVE=1 ;;
            -h|--help)
                cat <<EOF
Usage : sudo bash $(basename "$0") [OPTIONS]
  --update         Met à jour une installation existante (git pull + rebuild).
  --reconfigure    Refait la saisie de configuration (.env.production).
  --skip-ssl       N'émet pas de certificat Let's Encrypt.
  --skip-dns       Saute la vérification DNS.
  --non-interactive Utilise toutes les valeurs par défaut (réservé CI).
  -h, --help       Affiche cette aide.
EOF
                exit 0
                ;;
            *) fatal "Argument inconnu : $1" ;;
        esac
        shift
    done
}

###############################################################################
# Préparation logs
###############################################################################
init_logging() {
    mkdir -p "$LOG_DIR"
    chmod 750 "$LOG_DIR"
    # Tee tout vers le fichier de log
    exec > >(tee -a "$LOG_FILE") 2>&1
}

###############################################################################
# 1. Pré-requis système
###############################################################################
check_prereqs() {
    step "Pré-requis système"

    [[ $EUID -eq 0 ]] || fatal "Lancer en root : sudo bash $0"

    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        info "OS détecté : $PRETTY_NAME"
        case "${ID:-}" in
            ubuntu|debian) success "Distribution compatible." ;;
            *) warn "Distribution non testée — adaptations possibles." ;;
        esac
    fi

    info "Architecture : $(uname -m)"

    # Connectivité Internet
    if ! curl -sSf --max-time 5 https://api.github.com >/dev/null 2>&1; then
        fatal "Pas d'accès Internet (https). Vérifier réseau / proxy."
    fi
    success "Connexion Internet OK."

    # Ressources
    local ram_mb disk_gb
    ram_mb=$(free -m | awk '/^Mem:/ {print $2}')
    disk_gb=$(df -BG / | awk 'NR==2 {gsub(/G/,"",$4); print $4}')
    info "RAM totale  : ${ram_mb} Mo"
    info "Disque libre / : ${disk_gb} Go"

    [[ ${ram_mb:-0} -lt 1500 ]] && warn "RAM < 1.5 Go — Mongo + builds peuvent saturer (2 Go recommandés)."
    [[ ${disk_gb:-0} -lt 10 ]]  && warn "Espace disque libre < 10 Go — prévoir une extension."

    # Ports critiques libres
    for p in 80 443 "$LOCAL_PORT"; do
        if ss -ltn | awk '{print $4}' | grep -E ":${p}$" >/dev/null 2>&1; then
            warn "Le port $p semble déjà occupé. La suite peut échouer."
        fi
    done
}

###############################################################################
# 2. Paquets système & Docker
###############################################################################
install_packages() {
    step "Paquets système & Docker"

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y -qq
    apt-get install -y -qq --no-install-recommends \
        ca-certificates curl wget gnupg lsb-release dnsutils iproute2 \
        ufw nginx certbot python3-certbot-nginx \
        git jq openssl

    if ! command -v docker >/dev/null 2>&1; then
        info "Installation de Docker Engine officiel…"
        install -m 0755 -d /etc/apt/keyrings
        # shellcheck disable=SC1091
        . /etc/os-release
        curl -fsSL "https://download.docker.com/linux/${ID}/gpg" \
            | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} $(lsb_release -cs) stable" \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -y -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
                                docker-buildx-plugin docker-compose-plugin
    fi

    systemctl enable --now docker

    if ! docker info >/dev/null 2>&1; then
        fatal "Docker ne fonctionne pas. Voir : systemctl status docker"
    fi

    success "Docker $(docker --version | awk '{print $3}' | tr -d ',') opérationnel."
    success "Docker Compose $(docker compose version --short)."

    # Pare-feu
    if ask_yesno "Configurer UFW (autoriser SSH, 80, 443) ?" y; then
        ufw allow OpenSSH 2>/dev/null || true
        ufw allow 80/tcp  >/dev/null
        ufw allow 443/tcp >/dev/null
        echo "y" | ufw enable >/dev/null 2>&1 || true
        success "UFW activé : 22 / 80 / 443. Le port $LOCAL_PORT est lié à 127.0.0.1 uniquement."
    fi
}

###############################################################################
# 3. Récupération / mise à jour des sources
###############################################################################
fetch_source() {
    step "Sources VITA-FORM dans $APP_DIR"

    if [[ -d "$APP_DIR/.git" ]]; then
        info "Dépôt git détecté — git pull (mode $MODE)."
        # Sauvegarde de l'env avant pull
        [[ -f "$ENV_FILE" ]] && cp "$ENV_FILE" "${ENV_FILE}.pre-pull.$(date +%s).bak"
        git -C "$APP_DIR" fetch --all --prune
        git -C "$APP_DIR" pull --ff-only \
            || warn "git pull non fast-forward — résolution manuelle requise."
    elif [[ -d "$APP_DIR" && -f "$APP_DIR/backend/server.py" ]]; then
        info "Sources déjà présentes (sans .git)."
    else
        local default_repo="https://github.com/votre-orga/vita-form.git"
        ask "URL du dépôt git VITA-FORM (ou 'skip' si déjà copié)" \
            "$default_repo" GIT_URL
        if [[ "$GIT_URL" == "skip" ]]; then
            warn "Saut du clonage — vérifiez que les sources sont bien dans $APP_DIR."
        else
            mkdir -p "$(dirname "$APP_DIR")"
            git clone --depth 1 "$GIT_URL" "$APP_DIR"
        fi
    fi

    [[ -f "$APP_DIR/backend/server.py" ]]   || fatal "Backend introuvable dans $APP_DIR/backend."
    [[ -f "$APP_DIR/frontend/package.json" ]] || fatal "Frontend introuvable dans $APP_DIR/frontend."
    [[ -f "$COMPOSE_FILE" ]]                || fatal "$COMPOSE_FILE introuvable."

    success "Sources prêtes."
}

###############################################################################
# 4. Configuration interactive (.env.production)
###############################################################################
configure_env() {
    step "Configuration de l'environnement"

    if [[ -f "$ENV_FILE" && "$MODE" == "update" ]]; then
        info "Mode update : conservation de $ENV_FILE existant."
        success "Config existante conservée."
        return 0
    fi

    if [[ -f "$ENV_FILE" && "$MODE" != "reconfigure" ]]; then
        warn "$ENV_FILE existe."
        if ask_yesno "Le réutiliser tel quel ?" y; then
            success "Configuration existante conservée."
            return 0
        fi
        cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%s)"
        info "Sauvegarde créée."
    fi

    echo
    info "Renseignez les paramètres de votre déploiement."
    echo

    ask_domain "Nom de domaine public" "$DEFAULT_DOMAIN" DOMAIN_NAME
    ask_email  "Email Let's Encrypt / contact" "admin@vitae-publica.tech" LETSENCRYPT_EMAIL

    echo
    info "${C_BOLD}Compte SuperAdmin VITA-FORM${C_RESET} (créé automatiquement)"
    ask_email "Email admin" "admin@vitae-publica.tech" ADMIN_EMAIL
    ask_secret "Mot de passe admin (≥ 8 caractères)" ADMIN_PASSWORD 8

    echo
    info "${C_BOLD}Universal Key Emergent${C_RESET}"
    info "https://emergent.sh → Profile → Universal Key (sk-emergent-…)"
    info "Sert pour Claude Sonnet 4.5 + object storage."
    ask_secret "EMERGENT_LLM_KEY" EMERGENT_LLM_KEY 10

    echo
    info "${C_BOLD}PayPal${C_RESET} — compte personnel ou business"
    ask_email  "PAYPAL_BUSINESS_EMAIL (compte recevant les paiements)" \
               "ely.mustapha@yahoo.ca" PAYPAL_BUSINESS_EMAIL
    ask "PAYPAL_MERCHANT_ID (Profil PayPal → Identité du compte)" \
        "XGYL8NPMKHDUY" PAYPAL_MERCHANT_ID
    if ask_yesno "Utiliser le bac à sable PayPal Sandbox (tests) ?" n; then
        PAYPAL_ENV="sandbox"
    else
        PAYPAL_ENV="live"
    fi
    ask "Prix paywall en EUR" "14.90" PAYWALL_PRICE_EUR

    echo
    info "${C_BOLD}Resend${C_RESET} (https://resend.com → API Keys)"
    info "Domaine d'envoi à vérifier dans Resend (SPF/DKIM/DMARC)."
    ask_secret "RESEND_API_KEY (re_…)" RESEND_API_KEY 10
    ask_email "Email expéditeur (vérifié dans Resend)" \
              "noreply@${DOMAIN_NAME}" SENDER_EMAIL

    echo
    info "${C_BOLD}Sécurité${C_RESET}"
    JWT_SECRET="$(openssl rand -hex 32)"
    success "JWT_SECRET généré (64 hex)."

    PUBLIC_APP_URL="https://${DOMAIN_NAME}"

    # Écriture atomique
    local tmp="${ENV_FILE}.tmp.$$"
    cat > "$tmp" <<EOF
# VITA-FORM — Configuration de production
# Généré par deploy/install.sh v${SCRIPT_VERSION} le $(date -Iseconds)
# NE JAMAIS committer ce fichier dans git.

DB_NAME=vitaform_db
CORS_ORIGINS=${PUBLIC_APP_URL}

EMERGENT_LLM_KEY=${EMERGENT_LLM_KEY}

JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256

ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

PAYPAL_ENV=${PAYPAL_ENV}
PAYPAL_BUSINESS_EMAIL=${PAYPAL_BUSINESS_EMAIL}
PAYPAL_MERCHANT_ID=${PAYPAL_MERCHANT_ID}
PAYWALL_PRICE_EUR=${PAYWALL_PRICE_EUR}

RESEND_API_KEY=${RESEND_API_KEY}
SENDER_EMAIL=${SENDER_EMAIL}

APP_NAME=vitaform
PUBLIC_APP_URL=${PUBLIC_APP_URL}
DOMAIN_NAME=${DOMAIN_NAME}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}
EOF
    chmod 600 "$tmp"
    mv -f "$tmp" "$ENV_FILE"
    success "Configuration écrite dans $ENV_FILE (chmod 600)."
}

###############################################################################
# 5. Vérification DNS
###############################################################################
check_dns() {
    [[ $SKIP_DNS -eq 1 ]] && { info "DNS check skipped (--skip-dns)."; return 0; }
    step "Vérification DNS"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    local public_ip resolved_ip
    public_ip="$(curl -s4 --max-time 5 https://api.ipify.org || true)"
    resolved_ip="$(dig +short "$DOMAIN_NAME" A | tail -n 1 || true)"

    info "IP publique du serveur : ${public_ip:-inconnue}"
    info "IP DNS de ${DOMAIN_NAME}     : ${resolved_ip:-aucune}"

    if [[ -n "$public_ip" && "$public_ip" == "$resolved_ip" ]]; then
        success "DNS OK — ${DOMAIN_NAME} pointe sur ce serveur."
        return 0
    fi

    warn "Le DNS ne pointe pas (encore) sur ce serveur."
    warn "Créez un enregistrement A : ${DOMAIN_NAME} → ${public_ip:-IP_DU_SERVEUR}"
    warn "Délai de propagation DNS : 5 min à 24 h."
    if ! ask_yesno "Continuer malgré tout (le SSL Certbot peut échouer) ?" n; then
        fatal "Configuration DNS requise. Relancer après propagation."
    fi
}

###############################################################################
# 6. Build & lancement Docker
###############################################################################
build_and_start() {
    step "Build images & lancement de la stack"

    cd "$DEPLOY_DIR"

    info "Pull des images de base…"
    docker compose --env-file "$ENV_FILE" pull --ignore-pull-failures || true

    info "Build des images applicatives (peut prendre 3-5 min)…"
    docker compose --env-file "$ENV_FILE" build --pull

    info "Lancement de la stack en arrière-plan…"
    docker compose --env-file "$ENV_FILE" up -d --remove-orphans

    info "Attente du backend (90 s max)…"
    local i=0
    for i in $(seq 1 45); do
        if curl -sf "http://127.0.0.1:${LOCAL_PORT}/api/" >/dev/null 2>&1; then
            success "Stack opérationnelle sur 127.0.0.1:${LOCAL_PORT} (après ${i} essais)."
            return 0
        fi
        sleep 2
    done

    fail "Le backend ne répond pas après 90 s. Logs récents :"
    docker compose --env-file "$ENV_FILE" logs --tail 80
    fatal "Démarrage incomplet. Inspecter avec : docker compose -f $COMPOSE_FILE logs"
}

###############################################################################
# 7. Reverse-proxy Nginx hôte
###############################################################################
setup_nginx() {
    step "Reverse-proxy Nginx hôte"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    local conf="/etc/nginx/sites-available/vita-form"
    cat > "$conf" <<EOF
# Reverse-proxy hôte VITA-FORM (généré par install.sh)
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME};

    client_max_body_size 25m;

    location / {
        proxy_pass http://127.0.0.1:${LOCAL_PORT};
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
    success "Nginx hôte : ${DOMAIN_NAME} → 127.0.0.1:${LOCAL_PORT}."
}

###############################################################################
# 8. SSL Let's Encrypt
###############################################################################
setup_ssl() {
    [[ $SKIP_SSL -eq 1 ]] && { info "SSL ignoré (--skip-ssl)."; return 0; }
    step "Certificat SSL Let's Encrypt"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    if ! ask_yesno "Demander un certificat SSL pour ${DOMAIN_NAME} ?" y; then
        warn "SSL ignoré. Plus tard : certbot --nginx -d ${DOMAIN_NAME}"
        return 0
    fi

    if certbot certificates 2>/dev/null | grep -q "Domains: ${DOMAIN_NAME}"; then
        info "Certificat existant — tentative de renouvellement."
        certbot renew --nginx --non-interactive --quiet \
            || warn "Renouvellement échoué (probablement non expiré)."
    else
        certbot --nginx \
            -d "${DOMAIN_NAME}" \
            -m "${LETSENCRYPT_EMAIL}" \
            --agree-tos --redirect --non-interactive
    fi

    systemctl enable --now certbot.timer 2>/dev/null || true
    success "SSL configuré. Renouvellement auto via certbot.timer."
}

###############################################################################
# 9. Tests post-déploiement
###############################################################################
post_checks() {
    step "Tests fonctionnels"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    local target="${PUBLIC_APP_URL}"
    [[ $SKIP_SSL -eq 1 ]] && target="http://${DOMAIN_NAME}"

    # 1. API root
    info "1/5  Endpoint racine API"
    if curl -sf --max-time 10 "${target}/api/" 2>/dev/null | grep -q "VITA-FORM"; then
        success "API accessible sur ${target}/api/"
    else
        warn "API publique inaccessible — vérifier DNS / SSL / firewall."
        info "Test direct local : curl http://127.0.0.1:${LOCAL_PORT}/api/"
    fi

    # 2. Login admin
    info "2/5  Login admin"
    local login_payload token
    login_payload=$(jq -nc --arg e "$ADMIN_EMAIL" --arg p "$ADMIN_PASSWORD" \
                     '{email:$e, password:$p}')
    token="$(curl -s --max-time 10 -X POST "${target}/api/auth/login" \
        -H "Content-Type: application/json" -d "$login_payload" \
        2>/dev/null | jq -r '.access_token // empty')"
    if [[ -n "$token" ]]; then
        success "Compte admin opérationnel."
    else
        warn "Login admin échoué — vérifier les logs backend."
    fi

    # 3. Institutions seedées
    info "3/5  Institutions seedées"
    local count
    count="$(curl -s --max-time 10 "${target}/api/institutions" 2>/dev/null \
        | jq 'length // 0' 2>/dev/null || echo 0)"
    if [[ "${count:-0}" -ge 22 ]]; then
        success "${count} institutions seedées."
    else
        warn "Seulement ${count} institutions (attendu ≥ 22)."
    fi

    # 4. Corpus jurisprudentiel
    info "4/5  Corpus jurisprudentiel (RAG)"
    if [[ -n "$token" ]]; then
        count="$(curl -s --max-time 10 -H "Authorization: Bearer $token" \
            "${target}/api/jurisprudences?limit=100" 2>/dev/null \
            | jq 'length // 0' 2>/dev/null || echo 0)"
        if [[ "${count:-0}" -ge 20 ]]; then
            success "${count} jurisprudences indexées."
        else
            warn "Corpus partiel : ${count} entrées."
        fi
    fi

    # 5. PayPal
    info "5/5  Configuration PayPal"
    local merchant
    merchant="$(curl -s --max-time 10 "${target}/api/payments/options" 2>/dev/null \
        | jq -r '.merchant_email // empty')"
    if [[ "$merchant" == "$PAYPAL_BUSINESS_EMAIL" ]]; then
        success "PayPal configuré : ${merchant}"
    else
        warn "PayPal non configuré (merchant=${merchant:-vide})."
    fi
}

###############################################################################
# 10. Webhook PayPal IPN
###############################################################################
check_ipn() {
    step "Webhook PayPal IPN"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    cat <<EOF

  ${C_BOLD}Configuration manuelle requise dans le compte PayPal :${C_RESET}
  -------------------------------------------------------------
  1. Connectez-vous : https://www.paypal.com/businessmanage/account/notifications
  2. ${C_GOLD}« Notifications de paiement instantané (IPN) »${C_RESET} → Mettre à jour
  3. URL de notification :
       ${C_BOLD}${PUBLIC_APP_URL}/api/webhook/paypal${C_RESET}
     Recevoir des messages IPN : ${C_BOLD}Activé${C_RESET}
  4. Enregistrer.

  Sans IPN actif, les paiements PayPal ne déverrouillent PAS automatiquement
  les livrables (vous pourrez toujours les valider manuellement via /admin).

EOF
    if ask_yesno "IPN configuré ?" n; then
        success "Configuration IPN confirmée."
    else
        warn "À faire avant la mise en production effective."
    fi
}

###############################################################################
# 11. Récapitulatif
###############################################################################
final_summary() {
    step "Installation terminée"
    # shellcheck disable=SC1090
    . "$ENV_FILE"

    cat <<EOF

${C_GOLD}${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_GOLD}${C_BOLD}  VITA-FORM est déployé.${C_RESET}

  ${C_BOLD}URL publique${C_RESET}    ${PUBLIC_APP_URL}
  ${C_BOLD}Accueil${C_RESET}         ${PUBLIC_APP_URL}/
  ${C_BOLD}Auteur${C_RESET}          ${PUBLIC_APP_URL}/auteur
  ${C_BOLD}Théorie${C_RESET}         ${PUBLIC_APP_URL}/theorie
  ${C_BOLD}Admin${C_RESET}           ${PUBLIC_APP_URL}/admin
  ${C_BOLD}IPN webhook${C_RESET}     ${PUBLIC_APP_URL}/api/webhook/paypal

  ${C_BOLD}Identifiant admin${C_RESET}   ${ADMIN_EMAIL}
  ${C_BOLD}PayPal marchand${C_RESET}     ${PAYPAL_BUSINESS_EMAIL} (${PAYPAL_ENV})

  ${C_BOLD}Configuration${C_RESET}   $ENV_FILE  (chmod 600)
  ${C_BOLD}Logs install${C_RESET}    $LOG_FILE
  ${C_BOLD}Logs runtime${C_RESET}    docker compose -f $COMPOSE_FILE logs -f

  ${C_BOLD}Helper${C_RESET}          $DEPLOY_DIR/manage.sh  (logs|restart|backup|update|status)

  ${C_BOLD}À faire après installation :${C_RESET}
   1. Configurer l'IPN PayPal (étape 10).
   2. Vérifier le domaine d'envoi dans Resend (DNS SPF/DKIM/DMARC).
   3. ${PUBLIC_APP_URL}/admin → onglet « Comptes bancaires » : saisir vos
      vrais RIB (option de paiement par virement).
   4. Importer un corpus complémentaire de jurisprudences si besoin.
   5. Mettre en place une sauvegarde quotidienne de MongoDB :
        $DEPLOY_DIR/manage.sh backup        # à programmer en cron

  ${C_BOLD}Mise à jour ultérieure :${C_RESET}
        sudo bash $DEPLOY_DIR/install.sh --update

${C_GOLD}${C_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}

EOF
}

###############################################################################
# Main
###############################################################################
main() {
    parse_args "$@"
    init_logging

    banner
    info "Mode : ${C_BOLD}${MODE}${C_RESET}    Logs : $LOG_FILE"

    if [[ $NON_INTERACTIVE -eq 0 ]]; then
        if ! ask_yesno "Démarrer l'installation ?" y; then
            info "Annulé par l'utilisateur."
            exit 0
        fi
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
    check_ipn
    final_summary
}

main "$@"
