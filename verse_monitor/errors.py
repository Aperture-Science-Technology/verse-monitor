"""Error classification for Qdrant and MCP service errors.

Maps raw exceptions to structured JSON responses with error codes,
severity levels, and actionable messages for MCP tool consumers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedError:
    """Structured error response for MCP tools."""
    error: str
    error_code: str
    severity: str  # "transient", "config", "service", "unknown"
    message: str
    details: str = ""
    retryable: bool = False
    suggested_action: str = ""


def classify_qdrant_error(exc: Exception) -> ClassifiedError:
    """Classify a Qdrant or client error into a structured response.

    Handles:
    - 404 "Collection doesn't exist" → transient, retryable, triggers re-index
    - 400 "Vector dimension error" → config error, needs manual fix
    - AttributeError (no attribute 'search') → service error, SDK mismatch
    - Connection errors → transient, retryable
    - Everything else → unknown
    """
    exc_str = str(exc)
    exc_type = type(exc).__name__

    # 404 — Collection doesn't exist
    if "404" in exc_str or "doesn't exist" in exc_str or "Not found" in exc_str:
        return ClassifiedError(
            error="collection_not_found",
            error_code="QDRANT_404",
            severity="transient",
            message="La collection Qdrant est introuvable. Une re-indexation est nécessaire.",
            details=exc_str,
            retryable=True,
            suggested_action="Déclencher une re-indexation de la collection.",
        )

    # 400 — Vector dimension mismatch
    if "400" in exc_str or "dimension" in exc_str.lower():
        return ClassifiedError(
            error="dimension_mismatch",
            error_code="QDRANT_400",
            severity="config",
            message="La dimension des vecteurs ne correspond pas à la configuration de la collection.",
            details=exc_str,
            retryable=False,
            suggested_action="Supprimer et recréer la collection avec la bonne dimension (1536).",
        )

    # AttributeError — SDK method not found (e.g. 'search' vs 'query_points')
    if exc_type == "AttributeError" and "QdrantClient" in exc_str:
        return ClassifiedError(
            error="sdk_mismatch",
            error_code="QDRANT_SDK",
            severity="service",
            message="Incompatibilité du client Qdrant. Méthode introuvable.",
            details=exc_str,
            retryable=False,
            suggested_action="Vérifier la version du client Qdrant et utiliser query_points().",
        )

    # Connection errors
    if exc_type in ("ConnectionError", "ConnectTimeout", "TimeoutError"):
        return ClassifiedError(
            error="connection_failed",
            error_code="QDRANT_CONN",
            severity="transient",
            message="Impossible de se connecter à Qdrant.",
            details=exc_str,
            retryable=True,
            suggested_action="Vérifier que Qdrant est accessible et relancer.",
        )

    # Fallback — unknown error
    return ClassifiedError(
        error="unknown",
        error_code="UNKNOWN",
        severity="unknown",
        message="Erreur inattendue lors de l'accès à Qdrant.",
        details=exc_str,
        retryable=False,
        suggested_action="Consulter les logs pour plus de détails.",
    )


def error_to_json(exc: Exception) -> str:
    """Classify an error and return it as a JSON string for MCP tool responses."""
    classified = classify_qdrant_error(exc)
    return __import__("json").dumps(asdict(classified), indent=2, ensure_ascii=False)
