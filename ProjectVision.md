# JARVISv6 ProjectVision

## Vision

JARVISv6 is a local-first, voice-first personal assistant designed for real conversational interaction on user-owned hardware.

It is not a chatbot with voice added later. It is a real-time conversation engine with text as a fallback surface.

The target experience is closer to J.A.R.V.I.S. than a browser chat app:
- the user can speak naturally
- the system listens, transcribes, reasons, responds, and speaks back
- the user can interrupt
- the system preserves turn continuity
- the assistant has a defined personality
- failures are explicit and degrade cleanly instead of silently collapsing

JARVISv6 must be useful on day one in a minimal conversational loop, then expand toward richer memory, tool use, interruption handling, assistant presence, and personality depth.

---

## Product Identity

JARVISv6 is:

- voice-first
- desktop-first
- hardware-aware from process start
- local-first by default
- deterministic in orchestration
- explicit in memory and cognition
- interruptible
- personality-driven
- text-capable, but not text-centered

JARVISv6 is not:

- a text chat system with optional voice buttons
- a detached voice panel experiment
- a cloud-first assistant that happens to run locally
- a collection of disconnected AI features without a primary interaction model
- a personality-less command shell with speech bolted on

---

## Primary Goal

Build a usable voice-first assistant whose core interaction loop works end-to-end in the real runtime:

1. system profiles hardware at startup
2. system emits a capability profile used by all downstream subsystems
3. user invokes the assistant
4. assistant captures audio
5. assistant transcribes locally by default
6. assistant routes the turn through the same cognition and execution engine used by all modalities
7. assistant returns a response aligned to the configured personality
8. assistant speaks back locally when TTS is available
9. user can interrupt and continue naturally
10. all failure modes are visible and recoverable

This loop is the root acceptance path for the system.

If this path does not work in the active runtime, the system is not considered complete regardless of subsystem tests.

---

## Foundational Principle

### Hardware Profiling Comes First

The first callable system capability in JARVISv6 is the hardware profiler.

Before UI, before voice capture, before model selection, before orchestration, the system must detect the execution environment and emit a capability flags object.

This profile is the root input for:
- model selection
- STT runtime selection
- TTS runtime selection
- LLM backend selection
- quantization strategy
- concurrency limits
- degraded-mode policy
- wake-word support
- desktop vs laptop behavior
- power-aware behavior
- personality/runtime presentation constraints where needed

JARVISv6 should not guess what it can do.
It should know.

---

## Core Principles

### 1. Voice Is the Root Mode

Voice is not a late-stage feature.
Voice defines the primary system architecture.

Text input is a fallback and debug path into the same turn engine.

### 2. Hardware-Aware Execution Starts at Boot

JARVISv6 must begin with a hardware profiling pass that detects:
- OS
- CPU
- GPU
- GPU vendor
- CUDA availability
- NPU availability
- total memory
- available memory where practical
- desktop vs laptop profile where practical

This detection must emit a callable profile object and capability flags object that downstream systems consume directly.

### 3. Local-First by Default

JARVISv6 should prefer local execution for:
- STT
- TTS
- reasoning where hardware allows
- memory
- orchestration
- artifacts and trace storage

Remote providers may be used only through explicit policy and only when local capability is unavailable or intentionally overridden.

### 4. Deterministic Orchestration

LLMs provide reasoning, not control.

Control flow must be explicit and deterministic through a defined conversation and execution state machine.
No hidden assistant behavior should exist only inside a prompt.

### 5. Externalized Cognition

Memory, plans, artifacts, context, and tool traces must live outside the model.
The model is stateless between calls unless context is explicitly supplied.

### 6. Personality Is a Core System Dimension

Personality is not cosmetic.
It is part of the assistant contract.

JARVISv6 must define personality explicitly so that:
- wording style is intentional
- spoken response style is intentional
- pacing and brevity can be tuned
- persona does not drift unpredictably
- tone survives across turns and modalities
- personality settings remain compatible with deterministic orchestration and explicit policies

Personality must be externally configured and inspectable, not left as vague prompt residue.

### 7. Clear Failure States

JARVISv6 must never silently fail with empty output or unexplained states.

Every major subsystem must fail closed and visibly:
- profiler unavailable
- STT unavailable
- TTS unavailable
- model missing
- provider import failure
- wake-word unavailable
- interrupted response
- execution failure

