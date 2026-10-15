"""Original 093: real Tk widgets, no outside application/network/automatic data reads."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ai_broadcaster.desktop import AistingApp
from ai_broadcaster.offline_broadcast_journal import OfflineBroadcastJournal
from ai_broadcaster.offline_settings import DEFAULTS

with patch('ai_broadcaster.desktop.load_settings', return_value=deepcopy(DEFAULTS)), \
     patch('ai_broadcaster.desktop.save_settings', side_effect=AssertionError('no setting changes')), \
     patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), \
     patch('subprocess.Popen', side_effect=AssertionError('outside process forbidden')):
    app = AistingApp()
    try:
        app.update()
        label = '가상 기억 검색·다음 회차 연결'
        assert label in app._tab_nav_widget.cget('values')
        app._tab_nav.set(label)
        app._tab_nav_widget.event_generate('<<ComboboxSelected>>')
        app.update()
        app._memory_recall_query.set('보스전')
        app._memory_recall_search()
        assert not app._memory_recall.hits
        j = OfflineBroadcastJournal('지난 게임')
        j.add_mock_event('operator_note', '가상 보스전')
        app._past_memory.add_journal(j)
        app._past_memory_refresh('092 입력')
        app._memory_recall_search()
        assert len(app._memory_recall.hits) == 1
        app._memory_recall_selected.set('1. 지난 게임')
        app._memory_recall_prepare()
        assert app._memory_recall.context is not None
        assert '가상 보스전' in app._memory_recall_text.get('1.0', 'end')
        app._memory_recall_next_question.set('지난번에 뭐했지?')
        app._memory_recall_rehearse()
        assert '모의 답변' in app._memory_recall_text.get('1.0', 'end')
        assert '지난번에 뭐했지?' in app._memory_recall_text.get('1.0', 'end')
        app._memory_recall_query.set('영화')
        assert app._memory_recall.context is None
        app._memory_recall_search()
        assert not app._memory_recall.hits
        app._memory_recall_query.set('보스전')
        app._memory_recall_search()
        app._past_memory.remove_card(0)
        app._past_memory_refresh('092 삭제')
        app._memory_recall_selected.set('1. 지난 게임')
        app._memory_recall_prepare()
        assert app._memory_recall.context is None
        assert '거부' in app._memory_recall_status.get()
        assert app._memory_recall_text.get('1.0', 'end').strip() == ''
    finally:
        app.destroy()
print('STAGE 093 GUI PASS: manual query, opt-in handoff, stale rejection, no external actions')
