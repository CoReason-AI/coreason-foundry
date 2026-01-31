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
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from coreason_manifest.definitions.agent import (
    AgentDefinition,
    AgentDependencies,
    AgentInterface,
    AgentMetadata,
    AgentTopology,
    ModelConfig,
    Step,
    StrictUri,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    tools: List[StrictUri] = Field(default_factory=list, description="List of tool URIs")
    scratchpad: Optional[str] = None
    author_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("version_number")
    @classmethod
    def validate_version_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Version number must be positive")
        return v

    def to_manifest(self) -> AgentDefinition:
        """
        Converts the draft into a Kernel-compliant AgentDefinition.
        """
        return AgentDefinition(
            metadata=AgentMetadata(
                id=str(self.id),
                version=f"0.0.{self.version_number}",
                name="Draft Agent",
                author=str(self.author_id),
                created_at=self.created_at.isoformat(),
            ),
            interface=AgentInterface(inputs={}, outputs={}),
            topology=AgentTopology(
                steps=(Step(id="step-1", description=self.prompt_text),),
                model_config=ModelConfig(
                    model=str(self.model_configuration.get("model", "gpt-4")),
                    temperature=float(self.model_configuration.get("temperature", 0.7)),
                ),
            ),
            dependencies=AgentDependencies(
                tools=self.tools,
                libraries=[],
            ),
            integrity_hash="0" * 64,  # Placeholder hash
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
