"""Original stage 061: offline-only platform chat connection CONTRACT rehearsal.

No real platform client, sockets, tokens, credentials, messages, timers or persistence.
Stage 062 is responsible for later real-time receiving, subject to approval.
"""
from __future__ import annotations

from dataclasses import dataclass

from .offline_settings import PLATFORMS

PLATFORM_CODES = tuple(PLATFORMS.values())


@dataclass(frozen=True)
class ConnectorSnapshot:
    selected: tuple[str, ...]
    connected: tuple[str, ...]
    phase: str
    attempts: int
    error: str = ''

    @property
    def mock_only(self) -> bool:
        return True

    def describe(self) -> str:
        return '\n'.join((
            '원본 061 · 방송 플랫폼 채팅 연결 계약 · 오프라인 모의',
            '선택: ' + (', '.join(self.selected) or '없음'),
            '가상 연결: ' + (', '.join(self.connected) or '없음'),
            f'상태: {self.phase} · 수동 시도: {self.attempts}',
            ('모의 오류: ' + self.error) if self.error else '모의 오류: 없음',
            '실제 치지직·유튜브·트위치 연결: 0건 / 채팅 수신: 0건',
            '계정·토큰·권한·웹소켓·HTTP·OBS·저장·백그라운드 실행 없음',
            '연결 시험 통과는 실제 방송 연결 성공이나 사용자 승인에 해당하지 않습니다.',
        ))


class OfflinePlatformChatConnector:
    """Operator-triggered, in-memory all-or-nothing mock connection state.

    A configured platform does NOT connect until connect() is called. If the
    simulated handshake fails, no platform remains connected. No actual client
    or network function is imported or called by this module.
    """

    def __init__(self, selected: list[str] | tuple[str, ...], *, fail_on: str | None = None):
        if type(selected) not in (list, tuple) or any(type(x) is not str for x in selected):
            raise ValueError('선택한 플랫폼 목록 형식이 잘못됐습니다.')
        if len(set(selected)) != len(selected) or any(x not in PLATFORM_CODES for x in selected):
            raise ValueError('중복 또는 지원하지 않는 방송 플랫폼이 있습니다.')
        if fail_on is not None and fail_on not in PLATFORM_CODES:
            raise ValueError('모의 장애 플랫폼이 유효하지 않습니다.')
        self._selected = tuple(selected)
        self._connected: tuple[str, ...] = ()
        self._phase = '미연결'
        self._attempts = 0
        self._error = ''
        self._fail_on = fail_on

    def snapshot(self) -> ConnectorSnapshot:
        return ConnectorSnapshot(self._selected, self._connected, self._phase,
                                 self._attempts, self._error)

    def connect(self) -> ConnectorSnapshot:
        """A single explicit simulated handshake; never performs I/O."""
        if self._connected:
            raise ValueError('이미 모의 연결 중입니다. 먼저 연결을 해제하세요.')
        if not self._selected:
            raise ValueError('연결할 플랫폼을 방송 설정에서 선택하세요.')
        self._attempts += 1
        # Atomic simulation: a failure must not leave earlier platforms active.
        if self._fail_on in self._selected:
            self._connected = ()
            self._phase = '모의 연결 실패'
            self._error = '선택 플랫폼의 가상 핸드셰이크 실패 · 자동 재시도 없음'
            return self.snapshot()
        self._connected = self._selected
        self._phase = '모의 연결됨 (실제 연결 아님)'
        self._error = ''
        return self.snapshot()

    def set_mock_failure(self, platform: str | None) -> None:
        """069: configure a one-shot *simulated* handshake fault while disconnected.

        Never initiates a connection or a retry; only an explicit connect()
        call can increment attempts. The caller clears the fault after the drill.
        """
        if platform is not None and platform not in PLATFORM_CODES:
            raise ValueError('모의 장애 플랫폼이 유효하지 않습니다.')
        if self._connected:
            raise ValueError('가상 연결 중에는 장애 조건을 변경할 수 없습니다.')
        self._fail_on = platform

    def disconnect(self) -> ConnectorSnapshot:
        self._connected = ()
        self._phase = '수동 모의 연결 해제'
        self._error = ''
        return self.snapshot()
