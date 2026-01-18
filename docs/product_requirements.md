# **Product Requirements Document: coreason-foundry**

Domain: Agent Development Life Cycle (ADLC)
Architectural Role: The Collaborative Workspace Manager & Real-Time State Engine
Integration Target: coreason-api (HTTP/WS Provider), coreason-assay (Consumer)

## ---

**1\. Executive Summary**

coreason-foundry is the interactive, stateful backend for the CoReason IDE. It bridges the gap between fleeting engineering thoughts and permanent GxP artifacts.

Its mandate is to enable **Synchronous Collaboration** without compromising **GxP Attribution**. It manages the "Liquid State" of agent development (drafts, scratchpads, configs) in a high-speed database. Crucially, it resolves the conflict between "Real-Time Teamwork" and "Regulatory Audit Trails" by implementing a hybrid model: **Real-Time Social Awareness** (via WebSockets) combined with **Serialized Technical Editing** (via Pessimistic Locking).

## **2\. Functional Philosophy**

The agent must implement the **Collaborative GxP Control Loop**:

1. **Draft-Iterate-Freeze:** No change is final until published. The DB acts as the "Staging Area" reflecting the current intent of the team.
2. **Attribution \> Convenience:** To ensure strict 21 CFR Part 11 compliance, we reject "simultaneous editing" (Google Docs style) in favor of **Field-Level Locking**. Every character change must be attributable to exactly one user session.
3. **Real-Time Context:** While coding is serialized, context is shared instantly. If User A runs a test, User B sees the console logs stream in real-time.
4. **Traceability from Birth:** Every draft version, even those never published, is immutable once saved to allow for "Undo/Redo" and forensic auditing.

## ---

**3\. Core Functional Requirements (Component Level)**

### **3.1 The Project Manager (The Container)**

**Concept:** The entity that groups related assets into a "Workspace."

* **Workspace Creation:** Creates a container for a specific agent initiative (e.g., "Oncology Clinical Protocol Agent").
* **Asset Bundling:** Tracks all file types: System Prompts, Topology (JSON/YAML), Test Corpora (BEC), and Few-Shot Conversation Logs.
* **Access Control:** Enforces permissions (Edit vs. View). Integrates with coreason-identity.

### **3.2 The Draft Engine (The Editor)**

**Concept:** The mechanism for reading/writing mutable state.

* **Versioning (Micro-Commits):** Every "Save" creates a distinct version in the DB (v0.1.1). This supports full "Undo/Redo" capability.
* **Diffing Utility:** Provides a compare\_versions(id\_A, id\_B) method returning a text delta to visualize changes between drafts.
* **Pessimistic Locking Protocol (UPDATED):**
  * **Acquire:** When a user focuses a field (e.g., system\_prompt), the client requests a lock. If free, the server grants it and broadcasts LOCKED\_BY\_USER\_X to all other viewers.
  * **Deny:** If already locked, the request is rejected. The UI renders the field as Read-Only for the requester.
  * **Release:** The lock is released on "Save," "Cancel," or "Socket Disconnect."

### **3.3 The Real-Time Gateway (The Broadcaster) \[NEW\]**

**Concept:** A WebSocket manager handling ephemeral state and event streaming.

* **Presence Engine:** Tracks connected user\_ids per project\_id. Broadcasts "User Joined/Left" events to render avatars in the UI.
* **Live Console Streaming:** If User A triggers a coreason-assay test, the stdout/stderr logs are piped through the WebSocket channel so User B can watch the test execution live.
* **Instant Comment Delivery:** When a comment is created (via HTTP), a notification event is pushed immediately to all connected sockets.

### **3.4 The Annotation Layer (The Notebook)**

**Concept:** A meta-layer for human collaboration.

* **Contextual Comments:** Users can attach comments to specific lines of code or prompt text.
* **Scratchpad:** A shared free-text area for "Engineering Notes."
* **Task Tracking:** Support for simple checklists (e.g., "To-Do: Fix JSON schema").

### **3.5 The Staging Bridge (The Handshake)**

**Concept:** The preparation interface for downstream tools.

* **Export for Assay:** Serializes the *current active draft* into a runnable payload for testing.
* **Export for Publisher:** Locks the project (Global Read-Only) and hands over the "Final Bundle" to coreason-publisher for Git committal.

## ---

**4\. Integration Requirements (The Ecosystem)**

* **API Provider (Hook for coreason-api):**
  * **HTTP:** Exposes CRUD endpoints (create\_draft, save\_draft, get\_diff).
  * **WebSocket:** Exposes /ws/project/{id} endpoint for event streaming.
* **Test Subject (Hook for coreason-assay):**
  * assay requests the logic from foundry. foundry ensures assay receives the exact version currently visible in the editor.
* **Archival Source (Hook for coreason-publisher):**
  * The Foundry is the "Source of Truth" for the Publisher. publisher commits exactly what is in the Foundry DB.

## ---

**5\. User Stories (Behavioral Expectations)**

### **Story A: The "Locked Edit" (GxP Safety)**

Trigger: User A and User B open "Oncology Agent."
Action: User A clicks into the "System Prompt" box.
System Response: Foundry grants lock to User A.
Broadcast: Foundry sends LOCK\_ACQUIRED event to User B.
User B UI: The "System Prompt" box turns grey with a badge: "Being edited by User A." User B cannot type.
Completion: User A clicks Save. Lock is released. User B's UI unlocks.

### **Story B: The "Live Observation" (Collaboration)**

Trigger: User A says "Watch this test run" via voice chat.
Action: User A clicks "Run Benchmark" in the UI.
System Response: coreason-assay begins execution.
Streaming: Foundry pipes the assay logs via WebSocket to the project\_123 channel.
User B UI: User B sees the terminal window scroll in real-time, showing the agent's reasoning steps as they happen.

### **Story C: The "Rollback" (Version Control)**

Trigger: SRE realizes Draft v15 broke the JSON formatting.
Action: SRE views "Version History." Selects "Draft v14."
Diff: foundry computes the diff, showing the error.
Restore: SRE clicks "Revert." foundry creates Draft v16 (clone of v14) to preserve the linear history of the mistake.

## ---

**6\. Observability Requirements**

To support the "Glass Box" philosophy, the collaborative state must be transparent.

* **FoundryLog Object:**
  * **Edit Events:** standard CRUD logs (User, Time, Delta).
  * **Lock Events:** LOCK\_ACQUIRED and LOCK\_RELEASED (vital for proving who controlled the screen during critical edits).
  * **Socket Events:** Connection/Disconnection logs (Presence auditing).
* **Metrics:** Track "Active Socket Connections" and "Lock Contention Rate" (how often users are blocked by others).

## ---

**7\. Data Schema (Conceptual)**

This serves as the blueprint for the database and state management.

### **Persistent (SQL/NoSQL)**

* **Project**: id, name, created\_at, current\_draft\_id
* **Draft**: id, project\_id, version\_number, prompt\_text, model\_config (JSON), author\_id (The single user who held the lock)
* **Comment**: id, draft\_id, target\_field, text, author\_id

### **Ephemeral (Redis / Memory)**

* **LockRegistry**:
  * Key: lock:project:{id}:field:{name}
  * Value: { user\_id: "...", expires\_at: "..." }
* **PresenceRegistry**:
  * Key: presence:project:{id}
  * Value: List\[user\_id\]
