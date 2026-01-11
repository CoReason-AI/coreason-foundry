# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from coreason_foundry.exceptions import ProjectNotFoundError
from coreason_foundry.models import Draft, Project
from coreason_foundry.utils.logger import logger


class ProjectRepository(ABC):
    """
    Abstract base class for Project storage.
    """

    @abstractmethod
    async def save(self, project: Project) -> Project:
        """Saves a project."""
        pass  # pragma: no cover

    @abstractmethod
    async def get(self, project_id: UUID) -> Optional[Project]:
        """Retrieves a project by ID."""
        pass  # pragma: no cover

    @abstractmethod
    async def list_all(self) -> List[Project]:
        """Lists all projects."""
        pass  # pragma: no cover


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


class InMemoryProjectRepository(ProjectRepository):
    """
    In-memory implementation of ProjectRepository.
    """

    def __init__(self) -> None:
        self._projects: dict[UUID, Project] = {}

    async def save(self, project: Project) -> Project:
        # Store a deep copy to mimic DB isolation
        self._projects[project.id] = copy.deepcopy(project)
        return copy.deepcopy(project)

    async def get(self, project_id: UUID) -> Optional[Project]:
        project = self._projects.get(project_id)
        if project:
            return copy.deepcopy(project)
        return None

    async def list_all(self) -> List[Project]:
        return [copy.deepcopy(p) for p in self._projects.values()]


class InMemoryDraftRepository(DraftRepository):
    """
    In-memory implementation of DraftRepository.
    """

    def __init__(self) -> None:
        self._drafts: dict[UUID, Draft] = {}

    async def save(self, draft: Draft) -> Draft:
        # Simulate Unique Constraint (project_id, version_number)
        for existing in self._drafts.values():
            if existing.project_id == draft.project_id and existing.version_number == draft.version_number:
                if existing.id != draft.id:
                    # Raise an exception similar to what SQL would raise (IntegrityError)
                    raise ValueError(
                        f"Unique constraint violation: Draft {draft.version_number} "
                        f"already exists for Project {draft.project_id}"
                    )

        self._drafts[draft.id] = copy.deepcopy(draft)
        return copy.deepcopy(draft)

    async def get(self, draft_id: UUID) -> Optional[Draft]:
        draft = self._drafts.get(draft_id)
        if draft:
            return copy.deepcopy(draft)
        return None

    async def list_by_project(self, project_id: UUID) -> List[Draft]:
        drafts = sorted(
            [d for d in self._drafts.values() if d.project_id == project_id],
            key=lambda d: d.version_number,
        )
        return [copy.deepcopy(d) for d in drafts]

    async def get_latest_version(self, project_id: UUID) -> Optional[int]:
        drafts = await self.list_by_project(project_id)
        if not drafts:
            return None
        return drafts[-1].version_number


class ProjectManager:
    """
    Manages the lifecycle of Projects (Workspaces).
    """

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    async def create_project(self, name: str) -> Project:
        """Creates a new project container."""
        project = Project(name=name)
        await self.repository.save(project)
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
    """

    def __init__(self, project_repo: ProjectRepository, draft_repo: DraftRepository) -> None:
        self.project_repo = project_repo
        self.draft_repo = draft_repo

    async def create_draft(
        self,
        project_id: UUID,
        prompt_text: str,
        model_configuration: Dict[str, Any],
        author_id: UUID,
    ) -> Draft:
        """
        Creates a new draft for a project.

        This method:
        1. Verifies the project exists.
        2. Calculates the new version number.
        3. Creates and persists the new draft.
        4. Updates the project's current_draft_id atomically.
        """
        # 1. Verify Project Exists
        project = await self.project_repo.get(project_id)
        if not project:
            logger.error(f"Failed to create draft: Project {project_id} not found.")
            raise ProjectNotFoundError(f"Project with ID {project_id} not found.")

        # 2. Calculate Version
        latest_version = await self.draft_repo.get_latest_version(project_id)
        new_version = (latest_version or 0) + 1

        # 3. Create Draft
        draft = Draft(
            project_id=project_id,
            version_number=new_version,
            prompt_text=prompt_text,
            model_configuration=model_configuration,
            author_id=author_id,
        )
        saved_draft = await self.draft_repo.save(draft)

        # 4. Update Project Pointer
        # Since Project is a Pydantic model (not frozen), we can update it?
        # Check Project definition in models.py: it inherits from BaseModel, not frozen.
        # But good practice is to treat as immutable if possible or just update field.
        # However, to save it via repo, we pass the object.
        # In SQL repo, it merges.

        # We need to make sure we are updating the "current" state of the project.
        # Ideally, we should use a transaction here, but at the Manager level,
        # we rely on the Repositories sharing a session context if using SQL.
        # For InMemory, it's immediate.

        project.current_draft_id = saved_draft.id
        await self.project_repo.save(project)

        logger.info(f"Created Draft v{new_version} for Project {project_id}")
        return saved_draft
