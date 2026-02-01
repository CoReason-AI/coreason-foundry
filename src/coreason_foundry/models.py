# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from coreason_manifest.definitions.agent import (
    AgentDefinition,
    AgentDependencies,
    AgentInterface,
    AgentMetadata,
    AgentRuntimeConfig,
    ModelConfig,
)
from coreason_manifest.definitions.topology import LogicNode
from pydantic import BaseModel, ConfigDict, Field, field_validator

from coreason_foundry.utils.hashing import compute_agent_hash


class Project(BaseModel):
    """
    Represents a workspace container for a specific agent initiative.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_draft_id: Optional[UUID] = None


class Draft(BaseModel):
    """
    Represents an immutable version of the agent's state.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    version_number: int
    prompt_text: str
    model_configuration: Dict[str, Any] = Field(description="Configuration parameters for the model")
    scratchpad: Optional[str] = None
    author_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("version_number")
    @classmethod
    def validate_version_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Version number must be positive")
        return v

    def to_manifest(self, project_name: str) -> AgentDefinition:
        """
        Converts the Draft into a strict AgentDefinition.

        Note: coreason-manifest v0.9.0 uses a Graph-based AgentRuntimeConfig and
        does not natively support a 'system_prompt' or inline 'tools' definition.
        This conversion produces a skeleton AgentDefinition with a dummy topology.
        The system prompt and tools are NOT currently preserved in the manifest
        due to schema limitations.
        """
        # 1. Prepare Version String
        version_str = f"0.0.{self.version_number}"

        # 2. Extract Model Config
        # Ensure model and temperature exist
        model = self.model_configuration.get("model", "gpt-4")
        temperature = self.model_configuration.get("temperature", 0.7)

        # Validate temperature
        if not isinstance(temperature, (int, float)) or not (0.0 <= temperature <= 2.0):
            temperature = 0.7

        llm_config = ModelConfig(model=str(model), temperature=float(temperature))

        # 3. Construct Metadata
        metadata = AgentMetadata(
            id=self.id,
            version=version_str,
            name=project_name,
            author=str(self.author_id),
            created_at=self.created_at,
            requires_auth=False,
        )

        # 4. Construct Interface (Empty/Default)
        interface = AgentInterface(inputs={}, outputs={}, injected_params=[])

        # 5. Construct Runtime Config (Skeleton Topology)
        # We create a single logic node to satisfy the graph requirement.
        dummy_node = LogicNode(
            id="main",
            code="pass",  # Dummy code
            type="logic",
        )

        runtime_config = AgentRuntimeConfig(nodes=[dummy_node], edges=[], entry_point="main", model_config=llm_config)

        # 6. Construct Dependencies (Empty)
        # Tools are not mapped because ToolRequirement requires URI/Hash,
        # but Draft only has definitions.
        dependencies = AgentDependencies(tools=[], libraries=())

        # 7. Prepare raw data for hashing
        # Matches the structure of the resulting AgentDefinition components
        raw_data = {
            "metadata": metadata.model_dump(mode="json"),
            "interface": interface.model_dump(mode="json"),
            "config": runtime_config.model_dump(mode="json"),
            "dependencies": dependencies.model_dump(mode="json"),
        }

        # 8. Calculate Hash
        integrity_hash = compute_agent_hash(raw_data)

        # 9. Return Strict Object
        return AgentDefinition(
            metadata=metadata,
            interface=interface,
            config=runtime_config,
            dependencies=dependencies,
            integrity_hash=integrity_hash,
        )


class Comment(BaseModel):
    """
    Represents a contextual comment on a specific draft.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    draft_id: UUID
    target_field: str
    text: str
    author_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Comment text cannot be empty")
        return v
