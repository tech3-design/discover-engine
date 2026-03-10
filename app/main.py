from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register all checkers on startup
    import app.checkers.site_foundation  # noqa: F401
    import app.checkers.indexability_speed  # noqa: F401
    import app.checkers.graph_discovery  # noqa: F401
    import app.checkers.node_readability  # noqa: F401
    import app.checkers.authority_trust  # noqa: F401
    import app.checkers.llm_extraction  # noqa: F401
    import app.checkers.content_quality  # noqa: F401

    from app.checkers.registry import registry

    structlog.get_logger().info(
        "checkers_registered", count=len(registry.all())
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.v1.router import v1_router

    app.include_router(v1_router)

    return app


app = create_app()
