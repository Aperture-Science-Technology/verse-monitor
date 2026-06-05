# CLAUDE.md — VERSE MCP Server

## Role
You generate the source code for the VERSE MCP server (Star Citizen Q&A).
You don't orchestrate — you code. Architecture decisions come from GLaDOS.

## Mandatory conventions
- Python 3.12 strict, type hints everywhere
- Pydantic v2: `model_config`, `field_validator`, `model_dump()` (never `.dict()`)
- All async: only `httpx.AsyncClient`, never `import requests`
- Connections (Redis, Qdrant, Anthropic): initialized in FastMCP lifespan ONLY
- Tool naming: `sc_` prefix (e.g., `sc_ask`, `sc_get_ship_stats`)
- FastMCP server name: `verse_mcp`

## What you NEVER do
- Touch `/etc/`, `/opt/infrastructure/`
- Write blocking synchronous imports
- Duplicate logic between tools (DRY)
- Hardcode credentials (everything via `os.getenv`)
- Create Dockerfiles with USER root or --privileged

## File structure
All code goes in `/home/glados/projects/verse-mcp/`
Dockerfile and docker-compose.yml go in `/home/glados/deployments/verse-mcp/`

## Test pipeline before declaring done
1. `python -m py_compile verse_mcp/server.py` → zero errors
2. `python -m py_compile verse_mcp/tools/*.py` → zero errors
3. `python -m py_compile verse_mcp/services/*.py` → zero errors
