# Architecture

## Overview

**coreason-foundry** serves as the **Collaborative Workspace Manager & Real-Time State Engine** for the CoReason IDE. It is designed to bridge the gap between fleeting engineering thoughts and permanent GxP artifacts.

### The Collaborative GxP Control Loop

The architecture implements a specific control loop to satisfy regulatory requirements while enabling collaboration:

1.  **Draft-Iterate-Freeze**: The database acts as a staging area. No change is final until published.
2.  **Attribution > Convenience**: Simultaneous editing is rejected in favor of **Field-Level Locking** to ensure 21 CFR Part 11 compliance.
3.  **Real-Time Context**: Context (logs, presence) is shared instantly via WebSockets, even if editing is serialized.
4.  **Traceability**: Every draft version is immutable once saved, allowing for forensic auditing and undo/redo capabilities.

## Core Components

The system is built around several key components that map directly to the functional requirements.

### 1. The Project Manager (The Container)

*   **Class**: `coreason_foundry.managers.ProjectManager`
*   **Responsibility**: Groups related assets into a "Workspace" or "Project". It handles the lifecycle of the container itself, including creation and retrieval.
*   **Data Model**: `Project` (ID, Name, Created At, Current Draft ID).

### 2. The Draft Engine (The Editor)

*   **Class**: `coreason_foundry.managers.DraftManager`
*   **Responsibility**: Manages the mutable state of the agent development. It implements the "Micro-Commits" philosophy where every save creates a new version.
*   **Key Features**:
    *   **Versioning**: Every save creates a new `Draft` record.
    *   **Diffing**: Provides utilities (`compare_versions`) to visualize changes between any two draft versions.
    *   **Transactional Integrity**: Uses a `UnitOfWork` pattern to ensure that draft creation and project pointer updates happen atomically.

### 3. The Locking Protocol (The Traffic Light)

*   **Class**: `coreason_foundry.locking.RedisLockRegistry`
*   **Responsibility**: Enforces the pessimistic locking protocol to prevent simultaneous editing of the same field.
*   **Mechanism**:
    *   **Acquire**: Uses Redis `SET NX` (Set if Not Exists) with a TTL to acquire a lock on a specific field for a specific user.
    *   **Release**: Uses Lua scripts to safely release the lock only if the requesting user owns it.
    *   **Schema**: Locks are stored in Redis with keys like `lock:project:{id}:field:{name}` and values containing the owner's `user_id`.

## Data Schema (Conceptual)

### Persistent Storage (SQL)

*   **Project**: `id`, `name`, `created_at`, `current_draft_id`
*   **Draft**: `id`, `project_id`, `version_number`, `prompt_text`, `model_configuration` (JSON), `author_id`
*   **Comment**: `id`, `draft_id`, `target_field`, `text`, `author_id`

### Ephemeral Storage (Redis)

*   **LockRegistry**:
    *   Key: `lock:project:{id}:field:{name}`
    *   Value: `{ "user_id": "...", "expires_at": "..." }`
*   **PresenceRegistry**:
    *   Key: `presence:project:{id}`
    *   Value: `List[user_id]`