### 8. Live Runtime Validation Over Narrow Success

A feature is only complete if it works in the actual runtime used by the product.
Passing builds and narrow tests are necessary but not sufficient.

---

## Product Outcome

JARVISv6 should feel like a persistent local assistant, not like a web app with AI features.

The user experience target is:
- low-friction invocation
- natural spoken interaction
- immediate system feedback
- visible state transitions
- smooth degradation when a modality is unavailable
- continuity across turns
- recognizable assistant personality

The user should understand at all times whether JARVIS is:
- profiling
- idle
- listening
- transcribing
- thinking
- speaking
- interrupted
- degraded
- failed

---

## First System Capability: Hardware Profiler

The hardware profiler is the first required implementation slice of JARVISv6.

### Purpose

Detect host capabilities and return a normalized profile object that the rest of the system can call.

### Required Detection Targets

- operating system
- architecture
- CPU model and capabilities
- GPU presence
- GPU vendor
- CUDA availability
- NPU presence and type where detectable
- total memory
- usable memory where practical
- storage constraints where practical
- desktop vs laptop classification where practical

### Required Output

The profiler must return a normalized capability object, conceptually like:

- `os`
- `arch`
- `cpu`
- `gpu`
- `gpu_vendor`
- `cuda_available`
- `npu_available`
- `npu_vendor`
- `memory_gb`
- `device_class`
- `capability_flags`

### Capability Flags

The emitted flags should support decisions such as:
- `supports_local_llm`
- `supports_gpu_llm`
- `supports_cuda_llm`
- `supports_local_stt`
- `supports_local_tts`
- `supports_wake_word`
- `supports_realtime_voice`
- `supports_desktop_shell`
- `requires_degraded_mode`

The exact schema can evolve, but the principle cannot:
every major subsystem should consume a shared capability profile rather than inventing its own environment checks.

### Non-Goals of the Profiler

The profiler does not:
- present UI
- load models
- invoke voice runtimes
- choose final personality
- execute assistant turns

It detects and emits.
That is its contract.

---

## Personality System

Personality must be a first-class subsystem in JARVISv6.

### Purpose

Define how JARVIS behaves, not just what it says.

### Personality Scope

Personality should influence:
- tone
- brevity
- assertiveness
- warmth
- humor policy
- formality
- spoken cadence targets
- interruption handling style
- acknowledgment style
- confirmation style
- assistant identity consistency

### Personality Constraints

Personality must not:
- override safety or policy rules
- invent facts
- bypass deterministic orchestration
- produce inconsistent behavior between text and voice
- live only as an opaque system prompt fragment

### Personality Representation

Personality should be externalized and configurable through structured settings, profiles, or policy artifacts.

A minimal conceptual personality profile should look like:

- `profile_id`
- `display_name`
- `identity_summary`
- `tone`
- `brevity`
- `formality`
- `warmth`
- `assertiveness`
- `humor_policy`
- `response_style`
- `acknowledgment_style`
- `interruption_style`
- `voice_pacing`
- `voice_energy`
- `safety_overrides`
- `enabled`

The exact schema can evolve, but the principle cannot:
personality must be structured enough to persist, compare, validate, and apply consistently across text and voice paths.

### Personality and Voice

Voice output should reflect the same personality profile as text output where possible.

If the chosen TTS runtime supports voice variation, it should map to the configured personality.
If TTS does not support it, the text response style should still remain personality-consistent.

---

## Session Model

A session is the bounded conversational context within which turns are grouped for continuity, memory policy, and interruption recovery.

A session begins when JARVIS transitions from `IDLE` into an invocation-handling path for a user interaction.
A session may contain one or more turns.
A session remains active while the assistant is still handling follow-up interaction under continuity policy.
A session ends when the system returns to a clean idle baseline and continuity policy decides no active interaction context remains.

A session is not equivalent to a single HTTP request, a single utterance, or a single UI screen.
It is the interaction container used to group related turns and their artifacts.

---

## Core Interaction Model

JARVISv6 is built around a canonical turn lifecycle.

### Canonical Turn States

- `BOOTSTRAP`
- `PROFILING`
- `IDLE`
- `LISTENING`
- `TRANSCRIBING`
- `REASONING`
- `ACTING`
- `RESPONDING`
- `SPEAKING`
- `INTERRUPTED`
- `RECOVERING`
- `FAILED`

