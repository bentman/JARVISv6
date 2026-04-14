### Preferred Slice Order

~~#### Slice 0: Hardware Profiler~~ Completed
- callable hardware detection
- normalized capability profile output
- runtime profile selection input
- no UI required

~~#### Slice 1: Minimal Voice Turn~~ Completed
- explicit invocation
- capture one utterance
- local STT
- route through normal cognition engine
- return visible text response
- personality profile applied to response

~~#### Slice 2: Spoken Response~~ Completed
- local TTS for response playback
- explicit speaking state
- graceful no-TTS degraded mode

~~#### Slice 3: Turn Continuity and Memory~~ Completed
- preserve session continuity across multiple spoken turns
- align artifacts and memory writes
- prove memory write policy for conversational turns rather than leaving memory as an unvalidated side effect

~~#### Slice 4: Interruptibility~~ Completed
- barge-in during speech
- clean stop/resume transitions
- explicit interruption artifact capture

~~### Slice 0.0 — Readiness / Validation Tightening~~ Completed

- Align startup/init and validation ownership boundaries
- Fail early and clearly when required voice-model assets are missing
- Keep runtime harness validation-only (not a model initializer)
- Reconcile `settings.py` with `.env` / `.env.example` contract
- Correct stale readiness-test expectations to match current manifest/resolver behavior
- Improve trustworthiness of repo readiness and validation signals before new application-surface work

~~### Slice 5A — Application Shell and Start Path~~ Completed

Goal: establish a clean, honest, user-facing application shell around the verified voice/runtime core before any polish-focused expansion.

Scope:
- Canonical build/start path for the application
- One clear application entry mechanism for normal local use
- Typed fallback wired into the same turn engine as voice
- Push-to-talk / explicit invocation surface
- Assistant status, readiness, and degraded-mode visibility
- Basic configuration and diagnostics surface
- Conversation display and control surface sufficient for real use
- Clear startup/init ownership and failure presentation

Acceptance intent:
- A user can build/start the application through one supported path
- The application exposes the same core assistant behavior through voice and typed fallback
- Readiness, missing prerequisites, and degraded states are surfaced clearly before or at startup
- The shell is functional and trustworthy even if it is not yet polished

Notes:
- This slice is foundational, not cosmetic
- It exists to bridge the verified backend/runtime capabilities with a usable application surface
- It should reuse proven application-shell ideas where possible without weakening current runtime/startup ownership boundaries

~~### Slice 5B — Presence and Persona~~ Completed

Goal: add assistant presence behaviors and polish after the application shell/start path is established.

Scope:
- Desktop shell polish
- Personality shaping controls
- Assistant presence behaviors
- Wake word
- Higher-quality interaction feel around the already-working application shell

Acceptance intent:
- The assistant feels more present, responsive, and characterful
- Presence features layer on top of a stable application shell rather than compensating for a missing one
- Persona/polish improvements do not undermine startup honesty, readiness clarity, or core turn reliability

Notes:
- Wake word remains valuable, but it should follow a trustworthy start path and usable shell
- This slice is about improving how JARVIS feels, not creating the first viable application surface

---

~~### Slice 6 — Durable Desktop Host + Resident Lifecycle~~ Completed

Goal: replace the bounded proving host with the real `desktop/` product shell and close the remaining same-session resident interaction gap.

Scope:
- Native desktop application under `desktop/` (Tauri or equivalent) as the durable application surface
- System tray presence, start/stop/running controls, and clean process lifecycle
- Conversation display, assistant status, and push-to-talk / hotkey invocation
- Resident voice loop: continuous interaction within a session without manual re-invocation between turns
- Wake word host integration (capability already verified in Slice 5B; this slice wires it into the durable host)
- Configuration and diagnostics surface within the desktop shell
- Shell consumes `startup_service.py`, `voice_service.py`, and `task_service.py` unchanged — no orchestration logic inside the shell

Acceptance intent:
- A user can launch JARVIS as a native desktop application with visible start/stop/running state
- The assistant maintains a continuous resident session without requiring manual re-invocation between turns
- Wake word and push-to-talk both work as invocation paths within the durable host
- Shell remains a thin adapter; all orchestration, memory, and runtime selection remain backend-owned
- `scripts/run_jarvis.py` is retired or explicitly demoted to a developer/diagnostic tool

Notes:
- Design with overlay and ambient presence as the capability group end state, even if early milestones are tray + controls + conversation display
- The current verified interruption boundary is single-turn with caller-initiated next turn — this slice closes that into a true resident path
- Wake capabilities from Slice 5B integrate here; do not re-invent them

### Slice 7 — Local Service Substrate (Redis + SearXNG)

Goal: stand up Redis and SearXNG as local backing services and make the cache and search backends callable from the backend runtime layer.

Scope:
- `docker-compose.yml` (already declared at repo root) provisioning Redis and SearXNG
- Service discovery, health checks, and fail-closed degradation when services are unavailable
- Backend cache layer under `backend/app/cache/` wired to Redis
- Internet search runtime under `backend/app/runtimes/internetsearch/` wired to SearXNG as primary, with DDGS and Tavily as escalation fallbacks
- Redis treated as accelerator and coordination substrate — persisted memory, sessions, and turns remain under `data/` as durable authority

