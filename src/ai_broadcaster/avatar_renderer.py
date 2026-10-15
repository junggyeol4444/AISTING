"""AISTING 2D 샘플을 두 개의 로컬 Tkinter Canvas에 동일하게 그리는 코드.

OBS나 스트리밍 API를 호출하지 않는다. 정확한 음소 기반 립싱크가 아니라
실제 로컬 음성 프로세스의 재생 상태를 표시하는 애니메이션 샘플이다.
"""
from __future__ import annotations

from dataclasses import dataclass

EXPRESSIONS = ("neutral", "smile", "surprised", "concerned")

BACKGROUND_COLORS = {"남색 스튜디오": "#17223c", "초록색 배경": "#00db53"}


@dataclass(frozen=True)
class AvatarFrame:
    name: str
    speaking: bool
    frame: int
    background: str = "남색 스튜디오"
    expression: str = "neutral"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise ValueError("캐릭터 이름은 문자열이어야 합니다.")
        if type(self.speaking) is not bool:
            raise ValueError("음성 재생 상태는 참/거짓이어야 합니다.")
        if type(self.frame) is not int or self.frame < 0:
            raise ValueError("애니메이션 프레임은 음수가 아닌 정수여야 합니다.")
        if self.background not in BACKGROUND_COLORS:
            raise ValueError("허용된 로컬 아바타 배경이 아닙니다.")
        if type(self.expression) is not str or self.expression not in EXPRESSIONS:
            raise ValueError("허용된 내장 2D 표정이 아닙니다.")

    @property
    def mouth(self) -> int:
        return (1, 2, 3, 2)[self.frame % 4] if self.speaking else 0

    @property
    def blink(self) -> bool:
        return self.frame % 45 in (0, 1)

    @property
    def display_name(self) -> str:
        return self.name.strip()[:24] or "아이스팅"


def draw_avatar(canvas, pose: AvatarFrame) -> None:
    """Tk 메인 이벤트 루프에서만 호출. 외부 입출력/서버 연결 없음."""
    canvas.configure(bg=BACKGROUND_COLORS[pose.background])
    canvas.delete("all")
    canvas.create_oval(65, 22, 310, 285, fill="#344f87", outline="", tags=("aisting_sample_2d",))
    canvas.create_oval(65, 270, 305, 440, fill="#9baeea", outline="")
    canvas.create_oval(107, 80, 265, 282, fill="#f6d3c5", outline="")
    canvas.create_arc(103, 45, 270, 168, start=0, extent=180,
                      fill="#30364f", outline="", style="pieslice")
    for x in (154, 218):
        if pose.blink:
            canvas.create_line(x-12, 170, x+12, 170, fill="#4d4460", width=4,
                               tags=("aisting_eyes_blink",))
        else:
            canvas.create_oval(x-12, 159, x+12, 182, fill="#ffffff", outline="",
                               tags=("aisting_eyes_open",))
            canvas.create_oval(x-7, 162, x+7, 182, fill="#576caf", outline="")
    # 운영자가 선택한 기본 표정만 그린다. AI 감정 자동 판정/실제 Live2D 표정 아님.
    brow_shapes = {
        "neutral": ((141, 140, 166, 139), (204, 139, 229, 140)),
        "smile": ((141, 143, 166, 136), (204, 136, 229, 143)),
        "surprised": ((141, 130, 166, 133), (204, 133, 229, 130)),
        "concerned": ((141, 135, 166, 143), (204, 143, 229, 135)),
    }
    for coords in brow_shapes[pose.expression]:
        canvas.create_line(*coords, fill="#4d4460", width=4,
                           tags=("aisting_expression_" + pose.expression,))
    if pose.expression == "smile":
        for x in (129, 243):
            canvas.create_oval(x-8, 209, x+8, 215, fill="#eaa5a0", outline="",
                               tags=("aisting_expression_smile",))
    elif pose.expression == "surprised":
        canvas.create_oval(176, 223, 196, 241, outline="#9f5069", width=2,
                           tags=("aisting_expression_surprised",))
    elif pose.expression == "concerned":
        canvas.create_arc(176, 239, 196, 252, start=20, extent=140,
                          style="arc", outline="#9f5069", width=2,
                          tags=("aisting_expression_concerned",))
    # 발화 활동 중 반복되는 입 동작으로, 파형/음소 동기화는 구현하지 않음.
    if pose.mouth:
        r = 5 + 3 * pose.mouth
        canvas.create_oval(186-r, 233-r, 186+r, 233+r,
                           fill="#8e4166", outline="", tags=("aisting_mouth_open",))
    else:
        canvas.create_arc(172, 221, 201, 240, start=195, extent=150,
                          style="arc", outline="#9f5069", width=3, tags=("aisting_mouth_closed",))
    canvas.create_text(185, 325, text=pose.display_name, fill="#ffffff",
                       font=("Malgun Gothic", 16, "bold"), tags=("aisting_display_name",))


def draw_unavailable_3d(canvas) -> None:
    """3D 선택 시 2D 캐릭터를 몰래 대체하지 않고 정확한 안내만 표시."""
    canvas.configure(bg=BACKGROUND_COLORS["남색 스튜디오"])
    canvas.delete("all")
    canvas.create_text(185, 139, text="3D (VRM) 선택됨", fill="#ffffff",
                       font=("Malgun Gothic", 20, "bold"), tags=("aisting_3d_unavailable",))
    canvas.create_text(185, 210, text="3D 렌더러·VRM 모델 미설치\n모델 준비와 운영자 승인 후 연결",
                       fill="#d8e0ff", justify="center",
                       font=("Malgun Gothic", 12))
