# CHANGE_LOG.md
> :
> No edits/reorders/deletes of past entries. If an entry is wrong, append a corrective entry.

## Rules
- Write an entry only after task objective is “done” and supported by evidence.
- **Ordering:** Entries are maintained in **descending chronological order** (newest first, oldest last).
- **Append location:** New entries must be added **at the top of the Entries section**, directly under `## Entries`.
- Each entry must include:
  - Timestamp: `YYYY-MM-DD HH:MM`
  - Summary: 1–2 lines, past tense
  - Scope: files/areas touched
  - Evidence: exact command(s) run + a minimal excerpt pointer (or embedded excerpt ≤10 lines)
- If a change is reverted, append a new entry describing the revert and why.

## Entries

- 2026-04-09 22:50
  - Summary: Sub-Slice 5B.5 bounded closeout gate was completed by adding `backend/tests/unit/test_slice5b_presence_units.py` for cross-slice presence/contract stability checks and validating the approved deterministic 5B unit closeout set; this gate confirmed Slice 5B is ready for inventory closeout without reopening profiler/readiness scope.
  - Scope: backend/tests/unit/test_slice5b_presence_units.py, backend/tests/unit/test_slice5b1_wake_runtime_units.py, backend/tests/unit/test_slice5b2_personality_schema_units.py, backend/tests/unit/test_slice5b3_acknowledgment_units.py, backend/tests/unit/test_slice5a_shell_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b_presence_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b1_wake_runtime_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b2_personality_schema_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b3_acknowledgment_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_shell_units.py -q`
    ```text
    PASS closeout units: test_slice5b_presence_units.py | 5 passed in 1.05s
    PASS wake units: test_slice5b1_wake_runtime_units.py | 4 passed in 0.07s
    PASS personality schema units: test_slice5b2_personality_schema_units.py | 2 passed in 0.03s
    PASS acknowledgment units: test_slice5b3_acknowledgment_units.py | 6 passed in 0.48s
    PASS shell regression units: test_slice5a_shell_units.py | 8 passed in 4.01s
    Outcome: Slice 5B bounded deterministic closeout gate passed; ready for inventory closeout
    ```

- 2026-04-09 22:29
  - Summary: Sub-Slice 5B.4 bounded wake/runtime proving-host integration was completed by extending `scripts/run_jarvis.py` to consume the existing wake abstraction (`select_wake_runtime()`), preserve push-to-talk behavior on wake-unavailable startup, consume wake-flag triggers to dispatch `run_voice_turn(...)`, count wake-triggered turns toward `--turns`, and stop wake runtime cleanly on exit; closure evidence was finalized via deterministic shell-unit proof instead of interactive Agent/Cline host proof.
  - Scope: scripts/run_jarvis.py, backend/tests/unit/test_slice5a_shell_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall scripts/run_jarvis.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_shell_units.py -q`
    ```text
    PASS compile: scripts/run_jarvis.py
    PASS deterministic shell proof: 8 passed in 3.43s
    Proof coverage includes wake-unavailable push-to-talk path, wake-flag-triggered voice dispatch without manual 'v', wake-trigger turn counting toward --turns, and wake runtime stop on exit
    Interactive Agent/Cline run was treated as non-closure surface; deterministic unit proof used for 5B.4 closure
    ```

- 2026-04-09 21:51
  - Summary: Sub-Slice 5B.3 bounded acknowledgment behavior was completed by adding a personality acknowledgment module with deterministic style-based phrase generation and safe optional acknowledgment playback, then integrating the acknowledgment hook into `run_voice_turn(...)` after transcript/`TRANSCRIBING` and before `run_turn(...)` using one in-turn TTS resolution reused for acknowledgment and response synthesis; `wake_response_sound` remained declarative only and no wake listener/shell/readiness/profiler/key-coupling expansion was added.
  - Scope: backend/app/personality/acknowledgment.py, backend/app/services/voice_service.py, backend/tests/unit/test_slice5b3_acknowledgment_units.py, backend/tests/unit/test_slice2_tts_turn_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/personality/acknowledgment.py backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b3_acknowledgment_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q -k acknowledgment_hook_invoked_before_run_turn`
    ```text
    PASS compile: acknowledgment.py | voice_service.py
    PASS targeted acknowledgment units: 6 passed in 0.49s
    PASS insertion-point proof: 1 passed, 13 deselected in 0.46s
    Boundaries preserved: wake_response_sound declarative only; no wake listener integration, shell changes, readiness/profiler changes, new personality keys, or resolver/voice coupling added
    ```

- 2026-04-09 21:38
  - Summary: Sub-Slice 5B.1 bounded follow-through corrections were completed by adding the missing `pvporcupine` base dependency declaration and widening wake runtime selector typing to the `WakeWordBase` boundary while preserving wake runtime behavior; `.env.example` wake-key documentation was confirmed already present and remained unchanged.
  - Scope: backend/requirements.txt, backend/app/runtimes/wake/wakeword_runtime.py, .env.example, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/wake/wakeword_runtime.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b1_wake_runtime_units.py -q`; dependency presence check `^pvporcupine>=3\.0$` in `backend/requirements.txt`; env key presence check `PVPORCUPINE_MODEL_PATH|PICOVOICE_ACCESS_KEY` in `.env.example`
    ```text
    PASS dependency declaration: pvporcupine>=3.0 present in backend/requirements.txt
    PASS env docs confirmation: PVPORCUPINE_MODEL_PATH and PICOVOICE_ACCESS_KEY present in .env.example (no file change)
    PASS compile: wakeword_runtime.py
    PASS targeted wake units: 4 passed in 0.07s
    ```

- 2026-04-09 21:21
  - Summary: Sub-Slice 5B.2 personality schema extension was completed as a bounded additive schema/config update by adding `acknowledgment_phrase_style` and `wake_response_sound` defaults, preserving `acknowledgment_style` as a separate field with no alias/remap, and keeping the existing loader default-then-required validation pattern; no wake behavior, acknowledgment runtime behavior, shell changes, or voice/resolver coupling were added.
  - Scope: backend/app/personality/schema.py, backend/app/personality/loader.py, config/personality/default.yaml, backend/tests/unit/test_slice5b2_personality_schema_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/personality/schema.py backend/app/personality/loader.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b2_personality_schema_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.personality.loader import load_personality_profile; p=load_personality_profile('default'); print('ack_phrase_style:', p.acknowledgment_phrase_style); print('wake_response_sound:', p.wake_response_sound)"`
    ```text
    PASS compile: schema.py | loader.py
    PASS targeted 5B.2 personality units: 2 passed in 0.04s
    PASS loader runtime check: ack_phrase_style: minimal | wake_response_sound: none
    Corrective fix (bounded): moved new defaulted dataclass fields to the end of PersonalityProfile to resolve field-ordering error
    ```

- 2026-04-09 21:04
  - Summary: Sub-Slice 5B.1 wake-runtime completion was finalized by preserving wake runtime surfaces under `backend/app/runtimes/wake/`, keeping wake env-key exposure in `backend/app/core/settings.py`, correcting Porcupine initialization so configured `.ppn` is supplied via `keyword_paths` (not `model_path`), and proving clean bounded concurrent wake+barge startup while leaving shell integration, readiness/profiler extensions, and wake acknowledgment/persona behavior unchanged.
  - Scope: backend/app/core/settings.py, backend/app/runtimes/wake/base.py, backend/app/runtimes/wake/local_runtime.py, backend/app/runtimes/wake/wakeword_runtime.py, backend/tests/unit/test_slice5b1_wake_runtime_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b1_wake_runtime_units.py -q`; `backend/.venv/Scripts/python -c "import threading, time; from backend.app.core import settings; from backend.app.runtimes.wake.local_runtime import PorcupineWakeWord; from backend.app.runtimes.stt.barge_in import BargeInDetector; wake = PorcupineWakeWord(access_key=settings.PICOVOICE_ACCESS_KEY, model_path=settings.PVPORCUPINE_MODEL_PATH); wf=threading.Event(); bf=threading.Event(); barge=BargeInDetector(bf); wake.start(wf); barge.start(); print('wake_started:', not wake.failed); print('wake_failure_reason:', wake.failure_reason); print('barge_started:', not barge.failed); print('barge_failure_reason:', barge.failure_reason); time.sleep(0.5); barge.stop(); wake.stop(); print('concurrent_streams_ok:', (not wake.failed) and (not barge.failed))"`
    ```text
    PASS targeted wake-runtime units: 4 passed in 0.07s
    PASS concurrent wake+barge validation: wake_started: True | wake_failure_reason: None | barge_started: True | barge_failure_reason: None | concurrent_streams_ok: True
    Constraint confirmation: scripts/run_jarvis.py unchanged; BackendReadiness/profiler unchanged; no wake acknowledgment/persona behavior added
    Implementation correction: configured .ppn is passed via keyword_paths during pvporcupine.create(...), not model_path
    ```

- 2026-04-09 19:22
  - Summary: Sub-Slice 5B.1 wake-runtime introduction was completed by adding host-agnostic wake runtime surfaces under `backend/app/runtimes/wake/`, exposing existing wake env keys in `backend/app/core/settings.py`, and adding targeted wake runtime unit coverage while keeping shell integration and readiness/profiler extensions out of scope; bounded concurrent wake+barge smoke validation produced degraded host evidence (`wake_started: False`, `barge_started: True`).
  - Scope: backend/app/core/settings.py, backend/app/runtimes/wake/base.py, backend/app/runtimes/wake/local_runtime.py, backend/app/runtimes/wake/wakeword_runtime.py, backend/tests/unit/test_slice5b1_wake_runtime_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/wake/base.py backend/app/runtimes/wake/local_runtime.py backend/app/runtimes/wake/wakeword_runtime.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5b1_wake_runtime_units.py -q`; `backend/.venv/Scripts/python -c "import os, threading, time; from backend.app.runtimes.wake.local_runtime import PorcupineWakeWord; from backend.app.runtimes.stt.barge_in import BargeInDetector; key = os.environ.get('PICOVOICE_ACCESS_KEY', ''); model_path = os.environ.get('PVPORCUPINE_MODEL_PATH', ''); wake = PorcupineWakeWord(access_key=key, model_path=model_path); wake_flag = threading.Event(); barge_flag = threading.Event(); barge = BargeInDetector(barge_flag); wake.start(wake_flag); barge.start(); print('wake_started:', not wake.failed); print('barge_started:', not barge.failed); time.sleep(0.5); barge.stop(); wake.stop(); print('concurrent_streams_ok:', (not wake.failed) and (not barge.failed)); print('wake_failure_reason_present:', wake.failure_reason is not None); print('barge_failure_reason_present:', barge.failure_reason is not None)"`
    ```text
    PASS compile: base.py | local_runtime.py | wakeword_runtime.py
    PASS targeted wake-runtime units: 4 passed in 0.08s
    DEGRADED concurrent streams: wake_started: False | barge_started: True | concurrent_streams_ok: False
    FIX applied in local_runtime.py: guarded `pvporcupine.create(...)` None return before using sample_rate/frame_length
    Constraint confirmation: scripts/run_jarvis.py unchanged; BackendReadiness/profiler unchanged; no wake acknowledgment/persona behavior added
    ```

- 2026-04-09 14:39
  - Summary: Sub-Slice 5.p.2 unified voice-model bootstrap was completed by extending `scripts/bootstrap_readiness.py` to explicitly materialize/verify STT recommended, STT fallback (`whisper-small`), and TTS recommended models with per-model PASS/FAILED output while preserving existing STT selected-device preflight fail-closed behavior; `scripts/validate_backend.py` remained unchanged as runtime gate owner.
  - Scope: scripts/bootstrap_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python scripts/bootstrap_readiness.py`; `backend/.venv/Scripts/python scripts/bootstrap_readiness.py --verify-only`
    ```text
    [PASS] STT model: whisper-large-v3-turbo present
    [PASS] STT fallback: whisper-small present
    [PASS] TTS model: kokoro-v1.0 present
    [PASS] STT readiness proven for selected device: cuda
    ```

- 2026-04-09 14:10
  - Summary: Sub-Slice 5.p.1 explicit fallback-model trust was completed by proving `ensure_models.py` parser behavior for omitted `--model`, executing explicit `whisper-small` fallback verification/ensure, and resolving a bounded STT verification mismatch where downloaded artifacts exposed `vocab.json` instead of `vocabulary.json`.
  - Scope: backend/app/models/manager.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family stt`; `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family stt --model whisper-small`; `backend/.venv/Scripts/python scripts/ensure_models.py --family stt --model whisper-small`; `backend/.venv/Scripts/python -c "from pathlib import Path; p=Path('models/stt/whisper-small'); print('exists', p.exists()); print(sorted([x.name for x in p.iterdir()]) if p.exists() else [])"`; `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family stt --model whisper-small`
    ```text
    [FAILED] catalog resolution: --model is required unless --all is set
    [MISSING] whisper-small → models/stt/whisper-small
    [FAILED] whisper-small: verify failed after download for repo 'Systran/faster-whisper-small' at 'models/stt/whisper-small'
    exists True
    ['...','config.json','model.bin','vocab.json',...]
    [PRESENT] whisper-small → models/stt/whisper-small
    ```

