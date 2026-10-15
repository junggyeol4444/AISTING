"""Stage 044 GUI smoke, Linux virtual Tk display, no Windows TTS/PC probe."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import VOICES, load_settings, save_settings
from ai_broadcaster.synthesis_environment import load_synthesis_environment

with tempfile.TemporaryDirectory() as temp:
    d = Path(temp)
    envpath = d / 'synthesis.json'
    settingspath = d / 'settings.json'
    dbpath = d / 'conversation.sqlite3'
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settingspath)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda value: save_settings(value, settingspath)), \
         patch('ai_broadcaster.desktop.synthesis_environment_path', return_value=envpath), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('subprocess.Popen', side_effect=AssertionError('external process')):
        app = AistingApp()
        try:
            app.update()
            app._tab_nav.set('한국어 TTS 환경 준비')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(), 'text') == '한국어 TTS 환경 준비'
            assert not envpath.exists() and not settingspath.exists() and not dbpath.exists()
            app._synth_preview()
            assert '초안' in app._synth_status.get()
            assert 'ko-KR' in app._synth_result.get('1.0', 'end')
            assert '음성 방식 미정' in app._synth_result.get('1.0', 'end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=False):
                app._synth_save()
            assert not envpath.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._synth_save()
            draft = load_synthesis_environment(envpath, 'undecided',
                          {'installed_voice_name': '', 'rate': 0, 'volume': 85})
            assert draft.engine == 'not_selected'
            assert not settingspath.exists() and not dbpath.exists()
            # Switching the source rejects a stale plan and never installs/runs a model.
            own = next(k for k, v in VOICES.items() if v == 'own_recording')
            app._voice.set(own)
            assert '무효' in app._synth_status.get()
            app._synth_load()
            assert '불러오기 차단' in app._synth_status.get()
            app._synth_preview()
            assert '미설치' in app._synth_result.get('1.0', 'end')
            app._voice.set(next(k for k, v in VOICES.items() if v == 'undecided'))
            app._synth_load()
            assert '불러오기' in app._synth_status.get()
            app._voice_rate.set('2')
            app._synth_load()
            assert '불러오기 차단' in app._synth_status.get()
            app._voice_rate.set('0')
            with patch('ai_broadcaster.desktop.messagebox.askyesno', side_effect=[True, False]):
                app._synth_delete()
            assert envpath.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno', return_value=True):
                app._synth_delete()
            assert not envpath.exists()
            assert not settingspath.exists() and not dbpath.exists()
            print('GUI original roadmap 044 Korean synthesis environment: PASS')
        finally:
            app.destroy()
