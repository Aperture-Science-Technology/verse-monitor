#!/bin/bash
# ============================================================
# Docker Image Security Scanner — Trivy
# Scanne toutes les images utilisées dans les déploiements
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPORT_DIR="/home/glados/.hermes/reports"
mkdir -p "$REPORT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }

echo "============================================"
echo "  Docker Image Security Scan — Trivy"
echo "  $(date)"
echo "============================================"

# Installer Trivy si absent
if ! command -v trivy &>/dev/null; then
  warn "Trivy non trouvé — installation..."
  # Méthode d'installation officielle
  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
  log "Trivy installé : $(trivy --version)"
fi

# Liste des images à scanner
IMAGES=(
  "redis:7-alpine"
  "qdrant/qdrant:latest"
  "traefik:v3.6"
  "tecnativa/docker-socket-proxy:latest"
  "moby/buildkit:buildx-stable-1"
)

# Images locales (buildées)
LOCAL_IMAGES=(
  "verse-mcp-verse-mcp"
  "verse-mcp-verse-monitor"
  "verse-mcp-verse-monitor-portal"
)

CRITICAL=0
HIGH=0

echo ""
echo "─── Scan des images distantes ───"
for img in "${IMAGES[@]}"; do
  echo ""
  echo ">>> $img"
  REPORT_FILE="$REPORT_DIR/trivy-${img//[\/:]/_}-${TIMESTAMP}.json"
  
  if trivy image --severity HIGH,CRITICAL --format json --output "$REPORT_FILE" "$img" 2>/dev/null; then
    # Compter les vulnérabilités
    CRIT_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
    HIGH_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
    
    CRITICAL=$((CRITICAL + CRIT_COUNT))
    HIGH=$((HIGH + HIGH_COUNT))
    
    if [[ $CRIT_COUNT -gt 0 ]]; then
      err "  CRITICAL: $CRIT_COUNT | HIGH: $HIGH_COUNT"
    elif [[ $HIGH_COUNT -gt 0 ]]; then
      warn "  CRITICAL: 0 | HIGH: $HIGH_COUNT"
    else
      log "  Aucune vulnérabilité HIGH/CRITICAL"
    fi
  else
    err "  Échec du scan pour $img"
  fi
done

echo ""
echo "─── Scan des images locales ───"
for img in "${LOCAL_IMAGES[@]}"; do
  echo ""
  echo ">>> $img"
  if docker image inspect "$img" &>/dev/null; then
    REPORT_FILE="$REPORT_DIR/trivy-${img//[\/:]/_}-${TIMESTAMP}.json"
    
    if trivy image --severity HIGH,CRITICAL --format json --output "$REPORT_FILE" "$img" 2>/dev/null; then
      CRIT_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
      HIGH_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$REPORT_FILE" 2>/dev/null || echo "0")
      
      CRITICAL=$((CRITICAL + CRIT_COUNT))
      HIGH=$((HIGH + HIGH_COUNT))
      
      if [[ $CRIT_COUNT -gt 0 ]]; then
        err "  CRITICAL: $CRIT_COUNT | HIGH: $HIGH_COUNT"
      elif [[ $HIGH_COUNT -gt 0 ]]; then
        warn "  CRITICAL: 0 | HIGH: $HIGH_COUNT"
      else
        log "  Aucune vulnérabilité HIGH/CRITICAL"
      fi
    else
      err "  Échec du scan pour $img"
    fi
  else
    warn "  Image locale non trouvée : $img"
  fi
done

echo ""
echo "============================================"
echo "  RÉSUMÉ DU SCAN"
echo "============================================"
echo "  Total CRITICAL : $CRITICAL"
echo "  Total HIGH     : $HIGH"
echo "  Rapports       : $REPORT_DIR/"
echo ""

if [[ $CRITICAL -gt 0 ]]; then
  err "⚠️  $CRITICAL vulnérabilités CRITIQUES détectées — action immédiate requise"
  exit 1
elif [[ $HIGH -gt 0 ]]; then
  warn "⚠️  $HIGH vulnérabilités HIGH détectées — planifier les mises à jour"
  exit 0
else
  log "✅ Aucune vulnérabilité HIGH/CRITICAL détectée"
  exit 0
fi