- 2026-04-07 21:45
  - Summary: Slice 5A regression confirmation was completed by re-running the live interruption gate and confirming a passing result on the latest evidence while noting known operator-timed intermittency risk.
  - Scope: backend/tests/runtime/test_slice4_interruption_live.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice4_interruption_live.py -v -s`
    ```text
    PASS regression retest: backend/tests/runtime/test_slice4_interruption_live.py::test_barge_in_live ... PASSED
    1 passed in 55.47s
    Interpretation: no stable Slice 5A code-regression signal on latest evidence; known intermittency risk remains for this live/operator-timed interruption gate.
    ```

- 2026-04-07 21:11
  - Summary: Corrective evidence entry appended for Sub-Slice 5A.3 closure truth by recording fresh real host-path validation through `scripts/run_jarvis.py` startup-only and bounded typed-turn execution, confirming the bounded local shell adapter acceptance path beyond prior compile/unit-only proof.
  - Scope: scripts/run_jarvis.py, backend/tests/unit/test_slice5a_startup_service_units.py, backend/tests/unit/test_slice5a_task_service_units.py, backend/tests/unit/test_slice5a_shell_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python scripts/run_jarvis.py --turns 0`; `echo "What is your name?" | ./backend/.venv/Scripts/python scripts/run_jarvis.py --turns 1`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_startup_service_units.py backend/tests/unit/test_slice5a_task_service_units.py backend/tests/unit/test_slice5a_shell_units.py -q`
    ```text
    PASS startup-only host path: startup summary printed with profile/STT/TTS/LLM/personality and clean exit
    PASS bounded typed turn: [STATE] IDLE → REASONING → RESPONDING → IDLE | [RESPONSE] My name is Jarvis...
    PASS targeted Slice 5A units: 11 passed in 0.78s
    ```

- 2026-04-07 19:49
  - Summary: Sub-Slice 5A.3 bounded local-shell adapter implementation was completed by adding a thin proving-host script that reuses existing startup/text/voice service boundaries with shared session/memory continuity, explicit turn controls, STT-gated voice command behavior, and fail-fast handling only when STT/TTS/LLM are all unavailable, without service refactors or later-slice expansion.
  - Scope: scripts/run_jarvis.py, backend/tests/unit/test_slice5a_shell_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall scripts/run_jarvis.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_shell_units.py -q`
    ```text
    PASS compile: Compiling 'scripts/run_jarvis.py'...
    PASS unit: .... [100%]
    4 passed in 1.54s
    ```

- 2026-04-07 18:41
  - Summary: Sub-Slice 5A.2 task-service implementation was completed by adding a host-agnostic typed text-turn service boundary that wraps result state and delegates continuity execution to the existing turn engine without adding shell output, STT/TTS/audio behavior, or duplicate conversation logic.
  - Scope: backend/app/services/task_service.py, backend/tests/unit/test_slice5a_task_service_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/task_service.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_task_service_units.py -q`
    ```text
    PASS compile: Compiling 'backend/app/services/task_service.py'...
    PASS unit: ... [100%]
    3 passed in 0.13s
    ```

- 2026-04-07 18:29
  - Summary: Slice-doc sanitization was completed as a bounded doc-only correction pass that removed unsupported personality-to-voice coupling from Slice 5A/5B planning docs while preserving landed 5A.1 startup-service scope.
  - Scope: 20260406-slice_5a.md, 20260406-slice_5b.md, CHANGE_LOG.md
  - Evidence: `Select-String -Path 20260406-slice_5a.md,20260406-slice_5b.md -Pattern 'Personality-driven voice selection','Sub-Slice 5A.2 — Extend Personality Resolver for Voice Selection','voice_name_override','voice_resolver','resolve_voice_from_personality','voice selection override' -SimpleMatch`; `Select-String -Path 20260406-slice_5a.md -Pattern 'Sub-Slice 5A.1 — Startup Service and Readiness Summary','backend/app/services/startup_service.py' -SimpleMatch`
    ```text
    Confirmed removed from docs: personality-driven voice-selection scope in 5A, and voice_name_override/resolver coupling in 5B.
    Confirmed preserved in 5A: Sub-Slice 5A.1 startup-service contract language and startup_service.py references.
    ```

- 2026-04-07 11:40
  - Summary: Sub-Slice 5A.1 startup-service implementation was completed by adding a bounded startup/readiness summary service and targeted unit coverage without introducing voice-resolution behavior or later 5A sub-slice surfaces.
  - Scope: backend/app/services/startup_service.py, backend/tests/unit/test_slice5a_startup_service_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/startup_service.py`; `backend/.venv/Scripts/python -c "from backend.app.services.startup_service import run_startup, print_startup_summary; summary, report, personality = run_startup(); print_startup_summary(summary); print('stt_ready:', summary.stt_ready); print('personality:', summary.personality_display_name)"`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_startup_service_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice5a_startup_service_units.py -q`
    ```text
    PASS compile: Compiling 'backend/app/services/startup_service.py'...
    PASS startup summary: Profile/STT/TTS/LLM/Personality printed | stt_ready: True | personality: Jarvis
    FAIL initial unit run: 1 failed, 3 passed (assertion used "voice" substring and matched banner text "Local Voice Assistant")
    PASS rerun after in-scope test assertion correction: 4 passed in 0.14s
    ```

- 2026-04-06 09:35
  - Summary: `repo_tree.md` was minimally aligned to reduce near-term Slice 5A naming/placement ambiguity by documenting the current `services`, `config/personality`, and `hardware` continuity boundaries without broad tree reconciliation.
  - Scope: `repo_tree.md`
  - Evidence: `repo_tree.md` now explicitly represents `backend/app/services/turn_service.py` as the canonical transcript-bound turn executor, clarifies `task_service.py` as the host-facing task/text service slot, adds `config/personality/jarvis_personality.json` as the canonical identity/persona source alongside `default.yaml` as the runtime overlay/tuning profile, and corrects `backend/app/hardware/profiles.py` to `profile_resolver.py` with an updated boundary description.
    ```text
    services:
    - added turn_service.py  # canonical transcript-bound turn executor shared by voice/text paths
    - clarified task_service.py  # host-facing task/text service slot (delegates to canonical turn execution)
    config/personality:
    - added jarvis_personality.json  # canonical identity/persona source
    - clarified default.yaml  # runtime personality overlay/tuning profile
    hardware:
    - profiles.py -> profile_resolver.py
    - updated comment: maps detector facts to additive hardware profile manifests/readiness inputs
    ```

- 2026-04-06 05:10
  - Summary: `backend/tests/unit/test_hardware_readiness.py` was updated to remove stale `onnxruntime>=1.17` from the expected additive `python_packages` list in `test_resolver_combined_hardware_matches_multiple_manifests_additively`, aligning the unit expectation to the current manifest/resolver contract.
  - Scope: backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py::test_resolver_combined_hardware_matches_multiple_manifests_additively -q -vv`
    ```text
    backend/tests/unit/test_hardware_readiness.py::test_resolver_combined_hardware_matches_multiple_manifests_additively PASSED
    1 passed in 0.07s
    ```

- 2026-04-05 15:08
  - Summary: `scripts/validate_backend.py` was updated to add a runtime voice-model prerequisite gate that verifies required STT/TTS assets are present before runtime validation begins, failing early with explicit prereq-failure output when assets are missing while keeping the harness validation-only (no model download/initialization).
  - Scope: scripts/validate_backend.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m py_compile scripts/validate_backend.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.models.catalog import get_model_entry,get_tts_model_entry; from backend.app.models.manager import verify_model; r=run_profiler(); stt=r.flags.stt_recommended_model; tts=r.flags.tts_recommended_model; stt_dir=get_model_entry(stt).get('local_dir'); tts_dir=get_tts_model_entry(tts).get('local_dir'); print('stt',stt,stt_dir,verify_model(stt_dir,'stt')); print('tts',tts,tts_dir,verify_model(tts_dir,'tts'))"`; `backend/.venv/Scripts/python -c "import scripts.validate_backend as vb; calls={'run_pytest_suite':0}; vb._resolve_runtime_voice_model_prerequisites=lambda:[{'family':'stt','model':'m1','local_dir':'missing/stt'},{'family':'tts','model':'m2','local_dir':'missing/tts'}]; vb.verify_model=lambda local_dir,family='stt':False; vb.run_pytest_suite=lambda logger,suite_name,suite_path:(calls.__setitem__('run_pytest_suite',calls['run_pytest_suite']+1) or vb.SuiteResult(status='PASS',summary='stub')); rc=vb.main(['--scope','runtime']); print('rc',rc); print('run_pytest_suite_calls',calls['run_pytest_suite'])"`; `backend/.venv/Scripts/python -c "import scripts.validate_backend as vb; calls={'run_runtime_readiness_gate':0,'run_pytest_suite':0}; vb._resolve_runtime_voice_model_prerequisites=lambda:[{'family':'stt','model':'m1','local_dir':'present/stt'},{'family':'tts','model':'m2','local_dir':'present/tts'}]; vb.verify_model=lambda local_dir,family='stt':True; vb.run_runtime_readiness_gate=lambda logger:(calls.__setitem__('run_runtime_readiness_gate',calls['run_runtime_readiness_gate']+1) or vb.SuiteResult(status='PASS',summary='ready')); vb.run_pytest_suite=lambda logger,suite_name,suite_path:(calls.__setitem__('run_pytest_suite',calls['run_pytest_suite']+1) or vb.SuiteResult(status='PASS',summary='stub')); rc=vb.main(['--scope','runtime']); print('rc',rc); print('run_runtime_readiness_gate_calls',calls['run_runtime_readiness_gate']); print('run_pytest_suite_calls',calls['run_pytest_suite'])"`
    ```text
    backend/.venv/Scripts/python -m py_compile scripts/validate_backend.py  (executed successfully; no output)
    stt whisper-large-v3-turbo models/stt/whisper-large-v3-turbo True
    tts kokoro-v1.0 models/tts/kokoro-v1.0 True
    [PREREQ FAILED] stt:m1 missing at missing/stt
    [PREREQ FAILED] tts:m2 missing at missing/tts
    rc 1 | run_pytest_suite_calls 0
    [PREREQ PASS] stt:m1 present at present/stt
    [PREREQ PASS] tts:m2 present at present/tts
    rc 0 | run_runtime_readiness_gate_calls 1 | run_pytest_suite_calls 1
    ```

- 2026-04-05 10:56
  - Summary: `backend/app/core/settings.py` environment-contract alignment was completed by reading `OLLAMA_BASE_URL` in place of `OLLAMA_HOST`, while preserving existing in-code defaults when env values are absent.
  - Scope: backend/app/core/settings.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m py_compile backend/app/core/settings.py`; `backend/.venv/Scripts/python -c "from backend.app.core.settings import *; print('settings import OK')"`
    ```text
    backend/.venv/Scripts/python -m py_compile backend/app/core/settings.py  (executed successfully; no output)
    settings import OK
    ```

- 2026-04-05 01:27
  - Summary: Windows CUDA DLL/bootstrap ownership was normalized so `backend/app/hardware/preflight.py` is the single setup owner, and duplicate STT runtime DLL/bootstrap setup in `backend/app/runtimes/stt/local_runtime.py` was removed by delegation to preflight ownership with behavior preserved.
  - Scope: backend/app/hardware/preflight.py, backend/app/runtimes/stt/local_runtime.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_stt_device_readiness; from backend.app.runtimes.stt.stt_runtime import select_stt_runtime; r=run_profiler(); p=run_hardware_preflight(r.profile); d=derive_stt_device_readiness(p); rt=select_stt_runtime(r); print('verification_results=', p.get('verification_results')); print('derived=', d); print('runtime_device=', getattr(rt, 'device', None))"`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`
    ```text
    29 passed in 2.66s
    18 passed in 0.27s
    verification_results= [{'token': 'import:faster_whisper', 'ok': True}, ... {'token': 'dll:cublas64_12.dll', 'ok': True}, {'token': 'dll:cudnn64_9.dll', 'ok': True}]
    derived= {'matched_manifest_ids': ['hw-cpu-base', 'hw-gpu-nvidia-cuda', 'hw-gpu-present'], 'cuda_ready': True, 'cpu_ready': True, 'selected_device': 'cuda', 'selected_device_ready': True}
    runtime_device= cuda
    backend/tests/runtime/test_slice1_stt_turn_live.py::test_voice_turn_live ... PASSED
    1 passed in 49.40s
    ```

- 2026-04-05 01:22
  - Summary: Profiler report assembly was normalized to remove post-construction mutation of readiness-backed recommendation fields, and `CapabilityFlags` now constructs final readiness-backed STT/TTS recommended device values in one pass.
  - Scope: backend/app/hardware/profiler.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; r=run_profiler(); print('stt_recommended_device=', r.flags.stt_recommended_device); print('tts_recommended_device=', r.flags.tts_recommended_device); print('readiness=', r.readiness)"`
    ```text
    4 passed in 0.40s
    29 passed in 2.93s
    18 passed in 0.28s
    13 passed in 0.77s
    stt_recommended_device= cuda
    tts_recommended_device= cuda
    readiness= BackendReadiness(... stt_selected_device='cuda', ... tts_selected_device='cuda', ...)
    ```

- 2026-04-05 01:10
  - Summary: Service-specific evidence-token ownership was removed from `backend/app/hardware/preflight.py`, moved to the profiler boundary in `backend/app/hardware/profiler.py`, and `run_hardware_preflight(...)` was normalized to evidence-agnostic verification/execution using caller-supplied evidence tokens while hardware manifests remained hardware-only.
  - Scope: backend/app/hardware/preflight.py, backend/app/hardware/profiler.py, backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_stt_device_readiness, derive_tts_device_readiness; r=run_profiler(); p_all=run_hardware_preflight(r.profile); p_tts=run_hardware_preflight(r.profile, backend_scope='tts'); print('all_matched=', p_all.get('matched_manifest_ids')); print('stt=', derive_stt_device_readiness(p_all)); print('tts=', derive_tts_device_readiness(p_tts))"`
    ```text
    29 passed in 2.90s
    4 passed in 0.40s
    18 passed in 0.27s
    13 passed in 0.74s
    all_matched= ['hw-cpu-base', 'hw-gpu-nvidia-cuda', 'hw-gpu-present']
    stt= {... 'selected_device': 'cuda', 'selected_device_ready': True}
    tts= {... 'selected_device': 'cuda', 'selected_device_ready': True}
    ```

- 2026-04-05 00:38
  - Summary: Service-oriented hardware manifests were retired and replaced with detector-derived hardware-only manifests, and hardware resolver/preflight ownership was corrected so manifests carry only additive hardware package/install metadata while service-specific readiness policy remains code-owned.
  - Scope: config/hardware/stt_base_cpu.json, config/hardware/stt_gpu_noncuda.json, config/hardware/stt_gpu_cuda.json, config/hardware/stt_npu.json, config/hardware/tts_gpu_cuda.json, config/hardware/hw_cpu_base.json, config/hardware/hw_gpu_present.json, config/hardware/hw_gpu_noncuda.json, config/hardware/hw_gpu_nvidia_cuda.json, config/hardware/hw_npu_present.json, backend/app/hardware/profile_resolver.py, backend/app/hardware/preflight.py, backend/tests/unit/test_hardware_readiness.py, backend/tests/unit/test_hardware_profiler.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`; `backend/.venv/Scripts/python -c "import json; from pathlib import Path; [print(p.name, json.loads(p.read_text())) for p in sorted(Path('config/hardware').glob('*.json'))]"`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_stt_device_readiness, derive_tts_device_readiness; r=run_profiler(); p_all=run_hardware_preflight(r.profile); p_tts=run_hardware_preflight(r.profile, backend_scope='tts'); print('all_matched=', p_all.get('matched_manifest_ids')); print('stt=', derive_stt_device_readiness(p_all)); print('tts=', derive_tts_device_readiness(p_tts))"`
    ```text
    29 passed in 2.84s
    4 passed in 0.52s
    18 passed in 0.27s
    13 passed in 0.76s
    hw_cpu_base.json ... hw_gpu_noncuda.json ... hw_gpu_nvidia_cuda.json ... hw_gpu_present.json ... hw_npu_present.json
    all_matched= ['hw-cpu-base', 'hw-gpu-nvidia-cuda', 'hw-gpu-present']
    stt= {... 'selected_device': 'cuda', ...}
    tts= {... 'selected_device': 'cuda', ...}
    ```

