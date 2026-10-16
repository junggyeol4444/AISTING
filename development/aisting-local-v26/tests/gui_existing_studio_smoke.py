"""Run actual Tk studio widgets on Linux/Xvfb; NOT LLM, TTS or OBS evidence."""
from pathlib import Path
import sys
import types
import tkinter as tk
from tempfile import TemporaryDirectory
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'payload' / 'src'))

from ai_broadcaster.original_plan_studio import OriginalPlanStudio
sys.path.insert(0, str(ROOT / "tests"))
from test_v5_official_file_inspection import make_fixture


class StubExistingDesktop:
    # Only a GUI fixture; the actual application supplies .settings from
    # persisted offline_settings. No fake AI/video/speech is generated here.
    settings = {'persona_mode': 'custom',
                'persona': {'name': '기존 저장된 방송인',
                            'style': '맑은 한국어',
                            'character': '활기찬 캐릭터'}}


def main():
    fake = types.ModuleType('ai_broadcaster.offline_settings')
    fake.active_persona = lambda x: x['persona']
    original = sys.modules.get('ai_broadcaster.offline_settings')
    sys.modules['ai_broadcaster.offline_settings'] = fake
    try:
        root = tk.Tk()
        root.title('AISTING existing app local integration - Tk layout only')
        root.geometry('960x740+10+10')
        root.configure(bg='#F4F7FB')
        main_frame = ttk.Frame(root)
        main_frame.pack(fill='both', expand=True)
        studio = OriginalPlanStudio(main_frame, StubExistingDesktop())
        root.update()
        assert studio.saved_persona.get().startswith('기존 저장된 방송인')
        assert '미연결' in studio.state.get()
        assert '미설정' in studio.tts_status.get()
        assert '미확인' in studio.obs_status.get()
        assert '아직 확인하지 않았습니다' in studio.ws_status.get()
        # Exercise the actual read-only static-inspection UI path against a
        # local file fixture. No AI/voice/avatar processes are created.
        with TemporaryDirectory() as fixture_dir:
            make_fixture(Path(fixture_dir))
            studio.project_dir.set(fixture_dir)
            studio._inspect_core_files()
            assert 'ollama_llm' in studio.core_file_status.get()
            assert '실제 AI 응답·음성·Live2D 동작은 여전히 미검증' in studio.core_file_status.get()
        # Only UI-event dispatch is exercised; NO real WebSocket connection.
        studio._events.put(('ws_error', '로컬 UI 문자열 확인'))
        studio._consume_events()
        assert '로컬 UI 문자열 확인' in studio.ws_status.get()
        studio._events.put(('ws_init', types.SimpleNamespace(
            config_name='LOCAL_FIXTURE', model_name='mao_pro',
            model_url='/live2d-models/mao_pro/runtime/mao_pro.model3.json')))
        studio._consume_events()
        assert 'LOCAL_FIXTURE' in studio.ws_status.get()
        assert '실제 AI 응답·TTS·Live2D 동작은 미검증' in studio.ws_status.get()
        # No real model, TTS or OBS is started by rendering this app.
        studios = [widget for widget in main_frame.winfo_children()]
        assert studios
        child_count = len(main_frame.winfo_children())
        studio._open_gpt_sovits_panel()
        root.update()
        popups = [x for x in main_frame.winfo_children() if isinstance(x, tk.Toplevel)]
        assert len(popups) == 1 and 'GPT-SoVITS' in popups[0].title()
        popups[0].destroy()
        studio._open_obs_panel()
        root.update()
        popups = [x for x in main_frame.winfo_children() if isinstance(x, tk.Toplevel)]
        assert len(popups) == 1 and 'OBS' in popups[0].title()
        # UI regression only: the result is inserted into the same observer
        # queue used by the real OBS thread. Not an OBS connection pass.
        expected = types.SimpleNamespace(version='LOCAL_FIXTURE', scene='READ_ONLY', streaming=False)
        studio._events.put(('obs_connected', (expected, '화면·입력 소스 목록 UI 렌더 검사')))
        studio._consume_events()
        root.update()
        assert 'LOCAL_FIXTURE' in studio.obs_status.get()
        assert studio._obs_panel_status is not None
        assert '화면·입력 소스 목록 UI 렌더 검사' in studio._obs_panel_status.get()
        root.tk.call(studio._obs_window.protocol('WM_DELETE_WINDOW'))
        root.update()
        assert studio._obs_panel_status is None
        assert studio._obs_window is None
        studio._events.put(('obs_error', '창 닫힌 뒤 오류 문자열 표시 검사'))
        studio._consume_events()
        root.update()
        assert '창 닫힌 뒤 오류' in studio.obs_status.get()
        try:
            from PIL import ImageGrab
            evidence = ROOT / 'evidence'
            evidence.mkdir(exist_ok=True)
            ImageGrab.grab(bbox=(0, 0, 1020, 800), all_screens=True).save(
                evidence / 'linux_tk_studio_v19_UI_only_NOT_real_live2d.png')
        except Exception as exc:
            print('Screenshot unavailable; GUI checks still ran:', exc)
        assert len(main_frame.winfo_children()) == child_count
        studio.close()
        root.destroy()
        print('Tk real-window layout: PASS (not Windows EXE or real LLM/TTS/OBS)')
    finally:
        if original is None:
            sys.modules.pop('ai_broadcaster.offline_settings', None)
        else:
            sys.modules['ai_broadcaster.offline_settings'] = original


if __name__ == '__main__':
    main()
