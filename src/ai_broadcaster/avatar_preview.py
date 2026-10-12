"""Tkinter Canvas만으로 렌더링하는 무료 2D 아바타 *샘플*.

별도 모델/이미지/라이선스/외부 서버/웹 브라우저 없음.
말하기 상태에 따라 입을 움직이지만 실제 음소·입 모양 싱크는 아님.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .avatar_animation import SpeechActivity, blink_frame, mouth_frame


class AvatarPreviewPanel(ttk.Frame):
    def __init__(
        self, master: tk.Misc, *,
        activity: SpeechActivity,
        get_name: Callable[[], str],
    ) -> None:
        super().__init__(master)
        if not isinstance(activity, SpeechActivity):
            raise TypeError("공유 음성 활동 상태가 필요합니다.")
        self.activity = activity
        self.get_name = get_name
        self._frame = 0
        self._demo = tk.BooleanVar(value=False)
        self._status = tk.StringVar(value="대기 중 · 입 모양은 예시 애니메이션")
        ttk.Label(
            self, text="기본 2D 아바타 미리보기",
            font=("Malgun Gothic", 13, "bold"),
        ).pack(anchor="center", pady=(4, 6))
        ttk.Label(
            self,
            text="EXE 자체 그림으로 만든 샘플입니다. Live2D·3D 모델이 아닙니다.",
            wraplength=620,
        ).pack(pady=(0, 6))
        self.canvas = tk.Canvas(
            self, width=350, height=332,
            bg="#121a36", highlightthickness=0, bd=0,
        )
        self.canvas.pack(pady=(5, 9))
        ttk.Checkbutton(
            self, text="음성 없이 입 움직임 테스트",
            variable=self._demo,
        ).pack(anchor="center")
        ttk.Label(self, textvariable=self._status).pack(pady=(4, 8))
        ttk.Label(
            self,
            text="음성 재생 시 입 움직임은 발화 중 상태를 나타낼 뿐,\n"
                 "실제 음소 분석·립싱크 정확도를 보장하지 않습니다.",
            justify="center",
        ).pack(pady=3)
        self._after_id: str | None = None
        self._draw()
        self._schedule_next()

    def _schedule_next(self) -> None:
        if not self.winfo_exists():
            return
        self._after_id = self.after(110, self._tick)

    def _tick(self) -> None:
        self._after_id = None
        self._frame += 1
        self._draw()
        self._schedule_next()

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        is_voice_active = self.activity.talking
        speaking = is_voice_active or self._demo.get()
        mouth = mouth_frame(speaking, self._frame)
        blink = blink_frame(self._frame)
        # Background stars / gentle studio scene.
        for x,y,r in ((28,30,2),(310,42,3),(45,210,2),(299,243,2),
                      (76,57,2),(266,110,2),(326,195,2)):
            canvas.create_oval(x-r,y-r,x+r,y+r,fill="#6c87cc",outline="")
        canvas.create_oval(53,25,299,274,fill="#24335e",outline="")
        canvas.create_oval(75,45,277,256,fill="#314577",outline="")
        # Shoulder / hoodie.
        canvas.create_oval(68,250,282,396,fill="#8aa6ff",outline="#6b86c8",width=3)
        canvas.create_polygon(
            130,252,175,292,216,251,208,319,142,319,
            fill="#d4ddff",outline="",
        )
        # Ears, hair silhouette, face.
        canvas.create_oval(103,95,250,266,fill="#29334f",outline="")
        canvas.create_oval(92,153,114,198,fill="#ffd8c3",outline="")
        canvas.create_oval(238,153,260,198,fill="#ffd8c3",outline="")
        canvas.create_oval(108,80,242,271,fill="#ffdccc",outline="#c78f8b",width=2)
        canvas.create_polygon(
            108,137,109,99,134,74,180,64,225,85,240,132,
            219,117,204,93,175,120,149,103,126,133,
            fill="#29334f",outline="",
        )
        canvas.create_polygon(110,119,132,90,155,104,139,148,112,160,
                              fill="#29334f",outline="")
        # Eyes / blink.
        if blink:
            for x in (145,207):
                canvas.create_line(x-13,175,x+13,175,fill="#464367",width=3,smooth=True)
        else:
            for x in (145,207):
                canvas.create_oval(x-11,164,x+11,185,fill="#ffffff",outline="")
                canvas.create_oval(x-7,166,x+7,186,fill="#4f69b5",outline="")
                canvas.create_oval(x-3,171,x+3,180,fill="#182647",outline="")
                canvas.create_oval(x-4,169,x-1,172,fill="#ffffff",outline="")
        # Cheeks, mouth (activity-based approximation).
        for x in (123,225):
            canvas.create_oval(x-13,200,x+13,209,fill="#f8a8a5",outline="")
        if mouth == 0:
            canvas.create_arc(163,214,187,226,start=185,extent=170,
                              style="arc",outline="#a04b68",width=3)
        else:
            sizes={1:(10,6),2:(16,12),3:(20,19)}
            w,h=sizes[mouth]
            canvas.create_oval(175-w/2,218-h/2,175+w/2,218+h/2,
                               fill="#833d61",outline="#b6657b",width=2)
        # Hairpins, label and small speaking marker.
        canvas.create_polygon(226,118,231,112,238,119,232,126,
                              fill="#e9c56d",outline="")
        name=self.get_name()
        if not isinstance(name,str) or not name.strip():
            name="아이스팅"
        name=name.strip()[:24]
        canvas.create_text(175,305,text=name,
                           font=("Malgun Gothic",15,"bold"),fill="#f4f6ff")
        self._status.set(
            "PC 음성 재생 중 · 입 움직임 예시"
            if is_voice_active else
            "입 움직임 테스트 중 (소리 없음)"
            if self._demo.get() else
            "대기 중 · 음성 재생 또는 테스트를 선택하세요"
        )

    def destroy(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id=None
        super().destroy()
