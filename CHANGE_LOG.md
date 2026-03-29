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