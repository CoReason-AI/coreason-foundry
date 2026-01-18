# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import uuid
from typing import Any

import pytest
from pydantic import BaseModel

from coreason_foundry.memory import GenericInMemoryRepository


class SimpleEntity(BaseModel):
    id: uuid.UUID


class SimpleInMemoryRepository(GenericInMemoryRepository[SimpleEntity]):
    def __init__(self) -> None:
        super().__init__({})

    async def add(self, entity: SimpleEntity) -> SimpleEntity:
        return await self._add(entity)

    async def update(self, entity: SimpleEntity) -> SimpleEntity:
        return await self._update(entity)

    async def get(self, entity_id: uuid.UUID) -> Any:
        return await self._get(entity_id)


@pytest.mark.asyncio
async def test_generic_repo_add_duplicate() -> None:
    repo = SimpleInMemoryRepository()
    entity_id = uuid.uuid4()
    entity = SimpleEntity(id=entity_id)

    await repo.add(entity)

    with pytest.raises(ValueError, match="already exists"):
        await repo.add(entity)


@pytest.mark.asyncio
async def test_generic_repo_update_not_found() -> None:
    repo = SimpleInMemoryRepository()
    entity_id = uuid.uuid4()
    entity = SimpleEntity(id=entity_id)

    with pytest.raises(ValueError, match="not found"):
        await repo.update(entity)


@pytest.mark.asyncio
async def test_generic_repo_delete() -> None:
    repo = SimpleInMemoryRepository()
    entity_id = uuid.uuid4()
    entity = SimpleEntity(id=entity_id)
    await repo.add(entity)

    assert await repo._delete(entity_id) is True
    assert await repo._delete(entity_id) is False
