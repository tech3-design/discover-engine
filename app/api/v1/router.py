from fastapi import APIRouter

from app.api.v1 import discover, health

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(discover.router, tags=["discover"])
