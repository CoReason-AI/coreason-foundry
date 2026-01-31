# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from coreason_foundry.api.app import app
from coreason_foundry.api.dependencies import get_current_user_id, get_draft_manager
from coreason_foundry.api.schemas import OptimizationExample, OptimizationRequest
from coreason_foundry.managers import DraftManager
from coreason_foundry.memory import InMemoryUnitOfWork
from coreason_foundry.models import Project
from coreason_foundry.services.refinery import PromptRefinery
from fastapi.testclient import TestClient


@pytest.fixture
def mock_dspy() -> Any:
    with patch("coreason_foundry.services.refinery.dspy") as mock:
        # Mock context
        mock.context = MagicMock()
        mock.context.return_value.__enter__.return_value = None

        # Mock make_signature
        mock.make_signature = MagicMock(return_value="MockSignature")

        # Define a real class for Module to support inheritance and method execution in tests
        class MockModule:
            def __init__(self) -> None:
                pass

        mock.Module = MockModule

        # Mock Predict
        mock.Predict = MagicMock()

        # Mock Example
        mock.Example = MagicMock()

        yield mock


@pytest.fixture
def mock_copro() -> Any:
    with patch("coreason_foundry.services.refinery.COPRO") as mock:
        yield mock


def test_prompt_refinery_optimize(mock_dspy: Any, mock_copro: Any) -> None:
    # Setup
    refinery = PromptRefinery(llm_client="dummy")
    examples = [OptimizationExample(input_text="i", expected_output="o")]

    # Mock COPRO instance and compile
    copro_instance = mock_copro.return_value
    compiled_module = MagicMock()
    # Structure for extracting instruction: compiled_module.prog.signature.instructions
    compiled_module.prog.signature.instructions = "Optimized Prompt"
    copro_instance.compile.return_value = compiled_module

    # Execute
    result = refinery.optimize("Original Prompt", examples, iterations=5)

    # Verify
    assert result == "Optimized Prompt"
    mock_dspy.context.assert_called_with(lm="dummy")
    mock_copro.assert_called()
    copro_instance.compile.assert_called()


def test_prompt_refinery_optimize_failure(mock_dspy: Any, mock_copro: Any) -> None:
    # Setup
    refinery = PromptRefinery()
    examples = [OptimizationExample(input_text="i", expected_output="o")]

    # Mock COPRO failure
    mock_copro.side_effect = Exception("Optimization Error")

    # Execute
    result = refinery.optimize("Original Prompt", examples)

    # Verify fallback
    assert result == "Original Prompt"


def test_prompt_refinery_metric(mock_dspy: Any, mock_copro: Any) -> None:
    refinery = PromptRefinery()
    examples = [OptimizationExample(input_text="i", expected_output="o")]

    # We want to capture the metric function passed to COPRO
    refinery.optimize("p", examples)

    # Get the metric function
    # call_args is (args, kwargs)
    call_args = mock_copro.call_args
    metric_fn = call_args.kwargs["metric"]

    # Test the metric function
    # We compare .prediction attributes
    ex = MagicMock()
    ex.prediction = "foo"
    pred = MagicMock()
    pred.prediction = "foo"

    res = metric_fn(ex, pred)
    assert res is True

    pred.prediction = "bar"
    res = metric_fn(ex, pred)
    assert res is False


def test_prompt_refinery_agent_module(mock_dspy: Any, mock_copro: Any) -> None:
    refinery = PromptRefinery()
    examples = [OptimizationExample(input_text="i", expected_output="o")]

    # Mock COPRO
    copro_instance = mock_copro.return_value

    refinery.optimize("p", examples)

    # Get the module instance passed to compile
    if copro_instance.compile.called:
        args, _ = copro_instance.compile.call_args
        module_instance = args[0]

        # Test forward (covers line 58)
        # Setup mock for self.prog (dspy.Predict)
        # Note: self.prog is assigned in __init__ (lines 54-55), which ran when Module was created.
        # But since we mocked dspy.Predict, self.prog is a mock.
        module_instance.prog.return_value = "prediction"

        res = module_instance.forward("test_input")
        assert res == "prediction"
        module_instance.prog.assert_called_with(input_text="test_input")


@pytest.mark.asyncio
async def test_manager_optimize_draft(mock_dspy: Any, mock_copro: Any) -> None:
    # Setup
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow=uow, llm_client="dummy")

    project_id = uuid4()
    author_id = uuid4()

    # Create Project
    project = Project(name="Test Project")
    project.id = project_id
    await uow.projects.add(project)

    # Create Draft
    tools = ["https://example.com/tool"]
    draft = await manager.create_draft(project_id, "Original Prompt", {}, author_id, tools=tools, scratchpad="Old Note")

    # Mock Refinery behavior
    copro_instance = mock_copro.return_value
    compiled_module = MagicMock()
    compiled_module.prog.signature.instructions = "Optimized Prompt"
    copro_instance.compile.return_value = compiled_module

    # Execute
    req = OptimizationRequest(
        examples=[
            OptimizationExample(input_text="i", expected_output="o"),
            OptimizationExample(input_text="i2", expected_output="o2"),
            OptimizationExample(input_text="i3", expected_output="o3"),
        ],
        metric_description="Use brevity",
    )
    new_draft = await manager.optimize_draft(draft.id, req, author_id)

    # Verify
    assert new_draft.version_number == draft.version_number + 1
    assert new_draft.prompt_text == "Optimized Prompt"
    assert [str(t) for t in new_draft.tools] == tools
    assert new_draft.scratchpad is not None
    assert "Auto-optimized" in new_draft.scratchpad
    assert "Old Note" in new_draft.scratchpad
    assert "Metric: Use brevity" in new_draft.scratchpad
    assert new_draft.id != draft.id

    # Check project pointer updated
    updated_project = await uow.projects.get(project_id)
    assert updated_project
    assert updated_project.current_draft_id == new_draft.id


