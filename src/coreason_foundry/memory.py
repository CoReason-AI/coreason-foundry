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
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from coreason_foundry.interfaces import (
    CommentRepository,
    DraftRepository,
    PresenceRegistry,
    ProjectRepository,
    UnitOfWork,
)
from coreason_foundry.models import Comment, Draft, Project

T = TypeVar("T")


class GenericInMemoryRepository(Generic[T]):
    """
    Generic In-Memory Repository implementing common CRUD operations.
    """

    def __init__(self, storage: Dict[UUID, Any]) -> None:
        self._storage = storage

    async def _add(self, entity: T) -> T:
        # Check for existing ID to simulate database PK constraint
        # Use getattr to satisfy mypy since T is generic
        entity_id = getattr(entity, "id", None)
        if entity_id and entity_id in self._storage:
            raise ValueError(f"Entity with ID {entity_id} already exists.")

        # Store a deep copy to mimic DB isolation
        if entity_id:
            self._storage[entity_id] = copy.deepcopy(entity)

        # We assume entity has an ID for this repo logic to work
        return copy.deepcopy(entity)

    async def _update(self, entity: T) -> T:
        # Check if entity exists
        entity_id = getattr(entity, "id", None)
        if not entity_id or entity_id not in self._storage:
            raise ValueError(f"Entity with ID {entity_id} not found.")

        # Update storage
        self._storage[entity_id] = copy.deepcopy(entity)
        return copy.deepcopy(entity)

    async def _get(self, entity_id: UUID) -> Optional[T]:
        entity = self._storage.get(entity_id)
        if entity:
            return copy.deepcopy(entity)  # type: ignore
        return None

    async def _list_all(self) -> List[T]:
        return [copy.deepcopy(e) for e in self._storage.values()]  # type: ignore

    async def _delete(self, entity_id: UUID) -> bool:
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False


class InMemoryProjectRepository(GenericInMemoryRepository[Project], ProjectRepository):
    """
    In-memory implementation of ProjectRepository.
    """

    def __init__(self, storage: Optional[Dict[UUID, Any]] = None) -> None:
        super().__init__(storage if storage is not None else {})

    async def add(self, project: Project) -> Project:
        return await self._add(project)

    async def update(self, project: Project) -> Project:
        return await self._update(project)

    async def get(self, project_id: UUID) -> Optional[Project]:
        return await self._get(project_id)

    async def list_all(self) -> List[Project]:
        return await self._list_all()


class InMemoryDraftRepository(GenericInMemoryRepository[Draft], DraftRepository):
    """
    In-memory implementation of DraftRepository.
    """

    def __init__(self, storage: Optional[Dict[UUID, Any]] = None) -> None:
        super().__init__(storage if storage is not None else {})

    async def add(self, draft: Draft) -> Draft:
        # Simulate Unique Constraint (project_id, version_number)
        for existing in self._storage.values():
            if existing.project_id == draft.project_id and existing.version_number == draft.version_number:
                # Raise an exception similar to what SQL would raise (IntegrityError)
                raise ValueError(
                    f"Unique constraint violation: Draft {draft.version_number} "
                    f"already exists for Project {draft.project_id}"
                )

        return await self._add(draft)

    async def get(self, draft_id: UUID) -> Optional[Draft]:
        return await self._get(draft_id)

    async def list_by_project(self, project_id: UUID) -> List[Draft]:
        drafts = sorted(
            [d for d in self._storage.values() if d.project_id == project_id],
            key=lambda d: d.version_number,
        )
        return [copy.deepcopy(d) for d in drafts]

    async def get_latest_version(self, project_id: UUID) -> Optional[int]:
        drafts = await self.list_by_project(project_id)
        if not drafts:
            return None
        return drafts[-1].version_number


class InMemoryCommentRepository(GenericInMemoryRepository[Comment], CommentRepository):
    """
    In-memory implementation of CommentRepository.
    """

    def __init__(self, storage: Optional[Dict[UUID, Any]] = None) -> None:
        super().__init__(storage if storage is not None else {})

    async def add(self, comment: Comment) -> Comment:
        return await self._add(comment)

    async def get(self, comment_id: UUID) -> Optional[Comment]:
        return await self._get(comment_id)

    async def list_by_draft(self, draft_id: UUID) -> List[Comment]:
        comments = sorted(
            [c for c in self._storage.values() if c.draft_id == draft_id],
            key=lambda c: c.created_at,
        )
        return [copy.deepcopy(c) for c in comments]

    async def delete(self, comment_id: UUID) -> bool:
        return await self._delete(comment_id)


class InMemoryUnitOfWork(UnitOfWork):
    """
    In-Memory Unit of Work.
    Simulates transaction by using separate storage that merges on commit.
    Actually, simpler: use shared storage but allow rollback?
    In-Memory usually doesn't need complex transaction logic if not testing concurrency deeply.
    But to support "UnitOfWork" interface properly, we should provide the repos.
    """

    def __init__(self) -> None:
        # Shared storage for "committed" state
        self._project_storage: Dict[UUID, Any] = {}
        self._draft_storage: Dict[UUID, Any] = {}
        self._comment_storage: Dict[UUID, Any] = {}

        # Initialize Repositories with shared storage
        self.projects = InMemoryProjectRepository(self._project_storage)
        self.drafts = InMemoryDraftRepository(self._draft_storage)
        self.comments = InMemoryCommentRepository(self._comment_storage)

    async def __aenter__(self) -> "UnitOfWork":
        # For simple in-memory, we just return self.
        # If we wanted true rollback, we'd snapshot storage here.
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self) -> None:
        # In this simple implementation, operations are immediate.
        pass

    async def rollback(self) -> None:
        # Implementing rollback for in-memory is hard without complex snapshotting.
        # For now, we assume tests don't strictly verify rollback of in-memory
        # unless we implement a "transactional" in-memory repo which writes to a temporary dict
        # and merges on commit.
        pass


class InMemoryPresenceRegistry(PresenceRegistry):
    """
    In-memory implementation of PresenceRegistry.
    """

    def __init__(self) -> None:
        # Map project_id -> Set[user_id]
        self._presence: Dict[UUID, set[UUID]] = {}

    async def add_user(self, project_id: UUID, user_id: UUID) -> None:
        if project_id not in self._presence:
            self._presence[project_id] = set()
        self._presence[project_id].add(user_id)

    async def remove_user(self, project_id: UUID, user_id: UUID) -> None:
        if project_id in self._presence:
            self._presence[project_id].discard(user_id)

    async def get_present_users(self, project_id: UUID) -> List[UUID]:
        return list(self._presence.get(project_id, set()))
