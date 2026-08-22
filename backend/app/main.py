from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": settings.app_name}