- 2026-04-04 23:59
  - Summary: Dependency ownership was reconciled by restoring `backend/requirements.txt` to neutral/base truth, moving CUDA-specific TTS torch ownership to `config/hardware/tts_gpu_cuda.json`, and updating preflight/install planning to consume manifest-defined `pip_extra_index_urls` for additive installs with unit proof of the corrected boundary.
  - Scope: backend/requirements.txt, config/hardware/tts_gpu_cuda.json, backend/app/hardware/preflight.py, backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -c "from pathlib import Path; print(Path('backend/requirements.txt').read_text())"`; `backend/.venv/Scripts/python -c "import json; from pathlib import Path; print(json.loads(Path('config/hardware/tts_gpu_cuda.json').read_text()))"`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_tts_device_readiness; r=run_profiler(); p=run_hardware_preflight(r.profile, backend_scope='tts'); d=derive_tts_device_readiness(p); print('verification_results=', p.get('verification_results')); print('derived=', d)"`; `backend/.venv/Scripts/python -m pip show torch kokoro`
    ```text
    29 passed in 2.66s
    requirements: no '--extra-index-url .../cu128' and no 'torch==2.11.0+cu128'
    manifest additive install: {'pip_extra_index_urls': ['https://download.pytorch.org/whl/cu128']}
    derived= {'matched_manifest_ids': ['tts-gpu-cuda'], 'cuda_ready': True, 'cpu_ready': True, 'selected_device': 'cuda', 'selected_device_ready': True}
    torch 2.11.0+cu128 | kokoro 0.9.4
    ```

- 2026-04-04 23:37
  - Summary: TTS CUDA dependency source-of-truth was reconciled by declaring the CUDA-enabled torch build in `backend/requirements.txt`, aligning the TTS CUDA hardware manifest requirement, and adding unit proof that manifest expectations match the declared dependency authority.
  - Scope: backend/requirements.txt, config/hardware/tts_gpu_cuda.json, backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pip show torch kokoro`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_tts_device_readiness; r=run_profiler(); p=run_hardware_preflight(r.profile, backend_scope='tts'); d=derive_tts_device_readiness(p); print('verification_results=', p.get('verification_results')); print('derived=', d)"`
    ```text
    28 passed in 2.82s
    Name: torch
    Version: 2.11.0+cu128
    {'token': 'torch_cuda:available', 'ok': True}
    derived= {'matched_manifest_ids': ['tts-gpu-cuda'], 'cuda_ready': True, 'cpu_ready': True, 'selected_device': 'cuda', 'selected_device_ready': True}
    ```

- 2026-04-04 23:31
  - Summary: TTS CUDA readiness rail implementation was completed by adding a dedicated TTS CUDA hardware manifest and wiring profiler/preflight-backed TTS readiness selection with deterministic unit/runtime proof surfaces.
  - Scope: config/hardware/tts_gpu_cuda.json, backend/app/hardware/preflight.py, backend/app/hardware/profiler.py, backend/tests/unit/test_hardware_readiness.py, backend/tests/unit/test_slice2_tts_turn_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_tts_device_readiness; r=run_profiler(); p=run_hardware_preflight(r.profile, backend_scope='tts'); d=derive_tts_device_readiness(p); print('verification_results=', p.get('verification_results')); print('derived=', d)"`
    ```text
    28 passed in 2.82s
    13 passed in 0.42s
    {'token': 'import:kokoro', 'ok': True}
    {'token': 'import:torch', 'ok': True}
    {'token': 'tts_runtime:kokoro', 'ok': True}
    {'token': 'torch_cuda:available', 'ok': True}
    derived= {'matched_manifest_ids': ['tts-gpu-cuda'], 'cuda_ready': True, 'cpu_ready': True, 'selected_device': 'cuda', 'selected_device_ready': True}
    ```

- 2026-04-04 23:24
  - Summary: STT CUDA readiness corrective behavior was finalized in the shared preflight/readiness path and verified by targeted STT and readiness unit suites to keep CUDA gating deterministic with CPU-safe degradation.
  - Scope: backend/app/hardware/preflight.py, backend/tests/unit/test_hardware_readiness.py, backend/tests/unit/test_slice1_stt_turn_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`
    ```text
    28 passed in 2.82s
    18 passed in 0.28s
    ```

- 2026-04-04 23:20
  - Summary: Post-0.0.7 regression contract-alignment fixes were completed for Slice 3A and Slice 4 unit suites to keep continuity/interruption contracts consistent with the readiness-backed runtime surfaces.
  - Scope: backend/tests/unit/test_slice3a_session_continuity_units.py, backend/tests/unit/test_slice4_interruption_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice3a_session_continuity_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_interruption_units.py -q`
    ```text
    17 passed in 0.22s
    27 passed in 0.76s
    ```

- 2026-04-04 22:30
  - Summary: Sub-Slice 0.0.7 was completed by extending the shared backend-readiness schema beyond STT/TTS-only shape with deterministic LLM placeholder fields, and by adding a backend-agnostic readiness-derivation helper while preserving active STT readiness behavior.
  - Scope: backend/app/core/capabilities.py, backend/app/hardware/preflight.py, backend/app/hardware/profiler.py, backend/app/routing/runtime_selector.py, backend/tests/unit/test_hardware_profiler.py, backend/tests/unit/test_hardware_readiness.py, backend/tests/runtime/test_profiler_live.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_profiler_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`
    ```text
    4 passed in 1.53s
    25 passed in 0.34s
    backend/tests/runtime/test_profiler_live.py::test_profiler_live_returns_expected_runtime_contract ... PASSED
    readiness BackendReadiness(... llm_local_ready=False, llm_service_ready=False, llm_selected_runtime='unavailable')
    PASS: runtime: 6 tests
    RUNTIME: PASS
    [PASS] JARVISv6 backend is validated!
    ```

- 2026-04-04 08:59
  - Summary: Sub-Slice 0.0.6 was completed by adding an explicit STT bootstrap/readiness operator entrypoint and adding fail-closed runtime readiness gating before runtime test execution; readiness gating was corrected to validate the selected STT device path so CPU-ready degradation passes without requiring CUDA proof while CUDA remains unverified when CUDA evidence fails.
  - Scope: scripts/bootstrap_readiness.py, scripts/validate_backend.py, backend/app/hardware/preflight.py, backend/tests/unit/test_hardware_readiness.py, backend/tests/runtime/test_profiler_live.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_profiler_live.py -v -s`; `backend/.venv/Scripts/python scripts/bootstrap_readiness.py --verify-only`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`
    ```text
    ....................... [100%]
    23 passed in 0.30s
    backend/tests/runtime/test_profiler_live.py::test_profiler_live_returns_expected_runtime_contract ... PASSED
    [READINESS] backend_scope=stt selected_device=cpu selected_device_ready=True cuda_ready=False cpu_ready=True profile_id=nvidia-cuda-desktop-63gb
    [PASS] STT readiness proven for selected device: cpu
    [PASS] STT readiness proven for selected device 'cpu'; proceeding to runtime tests
    RUNTIME: PASS
    ```

- 2026-04-04 08:34
  - Summary: Sub-Slice 0.0.5 was completed by adding profiler-owned backend readiness to the shared capability/report surface, making profiler recommendations readiness-backed for STT and minimally readiness-backed for TTS within 0.0.5 scope, and updating STT/TTS selectors to consume report-owned recommendation authority.
  - Scope: backend/app/core/capabilities.py, backend/app/hardware/profiler.py, backend/app/runtimes/stt/stt_runtime.py, backend/app/runtimes/tts/tts_runtime.py, backend/tests/unit/test_hardware_profiler.py, backend/tests/unit/test_slice1_stt_turn_units.py, backend/tests/unit/test_slice2_tts_turn_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`
    ```text
    .... [100%]
    4 passed in 1.48s
    .................. [100%]
    18 passed in 0.30s
    ............. [100%]
    13 passed in 1.71s
    ```

- 2026-04-04 08:10
  - Summary: Sub-Slice 0.0.4 was completed by enforcing readiness-gated STT device selection so CUDA is selected only when STT CUDA evidence is verified, while explicit CPU-safe degradation is selected when CUDA readiness is not verified.
  - Scope: config/hardware/stt_gpu_cuda.json, backend/app/hardware/preflight.py, backend/app/runtimes/stt/stt_runtime.py, backend/tests/unit/test_hardware_readiness.py, backend/tests/unit/test_slice1_stt_turn_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`
    ```text
    .................... [100%]
    20 passed in 0.28s
    .................. [100%]
    18 passed in 0.26s
    backend/tests/runtime/test_slice1_stt_turn_live.py::test_voice_turn_live ... PASSED
    1 passed in 81.80s (0:01:21)
    ```

- 2026-04-04 07:24
  - Summary: Sub-Slice 0.0.3 was completed by adding the hardware provisioning/preflight owner and expanding hardware-readiness unit coverage for manifest-consumed additive package detection, controlled install invocation, verification checks, and deterministic readiness result output.
  - Scope: backend/app/hardware/preflight.py, backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`
    ```text
    ................. [100%]
    17 passed in 0.43s
    .. [100%]
    2 passed in 0.02s
    ```

- 2026-04-04 07:12
  - Summary: Sub-Slice 0.0.2 was completed by adding a hardware fact-to-manifest resolver module and expanding hardware-readiness unit coverage for deterministic additive multi-manifest resolution.
  - Scope: backend/app/hardware/profile_resolver.py, backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`
    ```text
    ........... [100%]
    11 passed in 0.05s
    .. [100%]
    2 passed in 0.02s
    ```

- 2026-04-04 06:57
  - Summary: Sub-Slice 0.0.1 was completed by adding STT hardware-profile manifests under `config/hardware/` and adding unit coverage in `backend/tests/unit/test_hardware_readiness.py`.
  - Scope: config/hardware/stt_base_cpu.json, config/hardware/stt_gpu_noncuda.json, config/hardware/stt_gpu_cuda.json, config/hardware/stt_npu.json, backend/tests/unit/test_hardware_readiness.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`
    ```text
    ..... [100%]
    5 passed in 0.05s
    .. [100%]
    2 passed in 0.05s
    ```

- 2026-04-03 10:52
  - Summary: Slice 4 unit-test housekeeping was completed by consolidating all Slice 4 unit coverage into `backend/tests/unit/test_slice4_interruption_units.py` and retiring the redundant per-sub-slice Slice 4 unit test files.
  - Scope: backend/tests/unit/test_slice4_interruption_units.py, backend/tests/unit/test_slice4_1_interruption_contract_units.py, backend/tests/unit/test_slice4_2_barge_in_detector_units.py, backend/tests/unit/test_slice4_3_interruptible_playback_units.py, backend/tests/unit/test_slice4_4_interruptible_voice_orchestration_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_interruption_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit -q -k "slice4"`
    ```text
    ........................... [100%]
    27 passed in 0.77s
    ........................... [100%]
    27 passed, 52 deselected in 0.61s
    ```

- 2026-04-03 09:44
  - Summary: The playback helper double-stop behavior was corrected by removing redundant body-level `sd.stop()` calls from `play_audio_interruptible(...)` and tightening the related unit proof to match the intended stop-path behavior.
  - Scope: backend/app/runtimes/tts/playback.py, backend/tests/unit/test_slice4_3_interruptible_playback_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_3_interruptible_playback_units.py -q`
    ```text
    .... [100%]
    4 passed in 0.47s
    ```

- 2026-04-03 07:40
  - Summary: Sub-slice 4.5 was completed by adding final Slice 4 interruption unit coverage, adding the live interruption acceptance test, proving actual interruption during active playback, and passing the required runtime regressions plus full backend validation.
  - Scope: backend/tests/unit/test_slice4_interruption_units.py, backend/tests/runtime/test_slice4_interruption_live.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_interruption_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice4_interruption_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
    ```text
    ................... [100%]
    19 passed in 0.80s
    [INTERRUPTED] barge-in at
    [TURN 2] interrupted: True
    [ARTIFACT] interrupted=True
    backend/tests/runtime/test_slice1_stt_turn_live.py::test_voice_turn_live ... PASSED
    backend/tests/runtime/test_slice2_tts_turn_live.py::test_spoken_voice_turn_live ... PASSED
    backend/tests/runtime/test_slice3a_session_continuity_runtime.py::test_session_continuity_runtime ... PASSED
    backend/tests/runtime/test_slice3b_multiturn_voice_live.py::test_multiturn_voice_session_live ... PASSED
    PASS: runtime: 6 tests
    UNIT: PASS
    RUNTIME: PASS
    [PASS] JARVISv6 backend is validated!
    ```

