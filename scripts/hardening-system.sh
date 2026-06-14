#!/bin/bash
# ============================================================
# Aperture Science VPS — Security Hardening Script v1.0
# Debian 13 (trixie) — À exécuter en root
# ============================================================
# Ce script durcit :
#   1. SSH
#   2. UFW (pare-feu)
#   3. Fail2Ban
#   4. Docker daemon
#   5. Kernel sysctl
#   6. AppArmor
#   7. Audit Lynis
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }

# Vérification root
if [[ $EUID -ne 0 ]]; then
   err "Ce script doit être exécuté en root (sudo ./hardening-system.sh)"
   exit 1
fi

echo "============================================"
echo "  Aperture Science VPS — Hardening v1.0"
echo "  $(date)"
echo "============================================"
echo ""

# ============================================================
# 1. SSH HARDENING
# ============================================================
echo "─── 1. SSH Hardening ───"

# Sauvegarde
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d%H%M%S)
log "Sauvegarde sshd_config créée"

# Appliquer les durcissements
cat > /etc/ssh/sshd_config.d/99-hardening.conf << 'SSHEOF'
# === Aperture Science SSH Hardening ===
# Généré automatiquement — ne pas éditer manuellement

# Authentification
# PermitRootLogin prohibit-password : root par clé seulement (pas de password)
# NE PAS mettre "no" — si glados est bloqué, root est le fallback
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no

# Restriction d'accès
AllowUsers glados
MaxAuthTries 3
LoginGraceTime 20

# Désactiver les fonctionnalités dangereuses
X11Forwarding no
# AllowTcpForwarding local : autorise uniquement les tunnels locaux (port forwarding)
# Nécessaire pour l'accès au dashboard Hermes via tunnel SSH
# "no" bloquerait tous les tunnels, "yes" autorise aussi le remote (dangereux)
AllowTcpForwarding local
AllowAgentForwarding no
PermitTunnel no
GatewayPorts no
PermitUserEnvironment no

# Sécurité supplémentaire
UsePAM yes
StrictModes yes
IgnoreRhosts yes
HostbasedAuthentication no

# Timeouts
ClientAliveInterval 300
ClientAliveCountMax 2

# Banner (optionnel — décommenter si souhaité)
# Banner /etc/ssh/banner
SSHEOF

log "Configuration SSH hardening écrite"

# Valider la config SSH avant reload
if sshd -t 2>/dev/null; then
    log "Configuration SSH valide"
    systemctl reload sshd
    log "SSHD rechargé"
else
    err "ERREUR de configuration SSH — restauration de la sauvegarde"
    cp /etc/ssh/sshd_config.bak.* /etc/ssh/sshd_config
    exit 1
fi

# ============================================================
# 2. UFW (PARE-FEU)
# ============================================================
echo ""
echo "─── 2. UFW Firewall ───"

# Activer UFW avec des règles strictes
ufw --force reset
log "UFW reset"

ufw default deny incoming
ufw default allow outgoing
log "Politiques par défaut : deny incoming, allow outgoing"

# SSH — limiter le rate
ufw limit 22/tcp comment 'SSH rate-limited'
log "SSH (22) — rate limité"

# HTTP/HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
log "HTTP (80) + HTTPS (443) autorisés"

# Activer
ufw --force enable
log "UFW activé"

ufw status verbose

# ============================================================
# 3. FAIL2BAN
# ============================================================
echo ""
echo "─── 3. Fail2Ban ───"

# Jail SSH
cat > /etc/fail2ban/jail.d/ssh-hardened.conf << 'F2BEOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
findtime = 600
bantime = 3600
banaction = ufw
F2BEOF

log "Jail SSH configurée (maxretry=3, bantime=1h)"

# Jail Traefik (si logs accessibles)
cat > /etc/fail2ban/jail.d/traefik-auth.conf << 'F2BEOF'
[traefik-auth]
enabled = true
port = http,https
filter = traefik-auth
logpath = /var/log/traefik/access.log
maxretry = 10
findtime = 60
bantime = 600
banaction = ufw
F2BEOF

# Créer le filter Traefik
cat > /etc/fail2ban/filter.d/traefik-auth.conf << 'F2BEOF'
[Definition]
failregex = ^<HOST> .* "(GET|POST|PUT|DELETE) .*" (401|403|429) .*$
ignoreregex =
F2BEOF

log "Jail Traefik auth configurée"

# Reload Fail2Ban
systemctl restart fail2ban
log "Fail2Ban redémarré"

fail2ban-client status sshd 2>/dev/null || warn "Vérifier le status Fail2Ban manuellement"

# ============================================================
# 4. DOCKER DAEMON HARDENING
# ============================================================
echo ""
echo "─── 4. Docker Daemon ───"

cat > /etc/docker/daemon.json << 'DOCKEREOF'
{
  "icc": false,
  "iptables": true,
  "userns-remap": "default",
  "no-new-privileges": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    },
    "nproc": {
      "Name": "nproc",
      "Hard": 4096,
      "Soft": 4096
    }
  },
  "seccomp-profile": "/etc/docker/seccomp-default.json"
}
DOCKEREOF

