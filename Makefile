# ============================================================
# verse-monitor — Makefile
# ============================================================
# Usage: make <target>
# ============================================================

.PHONY: help build up down restart logs status clean ingest shell-mcp shell-portal shell-worker

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Docker Compose ---

build: ## Build all images
	cd /home/glados/deployments/verse-monitor && docker compose build

up: ## Start all services
	cd /home/glados/deployments/verse-monitor && docker compose up -d

down: ## Stop all services
	cd /home/glados/deployments/verse-monitor && docker compose down

restart: ## Restart all services
	cd /home/glados/deployments/verse-monitor && docker compose restart

rebuild: down build up ## Full rebuild cycle

# --- Status ---

status: ## Show container status
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "verse-monitor|redis|qdrant|CONTAINER"

logs: ## Show all logs (last 50 lines)
	@echo "=== MCP ===" && docker logs verse-monitor-mcp --tail 50 2>&1
	@echo "=== Portal ===" && docker logs verse-monitor-portal --tail 50 2>&1
	@echo "=== Worker ===" && docker logs verse-monitor-worker --tail 50 2>&1

logs-mcp: ## Show MCP logs
	docker logs verse-monitor-mcp --tail 100 --follow

logs-portal: ## Show Portal logs
	docker logs verse-monitor-portal --tail 100 --follow

logs-worker: ## Show Worker logs
	docker logs verse-monitor-worker --tail 100 --follow

# --- Health ---

health: ## Check all health endpoints
	@echo "MCP:      $$(docker exec verse-monitor-mcp python3 -c 'import socket; s=socket.socket(); s.settimeout(3); s.connect((\"localhost\",8000)); s.close(); print(\"OK\")' 2>&1)"
	@echo "Portal:   $$(docker exec verse-monitor-portal python3 -c 'import socket; s=socket.socket(); s.settimeout(3); s.connect((\"localhost\",8080)); s.close(); print(\"OK\")' 2>&1)"
	@echo "Redis:    $$(docker exec redis-verse redis-cli -a $$(docker exec redis-verse redis-cli CONFIG GET requirepass | tail -1) ping 2>&1)"
	@echo "Qdrant:   $$(curl -s http://localhost:6333/health 2>/dev/null || echo 'N/A')"

# --- Ingestion ---

ingest: ## Run big batch ingestion (MAX_PAGES=200, sc_chunks)
	docker exec verse-monitor-mcp python3 -m scripts.ingest_big_batch

ingest-direct: ## Run direct event ingestion (devtracker/roadmap/comm-links → sc_events)
	docker exec verse-monitor-mcp python3 -m scripts.ingest_events_direct

ingest-check: ## Check ingestion stats
	@echo "=== Qdrant collections ==="
	@docker exec verse-monitor-mcp python3 -c "
from qdrant_client import QdrantClient
c = QdrantClient(url='http://qdrant:6333')
for col in c.get_collections().collections:
    info = c.get_collection(col.name)
    print(f'  {col.name}: {info.points_count} points')
"
	@echo "=== Redis stream ==="
	@docker exec redis-verse redis-cli -a $$(docker exec redis-verse redis-cli CONFIG GET requirepass | tail -1) XLEN sc:events 2>/dev/null || echo "  N/A"

# --- Shell Access ---

shell-mcp: ## Open shell in MCP container
	docker exec -it verse-monitor-mcp /bin/sh

shell-portal: ## Open shell in Portal container
	docker exec -it verse-monitor-portal /bin/sh

shell-worker: ## Open shell in Worker container
	docker exec -it verse-monitor-worker /bin/sh

# --- Cleanup ---

clean: ## Remove orphaned images and dangling volumes
	docker image prune -f
	docker volume prune -f

clean-all: down clean ## Full cleanup (stops everything)