Text and voice both enter this same turn lifecycle.

### Canonical Turn Flow

#### Startup
1. system starts
2. hardware profiler runs
3. capability flags are emitted
4. runtime profile is selected
5. personality profile is loaded
6. system enters `IDLE`

#### Voice Turn
1. user invokes assistant
2. assistant enters `LISTENING`
3. audio is captured
4. assistant enters `TRANSCRIBING`
5. transcript is produced
6. transcript enters normal cognition/execution path
7. assistant enters `REASONING` / `ACTING`
8. response text is produced in alignment with personality profile
9. assistant enters `RESPONDING`
10. if TTS available, assistant enters `SPEAKING`
11. user may interrupt at any point allowed by policy
12. turn ends in `IDLE`, `RECOVERING`, or `FAILED`

#### Text Turn
1. user submits typed text
2. system bypasses listen/transcribe stages
3. text enters the same cognition/execution path
4. response follows the same response lifecycle and personality rules

Text is therefore a secondary ingress path, not a separate product architecture.

---

## Interruption Policy

Interruption is a first-class system behavior, not a UI afterthought.

### Policy Model

For the initial V6 architecture, interruption policy should follow these rules:

1. **Speech output is interruptible.**
   If the assistant is in `SPEAKING`, a valid barge-in signal should stop speech output immediately or at the nearest safe boundary supported by the runtime.

2. **Listening has priority over continued speaking when barge-in is accepted.**
   Once interruption is accepted, the system transitions out of `SPEAKING` and into the next valid capture state according to policy.

3. **The interrupted response must remain traceable.**
   The turn artifact must record that the response was interrupted, including timing and recovery state.

4. **State preservation is explicit.**
   The assistant must preserve enough turn/session context to continue coherently after interruption.

5. **Unsafe or unsupported interruption modes degrade cleanly.**
   If true barge-in is not supported by the current runtime, the system must expose that limitation and fall back to a defined stop-and-reinvoke behavior.

### Initial Implementation Rule

The first acceptable interruption behavior is:
- user interrupts while JARVIS is speaking
- speech output stops
- system records the interruption
- system transitions cleanly to the next allowed state without corrupting the session

Perfect conversational overlap is not required initially.
Deterministic interruption behavior is required.

---

## Canonical Turn Artifact

Every turn should produce an explicit artifact, whether voice or text.

A turn artifact should capture at minimum:
- turn id
- session id
- input modality
- hardware profile id or snapshot
- capability flags used for the turn
- active personality profile
- raw audio references, if any
- transcript
- final prompt text used for cognition
- retrieved memory/context references
- tools invoked
- reasoning/execution trace metadata
- response text
- audio output references, if any
- interruption events
- final state
- explicit failure reason, if any
- timestamps for each major phase

This artifact is the authoritative record of what happened.

---

## Architecture Overview

JARVISv6 should be organized into the following major layers.

### 1. Hardware Intelligence Layer

Responsible for:
- detecting available hardware
- classifying execution environment
- selecting runtime profiles
- emitting capability flags
- exposing a callable hardware profile object to the rest of the system

This layer decides what is realistically available before the assistant attempts work.

Examples:
- CPU-only fallback
- GPU-accelerated local inference
- CUDA-enabled profile
- NPU-assisted profile where supported
- degraded voice mode when TTS is unavailable
- text fallback when STT is unavailable

### 2. Personality Layer

Responsible for:
- loading personality definitions
- applying personality policy to responses
- maintaining consistent style across text and voice
- exposing structured personality controls to the conversation engine
- keeping persona explicit and inspectable

This layer shapes assistant identity without owning orchestration.

### 3. Voice Runtime Layer

Responsible for:
- microphone access orchestration
- audio capture lifecycle
- wake word integration when enabled
- STT session execution
- TTS session execution
- interruption and barge-in handling
- audio device management

This layer owns real-time voice execution, not the chat UI.

### 4. Conversation Engine

Responsible for:
- turn lifecycle orchestration
- explicit state transitions
- routing between listen, transcribe, reason, act, respond, speak
- interruption recovery
- session continuity

This is the core runtime of JARVISv6.

### 5. Cognition Engine

Responsible for:
- prompt assembly
- planning
- tool-use decisions
- execution governance
- memory retrieval and writeback
- policy enforcement
- applying the active personality profile consistently during prompt assembly and response shaping

