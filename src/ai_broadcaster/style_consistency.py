"""33단계: 운영자 정의 말투의 읽기 전용 일관성 점검.

실제 모델의 자연스러움 평가가 아닌, 프롬프트/시험 응답의 구조 검사다.
"""
from dataclasses import dataclass
from .personality_preferences import review_preferences


@dataclass(frozen=True)
class StyleConsistencyReport:
    guidance: str
    samples: tuple[str, ...]
    checks: tuple[tuple[str, bool], ...]

    @property
    def passed(self) -> bool:
        return all(ok for _, ok in self.checks)

    def describe(self) -> str:
        lines = ['33단계 · 말투 일관성 구조 점검 (읽기 전용)',
                 '실제 AI 자연스러움·의미적 일관성은 평가하지 않습니다.',
                 f'검사: {sum(ok for _, ok in self.checks)}/{len(self.checks)} 통과']
        lines.extend(('통과' if ok else '실패') + ' · ' + name for name, ok in self.checks)
        lines.append('캐릭터 프롬프트:\n' + self.guidance)
        return '\n'.join(lines)


def check_style_consistency(mode: str, draft: dict[str, str],
                            likes: str = '', dislikes: str = '',
                            samples: tuple[str, ...] = ()) -> StyleConsistencyReport:
    """사용자 입력을 수정·저장·전송하지 않고 검사한다."""
    review = review_preferences(mode, draft, likes, dislikes)
    if not isinstance(samples, (tuple, list)) or len(samples) > 20:
        raise ValueError('시험 응답은 최대 20개입니다.')
    if any(not isinstance(s, str) or len(s) > 2000 or '\x00' in s for s in samples):
        raise ValueError('시험 응답은 2000자 이내의 텍스트여야 합니다.')
    p = review.persona
    checks = [('선택 캐릭터 이름 전달', p['name'] in review.guidance),
              ('선택 성격 전달', p['character'] in review.guidance),
              ('선택 말투 전달', p['style'] in review.guidance),
              ('사용자 취향 반영', (not review.likes or review.likes in review.guidance)
               and (not review.dislikes or review.dislikes in review.guidance)),
              ('응답 텍스트 공백 없음', all(bool(s.strip()) for s in samples)),
              ('응답 순서 및 중복 보존', tuple(samples) == tuple(list(samples)))]
    return StyleConsistencyReport(review.guidance, tuple(samples), tuple(checks))
