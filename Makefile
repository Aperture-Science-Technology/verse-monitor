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

ingest: ## Run big batch ingestion (MAX_PAGES=200)
	cd /home/glados/projects/verse-monitor && \
	REDIS_URL="redis://:$$(grep REDIS_PASSWORD /home/glados/deployments/verse-monitor/.env | cut -d= -f2-)@redis-verse:6379" \
	QDRANT_URL="http://qdrant:6333" \
	OPENROUTER_API_KEY="$$(grep OPENROUTER_API_KEY /home/glados/deployments/verse-monitor/.env | cut -d= -f2-)" \
	MAX_PAGES=200 \
	docker run --rm --network verse-monitor-network \
		-v /home/glados/projects/verse-monitor:/app:ro \
		-w /app -e REDIS_URL -e QDRANT_URL -e OPENROUTER_API_KEY -e MAX_PAGES \
		python:3.12-slim \
		bash -c 'pip install -e . -q 2>&1 | tail -3 && python3 scripts/ingest_big_batch.py'

ingest-direct: ## Run direct event ingestion (devtracker/roadmap/comm-links)
	cd /home/glados/projects/verse-monitor && \
	REDIS_URL="redis://:$$(grep REDIS_PASSWORD /home/glados/deployments/verse-monitor/.env | cut -d= -f2-)@redis-verse:6379" \
	QDRANT_URL="http://qdrant:6333" \
	OPENROUTER_API_KEY="$$(grep OPENROUTER_API_KEY /home/glados/deployments/verse-monitor/.env | cut -d= -f2-)" \
	docker run --rm --network verse-monitor-network \
		-v /home/glados/projects/verse-monitor:/app:ro \
		-w /app -e REDIS_URL -e QDRANT_URL -e OPENROUTER_API_KEY \
		python:3.12-slim \
		bash -c 'pip install -e . -q 2>&1 | tail -3 && python3 scripts/ingest_events_direct.py'

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
