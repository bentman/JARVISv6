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

