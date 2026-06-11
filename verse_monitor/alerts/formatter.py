"""Formatter Discord : templates markdown par EventType.

Zéro LLM — uniquement des templates structurés avec les champs de l'événement.
"""

from verse_monitor.models import EventType, SCEvent

_TEMPLATES: dict[EventType, str] = {
    EventType.ROADMAP_CARD_DELAYED: "⚠️ **Glissement roadmap**\n**{card}** : {from_patch} → {to_patch}\n[Roadmap]({url})",
    EventType.ROADMAP_CARD_RELEASED: "✅ **Feature live !**\n**{card}** disponible dans {patch}\n[Roadmap]({url})",
    EventType.ROADMAP_CARD_REMOVED: "🗑️ **Card supprimée**\n**{card}** ({patch})\n[Roadmap]({url})",
    EventType.ROADMAP_CARD_ADDED: "🆕 **Nouvelle card**\n**{card}** → {patch}\n[Roadmap]({url})",
    EventType.ROADMAP_CARD_UPDATED: "📝 **Card mise à jour**\n**{card}** : {from_patch} → {to_patch}\n[Roadmap]({url})",
    EventType.PATCH_NOTES_LIVE: "🚨 **Patch notes live**\n**{title}**\n[Patch notes]({url})",
    EventType.DEVTRACKER_POST: "📌 **Post dev — {author}**\n**{title}**\n{preview}\n[Spectrum]({url})",
    EventType.COMM_LINK_PUBLISHED: "📰 **Comm-Link**\n**{title}**\n[Comm-Link]({url})",
    EventType.TWISC_PUBLISHED: "📋 **This Week in Star Citizen**\n**{title}**\n[Lire]({url})",
    EventType.MONTHLY_REPORT: "📊 **Rapport mensuel**\n**{title}**\n[Lire]({url})",
}

_FALLBACK = "📡 **{event_type}**\n**{title}**\n[Lien]({url})"


def format_discord_payload(event: SCEvent) -> dict:
    """Formate un événement en payload Discord (JSON)."""
    template = _TEMPLATES.get(event.type, _FALLBACK)

    # Constrict le contexte de formatage depuis l'event + diff
    ctx = {
        "title": event.title,
        "url": event.url or "https://robertsspaceindustries.com",
        "author": event.author or "CIG",
        "preview": event.diff.get("preview", ""),
        "event_type": event.type.value,
    }
    # Ajouter les champs diff
    ctx.update(event.diff)

    try:
        content = template.format(**ctx)
    except KeyError as e:
        content = _FALLBACK.format(**ctx)

    return {"content": content}