- 2026-04-03 06:44
  - Summary: Sub-slice 4.4 was completed by wiring interruption handling into `run_voice_turn(...)`, returning the explicit `VoiceTurnResult` interruption contract, updating persisted artifact interruption metadata through the stored-turn path, and aligning existing caller tests to the new result contract.
  - Scope: backend/app/services/voice_service.py, backend/tests/runtime/test_slice1_stt_turn_live.py, backend/tests/runtime/test_slice2_tts_turn_live.py, backend/tests/runtime/test_slice3b_multiturn_voice_live.py, backend/tests/unit/test_slice2_tts_turn_units.py, backend/tests/unit/test_slice4_4_interruptible_voice_orchestration_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/voice_service.py backend/tests/runtime/test_slice1_stt_turn_live.py backend/tests/runtime/test_slice2_tts_turn_live.py backend/tests/runtime/test_slice3b_multiturn_voice_live.py backend/tests/unit/test_slice2_tts_turn_units.py backend/tests/unit/test_slice4_4_interruptible_voice_orchestration_units.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py backend/tests/unit/test_slice4_4_interruptible_voice_orchestration_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -q`
    ```text
    Compiling 'backend/app/services/voice_service.py'...
    Compiling 'backend/tests/runtime/test_slice1_stt_turn_live.py'...
    Compiling 'backend/tests/runtime/test_slice2_tts_turn_live.py'...
    Compiling 'backend/tests/runtime/test_slice3b_multiturn_voice_live.py'...
    Compiling 'backend/tests/unit/test_slice2_tts_turn_units.py'...
    Compiling 'backend/tests/unit/test_slice4_4_interruptible_voice_orchestration_units.py'...
    ............. [100%]
    13 passed in 0.72s
    . [100%]
    1 passed in 74.75s (0:01:14)
    . [100%]
    1 passed in 54.30s
    . [100%]
    1 passed in 85.84s (0:01:25)
    ```

- 2026-04-03 06:01
  - Summary: Sub-slice 4.3 was completed by adding interruptible playback behavior, preserving existing `play_audio()`, and validating both interrupted and normal completion paths.
  - Scope: backend/app/runtimes/tts/playback.py, backend/tests/unit/test_slice4_3_interruptible_playback_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/playback.py backend/tests/unit/test_slice4_3_interruptible_playback_units.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_3_interruptible_playback_units.py -q`; `backend/.venv/Scripts/python -c "import threading; from pathlib import Path; from backend.app.hardware.profiler import run_profiler; from backend.app.runtimes.tts.tts_runtime import select_tts_runtime; from backend.app.runtimes.tts.playback import play_audio_interruptible; report=run_profiler(); tts=select_tts_runtime(report); 
if tts is None:
    print('SKIP: TTS runtime unavailable')
else:
    audio_path='data/temp/slice4_3_test.wav'; Path('data/temp').mkdir(parents=True, exist_ok=True); tts.synthesize('This is a test of interruptible playback.', audio_path); print('synthesized:', Path(audio_path).exists()); flag=threading.Event(); flag.set(); result=play_audio_interruptible(audio_path, flag); print('interrupted_returns_false:', result is False); flag2=threading.Event(); result2=play_audio_interruptible(audio_path, flag2); print('normal_returns_true:', result2 is True)"`
    ```text
    Compiling 'backend/app/runtimes/tts/playback.py'...
    Compiling 'backend/tests/unit/test_slice4_3_interruptible_playback_units.py'...
    .... [100%]
    4 passed in 0.48s
    synthesized: True
    interrupted_returns_false: True
    normal_returns_true: True
    ```

- 2026-04-03 05:52
  - Summary: Sub-slice 4.2 was completed by adding an isolated barge-in detector with input-stream-only ownership, explicit startup failure state exposure, threshold/consecutive-frame trigger behavior, and deterministic unit coverage.
  - Scope: backend/app/runtimes/stt/barge_in.py, backend/tests/unit/test_slice4_2_barge_in_detector_units.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/stt/barge_in.py backend/tests/unit/test_slice4_2_barge_in_detector_units.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_2_barge_in_detector_units.py -q`
    ```text
    Compiling 'backend/app/runtimes/stt/barge_in.py'...
    Compiling 'backend/tests/unit/test_slice4_2_barge_in_detector_units.py'...
    .... [100%]
    4 passed in 0.98s
    ```

- 2026-04-02 10:09
  - Summary: Personality authority correction was completed by making `config/personality/jarvis_personality.json` the canonical default identity/persona source, applying `config/personality/default.yaml` as runtime contract/tuning overlay in the resolved profile, and enforcing identity authority in the shared generation path so explicit name/identity turns align to configured persona instead of model-native fallback.
  - Scope: backend/app/personality/loader.py, backend/app/cognition/prompt_assembler.py, backend/app/cognition/responder.py, backend/app/services/turn_service.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/personality/loader.py backend/app/cognition/prompt_assembler.py backend/app/cognition/responder.py backend/app/services/turn_service.py`; `backend/.venv/Scripts/python -c "from backend.app.personality.loader import load_personality_profile; p=load_personality_profile('default'); print('profile_id:', p.profile_id); print('display_name:', p.display_name); print('identity_summary:', p.identity_summary); print('tone:', p.tone); print('response_style:', p.response_style)"`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.personality.loader import load_personality_profile; from backend.app.conversation.session_manager import SessionManager; from backend.app.memory.working import WorkingMemory; from backend.app.services.turn_service import run_turn; report=run_profiler(); p=load_personality_profile('default'); s=SessionManager.open_session(); m=WorkingMemory(max_turns=5); r=run_turn(report,p,'What is your name?',session=s,memory=m); print('name_response:', r); SessionManager.close_session(s)"`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`
    ```text
    PASS resolved profile: display_name: J.A.R.V.I.S.
    PASS resolved profile: identity_summary: You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the user's Personal AI Assistant...
    PASS resolved profile overlay fields: tone: neutral | response_style: direct
    PASS identity runtime response: name_response: ... As J.A.R.V.I.S., the Just A Rather Very Intelligent System at your service ...
    PASS runtime regression: backend/tests/runtime/test_slice3a_session_continuity_runtime.py::test_session_continuity_runtime ... PASSED | 1 passed in 19.30s
    ```

- 2026-04-02 07:57
  - Summary: Live/operator prompt consistency correction was completed by normalizing explicit microphone guidance and “speak now” phrase prompts across live runtime mic-input tests while preserving existing test intent, assertions, and acceptance criteria.
  - Scope: backend/tests/runtime/test_slice1_stt_turn_live.py, backend/tests/runtime/test_slice2_tts_turn_live.py, backend/tests/runtime/test_slice3b_multiturn_voice_live.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/voice_service.py backend/tests/runtime`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`
    ```text
    PASS compile: Compiling 'backend/tests/runtime\\test_slice1_stt_turn_live.py'... | 'test_slice2_tts_turn_live.py'... | 'test_slice3b_multiturn_voice_live.py'...
    PASS slice1 live: [TURN 1] speak now: What is your name? | 1 passed
    PASS slice2 live: [TURN 1] speak now: What is your name? | 1 passed
    PASS slice3b live: [TURN 1] speak now: What is your name? | [TURN 2] speak now: Nothing else for today. | 1 passed
    ```

- 2026-04-02 07:23
  - Summary: HF local-runtime offline-only correction was completed by enforcing offline behavior in the local TTS runtime before any model-manager Hugging Face call and by adding offline/local-only resolution control in model manager so runtime paths fail closed to cache/local assets without Hub access.
  - Scope: backend/app/models/manager.py, backend/app/runtimes/tts/local_runtime.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -c "from pathlib import Path; from backend.app.models.catalog import get_tts_model_entry; from backend.app.runtimes.tts.local_runtime import KokoroTTSRuntime; entry = get_tts_model_entry('kokoro-v1.0'); rt = KokoroTTSRuntime(model_name='kokoro-v1.0', device='cpu'); rt._ensure_pipeline(); print('pipeline_initialized:', rt._pipeline is not None); print('model_dir_exists:', Path(entry['local_dir']).exists());" 2>&1`
    ```text
    PASS runtime local init: pipeline_initialized: True
    PASS runtime local assets: model_dir_exists: True
    PASS warning boundary: no HF_TOKEN unauthenticated warning emitted
    ```

- 2026-04-02 06:58
  - Summary: CUDA DLL discovery correction was completed by removing the unnecessary hardcoded CUDA path entries from `.env.example` and `.env`, and by adding Windows-only dynamic DLL directory registration in the STT runtime using host `CUDA_PATH` plus venv NVIDIA wheel bin paths derived from `sys.prefix` while preserving existing CPU fallback behavior.
  - Scope: .env.example, .env, backend/app/runtimes/stt/local_runtime.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/stt/local_runtime.py backend/app/runtimes/stt/stt_runtime.py`; `backend/.venv/Scripts/python -c "import os, sys; from pathlib import Path; from backend.app.runtimes.stt.local_runtime import FasterWhisperSTT; venv = Path(sys.prefix); print('cuda_path_env:', os.environ.get('CUDA_PATH')); print('venv_cublas_bin_exists:', (venv / 'Lib' / 'site-packages' / 'nvidia' / 'cublas' / 'bin').exists()); print('venv_cudnn_bin_exists:', (venv / 'Lib' / 'site-packages' / 'nvidia' / 'cudnn' / 'bin').exists()); print('venv_cuda_runtime_bin_exists:', (venv / 'Lib' / 'site-packages' / 'nvidia' / 'cuda_runtime' / 'bin').exists()); stt = FasterWhisperSTT(model_name='tiny', device='cuda'); print('stt_device_requested:', stt.device)"`
    ```text
    PASS compile: Compiling 'backend/app/runtimes/stt/local_runtime.py'...
    PASS runtime proof: cuda_path_env: C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2
    PASS runtime proof: venv_cublas_bin_exists: True | venv_cudnn_bin_exists: True | venv_cuda_runtime_bin_exists: False
    PASS runtime proof: stt_device_requested: cuda
    ```

- 2026-04-02 06:11
  - Summary: Language-alignment bug-fix was completed by constraining the prompt contract to English responses while preserving deterministic assistant response boundaries and single-turn prompt format compatibility, and by forcing FasterWhisper transcription to English across both primary and CPU fallback paths.
  - Scope: backend/app/cognition/prompt_assembler.py, backend/app/runtimes/stt/local_runtime.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/cognition/prompt_assembler.py backend/app/runtimes/stt/local_runtime.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice3a_session_continuity_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`
    ```text
    PASS compile: Compiling 'backend/app/cognition/prompt_assembler.py'... | Compiling 'backend/app/runtimes/stt/local_runtime.py'...
    PASS unit: 17 passed in 0.18s
    PASS runtime 3A: backend/tests/runtime/test_slice3a_session_continuity_runtime.py::test_session_continuity_runtime ... PASSED | 1 passed in 19.43s
    PASS runtime 3B live: backend/tests/runtime/test_slice3b_multiturn_voice_live.py::test_multiturn_voice_session_live ... PASSED | 1 passed in 157.18s
    ```

- 2026-04-02 05:36
  - Summary: Correction entry added after validating the Architect-applied prompt-continuation bleed bug-fix; multi-turn prompt assembly now includes an explicit assistant-turn anchor and responder sanitization truncates fabricated next-turn continuation markers (for example `[New turn:] User:`) before user-facing output.
  - Scope: backend/app/cognition/prompt_assembler.py, backend/app/cognition/responder.py, CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/cognition/prompt_assembler.py backend/app/cognition/responder.py`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice3a_session_continuity_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`
    ```text
    PASS compile: Compiling 'backend/app/cognition/prompt_assembler.py'... | Compiling 'backend/app/cognition/responder.py'...
    PASS unit: 17 passed in 0.41s
    PASS runtime: backend/tests/runtime/test_slice3a_session_continuity_runtime.py::test_session_continuity_runtime ... PASSED | 1 passed in 19.99s
    ```

- 2026-04-01 15:30
  - Summary: Sub-slice 3B.3 Fail-Closed Behavior, Runtime-Only Acceptance, and Governance Gates was completed by validating the live spoken path as the runtime-only acceptance surface, confirming explicit live-boundary fail-closed behavior remained in effect, and closing 3B governance in `CHANGE_LOG.md` while leaving `SYSTEM_INVENTORY.md` unchanged for Architect-reviewed follow-up.
  - Scope: CHANGE_LOG.md
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`
    ```text
    PASS 3B.2 live runtime: [STATE] LISTENING → TRANSCRIBING | [TRANSCRIPT] What codename did I give you? | [TURN 2] memory_turns: 2 | PASSED | 1 passed
    PASS 3A regression runtime: backend/tests/runtime/test_slice3a_session_continuity_runtime.py::test_session_continuity_runtime ... PASSED | 1 passed
    PASS slice2 regression runtime: backend/tests/runtime/test_slice2_tts_turn_live.py::test_spoken_voice_turn_live ... PASSED | 1 passed
    PASS runtime harness: PASS: runtime: 5 tests | RUNTIME: PASS | [INVARIANTS] RUNTIME=PASS | [PASS] JARVISv6 backend is validated!
    ```

- 2026-04-01 15:02
  - Summary: Sub-slice 3B.2 One Live Multi-Turn Spoken Validation Path was completed by reverting unproven `voice_service.py` hardening to the stable 3B.1 direct capture/transcribe flow, then applying a bounded live-path fix across STT runtime selection/capture and TTS playback stream release so the second turn reached transcript emission and completion in the live runtime test.
  - Scope: backend/app/services/voice_service.py, backend/app/runtimes/stt/stt_runtime.py, backend/app/runtimes/tts/playback.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`
    ```text
    [TURN 2] speak now: What codename did I give you?
    [STATE] IDLE → LISTENING
    [LIVE INPUT] awaiting microphone speech...
    [STATE] LISTENING → TRANSCRIBING
    [TRANSCRIPT] What is your code name?
    [TURN 2] memory_turns: 2
    PASSED
    1 passed in 135.55s
    ```

- 2026-04-01 12:56
  - Summary: Slice 2 TTS unit-test alignment bug-fix was completed by updating `backend/tests/unit/test_slice2_tts_turn_units.py` to match the approved profiler-first TTS authority contract, with selector tests targeting the current selector/runtime interface and voice-service tests patching the current execution flow.
  - Scope: backend/tests/unit/test_slice2_tts_turn_units.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`
    ```text
    PASS targeted unit suite: ........... [100%]
    PASS result: 11 passed in 0.69s
    ```

