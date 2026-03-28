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

- 2026-03-28 17:59
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