The cognition engine must consume personality explicitly, not implicitly.
That means:
- the active personality profile is an input to prompt assembly
- personality rules are applied equally for voice and text turns
- personality never bypasses tool policy, memory policy, or safety policy
- personality must be traceable as part of the turn artifact context

This layer follows explicit cognition principles:
- models are stateless workers
- memory is externalized
- plans and outcomes are explicit
- reasoning is constrained by deterministic orchestration

### 6. Memory System

Responsible for:
- working memory
- episodic memory
- semantic memory
- task and conversation history
- retrieval and summarization
- explicit write policies

Memory exists to support continuity and assistant usefulness, not as a hidden side effect.

### 7. Desktop Shell

Responsible for:
- user-facing interface
- tray and overlay modes
- hotkeys / push-to-talk
- conversation display
- assistant status display
- configuration and diagnostics

The desktop shell is the home of the assistant, but not the source of orchestration logic.

### 8. Text Surface

Responsible for:
- typed fallback interaction
- debugging
- explicit task entry when voice is not appropriate
- visibility into cognition/tool results when needed

This must reuse the same conversation engine rather than inventing a separate chat architecture.

---

## Voice-First Functional Requirements

### Must Have

- callable hardware profiler that returns a normalized capability profile
- local-first STT path
- local-first TTS path when runtime is available
- push-to-talk or equivalent explicit invocation path
- assistant response through the canonical turn engine
- deterministic state transitions
- explicit error states
- typed fallback
- hardware-aware runtime selection
- personality profile loading and application
- traceable turn artifacts
- fail-closed behavior for missing runtime/model/provider
- clear interruption path for assistant speech
- no silent blank responses

### Should Have

- wake word support
- streaming partial transcription
- streaming partial assistant response
- low-latency response start
- visible degraded-mode indicators
- profile-aware runtime selection
- selectable personality profiles
- selectable voices
- session continuity across interruptions

### Could Have

- ambient listening mode
- multi-device orchestration
- proactive notifications
- emotional or expressive speech controls
- richer avatar or desktop presence
- multimodal visual awareness

### Must Not

- depend on cloud-only operation by default
- hide failures behind null/empty payloads
- let voice logic break primary typed interaction
- let UI experiments define backend architecture
- merge unproven subsystem work as “complete” without live-path validation

---

## Runtime Strategy

### Local-First Execution Order

The preferred execution order is:
1. local runtime
2. local fallback runtime
3. explicitly approved remote provider

This applies independently to:
- STT
- TTS
- LLM reasoning
- embeddings and memory support services

### Runtime Selection Inputs

Runtime selection must be driven by:
- hardware profile
- capability flags
- policy
- user preferences
- personality/runtime compatibility where applicable

### Hardware Profiles

JARVISv6 should support profile-driven execution such as:
- desktop x86_64 with NVIDIA GPU and CUDA
- desktop x86_64 CPU-only
- laptop x86_64 with integrated GPU
- laptop ARM with NPU
- constrained fallback profile

Each profile should influence:
- model family
- quantization
- max concurrency
- response strategy
- voice latency expectations
- degraded-mode policy

### Degraded Modes

Examples:
- STT available, TTS unavailable -> text reply + explicit silent-response mode
- TTS available, STT unavailable -> typed input + spoken output
- local LLM unavailable -> explicit provider fallback if allowed
- wake unavailable -> push-to-talk only
- microphone unavailable -> text-only fallback
- GPU unavailable -> CPU profile with explicit performance downgrade

Degraded mode is acceptable.
Silent confusion is not.

---

## Explicit Cognition Framework Alignment

JARVISv6 should continue and strengthen the Explicit Cognition Framework.

### ECF Rules

- no hidden long-term assistant state inside the model
- no implicit memory writes without policy
- tool actions must be explicit and logged
- plans and execution phases must be inspectable
- all important state transitions must be reconstructable from artifacts
- cognition must remain separable from presentation and transport
- personality must be explicit and externally represented
- hardware capability assumptions must be derived from the profiler, not hidden inside provider code

### Why ECF Matters More in V6

Voice interaction increases ambiguity, latency sensitivity, interruption complexity, and persona sensitivity.
Without explicit cognition, explicit hardware awareness, and explicit turn artifacts, debugging spoken interaction becomes nearly impossible.

