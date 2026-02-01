# Coreason Manifest Integration Guide

This document details the integration between `coreason-foundry` (The Workspace Manager) and `coreason-manifest` (The Shared Kernel).

## Overview

`coreason-foundry` is responsible for managing the lifecycle of Agent development (Projects, Drafts, Collaboration). When an Agent is ready to be deployed or exported, it must be converted into a standard, portable artifact.

`coreason-manifest` provides the strict schemas and validation logic for this artifact, known as the **Agent Manifest**.

## Key Classes & Structures

The integration relies on importing specific definitions from the `coreason-manifest` library (v0.9.0+).

### 1. `AgentDefinition`
**Import:** `coreason_manifest.definitions.agent.AgentDefinition`

The root object of the manifest. It is a strictly typed Pydantic model that acts as the "Source of Truth" for an Agent.
*   **Role:** The final output of the `Draft.to_manifest()` method.
*   **Key Fields:**
    *   `metadata`: Identity info (Name, Version, ID).
    *   `config`: The runtime execution graph.
    *   `interface`: Inputs/Outputs contract.
    *   `integrity_hash`: A SHA256 hash ensuring the artifact hasn't been tampered with.

### 2. `AgentRuntimeConfig`
**Import:** `coreason_manifest.definitions.agent.AgentRuntimeConfig`

Defines *how* the agent executes.
*   **Structure:** It is **Graph-based** (Nodes & Edges).
*   **Mismatch Note:** Foundry's `Draft` model is currently "Atomic" (System Prompt + Model Config). The Kernel's v0.9.0 schema is "Graph" (Nodes + Edges).
*   **Mapping Strategy:** We map the atomic draft to a **Skeleton Topology** containing a single `LogicNode` to satisfy the strict schema requirements.

### 3. `AgentMetadata`
**Import:** `coreason_manifest.definitions.agent.AgentMetadata`

Contains versioning and authorship details.
*   **Foundry Mapping:**
    *   `name` <- `Project.name`
    *   `version` <- `0.0.{Draft.version_number}`
    *   `author` <- `Draft.author_id`

## The "Skeleton Topology" Mapping

Because `coreason-manifest` v0.9.0 enforces a graph structure (Nodes/Edges) and lacks fields for a top-level "System Prompt" or inline "Tools", Foundry uses the following mapping strategy to generate valid artifacts:

1.  **System Prompt:** *Currently Dropped*. (Pending Kernel schema update or proper storage in a Node).
2.  **Tools:** *Currently Dropped*. (Pending Kernel schema update to support inline definitions vs. strict URI/Hash requirements).
3.  **Topology:**
    *   Creates a single `LogicNode` with ID `main`.
    *   Sets `entry_point` to `main`.
    *   Sets `code` to a dummy pass.

This ensures that `coreason-foundry` produces `AgentDefinition` objects that:
1.  Pass strict Pydantic validation.
2.  Can be hashed consistently.
3.  Can be ingested by other systems expecting valid Manifests (even if functionally empty until the schema matures).

## Integrity Hashing

**File:** `src/coreason_foundry/utils/hashing.py`

Every generated `AgentDefinition` includes an `integrity_hash`.
*   **Algorithm:** SHA256.
*   **Normalization:** Canonical JSON (sorted keys, no whitespace).
*   **Scope:** Hashes the `metadata`, `interface`, `config`, and `dependencies` dictionaries before the final object is assembled.
