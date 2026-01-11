# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.models import DraftORM, ProjectORM
from coreason_foundry.managers import ProjectRepository
from coreason_foundry.models import Draft, Project


class DraftRepository(ABC):
    """
    Abstract base class for Draft storage.
    """

    @abstractmethod
    async def save(self, draft: Draft) -> Draft:
        """Saves a draft."""
        pass  # pragma: no cover

    @abstractmethod
    async def get(self, draft_id: UUID) -> Optional[Draft]:
        """Retrieves a draft by ID."""
        pass  # pragma: no cover

    @abstractmethod
    async def list_by_project(self, project_id: UUID) -> List[Draft]:
        """Lists all drafts for a project."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_latest_version(self, project_id: UUID) -> Optional[int]:
        """Retrieves the latest version number for a project."""
        pass  # pragma: no cover


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


class SqlAlchemyDraftRepository(DraftRepository):
    """
    SQLAlchemy implementation of DraftRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, draft: Draft) -> Draft:
        draft_orm = DraftORM(
            id=draft.id,
            project_id=draft.project_id,
            version_number=draft.version_number,
            prompt_text=draft.prompt_text,
            model_configuration=draft.model_configuration,
            author_id=draft.author_id,
            created_at=draft.created_at,
        )
        merged_orm = await self.session.merge(draft_orm)
        await self.session.flush()

        return Draft(
            id=merged_orm.id,
            project_id=merged_orm.project_id,
            version_number=merged_orm.version_number,
            prompt_text=merged_orm.prompt_text,
            model_configuration=merged_orm.model_configuration,
            author_id=merged_orm.author_id,
            created_at=merged_orm.created_at,
        )

    async def get(self, draft_id: UUID) -> Optional[Draft]:
        result = await self.session.execute(select(DraftORM).where(DraftORM.id == draft_id))
        draft_orm = result.scalar_one_or_none()
        if not draft_orm:
            return None
        return Draft(
            id=draft_orm.id,
            project_id=draft_orm.project_id,
            version_number=draft_orm.version_number,
            prompt_text=draft_orm.prompt_text,
            model_configuration=draft_orm.model_configuration,
            author_id=draft_orm.author_id,
            created_at=draft_orm.created_at,
        )

    async def list_by_project(self, project_id: UUID) -> List[Draft]:
        result = await self.session.execute(
            select(DraftORM).where(DraftORM.project_id == project_id).order_by(DraftORM.version_number.asc())
        )
        drafts_orm = result.scalars().all()
        return [
            Draft(
                id=d.id,
                project_id=d.project_id,
                version_number=d.version_number,
                prompt_text=d.prompt_text,
                model_configuration=d.model_configuration,
                author_id=d.author_id,
                created_at=d.created_at,
            )
            for d in drafts_orm
        ]

    async def get_latest_version(self, project_id: UUID) -> Optional[int]:
        result = await self.session.execute(
            select(DraftORM.version_number)
            .where(DraftORM.project_id == project_id)
            .order_by(desc(DraftORM.version_number))
            .limit(1)
        )
        version: Optional[int] = result.scalar_one_or_none()
        return version