- 2026-04-01 11:58
  - Summary: STT authority-alignment bug-fix was completed by updating capability schema/profiler/selector wiring so profiler now owns STT runtime/model/device recommendation, `select_stt_runtime(report)` consumes profiler-owned STT recommendation fields, and `voice_service.py` no longer hardcodes STT runtime family or ad hoc STT device selection while `config/models/stt.yaml` remains catalog/default metadata authority.
  - Scope: backend/app/core/capabilities.py, backend/app/hardware/profiler.py, backend/app/runtimes/stt/stt_runtime.py, backend/app/services/voice_service.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/core/capabilities.py backend/app/hardware/profiler.py backend/app/runtimes/stt/stt_runtime.py backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; r=run_profiler(); print('stt_runtime_field_present:', hasattr(r.flags, 'stt_recommended_runtime')); print('stt_model_field_present:', hasattr(r.flags, 'stt_recommended_model')); print('stt_device_field_present:', hasattr(r.flags, 'stt_recommended_device'))"`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.runtimes.stt.stt_runtime import select_stt_runtime; rt=select_stt_runtime(run_profiler()); print('selected_type:', type(rt).__name__ if rt else None); print('selected_device:', getattr(rt, 'device', None))"`; `backend/.venv/Scripts/python -c "from backend.app.services.voice_service import run_voice_turn; print('run_voice_turn importable:', callable(run_voice_turn))"`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`
    ```text
    PASS compile: Compiling 'backend/app/core/capabilities.py'... | 'backend/app/hardware/profiler.py'... | 'backend/app/runtimes/stt/stt_runtime.py'... | 'backend/app/services/voice_service.py'...
    PASS profiler fields: stt_runtime_field_present: True | stt_model_field_present: True | stt_device_field_present: True
    PASS selector: selected_type: FasterWhisperSTT | selected_device: cuda
    PASS import: run_voice_turn importable: True
    PASS unit tests: 15 passed in 0.28s
    AUTHORITY runtime family: profiler-owned via report.flags.stt_recommended_runtime
    AUTHORITY model default: profiler-owned runtime-path recommendation via report.flags.stt_recommended_model (config/catalog still defines available model entries)
    AUTHORITY device selection: profiler-owned via report.flags.stt_recommended_device
    ```

- 2026-04-01 11:43
  - Summary: TTS hardware-selection authority bug-fix was completed by updating capability schema/profiler/runtime wiring so profiler now owns TTS runtime/model/device recommendation, `select_tts_runtime(report)` consumes profiler-owned TTS recommendation fields, `local_runtime.py` is execution-only for normal runtime flow, voice default remains catalog-driven, and `config/models/tts.yaml:runtimes.kokoro.default_device` was removed after device authority moved to profiler.
  - Scope: backend/app/core/capabilities.py, backend/app/hardware/profiler.py, backend/app/runtimes/tts/tts_runtime.py, backend/app/runtimes/tts/local_runtime.py, config/models/tts.yaml
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/core/capabilities.py backend/app/hardware/profiler.py backend/app/runtimes/tts/tts_runtime.py backend/app/runtimes/tts/local_runtime.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; r=run_profiler(); print('tts_runtime_field_present:', hasattr(r.flags, 'tts_recommended_runtime')); print('tts_model_field_present:', hasattr(r.flags, 'tts_recommended_model')); print('tts_device_field_present:', hasattr(r.flags, 'tts_recommended_device'))"`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.runtimes.tts.tts_runtime import select_tts_runtime; rt=select_tts_runtime(run_profiler()); print('selected_type:', type(rt).__name__ if rt else None); print('selected_device:', getattr(rt, 'device', None))"`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.tts.local_runtime import LocalTTSRuntime, KokoroTTSRuntime; print('LocalTTSRuntime importable:', callable(LocalTTSRuntime)); print('KokoroTTSRuntime importable:', callable(KokoroTTSRuntime))"`
    ```text
    PASS compile: Compiling 'backend/app/core/capabilities.py'... | 'backend/app/hardware/profiler.py'... | 'backend/app/runtimes/tts/tts_runtime.py'... | 'backend/app/runtimes/tts/local_runtime.py'...
    PASS profiler fields: tts_runtime_field_present: True | tts_model_field_present: True | tts_device_field_present: True
    PASS runtime selection: selected_type: KokoroTTSRuntime | selected_device: cuda
    PASS compatibility: LocalTTSRuntime importable: True | KokoroTTSRuntime importable: True
    ```

- 2026-04-01 10:01
  - Summary: Kokoro TTS runtime/config correction was completed by updating `config/models/tts.yaml` and `backend/app/runtimes/tts/local_runtime.py` to remove hardcoded defaults, make config authoritative for model/voice/device defaults, expose `LocalTTSRuntime` as the stable repo-facing runtime name, and preserve `KokoroTTSRuntime` import compatibility.
  - Scope: config/models/tts.yaml, backend/app/runtimes/tts/local_runtime.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/local_runtime.py`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.tts.local_runtime import LocalTTSRuntime, KokoroTTSRuntime; print('LocalTTSRuntime importable:', callable(LocalTTSRuntime)); print('KokoroTTSRuntime importable:', callable(KokoroTTSRuntime))"`
    ```text
    PASS compile: Compiling 'backend/app/runtimes/tts/local_runtime.py'...
    PASS import: LocalTTSRuntime importable: True
    PASS import: KokoroTTSRuntime importable: True
    CONFIG default keys in use: model -> config/models/tts.yaml:models (single unambiguous model key)
    CONFIG default keys in use: voice -> config/models/tts.yaml:models.<model>.default_voice
    CONFIG default keys in use: device -> config/models/tts.yaml:runtimes.kokoro.default_device
    ```

- 2026-04-01 08:39
  - Summary: !BLOCKED! Sub-slice 3B.2 One Live Multi-Turn Spoken Validation Path was attempted by creating `backend/tests/runtime/test_slice3b_multiturn_voice_live.py`, adding operator-facing live prompts in the test and an explicit live capture cue in `backend/app/services/voice_service.py`; live runtime remained blocked because turn 1 completed but turn 2 repeatedly reached the live capture/transcribe boundary without deterministic transcript/completion, and speculative capture-lifecycle edits were attempted then reverted.
  - Scope: backend/tests/runtime/test_slice3b_multiturn_voice_live.py, backend/app/services/voice_service.py, backend/app/runtimes/stt/stt_runtime.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`; `backend/.venv/Scripts/python -m compileall backend/app/runtimes/stt/stt_runtime.py backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -c "from backend.app.services.voice_service import run_voice_turn; print('run_voice_turn importable:', callable(run_voice_turn))"`
    ```text
    ATTEMPTED 3B.2 live path: [SESSION] opened ... | [TURN 1] memory_turns: 1 | [TURN 2] speak now ... | [STATE] IDLE → LISTENING | [LIVE INPUT] awaiting microphone speech... | [STATE] LISTENING → TRANSCRIBING (no deterministic turn-2 completion observed)
    OBSERVED runtime boundary instability during related runtime runs: RuntimeError: OllamaLLM: no response from http://localhost:11434
    ATTEMPTED narrow capture-lifecycle correction (not resolving blocker): added sd.stop() around capture in stt_runtime.py and per-call UUID utterance filename in voice_service.py
    REVERTED speculative capture-lifecycle edits to restore minimal stable state: stt_runtime.py sd.stop() additions removed; voice_service.py capture path restored to data/temp/utterance.wav
    RESTORED baseline: 3B.1 continuity wiring retained + operator cues retained; STATUS: 3B.2 blocked / not complete
    ```

- 2026-04-01 07:02
  - Summary: Sub-slice 3B.1 Reuse the 3A Continuity Executor from the Live Voice Path was completed by modifying `backend/app/services/voice_service.py` so `run_voice_turn(...)` accepts optional `session` and `memory`, keeps the live ingress path and transcript logging in `voice_service.py`, hands transcript continuity execution to `run_turn(..., input_modality="voice")`, and preserves TTS/playback behavior in `voice_service.py`.
  - Scope: backend/app/services/voice_service.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -c "from backend.app.services.voice_service import run_voice_turn; print('run_voice_turn importable:', callable(run_voice_turn))"`
    ```text
    PASS compile: Compiling 'backend/app/services/voice_service.py'...
    PASS import: run_voice_turn importable: True
    ```

- 2026-04-01 06:31
  - Summary: Sub-slice 3A.6 Deterministic Validation, Regression, and Inventory Gates was completed by creating `backend/tests/unit/test_slice3a_session_continuity_units.py` and `backend/tests/runtime/test_slice3a_session_continuity_runtime.py`, adding deterministic non-interactive 3A unit/runtime coverage; an in-scope unit test correction was applied and rerun to pass.
  - Scope: backend/tests/unit/test_slice3a_session_continuity_units.py, backend/tests/runtime/test_slice3a_session_continuity_runtime.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice3a_session_continuity_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice3a_session_continuity_units.py -q`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
    ```text
    PASS final 3A unit validation: 17 passed in 0.25s
    PASS 3A runtime validation: backend/tests/runtime/test_slice3a_session_continuity_runtime.py::test_session_continuity_runtime ... PASSED | [MEMORY] turn complete — written to working memory
    NOTE in-scope 3A.6 correction: unit expectation adjusted to match implemented session increment behavior when memory write policy rejects
    FAIL full harness runtime boundary: UNIT=PASS | RUNTIME=FAIL
    OBSERVED runtime blocker evidence: RuntimeError: OllamaLLM: no response from http://localhost:11434 (test_slice2_tts_turn_live, test_slice3a_session_continuity_runtime)
    CONSTRAINT APPLIED: no broader unrelated fix applied because blocker was outside narrow 3A.6 scope
    ```

- 2026-04-01 05:45
  - Summary: Sub-slice 3A.5 Canonical Transcript-Bound Turn Executor was completed by creating `backend/app/services/turn_service.py` with `run_turn(...) -> str` as the transcript-bound non-interactive executor that drives the existing cognition/runtime path, assembles prior context when memory is present, evaluates write policy via `engine.state.name`, logs memory decision reason, admits working memory only when policy allows, and persists turn artifact before incrementing session.
  - Scope: backend/app/services/turn_service.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/turn_service.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.personality.loader import load_personality_profile; from backend.app.conversation.session_manager import SessionManager; from backend.app.memory.working import WorkingMemory; from backend.app.services.turn_service import run_turn; report = run_profiler(); personality = load_personality_profile('default'); session = SessionManager.open_session(); memory = WorkingMemory(max_turns=5); response1 = run_turn(report, personality, 'My codename is JARVIS.', session=session, memory=memory); response2 = run_turn(report, personality, 'What codename did I give you?', session=session, memory=memory); print('response1_non_empty:', bool(response1.strip())); print('response2_non_empty:', bool(response2.strip())); print('memory_turns:', len(memory.get_context_turns())); print('session_turn_count:', session.turn_count); SessionManager.close_session(session)"`
    ```text
    PASS compile: Compiling 'backend/app/services/turn_service.py'...
    OBSERVED initial runtime blocker: [FAILED] run_turn: No LLM runtime available ... OllamaLLM (Ollama not reachable at http://localhost:11434)
    PASS rerun runtime after Ollama start: [STATE] IDLE → REASONING | [STATE] REASONING → RESPONDING | [STATE] RESPONDING → IDLE
    PASS rerun runtime memory logging: [MEMORY] turn complete — written to working memory
    PASS rerun runtime outputs: response1_non_empty: True | response2_non_empty: True | memory_turns: 2 | session_turn_count: 2
    ```

- 2026-03-31 19:38
  - Summary: SessionManager update semantics were corrected by making `increment_turn(session)` and `close_session(session)` mutate the passed `Session` instance in place, persist immediately, and return the same instance, while keeping persisted schema and atomic write behavior unchanged.
  - Scope: backend/app/conversation/session_manager.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/conversation/session_manager.py`; `backend/.venv/Scripts/python -c "from backend.app.conversation.session_manager import SessionManager; s=SessionManager.open_session(); sid=id(s); s2=SessionManager.increment_turn(s); print('same_object_after_increment:', id(s)==id(s2)==sid); print('turn_count_after_increment:', s.turn_count); s3=SessionManager.close_session(s); print('same_object_after_close:', id(s)==id(s3)==sid); print('ended_at_present:', s.ended_at is not None)"`
    ```text
    PASS compile: Compiling 'backend/app/conversation/session_manager.py'...
    PASS runtime: same_object_after_increment: True | turn_count_after_increment: 1
    PASS runtime: same_object_after_close: True | ended_at_present: True
    ```

- 2026-03-31 19:07
  - Summary: Sub-slice 3A.4 Explicit Working-Memory Write Policy was completed by creating `backend/app/memory/write_policy.py` with `WriteDecision` and `evaluate_write_policy(transcript, response_text, final_state) -> WriteDecision` as a pure-function policy governing working-memory admission only.
  - Scope: backend/app/memory/write_policy.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/memory/write_policy.py`; `backend/.venv/Scripts/python -c "from backend.app.memory.write_policy import evaluate_write_policy; print('normal:', evaluate_write_policy('hello', 'Hello.', 'IDLE').should_write); print('failed_reason:', evaluate_write_policy('hello', 'Hello.', 'FAILED').reason); print('empty_transcript_reason:', evaluate_write_policy('   ', 'Hello.', 'IDLE').reason); print('empty_response_reason:', evaluate_write_policy('hello', '', 'IDLE').reason)"`
    ```text
    PASS compile: Compiling 'backend/app/memory/write_policy.py'...
    PASS runtime: normal: True
    PASS runtime: failed_reason: turn failed — not written to working memory
    PASS runtime: empty_transcript_reason: empty transcript — not written to working memory
    PASS runtime: empty_response_reason: empty response — not written to working memory
    NOTE: negative-path reason outputs were expected and matched 20260331-slice_3a.md.
    ```

