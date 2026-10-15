"""34단계: 운영자가 선택한 상황별 반응 방향을 읽기 전용으로 검증한다."""
from dataclasses import dataclass
from .personality_preferences import review_preferences

SITUATIONS = ('악성 채팅', '후원 메시지', '모르는 질문', '일반 채팅')

@dataclass(frozen=True)
class ReactionDirectionReport:
    guidance: str
    directions: tuple[tuple[str, str], ...]
    checks: tuple[tuple[str, bool], ...]

    @property
    def passed(self):
        return all(ok for _, ok in self.checks)

    def describe(self):
        lines = ['34단계 · 사용자 지정 반응 방향 점검 (저장·AI 호출 없음)',
                 '반응 방향은 강제 행동 규칙이 아니라 운영자 참고 지침입니다.',
                 f'검사 {sum(ok for _, ok in self.checks)}/{len(self.checks)} 통과']
        lines.extend(('통과' if ok else '실패') + ' · ' + name for name, ok in self.checks)
        lines.append(self.guidance)
        return '\n'.join(lines)


def review_reaction_directions(mode, draft, directions, likes='', dislikes=''):
    if not isinstance(directions, dict):
        raise ValueError('반응 방향은 상황별 텍스트 사전이어야 합니다.')
    if set(directions) - set(SITUATIONS):
        raise ValueError('지원하지 않는 상황입니다.')
    for key, value in directions.items():
        if not isinstance(value, str) or len(value) > 500 or '\x00' in value:
            raise ValueError(f'{key}: 500자 이내의 텍스트만 허용합니다.')
    base = review_preferences(mode, draft, likes, dislikes)
    entries = tuple((key, directions.get(key, '').strip()) for key in SITUATIONS)
    filled = tuple((key, value) for key, value in entries if value)
    extra = '\n'.join(f'- {key}: {value}' for key, value in filled)
    guidance = base.guidance + ('\n운영자 지정 상황별 반응 방향 (선택):\n' + extra if extra else '')
    checks = (('선택 캐릭터 유지', base.persona['name'] in guidance),
              ('기존 성격·말투 유지', base.persona['character'] in guidance and base.persona['style'] in guidance),
              ('선택한 반응 방향 원문 보존', all(value in guidance for _, value in filled)),
              ('미입력 상황에 임의 규칙 없음', all(key not in extra for key, value in entries if not value)))
    return ReactionDirectionReport(guidance, entries, checks)
