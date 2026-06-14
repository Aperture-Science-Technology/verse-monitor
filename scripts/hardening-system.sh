#!/bin/bash
# ============================================================
# Aperture Science VPS — Security Hardening Script v2.0
# Debian 13 (trixie) — À exéiter en root (une seule fois)
# ============================================================
# Ce script durcit :
#   1. Crée un user admin (sudo) pour l'administration sécurité
#   2. SSH : désactive root, auth par clé, AllowUsers=admin
#   3. UFW (pare-feu)
#   4. Fail2Ban
#   5. Docker daemon
#   6. Kernel sysctl
#   7. AppArmor
#   8. Audit Lynis
# ============================================================
# Architecture post-hardening :
#   root    : désactivé en SSH
#   admin   : sudo complet, accès SSH autorisé
#   glados  : pas de sudo, accès SSH désactivé (apps uniquement via Docker)
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
echo "  Aperture Science VPS — Hardening v2.0"
echo "  $(date)"
echo "============================================"
echo ""

# ─── Demander le mot de passe admin ──────────────────────
echo "Création du compte admin (sudo, accès SSH)."
read -sp "Choisir un mot de passe pour admin : " ADMIN_PASS
echo ""
read -sp "Confirmer le mot de passe : " ADMIN_PASS_CONFIRM
echo ""

if [[ "$ADMIN_PASS" != "$ADMIN_PASS_CONFIRM" ]]; then
   err "Les mots de passe ne correspondent pas. Annulation."
   exit 1
fi

if [[ -z "$ADMIN_PASS" ]]; then
   err "Le mot de passe ne peut pas être vide. Annulation."
   exit 1
fi

log "Mot de passe admin validé"

# ============================================================
# 1. CRÉATION DU USER ADMIN
# ============================================================
echo ""
echo "─── 1. Création du user admin ───"

if id "admin" &>/dev/null; then
   warn "Le user admin existe déjà — on le met à jour"
   usermod -aG sudo admin 2>/dev/null || true
else
   useradd -m -s /bin/bash -G sudo admin
   echo "admin:${ADMIN_PASS}" | chpasswd
   log "User admin créé avec sudo"
fi

# Admin peut utiliser sudo sans mot de passe (pratique pour les scripts automatisés)
echo "admin ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/admin
chmod 440 /etc/sudoers.d/admin
log "Sudo sans mot de passe configuré pour admin"

# Créer le répertoire .ssh pour admin
mkdir -p /home/admin/.ssh
chmod 700 /home/admin/.ssh
touch /home/admin/.ssh/authorized_keys
chmod 600 /home/admin/.ssh/authorized_keys
chown -R admin:admin /home/admin/.ssh
log "Répertoire .ssh/admin préparé"

echo ""
warn "⚠️  IMPORTANT : Copier ta clé publique SSH dans /home/admin/.ssh/authorized_keys"
warn "   Pour l'instant, la connexion par mot de passe est activée temporairement"
warn "   pour permettre le premier login admin et la copie de la clé."
echo ""

# ============================================================
# 2. SSH HARDENING
# ============================================================
echo "─── 2. SSH Hardening ───"

# Sauvegarde
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d%H%M%S)
log "Sauvegarde sshd_config créée"

# Configuration SSH durcie
cat > /etc/ssh/sshd_config.d/99-hardening.conf << 'SSHEOF'
# === Aperture Science SSH Hardening v2 ===
# Généré automatiquement — ne pas éditer manuellement

# Authentification
# Root désactivé — seul admin peut se connecter en SSH
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no

# Restriction d'accès — seul admin peut se connecter
AllowUsers admin
MaxAuthTries 3
LoginGraceTime 20

# Désactiver les fonctionnalités dangereuses
X11Forwarding no
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

# Timeouts — déconnecte les sessions zombies
ClientAliveInterval 300
ClientAliveCountMax 2
SSHEOF

log "Configuration SSH hardening écrite (root désactivé, admin seul autorisé)"

# Valider la config SSH avant reload
if sshd -t 2>/dev/null; then
    log "Configuration SSH valide"
else
    err "ERREUR de configuration SSH — vérifiez avec: sshd -t"
    exit 1
fi

warn "La configuration SSH est prête."
warn "AVANT de recharger SSH, assurez-vous que :"
warn "  1. Votre clé publique est dans /home/admin/.ssh/authorized_keys"
warn "  2. Vous pouvez vous connecter en admin dans un AUTRE terminal"
echo ""
read -p "Recharger SSH maintenant ? (o/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[oOyY]$ ]]; then
    systemctl reload sshd
    log "SSHD rechargé"
else
    warn "SSH non rechargé — rechargez manuellement : systemctl reload sshd"
fi

# ============================================================
# 3. UFW (PARE-FEU)
# ============================================================
echo ""
echo "─── 3. UFW Firewall ───"

ufw --force reset
log "UFW reset"

