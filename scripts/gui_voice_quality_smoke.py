"""Stage 043 Tk quality notes smoke under existing Linux virtual display."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_settings import VOICES, load_settings, save_settings
from ai_broadcaster.voice_material_plan import MaterialItem, VoiceMaterialDraft, save_material_plan
from ai_broadcaster.voice_quality_review import load_quality_review, ASSESSMENT_LABELS

with tempfile.TemporaryDirectory() as temp:
    base=Path(temp)
    planpath=base/'voice_material_draft.json'; qualitypath=base/'quality.json'
    settingspath=base/'settings.json'; dbpath=base/'conversation.sqlite3'
    initial=load_settings(settingspath)
    source=initial['voice_source'] if 'voice_source' in initial else None
    with patch('ai_broadcaster.desktop.load_settings', side_effect=lambda: load_settings(settingspath)), \
         patch('ai_broadcaster.desktop.save_settings', side_effect=lambda d: save_settings(d,settingspath)), \
         patch('ai_broadcaster.desktop.material_plan_path', return_value=planpath), \
         patch('ai_broadcaster.desktop.quality_review_path', return_value=qualitypath), \
         patch('socket.socket.connect', side_effect=AssertionError('network')), \
         patch('sqlite3.connect', side_effect=AssertionError('db')):
        app=AistingApp()
        try:
            app.update()
            app._tab_nav.set('음성 품질 수동 검토')
            app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
            app.update()
            assert app._tabs.tab(app._tabs.select(),'text')=='음성 품질 수동 검토'
            assert not planpath.exists() and not qualitypath.exists()
            app._quality_preview()
            assert '미리보기 실패' in app._quality_status.get()
            app._load_quality_manifest()
            assert '준비표 없음' in app._quality_status.get()
            current=VOICES[app._voice.get()]
            plan=VoiceMaterialDraft(current,(MaterialItem('예시 인사',12),MaterialItem('예시 질문',24)))
            save_material_plan(planpath,plan,operator_confirmed=True)
            app._load_quality_manifest()
            assert app._quality_review is not None
            assert app._quality_alias.get()=='예시 인사'
            app._quality_fields[0].set(ASSESSMENT_LABELS['needs_rework'])
            app._quality_fields[1].set(ASSESSMENT_LABELS['operator_ok'])
            app._quality_note.insert(0,'운영자가 직접 기재')
            app._quality_apply_item()
            assert '보완 필요' in app._quality_result.get('1.0','end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno',return_value=False):
                app._quality_save()
            assert not qualitypath.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno',return_value=True):
                app._quality_save()
            r=load_quality_review(qualitypath,plan)
            assert r.items[0].assessments[0]=='needs_rework'
            assert r.items[0].note=='운영자가 직접 기재'
            assert not settingspath.exists() and not dbpath.exists()
            app._quality_reset()
            app._load_quality_manifest()
            app._quality_load()
            assert app._quality_fields[0].get()==ASSESSMENT_LABELS['needs_rework']
            # If source changes, stale review cannot be reused.
            other=next(label for label,code in VOICES.items() if code!=current)
            app._voice.set(other)
            assert app._quality_review is None
            app._load_quality_manifest()
            assert '불일치' in app._quality_status.get()
            app._voice.set(next(label for label,code in VOICES.items() if code==current))
            app._load_quality_manifest()
            assert app._quality_review is not None
            # Changing the plan invalidates both saved record and UI save.
            changed=VoiceMaterialDraft(current,(MaterialItem('예시 인사',13),MaterialItem('예시 질문',24)))
            save_material_plan(planpath,changed,operator_confirmed=True)
            with patch('ai_broadcaster.desktop.messagebox.askyesno',return_value=True):
                app._quality_save()
            assert '변경' in app._quality_result.get('1.0','end')
            app._quality_load()
            assert '변경' in app._quality_result.get('1.0','end')
            with patch('ai_broadcaster.desktop.messagebox.askyesno',side_effect=[True,False]):
                app._quality_delete()
            assert qualitypath.exists()
            with patch('ai_broadcaster.desktop.messagebox.askyesno',return_value=True):
                app._quality_delete()
            assert not qualitypath.exists()
            assert planpath.exists() and not settingspath.exists() and not dbpath.exists()
            print('GUI original stage 043 operator quality: PASS')
        finally:
            app.destroy()