Acceptance intent:
- Redis and SearXNG start cleanly via `docker compose up` and are reachable from the backend
- Cache layer is callable and degrades explicitly when Redis is unavailable
- Internet search runtime returns results via SearXNG on a healthy stack and falls back to DDGS when SearXNG is down
- No orchestration or memory authority moves into infrastructure

Notes:
- Prior JARVISv6 versions used this exact Docker pattern for Redis and SearXNG — known working territory
- Use `backend/app/runtimes/internetsearch/` as the forward boundary name for runtime/provider integration, separate from the tool adapter layer
- Design service discovery and health check patterns with future tool use and LLM escalation in mind

### Slice 8 — Tool Foundation + ACTING Path

Goal: make `ConversationState.ACTING` real by wiring the canonical turn path through deterministic tool execution for a first small set of high-value tools.

Scope:
- `backend/app/cognition/executor.py` implements deterministic tool execution within the turn lifecycle
- `ConversationState.ACTING` exercised on the real runtime path
- First tool set: time/date, filesystem read, internet search (via `backend/app/tools/search/` adapter over `backend/app/runtimes/internetsearch/`)
- Tool registry (`backend/app/tools/registry.py`) authoritative for tool discovery and dispatch
- Tool results flow back through the cognition path and are rendered by desktop and text shells
- Tool invocations recorded in turn artifacts

Acceptance intent:
- A voice or text turn that requires tool use reaches `ACTING` state and returns a tool-grounded response
- Time/date, filesystem read, and internet search each produce correct, traceable results in the live runtime
- Tool execution is explicit and logged — no hidden side effects
- Desktop and text shells render tool-grounded responses without knowing tool internals

Notes:
- Ownership: `backend/app/runtimes/internetsearch/` for provider integration, `backend/app/tools/search/` for tool-facing adapter, `executor.py` + `ACTING` for orchestration
- Design the tool contract to support arbitrary future tool addition without redesign
- This is the slice that makes JARVIS operationally useful rather than only conversational

### Slice 9 — Cross-Session Episodic Retrieval

Goal: turn the verified session/artifact base into true cross-session recall so JARVIS remembers things said in prior conversations.

Scope:
- `backend/app/memory/episodic.py` implemented: write, retrieve, and summarize episodic memory across sessions
- `backend/app/memory/retrieval.py` implemented: query episodic and working memory for relevant prior context
- Prior turn artifacts under `data/turns/` and session records under `data/sessions/` as durable authority
- Redis from Slice 7 used for lookup caching and retrieval performance acceleration
- Explicit write policy governing what enters episodic memory (extends existing `write_policy.py` pattern)
- Retrieved context injected into prompt assembly alongside working memory

Acceptance intent:
- A turn in session N can recall and reference information from session N-1 through episodic retrieval
- Episodic writes and retrievals are explicit, logged, and traceable in turn artifacts
- Redis caching of retrieval results degrades cleanly when Redis is unavailable
- Durable memory authority remains in persisted artifacts, not infrastructure

Notes:
- Design with semantic memory and summarization as the capability group end state, even if early milestones are simple episodic lookup by recency
- This closes the gap between "assistant that works in a session" and "persistent local assistant" — a direct ProjectVision.md requirement

### Slice 10 — Local llama.cpp Runtime Activation + LLM Readiness Rail

Goal: activate `LlamaCppLLM` as a working local inference path and extend the proven hardware readiness rail to cover LLM backend readiness.

Scope:
- Local llama.cpp deployed via Docker (same pattern as Redis/SearXNG in Slice 7, consistent with prior JARVISv6 versions)
- `backend/app/runtimes/llm/local_runtime.py` `LlamaCppLLM` inference wiring implemented (currently raises `NotImplementedError`)
- LLM readiness rail: `llm_local_ready` and `llm_selected_runtime` fields in `BackendReadiness` populated with real probe evidence
- Ollama remains the live fallback; local llama.cpp is a runtime substitution, not an architectural change
- `backend/app/routing/runtime_selector.py` prefers local llama.cpp when verified ready, falls back to Ollama explicitly

Acceptance intent:
- Local llama.cpp responds correctly to LLM requests through the existing runtime boundary
- `BackendReadiness.llm_local_ready=True` emitted only after probe evidence confirms local inference is usable
- Startup summary surfaces LLM readiness state explicitly alongside STT/TTS readiness
- Ollama fallback path remains functional and is exercised when local runtime is unavailable
- No change to tool, memory, or shell behavior — this is a runtime substitution only

Notes:
- Prior JARVISv6 versions used pre-compiled llama.cpp binaries in Docker — known working territory
- Extend the Slice 0.0 readiness rail pattern exactly as done for STT and TTS — no new pattern needed
- By this point desktop, tools, and memory are established; local LLM is an upgrade into a mature system

