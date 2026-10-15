"""Offline Windows-style user journey on a real Tk GUI (Xvfb on Linux).

Uses isolated temporary files and a *fake* local AI generator. It is NOT a
Windows, actual TTS, OBS, platform chat, or real model validation.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_chat import LocalMemory
from ai_broadcaster.offline_settings import DEFAULTS, load_settings, save_settings


class FakeLocalGenerator:
    def __init__(self, model, *, content, persona):
        assert model == 'fake-offline-model'
        self.content, self.persona = content, persona

    def set_content(self, content):
        self.content = content

    def set_persona(self, persona):
        self.persona = persona

    def generate(self, chat, history):
        return f'오프라인 가상 답변 {chat.sender}: {chat.text} / 기억 {len(history)}개'


def await_idle(app, *, expected, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.update()
        app._poll()
        if not app._busy and len(app._runner.completed) == expected:
            return
        time.sleep(0.02)
    raise AssertionError(f'GUI reply timeout: busy={app._busy}, status={app._status.get()}, done={len(app._runner.completed)}')


def run():
    with tempfile.TemporaryDirectory(prefix='aisting_operator_journey_') as temp:
        root = Path(temp)
        settings = root / 'settings.json'
        memory = root / 'conversation.sqlite3'
        untouched = root / 'user_existing.txt'
        untouched.write_text('PRESERVE', encoding='utf-8')
        with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settings)), \
             patch('ai_broadcaster.desktop.save_settings', side_effect=lambda data: save_settings(data, settings)), \
             patch('ai_broadcaster.desktop.LocalMemory', side_effect=lambda: LocalMemory(memory)), \
             patch('ai_broadcaster.desktop.LocalOllamaGenerator', FakeLocalGenerator), \
             patch('socket.create_connection', side_effect=AssertionError('external network forbidden')) as network, \
             patch('subprocess.Popen', side_effect=AssertionError('subprocess forbidden')) as process:
            app = AistingApp()
            try:
                app.update()
                assert app._auto_read.get() is False
                assert app._selected_mode.get() == '모의 답변 (인터넷 불필요)'
                assert load_settings(settings) == DEFAULTS
                assert not settings.exists()
                app._platforms['chzzk'].set(True)
                app._platforms['youtube'].set(True)
                app._content.set('수다 + 게임')
                app._persona_mode.set('직접 만들기')
                for key, value in [('name', '가상캐릭터'), ('style', '차분한 한국어'), ('character', '기억을 존중함')]:
                    entry = app._persona[key]
                    entry.delete(0, 'end')
                    entry.insert(0, value)
                app._avatar.set('2D')
                assert app._current_persona()['name'] == DEFAULTS['persona']['name'], (
                    'Uncommitted character draft must not become active'
                )
                app._save_character_identity()
                assert load_settings(settings)['persona']['name'] == '가상캐릭터'
                app._voice.set('Windows 무료 음성')
                app._voice_rate.set('2')
                app._voice_volume.set('75')
                app._save()
                saved = load_settings(settings)
                assert saved['platforms'] == ['chzzk', 'youtube']
                assert saved['content'] == 'both' and saved['avatar'] == '2d'
                assert saved['voice'] == 'windows_system'
                assert saved['voice_profile']['rate'] == 2 and saved['voice_profile']['volume'] == 75
                assert saved['persona_mode'] == 'custom' and saved['persona']['name'] == '가상캐릭터'
                assert not saved['streaming_enabled'] and not saved['scheduled_execution']
                assert not saved['external_publish_enabled']
                app._open_avatar_capture()
                app.update()
                assert app._avatar_capture_window is not None
                app._close_avatar_capture()
                assert app._avatar_capture_window is None
                print('JOURNEY 1: GUI first start/settings/platform/content/persona/voice/avatar/save/2D close PASS')
            finally:
                app._shutdown()
            app = AistingApp()
            try:
                app.update()
                assert app._platforms['chzzk'].get() and app._platforms['youtube'].get()
                assert app._content.get() == '수다 + 게임'
                assert app._persona_mode.get() == '직접 만들기'
                assert app._persona['name'].get() == '가상캐릭터'
                assert app._current_persona()['name'] == '가상캐릭터'
                # Runtime character is still the committed one during edits.
                app._persona['name'].delete(0, 'end')
                app._persona['name'].insert(0, '임시수정-저장안함')
                assert app._current_persona()['name'] == '가상캐릭터'
                app._persona['name'].delete(0, 'end')
                app._persona['name'].insert(0, '가상캐릭터')
                assert app._avatar.get() == '2D' and app._voice.get() == 'Windows 무료 음성'
                assert app._voice_rate.get() == '2' and app._voice_volume.get() == '75'
                app._avatar.set('3D')
                app.update()
                assert str(app._avatar_open_button.cget('state')) == 'disabled'
                app._avatar.set('2D')
                app._script.delete('1.0', 'end')
                app._script.insert('1.0', '가상시청자: 안녕\n가상시청자: 안녕\n두번째: 저장 확인')
                app._enqueue()
                assert len(app._runner.pending) == 3
                app._run_all()
                await_idle(app, expected=3)
                assert len(app._runner.pending) == 0
                assert len(app._runner.completed) == 3
                assert [x.original.text for x in app._runner.completed] == ['안녕', '안녕', '저장 확인']
                assert app._runner.memory is None
                assert not memory.exists(), 'mock mode must not auto-create memory'
                assert app._status.get().startswith('연습 완료')
                print('JOURNEY 2: restart/restored selections/mock FIFO duplicate replies/no DB PASS')
                app._reset_chat()
                app._selected_mode.set('로컬 Ollama (수동 선택)')
                app._model_name.set('fake-offline-model')
                app._script.insert('1.0', '가상시청자: 첫 기억\n다른시청자: 두 번째 기억')
                app._enqueue()
                app._run_all()
                await_idle(app, expected=2)
                assert app._runner.memory_errors == []
                assert [x.original.text for x in LocalMemory(memory).recent()] == ['첫 기억', '두 번째 기억']
                assert '기억 저장 실패' not in app._status.get()
                print('JOURNEY 3: fake local AI (NO real model)/SQLite 2 records PASS')
                app._script.insert('1.0', '가상시청자: 오류 주입')
                app._enqueue()
                with patch.object(app._runner.memory, 'append', side_effect=ValueError('simulated schema swap')):
                    app._run_all()
                    await_idle(app, expected=3)
                assert len(app._runner.memory_errors) == 1
                assert '기억 저장 실패 1건' in app._status.get(), app._status.get()
                assert len(LocalMemory(memory).recent()) == 2, 'failed write must not alter prior memory'
                print('JOURNEY 4: late memory failure shown to user / prior SQLite preserved PASS')
            finally:
                app._shutdown()
            app = AistingApp()
            try:
                app.update()
                assert len(LocalMemory(memory).recent()) == 2
                assert app._platforms['youtube'].get()
                assert untouched.read_text(encoding='utf-8') == 'PRESERVE'
                network.assert_not_called()
                process.assert_not_called()
                print('JOURNEY 5: final restart/persistence/untouched file/no network/no process PASS')
            finally:
                app._shutdown()


if __name__ == '__main__':
    run()
