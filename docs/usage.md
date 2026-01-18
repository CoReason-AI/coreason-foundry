# Usage Guide

This guide provides instructions and examples for using the `coreason-foundry` package.

## Installation

Ensure you have Python 3.12+ and Poetry installed.

```bash
git clone https://github.com/CoReason-AI/coreason_foundry.git
cd coreason_foundry
poetry install
```

## Quick Start (In-Memory)

For testing or rapid prototyping, you can use the In-Memory implementations which do not require a running database or Redis instance.

```python
import asyncio
from uuid import uuid4
from coreason_foundry.managers import ProjectManager, DraftManager
from coreason_foundry.memory import InMemoryUnitOfWork

async def main():
    # 1. Initialize the Unit of Work (which holds the repositories)
    uow = InMemoryUnitOfWork()

    # 2. Initialize Managers
    project_manager = ProjectManager(uow.projects)
    draft_manager = DraftManager(uow)

    # 3. Create a Project
    project = await project_manager.create_project(name="Oncology Agent")
    print(f"Created Project: {project.name} (ID: {project.id})")

    # 4. Create a Draft
    author_id = uuid4()
    draft = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="You are a helpful assistant.",
        model_configuration={"model": "gpt-4", "temperature": 0.7},
        author_id=author_id,
        scratchpad="Initial draft"
    )
    print(f"Created Draft v{draft.version_number} (ID: {draft.id})")

    # 5. Create a Second Draft (Simulation of iteration)
    draft_v2 = await draft_manager.create_draft(
        project_id=project.id,
        prompt_text="You are a helpful medical assistant specialized in oncology.",
        model_configuration={"model": "gpt-4", "temperature": 0.5},
        author_id=author_id,
        scratchpad="Refining system prompt"
    )
    print(f"Created Draft v{draft_v2.version_number}")

    # 6. Compare Versions
    diff = await draft_manager.compare_versions(draft.id, draft_v2.id)
    print("\n--- Diff ---")
    print(diff)

if __name__ == "__main__":
    asyncio.run(main())
```

## Production Setup

In a production environment, `coreason-foundry` expects a persistent SQL database (via SQLAlchemy) and Redis (for locking).

### Database Configuration

You need to provide an `AsyncSession` to the repositories.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 1. Setup SQLAlchemy Engine
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 2. Usage in an API Endpoint (Dependency Injection style)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Using Managers with SQLAlchemy

```python
from coreason_foundry.repositories import SqlAlchemyUnitOfWork
from coreason_foundry.managers import ProjectManager, DraftManager

async def create_agent_workflow(session):
    uow = SqlAlchemyUnitOfWork(session)
    project_manager = ProjectManager(uow.projects)
    draft_manager = DraftManager(uow)

    # ... use managers as shown in Quick Start ...
```

## Distributed Locking (Redis)

To enforce the GxP requirement that "Every character change must be attributable to exactly one user session", we use field-level locking backed by Redis.

```python
import redis.asyncio as redis
from uuid import uuid4
from coreason_foundry.locking import RedisLockRegistry

async def locking_example():
    # 1. Connect to Redis
    redis_client = redis.from_url("redis://localhost")
    lock_registry = RedisLockRegistry(redis_client)

    project_id = uuid4()
    user_a = uuid4()
    user_b = uuid4()
    field = "system_prompt"

    # 2. User A acquires lock
    acquired = await lock_registry.acquire(project_id, field, user_a)
    if acquired:
        print(f"User A acquired lock on {field}")

    # 3. User B tries to acquire lock (Should fail)
    acquired_b = await lock_registry.acquire(project_id, field, user_b)
    if not acquired_b:
        print(f"User B denied lock on {field} (Owned by User A)")

    # 4. Check owner
    owner = await lock_registry.get_lock_owner(project_id, field)
    print(f"Current owner: {owner}")

    # 5. User A releases lock
    await lock_registry.release(project_id, field, user_a)
    print("User A released lock")
```
