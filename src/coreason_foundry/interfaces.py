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

from coreason_foundry.models import Comment, Draft, Project


class ProjectRepository(ABC):
    """
    Abstract base class for Project storage.
    """

    @abstractmethod
    async def add(self, project: Project) -> Project:
        """Adds a new project."""
        pass  # pragma: no cover

    @abstractmethod
    async def update(self, project: Project) -> Project:
        """Updates an existing project."""
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
    async def add(self, draft: Draft) -> Draft:
        """Adds a new draft."""
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


class CommentRepository(ABC):
    """
    Abstract base class for Comment storage.
    """

    @abstractmethod
    async def add(self, comment: Comment) -> Comment:
        """Adds a new comment."""
        pass  # pragma: no cover

    @abstractmethod
    async def get(self, comment_id: UUID) -> Optional[Comment]:
        """Retrieves a comment by ID."""
        pass  # pragma: no cover

    @abstractmethod
    async def list_by_draft(self, draft_id: UUID) -> List[Comment]:
        """Lists all comments for a draft."""
        pass  # pragma: no cover

    @abstractmethod
    async def delete(self, comment_id: UUID) -> bool:
        """Deletes a comment by ID. Returns True if deleted, False if not found."""
        pass  # pragma: no cover


class UnitOfWork(ABC):
    """
    Abstract base class for Unit of Work pattern.
    Manages transactions and repository access.
    """

    projects: ProjectRepository
    drafts: DraftRepository
    comments: CommentRepository

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        """Starts a transaction."""
        pass  # pragma: no cover

    @abstractmethod
    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Ends a transaction (commit or rollback)."""
        pass  # pragma: no cover

    @abstractmethod
    async def commit(self) -> None:
        """Commits the transaction."""
        pass  # pragma: no cover

    @abstractmethod
    async def rollback(self) -> None:
        """Rolls back the transaction."""
        pass  # pragma: no cover


class LockRegistry(ABC):
    """
    Abstract base class for Distributed Locking.
    """

    @abstractmethod
    async def acquire(self, project_id: UUID, field: str, user_id: UUID, ttl_seconds: int = 60) -> bool:
        """
        Acquires a lock on a specific field of a project.
        Returns True if successful, False if already locked by another user.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def release(self, project_id: UUID, field: str, user_id: UUID) -> bool:
        """
        Releases a lock if it is held by the specified user.
        Returns True if released, False if lock was not held by user.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def get_lock_owner(self, project_id: UUID, field: str) -> Optional[UUID]:
        """
        Returns the user_id of the current lock owner, or None if unlocked.
        """
        pass  # pragma: no cover


class PresenceRegistry(ABC):
    """
    Abstract base class for Real-Time Presence (who is online).
    """

    @abstractmethod
    async def add_user(self, project_id: UUID, user_id: UUID) -> None:
        """
        Marks a user as present in a project.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def remove_user(self, project_id: UUID, user_id: UUID) -> None:
        """
        Removes a user from the project's presence list.
        """
        pass  # pragma: no cover

    @abstractmethod
    async def get_present_users(self, project_id: UUID) -> List[UUID]:
        """
        Returns a list of user_ids currently present in the project.
        """
        pass  # pragma: no cover
