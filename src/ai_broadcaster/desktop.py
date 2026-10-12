"""AISTING 네이티브 Windows 프로그램 창. HTTP 서버나 브라우저를 실행하지 않는다."""
import tkinter as tk
from tkinter import ttk, messagebox

from .desktop_state import (
    PLATFORM_LABELS, CONTENT_LABELS, PERSONA_LABELS, VOICE_LABELS,
    AVATAR_LABELS, label_for, from_screen,
)
from .operator_settings import load_settings, save_settings, default_settings
from .desktop_chat_tab import LocalChatTab
from .desktop_voice_tab import VoicePreviewTab
from .avatar_animation import SpeechActivity
from .avatar_preview import AvatarPreviewPanel

class AistingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AISTING - AI 방송인")
        self.geometry("740x670")
        self.minsize(620, 560)
        self.configure(background="#f6f8fb")
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TLabel", font=("Malgun Gothic", 10))
        style.configure("TButton", font=("Malgun Gothic", 10))
        style.configure("TNotebook.Tab", padding=(13, 8), font=("Malgun Gothic", 10))
        try:
            self.settings = load_settings()
            load_error = None
        except (OSError, ValueError) as exc:
            self.settings = default_settings()
            load_error = str(exc)

        main = ttk.Frame(self, padding=18)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="AISTING  |  AI 방송인", font=("Malgun Gothic", 19, "bold")).pack(anchor="w")
        ttk.Label(main, text="Windows 프로그램 · 로컬 PC에서 실행 · 무료 서비스만 사용").pack(anchor="w", pady=(3, 14))
        pages = ttk.Notebook(main)
        pages.pack(fill="both", expand=True)
        basic, person, chat, voice_preview, avatar, status = (
            ttk.Frame(pages, padding=13) for _ in range(6)
        )
        pages.add(basic, text="방송 설정")
        pages.add(person, text="캐릭터 · 목소리")
        pages.add(chat, text="AI 대화 테스트")
        pages.add(voice_preview, text="무료 음성 미리 듣기")
        pages.add(avatar, text="2D 아바타")
        pages.add(status, text="진행 현황")
        self._create_basic(basic)
        self._create_person(person)
        self._speech_activity = SpeechActivity()
        LocalChatTab(chat, activity=self._speech_activity).pack(fill="both", expand=True)
        VoicePreviewTab(voice_preview, activity=self._speech_activity).pack(fill="both", expand=True)
        AvatarPreviewPanel(
            avatar,
            activity=self._speech_activity,
            get_name=lambda: (
                self.fields["name"].get() if self.mode.get() == "직접 만들기"
                else default_settings()["persona"]["name"]
            ),
        ).pack(fill="both", expand=True)
        self._create_status(status)
        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(13, 0))
        self.status_text = tk.StringVar(value="설정 준비 완료" if not load_error else "설정 파일 읽기 실패")
        ttk.Label(footer, textvariable=self.status_text).pack(side="left")
        ttk.Button(footer, text="설정 저장", command=self.save).pack(side="right")
        if load_error:
            messagebox.showwarning("설정 오류", "기존 파일을 읽지 못해 기본값을 표시합니다. 원래 파일은 유지합니다.\n" + load_error, parent=self)

    def _group(self, tab, title):
        area = ttk.LabelFrame(tab, text=title, padding=12)
        area.pack(fill="x", pady=(0, 13))
        return area

    def _combo(self, tab, var, mapping):
        box = ttk.Combobox(tab, textvariable=var, state="readonly", values=list(mapping), width=35)
        box.pack(anchor="w", pady=7)
        return box

    def _create_basic(self, tab):
        group = self._group(tab, "1. 방송 플랫폼 (복수 선택 가능)")
        self.platforms = {}
        for label, code in PLATFORM_LABELS.items():
            var = tk.BooleanVar(value=code in self.settings["platforms"])
            self.platforms[label] = var
            ttk.Checkbutton(group, text=label, variable=var).pack(anchor="w", pady=4)
        ttk.Label(group, text="선택하지 않아도 저장할 수 있습니다.").pack(anchor="w")
        group = self._group(tab, "2. 방송 콘텐츠")
        self.content = tk.StringVar(value=label_for(CONTENT_LABELS, self.settings["content"]))
        self._combo(group, self.content, CONTENT_LABELS)
        group = self._group(tab, "확정된 정책")
        for line in ("실행: 내 PC", "유료 프로그램·API·구독·에셋 구매 없음",
                     "설정을 저장해도 방송은 시작되지 않습니다."):
            ttk.Label(group, text=line).pack(anchor="w", pady=4)

    def _create_person(self, tab):
        group = self._group(tab, "3. 캐릭터 선택")
        self.mode = tk.StringVar(value=label_for(PERSONA_LABELS, self.settings["persona"]["mode"]))
        chooser = self._combo(group, self.mode, PERSONA_LABELS)
        chooser.bind("<<ComboboxSelected>>", lambda ev: self._toggle_fields())
        self.fields = {}
        for key, label in (("name", "이름"), ("gender", "성별/설정"),
                           ("traits", "성격"), ("speech_style", "말투")):
            row = ttk.Frame(group)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=12).pack(side="left")
            entry = ttk.Entry(row)
            entry.insert(0, self.settings["persona"][key])
            entry.pack(side="left", fill="x", expand=True)
            self.fields[key] = entry
        self._toggle_fields()
        group = self._group(tab, "4. 목소리")
        self.voice = tk.StringVar(value=label_for(VOICE_LABELS, self.settings["voice"]))
        self._combo(group, self.voice, VOICE_LABELS)
        group = self._group(tab, "5. 아바타")
        self.avatar = tk.StringVar(value=label_for(AVATAR_LABELS, self.settings["avatar"]))
        self._combo(group, self.avatar, AVATAR_LABELS)

    def _toggle_fields(self):
        state = "normal" if self.mode.get() == "직접 만들기" else "disabled"
        for entry in self.fields.values():
            entry.configure(state=state)

    def _create_status(self, tab):
        group = self._group(tab, "현재 EXE에 구현된 기능")
        for line in (
            "완료: Windows용 프로그램 창과 설정 저장",
            "완료: 무료 로컬 AI 대화 테스트 탭 + SQLite 기억",
            "미완료: 로컬 AI 모델 실제 설치와 응답 검증",
            "테스트용 Windows 한국어 음성 미리 듣기 추가",
            "2D 샘플 아바타와 음성 재생 중 입 움직임 연동",
            "미완료: 정밀 립싱크·실제 Live2D 모델·OBS 송출",
            "미완료: 방송 플랫폼 계정 연결과 방송 시작",
            "예약 작업: 중지 유지",
        ):
            ttk.Label(group, text=line).pack(anchor="w", pady=6)
        ttk.Label(tab, text="이 버전은 설정용 초기 EXE이며 완성된 AI 방송인은 아닙니다.").pack(anchor="w")

    def save(self):
        try:
            result = from_screen(
                self.settings,
                platforms=[name for name, var in self.platforms.items() if var.get()],
                content=self.content.get(),
                persona_mode=self.mode.get(),
                persona_fields={k: v.get() for k, v in self.fields.items()},
                voice=self.voice.get(), avatar=self.avatar.get(),
            )
            save_settings(result)
        except (ValueError, OSError) as exc:
            self.status_text.set("설정 저장 실패")
            messagebox.showerror("저장 실패", str(exc), parent=self)
            return
        self.settings = result
        self.status_text.set("내 PC에 저장 완료. 방송이나 결제는 시작하지 않았습니다.")

def main():
    AistingApp().mainloop()
