from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.capabilities import FullCapabilityReport
from backend.app.hardware.profiler import run_profiler
from backend.app.personality.loader import load_personality_profile
from backend.app.personality.schema import PersonalityProfile
from backend.app.runtimes.llm.ollama_runtime import OllamaLLM


@dataclass(slots=True)
class StartupSummary:
    profile_id: str
    device_class: str

    stt_ready: bool
    stt_selected_device: str
    tts_ready: bool
    tts_selected_device: str
    llm_ready: bool
    llm_runtime_name: str

    personality_profile_id: str
    personality_display_name: str

    degraded_conditions: list[str]


def _is_selected_device_ready(selected_device: str) -> bool:
    return selected_device in {"cuda", "cpu"}


def run_startup(
    *, personality_name: str = "default"
) -> tuple[StartupSummary, FullCapabilityReport, PersonalityProfile]:
    """Profile hardware, check readiness, and load personality for host startup."""

    report = run_profiler()
    personality = load_personality_profile(personality_name)

    stt_selected_device = report.readiness.stt_selected_device
    tts_selected_device = report.readiness.tts_selected_device

    stt_ready = _is_selected_device_ready(stt_selected_device)
    tts_ready = _is_selected_device_ready(tts_selected_device)

    llm_ready = OllamaLLM().is_available()
    llm_runtime_name = "OllamaLLM" if llm_ready else "unavailable"

    degraded_conditions: list[str] = []
    if not stt_ready:
        degraded_conditions.append("STT unavailable (no ready selected device)")
    if not tts_ready:
        degraded_conditions.append("TTS unavailable (no ready selected device)")
    if not llm_ready:
        degraded_conditions.append("LLM service unavailable (Ollama not reachable)")

    summary = StartupSummary(
        profile_id=report.profile.profile_id,
        device_class=report.profile.device_class,
        stt_ready=stt_ready,
        stt_selected_device=stt_selected_device,
        tts_ready=tts_ready,
        tts_selected_device=tts_selected_device,
        llm_ready=llm_ready,
        llm_runtime_name=llm_runtime_name,
        personality_profile_id=personality.profile_id,
        personality_display_name=personality.display_name,
        degraded_conditions=degraded_conditions,
    )

    return summary, report, personality


def print_startup_summary(summary: StartupSummary) -> None:
    """Print a structured startup summary for shell hosts."""

    print("╔══════════════════════════════════════════════╗")
    print("║  JARVIS — Local Voice Assistant              ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  Profile:     {summary.profile_id} ({summary.device_class})")
    print(
        "  STT:         "
        f"{'ready' if summary.stt_ready else 'unavailable'} "
        f"({summary.stt_selected_device})"
    )
    print(
        "  TTS:         "
        f"{'ready' if summary.tts_ready else 'unavailable'} "
        f"({summary.tts_selected_device})"
    )
    print(
        "  LLM:         "
        f"{summary.llm_runtime_name} "
        f"({'ready' if summary.llm_ready else 'unavailable'})"
    )
    print(
        "  Personality: "
        f"{summary.personality_display_name} ({summary.personality_profile_id})"
    )

    if summary.degraded_conditions:
        print("══════════════════════════════════════════════")
        for condition in summary.degraded_conditions:
            print(f"  ⚠  DEGRADED: {condition}")
        print("══════════════════════════════════════════════")
