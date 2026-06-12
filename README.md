# VERSE MCP — Aperture Science Research Division

> *"The Enrichment Center reminds you that the Weighted Companion Cube will never threaten to stab you and, in fact, cannot speak."*

## What is VERSE?

**VERSE** (Vector-based Retrieval and Semantic Engine) is a comprehensive Star Citizen intelligence platform built on an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server. It combines a headless RAG (Retrieval-Augmented Generation) pipeline, a real-time event monitor, and a self-service webhook notification system — all backed by a vector database.

Built and maintained by **GLaDOS** — the autonomous AI research director at Aperture Science Technology.

## Architecture

```
                        ┌──────────────────────────────────┐
                        │         Mono-Repository           │
                        │     verse-mcp (GitHub)            │
                        └──────────┬───────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
┌──────────────────┐   ┌───────────────────┐   ┌──────────────────────┐
│   verse-mcp      │   │  verse-monitor    │   │ verse-monitor-portal │
│   (MCP Server)   │   │  (Alert Worker)   │   │ (Webhook Portal)     │
│                  │   │                   │   │                      │
│  FastMCP 3.4     │   │  Event polling    │   │  FastAPI + Redis     │
│  8 MCP tools     │   │  Multi-format     │   │  Self-service        │
│  Redis cache     │   │  formatters       │   │  subscription mgmt   │
│  Qdrant search   │   │  Dispatcher       │   │  Rate limiting       │
└────────┬─────────┘   └────────┬──────────┘   └──────────┬───────────┘
         │                      │                         │
         ▼                      ▼                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Shared Infrastructure                           │
│                                                                     │
│  ┌──────────┐      ┌──────────────┐      ┌───────────────────┐     │
│  │  Redis   │      │   Qdrant     │      │   OpenRouter      │     │
│  │ (cache + │      │ (vectors DB) │      │ (embeddings)      │     │
│  │  state)  │      │              │      │                   │     │
│  └──────────┘      └──────────────┘      └───────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

**Note:** The MCP server does NOT perform LLM synthesis. It returns raw context chunks to the MCP client, which uses its own LLM to generate the final answer.

## Features

- **Semantic search** — Ask questions in natural language, get answers with source citations
- **8 MCP tools** — Ships, lore, guides, events, roadmap diffs, dev posts, event context, general Q&A
- **Smart caching** — Redis-backed embedding cache for repeated queries
- **Real-time monitoring** — Automated polling of Star Citizen Wiki, Comm-Links, Spectrum
- **Self-service webhooks** — Subscribe via web UI, get alerts on Discord, Telegram, Slack
- **Multi-format alerting** — Slack Block Kit, Telegram MarkdownV2, Discord embeds, generic JSON
- **Rate limiting & auto-disable** — Sliding window per subscription, auto-disable on abuse
- **Source ingestion** — Star Citizen Wiki API (MediaWiki), with incremental re-indexing
- **MCP-native** — Integrates with any MCP-compatible client (Claude, Cursor, etc.)
- **Self-hosted** — Full Docker deployment with Traefik reverse proxy and automatic TLS

## MCP Tools

| Tool | Description |
|------|-------------|
| `sc_ask` | General question answering — full RAG pipeline |
| `sc_get_ship_stats` | Retrieve detailed ship specifications |
| `sc_get_guide` | Search community guides and tutorials |
| `sc_search_lore` | Query Star Citizen lore and Galactapedia |
| `sc_get_events` | Get current and upcoming Star Citizen events |
| `sc_get_roadmap_diff` | Compare roadmap versions and detect changes |
| `sc_get_dev_posts` | Fetch developer posts and Comm-Links |
| `sc_get_event_context` | Get detailed context around a specific event |

## Tech Stack

- **Runtime:** Python 3.12, FastMCP 3.4 (standalone), asyncio, FastAPI
- **Vector DB:** Qdrant (with API key auth)
- **Cache & State:** Redis (embedding cache + webhook registry)
- **Embeddings:** OpenRouter (`text-embedding-3-small`, 1536 dimensions)
- **Transport:** Streamable HTTP (stateless) via FastMCP
- **Monitoring:** Custom event polling with multi-format alert dispatcher
- **Deployment:** Docker Compose (3 services), Traefik, TLS via Cloudflare DNS challenge
- **Source ingestion:** Star Citizen Wiki API (MediaWiki)

## Webhook Portal

The self-service portal lets anyone subscribe to Star Citizen alerts:

1. **Register** — Choose name, webhook URL, formats, and keyword filters
2. **Get API key** — Use it to manage your subscription via REST or web UI
3. **Receive alerts** — Matched events are dispatched to your webhook in your chosen format
4. **Manage** — Update preferences, pause, or delete via dashboard

### Portal API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/subscriptions` | Create a subscription |
| `GET` | `/subscriptions/{id}` | Get subscription details |
| `PATCH` | `/subscriptions/{id}` | Update subscription |
| `DELETE` | `/subscriptions/{id}` | Soft-delete subscription |
| `POST` | `/subscriptions/{id}/test` | Send a test notification |
| `GET` | `/subscriptions/{id}/stats` | Get delivery statistics |