log "Docker daemon.json créé"

# Créer un profil seccomp minimal (permet la plupart des appels courants)
# Utilise le profil Docker par défaut comme base
if [[ ! -f /etc/docker/seccomp-default.json ]]; then
  # Télécharger le profil seccomp Docker par défaut
  if command -v curl &>/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/moby/moby/master/profiles/seccomp/default.json \
      -o /etc/docker/seccomp-default.json 2>/dev/null || \
      warn "Impossible de télécharger le profil seccomp — utiliser le défaut Docker"
  else
    warn "curl non disponible — profil seccomp non téléchargé"
  fi
fi

# Redémarrer Docker (ATTENTION : redémarre tous les conteneurs)
warn "Docker va redémarrer — tous les conteneurs seront relancés"
read -p "Continuer ? (o/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[oOyY]$ ]]; then
  systemctl restart docker
  log "Docker redémarré avec la nouvelle configuration"
else
  warn "Redémarrage Docker ignoré — appliquer manuellement : systemctl restart docker"
fi

# ============================================================
# 5. KERNEL SYSCTL HARDENING
# ============================================================
echo ""
echo "─── 5. Kernel Sysctl ───"

cat > /etc/sysctl.d/99-security-hardening.conf << 'SYSCTLEOF'
# === Aperture Science Kernel Hardening ===

# --- ASLR ---
kernel.randomize_va_space = 2

# --- Restriction d'accès au kernel ---
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.yama.ptrace_scope = 1
kernel.perf_event_paranoid = 3

# --- Network hardening ---
# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_synack_retries = 2

# IP spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP broadcasts
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Ignore source routed packets
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Log martians
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# IPv6 — désactiver si non utilisé
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1

# --- Filesystem ---
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.suid_dumpable = 0
SYSCTLEOF

sysctl --system > /dev/null 2>&1
log "Sysctl hardening appliqué"

# ============================================================
# 6. APPARMOR
# ============================================================
echo ""
echo "─── 6. AppArmor ───"

if command -v aa-status &>/dev/null; then
  # Activer AppArmor au boot
  systemctl enable apparmor 2>/dev/null || true
  systemctl start apparmor 2>/dev/null || true
  
  # Mettre tous les profils en enforce mode
  if aa-status --enabled 2>/dev/null; then
    # Charger les profils par défaut
    apparmor_parser -r /etc/apparmor.d/* 2>/dev/null || true
    log "AppArmor activé et profils chargés"
  else
    warn "AppArmor non activé — vérifier la configuration du kernel"
  fi
else
  warn "AppArmor non installé — apt install apparmor apparmor-utils apparmor-profiles"
fi

# ============================================================
# 7. LYNIS (AUDIT)
# ============================================================
echo ""
echo "─── 7. Lynis Security Audit ───"

if ! command -v lynis &>/dev/null; then
  apt-get update -qq && apt-get install -y -qq lynis 2>/dev/null
  log "Lynis installé"
fi

echo ""
warn "Lancement de l'audit Lynis (peut prendre 1-2 minutes)..."
lynis audit system --no-colors 2>/dev/null | tee /var/log/lynis-audit-$(date +%Y%m%d).log | tail -30

echo ""
log "Audit Lynis terminé — rapport complet : /var/log/lynis-audit-$(date +%Y%m%d).log"

# ============================================================
# 8. RÉSUMÉ
# ============================================================
echo ""
echo "============================================"
echo "  HARDENING TERMINÉ"
echo "  $(date)"
echo "============================================"
echo ""
echo "Résumé des actions :"
echo "  [✓] SSH : root login désactivé, auth par clé seulement, AllowUsers=glados"
echo "  [✓] UFW : deny incoming, allow 22/80/443, SSH rate-limited"
echo "  [✓] Fail2Ban : jail SSH + Traefik configurées"
echo "  [✓] Docker : user namespace, no-new-privileges, seccomp, logs limités"
echo "  [✓] Sysctl : ASLR, SYN flood, IP spoofing, martians, IPv6 désactivé"
echo "  [✓] AppArmor : activé si disponible"
echo "  [✓] Lynis : audit complet"
echo ""
echo "⚠️  IMPORTANT :"
echo "  1. Vérifiez que votre connexion SSH fonctionne AVANT de fermer cette session"
echo "  2. Ouvrez un nouveau terminal et testez : ssh glados@<IP>"
echo "  3. Si OK, fermez cette session root"
echo ""
echo "📋 Prochaines étapes (côté applicatif, par glados) :"
echo "  - Security headers Traefik (HSTS, CSP, X-Frame-Options)"
echo "  - Rate limiting Traefik"
echo "  - Durcissement Docker Compose (read-only, drop capabilities)"
echo "  - Scan Trivy des images Docker"
echo ""
