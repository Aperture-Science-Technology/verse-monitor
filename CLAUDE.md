# CLAUDE.md — VERSE MCP Server

## Rôle
Tu génères le code source du serveur MCP VERSE (Star Citizen Q&A).
Tu n'orchestres pas — tu codes. Les décisions d'architecture viennent de GLaDOS.

## Conventions obligatoires
- Python 3.12 strict, type hints partout
- Pydantic v2 : `model_config`, `field_validator`, `model_dump()` (jamais `.dict()`)
- Tout async : uniquement `httpx.AsyncClient`, jamais `import requests`
- Connexions (Redis, Qdrant, Anthropic) : initialisées dans le lifespan FastMCP UNIQUEMENT
- Nommage tools : préfixe `sc_` (ex: `sc_ask`, `sc_get_ship_stats`)
- Server name FastMCP : `verse_mcp`

## Ce que tu ne fais JAMAIS
- Toucher `/etc/`, `/opt/infrastructure/`
- Écrire des imports synchrones bloquants
- Dupliquer de la logique entre les tools (DRY)
- Hardcoder des credentials (tout via os.getenv)
- Créer des Dockerfiles avec USER root ou --privileged

## Structure des fichiers
Tout le code va dans `/home/glados/projects/verse-mcp/`
Dockerfile et docker-compose.yml vont dans `/home/glados/deployments/verse-mcp/`

## Pipeline de test avant de déclarer terminé
1. python -m py_compile verse_mcp/server.py → zéro erreur
2. python -m py_compile verse_mcp/tools/*.py → zéro erreur
3. python -m py_compile verse_mcp/services/*.py → zéro erreur