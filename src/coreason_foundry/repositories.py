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

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from coreason_foundry.db.models import CommentORM, DraftORM, ProjectORM
from coreason_foundry.managers import CommentRepository, DraftRepository, ProjectRepository
from coreason_foundry.models import Comment, Draft, Project


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
            scratchpad=draft.scratchpad,
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
            scratchpad=merged_orm.scratchpad,
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
            scratchpad=draft_orm.scratchpad,
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
                scratchpad=d.scratchpad,
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


class SqlAlchemyCommentRepository(CommentRepository):
    """
    SQLAlchemy implementation of CommentRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, comment: Comment) -> Comment:
        comment_orm = CommentORM(
            id=comment.id,
            draft_id=comment.draft_id,
            target_field=comment.target_field,
            text=comment.text,
            author_id=comment.author_id,
            created_at=comment.created_at,
        )
        merged_orm = await self.session.merge(comment_orm)
        await self.session.flush()

        return Comment(
            id=merged_orm.id,
            draft_id=merged_orm.draft_id,
            target_field=merged_orm.target_field,
            text=merged_orm.text,
            author_id=merged_orm.author_id,
            created_at=merged_orm.created_at,
        )

    async def get(self, comment_id: UUID) -> Optional[Comment]:
        result = await self.session.execute(select(CommentORM).where(CommentORM.id == comment_id))
        comment_orm = result.scalar_one_or_none()
        if not comment_orm:
            return None
        return Comment(
            id=comment_orm.id,
            draft_id=comment_orm.draft_id,
            target_field=comment_orm.target_field,
            text=comment_orm.text,
            author_id=comment_orm.author_id,
            created_at=comment_orm.created_at,
        )

    async def list_by_draft(self, draft_id: UUID) -> List[Comment]:
        result = await self.session.execute(
            select(CommentORM).where(CommentORM.draft_id == draft_id).order_by(CommentORM.created_at.asc())
        )
        comments_orm = result.scalars().all()
        return [
            Comment(
                id=c.id,
                draft_id=c.draft_id,
                target_field=c.target_field,
                text=c.text,
                author_id=c.author_id,
                created_at=c.created_at,
            )
            for c in comments_orm
        ]

    async def delete(self, comment_id: UUID) -> bool:
        result = await self.session.execute(delete(CommentORM).where(CommentORM.id == comment_id))
        await self.session.flush()
        return result.rowcount > 0  # type: ignore
