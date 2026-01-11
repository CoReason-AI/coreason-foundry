# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.base import Base
from coreason_foundry.db.session import DatabaseSessionManager, DatabaseSettings


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Use in-memory SQLite for testing
    settings = DatabaseSettings(url="sqlite+aiosqlite:///:memory:")
    manager = DatabaseSessionManager(settings)
    manager.init()

    if manager._engine is None:
        raise Exception("Engine not initialized")  # pragma: no cover

    # Create tables
    async with manager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager.session() as session:
        yield session

    await manager.close()
