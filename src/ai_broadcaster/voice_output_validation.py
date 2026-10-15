"""Original roadmap 045: isolated Korean TTS output-path rehearsal.

Simulation ONLY: no OS voice enumeration, PC interrogation, audio or subprocess.
Real Windows speaker playback exists separately and requires operator action.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .offline_tts import speech_chunks
from .offline_settings import validate_voice_profile


@dataclass(frozen=True)
class OutputRehearsal:
    segments: tuple[str, ...]
    completed: tuple[str, ...]
    remaining: tuple[str, ...]
    state: str  # simulated_complete | simulated_interrupted | simulated_error
    explanation: str

    def describe(self) -> str:
        parts = ["원본 045 · 한국어 음성 출력 경로 모의 검증 (실제 음성 출력 없음)",
                 f"모의 상태: {self.state}",
                 f"전체 구간: {len(self.segments)} · 처리: {len(self.completed)} · 남음: {len(self.remaining)}",
                 "실제 한국어 음성 재생/음질/Windows 기기 확인은 운영자 수동 검증 대기", ""]
        for i, chunk in enumerate(self.segments, 1):
            status = "모의 처리" if i <= len(self.completed) else "미처리"
            parts.append(f"{i}. [{status}] {chunk}")
        parts.append("처리된 구간과 남은 구간은 원문 순서와 문자를 유지합니다.")
        if self.explanation:
            parts.append("사유: " + self.explanation)
        return "\n".join(parts)


def rehearse_korean_output(text: str, *, source: str, profile: dict,
                           max_chunk: int = 600,
                           virtual_play: Callable[[str, int], bool] | None = None) -> OutputRehearsal:
    """Run virtual sequential synthesis; false means stopped, exception means error.

    Requires operator-selected Windows builtin voice source, NOT a real installed
    voice. Does not infer that one is installed or approve recordings/cloning.
    """
    if source != "windows_system":
        raise ValueError("Windows 무료 음성을 직접 선택한 경우에만 모의 출력 경로를 시험합니다. 다른 음성 모델은 미구성입니다.")
    validated = validate_voice_profile(profile)
    if not isinstance(validated, dict):
        raise ValueError("음성 설정을 확인할 수 없습니다.")
    segments = tuple(speech_chunks(text, maximum=max_chunk))
    played: list[str] = []
    state = "simulated_complete"
    explanation = ""
    for index, segment in enumerate(segments, 1):
        try:
            # The default virtual backend must be inert (no subprocess, no audio).
            response = True if virtual_play is None else virtual_play(segment, index)
            if type(response) is not bool:
                raise ValueError("가상 음성 출력 결과 형식 오류")
            if not response:
                state = "simulated_interrupted"
                explanation = f"{index}번째 구간에서 중단 모의 · 자동 재시도 없음"
                break
        except Exception as exc:
            state = "simulated_error"
            # Do not leak arbitrary exception messages with file paths / secrets.
            explanation = f"{index}번째 구간에서 오류 모의 ({type(exc).__name__}) · 자동 재시도 없음"
            break
        played.append(segment)
    return OutputRehearsal(segments, tuple(played), segments[len(played):], state, explanation)
