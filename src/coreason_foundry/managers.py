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

from coreason_foundry.models import Project
from coreason_foundry.utils.logger import logger


class ProjectRepository(ABC):
    """
    Abstract base class for Project storage.
    """

    @abstractmethod
    def save(self, project: Project) -> Project:
        """Saves a project."""
        pass  # pragma: no cover

    @abstractmethod
    def get(self, project_id: UUID) -> Optional[Project]:
        """Retrieves a project by ID."""
        pass  # pragma: no cover

    @abstractmethod
    def list_all(self) -> List[Project]:
        """Lists all projects."""
        pass  # pragma: no cover


class InMemoryProjectRepository(ProjectRepository):
    """
    In-memory implementation of ProjectRepository.
    """

    def __init__(self) -> None:
        self._projects: dict[UUID, Project] = {}

    def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    def get(self, project_id: UUID) -> Optional[Project]:
        return self._projects.get(project_id)

    def list_all(self) -> List[Project]:
        return list(self._projects.values())


class ProjectManager:
    """
    Manages the lifecycle of Projects (Workspaces).
    """

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def create_project(self, name: str) -> Project:
        """Creates a new project container."""
        project = Project(name=name)
        self.repository.save(project)
        logger.info(f"Created project: {project.name} ({project.id})")
        return project

    def get_project(self, project_id: UUID) -> Optional[Project]:
        """Retrieves a project by ID."""
        return self.repository.get(project_id)

    def list_projects(self) -> List[Project]:
        """Lists all available projects."""
        return self.repository.list_all()
