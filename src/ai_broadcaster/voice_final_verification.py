"""Roadmap 050: operator-triggered offline voice-chain acceptance rehearsal.

This is evidence for the virtual integration path ONLY. It cannot approve a real
Windows voice, audible quality, usage rights, or a completed broadcast system.
No audio device, OS voice listing, audio files, network, or user PC details used.
"""
from __future__ import annotations

from dataclasses import dataclass
from .dialogue_voice_link import DialogueVoiceLink
from .offline_tts import KoreanVoice
from .offline_chat import parse_script

MAX_CHATS = 30
PENDING_REAL_CHECKS = (
    'Windows 실기기/EXE 및 설치된 ko-KR 목소리 확인 (사용자 직접 확인)',
    '스피커 실제 출력·발음·억양·감정·자연스러움 평가 (사용자 판단)',
    '음성 사용권/동의 증빙 및 실제 목소리 선택 검증 (사용자 확인)',
    '10단계 전체 개발 기준 최종 승인 및 필요한 PC 확인 (사용자 승인 대기)',
    '실제 AI 모델·음성 엔진·아바타/방송 연동 시험 (별도 작업)',
)


@dataclass(frozen=True)
class VoiceFinalReport:
    voice_name: str
    chat_count: int
    checks: tuple[tuple[str, bool], ...]
    pending: tuple[str, ...] = PENDING_REAL_CHECKS

    @property
    def offline_pass(self) -> bool:
        return bool(self.checks) and all(ok for _, ok in self.checks)

    @property
    def real_voice_approved(self) -> bool:
        """Never promote a simulated result to real approval."""
        return False

    def describe(self) -> str:
        lines = [
            '원본 050 · 목소리 작동 통합 점검 (가상 경로만 / 실제 음성 재생 없음)',
            f'가상 목소리 식별자: {self.voice_name} · 모의 채팅 {self.chat_count}건',
            '가상 경로 점검: ' + ('전항목 통과' if self.offline_pass else '미통과'),
        ]
        lines += [('PASS' if ok else 'FAIL') + ' · ' + title for title, ok in self.checks]
        lines += ['실제 목소리 최종 승인: 미완료 · 자동 승인 없음', '사용자/실기기 확인 대기:']
        lines += ['- ' + x for x in self.pending]
        return '\n'.join(lines)


def verify_voice_chain(script: str, *, source: str, selected_name: str,
                       profile: dict) -> VoiceFinalReport:
    """Run 3 independent virtual scenarios on a button press; never persist data.

    An existing voice identifier is *synthetically* supplied as the virtual voice
    list and must never be described as evidence of an installed OS voice.
    """
    messages = parse_script(script)
    if not 2 <= len(messages) <= MAX_CHATS:
        raise ValueError('통합 점검에는 채팅 2~30건이 필요합니다.')
    if source != 'windows_system':
        raise ValueError('Windows 무료 음성 외의 실제 로컬 음성 엔진은 아직 연결되지 않았습니다.')
    voice = KoreanVoice(selected_name)
    options = dict(source=source, selected_name=selected_name,
                   available_voices=(voice,), profile=profile)

    called = []
    def capture(text, v, rate, volume, segment):
        called.append((text, v.name, rate, volume, segment))
        return True

    normal = DialogueVoiceLink(script, **options, virtual_speak=capture)
    initial = normal.status()
    done = normal.run_manual_batch()
    checks = [
        ('버튼 전 미처리 유지 및 실제 출력 호출 없음', initial.state == 'ready' and
         len(initial.pending) == len(messages)),
        ('전체 채팅 FIFO 처리·중복 보존',
         done.state == 'simulated_complete' and
         len(done.completed) == len(messages) and done.pending == () and
         [a.original for a in done.completed] == messages),
        ('한국어 모의 답변 정상 전달',
         bool(called) and all(a.reply.strip() and '모의 답변' in a.reply
                              for a in done.completed)),
        ('선택 목소리 식별자·속도·음량이 모든 구간에 전달',
         all(item[1:4] == (normal.voice.name, normal.rate, normal.volume)
             for item in called) and
         ''.join(item[0] for item in called) ==
         ''.join(a.reply for a in done.completed)),
    ]

    attempts = []
    failed_once = False
    def fault(text, v, rate, volume, segment):
        nonlocal failed_once
        attempts.append((text, v.name, rate, volume, segment))
        # The second chat's first segment fails once. No automatic retry.
        if not failed_once and len(fault_runner.completed) == 1:
            failed_once = True
            return False
        return True

    fault_runner = DialogueVoiceLink(script, **options, virtual_speak=fault)
    before_retry = fault_runner.run_manual_batch()
    attempts_at_failure = len(attempts)
    checks.extend([
        ('가상 중단 시 완료 1건과 미처리 대기열 유지',
         before_retry.state == 'simulated_interrupted' and
         len(before_retry.completed) == 1 and
         len(before_retry.pending) == len(messages) - 1 and
         before_retry.current is not None and
         before_retry.current.original == messages[1] and
         len(before_retry.remaining_segments) > 0),
        ('가상 중단 시 자동 재시도 없음',
         failed_once and attempts_at_failure == len(attempts)),
    ])
    resumed = fault_runner.run_manual_batch()
    checks.append(('운영자 수동 재개 후 전체 채팅 보존',
                   resumed.state == 'simulated_complete' and
                   resumed.pending == () and
                   [a.original for a in resumed.completed] == messages and
                   len(attempts) == len(called) + 1))
    # Separate virtual exception path, and inspect only the sanitized error state.
    def exception(*_):
        raise RuntimeError('PRIVATE_USER_PATH_DO_NOT_SHOW')
    error_runner = DialogueVoiceLink(script, **options, virtual_speak=exception)
    error = error_runner.step()
    checks.append(('가상 오류 시 미처리 원문 유지·내부 예외 문구 비노출',
                   error.state == 'simulated_error' and
                   len(error.pending) == len(messages) and
                   'PRIVATE_USER_PATH' not in error.reason))

    return VoiceFinalReport(normal.voice.name, len(messages), tuple(checks))
