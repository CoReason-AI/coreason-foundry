# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import difflib
from typing import Any, Dict, List, Optional
from uuid import UUID

from coreason_foundry.exceptions import ProjectNotFoundError
from coreason_foundry.interfaces import (
    ProjectRepository,
    UnitOfWork,
)
from coreason_foundry.models import Draft, Project
from coreason_foundry.utils.logger import logger


class ProjectManager:
    """
    Manages the lifecycle of Projects (Workspaces).
    """

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    async def create_project(self, name: str) -> Project:
        """Creates a new project container."""
        project = Project(name=name)
        await self.repository.add(project)
        logger.info(f"Created project: {project.name} ({project.id})")
        return project

    async def get_project(self, project_id: UUID) -> Optional[Project]:
        """Retrieves a project by ID."""
        return await self.repository.get(project_id)

    async def list_projects(self) -> List[Project]:
        """Lists all available projects."""
        return await self.repository.list_all()


class DraftManager:
    """
    Manages the lifecycle of Drafts.
    Uses UnitOfWork for transactional integrity.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        # expose repositories for read-only convenience if needed,
        # but operations should go through UoW if transactional.
        # However, for 'compare_versions' (read-only), we can use uow.drafts.
        # For backwards compatibility with tests that inspect .project_repo / .draft_repo:
        self.project_repo = uow.projects
        self.draft_repo = uow.drafts

    async def create_draft(
        self,
        project_id: UUID,
        prompt_text: str,
        model_configuration: Dict[str, Any],
        author_id: UUID,
        scratchpad: Optional[str] = None,
    ) -> Draft:
        """
        Creates a new draft for a project.

        This method:
        1. Verifies the project exists.
        2. Calculates the new version number.
        3. Creates and persists the new draft.
        4. Updates the project's current_draft_id atomically.
        """
        async with self.uow:
            # 1. Verify Project Exists
            project = await self.uow.projects.get(project_id)
            if not project:
                logger.error(f"Failed to create draft: Project {project_id} not found.")
                raise ProjectNotFoundError(f"Project with ID {project_id} not found.")

            # 2. Calculate Version
            latest_version = await self.uow.drafts.get_latest_version(project_id)
            new_version = (latest_version or 0) + 1

            # 3. Create Draft
            draft = Draft(
                project_id=project_id,
                version_number=new_version,
                prompt_text=prompt_text,
                model_configuration=model_configuration,
                scratchpad=scratchpad,
                author_id=author_id,
            )
            saved_draft = await self.uow.drafts.add(draft)

            # 4. Update Project Pointer
            project.current_draft_id = saved_draft.id
            await self.uow.projects.update(project)

            # Commit happens automatically on exit if no exception

        logger.info(f"Created Draft v{new_version} for Project {project_id}")
        return saved_draft

    async def compare_versions(self, draft_id_a: UUID, draft_id_b: UUID) -> str:
        """
        Compares two drafts and returns a unified diff of their prompt text.
        """
        # Read-only operation, no transaction strictly needed but harmless.
        draft_a = await self.uow.drafts.get(draft_id_a)
        draft_b = await self.uow.drafts.get(draft_id_b)

        if not draft_a:
            raise ValueError(f"Draft {draft_id_a} not found.")
        if not draft_b:
            raise ValueError(f"Draft {draft_id_b} not found.")

        if draft_a.project_id != draft_b.project_id:
            raise ValueError("Cannot compare drafts from different projects.")

        # difflib.unified_diff expects lists of strings
        diff = difflib.unified_diff(
            draft_a.prompt_text.splitlines(keepends=True),
            draft_b.prompt_text.splitlines(keepends=True),
            fromfile=f"Draft v{draft_a.version_number}",
            tofile=f"Draft v{draft_b.version_number}",
        )

        return "".join(diff)