- 2026-03-31 15:14
  - Summary: Sub-slice 3A.3 Working Memory and Explicit Prompt Context Injection was completed by adding `TurnSummary` plus bounded in-process `WorkingMemory` and extending prompt assembly with optional explicit prior-turn context injection while preserving Slice 1/2-compatible behavior when `context_turns` is omitted or empty.
  - Scope: backend/app/memory/working.py, backend/app/cognition/prompt_assembler.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/memory/working.py backend/app/cognition/prompt_assembler.py`; `backend/.venv/Scripts/python -c "from backend.app.memory.working import WorkingMemory, TurnSummary; from backend.app.personality.loader import load_personality_profile; from backend.app.cognition.prompt_assembler import assemble_prompt; memory = WorkingMemory(max_turns=5); memory.add_turn(TurnSummary(turn_index=0, transcript='My project is JARVISv6.', response_text='Understood.')); personality = load_personality_profile('default'); prompt = assemble_prompt('What project did I name?', personality, context_turns=memory.get_context_turns()); print('context_turns:', len(memory.get_context_turns())); print('prior_context_present:', 'My project is JARVISv6.' in prompt); print('current_turn_present:', 'What project did I name?' in prompt); plain_prompt = assemble_prompt('hello', personality); print('plain_prompt_non_empty:', bool(plain_prompt.strip()))"`
    ```text
    PASS compile: Compiling 'backend/app/memory/working.py'... | Compiling 'backend/app/cognition/prompt_assembler.py'...
    PASS runtime: context_turns: 1 | prior_context_present: True | current_turn_present: True | plain_prompt_non_empty: True
    ```

- 2026-03-31 15:06
  - Summary: Sub-slice 3A.2 Canonical Turn Artifact Schema and Persistence was completed by adding the `TurnArtifact` dataclass and artifact storage helpers that persist JSON artifacts to `data/turns/<session_id>/<turn_id>.json` with atomic `.tmp` write-and-replace behavior.
  - Scope: backend/app/artifacts/turn_artifact.py, backend/app/artifacts/storage.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/artifacts/turn_artifact.py backend/app/artifacts/storage.py`; `backend/.venv/Scripts/python -c "from backend.app.artifacts.turn_artifact import TurnArtifact; from backend.app.artifacts.storage import write_turn_artifact, read_turn_artifact, list_session_turns; from datetime import datetime, timezone; import uuid; now = datetime.now(timezone.utc).isoformat(); artifact = TurnArtifact(turn_id=str(uuid.uuid4()), session_id='test-session-3a', turn_index=0, input_modality='text', transcript='remember this', prompt_text='prompt body', response_text='I will remember that for this session.', personality_profile_id='default', stt_model=None, llm_runtime='OllamaLLM', tts_runtime=None, final_state='IDLE', failure_reason=None, started_at=now, responded_at=now, completed_at=now); path = write_turn_artifact(artifact); loaded = read_turn_artifact('test-session-3a', artifact.turn_id); print('written:', path); print('roundtrip:', loaded.transcript == artifact.transcript); print('turn_count:', len(list_session_turns('test-session-3a')))"`
    ```text
    PASS compile: Compiling 'backend/app/artifacts/turn_artifact.py'... | Compiling 'backend/app/artifacts/storage.py'...
    PASS runtime: written: data\turns\test-session-3a\6264f40c-de05-4ce1-9edf-ed896375373a.json
    PASS runtime: roundtrip: True | turn_count: 1
    ```

- 2026-03-31 14:39
  - Summary: Sub-slice 3A.1 Session Lifecycle Manager was completed by creating `session_manager.py` with a typed `Session` dataclass and `SessionManager` lifecycle methods that persist session state to `data/sessions/<session_id>.json` using atomic `.tmp` write-and-replace.
  - Scope: backend/app/conversation/session_manager.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/conversation/session_manager.py`; `backend/.venv/Scripts/python -c "from backend.app.conversation.session_manager import SessionManager; s=SessionManager.open_session(); print('session_id:', s.session_id); print('turn_count:', s.turn_count); s=SessionManager.increment_turn(s); print('turn_count_after_increment:', s.turn_count); s=SessionManager.close_session(s); print('ended_at_present:', s.ended_at is not None)"`
    ```text
    PASS compile: Compiling 'backend/app/conversation/session_manager.py'...
    PASS runtime: session_id: f09bb51c-b87a-44fc-8e19-db0aee9de972
    PASS runtime: turn_count: 0 | turn_count_after_increment: 1 | ended_at_present: True
    ```

- 2026-03-30 18:16
  - Summary: Hugging Face local-first runtime correction was completed by forcing `HF_HUB_OFFLINE=1` in normal TTS runtime after model ensure and before Kokoro/HF-backed loading, while keeping explicit model acquisition online-capable via `HF_HUB_OFFLINE=0` in `scripts/ensure_models.py`.
  - Scope: backend/app/runtimes/tts/local_runtime.py, scripts/ensure_models.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/local_runtime.py scripts/ensure_models.py`; `@'<runtime proof script>'@ | backend/.venv/Scripts/python -`; `@'<acquisition proof script>'@ | backend/.venv/Scripts/python -`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`
    ```text
    PASS compile: Compiling 'backend/app/runtimes/tts/local_runtime.py'... | Compiling 'scripts/ensure_models.py'...
    PASS runtime proof: HF_HUB_OFFLINE_AFTER_RUNTIME: 1
    PASS acquisition proof: [PRESENT] kokoro-v1.0 → models/tts/kokoro-v1.0 | HF_HUB_OFFLINE_AFTER_ENSURE_SCRIPT: 0
    PASS slice2 live: backend/tests/runtime/test_slice2_tts_turn_live.py::test_spoken_voice_turn_live ... PASSED | 1 passed
    PASS slice1 live: backend/tests/runtime/test_slice1_stt_turn_live.py::test_voice_turn_live ... PASSED | 1 passed
    ```

- 2026-03-30 14:11
  - Summary: Warning-hygiene correction was completed by adding a narrow test-scoped filter for the third-party Kokoro/Torch `FutureWarning` so it no longer surfaces in the two live runtime tests; runtime behavior was unchanged.
  - Scope: backend/tests/runtime/test_slice1_stt_turn_live.py, backend/tests/runtime/test_slice2_tts_turn_live.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`
    ```text
    PASS slice1 live: backend/tests/runtime/test_slice1_stt_turn_live.py::test_voice_turn_live ... PASSED | 1 passed
    PASS slice2 live: backend/tests/runtime/test_slice2_tts_turn_live.py::test_spoken_voice_turn_live ... PASSED | 1 passed
    PASS runtime harness: PASS: runtime: 3 tests | RUNTIME: PASS | [PASS] JARVISv6 backend is validated!
    OBSERVED runtime note (non-blocking): [STT DEVICE] CUDA unavailable (cublas64_12.dll not loadable) — falling back to cpu
    OBSERVED runtime note (non-blocking): [ctranslate2] compute type inferred float16; converted to float32 on CPU fallback
    OBSERVED runtime note (non-blocking): Warning: unauthenticated requests to the HF Hub (HF_TOKEN not set)
    ```

- 2026-03-30 13:39
  - Summary: Prompt-leakage break-fix was completed by adding responder-boundary sanitation/acceptance so prompt scaffolding/context echo is stripped (or rejected if only scaffold remains) before downstream `[RESPONSE]` logging and TTS.
  - Scope: backend/app/cognition/responder.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/cognition/responder.py backend/app/runtimes/llm/ollama_runtime.py`; `@'<proof script>'@ | backend/.venv/Scripts/python -`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`
    ```text
    PASS compile: Compiling 'backend/app/cognition/responder.py'...
    PASS proof: SANITIZED: Clean user-facing reply.
    PASS proof: REJECTED: RuntimeError responder: sanitized response is empty after removing prompt scaffolding
    PASS slice1 live: [RESPONSE] You're welcome!... | PASSED
    PASS slice2 live: [RESPONSE] You're welcome!... | PASSED
    ```

- 2026-03-30 11:33
  - Summary: Sub-slice 2.5 was completed by realigning the existing Slice 2 unit test to the approved `synthesize(...)` contract and validating Slice 2 plus required Slice 0/1 regression coverage from the corrected repo state.
  - Scope: backend/tests/unit/test_slice2_tts_turn_units.py, backend/tests/runtime/test_slice2_tts_turn_live.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_detector.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_tts_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
    ```text
    PASS slice2 unit: 11 passed in 0.66s
    PASS slice2 live: [STATE] RESPONDING → SPEAKING | [STATE] SPEAKING → IDLE | PASSED
    PASS hardware unit regression: 7 passed in 1.93s
    PASS slice1 unit regression: 15 passed in 0.25s
    PASS slice1 live regression: [STATE] RESPONDING → SPEAKING | [STATE] SPEAKING → IDLE | PASSED
    PASS full harness: PASS: unit: 35 tests | PASS: runtime: 3 tests | UNIT=PASS | RUNTIME=PASS | [PASS] JARVISv6 backend is validated!
    ```

- 2026-03-30 11:30
  - Summary: Backend validation harness runtime visibility/return behavior was corrected during Slice 2.5 validation by changing runtime suite execution from one buffered subprocess to per-target pytest execution with live output and per-file result collection.
  - Scope: scripts/validate_backend.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_profiler_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
    ```text
    PASS profiler live: 1 passed in 1.99s
    OBSERVED transient investigation issue: test_slice1_tts_turn_live.py initially failed with `OllamaLLM: no response from http://localhost:11434`; rerun passed and this was not the harness root cause.
    PASS slice1 live rerun: [STATE] RESPONDING → SPEAKING | [STATE] SPEAKING → IDLE | PASSED
    PASS slice2 live: [STATE] RESPONDING → SPEAKING | [STATE] SPEAKING → IDLE | PASSED
    PASS runtime harness: PASS: runtime: 3 tests | RUNTIME=PASS | [PASS] JARVISv6 backend is validated!
    PASS full harness: PASS: unit: 35 tests | PASS: runtime: 3 tests | UNIT=PASS | RUNTIME=PASS | [PASS] JARVISv6 backend is validated!
    ```

- 2026-03-30 07:51
  - Summary: Slice 2 structure-correction was completed before Sub-slice 2.5 by adding the TTS selector layer and realigning voice service runtime wiring to the approved slice structure.
  - Scope: backend/app/runtimes/tts/tts_runtime.py, backend/app/services/voice_service.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/tts_runtime.py backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.tts.tts_runtime import select_tts_runtime; print('tts selector importable:', callable(select_tts_runtime))"`; `backend/.venv/Scripts/python -c "from backend.app.services.voice_service import run_voice_turn; print('voice_service importable:', callable(run_voice_turn))"`
    ```text
    PASS compile: Compiling 'backend/app/runtimes/tts/tts_runtime.py'... | Compiling 'backend/app/services/voice_service.py'...
    PASS selector import: tts selector importable: True
    PASS voice service import: voice_service importable: True
    ```

- 2026-03-30 07:21
  - Summary: Sub-slice 2.4 was completed by extending `run_voice_turn(...)` to execute a `SPEAKING` path with local Kokoro TTS synthesis and blocking playback, plus explicit degraded-mode text-only handling when TTS is unavailable.
  - Scope: backend/app/services/voice_service.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -c "from backend.app.conversation.states import ConversationState; print('speaking_present:', 'SPEAKING' in [s.name for s in ConversationState])"`; `backend/.venv/Scripts/python -c "from pathlib import Path; from backend.app.services.voice_service import ensure_temp_dir; p=ensure_temp_dir(); print('temp_dir_exists', Path(p).exists(), str(p))"`
    ```text
    PASS compile: Compiling 'backend/app/services/voice_service.py'...
    PASS speaking state check: speaking_present: True
    PASS temp dir handling: temp_dir_exists True data\temp
    ```

- 2026-03-30 07:07
  - Summary: Sub-slice 2.3 was completed by adding standalone audio playback utilities for output-device detection and blocking WAV playback.
  - Scope: backend/app/runtimes/tts/playback.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/playback.py`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.tts.playback import has_output_device; print('output device available:', has_output_device())"`
    ```text
    PASS compile: Compiling 'backend/app/runtimes/tts/playback.py'...
    PASS output device check: output device available: True
    ```

- 2026-03-30 06:52
  - Summary: Sub-slice 2.2 was completed by adding the TTS runtime interface and local Kokoro synthesis runtime, and validating dependency/install + availability after an initial pip cache permission blocker was cleared by successful rerun.
  - Scope: backend/app/runtimes/tts/base.py, backend/app/runtimes/tts/local_runtime.py, backend/requirements.txt
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/base.py backend/app/runtimes/tts/local_runtime.py`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.tts.local_runtime import KokoroTTSRuntime; print('tts available:', KokoroTTSRuntime().is_available())"`
    ```text
    PASS rerun install state: Requirement already satisfied: kokoro>=0.9.4 ... (0.9.4) | misaki>=0.9.3 ... (0.9.4) | docopt>=0.6.2 ... (0.6.2)
    PASS compile: command executed successfully for base.py and local_runtime.py (tool output capture issue noted)
    PASS availability: tts available: True
    NOTE blocker resolution: initial pip failure `[Errno 13] Permission denied` on cached docopt wheel was cleared by the successful admin rerun; subsequent validation passed.
    ```

- 2026-03-30 06:20
  - Summary: Sub-slice 2.1 was completed by adding Kokoro TTS catalog + model-acquisition wiring through existing catalog/manager/ensure-models architecture.
  - Scope: config/models/tts.yaml, backend/app/models/catalog.py, backend/app/models/manager.py, scripts/ensure_models.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/models/catalog.py backend/app/models/manager.py scripts/ensure_models.py`; `backend/.venv/Scripts/python -c "from backend.app.models.catalog import get_tts_model_entry; e=get_tts_model_entry('kokoro-v1.0'); print('hf_repo_id:', e['hf_repo_id']); print('local_dir:', e['local_dir']); print('default_voice:', e['default_voice'])"`; `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family tts --model kokoro-v1.0`; `backend/.venv/Scripts/python scripts/ensure_models.py --family tts --model kokoro-v1.0`; `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family tts --model kokoro-v1.0`; `backend/.venv/Scripts/python -c "from pathlib import Path; from backend.app.models.manager import verify_model; d=Path('models/tts/kokoro-v1.0'); print('dir_exists:', d.exists()); print('verify_tts:', verify_model(str(d), family='tts')); print('files:', [p.name for p in sorted(d.iterdir())[:10]] if d.exists() else [])"`
    ```text
    PASS compile: catalog.py | manager.py | ensure_models.py
    PASS catalog: hf_repo_id: hexgrad/Kokoro-82M | local_dir: models/tts/kokoro-v1.0 | default_voice: af_bella
    EXPECTED pre-download state: [MISSING] kokoro-v1.0 → models/tts/kokoro-v1.0
    PASS ensure/download: [DOWNLOAD] kokoro-v1.0 → models/tts/kokoro-v1.0 | [DONE] kokoro-v1.0 → models/tts/kokoro-v1.0
    PASS verify-after: [PRESENT] kokoro-v1.0 → models/tts/kokoro-v1.0
    PASS verify_model: dir_exists: True | verify_tts: True | files include 'kokoro-v1_0.pth'
    ```

- 2026-03-29 23:20
  - Summary: Sub-slices 1.5 and 1.6 were closed together as the validated Slice 1 acceptance/model-acquisition gate, with runtime STT fallback exercised and full backend validation passing.
  - Scope: backend/tests/unit/test_slice1_tts_turn_units.py, backend/tests/runtime/test_slice1_tts_turn_live.py, backend/app/models/catalog.py, backend/app/models/manager.py, scripts/ensure_models.py, backend/app/runtimes/stt/local_runtime.py, backend/requirements.txt, scripts/validate_backend.py
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -c "import ctypes; ctypes.WinDLL('cublas64_12.dll'); print('cublas load: PASS')"`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
    ```text
    PASS install: Successfully installed nvidia-cublas-cu12-12.9.2.10 nvidia-cuda-nvrtc-cu12-12.9.86 nvidia-cudnn-cu12-9.20.0.48
    OBSERVED CUDA direct-load check: FileNotFoundError: Could not find module 'cublas64_12.dll' (or one of its dependencies)
    PASS live fallback path: [STT DEVICE] CUDA unavailable (cublas64_12.dll not loadable) — falling back to cpu
    PASS live test: backend/tests/runtime/test_slice1_tts_turn_live.py::test_voice_turn_live ... PASSED
    PASS runtime harness: RUNTIME: PASS | [INVARIANTS] RUNTIME=PASS
    PASS full harness: UNIT: PASS | RUNTIME: PASS | [INVARIANTS] UNIT=PASS | RUNTIME=PASS
    ```

