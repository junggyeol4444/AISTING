# -*- coding: utf-8 -*-
"""실제 공식 WAV·Cubism 입·OBS 미터의 단일 질문 내 단계별 관측 지연.

단조시계로 이미 관측한 시각만 사용한다. 방송·녹화·음성 재생·계정 접근
없이 계산하며 시청자 E2E, 파형 동일성 또는 음성 사용권의 증명이 아니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class OfficialMediaStageTiming:
    wav_after_prompt_seconds: float | None = None
    mouth_after_wav_seconds: float | None = None
    obs_after_wav_seconds: float | None = None
    obs_minus_mouth_seconds: float | None = None

    @property
    def first_local_audio_seconds(self) -> float | None:
        """이번 질문부터 OBS 선택 입력의 첫 음량 신호까지의 관측 시간."""
        if self.wav_after_prompt_seconds is None or self.obs_after_wav_seconds is None:
            return None
        return round(self.wav_after_prompt_seconds + self.obs_after_wav_seconds, 6)

    @property
    def first_local_mouth_seconds(self) -> float | None:
        """이번 질문부터 공식 Cubism 첫 입 움직임까지의 관측 시간."""
        if self.wav_after_prompt_seconds is None or self.mouth_after_wav_seconds is None:
            return None
        return round(self.wav_after_prompt_seconds + self.mouth_after_wav_seconds, 6)

    @property
    def first_local_audio_video_seconds(self) -> float | None:
        """둘 다 실제 관측된 경우에만 마지막 첫 신호의 로컬 시각차."""
        audio = self.first_local_audio_seconds
        mouth = self.first_local_mouth_seconds
        return round(max(audio, mouth), 6) if audio is not None and mouth is not None else None

    @property
    def local_audio_video_over_three_seconds(self) -> bool | None:
        """로컬 관측 한정 3초 초과. 시청자 종단간 성공 판정이 아니다."""
        total = self.first_local_audio_video_seconds
        return total > 3.0 if total is not None else None

    @property
    def longest_observed_stage_ko(self) -> str:
        """병렬 관측의 인과관계는 추정하지 않고 최장 시간 구간만 표시."""
        if self.first_local_audio_video_seconds is None:
            return "미측정"
        return max((
            (self.wav_after_prompt_seconds, "질문→공식 WAV"),
            (self.mouth_after_wav_seconds, "WAV→Cubism 첫 입"),
            (self.obs_after_wav_seconds, "WAV→OBS 첫 입력"),
        ), key=lambda item: item[0])[1]

    def describe_ko(self) -> str:
        def fmt(value: float | None) -> str:
            return "미측정" if value is None else f"{value:+.3f}초"
        return ("공식 WAV 최초 수신까지 " + fmt(self.wav_after_prompt_seconds)
                + " / WAV→Cubism 첫 입 " + fmt(self.mouth_after_wav_seconds)
                + " / WAV→OBS 첫 입력 미터 " + fmt(self.obs_after_wav_seconds)
                + " / OBS 첫 입력−Cubism 첫 입 " + fmt(self.obs_minus_mouth_seconds)
                + " / 로컬 첫 오디오·입 관측 완료 " + fmt(self.first_local_audio_video_seconds)
                + " / 로컬 3초 초과 " + ("미측정" if self.local_audio_video_over_three_seconds is None
                                       else "예" if self.local_audio_video_over_three_seconds else "아니요")
                + " / 관측 최장 구간 " + self.longest_observed_stage_ko
                + " (관측 콜백 시각차·시청자 전달 미검증)")


def measure_official_media_stages(
    *, prompt_started_at: float, prompt_finished_at: float,
    wav_received_at: float | None, mouth_first_at: float | None,
    obs_first_at: float | None, obs_observation_ended_at: float | None,
    same_utterance_overlap: bool,
) -> OfficialMediaStageTiming:
    """과거·역행·서로 다른 발화의 표본을 같은 단계 지연으로 취급하지 않는다."""
    def valid(value: object) -> bool:
        return type(value) in (int, float) and isfinite(value) and value > 0

    if (not valid(prompt_started_at) or not valid(prompt_finished_at)
            or prompt_finished_at < prompt_started_at):
        return OfficialMediaStageTiming()
    wav = (float(wav_received_at)
           if valid(wav_received_at)
           and prompt_started_at <= wav_received_at <= prompt_finished_at else None)
    mouth = (float(mouth_first_at)
             if wav is not None and valid(mouth_first_at)
             and wav <= mouth_first_at <= prompt_finished_at else None)
    obs = (float(obs_first_at)
           if wav is not None and same_utterance_overlap is True
           and valid(obs_first_at) and valid(obs_observation_ended_at)
           and wav <= obs_first_at <= obs_observation_ended_at else None)
    return OfficialMediaStageTiming(
        wav_after_prompt_seconds=round(wav - prompt_started_at, 6) if wav is not None else None,
        mouth_after_wav_seconds=round(mouth - wav, 6) if mouth is not None else None,
        obs_after_wav_seconds=round(obs - wav, 6) if obs is not None else None,
        obs_minus_mouth_seconds=round(obs - mouth, 6)
        if obs is not None and mouth is not None else None,
    )
