"""Kronos singleton — optional via KRONOS_ENABLED.

When KRONOS_ENABLED=false (e.g. the Docker image, which ships without torch),
`kronos` is None: the app boots normally and /prediction endpoints return 503.
The import itself is gated because kronos_service imports torch at module level.
"""

import os

KRONOS_ENABLED = os.getenv("KRONOS_ENABLED", "true").strip().lower() in ("1", "true", "yes")

if KRONOS_ENABLED:
    from backend.app.services.kronos_service import KronosService

    kronos = KronosService()
else:
    kronos = None
