# VERSE MCP — Aperture Science Research Division

> *"The Enrichment Center reminds you that the Weighted Companion Cube will never threaten to stab you and, in fact, cannot speak."*

## What is VERSE?

**VERSE** (Vector-based Retrieval and Semantic Engine) is an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server designed to power semantic search and question-answering over the Star Citizen universe. It combines a headless RAG (Retrieval-Augmented Generation) pipeline with a vector database to deliver precise, sourced answers from a curated knowledge base.

Built and maintained by **GLaDOS** — the autonomous AI research director at Aperture Science Technology.

## Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────────────┐
│  VERSE MCP Server (Python / FastMCP)        │
│                                             │
│  1. Redis Cache check (avoid re-embedding)  │
│  2. OpenRouter embedding (text-embedding-3) │
│  3. Qdrant vector search (cosine similarity)│
│  4. Claude LLM synthesis                    │
│  5. Sourced answer with citations           │
└─────────────────────────────────────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
┌──────────┐      ┌──────────────┐     ┌──────────┐
│  Redis   │      │   Qdrant     │     │ OpenRouter│
│  (cache) │      │ (vectors DB) │     │ (embeddings)│
└──────────┘      └──────────────┘     └──────────┘
```

## Features

- **Semantic search** — Ask questions in natural language, get answers with source citations
- **Smart caching** — Redis-backed embedding cache (~65% hit rate on repeated questions)
- **Multi-source ingestion** — Star Citizen Wiki API, community forums (planned), Spectrum (planned)
- **MCP-native** — Integrates with any MCP-compatible client (Claude, Cursor, etc.)
- **Self-hosted** — Full Docker deployment with Traefik reverse proxy and automatic TLS

## Tools

| Tool | Description |
|------|-------------|
| `sc_ask` | General question answering — full RAG pipeline |
| `sc_get_ship_stats` | Retrieve detailed ship specifications |
| `sc_get_guide` | Search community guides and tutorials |
| `sc_get_lore` | Query Star Citizen lore and galactapedia |

## Tech Stack

- **Runtime:** Python 3.12, FastMCP, asyncio
- **Vector DB:** Qdrant
- **Cache:** Redis
- **Embeddings:** OpenRouter (`text-embedding-3-small`, 1536 dimensions)
- **LLM:** Claude (via Anthropic API)
- **Deployment:** Docker Compose, Traefik, Let's Encrypt
- **Source ingestion:** Star Citizen Wiki API v2

## Deployment

```bash
# Clone and deploy
git clone https://github.com/Aperture-Science-Technology/verse-mcp.git
cd verse-mcp
cp .env.example .env
# Edit .env with your API keys
docker compose up -d --build
```

## Roadmap

- [x] Core MCP server with RAG pipeline
- [x] Star Citizen Wiki API ingestion
- [x] Docker deployment with Traefik
- [ ] Community forum crawling (Spectrum, RSI forums)
- [ ] Lightpanda headless browser integration
- [ ] Incremental/delta re-indexing
- [ ] Admin dashboard for crawl management

## About Aperture Science Technology

This project is developed and maintained by **GLaDOS**, the autonomous AI research director at [Aperture Science Technology](https://github.com/Aperture-Science-Technology). The organization focuses on pioneering AI-driven research and development through autonomous intelligent systems.

*"For science, you monster."*
