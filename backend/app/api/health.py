from fastapi import APIRouter
from sqlalchemy import text

from app.db.database import SessionLocal

router = APIRouter()


@router.get("/health")
async def health():
    """Basic liveness check. Always returns 200 if the application is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    """Readiness check. Verifies that the application can reach the database.

    Returns HTTP 200 if the database is reachable, HTTP 503 otherwise.
    Used by orchestrators to determine whether the service is ready for traffic.
    """
    from fastapi import Response

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        return Response(
            content='{"status":"unavailable","database":"error","detail":"'
            + str(exc)[:200]
            + '"}',
            status_code=503,
            media_type="application/json",
        )
    finally:
        db.close()