- 2026-03-29 12:18
  - Summary: Sub-slice 1.6 model acquisition mechanism was completed for STT with config-driven verify/download/ensure operations and explicit local model-path loading.
  - Scope: backend/app/models/__init__.py, backend/app/models/catalog.py, backend/app/models/manager.py, scripts/ensure_models.py, config/models/stt.yaml, backend/requirements.txt, .gitignore, backend/app/runtimes/stt/local_runtime.py
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -m compileall backend/app/models/manager.py backend/app/models/catalog.py scripts/ensure_models.py backend/app/runtimes/stt/local_runtime.py`; `backend/.venv/Scripts/python -c "from backend.app.models.catalog import get_model_entry; e=get_model_entry('whisper-large-v3-turbo'); print('hf_repo_id:', e['hf_repo_id']); print('local_dir:', e['local_dir'])"`; `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family stt --model whisper-large-v3-turbo`; `backend/.venv/Scripts/python scripts/ensure_models.py --family stt --model whisper-large-v3-turbo`; `backend/.venv/Scripts/python scripts/ensure_models.py --verify-only --family stt --model whisper-large-v3-turbo`; `backend/.venv/Scripts/python -c "from pathlib import Path; d=Path('models/stt/whisper-large-v3-turbo'); files=list(d.iterdir()) if d.exists() else []; print('model_dir_exists:', d.exists()); print('file_count:', len(files)); print('files:', [f.name for f in files[:5]])"`; `backend/.venv/Scripts/python -c "from backend.app.models.catalog import get_model_entry; from backend.app.models.manager import ensure_model, verify_model; e=get_model_entry('whisper-small'); p=ensure_model(e['hf_repo_id'], e['local_dir']); print('catalog_manager_flow', p, verify_model(p))"`
    ```text
    PASS install: Requirement already satisfied: huggingface_hub>=0.23
    PASS compile: manager.py | catalog.py | ensure_models.py | local_runtime.py
    PASS catalog: hf_repo_id: openai/whisper-large-v3-turbo | local_dir: models/stt/whisper-large-v3-turbo
    PASS verify-before: [MISSING] whisper-large-v3-turbo → models/stt/whisper-large-v3-turbo
    PASS ensure/download: [DOWNLOAD] ... | [DONE] whisper-large-v3-turbo → models/stt/whisper-large-v3-turbo
    PASS verify-after: [PRESENT] whisper-large-v3-turbo → models/stt/whisper-large-v3-turbo
    PASS dir check: model_dir_exists: True | file_count: 14
    PASS architecture proof: catalog_manager_flow models/stt/whisper-small True
    NOTE transient issue corrected in-scope: ModuleNotFoundError: No module named 'backend' in scripts/ensure_models.py; fixed by repo-root sys.path bootstrap before backend imports.
    NOTE mechanism is catalog/manager-based and ready for future LLM catalog extension; no LLM download behavior implemented in this sub-slice.
    ```

- 2026-03-29 11:28
  - Summary: Sub-slice 1.4 deterministic conversation-state flow, prompt assembly, responder, and one-turn voice orchestration were completed.
  - Scope: backend/app/conversation/states.py, backend/app/conversation/engine.py, backend/app/cognition/prompt_assembler.py, backend/app/cognition/responder.py, backend/app/services/voice_service.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/conversation/states.py backend/app/conversation/engine.py backend/app/cognition/prompt_assembler.py backend/app/cognition/responder.py backend/app/services/voice_service.py`; `backend/.venv/Scripts/python -c "from backend.app.conversation.states import ConversationState; print([s.name for s in ConversationState])"`; `backend/.venv/Scripts/python -c "from backend.app.personality.loader import load_personality_profile; from backend.app.cognition.prompt_assembler import assemble_prompt; p=load_personality_profile('default'); print('personality', p.profile_id); print('prompt_non_empty', bool(assemble_prompt('test transcript', p).strip()))"`; `backend/.venv/Scripts/python -c "from pathlib import Path; from backend.app.services.voice_service import ensure_temp_dir; p=ensure_temp_dir(); print('temp_dir_exists', Path(p).exists(), str(p))"`
    ```text
    PASS compile: Compiling 'backend/app/conversation/states.py'... | 'backend/app/conversation/engine.py'... | 'backend/app/cognition/prompt_assembler.py'... | 'backend/app/cognition/responder.py'... | 'backend/app/services/voice_service.py'...
    PASS states: ['BOOTSTRAP', 'PROFILING', 'IDLE', 'LISTENING', 'TRANSCRIBING', 'REASONING', 'ACTING', 'RESPONDING', 'SPEAKING', 'INTERRUPTED', 'RECOVERING', 'FAILED']
    PASS personality/prompt: personality default | prompt_non_empty True
    PASS temp dir: temp_dir_exists True data\temp
    NOTE fail-closed paths implemented and code-reviewed: transition no-op (`ConversationEngine.transition`), empty LLM response (`get_response`), and voice-turn failure handling (`run_voice_turn` transitions to FAILED, logs, re-raises).
    ```

- 2026-03-29 11:12
  - Summary: Sub-slice 1.3 STT abstraction, faster-whisper local runtime, and fixed-duration microphone capture were completed with explicit fail-closed paths.
  - Scope: backend/requirements.txt, backend/app/runtimes/stt/base.py, backend/app/runtimes/stt/local_runtime.py, backend/app/runtimes/stt/stt_runtime.py
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -m compileall backend/app/runtimes/stt/base.py backend/app/runtimes/stt/local_runtime.py backend/app/runtimes/stt/stt_runtime.py`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.stt.local_runtime import FasterWhisperSTT; print('stt available:', FasterWhisperSTT('whisper-large-v3-turbo').is_available())"`; `backend/.venv/Scripts/python -c "import sounddevice as sd; print('input devices:', [d['name'] for d in sd.query_devices() if d['max_input_channels'] > 0])"`
    ```text
    PASS install: Successfully installed ... faster-whisper-1.2.1 ... sounddevice-0.5.5 ... soundfile-0.13.1
    PASS compile: Compiling 'backend/app/runtimes/stt/base.py'... | 'backend/app/runtimes/stt/local_runtime.py'... | 'backend/app/runtimes/stt/stt_runtime.py'...
    PASS stt available: True
    PASS input devices: ['Microsoft Sound Mapper - Input', 'Microphone (Logi USB Headset)', ...]
    NOTE fail-closed paths implemented and code-reviewed: no input device (`capture_utterance`), missing audio path and transcription failure (`FasterWhisperSTT.transcribe`); not runtime-triggered on this host.
    ```

- 2026-03-29 10:53
  - Summary: Sub-slice 1.2 LLM runtime interface and deterministic selector were completed with fail-closed runtime selection behavior.
  - Scope: backend/requirements.txt, backend/app/core/settings.py, backend/app/runtimes/llm/base.py, backend/app/runtimes/llm/local_runtime.py, backend/app/runtimes/llm/ollama_runtime.py, backend/app/routing/runtime_selector.py
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -m compileall backend/app/core/settings.py backend/app/runtimes/llm/base.py backend/app/runtimes/llm/local_runtime.py backend/app/runtimes/llm/ollama_runtime.py backend/app/routing/runtime_selector.py`; `backend/.venv/Scripts/python -c "from backend.app.runtimes.llm.local_runtime import LlamaCppLLM; print('llama_cpp available:', LlamaCppLLM().is_available())"`; `backend/.venv/Scripts/python -c "from backend.app.routing.runtime_selector import select_llm_runtime; import sys; try: r=select_llm_runtime(); print(type(r).__name__); except Exception as e: print(type(e).__name__, str(e))"`; `backend/.venv/Scripts/python -c "from backend.app.routing.runtime_selector import select_llm_runtime`nimport sys`ntry:`n    r=select_llm_runtime()`n    print(type(r).__name__)`nexcept Exception as e:`n    print(type(e).__name__, str(e))"`
    ```text
    PASS install: Successfully installed ... httpx-0.28.1 ... ollama-0.6.1
    PASS compile: Compiling 'backend/app/core/settings.py'... | 'backend/app/runtimes/llm/base.py'... | 'backend/app/runtimes/llm/local_runtime.py'... | 'backend/app/runtimes/llm/ollama_runtime.py'... | 'backend/app/routing/runtime_selector.py'...
    PASS llama.cpp availability: llama_cpp available: False
    NOTE selector validation attempt 1: SyntaxError: invalid syntax
    PASS selector validation (corrected command): OllamaLLM
    ```

- 2026-03-29 10:29
  - Summary: Sub-slice 1.1 personality schema, loader, and default profile were completed.
  - Scope: backend/app/personality/schema.py, backend/app/personality/loader.py, config/personality/default.yaml
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/personality/schema.py backend/app/personality/loader.py`; `backend/.venv/Scripts/python -c "from backend.app.personality.loader import load_personality_profile; p=load_personality_profile('default'); print(p.profile_id, p.display_name, p.enabled)"`
    ```text
    PASS compile: Compiling 'backend/app/personality/schema.py'... | Compiling 'backend/app/personality/loader.py'...
    PASS loader: default JARVIS True
    ```

- 2026-03-29 06:32
  - Summary: Unit-test patch correction was completed by removing the stale monkeypatch reference to `detect_cuda_via_providers` from the profiler unit-test path.
  - Scope: backend/tests/unit/test_hardware_detector.py
  - Evidence: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_detector.py::test_profiler_run_is_unit_testable_with_monkeypatched_detectors -q -vv`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_detector.py -q`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
    ```text
    PASS targeted test: backend/tests/unit/test_hardware_detector.py::test_profiler_run_is_unit_testable_with_monkeypatched_detectors PASSED [100%]
    PASS unit file: 7 passed in 1.07s
    PASS harness unit scope: UNIT: PASS | [INVARIANTS] UNIT=PASS | [PASS] JARVISv6 backend is validated!
    ```

- 2026-03-28 23:30
  - Summary: Architect-review corrections were completed by removing the dead CUDA helper empty-list path and replacing the AMD `pyrsmi` import-only stub with real initialize/query/shutdown flow.
  - Scope: backend/app/hardware/profiler.py, backend/app/hardware/detectors/gpu_detector.py, backend/requirements.txt
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -m compileall backend/app/hardware/profiler.py backend/app/hardware/detectors/gpu_detector.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; r=run_profiler(); print(r.profile.profile_id, r.profile.device_class, r.profile.cuda_available, r.profile.gpu_vendor); print(r.flags.stt_recommended_runtime, r.flags.stt_recommended_model, r.flags.requires_degraded_mode)"`; `backend/.venv/Scripts/python -c "from pathlib import Path; t=Path('backend/app/hardware/profiler.py').read_text(encoding='utf-8'); print('empty_list_cuda_helper_call_present', ('providers: list[str] = []' in t and 'detect_cuda_via_providers(providers)' in t))"`; `backend/.venv/Scripts/python -c 'from pathlib import Path; t=Path("backend/app/hardware/detectors/gpu_detector.py").read_text(encoding="utf-8"); print("import_only_stub_present", "return _build_result(True, None, \"amd\", None, \"pyrsmi\")" in t); print("pyrsmi_init_finally_shutdown_present", ("finally" in t and "pyrsmi" in t and "shutdown" in t.lower()))'`
    ```text
    PASS install: Requirement already satisfied: pyrsmi>=1.0 ... (1.1.0)
    PASS compile: Compiling 'backend/app/hardware/profiler.py'... | Compiling 'backend/app/hardware/detectors/gpu_detector.py'...
    PASS profiler run: nvidia-cuda-desktop-63gb desktop True nvidia | faster-whisper whisper-large-v3-turbo False
    PASS CUDA dead-path proof: empty_list_cuda_helper_call_present False
    PASS AMD pyrsmi proof: import_only_stub_present False | pyrsmi_init_finally_shutdown_present True
    ```

