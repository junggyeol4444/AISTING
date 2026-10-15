"""31단계: 기존 사용자 캐릭터 입력의 로컬 무부작용 점검."""
from dataclasses import dataclass
from .persona_modes import chosen_persona, persona_guidance

@dataclass(frozen=True)
class PersonaInputReview:
    mode: str
    fields: dict[str, str]
    guidance: str
    source: str
    def describe(self) -> str:
        return ("31단계 · 캐릭터 페르소나 입력 확인 (읽기 전용)\n"
                + "입력 출처: " + self.source + "\n"
                + "캐릭터 이름: " + self.fields['name'] + "\n"
                + "성격: " + self.fields['character'] + "\n"
                + "말투: " + self.fields['style'] + "\n"
                + "로컬 프롬프트 미리보기:\n" + self.guidance + "\n"
                + "실제 모델/방송/사용자 승인: 미검증 · 공식 진행률 9/100")

def review_persona_input(mode: str, draft: dict[str, str]) -> PersonaInputReview:
    """기존 선택 규칙을 재사용하고, 저장/네트워크/모델 호출은 하지 않는다."""
    fields = chosen_persona(mode, draft)
    return PersonaInputReview(mode, fields, persona_guidance(fields),
                              '기본 캐릭터' if mode == 'default' else '사용자 직접 입력')
