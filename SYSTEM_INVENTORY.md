# SYSTEM_INVENTORY.md
> Authoritative capability ledger. This is not a roadmap or config reference. 
> Inventory entries must reflect only observable artifacts in this repository: files, directories, executable code, configuration, scripts, and explicit UI text. 
> Do not include intent, design plans, or inferred behavior.

## Rules
- One component entry = one capability or feature observed in the repository.
- New capabilities go at the top under `## Inventory` and above `## Observed Initial Inventory`.
- Corrections or clarifications go only below the `## Appendix` section.
- Entries must include:

- Capability: **Brief Descriptive Component Name** 
  - Date/Time
  - State: Planned, Implemented, Verified, Deferred
  - Location: `Relative File Path(s)`
  - Validation: Method &/or `Relative Script Path(s)`
  - Notes: 
    - Optional (3 lines max).

## States
- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command)
- Deferred: intentionally postponed (reason noted)

## Inventory

- Capability: Hardware Profile Provisioning and Backend Readiness Rail (Slice 0.0) verified - 2026-04-05 01:27
  - State: Verified
  - Location: `config/hardware/hw_cpu_base.json`, `config/hardware/hw_gpu_present.json`, `config/hardware/hw_gpu_noncuda.json`, `config/hardware/hw_gpu_nvidia_cuda.json`, `config/hardware/hw_npu_present.json`, `backend/app/hardware/profile_resolver.py`, `backend/app/hardware/preflight.py`, `backend/app/hardware/profiler.py`, `backend/app/core/capabilities.py`, `backend/app/runtimes/stt/stt_runtime.py`, `backend/app/runtimes/tts/tts_runtime.py`, `scripts/bootstrap_readiness.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_profiler.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice2_tts_turn_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; r=run_profiler(); print('stt_recommended_device=', r.flags.stt_recommended_device); print('tts_recommended_device=', r.flags.tts_recommended_device); print('readiness=', r.readiness)"`; `backend/.venv/Scripts/python scripts/bootstrap_readiness.py --verify-only`
  - Notes: Hardware-only manifests resolve additively, preflight owns provisioning/verification, profiler owns readiness/evidence-token selection, and STT/TTS recommendations/routes consume verified readiness fields.

- Capability: Windows CUDA DLL/bootstrap setup ownership normalized to preflight (STT delegated) verified - 2026-04-05 01:27
  - State: Verified
  - Location: `backend/app/hardware/preflight.py`, `backend/app/runtimes/stt/local_runtime.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_readiness.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice1_stt_turn_units.py -q`; `backend/.venv/Scripts/python -c "from backend.app.hardware.profiler import run_profiler; from backend.app.hardware.preflight import run_hardware_preflight, derive_stt_device_readiness; from backend.app.runtimes.stt.stt_runtime import select_stt_runtime; r=run_profiler(); p=run_hardware_preflight(r.profile); d=derive_stt_device_readiness(p); rt=select_stt_runtime(r); print('verification_results=', p.get('verification_results')); print('derived=', d); print('runtime_device=', getattr(rt, 'device', None))"`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`
  - Notes: `preflight.py` exposes the Windows CUDA DLL/bootstrap setup surface and STT local runtime delegates to that ownership surface.

- Capability: Interruptibility — Barge-In, Explicit Interruption Contract, and Artifact Evidence (Slice 4) verified - 2026-04-03 07:42
  - State: Verified
  - Location: `backend/app/runtimes/stt/barge_in.py`, `backend/app/runtimes/tts/playback.py`, `backend/app/conversation/engine.py`, `backend/app/artifacts/turn_artifact.py`, `backend/app/services/voice_service.py`, `backend/tests/unit/test_slice4_interruption_units.py`, `backend/tests/runtime/test_slice4_interruption_live.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_slice4_interruption_units.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice4_interruption_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
  - Notes: Verified boundary is single-turn interruption handling with caller-initiated next turn; no continuous voice loop capability recorded.

- Capability: Live Multi-Turn Spoken Continuity (Slice 3B) verified - 2026-04-01 19:01
  - State: Verified
  - Location: `backend/app/services/voice_service.py`, `backend/app/runtimes/stt/stt_runtime.py`, `backend/app/runtimes/tts/playback.py`, `backend/tests/runtime/test_slice3b_multiturn_voice_live.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`
  - Notes: Live two-turn spoken continuity on top of the Slice 3A path is runtime-verified, with turn 2 transcript/completion and runtime-only acceptance evidence recorded.

- Capability: Deterministic Session Continuity (Slice 3A) verified - 2026-04-01 19:01
  - State: Verified
  - Location: `backend/app/conversation/session_manager.py`, `backend/app/artifacts/turn_artifact.py`, `backend/app/artifacts/storage.py`, `backend/app/memory/working.py`, `backend/app/memory/write_policy.py`, `backend/app/services/turn_service.py`, `backend/app/cognition/prompt_assembler.py`, `backend/tests/unit/test_slice3a_session_continuity_units.py`, `backend/tests/runtime/test_slice3a_session_continuity_runtime.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3a_session_continuity_runtime.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice3b_multiturn_voice_live.py -v -s`
  - Notes: Session lifecycle, canonical artifact persistence, bounded working memory, explicit write policy, and transcript-bound continuity executor are verified as the Slice 3 continuity authority.

