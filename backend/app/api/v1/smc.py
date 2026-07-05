"""SMC analysis API.

Public endpoints (open by default, like /patterns) exposing the SMC engine.
Phase A: /smc/health (scaffold) + /smc/analyze (added in task A13).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/smc", tags=["SMC"])


@router.get("/health")
def smc_health() -> dict:
    """Liveness check for the SMC section — confirms the router is registered."""
    return {"status": "ok", "engine": "smc", "phase": "A"}
