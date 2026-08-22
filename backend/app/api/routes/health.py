import sqlite3

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from db.database import get_connection


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict[str, str]:
    try:
        connection = get_connection(settings.airport_database_file)
        try:
            data_status = connection.execute(
                "SELECT value FROM dataset_metadata WHERE key = 'status'"
            ).fetchone()
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The airport data snapshot is unavailable.",
        ) from exc

    if data_status is None or data_status["value"] != "complete":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The airport data snapshot is incomplete.",
        )

    return {"status": "ok", "data": "ready"}
