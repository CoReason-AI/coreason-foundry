# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from uuid import uuid4

from coreason_manifest.definitions.agent import AgentDefinition

from coreason_foundry.models import Draft


def test_draft_to_manifest_conversion() -> None:
    """
    Verifies that a Foundry Draft can be successfully converted to a Kernel AgentDefinition.
    """
    project_id = uuid4()
    author_id = uuid4()
    prompt = "You are a helpful assistant."
    tools = ["https://example.com/tools/weather"]
    config = {"model": "gpt-4-turbo", "temperature": 0.5}

    draft = Draft(
        project_id=project_id,
        version_number=1,
        prompt_text=prompt,
        model_configuration=config,
        tools=tools,
        author_id=author_id,
    )

    # Convert to Manifest
    agent_def = draft.to_manifest()

    # Verify Structure
    assert isinstance(agent_def, AgentDefinition)

    # Check Metadata
    assert str(agent_def.metadata.id) == str(draft.id)
    assert agent_def.metadata.version == "0.0.1"
    assert agent_def.metadata.author == str(author_id)

    # Check Topology (Prompt)
    assert len(agent_def.topology.steps) == 1
    assert agent_def.topology.steps[0].description == prompt
    # Using model_dump because field 'model_config' conflicts with Pydantic ConfigDict
    topology_dict = agent_def.topology.model_dump()
    # Field name is llm_config, but constructor alias is model_config
    assert topology_dict["llm_config"]["model"] == "gpt-4-turbo"
    assert topology_dict["llm_config"]["temperature"] == 0.5

    # Check Dependencies (Tools)
    assert len(agent_def.dependencies.tools) == 1
    assert str(agent_def.dependencies.tools[0]) == tools[0]
