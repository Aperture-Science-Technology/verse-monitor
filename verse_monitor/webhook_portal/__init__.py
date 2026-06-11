"""webhook_portal — Self-service multi-webhook portal for verse-monitor.

Provides:
- Subscription model (Pydantic)
- SubscriptionStore (Redis-backed CRUD)
- FastAPI REST API
- Frontend (vanilla HTML/JS)
- Multi-format webhook delivery (Discord, Slack, Telegram, generic)

This module is split into subpackages:
  models.py        — Subscription Pydantic model
  store.py         — SubscriptionStore Redis CRUD
  api.py           — FastAPI REST app
  formatters.py    — Multi-format webhook payloads
  rate_limiter.py — Redis sliding-window rate limiter
  portal_worker.py — Alert worker integration (multi-webhook matcher)
"""
