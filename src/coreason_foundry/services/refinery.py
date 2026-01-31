# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_foundry

from typing import List, Optional

import dspy
from dspy.teleprompt import COPRO

from coreason_foundry.api.schemas import OptimizationExample
from coreason_foundry.utils.logger import logger


class PromptRefinery:
    """
    Service for optimizing agent prompts using DSPy.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def optimize(
        self,
        current_prompt: str,
        examples: List[OptimizationExample],
        metric_description: Optional[str] = None,
        iterations: int = 10,
    ) -> str:
        """
        Optimizes the current prompt using the provided examples and DSPy's COPRO optimizer.
        """
        logger.info(f"Starting prompt optimization with {len(examples)} examples.")

        # 1. Define Dynamic Signature
        # We create a signature that uses the current_prompt as the initial instruction.
        # We assume a generic input_text -> prediction flow.
        Signature = dspy.make_signature(
            signature="input_text -> prediction",
            instructions=current_prompt,
            input_text=dspy.InputField(desc="The input to the agent"),
            prediction=dspy.OutputField(desc="The agent's response"),
        )

        # 2. Define the Agent Module
        class AgentModule(dspy.Module):
            def __init__(self):
                super().__init__()
                self.prog = dspy.Predict(Signature)

            def forward(self, input_text):
                return self.prog(input_text=input_text)

        # 3. Create Trainset
        trainset = [
            dspy.Example(input_text=ex.input_text, prediction=ex.expected_output).with_inputs("input_text")
            for ex in examples
        ]

        # 4. Define Metric
        # We compare the 'prediction' field which we defined in the signature/examples.
        # Note: dspy.evaluate.answer_exact_match expects 'answer' field, so we implement custom logic.
        def simple_metric(example, pred, trace=None):
            return example.prediction == pred.prediction

        # 5. Run Optimization (COPRO)
        try:
            # Ensure we use the configured client for this operation using a context manager.
            # This is safer for concurrent requests than global settings.configure.
            with dspy.context(lm=self.llm_client):
                # We map 'iterations' to COPRO's breadth (candidates per step).
                # We keep depth small to ensure it is lightweight.
                optimizer = COPRO(
                    metric=simple_metric,
                    breadth=max(2, iterations),
                    depth=2,
                    init_temperature=0.7,
                    verbose=False,
                )

                # Compile the module
                compiled_module = optimizer.compile(AgentModule(), trainset=trainset)

                # 6. Extract Optimized Instruction
                # The compiled module contains the best predictor found.
                optimized_instruction = compiled_module.prog.signature.instructions
                logger.info("Optimization successful.")
                return optimized_instruction

        except Exception as e:
            logger.exception("Optimization failed. Returning original prompt.")
            # In case of failure, preserve the original intent (Glass Box strategy fallback)
            return current_prompt
