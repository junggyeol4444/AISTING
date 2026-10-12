"""Windows EXE OBS 5.x status probe tab. READ-ONLY, explicit button only."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .obs_readonly import get_obs_snapshot, ObsSnapshot, avatar_capture_diagnostic


class ObsStatusTab(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._port=tk.StringVar(value="4455")
        self._password=tk.StringVar()
        self._status=tk.StringVar(value="연결 안 됨 · 버튼을 눌렀을 때만 내 PC의 OBS 상태를 확인합니다.")
        self._version=tk.StringVar(value="OBS 버전: 미확인")
        self._stream=tk.StringVar(value="방송 송출: 미확인")
        self._capture=tk.StringVar(value="장면을 선택해 소스 상태를 확인할 수 있어요.")
        self._events: queue.SimpleQueue[tuple[str,object]]=queue.SimpleQueue()
        self._working=False
        ttk.Label(self,text="OBS Studio 로컬 연결 확인 (읽기 전용)",
                  font=("Malgun Gothic",12,"bold")).pack(anchor="w",pady=(4,10))
        ttk.Label(self,text="OBS가 PC에 이미 설치돼 있어야 해요. 연결 확인만 하며 방송을 시작하거나 설정을 변경하지 않습니다.",
                  wraplength=560).pack(anchor="w",pady=(0,10))
        row=ttk.Frame(self)
        row.pack(fill="x",pady=(4,5))
        ttk.Label(row,text="로컬 포트",width=13).pack(side="left")
        ttk.Entry(row,textvariable=self._port,width=12).pack(side="left")
        ttk.Label(row,text="암호",width=7).pack(side="left",padx=(15,0))
        ttk.Entry(row,textvariable=self._password,show="*",width=24).pack(side="left",fill="x",expand=True)
        ttk.Label(self,text="암호는 설정 파일에 저장하지 않습니다. 연결 요청에서만 사용합니다.",
                  wraplength=560).pack(anchor="w")
        self._button=ttk.Button(self,text="OBS 연결 상태 확인",command=self._check)
        self._button.pack(anchor="w",pady=13)
        ttk.Label(self,textvariable=self._status,wraplength=560).pack(anchor="w",pady=(0,12))
        ttk.Label(self,textvariable=self._version).pack(anchor="w",pady=2)
        ttk.Label(self,textvariable=self._stream).pack(anchor="w",pady=2)
        ttk.Label(self,text="OBS 장면 목록 (보기만 가능)").pack(anchor="w",pady=(14,5))
        self._scenes=tk.Listbox(self,height=4,activestyle="none",exportselection=False)
        self._scenes.pack(fill="both",expand=True)
        self._inspect_button=ttk.Button(
            self,text="선택 장면 소스 확인 (읽기 전용)",command=self._inspect_scene,
        )
        self._inspect_button.pack(anchor="w",pady=(8,4))
        self._inspect_button.configure(state="disabled")
        ttk.Label(self,text="선택 장면 안의 소스 · OBS에서 설정은 직접 변경").pack(anchor="w",pady=(4,3))
        self._sources=tk.Listbox(self,height=5,activestyle="none",exportselection=False)
        self._sources.pack(fill="both",expand=True)
        ttk.Label(self,textvariable=self._capture,wraplength=560).pack(anchor="w",pady=(7,2))
        ttk.Label(self,text="소스가 있다고 해서 실제 아바타 창이 캡처 중이라는 뜻은 아닙니다.",
                  wraplength=560).pack(anchor="w",pady=(2,3))
        ttk.Label(self,text="실제 송출·장면 전환·OBS 설치·외부 API 연결은 하지 않습니다.",
                  wraplength=560).pack(anchor="w",pady=(2,0))
        self._scenes.bind("<<ListboxSelect>>",lambda _event:self._update_inspect_button())
        self.after(150,self._poll)

    def _update_inspect_button(self) -> None:
        self._inspect_button.configure(
            state="normal" if not self._working and self._scenes.curselection() else "disabled"
        )

    def _inspect_scene(self) -> None:
        selected=self._scenes.curselection()
        if selected and not self._working:
            scene_name=self._scenes.get(selected[0])
            self._check(scene_name=scene_name)

    def _check(self, scene_name: str | None = None)->None:
        if self._working:
            return
        try:
            port=int(self._port.get())
            if not 1<=port<=65535:
                raise ValueError
        except ValueError:
            messagebox.showwarning("포트 확인","OBS 포트를 1~65535 정수로 입력해 주세요.",parent=self)
            return
        password=self._password.get()
        self._working=True
        self._button.configure(state="disabled")
        self._inspect_button.configure(state="disabled")
        self._status.set("내 PC의 OBS WebSocket 상태 확인 중…")
        threading.Thread(target=self._worker,args=(port,password,scene_name),daemon=True).start()

    def _worker(self,port:int,password:str,scene_name:str | None)->None:
        try:
            snapshot=get_obs_snapshot(port=port,password=password,scene_name=scene_name)
        except Exception as exc:
            self._events.put(("error",str(exc)))
        else:
            self._events.put(("ok",snapshot))
        finally:
            password=""  # 암호 로그와 로컬 설정 저장을 하지 않음.

    def _poll(self)->None:
        try:
            while True:
                kind,item=self._events.get_nowait()
                self._working=False
                self._button.configure(state="normal")
                if kind=="error":
                    self._status.set("OBS 연결 확인 실패: "+str(item))
                    self._version.set("OBS 버전: 미확인")
                    self._stream.set("방송 송출: 미확인")
                    self._scenes.delete(0,"end")
                    self._sources.delete(0,"end")
                    self._capture.set("연결 정보를 확인하지 못했습니다. 실제 OBS 설정은 변경하지 않았습니다.")
                else:
                    self._status.set("OBS 읽기 전용 연결 확인 성공")
                    self._version.set(f"OBS {item.obs_version} · WebSocket {item.websocket_version}")
                    self._stream.set("방송 송출: 진행 중" if item.streaming else "방송 송출: 꺼짐")
                    self._scenes.delete(0,"end")
                    for index,scene in enumerate(item.scenes):
                        self._scenes.insert("end",scene)
                        if scene==item.inspected_scene:
                            self._scenes.selection_set(index)
                            self._scenes.see(index)
                    self._sources.delete(0,"end")
                    for source in item.scene_items:
                        enabled="사용" if source.enabled else "꺼짐"
                        kind=source.input_kind or "기타"
                        self._sources.insert(
                            "end",f"[{enabled}] {source.source_name} · {kind} · ID {source.item_id}"
                        )
                    self._capture.set(avatar_capture_diagnostic(item))
                self._update_inspect_button()
        except queue.Empty:
            pass
        self.after(150,self._poll)
