"""Original stage 053: inspect *existing* Tk avatar drawing, not external models.

No images, screen capture, local device discovery, networking, storage or audio.
The result is structural evidence of canvas draw calls, not visual quality approval.
"""
from __future__ import annotations

from dataclasses import dataclass

from .avatar_renderer import AvatarFrame, BACKGROUND_COLORS
from .avatar_choices import avatar_choice


@dataclass(frozen=True)
class DisplayCheck:
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AvatarDisplayAudit:
    selected_avatar: str
    checks: tuple[DisplayCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def describe(self) -> str:
        rows = ["원본 053단계 · 기존 Tk 아바타 표시 검증 (실제 모델 아님)",
                "구조 확인: %d/%d · %s" % (sum(check.passed for check in self.checks),
                len(self.checks), "통과" if self.passed else "재점검 필요")]
        for check in self.checks:
            rows.append(("[통과] " if check.passed else "[실패] ") + check.label + " — " + check.detail)
        rows += ["캔버스 그리기 상태 검사일 뿐 실제 화면 시인성·Windows·OBS 출력 검증 아님.",
                 "외부 Live2D/VRM 렌더러 및 모델 로딩·연결·권리·최종 승인: 미검증"]
        return "\n".join(rows)


def _tagged_text(canvas, tag: str) -> str | None:
    matches = canvas.find_withtag(tag)
    if len(matches) != 1:
        return None
    return str(canvas.itemcget(matches[0], "text"))


def _sample_checks(canvas, pose: AvatarFrame, location: str) -> list[DisplayCheck]:
    name = _tagged_text(canvas, "aisting_display_name")
    visible = bool(canvas.find_withtag("aisting_sample_2d"))
    expected_mouth = "aisting_mouth_open" if pose.mouth else "aisting_mouth_closed"
    other_mouth = "aisting_mouth_closed" if pose.mouth else "aisting_mouth_open"
    mouth_ok = (len(canvas.find_withtag(expected_mouth)) == 1 and
                len(canvas.find_withtag(other_mouth)) == 0)
    return [
        DisplayCheck(location + " 샘플 형태", visible and not canvas.find_withtag("aisting_3d_unavailable"),
                     "내장 2D 샘플 도형"),
        DisplayCheck(location + " 캐릭터 이름", name == pose.display_name,
                     "설정된 이름을 별도 항목으로 표시"),
        DisplayCheck(location + " 입 상태", mouth_ok,
                     "현재 프레임/모의 발화 상태와 입 도형 일치"),
        DisplayCheck(location + " 배경", str(canvas.cget("bg")) == BACKGROUND_COLORS[pose.background],
                     "사용자 선택 배경값과 캔버스 색상 일치"),
    ]


def audit_avatar_display(*, avatar: str, name: str, speaking: bool, frame: int,
                         main_canvas, capture_canvas=None,
                         capture_background: str = "남색 스튜디오") -> AvatarDisplayAudit:
    """Read Canvas item metadata only; never starts a process or opens a window."""
    choice = avatar_choice(avatar)
    pose = AvatarFrame(name, speaking, frame)
    if capture_background not in BACKGROUND_COLORS:
        raise ValueError("알 수 없는 별도 창 배경입니다.")
    checks: list[DisplayCheck] = []
    if choice.sample_2d_visible:
        checks.extend(_sample_checks(main_canvas, pose, "본 창"))
        if capture_canvas is None:
            checks.append(DisplayCheck("별도 창 닫힘", True, "운영자가 열지 않아도 정상"))
        else:
            checks.extend(_sample_checks(capture_canvas,
                AvatarFrame(name, speaking, frame, capture_background), "별도 창"))
    else:
        checks += [
            DisplayCheck("3D 미지원 안내", _tagged_text(main_canvas, "aisting_3d_unavailable") == "3D (VRM) 선택됨",
                         "3D 모델·렌더러 없음 명시"),
            DisplayCheck("2D 자동 대체 차단", not main_canvas.find_withtag("aisting_sample_2d") and
                         not main_canvas.find_withtag("aisting_display_name"),
                         "3D 선택 시 2D 샘플을 모델로 표시하지 않음"),
            DisplayCheck("3D 별도 창 차단", capture_canvas is None,
                         "미구현 3D 캡처/출력 창은 열리지 않아야 함"),
        ]
    return AvatarDisplayAudit(avatar, tuple(checks))
