# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from coreason_manifest.definitions.agent import StrictUri
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """
    Schema for creating a new project.
    """

    name: str = Field(..., min_length=1, description="The name of the project")


class DraftCreate(BaseModel):
    """
    Schema for creating a new draft (immutable version).
    """

    prompt_text: str = Field(..., description="The prompt text for the agent")
    model_configuration: Dict[str, Any] = Field(..., description="Configuration parameters for the model")
    tools: List[StrictUri] = Field(default_factory=list, description="List of tool URIs")
    scratchpad: Optional[str] = Field(None, description="Engineering notes or scratchpad content")


class DraftRead(BaseModel):
    """
    Schema for reading a draft.
    """

    id: UUID
    project_id: UUID
    version_number: int
    prompt_text: str
    model_configuration: Dict[str, Any]
    tools: List[StrictUri]
    scratchpad: Optional[str]
    author_id: UUID
    created_at: datetime


class DraftDiff(BaseModel):
    """
    Schema for draft comparison result.
    """

    diff: str


class OptimizationExample(BaseModel):
    """
    An input/output pair used for optimizing the prompt.
    """

    input_text: str = Field(..., description="The input to the agent")
    expected_output: str = Field(..., description="The expected output from the agent")


class OptimizationRequest(BaseModel):
    """
    Request payload for optimizing a draft's prompt.
    """

    examples: List[OptimizationExample] = Field(..., min_length=3, description="A list of golden examples (min 3)")
    iterations: int = Field(10, ge=1, description="Number of optimization iterations")
    metric_description: Optional[str] = Field(None, description="Description of the optimization metric")
