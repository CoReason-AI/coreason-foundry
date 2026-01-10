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

from pydantic import BaseModel, Field


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

    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    version_number: int
    prompt_text: str
    model_configuration: Dict[str, Any] = Field(description="Configuration parameters for the model")
    author_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
