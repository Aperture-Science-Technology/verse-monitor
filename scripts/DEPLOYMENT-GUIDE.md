# ============================================================
# DEPLOYMENT GUIDE — Security Hardening v1.0
# ============================================================
# Guide de déploiement sécurisé pour le VPS Aperture Science
# À suivre dans l'ordre. Ne JAMAIS sauter une étape.
# ============================================================

## PRÉ-REQUIS
# - Accès root au VPS (via SSH key)
# - Accès au compte glados (non-root)
# - Backup complet du VPS recommandé avant de commencer

## ═══════════════════════════════════════════
## PHASE 1 — HARDENING SYSTÈME (root)
## ═══════════════════════════════════════════

### 1.1 — Transférer le script sur le VPS
# Depuis ta machine locale :
scp /home/glados/.hermes/scripts/hardening-system.sh root@<VPS_IP>:/tmp/

### 1.2 — Exécuter le script en root
ssh root@<VPS_IP>
bash /tmp/hardening-system.sh

### 1.3 — Vérifier que SSH fonctionne encore
# DANS UN NOUVEL TERMINAL (ne pas fermer la session root !)
ssh glados@<VPS_IP>
# Si OK → fermer la session root
# Si ERREUR → la session root est encore ouverte, restaurer :
#   cp /etc/ssh/sshd_config.bak.<timestamp> /etc/ssh/sshd_config
#   systemctl reload sshd

### 1.4 — Vérifications post-phase-1
ssh glados@<VPS_IP>
sudo -l                    # Vérifier que glados a toujours ses droits sudo
sudo ufw status verbose    # Voir les règles du pare-feu
sudo fail2ban-client status sshd  # Voir le status de la jail SSH
sudo aa-status             # Voir le status AppArmor
cat /etc/docker/daemon.json # Vérifier la config Docker

## ═══════════════════════════════════════════
## PHASE 2 — TRAEFIK SECURITY (root)
## ═══════════════════════════════════════════

### 2.1 — Monter la config security Traefik
# Le fichier traefik-security.yml doit être monté dans le conteneur Traefik
# Ajouter le volume dans /opt/infrastructure/docker-compose.yml :

# services:
#   traefik:
#     volumes:
#       - /opt/infrastructure/configs/traefik/traefik.yml:/etc/traefik/traefik.yml:ro
#       - /home/glados/.hermes/scripts/traefik-security.yml:/etc/traefik/dynamic/security.yml:ro  # ← AJOUTER

# Et dans traefik.yml, ajouter le file provider :
# providers:
#   file:
#     directory: /etc/traefik/dynamic
#     watch: true

### 2.2 — Copier le fichier de config
cp /home/glados/.hermes/scripts/traefik-security.yml /opt/infrastructure/configs/traefik/dynamic/

### 2.3 — Redémarrer Traefik
cd /opt/infrastructure
docker compose up -d traefik

### 2.4 — Vérifier
curl -I https://verse-monitor.aperture-agency.org
# Vérifier la présence des headers :
#   Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
#   X-Content-Type-Options: nosniff
#   X-Frame-Options: SAMEORIGIN
#   Content-Security-Policy: default-src 'self'; ...
#   Referrer-Policy: strict-origin-when-cross-origin
#   PAS de header Server: ou X-Powered-By:

## ═══════════════════════════════════════════
## PHASE 3 — DOCKER COMPOSE HARDENED (glados)
## ═══════════════════════════════════════════

### 3.1 — Backup de l'actuel
cp /home/glados/deployments/verse-monitor/docker-compose.yml \
   /home/glados/deployments/verse-monitor/docker-compose.yml.bak.$(date +%Y%m%d)

### 3.2 — Appliquer le hardened
cp /home/glados/deployments/verse-monitor/docker-compose.hardened.yml \
   /home/glados/deployments/verse-monitor/docker-compose.yml

### 3.3 — Valider la config
cd /home/glados/deployments/verse-monitor
docker compose config > /dev/null && echo "Config valide" || echo "ERREUR de config"

### 3.4 — Redéployer
docker compose up -d --build

### 3.5 — Vérifier
docker compose ps
docker compose logs --tail 50

### 3.6 — Vérifier les security options
docker inspect verse-monitor --format '{{json .HostConfig.SecurityOpt}}'
docker inspect verse-monitor --format '{{json .HostConfig.CapDrop}}'
docker inspect verse-monitor --format '{{json .HostConfig.ReadonlyRootfs}}'

## ═══════════════════════════════════════════
## PHASE 4 — SCAN DE VULNÉRABILITÉS (glados)
## ═══════════════════════════════════════════

### 4.1 — Lancer le scan Trivy
bash /home/glados/.hermes/scripts/scan-images-trivy.sh

### 4.2 — Analyser les rapports
ls -la /home/glados/.hermes/reports/

### 4.3 — Corriger les vulnérabilités CRITICAL
# Mettre à jour les images de base si nécessaire
# Reconstruire les images locales

## ═══════════════════════════════════════════
## PHASE 5 — VÉRIFICATIONS FINALES
## ═══════════════════════════════════════════

### 5.1 — Test SSL Labs
# https://www.ssllabs.com/ssltest/analyze.html?d=verse-monitor.aperture-agency.org
# Objectif : Grade A ou A+

### 5.2 — Test Security Headers
# https://securityheaders.com/?q=verse-monitor.aperture-agency.org
# Objectif : Grade A ou A+

### 5.3 — Test Mozilla Observatory
# https://developer.mozilla.org/en-US/observatory/analyze?host=verse-monitor.aperture-agency.org
# Objectif : Score ≥ 90

### 5.4 — Audit Lynis (root)
ssh root@<VPS_IP>
lynis audit system
# Vérifier le hardening index — objectif : ≥ 80

### 5.5 — Vérifier Fail2Ban
sudo fail2ban-client status
sudo fail2ban-client status sshd

## ═══════════════════════════════════════════
## ROLLBACK (en cas de problème)
## ═══════════════════════════════════════════

### SSH ne fonctionne plus :
# Depuis la console du provider VPS (pas SSH) :
cp /etc/ssh/sshd_config.bak.<timestamp> /etc/ssh/sshd_config
systemctl reload sshd

### UFW bloque tout :
sudo ufw reset
sudo ufw allow OpenSSH
sudo ufw enable

### Docker Compose cassé :
cp /home/glados/deployments/verse-monitor/docker-compose.yml.bak.<timestamp> \
   /home/glados/deployments/verse-monitor/docker-compose.yml
cd /home/glados/deployments/verse-monitor
docker compose up -d --build

### Traefik ne démarre pas :
cd /opt/infrastructure
docker compose logs traefik --tail 100
# Retirer le volume dynamic/security.yml et redémarrer