- Capability: Spoken Response / Local TTS via Kokoro with response sanitation and local-first HF runtime (Slice 2) verified - 2026-03-30 18:27
  - State: Verified
  - Location: `config/models/tts.yaml`, `backend/app/models/catalog.py`, `backend/app/models/manager.py`, `scripts/ensure_models.py`, `backend/app/runtimes/tts/base.py`, `backend/app/runtimes/tts/local_runtime.py`, `backend/app/runtimes/tts/tts_runtime.py`, `backend/app/runtimes/tts/playback.py`, `backend/app/services/voice_service.py`, `backend/app/cognition/responder.py`, `backend/tests/runtime/test_slice2_tts_turn_live.py`, `backend/tests/runtime/test_slice1_stt_turn_live.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_stt_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`; `backend/.venv/Scripts/python -m compileall backend/app/runtimes/tts/local_runtime.py scripts/ensure_models.py`
  - Notes: Observable path includes Kokoro TTS catalog/model-acquisition, local TTS runtime + selector, standalone playback, `SPEAKING` execution in `run_voice_turn(...)`, responder-boundary sanitation before `[RESPONSE]`/TTS, and runtime `HF_HUB_OFFLINE=1` with explicit acquisition path `HF_HUB_OFFLINE=0`.

- Capability: Spoken Response / Local TTS via Kokoro (Slice 2) verified - 2026-03-30 11:40
  - State: Verified
  - Location: `config/models/tts.yaml`, `backend/app/models/catalog.py`, `backend/app/models/manager.py`, `scripts/ensure_models.py`, `backend/app/runtimes/tts/base.py`, `backend/app/runtimes/tts/local_runtime.py`, `backend/app/runtimes/tts/tts_runtime.py`, `backend/app/runtimes/tts/playback.py`, `backend/app/services/voice_service.py`, `backend/tests/unit/test_slice2_tts_turn_units.py`, `backend/tests/runtime/test_slice2_tts_turn_live.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice2_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
  - Notes: Observable path includes Kokoro TTS catalog/model acquisition, local TTS runtime selection, blocking playback utility, and `SPEAKING` state execution in the one-turn voice service path.

- Capability: Minimal Voice Turn + STT Model Acquisition Gate (Slice 1) verified - 2026-03-29 23:26
  - State: Verified
  - Location: `backend/app/personality/schema.py`, `backend/app/personality/loader.py`, `backend/app/core/settings.py`, `backend/app/runtimes/llm/base.py`, `backend/app/runtimes/llm/local_runtime.py`, `backend/app/runtimes/llm/ollama_runtime.py`, `backend/app/routing/runtime_selector.py`, `backend/app/runtimes/stt/base.py`, `backend/app/runtimes/stt/local_runtime.py`, `backend/app/runtimes/stt/stt_runtime.py`, `backend/app/models/catalog.py`, `backend/app/models/manager.py`, `scripts/ensure_models.py`, `config/models/stt.yaml`, `backend/app/conversation/states.py`, `backend/app/conversation/engine.py`, `backend/app/cognition/prompt_assembler.py`, `backend/app/cognition/responder.py`, `backend/app/services/voice_service.py`, `backend/tests/unit/test_slice1_tts_turn_units.py`, `backend/tests/runtime/test_slice1_tts_turn_live.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_slice1_tts_turn_live.py -v -s`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope runtime`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope all`
  - Notes: Observable path includes personality load, deterministic stateful one-turn orchestration, LLM runtime hierarchy, STT catalog/manager ensure path, and exercised CPU fallback when CUDA DLL load was unavailable.

- Capability: Hardware Profiler (Slice 0) verified - 2026-03-28 23:08
  - State: Verified
  - Location: `backend/app/core/capabilities.py`, `backend/app/hardware/profiler.py`, `backend/app/hardware/detectors/`, `backend/tests/unit/test_hardware_detector.py`, `backend/tests/runtime/test_profiler_live.py`
  - Validation: `backend/.venv/Scripts/python -m pytest backend/tests/unit/test_hardware_detector.py -q`; `backend/.venv/Scripts/python -m pytest backend/tests/runtime/test_profiler_live.py -v -s`
  - Notes: Callable `run_profiler()` emits `FullCapabilityReport(profile: HardwareProfile, flags: CapabilityFlags)` with implemented OS/CPU/GPU/CUDA/NPU/memory detector coverage.

- Capability: SYSTEM_INVENTORY extablished - 2026-02-14 13:35
  - State: Implemented
  - Location: `SYSTEM_INVENTORY.md`
  - Validation: `cat .\SYSTEM_INVENTORY.md -head 1` = `# SYSTEM_INVENTORY.md`
  - Notes: 

## Appendix