@pytest.mark.asyncio
async def test_manager_optimize_draft_not_found(mock_dspy: Any) -> None:
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow=uow)
    examples = [
        OptimizationExample(input_text="i1", expected_output="o1"),
        OptimizationExample(input_text="i2", expected_output="o2"),
        OptimizationExample(input_text="i3", expected_output="o3"),
    ]
    req = OptimizationRequest(examples=examples)

    with pytest.raises(ValueError, match="not found"):
        await manager.optimize_draft(uuid4(), req, uuid4())


@pytest.mark.asyncio
async def test_api_optimize_draft(mock_dspy: Any, mock_copro: Any) -> None:
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow=uow)
    app.dependency_overrides[get_draft_manager] = lambda: manager
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()

    project = Project(name="API Project")
    await uow.projects.add(project)

    draft = await manager.create_draft(project.id, "Original", {}, uuid4())

    # Mock COPRO
    copro_instance = mock_copro.return_value
    compiled_module = MagicMock()
    compiled_module.prog.signature.instructions = "API Optimized"
    copro_instance.compile.return_value = compiled_module

    client = TestClient(app)

    payload = {
        "examples": [
            {"input_text": "i", "expected_output": "o"},
            {"input_text": "i", "expected_output": "o"},
            {"input_text": "i", "expected_output": "o"},
        ],
        "metric_description": "API Test",
    }

    response = client.post(f"/drafts/{draft.id}/optimize", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["prompt_text"] == "API Optimized"
    assert "Metric: API Test" in data["scratchpad"]


def test_api_optimize_draft_not_found(mock_dspy: Any) -> None:
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow=uow)
    app.dependency_overrides[get_draft_manager] = lambda: manager
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()
    client = TestClient(app)

    payload = {"examples": [{"input_text": "i", "expected_output": "o"} for _ in range(3)]}

    response = client.post(f"/drafts/{uuid4()}/optimize", json=payload)
    assert response.status_code == 404


def test_api_optimize_draft_generic_error(mock_dspy: Any) -> None:
    # Simulate internal error
    manager = MagicMock()

    # Need to make optimize_draft async
    async def side_effect(*args: Any, **kwargs: Any) -> None:
        raise Exception("Internal Fail")

    manager.optimize_draft.side_effect = side_effect

    app.dependency_overrides[get_draft_manager] = lambda: manager
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()
    client = TestClient(app)

    payload = {"examples": [{"input_text": "i", "expected_output": "o"} for _ in range(3)]}

    response = client.post(f"/drafts/{uuid4()}/optimize", json=payload)
    assert response.status_code == 500


def test_api_optimize_draft_bad_request(mock_dspy: Any) -> None:
    manager = MagicMock()

    # Need to make optimize_draft async
    async def side_effect(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Some other error")

    manager.optimize_draft.side_effect = side_effect

    app.dependency_overrides[get_draft_manager] = lambda: manager
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()
    client = TestClient(app)

    payload = {"examples": [{"input_text": "i", "expected_output": "o"} for _ in range(3)]}

    response = client.post(f"/drafts/{uuid4()}/optimize", json=payload)
    assert response.status_code == 400


def test_api_optimize_draft_validation_error_examples(mock_dspy: Any) -> None:
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow=uow)
    app.dependency_overrides[get_draft_manager] = lambda: manager
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()
    client = TestClient(app)

    # Less than 3 examples
    payload = {
        "examples": [
            {"input_text": "i", "expected_output": "o"},
            {"input_text": "i", "expected_output": "o"},
        ]
    }

    response = client.post(f"/drafts/{uuid4()}/optimize", json=payload)
    assert response.status_code == 422


def test_api_optimize_draft_validation_error_iterations(mock_dspy: Any) -> None:
    uow = InMemoryUnitOfWork()
    manager = DraftManager(uow=uow)
    app.dependency_overrides[get_draft_manager] = lambda: manager
    app.dependency_overrides[get_current_user_id] = lambda: uuid4()
    client = TestClient(app)

    # Iterations < 1
    payload = {
        "examples": [{"input_text": "i", "expected_output": "o"} for _ in range(3)],
        "iterations": 0,
    }

    response = client.post(f"/drafts/{uuid4()}/optimize", json=payload)
    assert response.status_code == 422
