# Vignette: A Day in the Life of a GxP Agent Team

This vignette illustrates how `coreason-foundry` handles the tension between real-time collaboration and strict regulatory compliance (GxP) during the development of a clinical agent.

## Scene: The Oncology Agent

**Cast:**
*   **Alice (User A)**: Clinical Engineer.
*   **Bob (User B)**: Quality Assurance Specialist.
*   **Sarah (SRE)**: Site Reliability Engineer.

### Story A: The "Locked Edit" (GxP Safety)

Alice and Bob are in a video call, looking at the "Oncology Protocol Agent" workspace. They need to refine the system prompt to better handle adverse event reporting.

1.  **Trigger**: Alice says, "I'm going to update the safety instructions." She clicks into the "System Prompt" text area.
2.  **System Response**: `coreason-foundry` receives the lock request. It checks Redis and confirms the field is free. It grants the lock to Alice.
3.  **Broadcast**: The system broadcasts a `LOCK_ACQUIRED` event via WebSocket to all connected clients.
4.  **User Experience**:
    *   **Alice**: Sees the cursor blink. She can type freely.
    *   **Bob**: On his screen, the "System Prompt" box instantly turns grey. A badge appears: *"Being edited by Alice"*. He tries to click it, but it's read-only.
5.  **Completion**: Alice types the new instructions and clicks **Save**. The system creates a new immutable `Draft` (v14) in the database and releases the lock. Bob's screen unlocks, showing the new text.

*Why this matters:* In a GxP audit, we can prove that **only** Alice could have typed those characters during that specific session. Simultaneous editing (Google Docs style) would make individual attribution impossible.

### Story B: The "Live Observation" (Collaboration)

Bob wants to verify that Alice's changes didn't break the reasoning logic.

1.  **Trigger**: Alice says, "Running the benchmark now. Watch the output."
2.  **Action**: Alice clicks **Run Benchmark**.
3.  **System Response**: The request is routed to `coreason-assay`.
4.  **Streaming**: As the agent thinks, `coreason-foundry` pipes the `stdout`/`stderr` logs through the active WebSocket channel (`project_123`).
5.  **User Experience**: Bob sees the terminal window on his screen scroll in real-time. He watches the agent's "Chain of Thought" as it processes the test cases.
    *   *Bob:* "Wait, look at that log line. It's misinterpreting the severity level."
    *   *Alice:* "I see it. Good catch."

*Why this matters:* Even though editing is serialized for compliance, **context** is shared instantly. The team solves problems together in real-time.

### Story C: The "Rollback" (Version Control)

Later that day, Sarah (SRE) receives an alert. The JSON schema generation for the agent is failing in the staging environment.

1.  **Trigger**: Sarah investigates and realizes that Draft v15 (created by a junior engineer) introduced a syntax error in the `model_configuration` JSON.
2.  **Action**: Sarah opens the "Version History" tab in the CoReason IDE. She selects "Draft v14".
3.  **Diff**: `coreason-foundry` calls `DraftManager.compare_versions(v15, v14)`. The UI shows a red/green diff highlighting the malformed JSON bracket.
4.  **Restore**: Sarah clicks **Revert**.
5.  **System Response**: `coreason-foundry` does **not** delete Draft v15 (history must be immutable). Instead, it creates a **new** Draft v16, which is a clone of v14.
6.  **Result**: The project's `current_draft_id` is updated to v16. The linear history is preserved: `v14 (Good) -> v15 (Bad) -> v16 (Good, clone of v14)`.

*Why this matters:* The full audit trail is preserved. An auditor can see exactly when the error was introduced, who introduced it, and who fixed it.
