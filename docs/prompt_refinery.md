# Prompt Refinery

The **Prompt Refinery** is a subsystem within CoReason Foundry that enables automated optimization of Agent System Prompts using "Golden Set" examples. It leverages `dspy` (Declarative Self-Improving Language Programs) to algorithmically refine prompts based on empirical evidence (input/output pairs).

## Philosophy: Glass Box Optimization

Unlike "Black Box" optimizers that hide the resulting prompt, Foundry employs a "Glass Box" strategy.
1.  **Draft N (Human Intent):** The user writes an initial draft.
2.  **Optimization:** The user provides examples. The system runs an optimization loop (using `dspy.teleprompt.COPRO`).
3.  **Draft N+1 (Machine Optimized):** The system produces a *new* Draft version containing the optimized prompt.
4.  **Review:** The user can diff Draft N and Draft N+1 to see exactly what changed. The user retains full control and can revert or further edit the optimized prompt.

## How it Works

1.  **Input:**
    *   **Current Prompt:** The starting point.
    *   **Golden Set:** A list of `OptimizationExample` objects (Input Text -> Expected Output). Minimum 3 examples required.
    *   **Metric:** A description of what to optimize for (e.g., "brevity", "JSON compliance"). Currently uses an exact match or boolean logic metric.
    *   **Iterations:** Number of optimization candidates to generate (default 10).

2.  **Process:**
    *   Foundry wraps the draft prompt in a `dspy.Module`.
    *   It defines a training set from the provided examples.
    *   It executes the `COPRO` (Chain of Thought Proposal) teleprompter.
    *   The best performing instruction is extracted.

3.  **Output:**
    *   A new Draft is created with the optimized `prompt_text`.
    *   The `scratchpad` is updated with metadata about the optimization run.

## API Usage

### Endpoint

`POST /drafts/{draft_id}/optimize`

### Payload

```json
{
  "examples": [
    {
      "input_text": "Calculate 2+2",
      "expected_output": "4"
    },
    {
      "input_text": "Capital of France",
      "expected_output": "Paris"
    },
    {
      "input_text": "Reverse 'abc'",
      "expected_output": "cba"
    }
  ],
  "iterations": 10,
  "metric_description": "Accuracy and brevity"
}
```

### Response

Returns a `DraftRead` object representing the newly created draft.
