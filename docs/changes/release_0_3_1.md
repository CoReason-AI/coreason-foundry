# Delegated Identity and Row-Level Security (RLS)

## Summary
This release introduces mandatory **Delegated Identity** and **Row-Level Security (RLS)** to the `coreason-foundry` persistence layer. All core assets (`Project`, `Draft`) now require a strict `owner_id`, and access is gated by the authenticated user's identity.

## Key Changes

### 1. Dependencies
* Added `coreason-identity` for `UserContext` validation and management.
* Updated `anyio` to `^4.12.1` and development dependencies.

### 2. Database Schema
* Added `owner_id` (indexed string) column to `projects` and `drafts` tables.
* **Migration:** A new Alembic migration `40a8b9c7d6e5_add_ownership` is included.

### 3. Identity Injection
* API routes now enforce authentication via `HTTPBearer` token validation.
* A new dependency `get_user_context` hydrates a `UserContext` object from the request token.

### 4. Ownership Enforcement
* **ProjectManager & DraftManager:**
    * Creation methods automatically assign `owner_id` from the context.
    * Read/List methods strictly filter queries by `owner_id`.
    * Update operations verify ownership before execution, raising `AccessDeniedError` (403 Forbidden) on mismatch.
* **Repositories:**
    * Updated `get` and `list` interfaces to accept optional or mandatory `owner_id` filters.

## Breaking Changes
* All internal Manager and Repository APIs now require `owner_id` or `UserContext` where applicable.
* Tests have been updated to mock identity context.
