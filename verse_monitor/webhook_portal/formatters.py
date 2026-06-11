"""Multi-format webhook payload formatters.

Supports Discord (via existing formatter), Slack Block Kit, Telegram MarkdownV2,
and a raw generic JSON format.
"""

from __future__ import annotations

from verse_monitor.alerts.formatter import format_discord_payload
from verse_monitor.models import Priority, SCEvent

_PRIORITY_COLOR: dict[Priority, str] = {
    Priority.CRITICAL: "#ff0000",
    Priority.HIGH: "#ff8c00",
    Priority.MEDIUM: "#0080ff",
    Priority.LOW: "#808080",
}

_PRIORITY_EMOJI: dict[Priority, str] = {
    Priority.CRITICAL: "🚨",
    Priority.HIGH: "⚠️",
    Priority.MEDIUM: "📌",
    Priority.LOW: "ℹ️",
}

_TELEGRAM_SPECIAL = r"_*[]()~`>#+-=|{}.!"


def _escape_telegram(text: str) -> str:
    """Escape MarkdownV2 special characters for Telegram."""
    return "".join(f"\\{c}" if c in _TELEGRAM_SPECIAL else c for c in text)


def format_slack_payload(event: SCEvent) -> dict:
    """Slack Block Kit payload with color-coded attachment and header."""
    color = _PRIORITY_COLOR.get(event.priority, "#808080")
    emoji = _PRIORITY_EMOJI.get(event.priority, "📡")
    url = event.url or "https://robertsspaceindustries.com"
    event_type_label = event.type.value.replace("_", " ").title()

    return {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} {event_type_label}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{event.title}*\n<{url}|View on RSI>",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Priority: *{event.priority.value}*",
                            }
                        ],
                    },
                ],
            }
        ]
    }


def format_telegram_payload(event: SCEvent) -> dict:
    """Telegram Bot API payload using MarkdownV2 formatting."""
    url = event.url or "https://robertsspaceindustries.com"
    type_label = _escape_telegram(event.type.value.replace("_", " ").title())
    title = _escape_telegram(event.title)
    priority = _escape_telegram(event.priority.value)

    text = (
        f"*{type_label}*\n"
        f"{title}\n"
        f"Priority: `{priority}`\n"
        f"[View]({url})"
    )

    return {"text": text, "parse_mode": "MarkdownV2"}


def format_generic_payload(event: SCEvent) -> dict:
    """Raw JSON payload containing the full event data."""
    return {"event": event.model_dump(mode="json")}


FORMATTERS: dict[str, object] = {
    "discord": format_discord_payload,
    "slack": format_slack_payload,
    "telegram": format_telegram_payload,
    "generic": format_generic_payload,
}


def get_formatter(format: str):
    """Return formatter callable for the given format name; falls back to generic."""
    return FORMATTERS.get(format, format_generic_payload)