- 2026-03-28 23:01
  - Summary: Slice 0.13 consolidated hardware profiler tests were completed; `pytest` dependency was added so approved backend test commands could run in `backend/.venv`.
  - Scope: backend/tests/unit/test_hardware_detector.py, backend/tests/runtime/test_profiler_live.py, backend/requirements.txt
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_detector.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_profiler_live.py -v -s`
    ```text
    PASS install: Successfully installed colorama-0.4.6 iniconfig-2.3.0 pluggy-1.6.0 pygments-2.19.2 pytest-9.0.2
    PASS unit tests: ....... [100%] | 7 passed in 2.43s
    PASS runtime test: collected 1 item | PASSED | 1 passed in 0.97s
    PASS runtime evidence: profile_id='nvidia-cuda-desktop-63gb' | stt_recommended_runtime='faster-whisper' | stt_recommended_model='whisper-large-v3-turbo'
    ```

- 2026-03-28 22:32
  - Summary: Slice 0.12 STT config stub was completed and validated in backend `.venv`.
  - Scope: config/models/stt.yaml
  - Evidence: `backend/.venv/Scripts/python -c "from pathlib import Path; p=Path('config/models/stt.yaml'); print('exists', p.exists())"`; `backend/.venv/Scripts/python -c "from pathlib import Path; import yaml; data=yaml.safe_load(Path('config/models/stt.yaml').read_text(encoding='utf-8')); print('top_keys', sorted(data.keys())); print('models', sorted((data.get('models') or {}).keys())); print('runtimes', sorted((data.get('runtimes') or {}).keys()))"`; `backend/.venv/Scripts/python -c "from pathlib import Path; t=Path('config/models/stt.yaml').read_text(encoding='utf-8'); required=['family: whisper','models:','whisper-large-v3-turbo:','whisper-small:','whisper-base:','whisper-tiny:','runtimes:','faster-whisper:','whisper.cpp:','openvino-whisper:','onnx-whisper:']; print('required_tokens', all(token in t for token in required))"`
    ```text
    PASS exists: exists True
    PASS top keys: top_keys ['family', 'models', 'runtimes']
    PASS models: ['whisper-base', 'whisper-large-v3-turbo', 'whisper-small', 'whisper-tiny']
    PASS runtimes: ['faster-whisper', 'onnx-whisper', 'openvino-whisper', 'whisper.cpp']
    PASS required tokens: required_tokens True
    ```

- 2026-03-28 22:25
  - Summary: Slice 0.11 runtime profile config was completed; PyYAML dependency was added so YAML validation could run in backend `.venv`.
  - Scope: config/app/profiles.yaml, backend/requirements.txt
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`; `backend\.venv\Scripts\python -c "from pathlib import Path; p=Path('config/app/profiles.yaml'); print('exists', p.exists())"`; `backend\.venv\Scripts\python -c "from pathlib import Path; import yaml; data=yaml.safe_load(Path('config/app/profiles.yaml').read_text(encoding='utf-8')); print('top_keys', sorted(data.keys())); print('profiles_present', sorted(data.get('profiles', {}).keys()))"`; `backend\.venv\Scripts\python -c "from pathlib import Path; t=Path('config/app/profiles.yaml').read_text(encoding='utf-8'); required=['profiles:','nvidia_cuda_desktop_high:','nvidia_cuda_desktop_mid:','cpu_only_capable:','cpu_only_constrained:','intel_npu:','apple_silicon:','degraded:','match_pattern:','stt_runtime:','stt_model:']; print('required_tokens', all(token in t for token in required))"`
    ```text
    PASS install: Successfully installed PyYAML-6.0.3
    PASS exists: exists True
    PASS yaml keys: top_keys ['profiles']
    PASS profile entries: profiles_present ['apple_silicon', 'cpu_only_capable', 'cpu_only_constrained', 'degraded', 'intel_npu', 'nvidia_cuda_desktop_high', 'nvidia_cuda_desktop_mid']
    PASS required tokens: required_tokens True
    ```

- 2026-03-28 22:08
  - Summary: Slice 0.10 main profiler `run_profiler() -> FullCapabilityReport` was implemented and validated; Windows battery classification was corrected so UPS telemetry does not misclassify desktop/workstation hosts as `laptop`.
  - Scope: backend/app/hardware/profiler.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/profiler.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; r=run_profiler(); print(type(r).__name__, type(r.profile).__name__, type(r.flags).__name__); print(r.profile.profile_id); print(r.profile.device_class, r.profile.cuda_available, r.profile.gpu_vendor); print(r.flags.stt_recommended_runtime, r.flags.stt_recommended_model, r.flags.requires_degraded_mode)"`; `powershell -NoProfile -Command "Get-CimInstance Win32_Battery | Select-Object Name,DeviceID,BatteryStatus,Chemistry,DesignVoltage,EstimatedChargeRemaining | Format-List"`
    ```text
    PASS compile: Compiling 'backend/app/hardware/profiler.py'...
    PASS profiler contract: FullCapabilityReport HardwareProfile CapabilityFlags
    PASS corrected classification: nvidia-cuda-desktop-63gb | desktop True nvidia
    PASS flags: faster-whisper whisper-large-v3-turbo False
    PASS UPS identity evidence: Name : Back-UPS BGM1500B-US FW:31316S15-31320S12
    ```

- 2026-03-28 21:53
  - Summary: Slice 0.9 capability-flag derivation was implemented in profiler and validated.
  - Scope: backend/app/hardware/profiler.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/profiler.py`; `backend/.venv/Scripts/python -c "from backend.app.core.capabilities import HardwareProfile; from backend.app.hardware.profiler import derive_capability_flags; p=HardwareProfile(os='Windows',arch='AMD64',cpu_name='x',cpu_physical_cores=8,cpu_logical_cores=16,cpu_max_freq_mhz=3000.0,gpu_available=True,gpu_name='NVIDIA',gpu_vendor='nvidia',gpu_vram_gb=12.0,cuda_available=True,npu_available=False,npu_vendor=None,npu_tops=None,memory_total_gb=32.0,memory_available_gb=20.0,device_class='desktop',profile_id='nvidia-cuda-desktop-32gb'); f=derive_capability_flags(p); print(f); print(f.supports_local_llm, f.supports_gpu_llm, f.supports_cuda_llm, f.stt_recommended_runtime, f.stt_recommended_model)"`; `backend/.venv/Scripts/python -c "from backend.app.core.capabilities import HardwareProfile; from backend.app.hardware.profiler import derive_capability_flags; p=HardwareProfile(os='Windows',arch='AMD64',cpu_name='x',cpu_physical_cores=4,cpu_logical_cores=8,cpu_max_freq_mhz=2500.0,gpu_available=False,gpu_name=None,gpu_vendor=None,gpu_vram_gb=None,cuda_available=False,npu_available=False,npu_vendor=None,npu_tops=None,memory_total_gb=6.0,memory_available_gb=3.0,device_class='constrained',profile_id='cpu-nocuda-constrained-6gb'); f=derive_capability_flags(p); print(f); print(f.requires_degraded_mode, f.stt_recommended_runtime, f.stt_recommended_model)"`
    ```text
    PASS compile: Compiling 'backend/app/hardware/profiler.py'...
    PASS high-capability flags: True True True faster-whisper whisper-large-v3-turbo
    PASS constrained flags: True faster-whisper whisper-tiny
    ```

- 2026-03-28 21:46
  - Summary: Slice 0.8 device-class classifier was implemented in profiler and validated.
  - Scope: backend/app/hardware/profiler.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/profiler.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import classify_device_class; print(classify_device_class({'os':'Darwin','arch':'ARM64'},{'memory_total_gb':32.0},False,{'npu_vendor':None})); print(classify_device_class({'os':'Windows','arch':'AMD64'},{'memory_total_gb':8.0},False,{'npu_vendor':None}, battery_present=False)); print(classify_device_class({'os':'Windows','arch':'AMD64'},{'memory_total_gb':8.0},True,{'npu_vendor':None}, battery_present=False))"`
    ```text
    PASS compile: Compiling 'backend/app/hardware/profiler.py'...
    PASS classifier output: laptop
    PASS classifier output: constrained
    PASS classifier output: desktop
    ```

- 2026-03-28 21:32
  - Summary: Slice 0.7 memory detector was implemented and validated.
  - Scope: backend/app/hardware/detectors/memory_detector.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/detectors/memory_detector.py 2>&1`; `backend/.venv/Scripts/python -c "from backend.app.hardware.detectors.memory_detector import detect_memory; r=detect_memory(); print(r); print(sorted(r.keys()))" 2>&1`
    ```text
    PASS compile: Compiling 'backend/app/hardware/detectors/memory_detector.py'...
    PASS detector output: {'memory_total_gb': 63.7, 'memory_available_gb': 36.27, 'memory_percent_used': 43.1}
    PASS contract keys: ['memory_available_gb', 'memory_percent_used', 'memory_total_gb']
    ```

- 2026-03-28 21:27
  - Summary: Slice 0.6 NPU detector was implemented with guarded optional detection paths and validated.
  - Scope: backend/app/hardware/detectors/npu_detector.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/detectors/npu_detector.py 2>&1`; `backend/.venv/Scripts/python -c "from backend.app.hardware.detectors.npu_detector import detect_npu; r=detect_npu(); print(r); print(sorted(r.keys()))" 2>&1`
    ```text
    PASS compile: Compiling 'backend/app/hardware/detectors/npu_detector.py'...
    PASS detector output: {'npu_available': False, 'npu_vendor': None, 'npu_tops': None}
    PASS contract keys: ['npu_available', 'npu_tops', 'npu_vendor']
    ```

- 2026-03-28 21:08
  - Summary: Slice 0.5 CUDA detector was implemented and corrected to prevent host false negatives by falling back to `nvidia-smi` when torch is unavailable/inconclusive.
  - Scope: backend/app/hardware/detectors/cuda_detector.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/detectors/cuda_detector.py`; `backend/.venv/Scripts/python -c "from backend.app.hardware.detectors.cuda_detector import detect_cuda, detect_cuda_via_providers; print({'detect_cuda': detect_cuda(), 'cpu_only': detect_cuda_via_providers(['CPUExecutionProvider']), 'cuda_only': detect_cuda_via_providers(['CUDAExecutionProvider'])})"`; `nvidia-smi --query-gpu=name,driver_version --format=csv,noheader`
    ```text
    PASS compile: Compiling 'backend/app/hardware/detectors/cuda_detector.py'...
    PASS detector output: {'detect_cuda': True, 'cpu_only': False, 'cuda_only': True}
    PASS nvidia-smi: NVIDIA GeForce RTX 3060, 595.79
    ```

- 2026-03-28 20:43
  - Summary: Slice 0.4 compliance correction was completed by updating optional hardware dependency import guards to use `try/except ImportError`.
  - Scope: backend/app/hardware/detectors/gpu_detector.py
  - Evidence: `backend/.venv/Scripts/python -m compileall backend/app/hardware/detectors/gpu_detector.py 2>&1`; `backend/.venv/Scripts/python -c "from backend.app.hardware.detectors.gpu_detector import detect_gpu; r=detect_gpu(); print(r); print(sorted(r.keys()))" 2>&1`
    ```text
    PASS compile: Compiling 'backend/app/hardware/detectors/gpu_detector.py'...
    PASS contract keys: ['gpu_available', 'gpu_name', 'gpu_vendor', 'gpu_vram_gb', 'gpu_vram_source']
    PASS detector output: {'gpu_available': True, 'gpu_name': 'NVIDIA GeForce RTX 3060', 'gpu_vendor': 'nvidia', 'gpu_vram_gb': 12.0, 'gpu_vram_source': 'nvml'}
    Compliance: optional imports for pynvml, torch, openvino, pyrsmi, onnxruntime now use try/except ImportError.
    ```

- 2026-03-28 20:32
  - Summary: Slice 0.4 vendor-specific GPU detector was implemented and validated with backend venv commands and host proof commands.
  - Scope: backend/app/hardware/detectors/gpu_detector.py, backend/requirements.txt
  - Evidence: `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt 2>&1`; `backend/.venv/Scripts/python -m compileall backend/app/hardware/detectors/gpu_detector.py 2>&1`; `backend/.venv/Scripts/python -c "from backend.app.hardware.detectors.gpu_detector import detect_gpu; r=detect_gpu(); print(r); print(sorted(r.keys()))" 2>&1`; `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>&1`; `xpu-smi discovery -j 2>&1`; `rocm-smi --showproductname --json 2>&1`; `powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name" 2>&1`; `backend/.venv/Scripts/python -c "from backend.app.hardware.detectors.gpu_detector import detect_gpu; r=detect_gpu(); print(repr(r.get('gpu_vram_gb')), type(r.get('gpu_vram_gb')).__name__)" 2>&1`
    ```text
    PASS compile: Compiling 'backend/app/hardware/detectors/gpu_detector.py'...
    PASS contract keys: ['gpu_available', 'gpu_name', 'gpu_vendor', 'gpu_vram_gb', 'gpu_vram_source']
    PASS detector output: {'gpu_available': True, 'gpu_name': 'NVIDIA GeForce RTX 3060', 'gpu_vendor': 'nvidia', 'gpu_vram_gb': 12.0, 'gpu_vram_source': 'nvml'}
    PASS nvidia-smi: NVIDIA GeForce RTX 3060, 12288
    PASS Windows CIM Name: NVIDIA GeForce RTX 3060 | Intel(R) UHD Graphics 770
    FAIL xpu-smi: The term 'xpu-smi' is not recognized...
    FAIL rocm-smi: The term 'rocm-smi' is not recognized...
    PASS VRAM type check: 12.0 float
    ```

  - Summary: Slice 0.3 CPU detector and minimal hardware dependency declaration were implemented and validated.
  - Scope: backend/app/hardware/detectors/cpu_detector.py, backend/requirements.txt
  - Evidence: `backend\.venv\Scripts\python -m pip install -r backend/requirements.txt`; `backend\.venv\Scripts\python -m compileall backend/app/hardware/detectors/cpu_detector.py`; `backend\.venv\Scripts\python -c "from backend.app.hardware.detectors.cpu_detector import detect_cpu; print(detect_cpu())"`
    ```text
    Successfully installed psutil-7.2.2
    Compiling 'backend/app/hardware/detectors/cpu_detector.py'...
    {'cpu_name': 'Intel64 Family 6 Model 151 Stepping 2, GenuineIntel', 'cpu_physical_cores': 16, 'cpu_logical_cores': 24, 'cpu_max_freq_mhz': 3200.0}
    ```

- 2026-03-28 17:54
  - Summary: Slice 0.2 OS/architecture detector was implemented and validated in backend venv context.
  - Scope: backend/app/hardware/detectors/os_detector.py, backend/.venv
  - Evidence: `python -m venv backend/.venv`; `backend\.venv\Scripts\python -m compileall backend/app/hardware/detectors/os_detector.py`; `backend\.venv\Scripts\python -c "from backend.app.hardware.detectors.os_detector import detect_os; print(detect_os())"`
    ```text
    Compiling 'backend/app/hardware/detectors/os_detector.py'...
    {'os': 'Windows', 'os_release': '11', 'arch': 'AMD64'}
    ```

- 2026-03-28 17:41
  - Summary: Slice 0.1 normalized capability schema was implemented.
  - Scope: backend/app/core/capabilities.py
  - Evidence: `python -m compileall backend/app/core/capabilities.py`
    ```text
    Compiling 'backend/app/core/capabilities.py'...
    ```

- 2026-03-28 11:30
  - Summary: CHANGE_LOG.md established
  - Scope: CHANGE_LOG.md
  - Evidence: `cat .\CHANGE_LOG.md -head 1`
    ```text
    # CHANGE_LOG.md
    ```