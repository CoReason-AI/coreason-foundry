# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from coreason_foundry.api.dependencies import get_redis_client
from coreason_foundry.api.routes import drafts, projects, realtime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.
    """
    # Startup
    yield
    # Shutdown
    redis = get_redis_client()
    await redis.aclose()


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    """
    app = FastAPI(
        title="CoReason Foundry API",
        description="The Collaborative Workspace Manager & Real-Time State Engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.include_router(projects.router)
    app.include_router(drafts.router)
    app.include_router(realtime.router)

    return app


app = create_app()