ufw default deny incoming
ufw default allow outgoing
log "Politiques par défaut : deny incoming, allow outgoing"

ufw limit 22/tcp comment 'SSH rate-limited'
log "SSH (22) — rate limité"

ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
log "HTTP (80) + HTTPS (443) autorisés"

ufw --force enable
log "UFW activé"
ufw status verbose

# ============================================================
# 4. FAIL2BAN
# ============================================================
echo ""
echo "─── 4. Fail2Ban ───"

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

cat > /etc/fail2ban/filter.d/traefik-auth.conf << 'F2BEOF'
[Definition]
failregex = ^<HOST> .* "(GET|POST|PUT|DELETE) .*" (401|403|429) .*$
ignoreregex =
F2BEOF
log "Jail Traefik auth configurée"

systemctl restart fail2ban
log "Fail2Ban redémarré"

# ============================================================
# 5. DOCKER DAEMON HARDENING
# ============================================================
echo ""
echo "─── 5. Docker Daemon ───"

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
  }
}
DOCKEREOF
log "Docker daemon.json créé (user namespace, no-new-privileges, seccomp, logs)"

warn "Docker va redémarrer — tous les conteneurs seront relancés"
read -p "Continuer ? (o/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[oOyY]$ ]]; then
   systemctl restart docker
   log "Docker redémarré"
else
   warn "Redémarrage Docker ignoré — appliquer manuellement : systemctl restart docker"
fi

# ============================================================
# 6. KERNEL SYSCTL HARDENING
# ============================================================
echo ""
echo "─── 6. Kernel Sysctl ───"

cat > /etc/sysctl.d/99-security-hardening.conf << 'SYSCTLEOF'
# === Aperture Science Kernel Hardening ===

# ASLR
kernel.randomize_va_space = 2

# Restriction d'accès au kernel
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.yama.ptrace_scope = 1
kernel.perf_event_paranoid = 3

# Network hardening
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

# Filesystem
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.suid_dumpable = 0
SYSCTLEOF

sysctl --system > /dev/null 2>&1
log "Sysctl hardening appliqué"

# ============================================================
# 7. APPARMOR
# ============================================================
echo ""
echo "─── 7. AppArmor ───"

if command -v aa-status &>/dev/null; then
  systemctl enable apparmor 2>/dev/null || true
  systemctl start apparmor 2>/dev/null || true
  if aa-status --enabled 2>/dev/null; then
    apparmor_parser -r /etc/apparmor.d/* 2>/dev/null || true
    log "AppArmor activé et profils chargés"
  else
    warn "AppArmor non activé — vérifier la configuration du kernel"
  fi
else
  warn "AppArmor non installé — apt install apparmor apparmor-utils apparmor-profiles"
fi

# ============================================================
# 8. LYNIS (AUDIT)
# ============================================================
echo ""
echo "─── 8. Lynis Security Audit ───"

if ! command -v lynis &>/dev/null; then
  apt-get update -qq && apt-get install -y -qq lynis 2>/dev/null
  log "Lynis installé"
fi

echo ""
warn "Lancement de l'audit Lynis (peut prendre 1-2 minutes)..."
lynis audit system --no-colors 2>/dev/null | tee /var/log/lynis-audit-$(date +%Y%m%d).log | tail -30

log "Audit Lynis terminé — rapport : /var/log/lynis-audit-$(date +%Y%m%d).log"

# ============================================================
# 9. RÉSUMÉ
# ============================================================
echo ""
echo "============================================"
echo "  HARDENING TERMINÉ"
echo "  $(date)"
echo "============================================"
echo ""
echo "Résumé :"
echo "  [✓] User admin créé (sudo, accès SSH)"
echo "  [✓] SSH : root désactivé, admin seul autorisé, auth par clé"
echo "  [✓] UFW : deny incoming, allow 22/80/443, SSH rate-limited"
echo "  [✓] Fail2Ban : jail SSH + Traefik configurées"
echo "  [✓] Docker : user namespace, no-new-privileges, seccomp, logs"
echo "  [✓] Sysctl : ASLR, SYN flood, IP spoofing, martians, IPv6 off"
echo "  [✓] AppArmor : activé si disponible"
echo "  [✓] Lynis : audit complet"
echo ""
echo "⚠️  PROCHAINES ÉTAPES :"
echo "  1. Copier ta clé SSH dans /home/admin/.ssh/authorized_keys"
echo "  2. Tester la connexion : ssh admin@<VPS_IP>"
echo "  3. Désactiver PasswordAuthentication (une fois la clé confirmée) :"
echo "     sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config.d/99-hardening.conf"
echo "     systemctl reload sshd"
echo ""
echo "📋 Architecture post-hardening :"
echo "   root   : désactivé en SSH"
echo "   admin  : sudo complet, accès SSH (sécurité/infra)"
echo "   glados : pas de sudo, apps uniquement (Docker compose)"
echo ""