ECF is therefore more important in V6 than it was in prior text-centered versions.

---

## Acceptance Model

JARVISv6 should be accepted based on primary-path behavior in the real runtime.

### Minimum Real Acceptance Path

A minimal acceptable voice loop is:

1. system profiles the host and emits capability flags
2. the selected runtime profile is explicit
3. the personality profile is explicit
4. user invokes assistant
5. assistant enters listening state visibly
6. user speaks a simple request
7. assistant transcribes successfully
8. assistant routes the transcript through the normal cognition/execution path
9. assistant returns a valid response aligned to personality
10. if TTS runtime is available, assistant speaks it
11. if user interrupts during speech, assistant stops and transitions cleanly
12. final state is explicit and recorded

If this path does not work in the active runtime, the slice is not complete.

### Validation Hierarchy

1. live runtime behavior
2. capability profile correctness
3. targeted functional tests
4. build/test harness results
5. logs and traces
6. documentation updates

This order is intentional.

---

## Implementation Philosophy

JARVISv6 should be built through thin vertical slices, not isolated subsystem milestones.

The wrong approach is:
- build a route
- then build a recorder
- then build a panel
- then wire them later

The correct approach is:
- build the profiler first
- prove the runtime profile is correct
- prove the smallest real conversational loop
- preserve the primary path at every step
- expand capability only after the real loop works

### Preferred Slice Order

#### Slice 0: Hardware Profiler
- callable hardware detection
- normalized capability profile output
- runtime profile selection input
- no UI required

#### Slice 1: Minimal Voice Turn
- explicit invocation
- capture one utterance
- local STT
- route through normal cognition engine
- return visible text response
- personality profile applied to response

#### Slice 2: Spoken Response
- local TTS for response playback
- explicit speaking state
- graceful no-TTS degraded mode

#### Slice 3: Turn Continuity and Memory
- preserve session continuity across multiple spoken turns
- align artifacts and memory writes
- prove memory write policy for conversational turns rather than leaving memory as an unvalidated side effect

#### Slice 4: Interruptibility
- barge-in during speech
- clean stop/resume transitions
- explicit interruption artifact capture

#### Slice 5: Presence and Persona
- wake word
- desktop shell polish
- personality shaping controls
- assistant presence behaviors

---

## User Experience Goals

JARVISv6 should feel:
- immediate
- dependable
- local
- private
- responsive
- understandable
- interruptible
- personal

The user should never have to guess:
- what hardware/runtime profile was selected
- whether the assistant heard them
- whether the assistant is still thinking
- whether the assistant is speaking
- whether the system failed
- whether the system is degraded

---

## Non-Goals for Initial V6

The initial version of V6 does not need to include all future assistant ambitions.

It does not need:
- perfect wake-word support
- flawless multi-turn natural conversation
- rich emotional personality simulation
- broad proactive autonomy
- cloud orchestration
- mobile-first support

It does need:
- one honest hardware profiler
- one honest and working conversational loop
- correct runtime selection
- explicit personality handling
- deterministic control
- visible failures
- clean fallback behavior

---

## Repository and Governance Alignment

JARVISv6 must remain aligned with repo governance.

This means:
- evidence-first changes
- minimal diffs
- no claiming completion without reproducible proof
- approval-gated implementation
- no roadmap drift from runtime reality
- no “complete” status unless the primary path works in the real runtime

In repo terms:
- `ProjectVision.md` defines the target state and core invariants
- `SYSTEM_INVENTORY.md` defines what capabilities are actually observable now
- `CHANGE_LOG.md` defines what has actually been completed with evidence

These must not be conflated.

---

## Definition of Success

JARVISv6 is successful when it behaves like a real local assistant rather than a text system with voice attachments.

The earliest meaningful success state is:

- the system profiles the hardware first
- the system emits capability flags that drive runtime choices
- the assistant personality is explicit and consistent
- the user can invoke JARVIS with voice
- JARVIS can listen and transcribe locally
- the transcript enters the same core cognition path as typed input
- JARVIS produces a response in the real runtime
- JARVIS speaks when TTS is available
- JARVIS fails clearly when a modality is unavailable
- JARVIS can be interrupted without collapsing the session
- all of the above are traceable through explicit artifacts and deterministic state transitions

That is the foundation.
Everything else builds on top of it.