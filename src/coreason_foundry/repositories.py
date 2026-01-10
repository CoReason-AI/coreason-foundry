# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.models import ProjectORM
from coreason_foundry.managers import ProjectRepository
from coreason_foundry.models import Project


class SqlAlchemyProjectRepository(ProjectRepository):
    """
    SQLAlchemy implementation of ProjectRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, project: Project) -> Project:
        project_orm = ProjectORM(
            id=project.id,
            name=project.name,
            created_at=project.created_at,
            current_draft_id=project.current_draft_id,
        )
        # Check if exists to update or merge?
        # For now, simple merge logic or just add.
        # Since 'Project' model is Pydantic, we need to map to ORM.
        # If ID exists, we should probably update.
        # Using merge for simplicity in this implementation.
        merged_orm = await self.session.merge(project_orm)
        await self.session.flush()

        return Project(
            id=merged_orm.id,
            name=merged_orm.name,
            created_at=merged_orm.created_at,
            current_draft_id=merged_orm.current_draft_id,
        )

    async def get(self, project_id: UUID) -> Optional[Project]:
        result = await self.session.execute(select(ProjectORM).where(ProjectORM.id == project_id))
        project_orm = result.scalar_one_or_none()
        if not project_orm:
            return None
        return Project(
            id=project_orm.id,
            name=project_orm.name,
            created_at=project_orm.created_at,
            current_draft_id=project_orm.current_draft_id,
        )

    async def list_all(self) -> List[Project]:
        result = await self.session.execute(select(ProjectORM))
        projects_orm = result.scalars().all()
        return [
            Project(
                id=p.id,
                name=p.name,
                created_at=p.created_at,
                current_draft_id=p.current_draft_id,
            )
            for p in projects_orm
        ]
