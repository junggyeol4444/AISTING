"""32단계: 운영자가 입력한 성격·취향의 오프라인 프롬프트 미리보기.

취향은 운영자 명시 입력만 사용하며 기존 캐릭터/설정을 변경하지 않는다.
"""
from dataclasses import dataclass
from .persona_modes import chosen_persona, persona_guidance

@dataclass(frozen=True)
class PreferenceReview:
    persona: dict[str, str]
    likes: str
    dislikes: str
    guidance: str

    def describe(self) -> str:
        return ("32단계 · 성격 및 취향 반영 (읽기 전용)\n"
                f"성격: {self.persona['character']}\n"
                f"좋아하는 것: {self.likes or '미설정'}\n"
                f"싫어하는 것: {self.dislikes or '미설정'}\n"
                "프롬프트 미리보기:\n" + self.guidance + "\n"
                "※ 실제 AI 응답·자연스러움은 검증하지 않았습니다.")

def _clean(text: str) -> str:
    if not isinstance(text, str) or len(text) > 300 or '\x00' in text:
        raise ValueError('취향은 최대 300글자의 텍스트여야 합니다.')
    return text.strip()

def review_preferences(mode: str, draft: dict[str, str], likes: str = '', dislikes: str = '') -> PreferenceReview:
    persona = chosen_persona(mode, draft)
    likes, dislikes = _clean(likes), _clean(dislikes)
    guidance = persona_guidance(persona)
    if likes:
        guidance += '\n운영자가 설정한 좋아하는 것: ' + likes
    if dislikes:
        guidance += '\n운영자가 설정한 싫어하는 것: ' + dislikes
    return PreferenceReview(persona, likes, dislikes, guidance)
