# The Architecture and Utility of coreason-foundry

### 1. The Philosophy (The Why)

In the highly regulated world of GxP (Good Practice) software development—such as in the pharmaceutical or clinical domains—there exists a fundamental tension between **innovation** and **compliance**. Modern engineering teams demand "Google Docs-style" real-time collaboration to iterate quickly on agent prompts and topologies. However, regulatory bodies (like the FDA via 21 CFR Part 11) demand rigorous attribution: every character change must be traceable to a specific human identity, preventing the ambiguity of simultaneous multi-user edits.

**coreason-foundry** was built to resolve this paradox. It serves as the "Collaborative Workspace Manager" for the Agent Development Life Cycle (ADLC). Its philosophy is to bifurcate the development state into two distinct phases:

1.  **The Liquid State (Social Awareness):** Using WebSockets and ephemeral stores, the system provides immediate feedback on *who* is present and *what* is happening (e.g., streaming test logs), fostering a sense of shared presence.
2.  **The Solid State (GxP Attribution):** Actual modifications to the agent's logic (prompts, config) are governed by strict **Pessimistic Locking**. Only one user can hold the "write token" for a specific field at a time.

This architecture ensures that while communication is synchronous and fluid, the "commit history" remains linear, attributable, and audit-ready.

### 2. Under the Hood (The Dependencies & logic)

The package relies on a high-performance, asynchronous Python stack designed to handle both the real-time event loop and the transactional integrity required for audit trails.

*   **FastAPI & Uvicorn:** Provide the asynchronous backbone for handling high-concurrency WebSocket connections (for presence and log streaming) alongside standard HTTP CRUD operations.
*   **SQLAlchemy & asyncpg:** Manage the persistent "Solid State." The choice of `asyncpg` implies a need for high-throughput database interactions with PostgreSQL, essential when every "Save" is a full versioned commit.
*   **Redis:** Handles the "Liquid State." It serves as the high-speed registry for **Distributed Locks** (`RedisLockRegistry`) and **User Presence** (`RedisPresenceRegistry`), ensuring that locking operations are atomic and instant, which is critical for a smooth user experience.
*   **Pydantic:** Enforces strict schema validation at the edges, ensuring that complex agent configurations are structurally sound before they ever reach the database.

Internally, the logic is organized around specialized Managers:
*   **`ProjectManager`:** Acts as the container service, grouping assets into coherent workspaces.
*   **`DraftManager`:** Implements the "Micro-Commit" strategy. It utilizes a `UnitOfWork` pattern to ensure that creating a draft and updating the project pointer happen atomically. It also provides differential analysis (`compare_versions`) to visualize the evolution of an agent's reasoning.
*   **`RedisLockRegistry`:** The safety valve. It uses Redis's atomic `SET NX` (Set if Not Exists) to enforce the pessimistic locking protocol, rejecting conflicting edit attempts instantly.

### 3. In Practice (The How)

The following examples demonstrate the "Happy Path" of the Collaborative GxP Control Loop: creating a workspace, securing a lock to edit safely, and committing a new immutable version.

#### Creating a Workspace
The entry point for any initiative is the `ProjectManager`. It initializes the container that will hold all subsequent versions.

```python
import asyncio
from coreason_foundry.managers import ProjectManager
# Assumes repository is injected via dependency injection
from coreason_foundry.repositories import SqlAlchemyProjectRepository

async def initialize_workspace(repo: SqlAlchemyProjectRepository):
    manager = ProjectManager(repository=repo)

    # Create a container for the Oncology Agent
    project = await manager.create_project(name="Oncology Clinical Protocol Agent")
    print(f"Workspace initialized: {project.id}")
    return project
```

#### The "Safety Check" (Acquiring a Lock)
Before a user can type a single character, the frontend must request a lock. This ensures no other user is currently modifying the same field.

```python
from uuid import uuid4
from coreason_foundry.locking import RedisLockRegistry
# Assumes redis_client is an initialized redis.asyncio.Redis instance

async def start_editing(redis_client, project_id, user_id):
    registry = RedisLockRegistry(redis_client)
    target_field = "system_prompt"

    # Attempt to acquire the lock for the System Prompt
    is_locked = await registry.acquire(
        project_id=project_id,
        field=target_field,
        user_id=user_id,
        ttl_seconds=60
    )

    if is_locked:
        print(f"User {user_id} has exclusive control over {target_field}.")
    else:
        print(f"Access Denied: {target_field} is currently being edited by another user.")
```

#### The "Commit" (Saving a Draft)
Once editing is complete, the `DraftManager` persists the state as a new, immutable version. Note the use of `UnitOfWork` to guarantee data integrity.

```python
from coreason_foundry.managers import DraftManager

async def save_new_version(uow, project_id, author_id):
    manager = DraftManager(uow=uow)

    # The new prompt text crafted by the user
    new_prompt = """
    You are an expert oncologist.
    Analyze the provided patient data against the protocol inclusion criteria.
    """

    # Save creates a new version (e.g., v1 -> v2)
    draft = await manager.create_draft(
        project_id=project_id,
        prompt_text=new_prompt,
        model_configuration={"temperature": 0.2, "model": "gpt-4"},
        author_id=author_id,
        scratchpad="Adjusted tone to be more clinical."
    )

    print(f"Draft saved successfully: Version {draft.version_number} (ID: {draft.id})")
```
