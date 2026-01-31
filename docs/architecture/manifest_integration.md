# Coreason Manifest Integration

## Overview

This document details the integration of `coreason-foundry` with `coreason-manifest` (the Shared Kernel). This integration is a critical architectural step to ensure that the agents designed in Foundry ("Atomic Agents") are mathematically identical to the definitions expected by the Runtime (`coreason-maco`).

## Motivation: Eliminating Drift

In distributed systems where design and execution are separated, "Drift" occurs when the design tool's representation of an artifact diverges from the runtime's expectation.

*   **Foundry (Design Time):** Manages mutable *Drafts*. Users iterate on prompts, add tools, and tweak configurations.
*   **Kernel (Contract):** `coreason-manifest` defines the strict, immutable schema for an Agent.
*   **Runtime (Execution):** `coreason-maco` executes Agents based strictly on the Kernel schema.

By making Foundry depend on `coreason-manifest` data structures (specifically `AgentDefinition`, `ToolDefinition` via URIs, etc.), we ensure that a published Draft is guaranteed to be valid for execution.

## The Data Model

### Draft (Foundry)

The `Draft` model in Foundry represents a versioned, immutable snapshot of an agent's design state. It is "mutable" in the sense that users create *new* drafts to change state, but each draft instance is frozen.

Attributes:
*   `prompt_text`: The system prompt (Natural Language).
*   `tools`: A list of strict URIs pointing to MCP capabilities (e.g., `https://example.com/tools/weather`).
*   `model_configuration`: A loose dictionary of parameters.

### AgentDefinition (Kernel)

The `AgentDefinition` is the strict contract.

*   `metadata`: Identity, version, author.
*   `topology`: The execution graph. Currently, Foundry maps the `prompt_text` to a single-step execution graph.
*   `dependencies`: Lists external requirements (Tools).
*   `interface`: Inputs/Outputs (currently empty/default for generic agents).

## Conversion Logic (`to_manifest`)

The `Draft.to_manifest()` method performs the translation:

1.  **Topology Mapping:**
    *   `Draft.prompt_text` -> `AgentTopology.steps[0].description`.
    *   `Draft.model_configuration["model"]` -> `ModelConfig.model`.
    *   `Draft.model_configuration["temperature"]` -> `ModelConfig.temperature`.

2.  **Dependency Mapping:**
    *   `Draft.tools` (List[StrictUri]) -> `AgentDependencies.tools`.

3.  **Metadata Mapping:**
    *   `Draft.id` -> `AgentMetadata.id`.
    *   `Draft.author_id` -> `AgentMetadata.author`.
    *   `Draft.version_number` -> `AgentMetadata.version` (formatted as `0.0.{version}`).

## Persistence

To support this integration, the Foundry database schema (`drafts` table) now includes a `tools` column (JSON type) to persist the list of tool URIs. The Repository layer handles the serialization/deserialization between the Domain `List[StrictUri]` and the Persistence `List[str]`.