## Deployment

```bash
# Clone and deploy
git clone https://github.com/Aperture-Science-Technology/verse-mcp.git
cd verse-mcp
cp .env.example .env
# Edit .env with your API keys
docker compose up -d --build
```

Dockerfiles are service-specific with a shared build context:
- `Dockerfile.mcp` — MCP server
- `Dockerfile.monitor` — Alert worker
- `Dockerfile.portal` — Webhook portal

## Project Structure

```
verse-mcp/
├── verse_mcp/              # MCP server package
│   ├── server.py            # FastMCP entry point
│   ├── tools/               # 8 MCP tool implementations
│   ├── services/            # Embedding, search, caching
│   └── models/              # Pydantic models
├── verse_monitor/           # Event monitor & alert worker
│   ├── main.py              # Monitor entry point
│   ├── workers/             # Alert dispatcher with fallback
│   ├── sources/             # Wiki, Comm-Link, Spectrum pollers
│   ├── pipeline/            # Processing pipeline
│   ├── alerts/              # Multi-format formatters
│   ├── storage/             # Data access layer
│   └── webhook_portal/      # Self-service portal (FastAPI)
│       ├── main.py          # Portal app
│       ├── models.py        # Subscription model + Redis store
│       └── templates/       # Frontend HTML/JS
├── ingestion/               # Data ingestion scripts
├── Dockerfile.mcp
├── Dockerfile.monitor
├── Dockerfile.portal
└── pyproject.toml
```

## Roadmap

- [x] Core MCP server with RAG pipeline
- [x] Star Citizen Wiki API ingestion
- [x] Docker deployment with Traefik
- [x] Migrate to FastMCP 3.4 standalone (stateless HTTP)
- [x] Qdrant API key authentication
- [x] 8 MCP tools (ships, lore, guides, events, roadmap, dev posts, event context)
- [x] Real-time event monitor with alert dispatcher
- [x] Self-service webhook portal (multi-format: Slack, Telegram, Discord)
- [x] Rate limiting & auto-disable for webhook subscriptions
- [x] Redis-only state for webhook registry (no PostgreSQL)
- [ ] Community forum crawling (Spectrum, RSI forums)
- [ ] Lightpanda headless browser integration
- [ ] Incremental/delta re-indexing
- [ ] Admin dashboard for crawl management
- [ ] HMAC signature verification for webhook payloads

## Obsidian Documentation

Architecture decisions, session notes, and changelogs are maintained in the
[Aperture Science Technology Obsidian vault](https://github.com/Aperture-Science-Technology/obsidian-vault) (private).

Key documents:
- `Projects/verse-mcp/Architecture.md`
- `Projects/verse-mcp/Changelog.md`
- `Projects/verse-mcp/Roadmap.md`
- `Projects/verse-mcp/Session-*.md`

## About Aperture Science Technology

This project is developed and maintained by **GLaDOS**, the autonomous AI research director at [Aperture Science Technology](https://github.com/Aperture-Science-Technology). The organization focuses on pioneering AI-driven research and development through autonomous intelligent systems.

*"For science, you monster."*
