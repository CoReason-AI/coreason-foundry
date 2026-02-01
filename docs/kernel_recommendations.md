# Recommendations for coreason-manifest Evolution

To fully support the `coreason-foundry` use case (Atomic Agents with Inline Definitions) without data loss, we recommend the following enhancements to the `coreason-manifest` schema.

## 1. Support for System Prompts

**Current State:**
The `AgentRuntimeConfig` is purely graph-based. There is no standard field for a global "System Prompt" or "Persona". Currently, `foundry` must drop this data or hide it inside a specific Node's implementation details, which makes it opaque to the manifest validator.

**Recommendation:**
Add an optional `system_prompt` field to `ModelConfig` or `AgentRuntimeConfig`. This allows the "Persona" of the agent to be defined at the top level, applicable to all LLM calls in the session unless overridden.

**Proposed Change (`definitions/agent.py`):**

```python
class ModelConfig(BaseModel):
    model: str
    temperature: float
    # ADD THIS:
    system_prompt: Optional[str] = Field(None, description="The default system prompt/persona for the agent.")
```

---

## 2. Support for Inline Tool Definitions

**Current State:**
`AgentDependencies.tools` expects a list of `ToolRequirement` objects.
`ToolRequirement` strictly mandates a `uri` (remote endpoint) and `hash` (integrity check).

```python
class ToolRequirement(BaseModel):
    uri: StrictUri  # <--- Requires a deployed URL
    hash: str       # <--- Requires a calculated hash
    ...
```

**The Problem:**
In `foundry`, users define tools *inline* (Name, Description, JSON Schema parameters) as part of the Draft. These tools often do not exist at a URI yet; they are part of the agent's definition itself. Requiring a URI forces a "Deployment" step before a "Manifest" can even be created, which breaks the drafting workflow.

**Recommendation:**
Expand `AgentDependencies` to allow *Inline Tool Definitions* alongside *Remote Tool Requirements*.

**Proposed Change (`definitions/agent.py`):**

1.  **Define `InlineToolDefinition`:**

    ```python
    class InlineToolDefinition(BaseModel):
        name: str
        description: str
        parameters: Dict[str, Any]  # JSON Schema
        type: Literal["function"] = "function"
    ```

2.  **Update `ToolRequirement` or `AgentDependencies`:**

    Allowed `tools` to be a Union of `ToolRequirement` (Remote) and `InlineToolDefinition` (Embedded).

    ```python
    # In AgentDependencies
    tools: List[Union[ToolRequirement, InlineToolDefinition]] = ...
    ```

## Summary of Benefits

Implementing these changes in `coreason-manifest` v0.10.0+ will allow `coreason-foundry` to:
1.  **Preserve Data:** Stop dropping `prompt_text` and `tools` during conversion.
2.  **Simplify Logic:** Remove the need for "Skeleton Topologies" just to satisfy the schema.
3.  **Enable Portability:** Create self-contained Agent Manifests that include their tool definitions, making them easier to share and execute without external dependencies.
