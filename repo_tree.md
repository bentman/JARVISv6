## Repo Structure

JARVISv6 should use a repo layout that reinforces runtime domains, keeps config separate from code, keeps mutable artifacts out of source, and prevents UI-first drift.

### Structure Rules

- top-level folders come first; top-level root files come last; both lists stay alphabetized
- runtime domains own behavior; routes and UI surfaces are thin adapters
- `config/` stores declarative settings and profiles, not mutable runtime state
- `models/` stores model artifacts only, not executable source
- `data/`, `cache/`, and `reports/` store mutable outputs and must not contain source-of-truth code
- runtime integrations use generic labels where technology may change during development
- external escalation providers get explicit runtime files because they are stable policy surfaces
- search escalations live under their own provider domain, separate from LLM runtimes
- artifacts, sessions, and turns are persisted separately from implementation code
- frontend and desktop are product shells; conversation and runtime logic stay in backend domains

### Proposed Top-Level Tree

```text
JARVISv6/
├─ backend/                           # backend runtime, APIs, orchestration, providers, artifacts
├─ cache/                             # mutable cache and backing-store dev assets (redis state, temp); not source code
├─ config/                            # declarative config: app, models, policies, personality, prompts
├─ data/                              # mutable runtime state: memory, sessions, turns, temp
├─ desktop/                           # desktop shell (tauri/native integration, overlays, tray, hotkeys)
├─ docs/                              # architecture, runtime, and decision records
├─ frontend/                          # web/debug/operator surface
├─ models/                            # local model artifacts and downloaded runtime assets (llm, stt, tts, wake, etc.)
├─ reports/                           # validation, diagnostics, benchmark outputs
├─ scripts/                           # bootstrap, validation, packaging, utility scripts
├─ .env.example
├─ AGENTS.md
├─ CHANGE_LOG.md
├─ docker-compose.yml
├─ ProjectVision.md
├─ README.md
└─ SYSTEM_INVENTORY.md
````

### Backend Runtime Domains

```text
backend/
├─ app/
│  ├─ api/
│  │  ├─ dependencies.py             # route dependencies and shared request wiring
│  │  ├─ routes/
│  │  │  ├─ diagnostics.py           # diagnostics and health-facing endpoints
│  │  │  ├─ health.py                # health endpoints
│  │  │  ├─ session.py               # session-facing APIs
│  │  │  ├─ task.py                  # normal conversation/task APIs
│  │  │  └─ voice.py                 # voice-facing APIs
│  │  └─ schemas/
│  │     ├─ common.py                # shared API schemas
│  │     ├─ session.py               # session schemas
│  │     ├─ task.py                  # task schemas
│  │     └─ voice.py                 # voice schemas
│  ├─ artifacts/
│  │  ├─ session_artifact.py         # session artifact definitions
│  │  ├─ storage.py                  # artifact persistence helpers
│  │  ├─ trace_writer.py             # trace writing utilities
│  │  └─ turn_artifact.py            # canonical turn artifact definitions
│  ├─ cache/                         # cache code layer (access, policy, client); distinct from top-level cache/ data directory
│  │  ├─ manager.py                  # cache access layer
│  │  ├─ policies.py                 # cache policy rules
│  │  ├─ redis_client.py             # redis integration
│  │  └─ keys.py                     # cache key naming and namespaces
│  ├─ cognition/
│  │  ├─ executor.py                 # deterministic execution coordination
│  │  ├─ planner.py                  # planning logic
│  │  ├─ policies.py                 # cognition policies
│  │  ├─ prompt_assembler.py         # prompt assembly with personality/context inputs
│  │  └─ responder.py                # response shaping logic
│  ├─ conversation/
│  │  ├─ engine.py                   # turn lifecycle orchestration
│  │  ├─ interruption.py             # interruption/barge-in handling
│  │  ├─ session_manager.py          # session lifecycle management
│  │  ├─ states.py                   # canonical conversation states
│  │  └─ turn_manager.py             # turn creation/update/finalization
│  ├─ core/
│  │  ├─ capabilities.py             # normalized capability and profile types
│  │  ├─ errors.py                   # core error types
│  │  ├─ logging.py                  # logging setup
│  │  ├─ paths.py                    # canonical filesystem paths
│  │  └─ settings.py                 # environment/app settings
│  ├─ hardware/
│  │  ├─ detectors/
│  │  │  ├─ cpu_detector.py          # CPU detection
│  │  │  ├─ cuda_detector.py         # CUDA detection
│  │  │  ├─ gpu_detector.py          # GPU detection
│  │  │  ├─ memory_detector.py       # memory detection
│  │  │  ├─ npu_detector.py          # NPU detection
│  │  │  └─ os_detector.py           # OS/platform detection
│  │  ├─ profiler.py                 # main callable hardware profiler
│  │  └─ profile_resolver.py         # maps detector facts to additive hardware profile manifests/readiness inputs
│  ├─ memory/
│  │  ├─ episodic.py                 # episodic memory implementation
│  │  ├─ manager.py                  # memory coordination layer
│  │  ├─ retrieval.py                # retrieval logic
│  │  ├─ semantic.py                 # semantic memory implementation
│  │  ├─ write_policy.py             # memory write policies
│  │  └─ working.py                  # working memory implementation
│  ├─ personality/
│  │  ├─ adapter.py                  # applies personality to cognition/response layers
│  │  ├─ loader.py                   # loads personality profiles
│  │  ├─ resolver.py                 # resolves active personality for runtime/session
│  │  └─ schema.py                   # structured personality schema
│  ├─ routing/
│  │  ├─ capability_router.py        # routes work from capability flags
│  │  ├─ model_registry.py           # model/provider catalog access
│  │  └─ runtime_selector.py         # chooses concrete runtime/provider
│  ├─ runtimes/
│  │  ├─ llm/
│  │  │  ├─ base.py                  # common LLM runtime interface
│  │  │  ├─ claude_runtime.py        # anthropic escalation runtime
│  │  │  ├─ gemini_runtime.py        # google escalation runtime
│  │  │  ├─ local_runtime.py         # local/default LLM runtime
│  │  │  ├─ openai_runtime.py        # openai escalation runtime
│  │  │  ├─ xai_runtime.py           # xAI escalation runtime
│  │  │  └─ zai_runtime.py           # Z.AI escalation runtime
│  │  ├─ search/
│  │  │  ├─ base.py                  # common search runtime interface
│  │  │  ├─ ddgs_runtime.py          # DuckDuckGo search escalation runtime
│  │  │  ├─ local_runtime.py         # bundled/local search runtime if present
│  │  │  ├─ searxng_runtime.py       # SearXNG search escalation runtime
│  │  │  └─ tavily_runtime.py        # Tavily search escalation runtime
│  │  ├─ stt/
│  │  │  ├─ base.py                  # common STT runtime interface
│  │  │  ├─ local_runtime.py         # local/default STT runtime
│  │  │  └─ stt_runtime.py           # generic STT runtime adapter slot
│  │  ├─ tts/
│  │  │  ├─ base.py                  # common TTS runtime interface
│  │  │  ├─ local_runtime.py         # local/default TTS runtime
│  │  │  └─ tts_runtime.py           # generic TTS runtime adapter slot
│  │  └─ wake/
│  │     ├─ base.py                  # common wake runtime interface
│  │     ├─ local_runtime.py         # local/default wake runtime
│  │     └─ wakeword_runtime.py      # generic wake-word runtime adapter slot
│  ├─ services/
│  │  ├─ diagnostics_service.py      # diagnostics-facing service layer
│  │  ├─ session_service.py          # session service layer
│  │  ├─ task_service.py             # host-facing task/text service slot (delegates to canonical turn execution)
│  │  ├─ turn_service.py             # canonical transcript-bound turn executor shared by voice/text paths
│  │  └─ voice_service.py            # voice-facing service layer
│  └─ tools/
│     ├─ filesystem/                 # filesystem tools
│     ├─ registry.py                 # tool registry
│     ├─ search/                     # internal/bundled search tools
│     └─ system/                     # system tools
├─ tests/
│  ├─ fixtures/                      # shared test fixtures
│  ├─ integration/                   # integration tests
│  ├─ runtime/                       # live/runtime-oriented tests
│  └─ unit/                          # unit tests
├─ Dockerfile
├─ pyproject.toml
└─ requirements.txt
```

### Config Domains

```text
config/
├─ app/
│  ├─ defaults.yaml                  # global defaults
│  ├─ policies.yaml                  # safety, fallback, escalation, execution policies
│  └─ profiles.yaml                  # runtime profiles derived from capability flags
├─ cache/
│  ├─ redis.yaml                     # redis cache config
│  └─ policies.yaml                  # cache TTL / eviction / namespace policy
├─ models/
│  ├─ llm.yaml                       # LLM catalog and selection config
│  ├─ models.yaml                    # top-level model registry catalog
│  ├─ search.yaml                    # search runtime/provider config
│  ├─ stt.yaml                       # STT runtime/model config
│  ├─ tts.yaml                       # TTS runtime/model config
│  └─ wake.yaml                      # wake-word runtime config
├─ personality/
│  ├─ concise.yaml                   # concise personality profile
│  ├─ default.yaml                   # runtime personality overlay/tuning profile
│  ├─ jarvis_personality.json        # canonical identity/persona source
│  └─ warm.yaml                      # warm personality profile
└─ prompts/
   ├─ planner/                       # planner prompt assets
   ├─ responder/                     # responder prompt assets
   └─ system/                        # system prompt assets
```

### Mutable Runtime Domains

```text
cache/                               # mutable data only; no source code lives here
├─ redis/                            # local redis persistence and dev data
└─ temp/                             # cache-related temp outputs

data/
├─ memory/
│  ├─ episodic/                      # episodic memory data
│  ├─ semantic/                      # semantic memory data
│  └─ working/                       # working memory data
├─ sessions/                         # session artifacts and persisted state
├─ temp/                             # runtime temp files
└─ turns/                            # turn artifacts

reports/
├─ benchmarks/                       # benchmark outputs
├─ diagnostics/                      # diagnostics outputs
└─ validation/                       # validation reports
```
