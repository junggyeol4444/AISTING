"""AISTING offline Windows desktop program. No web server or browser.

All chat input is simulated locally. Actual streaming controls are absent.
"""
from __future__ import annotations

import queue
import sqlite3
import threading
import tkinter as tk
from collections import deque
from copy import deepcopy
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

from .brain_stage_review import review_brain
from .persona_input_review import review_persona_input
from .personality_preferences import review_preferences
from .style_consistency import check_style_consistency
from .reaction_directions import SITUATIONS, review_reaction_directions
from .basic_reaction_test import SAMPLE_REACTION_SCRIPT, run_basic_reaction_test
from .response_speed_test import SAMPLE_SPEED_SCRIPT, run_response_speed_test
from .all_chat_policy import AllChatPolicySession
from .platform_chat_connector import OfflinePlatformChatConnector
from .offline_chat_receiver import OfflineChatReceiveBuffer
from .offline_chat_order import OfflineChatOrder
from .offline_chat_integrity import OfflineChatIntegrity
from .offline_chat_reactions import OfflineChatReactions
from .offline_chat_latency import OfflineChatLatencyAudit
from .offline_viewer_context import OfflineViewerContext
from .offline_multi_viewer import OfflineMultiViewerDialogue
from .offline_chat_recovery import OfflineChatConnectionRecovery
from .offline_chat_communication_audit import run_offline_chat_communication_audit
from .offline_broadcast_scene import BroadcastSceneDraft, draw_broadcast_scene
from .offline_avatar_screen_link import inspect_avatar_screen_link
from .offline_broadcast_voice_link import OfflineBroadcastVoiceLink
from .offline_broadcast_output_audit import audit_broadcast_output
from .offline_broadcast_output_settings import prepare_offline_output_settings
from .offline_private_broadcast_rehearsal import rehearse_private_broadcast
from .offline_chat_voice_screen_integration import run_offline_chat_voice_screen_integration
from .offline_broadcast_duration import BroadcastDurationRules
from .offline_broadcast_closing import OfflineBroadcastClosing
from .offline_broadcast_closing_audit import run_offline_closing_audit
from .offline_start_control import OfflineStartController
from .offline_full_cycle_audit import run_offline_full_cycle_audit
from .offline_broadcast_automation_audit import run_offline_broadcast_automation_audit
from .offline_prebroadcast_notice import make_prebroadcast_notice
from .offline_notice_variation import NoticeVariationOptions, make_notice_variation
from .offline_end_notice import create_offline_end_notice
from .offline_broadcast_journal import OfflineBroadcastJournal, EVENT_KINDS
from .offline_past_broadcast_memory import OfflinePastBroadcastMemory
from .offline_memory_recall import OfflineMemoryRecall
from .offline_program_recovery import run_offline_program_recovery_audit, RecoveryDenied
from .offline_broadcast_safety import run_offline_broadcast_safety_audit, SafetyDenied
from .offline_operating_cost import COST_FIELDS, estimate_operating_cost, CostInputError
from .offline_unattended_endurance import run_virtual_unattended_endurance
from .offline_multisession_stability import run_virtual_multisession_stability
from .offline_operator_maintenance import (OfflineOperatorMaintenance, CHECKS, STATUSES,
                                          export_maintenance_snapshot)
from .offline_final_acceptance import (
    build_final_acceptance, inspect_bundled_project, export_final_acceptance,
)
from .offline_discord_notice_link import prepare_discord_notice_dry_run
from .offline_naver_cafe_review import review_naver_cafe_official_link
from .offline_notice_posting_rehearsal import OfflineNoticePostingRehearsal
from .offline_broadcast_schedule import (
    BroadcastScheduleDraft, WEEKDAYS, parse_reference, schedule_path,
    save_schedule, load_schedule, delete_schedule,
)
from .idle_speech import IdleSpeechSession
from .character_dialogue_review import (
    SAMPLE_CHARACTER_SCRIPT, VERDICTS, review_character_dialogue, assess_character_dialogue,
)
from .voice_material_plan import (
    VoiceMaterialDraft, parse_material_lines, material_plan_path,
    save_material_plan, load_material_plan, delete_material_plan,
)
from .synthesis_environment import (
    build_synthesis_environment, synthesis_environment_path,
    save_synthesis_environment, load_synthesis_environment, delete_synthesis_environment,
)
from .voice_quality_review import (
    ASSESSMENTS, ASSESSMENT_LABELS, CRITERIA, CRITERION_LABELS,
    blank_quality_review, set_quality_item, quality_review_path,
    save_quality_review, load_quality_review, delete_quality_review,
)
from .voice_rights_review import (
    VoiceRightsReview, rights_review_path, save_rights_review,
    load_rights_review, delete_rights_review,
)
from .operator_feedback import (
    CATEGORIES as FEEDBACK_CATEGORIES, draft_feedback, feedback_path,
    add_feedback, revise_feedback, delete_feedback, list_feedback,
)
from .operator_boundaries import (
    MAX_LINES, validate_boundaries, review_boundaries, boundaries_path,
    save_boundaries, load_boundaries, delete_boundaries,
)
from .offline_settings import (
    AVATARS, CONTENTS, PLATFORMS, VOICES, PERSONA_MODES, DEFAULTS,
    load_settings, save_settings, validate_voice_profile, active_persona,
)
from .offline_chat import ChatRehearsal, MockReplyGenerator, LocalOllamaGenerator, LocalMemory
from .offline_tts import WindowsKoreanSpeech, KoreanVoice, speech_chunks
from .voice_output_validation import rehearse_korean_output
from .selected_voice_routing import rehearse_selected_voice
from .dialogue_voice_link import DialogueVoiceLink
from .avatar_voice_mouth import VoiceMouthRehearsal
from .avatar_voice_sync import VirtualVoiceMouthSync
from .avatar_motion_review import AvatarMotionReview
from .avatar_layout import (AvatarLayout, draw_layout_preview, layout_path,
                           save_layout, load_layout, delete_layout)
from .avatar_endurance import run_virtual_endurance, audit_canvas_repetition, ALLOWED_HOURS
from .avatar_integration_review import audit_avatar_integration
from .voice_final_verification import verify_voice_chain
from .pronunciation_review import (
    LABELS as PRON_LABELS, parse_phrases, blank_review as blank_pronunciation_review,
    update_item as update_pronunciation_item, review_path as pronunciation_review_path,
    save_review as save_pronunciation_review, load_review as load_pronunciation_review,
    delete_review as delete_pronunciation_review,
)
from .emotion_expression_review import (
    LABELS as EMOTION_LABELS, blank_review as blank_emotion_review,
    update_item as update_emotion_item, review_path as emotion_review_path,
    save_review as save_emotion_review, load_review as load_emotion_review,
    delete_review as delete_emotion_review,
)
from .voice_choices import describe_voice_source, preferred_installed_voice
from .avatar_renderer import AvatarFrame, BACKGROUND_COLORS, draw_avatar, draw_unavailable_3d
from .avatar_choices import avatar_choice
from .avatar_display_validation import audit_avatar_display
from .avatar_expressions import (
    EXPRESSIONS as AVATAR_EXPRESSIONS, AvatarExpressionChoice, expression_path,
    save_expression, load_expression, delete_expression, expression_matches,
)
from .avatar_preparation import (AvatarPreparation, ORIGINS as AVATAR_ORIGINS, preparation_path,
                                 save_preparation, load_preparation, delete_preparation)
from .avatar_runtime_environment import (AvatarRuntimeDraft, RENDERERS as AVATAR_RENDERERS, runtime_environment_path, save_runtime_environment, load_runtime_environment, delete_runtime_environment)
from .content_modes import content_preview
from .persona_modes import chosen_persona
from .persona_drafts import EXAMPLE_DRAFTS, apply_draft_example, compact_persona_preview, preview_persona_guidance
from .local_runtime import local_operation_plan, check_local_storage
from .os_readiness import (
    OS_LABELS, ARCH_LABELS, ManualOsChoice, assess_manual_os,
    os_note_path, load_os_note, save_os_note, delete_os_note,
)
from .hardware_readiness import (
    ManualHardwareChoice, review_manual_hardware, hardware_note_path,
    load_hardware_note, save_hardware_note, delete_hardware_note,
)
from .development_scope import review_development_scope
from .software_cost_guide import build_software_cost_guide
from .workspace_setup import workspace_plan, create_workspace
from .runtime_profile import MODES as RUNTIME_MODES, RuntimeProfile, profile_path, load_profile, save_profile, delete_profile
from .manual_archive import plan_archive, create_archive, verify_archive
from .backup_recovery import inspect_backup, stage_recovery, STAGING_NAME
from .execution_selfcheck import run_execution_selfcheck
from .core_foundation import build_core_blueprint
from .core_execution import (
    OfflineCoreSession, CoreBatchError, CoreGenerationError,
    CoreInvalidReplyError, CoreRetryLimitError,
)
from .core_ai_probe import simulate_connection_test, probe_local_model
from .korean_dialogue_test import SAMPLE_KOREAN_SCRIPT, run_korean_dialogue_test
from .context_retention_test import SAMPLE_CONTEXT_SCRIPT, run_context_retention_test
from .response_error_test import SCENARIO_LABELS, run_response_error_test
from .response_records import ResponseRecordStore, snapshot_core_responses, response_records_path
from .conversation_continuity import check_saved_continuity
from .core_ai_connection import (
    build_core_ai_plan, core_ai_profile_path, save_core_ai_plan,
    load_core_ai_plan, delete_core_ai_plan,
)
from .development_review import (
    load_review_sources, evaluate_review, approval_path, approval_status,
    record_approval, revoke_approval, bundled_project_root,
)


def _label_for(options: dict[str, str], code: str) -> str:
    return next((key for key, value in options.items() if value == code), next(iter(options)))


class AistingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AISTING | 내 AI 방송인")
        # Keep bottom controls above the Windows taskbar on 768p laptops.
        # The settings tab has its own scrollbar for longer content.
        self.geometry(f"900x{min(720, max(625, self.winfo_screenheight() - 130))}+50+0")
        self.minsize(820, 625)
        self._save_problem = ""
        try:
            self.settings = load_settings()
        except (OSError, ValueError) as exc:
            self.settings = deepcopy(DEFAULTS)
            self._save_problem = str(exc)
        self._events: queue.SimpleQueue[tuple[str, object]] = queue.SimpleQueue()
        self._runner = ChatRehearsal()
        self._busy = False
        self._configured = False
        self._stop_requested = threading.Event()
        self._avatar_frame = 0
        self._avatar_expression = tk.StringVar(value="기본")
        self._closing = False
        self._poll_after_id: str | None = None
        self._avatar_after_id: str | None = None
        self._avatar_capture_window: tk.Toplevel | None = None
        self._avatar_capture_canvas: tk.Canvas | None = None
        self._avatar_capture_background = tk.StringVar(value="남색 스튜디오")
        self._avatar_capture_status = tk.StringVar(value="별도 창: 닫힘")
        self._avatar_demo = tk.BooleanVar(value=False)
        self._status = tk.StringVar(value="오프라인 개발본 · 자동 업로드/예약/실제 방송 없음")
        self._counts = tk.StringVar(value="대기 0개 · 처리 0개")
        self._selected_mode = tk.StringVar(value="모의 답변 (인터넷 불필요)")
        self._model_name = tk.StringVar()
        # Windows의 기본 음성 합성만 사용하며, 클릭 전 소리/프로세스는 시작하지 않는다.
        self._speaker = WindowsKoreanSpeech()
        self._speech_busy = False
        self._speech_cancel = threading.Event()
        self._speech_pending: deque[str] = deque()
        self._voices: dict[str, KoreanVoice] = {}
        self._voice_name = tk.StringVar()
        self._voice_preferred_name = self.settings["voice_profile"]["installed_voice_name"]
        self._voice_rate = tk.StringVar(value=str(self.settings["voice_profile"]["rate"]))
        self._voice_volume = tk.StringVar(value=str(self.settings["voice_profile"]["volume"]))
        self._speech_text = tk.StringVar(value="안녕하세요! 저는 아이스팅이에요.")
        self._auto_read = tk.BooleanVar(value=False)
        self._speech_status = tk.StringVar(value="기본 꺼짐 · 사용자가 눌러야 음성을 재생합니다.")
        self._last_reply: str | None = None

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        # A development notebook may contain 100+ diagnostic pages. Never show
        # those as a huge strip of unreadable, grey native tabs to operators.
        style.layout("Operator.TNotebook.Tab", [])
        style.configure("TLabel", font=("Malgun Gothic", 10))
        style.configure("TButton", font=("Malgun Gothic", 10), padding=(10, 6))
        style.configure("Operator.Title.TLabel", font=("Malgun Gothic", 21, "bold"))
        style.configure("Operator.Section.TLabel", font=("Malgun Gothic", 13, "bold"))

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 9))
        ttk.Label(header, text="AISTING", style="Operator.Title.TLabel").pack(side="left")
        ttk.Label(
            header, text="내 PC에서 준비하는 AI 방송인  ·  외부 방송 꺼짐",
        ).pack(side="right")
        navigation = ttk.Frame(main)
        navigation.pack(fill="x", pady=(0, 11))
        self._tab_nav = tk.StringVar(value="방송 설정")
        # Keep all original development screens reachable through this opt-in
        # selector; day-to-day actions have their own one-click navigation.
        for label in ("방송 설정", "내 캐릭터", "시청자 채팅 연습", "무료 한국어 음성", "아바타 미리보기"):
            ttk.Button(
                navigation, text=label, command=lambda target=label: self._navigate_to(target),
            ).pack(side="left", padx=(0, 5))
        advanced = ttk.Frame(navigation)
        advanced.pack(side="right")
        ttk.Label(advanced, text="전체 도구").pack(side="left", padx=(0, 5))
        self._tab_nav_widget = ttk.Combobox(
            advanced, textvariable=self._tab_nav, state="readonly", width=19,
        )
        self._tab_nav_widget.pack(side="left")
        tabs = ttk.Notebook(main, style="Operator.TNotebook")
        self._tabs = tabs
        tabs.pack(fill="both", expand=True)
        settings = ttk.Frame(tabs)
        character_editor = ttk.Frame(tabs, padding=14)
        rehearsal = ttk.Frame(tabs, padding=12)
        avatar = ttk.Frame(tabs, padding=12)
        voice_test = ttk.Frame(tabs, padding=12)
        local_operation = ttk.Frame(tabs, padding=12)
        os_review = ttk.Frame(tabs, padding=12)
        hardware_review = ttk.Frame(tabs, padding=12)
        scope_review = ttk.Frame(tabs, padding=12)
        software_cost = ttk.Frame(tabs, padding=12)
        workspace = ttk.Frame(tabs, padding=12)
        runtime = ttk.Frame(tabs, padding=12)
        archive_tab = ttk.Frame(tabs, padding=12)
        recovery_tab = ttk.Frame(tabs, padding=12)
        selfcheck_tab = ttk.Frame(tabs, padding=12)
        core_tab = ttk.Frame(tabs, padding=12)
        core_run_tab = ttk.Frame(tabs, padding=12)
        core_ai_tab = ttk.Frame(tabs, padding=12)
        core_probe_tab = ttk.Frame(tabs, padding=12)
        korean_test_tab = ttk.Frame(tabs, padding=12)
        context_test_tab = ttk.Frame(tabs, padding=12)
        response_error_tab = ttk.Frame(tabs, padding=12)
        response_records_tab = ttk.Frame(tabs, padding=12)
        continuity_tab = ttk.Frame(tabs, padding=12)
        brain_review_tab = ttk.Frame(tabs, padding=12)
        persona_input_tab = ttk.Frame(tabs, padding=12)
        preferences_tab = ttk.Frame(tabs, padding=12)
        style_tab = ttk.Frame(tabs, padding=12)
        reaction_tab = ttk.Frame(tabs, padding=12)
        boundaries_tab = ttk.Frame(tabs, padding=12)
        reaction_test_tab = ttk.Frame(tabs, padding=12)
        speed_test_tab = ttk.Frame(tabs, padding=12)
        all_chat_tab = ttk.Frame(tabs, padding=12)
        idle_speech_tab = ttk.Frame(tabs, padding=12)
        feedback_tab = ttk.Frame(tabs, padding=12)
        character_dialogue_tab = ttk.Frame(tabs, padding=12)
        voice_rights_tab = ttk.Frame(tabs, padding=12)
        voice_material_tab = ttk.Frame(tabs, padding=12)
        voice_quality_tab = ttk.Frame(tabs, padding=12)
        synthesis_environment_tab = ttk.Frame(tabs, padding=12)
        voice_output_tab = ttk.Frame(tabs, padding=12)
        selected_voice_tab = ttk.Frame(tabs, padding=12)
        pronunciation_tab = ttk.Frame(tabs, padding=12)
        emotion_tab = ttk.Frame(tabs, padding=12)
        dialogue_voice_tab = ttk.Frame(tabs, padding=12)
        voice_final_tab = ttk.Frame(tabs, padding=12)
        avatar_preparation_tab = ttk.Frame(tabs, padding=12)
        avatar_environment_tab = ttk.Frame(tabs, padding=12)
        avatar_display_tab = ttk.Frame(tabs, padding=12)
        avatar_expression_tab = ttk.Frame(tabs, padding=12)
        avatar_mouth_tab = ttk.Frame(tabs, padding=12)
        avatar_sync_tab = ttk.Frame(tabs, padding=12)
        avatar_motion_tab = ttk.Frame(tabs, padding=12)
        avatar_layout_tab = ttk.Frame(tabs, padding=12)
        avatar_endurance_tab = ttk.Frame(tabs, padding=12)
        avatar_integration_tab = ttk.Frame(tabs, padding=12)
        platform_chat_tab = ttk.Frame(tabs, padding=12)
        receive_tab = ttk.Frame(tabs, padding=12)
        order_tab = ttk.Frame(tabs, padding=12)
        integrity_tab = ttk.Frame(tabs, padding=12)
        reactions_tab = ttk.Frame(tabs, padding=12)
        latency_tab = ttk.Frame(tabs, padding=12)
        viewer_context_tab = ttk.Frame(tabs, padding=12)
        multi_viewer_tab = ttk.Frame(tabs, padding=12)
        chat_recovery_tab = ttk.Frame(tabs, padding=12)
        chat_communication_tab = ttk.Frame(tabs, padding=12)
        broadcast_scene_tab = ttk.Frame(tabs, padding=12)
        broadcast_schedule_tab = ttk.Frame(tabs, padding=12)
        prebroadcast_notice_tab = ttk.Frame(tabs, padding=12)
        notice_variation_tab = ttk.Frame(tabs, padding=12)
        discord_notice_tab = ttk.Frame(tabs, padding=12)
        cafe_review_tab = ttk.Frame(tabs, padding=12)
        notice_post_tab = ttk.Frame(tabs, padding=12)
        end_notice_tab = ttk.Frame(tabs, padding=12)
        automation_audit_tab = ttk.Frame(tabs, padding=12)
        broadcast_journal_tab = ttk.Frame(tabs, padding=12)
        past_memory_tab = ttk.Frame(tabs, padding=12)
        memory_recall_tab = ttk.Frame(tabs, padding=12)
        program_recovery_tab = ttk.Frame(tabs, padding=12)
        broadcast_safety_tab = ttk.Frame(tabs, padding=12)
        operating_cost_tab = ttk.Frame(tabs, padding=12)
        unattended_endurance_tab = ttk.Frame(tabs, padding=12)
        multisession_tab = ttk.Frame(tabs, padding=12)
        operator_maintenance_tab = ttk.Frame(tabs, padding=12)
        final_acceptance_tab = ttk.Frame(tabs, padding=12)
        review = ttk.Frame(tabs, padding=12)
        about = ttk.Frame(tabs, padding=12)
        for tab, label in ((settings, "방송 설정"), (character_editor, "내 캐릭터"), (rehearsal, "시청자 채팅 연습"),
                           (voice_test, "무료 한국어 음성"), (avatar, "아바타 미리보기"),
                           (local_operation, "PC 로컬 운영"),
                           (os_review, "OS 확인 준비"),
                           (hardware_review, "PC 사양 입력"),
                           (scope_review, "개발 범위 검토"),
                           (software_cost, "프로그램·비용 안내"),
                           (workspace, "개발 작업 공간"),
                           (runtime, "기본 실행 환경"),
                           (archive_tab, "기획안·설정 보관"),
                           (recovery_tab, "백업·복구 준비"),
                           (selfcheck_tab, "개발 환경 자가점검"),
                           (core_tab, "방송 코어 구성도"),
                           (core_run_tab, "기본 코어 수동 실행"),
                           (core_ai_tab, "코어 AI 연결 방식"),
                           (core_probe_tab, "AI 연결 시험"),
                           (korean_test_tab, "한국어 대화 시험"),
                           (context_test_tab, "대화 맥락 전달 시험"),
                           (response_error_tab, "응답 오류 처리 시험"),
                           (response_records_tab, "응답 기록 저장"),
                           (continuity_tab, "대화 연속성 검증"),
                           (brain_review_tab, "AI 두뇌 1차 점검"),
                           (persona_input_tab, "캐릭터 입력 확인"),
                           (preferences_tab, "성격·취향 반영"),
                           (style_tab, "말투 일관성 점검"),
                           (reaction_tab, "반응 방향 설정"),
                           (boundaries_tab, "금기·제한사항 설정"),
                           (reaction_test_tab, "기본 대화 반응 검사"),
                           (speed_test_tab, "응답 속도 관찰"),
                           (all_chat_tab, "전체 채팅 반응 원칙"),
                           (idle_speech_tab, "무채팅 자발 발화 모의"),
                           (feedback_tab, "운영자 피드백 수정 준비"),
                           (character_dialogue_tab, "캐릭터 대화 1차 검증"),
                           (voice_rights_tab, "음성 권리·동의 확인"),
                           (voice_material_tab, "음성 자료 준비표"),
                           (voice_quality_tab, "음성 품질 수동 검토"),
                           (synthesis_environment_tab, "한국어 TTS 환경 준비"),
                           (voice_output_tab, "한국어 음성 출력 모의 검증"),
                           (selected_voice_tab, "선택 목소리 적용 모의"),
                           (pronunciation_tab, "발음·억양 수동 검토"),
                           (emotion_tab, "감정 표현 수동 평가"),
                           (dialogue_voice_tab, "AI 대사·음성 연결 모의"),
                           (voice_final_tab, "목소리 통합 최종 점검"),
                           (avatar_preparation_tab, "아바타 모델 준비표"),
                           (avatar_environment_tab, "아바타 실행 환경 준비"),
                           (avatar_display_tab, "캐릭터 화면 표시 검사"),
                           (avatar_expression_tab, "기본 표정 설정"),
                           (avatar_mouth_tab, "음성·입 움직임 모의"),
                           (avatar_sync_tab, "음성·입 동기화 모의"),
                           (avatar_motion_tab, "표정·움직임 시험"),
                           (avatar_layout_tab, "캐릭터 화면 배치"),
                           (avatar_endurance_tab, "아바타 장시간 모의 시험"),
                           (avatar_integration_tab, "캐릭터 통합 작동 시험"),
                           (platform_chat_tab, "플랫폼 채팅 연결 모의"),
                           (receive_tab, "채팅 수신 모의"),
                           (order_tab, "메시지 순서 관리"),
                           (integrity_tab, "채팅 중복·누락 점검"),
                           (reactions_tab, "전체 채팅 모의 응답"),
                           (latency_tab, "채팅 무지연 모의 시험"),
                           (viewer_context_tab, "시청자 대화 맥락 연결"),
                           (multi_viewer_tab, "여러 시청자 대화 모의"),
                           (chat_recovery_tab, "채팅 연결 장애 복구 모의"),
                           (chat_communication_tab, "채팅 소통 통합 모의 검증"),
                           (broadcast_scene_tab, "방송 화면 구성 미리보기"),
                           (broadcast_schedule_tab, "방송 시작 일정 초안"),
                           (prebroadcast_notice_tab, "방송 전 공지 초안"),
                           (notice_variation_tab, "공지 문구 변주 (오프라인)"),
                           (discord_notice_tab, "디스코드 공지 연결 모의"),
                           (cafe_review_tab, "네이버 카페 공식 연동 검토"),
                           (notice_post_tab, "방송 시작 공지 게시 모의"),
                           (end_notice_tab, "방송 종료 공지·결과 기록"),
                           (automation_audit_tab, "방송 자동화 전체 모의 감사"),
                           (broadcast_journal_tab, "방송 대화·사건 기록 (오프라인)"),
                           (past_memory_tab, "과거 방송 기억 카드 (오프라인)"),
                           (memory_recall_tab, "가상 기억 검색·다음 회차 연결"),
                           (program_recovery_tab, "프로그램 오류 복구 모의 감사"),
                           (broadcast_safety_tab, "방송 이상 감지·안전 제어 모의"),
                           (operating_cost_tab, "운영 비용 수동 예산 계산"),
                           (unattended_endurance_tab, "장시간 무인 방송 모의 안정성"),
                           (multisession_tab, "다회차 방송 안정성 모의 검증"),
                           (operator_maintenance_tab, "운영자 유지보수 수동 점검"),
                           (final_acceptance_tab, "최종 기능 검수·승인 대기"),
                           (review, "개발 기준 검토"), (about, "개발 현황")):
            tabs.add(tab, text=label)
        # The full original development toolset remains reachable from the combo.
        self._tab_nav_widget.configure(values=tuple(tabs.tab(item, "text") for item in tabs.tabs()))

        def navigate(_event=None):
            label = self._tab_nav.get()
            for item in tabs.tabs():
                if tabs.tab(item, "text") == label:
                    tabs.select(item)
                    return

        def sync_navigation(_event=None):
            selected = tabs.select()
            if selected:
                self._tab_nav.set(tabs.tab(selected, "text"))

        self._tab_nav_widget.bind("<<ComboboxSelected>>", navigate)
        tabs.bind("<<NotebookTabChanged>>", sync_navigation)
        # Save is always visible, even on a 768-pixel Windows laptop.
        settings_footer = ttk.Frame(settings, padding=(13, 5))
        settings_footer.pack(side="bottom", fill="x")
        ttk.Label(settings_footer, text="로컬 저장만 합니다 · 실제 송출/예약 실행 안 함").pack(side="left")
        ttk.Button(settings_footer, text="방송 설정 저장", command=self._save).pack(side="right")
        # 설정 항목이 늘어나도 입력란이 잘리지 않도록 스크롤 제공.
        settings_canvas = tk.Canvas(settings, highlightthickness=0, borderwidth=0)
        settings_scrollbar = ttk.Scrollbar(settings, orient="vertical", command=settings_canvas.yview)
        settings_scrollbar.pack(side="right", fill="y")
        settings_canvas.pack(side="left", fill="both", expand=True)
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)
        settings_body = ttk.Frame(settings_canvas, padding=12)
        settings_window = settings_canvas.create_window((0, 0), window=settings_body, anchor="nw")
        settings_body.bind(
            "<Configure>",
            lambda _event: settings_canvas.configure(scrollregion=settings_canvas.bbox("all")),
        )
        settings_canvas.bind(
            "<Configure>",
            lambda event: settings_canvas.itemconfigure(settings_window, width=event.width),
        )
        self._settings_canvas = settings_canvas

        def scroll_settings_under_pointer(event):
            # On Windows, ttk children receive <MouseWheel> instead of the
            # parent canvas. Scroll only when the pointer is inside settings.
            px, py = self.winfo_pointerxy()
            widget = self.winfo_containing(px, py)
            while widget is not None:
                if widget is settings_canvas:
                    if event.delta:
                        steps = max(1, abs(event.delta) // 120)
                        settings_canvas.yview_scroll(
                            steps if event.delta < 0 else -steps, "units"
                        )
                    return "break"
                widget = widget.master
            return None

        self._build_settings(settings_body)
        self._build_character_editor(character_editor)
        # Bind at the *widget* level, before ttk class key handling can stop
        # propagation; binding only "all" did not work with a focused Entry.
        def attach_settings_wheel(widget):
            widget.bind("<MouseWheel>", scroll_settings_under_pointer, add="+")
            for child in widget.winfo_children():
                attach_settings_wheel(child)

        attach_settings_wheel(settings_canvas)
        self._build_rehearsal(rehearsal)
        self._build_voice(voice_test)
        self._build_avatar(avatar)
        self._build_local_operation(local_operation)
        self._build_os_review(os_review)
        self._build_hardware_review(hardware_review)
        self._build_scope_review(scope_review)
        self._build_software_cost_guide(software_cost)
        self._build_workspace_setup(workspace)
        self._build_runtime_profile(runtime)
        self._build_manual_archive(archive_tab)
        self._build_backup_recovery(recovery_tab, archive_tab)
        self._build_execution_selfcheck(selfcheck_tab)
        self._build_core_foundation(core_tab)
        self._build_core_execution(core_run_tab)
        self._build_core_ai_connection(core_ai_tab)
        self._build_core_ai_probe(core_probe_tab)
        self._build_korean_dialogue_test(korean_test_tab)
        self._build_context_retention_test(context_test_tab)
        self._build_response_error_test(response_error_tab)
        self._build_response_records(response_records_tab)
        self._build_continuity(continuity_tab)
        self._build_brain_review(brain_review_tab)
        self._build_persona_input_review(persona_input_tab)
        self._build_style_consistency(style_tab)
        self._build_reaction_directions(reaction_tab)
        self._build_operator_boundaries(boundaries_tab)
        self._build_basic_reaction_test(reaction_test_tab)
        self._build_response_speed_test(speed_test_tab)
        self._build_all_chat_policy(all_chat_tab)
        self._build_idle_speech(idle_speech_tab)
        self._build_operator_feedback(feedback_tab)
        self._build_character_dialogue_review(character_dialogue_tab)
        self._build_voice_rights_review(voice_rights_tab)
        self._build_voice_material_plan(voice_material_tab)
        self._build_voice_quality_review(voice_quality_tab)
        self._build_synthesis_environment(synthesis_environment_tab)
        self._build_voice_output_validation(voice_output_tab)
        self._build_selected_voice_routing(selected_voice_tab)
        self._build_pronunciation_review(pronunciation_tab)
        self._build_emotion_review(emotion_tab)
        self._build_dialogue_voice_link(dialogue_voice_tab)
        self._build_voice_final_verification(voice_final_tab)
        self._build_avatar_preparation(avatar_preparation_tab)
        self._build_avatar_runtime_environment(avatar_environment_tab)
        self._build_avatar_display_validation(avatar_display_tab)
        self._build_avatar_expressions(avatar_expression_tab)
        self._build_avatar_voice_mouth(avatar_mouth_tab)
        self._build_avatar_voice_sync(avatar_sync_tab)
        self._build_avatar_motion_review(avatar_motion_tab)
        self._build_avatar_layout(avatar_layout_tab)
        self._build_avatar_endurance(avatar_endurance_tab)
        self._build_avatar_integration(avatar_integration_tab)
        self._build_platform_chat_connector(platform_chat_tab)
        self._build_offline_chat_receiver(receive_tab)
        self._build_offline_chat_order(order_tab)
        self._build_offline_chat_integrity(integrity_tab)
        self._build_offline_chat_reactions(reactions_tab)
        self._build_offline_chat_latency(latency_tab)
        self._build_offline_viewer_context(viewer_context_tab)
        self._build_offline_multi_viewer(multi_viewer_tab)
        self._build_offline_chat_recovery(chat_recovery_tab)
        self._build_offline_chat_communication_audit(chat_communication_tab)
        self._build_broadcast_scene(broadcast_scene_tab)
        self._build_broadcast_schedule(broadcast_schedule_tab)
        self._build_prebroadcast_notice(prebroadcast_notice_tab)
        self._build_notice_variation(notice_variation_tab)
        self._build_discord_notice_link(discord_notice_tab)
        self._build_naver_cafe_review(cafe_review_tab)
        self._build_notice_post_rehearsal(notice_post_tab)
        self._build_end_notice(end_notice_tab)
        self._build_automation_audit(automation_audit_tab)
        self._build_broadcast_journal(broadcast_journal_tab)
        self._build_past_broadcast_memory(past_memory_tab)
        self._build_memory_recall(memory_recall_tab)
        self._build_program_recovery(program_recovery_tab)
        self._build_broadcast_safety(broadcast_safety_tab)
        self._build_operating_cost(operating_cost_tab)
        self._build_unattended_endurance(unattended_endurance_tab)
        self._build_multisession_stability(multisession_tab)
        self._build_operator_maintenance(operator_maintenance_tab)
        self._build_final_acceptance(final_acceptance_tab)
        self._build_preferences_review(preferences_tab)
        self._build_development_review(review)
        self._build_about(about)
        ttk.Label(main, textvariable=self._status, wraplength=760).pack(anchor="w", pady=(12, 0))
        if self._save_problem:
            messagebox.showwarning("설정 복구", "기존 설정 파일이 유효하지 않아 기본값을 보여줍니다. 원본 파일은 유지됩니다.\n" + self._save_problem, parent=self)
        self._poll_after_id = self.after(120, self._poll)
        self._avatar_after_id = self.after(150, self._avatar_tick)
        self.protocol("WM_DELETE_WINDOW", self._shutdown)

    def _shutdown(self) -> None:
        """PC 음성 및 예약된 Tk 콜백을 종료한다 (백그라운드 예약 개발과 무관)."""
        if self._closing:
            return
        self._closing = True
        for task in (self._poll_after_id, self._avatar_after_id):
            if task is not None:
                try:
                    self.after_cancel(task)
                except tk.TclError:
                    pass
        self._poll_after_id = None
        self._avatar_after_id = None
        self._speech_cancel.set()
        self._speech_pending.clear()
        self._stop_requested.set()
        self._close_avatar_capture()
        try:
            self._speaker.stop()
        finally:
            self.destroy()

    def _navigate_to(self, label: str) -> None:
        """Navigate to a top-level operator page or one of the retained tools."""
        for item in self._tabs.tabs():
            if self._tabs.tab(item, "text") == label:
                self._tabs.select(item)
                self._tab_nav.set(label)
                return
        raise ValueError("화면을 찾을 수 없습니다: " + label)

    def _section(self, parent, title):
        area = ttk.LabelFrame(parent, text=title, padding=9)
        area.pack(fill="x", pady=(0, 11))
        return area

    def _choice(self, parent, choices, current):
        variable = tk.StringVar(value=_label_for(choices, current))
        ttk.Combobox(parent, textvariable=variable, values=list(choices),
                     state="readonly", width=32).pack(anchor="w", pady=4)
        return variable

    def _build_settings(self, tab) -> None:
        ttk.Label(tab, text="방송 설정", style="Operator.Section.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(
            tab, text="방송을 시작하지 않고 준비값만 저장합니다. 캐릭터는 별도로 관리합니다.",
            wraplength=770,
        ).pack(anchor="w", pady=(0, 9))

        summary = self._section(tab, "내 캐릭터 · 저장된 정체성")
        self._saved_character_status = tk.StringVar(value=self._saved_character_description())
        ttk.Label(
            summary, textvariable=self._saved_character_status,
            font=("Malgun Gothic", 11, "bold"), wraplength=750,
        ).pack(anchor="w", pady=(0, 5))
        character_controls = ttk.Frame(summary)
        character_controls.pack(fill="x")
        ttk.Label(
            character_controls,
            text="다음 실행에도 그대로 사용 · 매번 다시 입력할 필요 없음",
        ).pack(side="left")
        ttk.Button(
            character_controls, text="캐릭터 관리",
            command=lambda: self._navigate_to("내 캐릭터"),
        ).pack(side="right")

        selections = ttk.Frame(tab)
        selections.pack(fill="x", pady=(0, 7))
        platform_box = ttk.LabelFrame(selections, text="방송 플랫폼 (복수 선택)", padding=9)
        platform_box.pack(side="left", fill="both", expand=True, padx=(0, 7))
        self._platforms = {}
        platform_row = ttk.Frame(platform_box)
        platform_row.pack(anchor="w", pady=(2, 5))
        for label, code in PLATFORMS.items():
            flag = tk.BooleanVar(value=code in self.settings["platforms"])
            ttk.Checkbutton(
                platform_row, text=label, variable=flag,
            ).pack(side="left", padx=(0, 14))
            self._platforms[code] = flag
        ttk.Label(
            platform_box, text="선택만으로 방송은 시작되지 않습니다.",
            wraplength=320,
        ).pack(anchor="w")

        content_box = ttk.LabelFrame(selections, text="방송 콘텐츠", padding=9)
        content_box.pack(side="left", fill="both", expand=True)
        self._content = self._choice(content_box, CONTENTS, self.settings["content"])
        self._content_preview = tk.StringVar(value=content_preview(CONTENTS[self._content.get()]))
        ttk.Label(
            content_box, textvariable=self._content_preview, wraplength=365,
        ).pack(anchor="w", pady=(3, 0))
        self._content.trace_add("write", self._content_changed)

        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 7))
        avatarbox = ttk.LabelFrame(row, text="아바타 외형 · 캐릭터와 별개", padding=9)
        avatarbox.pack(side="left", fill="both", expand=True, padx=(0, 7))
        voicebox = ttk.LabelFrame(row, text="목소리 선택", padding=9)
        voicebox.pack(side="left", fill="both", expand=True)
        self._avatar = self._choice(avatarbox, AVATARS, self.settings["avatar"])
        self._avatar_choice_info = tk.StringVar(value=avatar_choice(self.settings["avatar"]).description)
        ttk.Label(
            avatarbox, textvariable=self._avatar_choice_info, wraplength=360,
        ).pack(anchor="w", pady=(3, 0))
        self._avatar.trace_add("write", self._avatar_changed)
        self._voice = self._choice(voicebox, VOICES, self.settings["voice"])
        self._voice_source_info = tk.StringVar(value=describe_voice_source(self.settings["voice"]))
        ttk.Label(
            voicebox, textvariable=self._voice_source_info, wraplength=360,
        ).pack(anchor="w", pady=(3, 0))
        self._voice.trace_add("write", self._voice_source_changed)

    def _build_character_editor(self, tab) -> None:
        ttk.Label(tab, text="내 캐릭터", style="Operator.Section.TLabel").pack(anchor="w", pady=(1, 5))
        ttk.Label(
            tab, text="캐릭터는 처음 한 번 만들고 저장합니다. 이후에는 방송·대화에 자동 적용됩니다. "
                      "저장하기 전 초안은 실제 캐릭터를 바꾸지 않습니다.",
            wraplength=750,
        ).pack(anchor="w", pady=(0, 11))
        character = self._section(tab, "캐릭터 처음 만들기 / 직접 수정")
        self._persona_mode = self._choice(character, PERSONA_MODES, self.settings["persona_mode"])
        self._persona = {}
        for key, label in (("name", "이름"), ("style", "말투"), ("character", "성격")):
            line = ttk.Frame(character)
            line.pack(fill="x", pady=3)
            ttk.Label(line, text=label, width=9).pack(side="left")
            entry = ttk.Entry(line)
            entry.insert(0, self.settings["persona"][key])
            entry.pack(side="left", expand=True, fill="x")
            self._persona[key] = entry
        # 성격·말투 초안은 선택 사항이다. 운영자가 명시적으로 눌렀을 때에만 예시를 채운다.
        example_row = ttk.Frame(character)
        example_row.pack(fill="x", pady=(5, 2))
        ttk.Label(example_row, text="성격·말투 참고 초안").pack(side="left")
        self._persona_draft_example = tk.StringVar(value="예시를 선택하세요")
        ttk.Combobox(
            example_row, textvariable=self._persona_draft_example,
            values=("예시를 선택하세요", *EXAMPLE_DRAFTS),
            state="readonly", width=25,
        ).pack(side="left", padx=(8, 6))
        ttk.Button(example_row, text="선택한 초안 적용", command=self._apply_persona_example).pack(side="left")
        ttk.Button(example_row, text="AI 지침 미리보기", command=self._show_persona_guidance).pack(side="left", padx=(6, 0))
        self._persona_preview = tk.StringVar()
        ttk.Label(character, textvariable=self._persona_preview, justify="left",
                  wraplength=715).pack(anchor="w", pady=(5, 0))
        # This is a durable identity, NOT a form to fill out every time.
        # Uncommitted drafts never control chat, the avatar or the AI prompt.
        ttk.Label(
            character, textvariable=self._saved_character_status,
            wraplength=710,
        ).pack(anchor="w", pady=(5, 2))
        ttk.Button(
            character, text="캐릭터 처음 만들기 / 기존 캐릭터 수정 확정·저장",
            command=self._save_character_identity,
        ).pack(anchor="w", pady=(2, 0))
        self._persona_mode.trace_add("write", self._persona_changed)
        for item in self._persona.values():
            item.bind("<KeyRelease>", self._persona_changed)
        self._persona_changed()
        ttk.Button(
            tab, text="방송 설정으로 돌아가기",
            command=lambda: self._navigate_to("방송 설정"),
        ).pack(anchor="e", pady=(6, 0))

    def _avatar_changed(self, *_args) -> None:
        """선택만으로 모델을 설치하지 않는다. 3D에는 2D 샘플 캡처 창을 제공하지 않는다."""
        code = AVATARS.get(self._avatar.get())
        try:
            choice = avatar_choice(code)
        except ValueError:
            self._avatar_choice_info.set("아바타 선택 오류: 미정/2D/3D 중 고르세요.")
            if hasattr(self, "_avatar_open_button"):
                self._avatar_open_button.configure(state="disabled")
            return
        self._avatar_choice_info.set(choice.description)
        if hasattr(self, "_avatar_tab_info"):
            self._avatar_tab_info.set(choice.description)
        if hasattr(self, "_avatar_open_button"):
            self._avatar_open_button.configure(
                state="normal" if choice.can_open_sample_window else "disabled"
            )
        if not choice.can_open_sample_window and self._avatar_capture_window is not None:
            self._close_avatar_capture()
        if hasattr(self, "_avatar_prep_alias"):
            self._avatar_preparation_selection_changed()
        if hasattr(self, "_avatar_env_renderer"):
            self._avatar_runtime_environment_selection_changed()
        if hasattr(self, "_canvas"):
            self._draw_avatar_canvases()
        if hasattr(self, "_avatar_display_status"):
            self._avatar_display_status.set("선택 변경 · 현재 화면 재검사 필요")
        if hasattr(self, "_expression_status"):
            self._avatar_expression.set("기본")
            self._expression_status.set("아바타 형태 변경 · 기본 표정으로 초기화됨 (저장 기록 미적용)")

    def _voice_source_changed(self, *_args) -> None:
        source = VOICES.get(self._voice.get())
        self._voice_source_info.set(
            describe_voice_source(source) if source is not None else "잘못된 목소리 선택"
        )
        if source != "windows_system":
            # 다른 목소리 확보 방식 선택 시 이전 Windows 음성 선택을 실재생에 재사용하지 않음.
            self._auto_read.set(False)
            self._speech_pending.clear()
        self._update_voice_buttons()

    def _content_changed(self, *_args) -> None:
        label = self._content.get()
        # 이 콤보박스는 readonly지만 Tk 변수를 외부에서 수정할 수도 있다.
        code = CONTENTS.get(label)
        self._content_preview.set(content_preview(code) if code is not None else "잘못된 콘텐츠 선택")

    def _current_persona(self) -> dict[str, str]:
        """Always use the committed identity, never an unsaved editor draft."""
        return active_persona(self.settings)

    def _saved_character_description(self) -> str:
        character = active_persona(self.settings)
        if self.settings["persona_mode"] == "default":
            return ("현재 사용: 기본 캐릭터 " + character["name"]
                    + " · 새 캐릭터를 원할 때만 직접 만들기 후 확정·저장")
        return ("현재 사용: 저장된 캐릭터 " + character["name"]
                + " · 시작할 때 자동 불러옴 / 매번 다시 입력할 필요 없음")

    def _save_character_identity(self) -> None:
        """User action to create or change ONE persistent identity, separately."""
        try:
            mode = PERSONA_MODES[self._persona_mode.get()]
            draft = {key: item.get().strip() for key, item in self._persona.items()}
            # Only a validated and explicitly committed draft is usable.
            chosen_persona(mode, draft)
            updated = deepcopy(self.settings)
            updated["persona_mode"] = mode
            updated["persona"] = draft
            save_settings(updated)
        except (KeyError, ValueError, OSError) as exc:
            messagebox.showerror("캐릭터 저장 오류", str(exc), parent=self)
            return
        self.settings = updated
        self._saved_character_status.set(self._saved_character_description())
        self._status.set(
            "캐릭터를 내 PC에 확정·저장했어. 다음 실행에도 이 캐릭터를 그대로 사용해."
        )
        self._draw_avatar_canvases()

    def _persona_changed(self, *_args) -> None:
        is_custom = self._persona_mode.get() == "직접 만들기"
        for entry in self._persona.values():
            entry.configure(state="normal" if is_custom else "disabled")
        try:
            self._persona_preview.set(compact_persona_preview(
                PERSONA_MODES[self._persona_mode.get()],
                {key: entry.get() for key, entry in self._persona.items()},
                max_field=52,
            ))
        except (ValueError, KeyError) as exc:
            self._persona_preview.set("초안을 확인해 주세요: " + str(exc))

    def _apply_persona_example(self) -> None:
        """운영자가 누를 때만 예시 성격·말투를 입력란에 복사하고 이름은 유지."""
        fields = {key: entry.get() for key, entry in self._persona.items()}
        try:
            changed = apply_draft_example(fields, self._persona_draft_example.get())
        except ValueError as exc:
            messagebox.showwarning("성격·말투 참고 초안", str(exc), parent=self)
            return
        self._persona_mode.set("직접 만들기")
        for key in ("character", "style"):
            self._persona[key].delete(0, "end")
            self._persona[key].insert(0, changed[key])
        self._persona_changed()
        self._status.set("참고 초안을 입력란에 채웠어. 언제든 고칠 수 있고, 저장 버튼을 눌러야 PC에 저장돼.")

    def _show_persona_guidance(self) -> None:
        try:
            guidance = preview_persona_guidance(
                PERSONA_MODES[self._persona_mode.get()],
                {key: entry.get() for key, entry in self._persona.items()},
            )
        except (ValueError, KeyError) as exc:
            messagebox.showwarning("AI 지침 확인", str(exc), parent=self)
            return
        messagebox.showinfo("로컬 AI 지침 미리보기 (전송 안 함)", guidance, parent=self)

    def _save(self) -> None:
        data = deepcopy(DEFAULTS)
        data["platforms"] = [code for code, check in self._platforms.items() if check.get()]
        try:
            data["content"] = CONTENTS[self._content.get()]
        except KeyError:
            messagebox.showerror("콘텐츠 설정 오류", "지원하는 콘텐츠를 선택해 주세요.", parent=self)
            return
        try:
            data["avatar"] = avatar_choice(AVATARS.get(self._avatar.get())).code
        except ValueError as exc:
            messagebox.showerror("아바타 설정", str(exc), parent=self)
            return
        try:
            data["voice"] = VOICES[self._voice.get()]
            data["voice_profile"] = validate_voice_profile({
                "installed_voice_name": self._voice_preferred_name,
                "rate": int(self._voice_rate.get()),
                "volume": int(self._voice_volume.get()),
            })
        except (KeyError, ValueError) as exc:
            messagebox.showerror("목소리 설정", str(exc), parent=self)
            return
        # Broadcasting preferences must never silently commit an unapproved
        # character draft. Character creation has its own explicit Save button.
        data["persona_mode"] = self.settings["persona_mode"]
        data["persona"] = deepcopy(self.settings["persona"])
        try:
            save_settings(data)
        except (OSError, ValueError) as exc:
            messagebox.showerror("설정 저장 오류", str(exc), parent=self)
            return
        self.settings = data
        if hasattr(self, "_notice_status"):
            self._notice_invalidate()
        self._status.set("설정을 내 PC에 저장했어. 방송이나 외부 업로드는 시작되지 않았어.")

    def _build_rehearsal(self, tab) -> None:
        ttk.Label(tab, text="한 줄에 '닉네임: 메시지' 형식으로 입력해.").pack(anchor="w")
        self._script = tk.Text(tab, height=6, wrap="word", font=("Malgun Gothic", 10))
        self._script.pack(fill="both", expand=True, pady=(5, 6))
        self._script.insert("1.0", "철수: 안녕\n영희: 오늘은 무슨 게임 해?\n철수: 안녕")
        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Label(row, text="응답 방식").pack(side="left")
        self._mode_widget = ttk.Combobox(row, textvariable=self._selected_mode,
                                         values=("모의 답변 (인터넷 불필요)", "로컬 Ollama (수동 선택)"),
                                         state="readonly", width=26)
        self._mode_widget.pack(side="left", padx=(6, 10))
        ttk.Label(row, text="모델 이름").pack(side="left")
        self._model_input = ttk.Entry(row, textvariable=self._model_name, width=20)
        self._model_input.pack(side="left", fill="x", expand=True, padx=(6, 0))
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=7)
        self._add = ttk.Button(actions, text="대기열에 추가", command=self._enqueue)
        self._add.pack(side="left")
        self._run = ttk.Button(actions, text="모두 답변", command=self._run_all)
        self._run.pack(side="left", padx=(5, 0))
        self._stop = ttk.Button(actions, text="현재 답변 후 중지", command=self._request_stop)
        self._stop.pack(side="left", padx=(5, 0))
        self._stop.configure(state="disabled")
        self._reset = ttk.Button(actions, text="새 연습", command=self._reset_chat)
        self._reset.pack(side="right")
        ttk.Label(tab, textvariable=self._counts).pack(anchor="w")
        self._out = tk.Text(tab, height=13, state="disabled", wrap="word", font=("Malgun Gothic", 10))
        self._out.pack(fill="both", expand=True, pady=(5, 0))
        ttk.Label(tab, text="실제 플랫폼 연결 없음. AI 모델을 선택하지 않으면 외부 통신도 없어.").pack(anchor="w", pady=6)

    def _write(self, line) -> None:
        self._out.configure(state="normal")
        self._out.insert("end", line + "\n")
        self._out.see("end")
        self._out.configure(state="disabled")

    def _count(self) -> None:
        self._counts.set(f"대기 {len(self._runner.pending)}개 · 처리 {len(self._runner.completed)}개")

    def _enqueue(self) -> None:
        if self._busy:
            return
        try:
            amount = self._runner.add_script(self._script.get("1.0", "end-1c"))
        except ValueError as exc:
            messagebox.showwarning("대본 형식", str(exc), parent=self)
            return
        self._script.delete("1.0", "end")
        self._count()
        self._status.set(f"채팅 {amount}개 추가. 모두 답변 버튼을 눌러야 시작해.")

    def _run_all(self) -> None:
        if self._busy or not self._runner.pending:
            return
        if not self._configured:
            try:
                if self._selected_mode.get() == "로컬 Ollama (수동 선택)":
                    generator = LocalOllamaGenerator(
                        self._model_name.get().strip(),
                        content=CONTENTS[self._content.get()],
                        persona=self._current_persona(),
                    )
                    self._runner.generator = generator
                    self._runner.memory = LocalMemory()
                elif self._selected_mode.get() != "모의 답변 (인터넷 불필요)":
                    raise ValueError("알 수 없는 응답 모드")
            except (OSError, ValueError) as exc:
                messagebox.showwarning("로컬 모델 설정", str(exc), parent=self)
                return
            self._configured = True
            self._mode_widget.configure(state="disabled")
            self._model_input.configure(state="disabled")
        # 선택 변경은 다음 사용자가 시작한 로컬 AI 연습부터 반영한다.
        if isinstance(self._runner.generator, LocalOllamaGenerator):
            try:
                self._runner.generator.set_content(CONTENTS[self._content.get()])
                self._runner.generator.set_persona(self._current_persona())
            except (ValueError, KeyError) as exc:
                messagebox.showwarning("캐릭터 설정", str(exc), parent=self)
                return
        self._stop_requested.clear()
        self._busy = True
        for item in (self._run, self._add, self._reset):
            item.configure(state="disabled")
        self._stop.configure(state="normal")
        self._status.set("채팅 처리 중 · 의도적인 답변 지연은 없어.")
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self) -> None:
        try:
            while not self._stop_requested.is_set():
                answer = self._runner.process_next(lambda item: self._events.put(("answer", item)))
                if answer is None:
                    break
        except Exception as exc:
            self._events.put(("error", str(exc)))
        else:
            self._events.put(("stopped" if self._stop_requested.is_set() else "done", None))

    def _request_stop(self) -> None:
        self._stop_requested.set()
        self._status.set("현재 처리 중인 답변 후 멈춰. 대기 중인 채팅은 보존해.")

    def _reset_chat(self) -> None:
        if self._busy:
            return
        if self._runner.pending and not messagebox.askyesno(
            "새 연습", "답변하지 않은 채팅이 남아 있어. 삭제하고 새로 시작할까?", parent=self
        ):
            return
        self._runner = ChatRehearsal()
        self._configured = False
        self._mode_widget.configure(state="readonly")
        self._model_input.configure(state="normal")
        self._out.configure(state="normal")
        self._out.delete("1.0", "end")
        self._out.configure(state="disabled")
        self._count()

    def _poll(self) -> None:
        if self._closing:
            return
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        try:
            while True:
                kind, value = self._events.get_nowait()
                if kind == "answer":
                    self._write(f"{value.original.sender}: {value.original.text}\nAI: {value.reply}\n")
                    self._last_reply = value.reply
                    self._update_voice_buttons()
                    self._count()
                    if (self._auto_read.get() and self._voice.get() == "Windows 무료 음성"
                            and self._selected_voice() is not None):
                        self._speech_pending.append(value.reply)
                        self._play_queued_answer()
                elif kind in ("voices", "voice_error"):
                    self._voice_lookup_done(kind, value)
                elif kind in ("speech_done", "speech_stopped", "speech_error"):
                    self._speech_busy = False
                    self._speech_stop.configure(state="disabled")
                    self._voice_lookup.configure(state="normal")
                    self._update_voice_buttons()
                    self._speech_status.set(
                        "음성 재생 완료." if kind == "speech_done" else
                        "음성 재생 중지." if kind == "speech_stopped" else
                        "음성 오류: " + str(value)
                    )
                    # 자동 발화도 텍스트 답변을 받은 순서대로 재생한다.
                    if self._auto_read.get():
                        self._play_queued_answer()
                else:
                    self._busy = False
                    for item in (self._run, self._add, self._reset):
                        item.configure(state="normal")
                    self._stop.configure(state="disabled")
                    self._count()
                    # A reply can be delivered even when its optional SQLite
                    # history write fails. Never silently imply it was saved.
                    memory_notice = (
                        f" · 대화 기억 저장 실패 {len(self._runner.memory_errors)}건 (저장 상태 확인 필요)"
                        if self._runner.memory_errors else ""
                    )
                    if kind == "error":
                        self._status.set("오류: " + str(value) + " · 실패한 메시지부터 재시도 가능" + memory_notice)
                    elif kind == "stopped":
                        self._status.set("중지했어. 대기열은 유지했어." + memory_notice)
                    else:
                        self._status.set("연습 완료. 실제 방송으로 전송한 내용은 없어." + memory_notice)
        except queue.Empty:
            pass
        self._poll_after_id = self.after(120, self._poll)

    def _build_voice(self, tab) -> None:
        ttk.Label(tab, text="내 Windows PC에 설치된 무료 한국어 음성 사용", font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(3, 10))
        ttk.Label(tab, text="Windows 시스템 음성이 없으면 재생할 수 없어. 자동으로 설치하거나 내려받지 않아.", wraplength=690).pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=5)
        ttk.Label(row, text="설치된 한국어 음성").pack(side="left")
        self._voice_list = ttk.Combobox(row, textvariable=self._voice_name, values=[], state="readonly", width=41)
        self._voice_list.pack(side="left", fill="x", expand=True, padx=8)
        self._voice_list.bind("<<ComboboxSelected>>", self._on_installed_voice_selected)
        self._voice_lookup = ttk.Button(row, text="음성 목록 확인", command=self._find_voices)
        self._voice_lookup.pack(side="left")
        prefs = ttk.Frame(tab)
        prefs.pack(fill="x", pady=(5, 4))
        ttk.Label(prefs, text="재생 속도 (-4~4)").pack(side="left")
        tk.Spinbox(prefs, from_=-4, to=4, increment=1, width=5,
                   textvariable=self._voice_rate).pack(side="left", padx=(6, 16))
        ttk.Label(prefs, text="음량 (0~100)").pack(side="left")
        tk.Spinbox(prefs, from_=0, to=100, increment=5, width=5,
                   textvariable=self._voice_volume).pack(side="left", padx=6)
        ttk.Label(tab, text="목소리 이름·속도·음량을 저장하려면 '방송 설정'의 PC 저장 버튼을 누르세요.",
                  wraplength=680).pack(anchor="w", pady=(3, 5))
        ttk.Label(tab, text="내 목소리·동의받은 녹음·라이선스 음성은 확보 방식만 기록하며, 복제·학습을 시작하지 않습니다.",
                  wraplength=680).pack(anchor="w", pady=(0, 6))
        ttk.Label(tab, text="미리 듣기 문장 (600글자 이내)").pack(anchor="w", pady=(14, 4))
        ttk.Entry(tab, textvariable=self._speech_text).pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(tab, text="새 AI 답변 자동 읽기 (기본 꺼짐 · 사용자가 직접 켜기)",
                        variable=self._auto_read, command=self._auto_voice_changed).pack(anchor="w", pady=5)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=8)
        self._speech_play = ttk.Button(actions, text="문장 미리 듣기", command=self._preview_text)
        self._speech_play.pack(side="left")
        self._speech_read_reply = ttk.Button(actions, text="마지막 AI 답변 듣기", command=self._read_reply)
        self._speech_read_reply.pack(side="left", padx=(7, 0))
        self._speech_stop = ttk.Button(actions, text="소리 중지", command=self._stop_speech)
        self._speech_stop.pack(side="left", padx=(7, 0))
        self._speech_stop.configure(state="disabled")
        ttk.Label(tab, textvariable=self._speech_status, wraplength=670).pack(anchor="w", pady=11)
        ttk.Label(tab, text="PC의 스피커로만 재생돼. OBS 방송이나 외부 송출과는 연결되지 않아.", wraplength=680).pack(anchor="w")
        ttk.Label(tab, text="음성 재생 중에는 2D 아바타 샘플의 입이 움직여 (정확한 립싱크 아님).", wraplength=680).pack(anchor="w", pady=(8,0))
        self._update_voice_buttons()

    def _on_installed_voice_selected(self, _event=None) -> None:
        chosen = self._selected_voice()
        if chosen is not None:
            self._voice_preferred_name = chosen.name
            self._voice.set("Windows 무료 음성")
            self._speech_status.set("Windows 음성을 선택했어. 저장 버튼을 누르면 다음 실행에도 사용돼.")
        self._update_voice_buttons()

    def _selected_voice(self) -> KoreanVoice | None:
        return self._voices.get(self._voice_name.get())

    def _update_voice_buttons(self) -> None:
        if not hasattr(self, "_speech_play"):
            return
        ready = (self._voice.get() == "Windows 무료 음성"
                 and self._selected_voice() is not None and not self._speech_busy)
        self._speech_play.configure(state="normal" if ready else "disabled")
        self._speech_read_reply.configure(state="normal" if ready and self._last_reply else "disabled")

    def _find_voices(self) -> None:
        if self._speech_busy:
            return
        self._speech_busy = True
        self._voice_lookup.configure(state="disabled")
        self._update_voice_buttons()
        self._speech_status.set("Windows PC의 한국어 음성을 조회하고 있어…")
        threading.Thread(target=self._voice_lookup_worker, daemon=True).start()

    def _voice_lookup_worker(self) -> None:
        try:
            voices = self._speaker.installed_voices()
        except Exception as exc:
            self._events.put(("voice_error", str(exc)))
        else:
            self._events.put(("voices", voices))

    def _voice_lookup_done(self, kind: str, value: object) -> None:
        self._speech_busy = False
        self._voice_lookup.configure(state="normal")
        if kind == "voice_error":
            self._voices.clear()
            self._voice_list.configure(values=[])
            self._voice_name.set("")
            self._speech_status.set("음성 목록 오류: " + str(value))
        else:
            self._voices = {f"{v.name} ({v.culture})": v for v in value}
            labels = list(self._voices)
            self._voice_list.configure(values=labels)
            chosen = preferred_installed_voice(self._voice_preferred_name, value)
            preferred_missing = bool(self._voice_preferred_name) and chosen is None
            if chosen is not None:
                self._voice_name.set(f"{chosen.name} ({chosen.culture})")
            elif not self._voice_preferred_name and labels:
                # 최초 조회 시 목록의 첫 번째 음성을 시험용으로 표시하지만 저장은 명시적 클릭에서만.
                self._voice_name.set(labels[0])
            else:
                self._voice_name.set("")
            self._speech_status.set(
                "저장된 한국어 목소리가 이 PC에 없어. 임의로 다른 목소리로 바꾸지 않아."
                if preferred_missing else
                f"설치된 한국어 음성 {len(labels)}개 확인. 재생은 버튼을 눌러야 해."
                if labels else "설치된 한국어 음성이 없어. 임의로 설치하지 않아."
            )
        self._update_voice_buttons()

    def _auto_voice_changed(self) -> None:
        if not self._auto_read.get():
            # 다시 듣기는 현재 재생만 유지하고, 앞으로 대기 중인 자동 발화는 취소.
            self._speech_pending.clear()
            return
        if self._voice.get() != "Windows 무료 음성":
            self._auto_read.set(False)
            self._speech_pending.clear()
            self._speech_status.set("자동 읽기는 Windows 무료 음성을 선택했을 때만 사용해. 복제 음성은 미구현이야.")
            return
        self._play_queued_answer()

    def _play_queued_answer(self) -> None:
        if (self._speech_busy or not self._auto_read.get()
                or self._voice.get() != "Windows 무료 음성"
                or self._selected_voice() is None):
            return
        if self._speech_pending:
            self._start_speech(self._speech_pending.popleft())

    def _preview_text(self) -> None:
        self._start_speech(self._speech_text.get())

    def _read_reply(self) -> None:
        if self._last_reply:
            self._start_speech(self._last_reply)

    def _start_speech(self, text: str) -> None:
        if self._speech_busy:
            return
        if self._voice.get() != "Windows 무료 음성":
            self._speech_status.set("Windows 무료 음성을 선택한 경우에만 수동 미리듣기가 가능합니다.")
            return
        if self._selected_voice() is None:
            self._speech_status.set("한국어 음성을 먼저 선택해 줘.")
            return
        try:
            chunks = speech_chunks(text)
            profile = validate_voice_profile({
                "installed_voice_name": self._selected_voice().name,
                "rate": int(self._voice_rate.get()),
                "volume": int(self._voice_volume.get()),
            })
        except ValueError as exc:
            self._speech_status.set("읽기 실패: " + str(exc))
            return
        self._speech_busy = True
        self._speech_cancel.clear()
        self._voice_lookup.configure(state="disabled")
        self._speech_stop.configure(state="normal")
        self._update_voice_buttons()
        self._speech_status.set("PC에서 음성 재생 중… 외부 송출 없음")
        chosen = self._selected_voice()
        threading.Thread(target=self._speech_worker, args=(chunks, chosen, profile), daemon=True).start()

    def _speech_worker(self, chunks: list[str], voice: KoreanVoice,
                       profile: dict[str, object] | None = None) -> None:
        interrupted = False
        try:
            for part in chunks:
                if self._speech_cancel.is_set():
                    interrupted = True
                    break
                # 기본값은 기존 모의 음성 테스트와 동일한 호출 규약을 유지한다.
                if profile is None or (profile["rate"] == 0 and profile["volume"] == 85):
                    finished = self._speaker.speak(part, voice)
                else:
                    finished = self._speaker.speak(
                        part, voice, rate=profile["rate"], volume=profile["volume"]
                    )
                if not finished:
                    interrupted = True
                    break
        except Exception as exc:
            self._events.put(("speech_stopped" if self._speech_cancel.is_set() else "speech_error", str(exc)))
        else:
            self._events.put(("speech_stopped" if self._speech_cancel.is_set() or interrupted else "speech_done", None))

    def _stop_speech(self) -> None:
        if self._speech_busy:
            self._speech_pending.clear()
            self._auto_read.set(False)
            self._speech_cancel.set()
            self._speaker.stop()
            self._speech_status.set("현재 음성을 중지하는 중이야.")

    def _build_avatar(self, tab) -> None:
        """Scrollable avatar controls: reachable at 1024x768 Windows resolution."""
        outer = ttk.Frame(tab)
        outer.pack(fill="both", expand=True)
        avatar_viewport = tk.Canvas(outer, highlightthickness=0, borderwidth=0)
        avatar_scrollbar = ttk.Scrollbar(
            outer, orient="vertical", command=avatar_viewport.yview
        )
        avatar_viewport.configure(yscrollcommand=avatar_scrollbar.set)
        avatar_scrollbar.pack(side="right", fill="y")
        avatar_viewport.pack(side="left", fill="both", expand=True)
        body = ttk.Frame(avatar_viewport, padding=(8, 2, 8, 8))
        body_window = avatar_viewport.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _e: avatar_viewport.configure(
            scrollregion=avatar_viewport.bbox("all")))
        avatar_viewport.bind("<Configure>", lambda e: avatar_viewport.itemconfigure(
            body_window, width=e.width))

        ttk.Label(body, text="아바타 형태: 미정 / 2D / 3D (VRM) — 방송 설정에서 자유 선택").pack(anchor="w", pady=(4, 5))
        self._avatar_tab_info = tk.StringVar(value=avatar_choice(AVATARS[self._avatar.get()]).description)
        ttk.Label(body, textvariable=self._avatar_tab_info, wraplength=690).pack(anchor="w", pady=(0, 8))
        self._canvas = tk.Canvas(body, width=370, height=350, bg="#17223c", highlightthickness=0)
        self._canvas.pack(pady=4)
        ttk.Checkbutton(body, text="입 움직임 데모", variable=self._avatar_demo).pack(pady=5)
        group = ttk.LabelFrame(body, text="별도 아바타 창 (PC에서만 실행)", padding=8)
        group.pack(fill="x", pady=(8, 4))
        self._avatar_open_button = ttk.Button(group, text="2D 샘플 별도 창 열기", command=self._open_avatar_capture)
        self._avatar_open_button.pack(side="left")
        self._avatar_changed()
        ttk.Label(group, textvariable=self._avatar_capture_status).pack(side="left", padx=(10, 0))
        ttk.Label(
            body,
            text="OBS가 PC에 있다면 사용자가 OBS 창 캡처로 이 별도 창을 수동 선택할 수 있어.\n"
                 "창만 열며 OBS 설치·실행·방송 송출은 하지 않아.",
            justify="left", wraplength=700,
        ).pack(anchor="w", pady=(7, 0))

        def scroll_avatar(event):
            # Scroll only this tab when the cursor is inside its viewport.
            px, py = self.winfo_pointerxy()
            target = self.winfo_containing(px, py)
            while target is not None:
                if target is avatar_viewport:
                    if event.delta:
                        avatar_viewport.yview_scroll(
                            (1 if event.delta < 0 else -1) * max(1, abs(event.delta) // 120),
                            "units",
                        )
                    return "break"
                target = target.master
            return None

        def bind_scroll_tree(widget):
            widget.bind("<MouseWheel>", scroll_avatar, add="+")
            for child in widget.winfo_children():
                bind_scroll_tree(child)

        bind_scroll_tree(avatar_viewport)
        self._avatar_viewport = avatar_viewport

    def _open_avatar_capture(self) -> None:
        """오직 사용자 클릭으로 2D 샘플 창 생성. 3D 선택 때는 실행 차단."""
        if not avatar_choice(AVATARS.get(self._avatar.get())).can_open_sample_window:
            self._avatar_capture_status.set("3D 선택: 2D 샘플 창 열기 불가")
            return
        if self._avatar_capture_window is not None:
            if self._avatar_capture_window.winfo_exists():
                self._avatar_capture_window.lift()
                return
            self._avatar_capture_window = None
            self._avatar_capture_canvas = None
        win = tk.Toplevel(self)
        win.title("AISTING 아바타 · 로컬 창 캡처용")
        win.geometry("400x495")
        win.minsize(385, 450)
        win.configure(bg="#17223c")
        win.protocol("WM_DELETE_WINDOW", self._close_avatar_capture)
        self._avatar_capture_window = win
        self._avatar_capture_canvas = tk.Canvas(
            win, width=370, height=350,
            bg=BACKGROUND_COLORS[self._avatar_capture_background.get()],
            highlightthickness=0,
        )
        self._avatar_capture_canvas.pack(fill="both", expand=True, padx=8, pady=8)
        options = ttk.Frame(win, padding=8)
        options.pack(fill="x")
        ttk.Label(options, text="배경 색상").pack(side="left")
        ttk.Combobox(
            options, state="readonly", textvariable=self._avatar_capture_background,
            values=tuple(BACKGROUND_COLORS), width=16,
        ).pack(side="left", padx=(8, 4))
        ttk.Label(win, text="OBS에서 별도로 창 캡처를 추가해야 해. 방송은 시작하지 않아.",
                  wraplength=375).pack(pady=(0, 8))
        self._avatar_capture_status.set("별도 창: 열림")
        self._draw_avatar_canvases()

    def _close_avatar_capture(self) -> None:
        """별도 아바타 창만 닫아도 본 프로그램과 채팅/음성은 유지."""
        child = self._avatar_capture_window
        self._avatar_capture_window = None
        self._avatar_capture_canvas = None
        if child is not None:
            try:
                if child.winfo_exists():
                    child.destroy()
            except tk.TclError:
                pass
        self._avatar_capture_status.set("별도 창: 닫힘")

    def _draw_avatar_canvases(self) -> None:
        try:
            name = self._current_persona()["name"]
        except ValueError:
            name = DEFAULTS["persona"]["name"]
        talking = bool(self._avatar_demo.get() or self._speaker.speaking)
        # 3D 선택 시 가짜 3D 대신 명시적으로 미구현을 표시한다.
        choice = avatar_choice(AVATARS.get(self._avatar.get()))
        if choice.sample_2d_visible:
            draw_avatar(self._canvas, AvatarFrame(
                name, talking, self._avatar_frame,
                expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()],
            ))
        else:
            draw_unavailable_3d(self._canvas)
        canvas = self._avatar_capture_canvas
        if canvas is not None:
            if canvas.winfo_exists():
                draw_avatar(canvas, AvatarFrame(
                    name, talking, self._avatar_frame,
                    background=self._avatar_capture_background.get(),
                    expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()],
                ))
            else:
                self._avatar_capture_canvas = None
                self._avatar_capture_window = None
                self._avatar_capture_status.set("별도 창: 닫힘")

    def _avatar_tick(self) -> None:
        if self._closing:
            return
        if self._avatar_after_id is not None:
            try:
                self.after_cancel(self._avatar_after_id)
            except tk.TclError:
                pass
            self._avatar_after_id = None
        if not self.winfo_exists():
            return
        self._draw_avatar_canvases()
        self._avatar_frame += 1
        self._avatar_after_id = self.after(120, self._avatar_tick)

    def _build_local_operation(self, tab) -> None:
        """내 PC 운용 원칙/저장 경로를 표시한다. 열기만 해서는 점검도 하지 않는다."""
        ttk.Label(tab, text="9단계 · PC 로컬 운영 방식", font=("Malgun Gothic", 13, "bold")).pack(
            anchor="w", pady=(3, 8)
        )
        ttk.Label(
            tab,
            text="GitHub와 무관한 PC 로컬 프로그램입니다. 현재는 자동 방송이 아닌 개발본이며 "
                 "실제 방송 플랫폼 통신은 아직 구현되지 않았습니다.",
            wraplength=710,
        ).pack(anchor="w", pady=(0, 10))
        self._local_plan = local_operation_plan(self.settings)
        summary = tk.Text(tab, height=13, wrap="word", state="normal", font=("Malgun Gothic", 10))
        summary.pack(fill="both", expand=True)
        summary.insert("1.0", self._local_plan.describe())
        summary.configure(state="disabled")
        ttk.Label(
            tab, text="자가 점검 버튼을 누른 경우에만 로컬 전용 임시 파일을 생성·읽기·삭제합니다. "
                      "PC 사양 조회, AI 모델 설치, 인터넷 연결은 하지 않습니다.",
            wraplength=710,
        ).pack(anchor="w", pady=(10, 6))
        ttk.Button(tab, text="PC 저장 폴더 점검 (수동)", command=self._check_pc_storage).pack(
            anchor="w", pady=(0, 5))
        self._local_check_status = tk.StringVar(value="검사 전 · 자동 저장 공간 검사는 실행되지 않았습니다.")
        ttk.Label(tab, textvariable=self._local_check_status, wraplength=700).pack(anchor="w")

    def _check_pc_storage(self) -> None:
        """사용자가 클릭한 때에만 사용자 데이터 폴더를 안전하게 점검한다."""
        report = check_local_storage(self._local_plan.settings_path.parent)
        self._local_check_status.set(report.message)

    def _build_os_review(self, tab) -> None:
        """11단계 준비: OS 정보를 사용자가 직접 입력. 장치/시스템 자동 조회 없음."""
        ttk.Label(tab, text="11단계 · PC 운영체제 확인 준비", font=("Malgun Gothic", 13, "bold")).pack(
            anchor="w", pady=(2, 8))
        ttk.Label(
            tab, text="아직 사용자의 PC를 검사하지 않았습니다. 이 화면은 운영자가 직접 아는 정보를 "
                      "선택해 호환성 검토 사항을 확인하는 도구입니다. 시스템 조회·설치·외부 전송 없음.",
            wraplength=710,
        ).pack(anchor="w", pady=(0, 12))
        self._os_choice = tk.StringVar(value=next(iter(OS_LABELS)))
        self._os_arch = tk.StringVar(value=next(iter(ARCH_LABELS)))
        section = self._section(tab, "내 PC 정보 (자동 인식이 아닌 직접 입력)")
        ttk.Label(section, text="Windows 버전").pack(anchor="w")
        ttk.Combobox(section, textvariable=self._os_choice, values=list(OS_LABELS),
                     state="readonly", width=42).pack(anchor="w", pady=(4, 12))
        ttk.Label(section, text="시스템 종류").pack(anchor="w")
        ttk.Combobox(section, textvariable=self._os_arch, values=list(ARCH_LABELS),
                     state="readonly", width=42).pack(anchor="w", pady=(4, 8))
        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="선택 내용만 평가 (PC 조회 없음)",
                   command=self._assess_os_choice).pack(side="left")
        ttk.Button(buttons, text="입력 내용 PC에 기록 (확인 필요)",
                   command=self._save_os_choice).pack(side="left", padx=(6, 0))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 10))
        ttk.Button(row, text="지난 입력 불러오기", command=self._load_os_choice).pack(side="left")
        ttk.Button(row, text="입력 기록 삭제 (확인 필요)",
                   command=self._delete_os_choice).pack(side="left", padx=(6, 0))
        self._os_status = tk.StringVar(value="미검사 · PC 자동 조회 없음 · 11단계 실기기 검증 대기")
        ttk.Label(tab, textvariable=self._os_status, wraplength=710, justify="left").pack(anchor="w")
        ttk.Label(tab, text="선택값 기록은 실제 PC 확인·Windows EXE 작동 검증의 증거가 아닙니다. "
                            "이 기능 때문에 공식 10단계 승인이나 11단계를 완료 처리하지 않습니다.",
                  wraplength=700).pack(anchor="w", pady=(12, 0))

    def _manual_os_choice(self) -> ManualOsChoice:
        try:
            return ManualOsChoice(OS_LABELS[self._os_choice.get()], ARCH_LABELS[self._os_arch.get()])
        except KeyError as exc:
            raise ValueError("OS와 시스템 종류를 목록에서 직접 선택해 주세요.") from exc

    def _assess_os_choice(self) -> None:
        try:
            result = assess_manual_os(self._manual_os_choice())
        except (ValueError, TypeError) as exc:
            self._os_status.set("입력 오류: " + str(exc))
            return
        self._os_status.set(result.description + "\n11단계 실기기 검증: 미완료")

    def _save_os_choice(self) -> None:
        try:
            choice = self._manual_os_choice()
            # 실제 자동 인식이 아님을 확인하고 나서만 기록.
            if not messagebox.askyesno(
                "PC 운영체제 입력 기록",
                "이 값은 자동 PC 검사가 아닌 직접 입력한 참고 정보입니다.\n"
                "다른 시스템을 검사하거나 설치하지 않습니다. PC에 이 입력만 저장할까요?",
                parent=self,
            ):
                return
            save_os_note(choice, os_note_path(), operator_confirmed=True)
        except (ValueError, PermissionError, TypeError, OSError) as exc:
            messagebox.showwarning("입력 저장 실패", str(exc), parent=self)
            return
        self._os_status.set("사용자 입력 내용만 PC에 저장했습니다. 실제 운영체제 및 EXE 실행 검증은 미완료입니다.")

    def _load_os_choice(self) -> None:
        try:
            choice = load_os_note(os_note_path())
        except (ValueError, OSError, UnicodeError, TypeError) as exc:
            self._os_status.set("이전 입력 기록을 읽지 못했습니다: " + str(exc))
            return
        if choice is None:
            self._os_status.set("이전에 직접 저장한 운영체제 입력 기록이 없습니다.")
            return
        self._os_choice.set(_label_for(OS_LABELS, choice.os_code))
        self._os_arch.set(_label_for(ARCH_LABELS, choice.architecture))
        self._assess_os_choice()
        self._os_status.set("지난 사용자 입력을 불러왔습니다 (PC를 재검사한 것이 아닙니다).\n" + self._os_status.get())

    def _delete_os_choice(self) -> None:
        if not messagebox.askyesno(
            "운영체제 입력 기록 삭제",
            "사용자가 입력한 OS 참고 기록 하나만 삭제할까요? 방송 설정과 대화 기억은 유지합니다.",
            parent=self,
        ):
            return
        try:
            delete_os_note(os_note_path(), operator_confirmed=True)
        except (PermissionError, OSError) as exc:
            self._os_status.set("기록 삭제 실패: " + str(exc))
            return
        self._os_status.set("운영체제 사용자 입력 기록을 삭제했습니다. 다른 설정과 기억은 유지했습니다.")

    def _build_hardware_review(self, tab) -> None:
        """12단계 준비: 사용자가 입력한 CPU/RAM/GPU 참고 정보만 취급."""
        ttk.Label(tab, text="12단계 · PC CPU·RAM·GPU 확인 준비",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(2, 8))
        ttk.Label(
            tab, text="자동 PC 사양 조회는 하지 않습니다. 운영자가 아는 값만 직접 입력하고 "
                      "언제든 수정할 수 있습니다. 이 기록은 실행/성능 검증이 아닙니다.",
            wraplength=710,
        ).pack(anchor="w", pady=(0, 8))
        self._hardware_fields = {}
        descriptions = (
            ("cpu_name", "CPU 모델명", "예: 본인이 확인한 CPU 이름"),
            ("cpu_cores", "CPU 코어 수", "모르면 빈칸"),
            ("ram_gb", "RAM 용량 (GB)", "모르면 빈칸"),
            ("gpu_name", "GPU 모델명", "없거나 모르면 빈칸"),
            ("gpu_vram_gb", "GPU VRAM (GB)", "모르면 빈칸"),
        )
        entry_box = self._section(tab, "사용자가 직접 입력 (PC 자동 검색 없음)")
        for key, title, placeholder in descriptions:
            line = ttk.Frame(entry_box)
            line.pack(fill="x", pady=4)
            ttk.Label(line, text=title, width=17).pack(side="left")
            entry = ttk.Entry(line, width=35)
            entry.pack(side="left", padx=(6, 9), fill="x", expand=True)
            ttk.Label(line, text=placeholder).pack(side="left")
            self._hardware_fields[key] = entry
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(4, 8))
        ttk.Button(row, text="입력값 검토 (장치 조회 없음)", command=self._assess_hardware_choice).pack(side="left")
        ttk.Button(row, text="사용자 입력만 PC에 저장", command=self._save_hardware_choice).pack(side="left", padx=(6, 0))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Button(row, text="지난 입력 불러오기", command=self._load_hardware_choice).pack(side="left")
        ttk.Button(row, text="사양 참고 기록 삭제", command=self._delete_hardware_choice).pack(side="left", padx=(6, 0))
        self._hardware_status = tk.StringVar(
            value="입력 전 · 사용자의 실제 CPU·RAM·GPU를 확인하지 않았습니다. 공식 단계는 그대로 유지됩니다."
        )
        ttk.Label(tab, textvariable=self._hardware_status, wraplength=700, justify="left").pack(
            anchor="w", pady=(3, 0))

    def _manual_hardware_choice(self) -> ManualHardwareChoice:
        def optional_int(field: str) -> int | None:
            raw = self._hardware_fields[field].get().strip()
            if not raw:
                return None
            if not raw.isascii() or not raw.isdecimal():
                raise ValueError("CPU 코어·RAM·VRAM은 숫자만 입력해 주세요 (모르면 빈칸).")
            return int(raw)
        return ManualHardwareChoice(
            cpu_name=self._hardware_fields["cpu_name"].get().strip(),
            cpu_cores=optional_int("cpu_cores"),
            ram_gb=optional_int("ram_gb"),
            gpu_name=self._hardware_fields["gpu_name"].get().strip(),
            gpu_vram_gb=optional_int("gpu_vram_gb"),
        )

    def _assess_hardware_choice(self) -> None:
        try:
            report = review_manual_hardware(self._manual_hardware_choice())
            self._hardware_status.set(report.summary)
        except (ValueError, TypeError) as exc:
            self._hardware_status.set("입력 오류: " + str(exc))

    def _save_hardware_choice(self) -> None:
        try:
            value = self._manual_hardware_choice()
            if not messagebox.askyesno(
                "PC 사양 참고 기록 저장",
                "이 정보는 자동 PC 조회 결과가 아닌 직접 입력값입니다. "
                "설치나 성능 테스트 없이 이 내용만 PC에 저장할까요?", parent=self,
            ):
                return
            save_hardware_note(value, hardware_note_path(), operator_confirmed=True)
        except (ValueError, TypeError, OSError, PermissionError) as exc:
            messagebox.showwarning("참고 기록 저장 실패", str(exc), parent=self)
            return
        self._hardware_status.set("입력한 PC 사양 참고 정보만 저장했습니다. PC 실측·성능 검증은 미완료입니다.")

    def _load_hardware_choice(self) -> None:
        try:
            choice = load_hardware_note(hardware_note_path())
        except (ValueError, TypeError, OSError, UnicodeError) as exc:
            self._hardware_status.set("입력 기록 불러오기 실패: " + str(exc))
            return
        if choice is None:
            self._hardware_status.set("저장된 직접 입력 하드웨어 정보가 없습니다.")
            return
        values = {
            "cpu_name": choice.cpu_name,
            "cpu_cores": "" if choice.cpu_cores is None else str(choice.cpu_cores),
            "ram_gb": "" if choice.ram_gb is None else str(choice.ram_gb),
            "gpu_name": choice.gpu_name,
            "gpu_vram_gb": "" if choice.gpu_vram_gb is None else str(choice.gpu_vram_gb),
        }
        for key, value in values.items():
            entry = self._hardware_fields[key]
            entry.delete(0, "end")
            entry.insert(0, value)
        self._assess_hardware_choice()
        self._hardware_status.set("사용자 입력 기록 복원 (PC를 조회한 것이 아님).\n" + self._hardware_status.get())

    def _delete_hardware_choice(self) -> None:
        if not messagebox.askyesno("PC 사양 기록 삭제",
                                   "CPU·RAM·GPU 입력 참고 기록만 삭제할까요? 방송 설정과 기억은 유지합니다.",
                                   parent=self):
            return
        try:
            delete_hardware_note(hardware_note_path(), operator_confirmed=True)
        except (OSError, PermissionError) as exc:
            self._hardware_status.set("기록 삭제 실패: " + str(exc))
            return
        self._hardware_status.set("하드웨어 입력 참고 기록을 삭제했습니다. 다른 정보는 변경하지 않았습니다.")

    def _build_scope_review(self, tab) -> None:
        """13단계: 현재 OS/사양 탭의 사용자 입력값만 참조, 저장된 기록 자동 열람 없음."""
        ttk.Label(tab, text="13단계 · PC 기준 개발 범위 검토",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(2, 8))
        ttk.Label(
            tab,
            text="OS 확인 준비 및 PC 사양 입력 탭에 직접 입력한 값만 사용합니다. "
                 "이 탭을 열거나 검토 버튼을 눌러도 PC 사양 검색, 파일 읽기/저장, "
                 "외부 접속, 설치, 실제 실행 검사는 하지 않습니다.",
            wraplength=710,
        ).pack(anchor="w", pady=(0, 10))
        ttk.Button(tab, text="현재 직접 입력값으로 범위표 만들기 (실행 검사 없음)",
                   command=self._review_scope).pack(anchor="w", pady=(0, 8))
        self._scope_status = tk.StringVar(value="아직 검토하지 않았습니다. 실제 PC 호환성은 미검증입니다.")
        ttk.Label(tab, textvariable=self._scope_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._scope_view = tk.Text(tab, wrap="word", height=18, font=("Malgun Gothic", 10))
        self._scope_view.pack(fill="both", expand=True)
        self._scope_view.insert("1.0", "운영자가 OS/사양을 직접 입력한 뒤 위 버튼을 누르면 참고 범위표를 표시합니다.")
        self._scope_view.configure(state="disabled")

    def _review_scope(self) -> None:
        """메모리에 있는 입력값으로만 분석. 디스크·장치·네트워크를 건드리지 않는다."""
        try:
            scope = review_development_scope(self._manual_os_choice(), self._manual_hardware_choice())
            result = scope.describe()
            status = "참고 범위표 생성 · Windows 실행/AI 성능/실제 방송 가능 여부는 미검증입니다."
        except (ValueError, TypeError) as exc:
            result = "입력 오류: " + str(exc) + "\nOS/PC 사양 탭의 입력값을 수정해 주세요."
            status = "범위 검토 실패 · 이전 결과는 표시하지 않습니다."
        self._scope_view.configure(state="normal")
        self._scope_view.delete("1.0", "end")
        self._scope_view.insert("1.0", result)
        self._scope_view.configure(state="disabled")
        self._scope_status.set(status)

    def _build_software_cost_guide(self, tab) -> None:
        """14단계: 프로그램/비용 후보를 한 화면에 일괄 표시. PC/가격 자동 조회 없음."""
        ttk.Label(tab, text="14단계 · 프로그램·비용 사전 안내",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(2, 8))
        ttk.Label(
            tab,
            text="현재 필요한 도구와 향후 방송·아바타·음성 후보를 모두 보여줍니다. "
                 "가격/설치 여부는 조회하지 않으며 설치·결제·15단계 승인도 실행하지 않습니다.",
            wraplength=710, justify="left",
        ).pack(anchor="w", pady=(0, 8))
        self._cost_guide = build_software_cost_guide()
        self._cost_status = tk.StringVar(
            value="일괄 안내 표시 중 · 실제 설치 현황/현재 가격 미확인 · 구매/설치/승인 없음"
        )
        ttk.Label(tab, textvariable=self._cost_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        holder = ttk.Frame(tab)
        holder.pack(fill="both", expand=True)
        self._cost_view = tk.Text(holder, wrap="word", height=20, font=("Malgun Gothic", 10))
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=self._cost_view.yview)
        self._cost_view.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._cost_view.pack(side="left", fill="both", expand=True)
        self._cost_view.insert("1.0", self._cost_guide.describe())
        self._cost_view.configure(state="disabled")

    def _build_workspace_setup(self, tab) -> None:
        """16단계: 사용자 직접 경로 선택/미리보기/확인 후 폴더 구성."""
        ttk.Label(tab, text="16단계 · 개발용 폴더와 작업 공간 구성",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 9))
        ttk.Label(tab, text="상위 폴더를 직접 지정하세요. 화면을 열어도 폴더 생성·PC 조회는 하지 않습니다.",
                  wraplength=690).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 9))
        self._workspace_parent = tk.StringVar(value="")
        ttk.Entry(row, textvariable=self._workspace_parent, width=65).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="폴더 선택", command=self._choose_workspace_parent).pack(side="left", padx=(7, 0))
        actions = ttk.Frame(tab)
        actions.pack(anchor="w", pady=(0, 8))
        ttk.Button(actions, text="작업 공간 계획 미리보기", command=self._preview_workspace).pack(side="left")
        ttk.Button(actions, text="작업 공간 생성 (수동)", command=self._create_workspace).pack(side="left", padx=(9, 0))
        self._workspace_status = tk.StringVar(value="미선택 · 생성/설치/백업 실행 없음")
        ttk.Label(tab, textvariable=self._workspace_status, wraplength=700).pack(anchor="w", pady=(0, 8))
        self._workspace_view = tk.Text(tab, height=16, wrap="word", font=("Malgun Gothic", 10))
        self._workspace_view.pack(fill="both", expand=True)
        self._workspace_view.insert("1.0", "상위 폴더를 직접 선택한 뒤 '계획 미리보기'를 누르세요.\n"
                                    "승인 대기 중인 10단계·15단계와 별개로 준비할 수 있습니다.\n"
                                    "프로그램 설치·사용자 데이터 백업·방송 시작은 실행하지 않습니다.")
        self._workspace_view.configure(state="disabled")

    def _choose_workspace_parent(self) -> None:
        chosen = filedialog.askdirectory(parent=self, title="AISTING 작업 공간을 둘 상위 폴더 선택", mustexist=True)
        if chosen:
            self._workspace_parent.set(chosen)
            self._preview_workspace()

    def _set_workspace_report(self, text: str) -> None:
        self._workspace_view.configure(state="normal")
        self._workspace_view.delete("1.0", "end")
        self._workspace_view.insert("1.0", text)
        self._workspace_view.configure(state="disabled")

    def _preview_workspace(self) -> None:
        try:
            plan = workspace_plan(self._workspace_parent.get())
        except ValueError as exc:
            self._workspace_status.set(f"입력 오류: {exc}")
            self._set_workspace_report(str(exc))
            return
        self._set_workspace_report(plan.describe())
        self._workspace_status.set("계획 표시만 완료 · PC 파일 조회/생성 없음")

    def _create_workspace(self) -> None:
        try:
            plan = workspace_plan(self._workspace_parent.get())
        except ValueError as exc:
            self._workspace_status.set(f"입력 오류: {exc}")
            self._set_workspace_report(str(exc))
            return
        if not messagebox.askyesno(
            "개발 작업 공간 생성 확인",
            f"다음 위치에 AISTING 작업 폴더를 만들까요?\n\n{plan.root}\n\n"
            "기존 파일은 삭제·덮어쓰지 않습니다. 프로그램 설치나 백업은 하지 않습니다.",
            parent=self,
        ):
            self._workspace_status.set("사용자가 생성을 취소함 · 변경 없음")
            return
        try:
            root = create_workspace(plan, confirmed=True)
        except (OSError, ValueError, PermissionError) as exc:
            self._workspace_status.set("작업 공간 생성 실패 · 기존 파일 보존")
            self._set_workspace_report(f"작업 공간 생성 실패: {exc}")
            return
        self._set_workspace_report(plan.describe() + f"\n\n생성 확인: {root}\n"
                                   "기존 데이터 이동/복사, 자동 백업, 설치는 수행하지 않았습니다.")
        self._workspace_status.set("작업 공간 폴더 생성 완료 · 16단계 사용자 PC 검증/승인은 별도")

    def _build_runtime_profile(self, tab) -> None:
        """17단계: 명시적 저장·불러오기·적용. 초기화 시 파일 조회 없음."""
        ttk.Label(tab, text="17단계 · 기본 실행 환경 설정 (PC 로컬 · 수동)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 9))
        ttk.Label(tab, text="채팅 연습의 기본 응답 방식을 선택합니다. 앱 시작 시 모델/방송을 자동 실행하지 않습니다. "
                  "저장과 적용은 별도 동작이며 다른 방송 설정은 그대로 유지합니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        line = ttk.Frame(tab)
        line.pack(fill="x", pady=4)
        ttk.Label(line, text="응답 방식", width=13).pack(side="left")
        self._runtime_mode = tk.StringVar(value="모의 답변 (인터넷 불필요)")
        ttk.Combobox(line, textvariable=self._runtime_mode, values=tuple(RUNTIME_MODES),
                     state="readonly", width=31).pack(side="left", padx=(5, 0))
        line = ttk.Frame(tab)
        line.pack(fill="x", pady=4)
        ttk.Label(line, text="로컬 모델 이름", width=13).pack(side="left")
        self._runtime_model = tk.StringVar(value="")
        ttk.Entry(line, textvariable=self._runtime_model, width=35).pack(side="left", padx=(5, 0))
        ttk.Label(line, text="모의 답변일 때는 빈칸", wraplength=220).pack(side="left", padx=(9, 0))
        actions = ttk.Frame(tab)
        actions.pack(anchor="w", pady=(9, 4))
        ttk.Button(actions, text="실행 계획 미리보기", command=self._preview_runtime_profile).pack(side="left")
        ttk.Button(actions, text="선택값 저장 (수동)", command=self._save_runtime_profile).pack(side="left", padx=(7, 0))
        actions2 = ttk.Frame(tab)
        actions2.pack(anchor="w", pady=(0, 8))
        ttk.Button(actions2, text="저장 기록 불러오기", command=self._load_runtime_profile).pack(side="left")
        ttk.Button(actions2, text="채팅 연습에 적용", command=self._apply_runtime_profile).pack(side="left", padx=(7, 0))
        ttk.Button(actions2, text="저장 기록 삭제", command=self._delete_runtime_profile).pack(side="left", padx=(7, 0))
        self._runtime_status = tk.StringVar(value="기본 모의 답변 · 프로필 자동 읽기/저장/적용/연결 없음")
        ttk.Label(tab, textvariable=self._runtime_status, wraplength=700).pack(anchor="w", pady=(2, 8))
        self._runtime_view = tk.Text(tab, height=14, wrap="word", font=("Malgun Gothic", 10))
        self._runtime_view.pack(fill="both", expand=True)
        self._runtime_view.insert("1.0", "사용자가 선택한 응답 방식은 '채팅 연습에 적용'을 누른 뒤 "
                                  "'모두 답변'을 눌러야 실행됩니다.\n"
                                  "프로필을 저장해도 앱 시작 시 자동 적용하지 않습니다.\n"
                                  "10단계·15단계 승인 대기는 유지합니다.")
        self._runtime_view.configure(state="disabled")

    def _runtime_choice(self) -> RuntimeProfile:
        try:
            code = RUNTIME_MODES[self._runtime_mode.get()]
        except KeyError as exc:
            raise ValueError("지원하지 않는 응답 방식을 선택했습니다.") from exc
        return RuntimeProfile(code, self._runtime_model.get().strip())

    def _set_runtime_report(self, value: str) -> None:
        self._runtime_view.configure(state="normal")
        self._runtime_view.delete("1.0", "end")
        self._runtime_view.insert("1.0", value)
        self._runtime_view.configure(state="disabled")

    def _preview_runtime_profile(self) -> None:
        try:
            report = self._runtime_choice().describe()
        except ValueError as exc:
            self._runtime_status.set("입력 오류: " + str(exc))
            return
        self._set_runtime_report(report)
        self._runtime_status.set("계획 표시 완료 · PC 파일 조회/생성/네트워크 없음")

    def _save_runtime_profile(self) -> None:
        try:
            choice = self._runtime_choice()
        except ValueError as exc:
            self._runtime_status.set("입력 오류: " + str(exc))
            return
        if not messagebox.askyesno(
            "기본 실행 환경 저장", "선택한 수동 실행 환경만 별도 PC 파일에 저장할까요?\n"
            "앱 자동 시작·모델 연결·방송·설치는 하지 않습니다.", parent=self,
        ):
            self._runtime_status.set("사용자가 저장 취소 · 변경 없음")
            return
        try:
            save_profile(choice, profile_path(), operator_confirmed=True)
        except (OSError, ValueError, TypeError, PermissionError) as exc:
            self._runtime_status.set("실행 환경 저장 실패: " + str(exc))
            return
        self._runtime_status.set("수동 실행 환경만 저장 완료 · 채팅 연습에는 아직 적용하지 않음")

    def _load_runtime_profile(self) -> None:
        try:
            profile = load_profile(profile_path())
        except (OSError, ValueError, TypeError) as exc:
            self._runtime_status.set("실행 환경 불러오기 실패 · 원본 유지: " + str(exc))
            return
        if profile is None:
            self._runtime_status.set("저장된 실행 환경 기록 없음 · 기존 선택 유지")
            return
        self._runtime_mode.set(next(name for name, code in RUNTIME_MODES.items() if code == profile.mode))
        self._runtime_model.set(profile.model_name)
        self._set_runtime_report(profile.describe())
        self._runtime_status.set("수동 불러오기 완료 · 채팅 연습 적용/AI 연결 없음")

    def _apply_runtime_profile(self) -> None:
        if self._busy or self._configured:
            self._runtime_status.set("이미 시작한 채팅 연습에는 적용할 수 없음 · 연습이 끝난 뒤 '새 연습'을 눌러 주세요")
            return
        try:
            profile = self._runtime_choice()
        except ValueError as exc:
            self._runtime_status.set("입력 오류: " + str(exc))
            return
        label = next(name for name, code in RUNTIME_MODES.items() if code == profile.mode)
        self._selected_mode.set(label)
        self._model_name.set(profile.model_name)
        self._runtime_status.set("채팅 연습 응답 방식만 적용 완료 · '모두 답변'을 누르기 전에는 실행/연결 없음")

    def _delete_runtime_profile(self) -> None:
        if not messagebox.askyesno(
            "실행 환경 기록 삭제", "저장된 수동 실행 환경 기록 하나만 삭제할까요?\n"
            "방송 설정·기존 채팅/SQLite 기억·현재 화면 입력값은 유지합니다.", parent=self,
        ):
            self._runtime_status.set("사용자가 삭제 취소 · 변경 없음")
            return
        try:
            delete_profile(profile_path(), operator_confirmed=True)
        except (OSError, ValueError, PermissionError) as exc:
            self._runtime_status.set("실행 환경 삭제 실패: " + str(exc))
            return
        self._runtime_status.set("저장된 실행 환경 기록만 삭제 완료 · 기존 설정/기억 유지")

    def _build_manual_archive(self, tab) -> None:
        """18단계: 보관은 오직 사용자가 미리보기/파일 선택/확인 시에만 실행."""
        ttk.Label(tab, text="18단계 · 기획안과 설정 파일 보관 (수동)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 9))
        ttk.Label(tab, text="원본 기획안·요구사항·개발 로드맵 사본을 새 로컬 ZIP에 보관합니다. "
                  "개인 방송 설정과 실행 환경 기록은 체크한 경우에만 포함합니다. "
                  "기존 파일을 변경하거나 자동 복구·백업·방송을 시작하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 9))
        self._archive_settings = tk.BooleanVar(value=False)
        self._archive_runtime = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="내 방송 설정(settings.json)도 포함", variable=self._archive_settings).pack(anchor="w")
        ttk.Checkbutton(tab, text="수동 실행 환경 기록도 포함", variable=self._archive_runtime).pack(anchor="w")
        actions = ttk.Frame(tab)
        actions.pack(anchor="w", pady=(12, 7))
        ttk.Button(actions, text="보관 항목 미리보기", command=self._preview_manual_archive).pack(side="left")
        ttk.Button(actions, text="보관 ZIP 만들기 (수동)", command=self._create_manual_archive).pack(side="left", padx=(9, 0))
        self._archive_status = tk.StringVar(value="대기 · 앱 시작 시 설정 파일 조회/보관 없음")
        ttk.Label(tab, textvariable=self._archive_status, wraplength=700).pack(anchor="w", pady=(0, 8))
        self._archive_view = tk.Text(tab, height=15, wrap="word", font=("Malgun Gothic", 10))
        self._archive_view.pack(fill="both", expand=True)
        self._archive_view.insert("1.0", "보관할 설정 파일을 선택하고 '보관 항목 미리보기'를 누르세요.\n"
                                  "미리보기는 PC 파일을 읽거나 쓰지 않습니다.\n"
                                  "사용자가 선택한 위치에만 새 ZIP을 만들며 기존 파일을 덮어쓰지 않습니다.\n"
                                  "10단계 최종 승인과 11~18단계 실제 PC 확인은 별도입니다.")
        self._archive_view.configure(state="disabled")

    def _archive_plan(self):
        return plan_archive(include_settings=self._archive_settings.get(),
                            include_runtime=self._archive_runtime.get())

    def _set_archive_report(self, text: str) -> None:
        self._archive_view.configure(state="normal")
        self._archive_view.delete("1.0", "end")
        self._archive_view.insert("1.0", text)
        self._archive_view.configure(state="disabled")

    def _preview_manual_archive(self) -> None:
        plan = self._archive_plan()
        self._set_archive_report(plan.describe())
        self._archive_status.set("보관 계획만 표시 · 파일 조회/생성/네트워크 없음")

    def _create_manual_archive(self) -> None:
        plan = self._archive_plan()
        filename = filedialog.asksaveasfilename(
            parent=self, title="새 보관 ZIP 저장 위치 선택", defaultextension=".zip",
            filetypes=[("ZIP 파일", "*.zip")], initialfile="AISTING_Manual_Archive.zip",
        )
        if not filename:
            self._archive_status.set("파일 선택 취소 · 변경 없음")
            return
        if not messagebox.askyesno(
            "로컬 사본 보관 확인", "선택한 기획안/설정 파일의 사본을 새 ZIP으로 보관할까요?\n"
            "개인 설정이 포함되면 외부 공유에 주의하세요.\n"
            "기존 ZIP은 덮어쓰지 않으며 복원·방송·설치는 하지 않습니다.", parent=self,
        ):
            self._archive_status.set("사용자가 보관 취소 · 변경 없음")
            return
        try:
            created = create_archive(plan, filename, confirmed=True)
            manifest = verify_archive(created)
        except (OSError, ValueError, TypeError, PermissionError, UnicodeError) as exc:
            self._archive_status.set("보관 실패 · 원본 유지: " + str(exc))
            return
        self._set_archive_report(plan.describe() + "\n\n생성 위치: " + str(created)
                                 + f"\n무결성 검증: {len(manifest['entries'])}개 파일 SHA256 확인")
        self._archive_status.set("수동 ZIP 보관 완료 · 원본/사용자 설정 유지 · 복원/승인 아님")

    def _build_backup_recovery(self, tab, archive_tab) -> None:
        """19단계: 선택한 보관 ZIP만 검사하고 새 폴더에 복구 사본을 만든다."""
        ttk.Label(tab, text="19단계 · 로컬 백업 검증 및 복구 준비",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 9))
        ttk.Label(tab, text="18단계에서 직접 만든 ZIP을 선택해 무결성을 검사합니다. "
                  "복구 사본은 사용자 확인 후 새 폴더에만 저장합니다. "
                  "현재 방송 설정·SQLite 기억·기획안은 절대 자동 덮어쓰지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 9))
        ttk.Button(tab, text="새 백업 만들기 (18단계 화면으로 이동)",
                   command=lambda: self._tabs.select(archive_tab)).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 9))
        self._recovery_archive_path = tk.StringVar(value="")
        ttk.Entry(row, textvariable=self._recovery_archive_path, state="readonly").pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text="백업 ZIP 선택", command=self._choose_recovery_zip).pack(side="left", padx=(7, 0))
        actions = ttk.Frame(tab)
        actions.pack(anchor="w", pady=(0, 8))
        ttk.Button(actions, text="백업 무결성 검사 (읽기 전용)",
                   command=self._inspect_recovery_zip).pack(side="left")
        ttk.Button(actions, text="새 폴더에 복구 사본 만들기 (수동)",
                   command=self._stage_recovery).pack(side="left", padx=(8, 0))
        self._recovery_status = tk.StringVar(value="대기 · 자동 파일 조회/복구/백업 없음")
        ttk.Label(tab, textvariable=self._recovery_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._recovery_view = tk.Text(tab, height=15, wrap="word", font=("Malgun Gothic", 10))
        self._recovery_view.pack(fill="both", expand=True)
        self._set_recovery_report(
            "백업 ZIP을 선택한 뒤 '무결성 검사'를 눌러 확인하세요.\n"
            "'복구 사본 만들기'는 선택한 상위 폴더 아래 새 " + STAGING_NAME + " 폴더만 만듭니다.\n"
            "기존 파일을 덮어쓰거나 실행 중인 프로그램에 자동 적용하지 않습니다.\n"
            "SQLite 대화 기억은 현재 수동 보관 ZIP에 포함되지 않습니다.\n"
            "승인 대기 단계는 완료 처리하지 않습니다."
        )

    def _set_recovery_report(self, text: str) -> None:
        self._recovery_view.configure(state="normal")
        self._recovery_view.delete("1.0", "end")
        self._recovery_view.insert("1.0", text)
        self._recovery_view.configure(state="disabled")

    def _choose_recovery_zip(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self, title="검증할 AISTING 보관 ZIP 선택", filetypes=[("ZIP 파일", "*.zip")],
        )
        if selected:
            self._recovery_archive_path.set(selected)
            self._recovery_status.set("ZIP 선택 완료 · 검사 전 · 복구 실행 없음")
            self._set_recovery_report("검사 버튼을 눌러 ZIP 내용을 확인해 주세요. 자동 복원은 없습니다.")
        else:
            self._recovery_status.set("파일 선택 취소 · 변경 없음")

    def _inspect_recovery_zip(self) -> None:
        selected = self._recovery_archive_path.get().strip()
        if not selected:
            self._recovery_status.set("백업 ZIP을 먼저 선택해 주세요.")
            return
        try:
            report = inspect_backup(selected)
        except (OSError, ValueError, TypeError, PermissionError, UnicodeError) as exc:
            self._recovery_status.set("검사 실패 · 파일 변경 없음: " + str(exc))
            self._set_recovery_report("ZIP을 사용할 수 없습니다. 복구 사본을 만들지 마세요.")
            return
        self._set_recovery_report(report.describe())
        self._recovery_status.set("백업 SHA256 검사 완료 · 파일 변경/복구 없음")

    def _stage_recovery(self) -> None:
        selected = self._recovery_archive_path.get().strip()
        if not selected:
            self._recovery_status.set("백업 ZIP을 먼저 선택해 주세요.")
            return
        parent = filedialog.askdirectory(
            parent=self, title="새 복구 사본 폴더를 둘 상위 폴더 선택", mustexist=True,
        )
        if not parent:
            self._recovery_status.set("복구 사본 위치 선택 취소 · 변경 없음")
            return
        if not messagebox.askyesno(
            "수동 복구 사본 생성 확인",
            "검증한 ZIP의 파일을 새 '" + STAGING_NAME + "' 폴더에만 복사할까요?\n"
            "기존 파일은 덮어쓰지 않으며 실행 중인 설정·SQLite에는 적용되지 않습니다.\n"
            "이 작업은 실제 설정 복원/방송/설치/승인이 아닙니다.", parent=self,
        ):
            self._recovery_status.set("사용자가 복구 사본 생성 취소 · 변경 없음")
            return
        try:
            report = inspect_backup(selected)
            created = stage_recovery(selected, parent, confirmed=True)
        except (OSError, ValueError, TypeError, PermissionError, UnicodeError) as exc:
            self._recovery_status.set("복구 사본 준비 실패 · 기존 파일 유지: " + str(exc))
            return
        self._set_recovery_report(report.describe() + "\n\n새 복구 사본 폴더: " + str(created))
        self._recovery_status.set("수동 복구 사본 생성 완료 · 기존 설정/SQLite 보존 · 자동 복원 아님")

    def _build_execution_selfcheck(self, tab) -> None:
        """20단계: 사용자 버튼 클릭 이전에는 PC 정보 조회/테스트 실행 없음."""
        ttk.Label(tab, text="20단계 · 개발 환경 수동 자가점검",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 9))
        ttk.Label(
            tab, text="사용자가 버튼을 눌렀을 때만 동봉된 개발 기준·모의 채팅·임시 설정·"
            "임시 SQLite 기억을 검사합니다. 실제 PC 사양/설치 상태/계정은 조회하지 않습니다. "
            "Windows 실기기 및 EXE 검증이나 사용자 승인을 대신하지 않습니다.",
            wraplength=710,
        ).pack(anchor="w", pady=(0, 9))
        ttk.Button(tab, text="오프라인 샘플 자가점검 실행 (수동)",
                   command=self._run_execution_selfcheck).pack(anchor="w", pady=(0, 8))
        self._selfcheck_status = tk.StringVar(value="검사 전 · 자동 실행/PC 사양 조회 없음")
        ttk.Label(tab, textvariable=self._selfcheck_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._selfcheck_view = tk.Text(tab, height=17, wrap="word", state="disabled",
                                      font=("Malgun Gothic", 10))
        self._selfcheck_view.pack(fill="both", expand=True)
        self._set_selfcheck_report(
            "20단계 코드는 개발 환경의 안전한 샘플 실행만 점검합니다.\n"
            "점검 전에는 사용자 PC 정보를 조회하거나 파일을 생성하지 않습니다.\n"
            "수동 점검을 실행해도 실제 사용자 설정·기억은 읽거나 변경하지 않습니다.\n"
            "10단계 승인 및 11~20단계 사용자 PC 실기기 확인은 보류됩니다."
        )

    def _set_selfcheck_report(self, text: str) -> None:
        self._selfcheck_view.configure(state="normal")
        self._selfcheck_view.delete("1.0", "end")
        self._selfcheck_view.insert("1.0", text)
        self._selfcheck_view.configure(state="disabled")

    def _run_execution_selfcheck(self) -> None:
        self._selfcheck_status.set("오프라인 샘플 점검 실행 중 · 실제 PC 조회 없음")
        try:
            report = run_execution_selfcheck()
        except Exception as exc:
            self._selfcheck_status.set("자가점검 실패: " + str(exc))
            self._set_selfcheck_report("예상치 못한 오류가 발생했습니다. 완료 처리하지 않습니다.")
            return
        self._set_selfcheck_report(report.describe())
        self._selfcheck_status.set(
            "샘플 자가점검 5/5 통과 · Windows 실기기 미검증 · 승인 대기"
            if report.passed else "샘플 자가점검 실패 · 보고서 확인 · 승인 대기"
        )

    def _build_core_foundation(self, tab) -> None:
        """21단계: 현재 화면 선택값을 메모리에서만 분석. 코어/방송 실행 없음."""
        ttk.Label(tab, text="21단계 · 방송 코어 기반 프로젝트 준비",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            tab, text="현재 방송 설정 화면의 선택값과 채팅 연습 응답 방식을 기반으로 "
            "입력·답변·기억·음성·아바타·송출의 연결 계약과 미구현 항목을 확인합니다. "
            "설정 저장/PC 정보 조회/AI 연결/실제 방송은 수행하지 않습니다.",
            wraplength=710,
        ).pack(anchor="w", pady=(0, 10))
        ttk.Button(tab, text="현재 선택값으로 코어 구성도 확인 (실행 아님)",
                   command=self._preview_core_foundation).pack(anchor="w", pady=(0, 8))
        self._core_status = tk.StringVar(value="구성도 미검토 · 코어/방송 자동 실행 없음")
        ttk.Label(tab, textvariable=self._core_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._core_view = tk.Text(tab, height=16, wrap="word", state="disabled",
                                  font=("Malgun Gothic", 10))
        self._core_view.pack(fill="both", expand=True)
        self._set_core_report(
            "21단계 방송 코어 연결 계약의 소스 구조를 준비했습니다.\n"
            "구성도는 현재 화면 선택값을 확인한 후에만 생성됩니다.\n"
            "실제 방송 코어 실행(22단계)과 외부 오픈소스 통합은 아직 구현하지 않았습니다.\n"
            "원본 기획안/사용자 승인/PC 실기기 검증은 변경하지 않습니다."
        )

    def _set_core_report(self, text: str) -> None:
        self._core_view.configure(state="normal")
        self._core_view.delete("1.0", "end")
        self._core_view.insert("1.0", text)
        self._core_view.configure(state="disabled")

    def _preview_core_foundation(self) -> None:
        """저장하지 않은 선택도 미리보기 가능; 디스크·네트워크에 접근하지 않는다."""
        try:
            selected = deepcopy(self.settings)
            selected["platforms"] = [code for code, flag in self._platforms.items() if flag.get()]
            selected["content"] = CONTENTS[self._content.get()]
            selected["persona_mode"] = PERSONA_MODES[self._persona_mode.get()]
            selected["persona"] = {key: widget.get().strip() for key, widget in self._persona.items()}
            selected["avatar"] = AVATARS[self._avatar.get()]
            selected["voice"] = VOICES[self._voice.get()]
            selected["voice_profile"] = validate_voice_profile({
                "installed_voice_name": self._voice_preferred_name,
                "rate": int(self._voice_rate.get()),
                "volume": int(self._voice_volume.get()),
            })
            mode = RUNTIME_MODES[self._selected_mode.get()]
            plan = build_core_blueprint(selected, mode)
            self._set_core_report(plan.describe())
            self._core_status.set("코어 연결 계약 7개 구성도 확인 · 실행/설치/방송 없음 · 승인 대기")
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._set_core_report("구성도 생성 실패 · 현재 선택값을 확인해 주세요.\n" + str(exc))
            self._core_status.set("구성도 생성 실패 · 코어 실행 없음 · 승인 대기")

    def _build_core_execution(self, tab) -> None:
        """22단계: 명시적 클릭만 처리하는 메모리 내 모의 코어 GUI."""
        self._core_session: OfflineCoreSession | None = None
        ttk.Label(tab, text="22단계 · 기본 코어 수동 실행 (모의 전용)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="이 탭은 별도 모의 코어입니다. 현재 설정의 선택값만 메모리에서 검증합니다. "
                  "로컬 Ollama 모드가 선택돼 있어도 AI 연결을 하지 않습니다. "
                  "기존 채팅 연습/SQLite 기억·설정 파일·실제 방송은 건드리지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._core_input = tk.Text(tab, height=5, wrap="word", font=("Malgun Gothic", 10))
        self._core_input.pack(fill="x", pady=(0, 7))
        self._core_input.insert("1.0", "철수: 안녕\n영희: 오늘 뭐 해?")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="대본 추가 (수동)", command=self._core_enqueue).pack(side="left")
        ttk.Button(actions, text="1건 모의 실행", command=lambda: self._core_run(1)).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="최대 50건 모의 실행", command=lambda: self._core_run(50)).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="모의 세션 초기화", command=self._core_reset).pack(side="right")
        recovery_actions = ttk.Frame(tab)
        recovery_actions.pack(fill="x", pady=(0, 8))
        ttk.Button(recovery_actions, text="실패 건 수동 재시도 (최대 2회)",
                   command=self._core_retry_failed).pack(side="left")
        ttk.Button(recovery_actions, text="실패 건 제외 (별도 확인)",
                   command=self._core_discard_failed).pack(side="left", padx=(8, 0))
        self._core_exec_status = tk.StringVar(value="대기 0건 · 처리 0건 · 자동 실행 없음")
        ttk.Label(tab, textvariable=self._core_exec_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._core_exec_view = tk.Text(tab, height=14, wrap="word", state="disabled",
                                       font=("Malgun Gothic", 10))
        self._core_exec_view.pack(fill="both", expand=True)
        self._set_core_exec_report("아직 실행하지 않았습니다. 대본을 추가한 후 실행 버튼을 눌러야 합니다.\n"
                                   "외부 모델/음성/아바타/방송 연결 없음 · 승인/실기기 검증 별도.")

    def _set_core_exec_report(self, report: str) -> None:
        self._core_exec_view.configure(state="normal")
        self._core_exec_view.delete("1.0", "end")
        self._core_exec_view.insert("1.0", report)
        self._core_exec_view.configure(state="disabled")

    def _core_selection(self) -> dict[str, object]:
        """현재 화면 값만 읽고 PC 정보/설정 파일은 읽지 않는다."""
        selected = deepcopy(self.settings)
        selected["platforms"] = [code for code, flag in self._platforms.items() if flag.get()]
        selected["content"] = CONTENTS[self._content.get()]
        # A mock core session uses the committed broadcasting character too.
        # Uncommitted editor drafts may only appear in explicitly labeled previews.
        selected["persona_mode"] = self.settings["persona_mode"]
        selected["persona"] = deepcopy(self.settings["persona"])
        selected["avatar"] = AVATARS[self._avatar.get()]
        selected["voice"] = VOICES[self._voice.get()]
        selected["voice_profile"] = validate_voice_profile({
            "installed_voice_name": self._voice_preferred_name,
            "rate": int(self._voice_rate.get()),
            "volume": int(self._voice_volume.get()),
        })
        return selected

    def _core_get_session(self) -> OfflineCoreSession:
        selected = self._core_selection()
        if self._core_session is None:
            candidate = OfflineCoreSession(selected)
            self._core_session = candidate
        else:
            self._core_session.update_selection(selected)
        return self._core_session

    def _core_update_status(self, suffix: str) -> None:
        session = self._core_session
        pending = session.pending_count if session else 0
        processed = session.total_processed if session else 0
        self._core_exec_status.set(f"대기 {pending}건 · 처리 {processed}건 · {suffix}")

    def _core_enqueue(self) -> None:
        try:
            session = self._core_get_session()
            amount = session.enqueue(self._core_input.get("1.0", "end-1c"))
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._core_update_status("대본/선택값 오류 · 대기열 보존")
            self._set_core_exec_report("추가 실패: " + str(exc))
            return
        self._core_input.delete("1.0", "end")
        self._core_update_status(f"{amount}건 추가 · 실행 버튼 대기 · 모의 전용")
        self._set_core_exec_report("모의 코어 입력 대기열에 추가했습니다. 아직 답변은 생성하지 않았습니다.")

    def _core_run(self, count: int) -> None:
        try:
            session = self._core_get_session()
            result = session.run_batch(count)
        except CoreBatchError as exc:
            failure = exc.failure
            self._core_update_status("실행 오류 · 실패한 입력 보존 · 자동 재시도 없음")
            self._set_core_exec_report(
                "실행 중 오류: " + str(exc) +
                (f"\n오류 분류: {failure.code} · 시도 {failure.attempts}/3회" if failure else "\n재시도 상한/실행 차단") +
                "\n성공 처리 " + str(len(exc.processed)) +
                "건 · 실패한 항목부터 재시도 가능.\n" +
                "\n".join(f"{x.input.sender}: {x.input.text}\nAI(모의): {x.text}" for x in exc.processed))
            return
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._core_update_status("실행 전 검증 실패 · 대기열 보존")
            self._set_core_exec_report("실행 실패: " + str(exc))
            return
        self._core_update_status("모의 실행 완료 · 방송/외부 연결 없음")
        self._set_core_exec_report(result.describe())

    def _core_retry_failed(self) -> None:
        """27단계: 사용자가 클릭한 경우에만 실패한 선두 입력을 단 한 번 재시도."""
        session = self._core_session
        if session is None or session.last_failure is None:
            self._core_update_status("재시도할 실패 건 없음")
            self._set_core_exec_report("실패 건이 없으므로 재시도하지 않았습니다.")
            return
        try:
            reply = session.retry_failed()
        except (CoreGenerationError, CoreInvalidReplyError, CoreRetryLimitError) as exc:
            failure = session.last_failure
            self._core_update_status("재시도 실패 · 실패 입력 보존 · 자동 반복 없음")
            self._set_core_exec_report(
                f"수동 재시도 실패: {exc}\n" +
                (f"분류: {failure.code} · 시도 {failure.attempts}/3회" if failure else "") +
                "\n확인 후 제외하거나 세션을 초기화할 수 있습니다.")
            return
        self._core_update_status("수동 재시도 1건 성공 · 이후 입력은 대기")
        self._set_core_exec_report(f"수동 재시도 성공: {reply.input.sender}: {reply.input.text}\nAI(모의): {reply.text}")

    def _core_discard_failed(self) -> None:
        """명시적 확인 없이는 대기열에서 입력을 삭제하지 않는다."""
        session = self._core_session
        if session is None or session.last_failure is None:
            self._core_update_status("제외할 실패 건 없음")
            self._set_core_exec_report("실패 건이 없으므로 입력을 제외하지 않았습니다.")
            return
        if not messagebox.askyesno(
            "실패 입력 제외 확인", "현재 실패한 입력 1건을 대기열에서 제외할까요?\n"
            "이 작업은 모의 세션에서만 적용되며 성공한 답변/다른 입력은 유지됩니다.",
            parent=self,
        ):
            self._core_update_status("제외 취소 · 실패 입력 유지")
            return
        removed = session.discard_failed(confirmed=True)
        self._core_update_status("확인 후 실패 입력 1건 제외 · 나머지 대기열 보존")
        self._set_core_exec_report(f"사용자 확인으로 제외: {removed.sender}: {removed.text}\n"
                                   "나머지 입력은 자동 실행되지 않습니다.")

    def _core_reset(self) -> None:
        if self._core_session is not None:
            self._core_session.reset()
        self._core_update_status("모의 세션만 초기화 · 기존 데이터 유지")
        self._set_core_exec_report("모의 세션 초기화. 기존 설정·채팅 연습·SQLite 기억은 변경하지 않았습니다.")

    def _build_core_ai_connection(self, tab) -> None:
        """23단계: 실제 모델을 연결하지 않는 코어 전용 방식 선택."""
        ttk.Label(tab, text="23단계 · 코어 AI 모델 연결 방식 설정",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="코어 AI 연결 후보만 정합니다. 실제 모델·PC·네트워크를 조회하지 않습니다. "
                  "이전 채팅 연습의 설정은 바꾸지 않고, 코어 실행은 항상 모의 답변만 사용합니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 10))
        self._core_ai_mode = tk.StringVar(value="모의 답변 (인터넷 불필요)")
        self._core_ai_model = tk.StringVar(value="")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="연결 방식").pack(side="left")
        self._core_ai_selector = ttk.Combobox(
            row, textvariable=self._core_ai_mode, values=tuple(RUNTIME_MODES),
            state="readonly", width=32,
        )
        self._core_ai_selector.pack(side="left", padx=(10, 0))
        model_row = ttk.Frame(tab)
        model_row.pack(fill="x", pady=(0, 8))
        ttk.Label(model_row, text="로컬 모델 이름").pack(side="left")
        ttk.Entry(model_row, textvariable=self._core_ai_model, width=38).pack(side="left", padx=(10, 0))
        ttk.Label(tab, text="로컬 후보는 127.0.0.1:11434 전용. "
                  "모의 답변 선택 시 모델 이름을 비워 두세요. 클라우드/임의 서버 주소는 지원하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="연결 방식 미리보기", command=self._preview_core_ai).pack(side="left")
        ttk.Button(actions, text="코어에 계획만 적용 (연결 없음)",
                   command=self._apply_core_ai).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="모의 방식으로 초기화", command=self._reset_core_ai).pack(side="left", padx=(8, 0))
        record_actions = ttk.Frame(tab)
        record_actions.pack(fill="x", pady=(0, 8))
        ttk.Button(record_actions, text="연결 계획 저장 (수동)", command=self._save_core_ai).pack(side="left")
        ttk.Button(record_actions, text="저장된 계획 불러오기", command=self._load_core_ai).pack(side="left", padx=(8, 0))
        ttk.Button(record_actions, text="저장된 계획 삭제", command=self._delete_core_ai).pack(side="left", padx=(8, 0))
        self._core_ai_status = tk.StringVar(value="모의 방식 기본값 · 실제 AI 연결 없음")
        ttk.Label(tab, textvariable=self._core_ai_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._core_ai_view = tk.Text(tab, height=15, wrap="word", state="disabled",
                                     font=("Malgun Gothic", 10))
        self._core_ai_view.pack(fill="both", expand=True)
        self._set_core_ai_report("아직 연결 계획을 적용하지 않았습니다.\n"
                                 "선택값은 기본적으로 메모리에만 보관하며, 수동 저장 확인 시에만 별도 파일에 기록합니다.\n"
                                 "실제 로컬 Ollama 연결 시험·방송 시작·설치·PC 사양 조회 없음.")

    def _set_core_ai_report(self, report: str) -> None:
        self._core_ai_view.configure(state="normal")
        self._core_ai_view.delete("1.0", "end")
        self._core_ai_view.insert("1.0", report)
        self._core_ai_view.configure(state="disabled")

    def _core_ai_candidate(self):
        mode = RUNTIME_MODES[self._core_ai_mode.get()]
        return build_core_ai_plan(mode, self._core_ai_model.get().strip())

    def _preview_core_ai(self) -> None:
        try:
            plan = self._core_ai_candidate()
        except (KeyError, ValueError, TypeError) as exc:
            self._core_ai_status.set("연결 계획 검증 실패 · 이전 계획 유지")
            self._set_core_ai_report("미리보기 실패: " + str(exc))
            return
        self._core_ai_status.set("오프라인 계획 미리보기만 완료 · 적용/연결 안 함")
        self._set_core_ai_report(plan.describe())

    def _apply_core_ai(self) -> None:
        try:
            plan = self._core_ai_candidate()
            session = self._core_get_session()
            session.configure_ai_plan(plan)
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._core_ai_status.set("계획 적용 실패 · 기존 계획/대기열 유지")
            self._set_core_ai_report("적용 실패: " + str(exc))
            return
        self._core_ai_status.set("코어 메모리에 계획 적용 · 실제 모델 연결/모의 코어 변경 없음")
        self._set_core_ai_report(plan.describe() + "\n\n현재 코어 세션의 계획만 갱신했습니다.")

    def _reset_core_ai(self) -> None:
        self._core_ai_mode.set("모의 답변 (인터넷 불필요)")
        self._core_ai_model.set("")
        if self._core_session is not None:
            self._core_session.configure_ai_plan(build_core_ai_plan())
        self._core_ai_status.set("모의 연결 계획으로 초기화 · 대기열/이력 보존")
        self._set_core_ai_report(build_core_ai_plan().describe())

    def _save_core_ai(self) -> None:
        try:
            plan = self._core_ai_candidate()
        except (KeyError, ValueError, TypeError) as exc:
            self._core_ai_status.set("저장 전 검증 실패 · 기존 기록 유지: " + str(exc))
            return
        if not messagebox.askyesno(
            "코어 AI 연결 계획 저장", "선택한 방식만 별도 로컬 파일에 저장할까요?\n"
            "모델 연결·설치·방송·자동 적용은 하지 않습니다.", parent=self,
        ):
            self._core_ai_status.set("사용자가 계획 저장 취소 · 변경 없음")
            return
        try:
            save_core_ai_plan(plan, core_ai_profile_path(), operator_confirmed=True)
        except (OSError, ValueError, TypeError, PermissionError) as exc:
            self._core_ai_status.set("연결 계획 저장 실패: " + str(exc))
            return
        self._core_ai_status.set("계획 파일만 수동 저장 · 코어/모델 연결/자동 적용 없음")

    def _load_core_ai(self) -> None:
        try:
            plan = load_core_ai_plan(core_ai_profile_path())
        except (OSError, ValueError, TypeError) as exc:
            self._core_ai_status.set("계획 불러오기 실패 · 기존 선택 유지: " + str(exc))
            return
        if plan is None:
            self._core_ai_status.set("저장된 코어 연결 계획 없음 · 기존 선택 유지")
            return
        self._core_ai_mode.set(next(name for name, code in RUNTIME_MODES.items() if code == plan.mode))
        self._core_ai_model.set(plan.model_name)
        self._core_ai_status.set("계획 수동 불러오기 · 코어 적용/AI 연결 없음")
        self._set_core_ai_report(plan.describe())

    def _delete_core_ai(self) -> None:
        if not messagebox.askyesno(
            "코어 AI 계획 기록 삭제", "저장된 코어 AI 연결 계획 파일 하나만 삭제할까요?\n"
            "현재 화면/코어 계획/기존 설정/기억은 유지합니다.", parent=self,
        ):
            self._core_ai_status.set("사용자가 계획 삭제 취소 · 변경 없음")
            return
        try:
            delete_core_ai_plan(core_ai_profile_path(), operator_confirmed=True)
        except (OSError, ValueError, TypeError, PermissionError) as exc:
            self._core_ai_status.set("계획 삭제 실패 · 기록 보존: " + str(exc))
            return
        self._core_ai_status.set("저장된 계획 파일만 삭제 · 현재 코어/설정/기억 유지")

    def _build_core_ai_probe(self, tab) -> None:
        """24단계: 승인 전 모의 프로토콜 시험 / 명시적 동의 후 loopback만 조회."""
        ttk.Label(tab, text="24단계 · AI 연결 시험", font=("Malgun Gothic", 13, "bold")).pack(
            anchor="w", pady=(0, 8))
        ttk.Label(tab, text="23단계 '코어 AI 연결 방식' 화면의 현재 선택값을 시험합니다. "
                  "모의 시험은 PC/네트워크에 접속하지 않습니다. 실제 조회는 별도 확인 후 "
                  "동일 PC의 127.0.0.1:11434/api/tags에서 모델 이름만 확인합니다. "
                  "실제 AI 답변 생성·프로그램 설치·방송 송출은 하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 10))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Button(row, text="오프라인 가상 응답 시험", command=self._simulate_core_ai_probe).pack(side="left")
        ttk.Button(row, text="실제 PC 로컬 조회 (별도 승인 필요)",
                   command=self._run_core_ai_probe).pack(side="left", padx=(8, 0))
        self._core_probe_status = tk.StringVar(value="미실행 · PC 정보 자동 수집/연결 없음")
        ttk.Label(tab, textvariable=self._core_probe_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._core_probe_view = tk.Text(tab, height=15, wrap="word", state="disabled",
                                        font=("Malgun Gothic", 10))
        self._core_probe_view.pack(fill="both", expand=True)
        self._set_core_probe_report("아직 시험하지 않았습니다. 실제 연결 성공으로 간주하지 않습니다.")

    def _set_core_probe_report(self, report: str) -> None:
        self._core_probe_view.configure(state="normal")
        self._core_probe_view.delete("1.0", "end")
        self._core_probe_view.insert("1.0", report)
        self._core_probe_view.configure(state="disabled")

    def _simulate_core_ai_probe(self) -> None:
        try:
            plan = self._core_ai_candidate()
            result = simulate_connection_test(plan)
        except (KeyError, ValueError, TypeError) as exc:
            self._core_probe_status.set("가상 시험 실패 · 선택값 확인 필요")
            self._set_core_probe_report("검증 실패: " + str(exc))
            return
        self._core_probe_status.set("오프라인 가상 응답 검증 완료 · 실제 연결 확인 아님")
        self._set_core_probe_report(result.describe())

    def _run_core_ai_probe(self) -> None:
        try:
            plan = self._core_ai_candidate()
        except (KeyError, ValueError, TypeError) as exc:
            self._core_probe_status.set("실제 조회 전 선택값 검증 실패")
            self._set_core_probe_report("검증 실패: " + str(exc))
            return
        if plan.mode != "local_ollama":
            self._core_probe_status.set("모의 답변 방식 · 실제 로컬 모델 조회 불필요")
            return
        if not messagebox.askyesno(
            "동일 PC Ollama 조회 승인", "지금 선택한 로컬 모델의 존재 여부를 확인할까요?\n"
            "사용자가 승인하면 127.0.0.1:11434/api/tags에 단 한 번 접속하여 "
            "로컬 모델 목록을 읽습니다. 외부 서버/프록시/모델 실행/다운로드/설치는 사용하지 않습니다.\n"
            "취소하면 PC 조회나 네트워크 연결은 전혀 실행하지 않습니다.", parent=self,
        ):
            self._core_probe_status.set("사용자가 로컬 조회 취소 · 연결 없음")
            return
        try:
            result = probe_local_model(plan, operator_confirmed=True)
        except (ValueError, TypeError, PermissionError, OSError) as exc:
            self._core_probe_status.set("로컬 조회 실패 · 코어/설정 불변")
            self._set_core_probe_report("조회 실패: " + str(exc))
            return
        self._core_probe_status.set("로컬 조회 종료 · " + ("선택 모델 발견" if result.model_available else "선택 모델 사용 가능 미확인"))
        self._set_core_probe_report(result.describe())

    def _build_korean_dialogue_test(self, tab) -> None:
        """25단계: 별도 메모리 모의 세션으로 한국어 구조 회귀 시험."""
        ttk.Label(tab, text="25단계 · 한국어 대화 시험 (모의 전용)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="아래 예시를 수정할 수 있습니다. 버튼을 눌렀을 때만 별도 메모리 코어로 "
                  "한글·순서·중복·응답 문자 형식을 검사합니다. 한국어 자연스러움/의미 이해는 "
                  "판정하지 않습니다. 로컬 Ollama를 선택했어도 연결하지 않습니다. "
                  "기존 설정·채팅 연습·SQLite 기억·방송은 변경하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._korean_test_input = tk.Text(tab, height=7, wrap="word", font=("Malgun Gothic", 10))
        self._korean_test_input.pack(fill="x", pady=(0, 7))
        self._korean_test_input.insert("1.0", SAMPLE_KOREAN_SCRIPT)
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Button(row, text="오프라인 한국어 구조 시험 (수동)",
                   command=self._run_korean_dialogue_test).pack(side="left")
        ttk.Button(row, text="기본 예시 다시 넣기", command=self._reset_korean_test_input).pack(
            side="left", padx=(8, 0))
        self._korean_test_status = tk.StringVar(value="미실행 · 실제 AI 연결/PC 조회 없음")
        ttk.Label(tab, textvariable=self._korean_test_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._korean_test_view = tk.Text(tab, height=11, wrap="word", state="disabled",
                                         font=("Malgun Gothic", 10))
        self._korean_test_view.pack(fill="both", expand=True)
        self._set_korean_test_report("아직 실행하지 않았습니다. 실제 모델 한국어 대화 품질 검증은 별도 승인 대기입니다.")

    def _set_korean_test_report(self, report: str) -> None:
        self._korean_test_view.configure(state="normal")
        self._korean_test_view.delete("1.0", "end")
        self._korean_test_view.insert("1.0", report)
        self._korean_test_view.configure(state="disabled")

    def _reset_korean_test_input(self) -> None:
        self._korean_test_input.delete("1.0", "end")
        self._korean_test_input.insert("1.0", SAMPLE_KOREAN_SCRIPT)
        self._korean_test_status.set("기본 예시만 다시 표시 · 실행/저장/연결 없음")

    def _run_korean_dialogue_test(self) -> None:
        try:
            selection = self._core_selection()
            report = run_korean_dialogue_test(selection, self._korean_test_input.get("1.0", "end-1c"))
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._korean_test_status.set("한국어 시험 입력/선택값 오류 · 기존 데이터 유지")
            self._set_korean_test_report("실행 전 검증 실패: " + str(exc))
            return
        self._korean_test_status.set(
            f"오프라인 구조 시험 {'통과' if report.passed else '실패'} "
            f"{report.passed_count}/{report.total}건 · 실제 한국어 AI 품질 미검증")
        self._set_korean_test_report(report.describe())

    def _build_context_retention_test(self, tab) -> None:
        """26단계: 기존 코어와 분리된 메모리 모의 맥락 전달 검증."""
        ttk.Label(tab, text="26단계 · 대화 맥락 전달 시험 (모의 전용)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="사용자가 버튼을 누르면 별도 메모리 세션에서 최근 최대 8건의 "
                  "대화 이력이 답변 포트로 정확히 전달되는지 확인합니다. 10건 이상이면 "
                  "오래된 이력 잘림도 검사합니다. 실제 AI의 의미 이해·장기 기억은 평가하지 "
                  "않습니다. 사용자 파일·SQLite·PC 조회·모델 연결·방송 없음.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._context_test_input = tk.Text(tab, height=8, wrap="word", font=("Malgun Gothic", 10))
        self._context_test_input.pack(fill="x", pady=(0, 7))
        self._context_test_input.insert("1.0", SAMPLE_CONTEXT_SCRIPT)
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Button(row, text="오프라인 맥락 전달 시험 (수동)",
                   command=self._run_context_retention_test).pack(side="left")
        ttk.Button(row, text="기본 예시 다시 넣기", command=self._reset_context_test_input).pack(
            side="left", padx=(8, 0))
        self._context_test_status = tk.StringVar(value="미실행 · 실제 모델/PC 조회 없음")
        ttk.Label(tab, textvariable=self._context_test_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._context_test_view = tk.Text(tab, height=11, wrap="word", state="disabled",
                                          font=("Malgun Gothic", 10))
        self._context_test_view.pack(fill="both", expand=True)
        self._set_context_test_report("아직 실행하지 않았습니다. 실제 모델 맥락 이해는 승인 대기입니다.")

    def _set_context_test_report(self, text: str) -> None:
        self._context_test_view.configure(state="normal")
        self._context_test_view.delete("1.0", "end")
        self._context_test_view.insert("1.0", text)
        self._context_test_view.configure(state="disabled")

    def _reset_context_test_input(self) -> None:
        self._context_test_input.delete("1.0", "end")
        self._context_test_input.insert("1.0", SAMPLE_CONTEXT_SCRIPT)
        self._context_test_status.set("기본 예시만 복원 · 실행/저장/연결 없음")

    def _run_context_retention_test(self) -> None:
        try:
            selection = self._core_selection()
            report = run_context_retention_test(
                selection, self._context_test_input.get("1.0", "end-1c"))
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._context_test_status.set("맥락 시험 입력/선택값 오류 · 기존 데이터 유지")
            self._set_context_test_report("실행 전 검증 실패: " + str(exc))
            return
        self._context_test_status.set(
            f"오프라인 맥락 전달 {'통과' if report.passed else '실패'} "
            f"{report.passed_count}/{report.total}건 · 실제 AI 의미 이해 미검증")
        self._set_context_test_report(report.describe())

    def _build_response_error_test(self, tab) -> None:
        """27단계: 실제 네트워크 없이 독립된 모의 포트에 결함을 주입한다."""
        ttk.Label(tab, text="27단계 · 기본 응답 오류 처리 (오프라인 모의 전용)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="시간 초과·연결 오류·생성 예외·잘못된 답변을 가상으로 주입하여 "
                  "실패한 입력의 보존, 최대 3회 시도, 확인 후 제외 및 FIFO 복구를 검사합니다. "
                  "기존 코어/설정/SQLite를 변경하지 않으며 실제 AI·PC 조회·방송은 하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="시험 항목").pack(side="left")
        labels = {"전체 8개 시나리오": "all"}
        labels.update({label: code for code, label in SCENARIO_LABELS.items()})
        self._response_error_choices = labels
        self._response_error_choice = tk.StringVar(value="전체 8개 시나리오")
        ttk.Combobox(row, textvariable=self._response_error_choice, state="readonly",
                     values=tuple(labels), width=30).pack(side="left", padx=(8, 8))
        ttk.Button(row, text="오프라인 오류 시험 (수동)",
                   command=self._run_response_error_test).pack(side="left")
        self._response_error_status = tk.StringVar(value="미실행 · 모델/PC 접근 없음")
        ttk.Label(tab, textvariable=self._response_error_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._response_error_view = tk.Text(tab, height=14, wrap="word", state="disabled",
                                            font=("Malgun Gothic", 10))
        self._response_error_view.pack(fill="both", expand=True)
        self._set_response_error_report("아직 실행하지 않았습니다. 실제 AI 오류 복구 품질은 승인 후 별도 검증합니다.")

    def _set_response_error_report(self, text: str) -> None:
        self._response_error_view.configure(state="normal")
        self._response_error_view.delete("1.0", "end")
        self._response_error_view.insert("1.0", text)
        self._response_error_view.configure(state="disabled")

    def _run_response_error_test(self) -> None:
        try:
            selection = self._core_selection()
            code = self._response_error_choices[self._response_error_choice.get()]
            report = run_response_error_test(selection, code)
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._response_error_status.set("오류 시험 입력/선택값 오류 · 기존 데이터 유지")
            self._set_response_error_report("실행 전 검증 실패: " + str(exc))
            return
        self._response_error_status.set(
            f"오프라인 응답 오류 시험 {'통과' if report.passed else '실패'} "
            f"{report.passed_count}/{len(report.checks)}건 · 실제 모델 미연결")
        self._set_response_error_report(report.describe())

    def _build_style_consistency(self, tab) -> None:
        ttk.Label(tab, text="33단계 · 캐릭터 말투 구조 점검 (저장·모델 호출 없음)").pack(anchor="w")
        ttk.Label(tab, text="시험 응답 (한 줄당 하나, 선택 사항; 실제 모델 출력 아님)").pack(anchor="w")
        self._style_samples = tk.Text(tab, height=5)
        self._style_samples.pack(fill="x")
        ttk.Button(tab, text="현재 캐릭터 말투 점검", command=self._run_style_consistency).pack(anchor="w", pady=8)
        self._style_status = tk.StringVar(value="미실행 · 사용자 요청 시에만 점검")
        ttk.Label(tab, textvariable=self._style_status).pack(anchor="w")
        self._style_result = tk.Text(tab, height=13, state="disabled", wrap="word")
        self._style_result.pack(fill="both", expand=True)

    def _run_style_consistency(self) -> None:
        try:
            mode = PERSONA_MODES[self._persona_mode.get()]
            draft = {key: entry.get() for key, entry in self._persona.items()}
            raw = self._style_samples.get("1.0", "end-1c")
            samples = tuple(raw.splitlines()) if raw else ()
            report = check_style_consistency(mode, draft, self._preference_likes.get(),
                                             self._preference_dislikes.get(), samples)
            message = report.describe()
            self._style_status.set("구조 검사 통과" if report.passed else "구조 검사 실패")
        except (ValueError, TypeError, KeyError) as exc:
            message = "입력 오류: " + str(exc)
            self._style_status.set("입력 확인 실패")
        self._style_result.configure(state="normal")
        self._style_result.delete("1.0", "end")
        self._style_result.insert("1.0", message)
        self._style_result.configure(state="disabled")

    def _build_reaction_directions(self, tab) -> None:
        ttk.Label(tab, text="34단계 · 상황별 반응 방향 (선택·읽기 전용)").pack(anchor="w")
        ttk.Label(tab, text="입력하지 않은 상황의 규칙은 생성하지 않습니다. 실제 모델 호출 없음.").pack(anchor="w")
        self._reaction_inputs = {}
        for situation in SITUATIONS:
            ttk.Label(tab, text=situation).pack(anchor="w", pady=(7, 0))
            field = ttk.Entry(tab)
            field.pack(fill="x")
            self._reaction_inputs[situation] = field
        ttk.Button(tab, text="반응 방향 미리보기", command=self._run_reaction_directions).pack(anchor="w", pady=8)
        self._reaction_status = tk.StringVar(value="미실행 · 저장하지 않습니다")
        ttk.Label(tab, textvariable=self._reaction_status).pack(anchor="w")
        self._reaction_result = tk.Text(tab, height=12, state="disabled", wrap="word")
        self._reaction_result.pack(fill="both", expand=True)

    def _run_reaction_directions(self) -> None:
        try:
            mode = PERSONA_MODES[self._persona_mode.get()]
            draft = {key: entry.get() for key, entry in self._persona.items()}
            directions = {key: field.get() for key, field in self._reaction_inputs.items()}
            report = review_reaction_directions(mode, draft, directions,
                                                self._preference_likes.get(), self._preference_dislikes.get())
            message = report.describe()
            self._reaction_status.set("구조 검사 통과" if report.passed else "구조 검사 실패")
        except (ValueError, TypeError, KeyError) as exc:
            message = "입력 오류: " + str(exc)
            self._reaction_status.set("입력 확인 실패")
        self._reaction_result.configure(state="normal")
        self._reaction_result.delete("1.0", "end")
        self._reaction_result.insert("1.0", message)
        self._reaction_result.configure(state="disabled")

    def _build_operator_boundaries(self, tab) -> None:
        ttk.Label(tab, text="35단계 · 운영자가 정하는 캐릭터 금기·제한사항").pack(anchor="w")
        ttk.Label(tab, text="비워두면 제한을 새로 만들지 않습니다. 한 줄에 하나씩, 최대 12개.\n"
                        "실제 모델·채팅 필터는 연결되지 않았습니다. 저장·불러오기·삭제는 모두 수동입니다.",
                  wraplength=710).pack(anchor="w", pady=(5, 8))
        self._boundary_input = tk.Text(tab, height=7, wrap="word", font=("Malgun Gothic", 10))
        self._boundary_input.pack(fill="x")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=8)
        ttk.Button(row, text="구조·프롬프트 미리보기", command=self._preview_boundaries).pack(side="left")
        ttk.Button(row, text="확인 후 저장", command=self._save_boundaries).pack(side="left", padx=5)
        ttk.Button(row, text="기록 수동 불러오기", command=self._load_boundaries).pack(side="left")
        ttk.Button(row, text="기록 삭제", command=self._delete_boundaries).pack(side="left", padx=5)
        self._boundary_status = tk.StringVar(value="미실행 · 금기 미설정 · 자동 적용 없음")
        ttk.Label(tab, textvariable=self._boundary_status, wraplength=720).pack(anchor="w")
        self._boundary_result = tk.Text(tab, height=12, wrap="word", state="disabled")
        self._boundary_result.pack(fill="both", expand=True)

    def _boundary_lines(self) -> tuple[str, ...]:
        raw = self._boundary_input.get("1.0", "end-1c")
        return validate_boundaries(raw.splitlines() if raw.strip() else [])

    def _boundary_show(self, status: str, message: str) -> None:
        self._boundary_status.set(status)
        self._boundary_result.configure(state="normal")
        self._boundary_result.delete("1.0", "end")
        self._boundary_result.insert("1.0", message)
        self._boundary_result.configure(state="disabled")

    def _preview_boundaries(self) -> None:
        try:
            report = review_boundaries(
                PERSONA_MODES[self._persona_mode.get()],
                {key: entry.get() for key, entry in self._persona.items()},
                self._boundary_lines(), self._preference_likes.get(), self._preference_dislikes.get())
            self._boundary_show("구조 검사 통과 · 모델 적용 전", report.describe())
        except (ValueError, TypeError, KeyError) as exc:
            self._boundary_show("입력 확인 실패", "입력 오류: " + str(exc))

    def _save_boundaries(self) -> None:
        try:
            lines = self._boundary_lines()
            if not messagebox.askyesno("로컬 저장 확인", "입력한 금기·제한사항만 PC에 저장할까요?\n"
                                     "다른 캐릭터 설정이나 기억은 변경하지 않습니다.", parent=self):
                self._boundary_status.set("저장 취소 · 기존 기록 유지")
                return
            save_boundaries(boundaries_path(), lines, operator_confirmed=True)
            self._boundary_show("운영자 확인 후 로컬 저장 완료 · 자동 적용 없음",
                                f"{len(lines)}개 항목 저장. 실제 AI 응답 차단 기능은 아직 연결되지 않았습니다.")
        except (ValueError, TypeError, OSError) as exc:
            self._boundary_show("저장 실패 · 기존 데이터 유지", "저장 오류: " + str(exc))

    def _load_boundaries(self) -> None:
        try:
            lines = load_boundaries(boundaries_path())
            if lines is None:
                self._boundary_show("저장 기록 없음 · 입력 유지", "저장된 금기·제한사항이 없습니다.")
                return
            self._boundary_input.delete("1.0", "end")
            self._boundary_input.insert("1.0", "\n".join(lines))
            self._boundary_show("수동 불러오기 완료 · 자동 적용 없음", f"{len(lines)}개 운영자 입력 복원")
        except (ValueError, OSError) as exc:
            self._boundary_show("불러오기 실패 · 입력 유지", "읽기 오류: " + str(exc))

    def _delete_boundaries(self) -> None:
        if not messagebox.askyesno("삭제 확인 1/2", "저장된 금기·제한사항 기록만 삭제할까요?", parent=self):
            return
        if not messagebox.askyesno("삭제 확인 2/2", "복구되지 않습니다. 기록을 삭제할까요?", parent=self):
            return
        try:
            removed = delete_boundaries(boundaries_path(), operator_confirmed=True)
            self._boundary_show("로컬 기록 삭제 완료" if removed else "삭제할 기록 없음",
                                "현재 입력란·기존 설정·채팅 기억은 변경하지 않았습니다.")
        except (ValueError, OSError) as exc:
            self._boundary_show("삭제 실패", "삭제 오류: " + str(exc))

    def _build_basic_reaction_test(self, tab) -> None:
        """원본 계획 35: 버튼 클릭 시 분리된 메모리 모의 세션에서만 실행."""
        ttk.Label(tab, text="원본 35단계 · 기본 대화 반응 검사 (실제 AI 미연결)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="모든 채팅에 순서대로 반응하는지, 반복 채팅이 사라지지 않는지, "
                  "직전 맥락이 전달되는지 검사합니다. 예시를 수정할 수 있습니다. "
                  "버튼을 눌렀을 때만 모의 코어가 실행됩니다. 사용자가 지정한 금기와 "
                  "반응 방향을 자동으로 적용하거나 저장하지 않습니다. "
                  "실제 사람 같은 자연스러움/응답 속도/AI 품질 판정은 별도입니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._basic_reaction_input = tk.Text(tab, height=7, wrap="word", font=("Malgun Gothic", 10))
        self._basic_reaction_input.pack(fill="x", pady=(0, 8))
        self._basic_reaction_input.insert("1.0", SAMPLE_REACTION_SCRIPT)
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="기본 대화 반응 시험 (수동)",
                   command=self._run_basic_reaction_test).pack(side="left")
        ttk.Button(controls, text="예시 복원",
                   command=self._reset_basic_reaction_test).pack(side="left", padx=(8, 0))
        self._basic_reaction_status = tk.StringVar(value="미실행 · 오프라인 모의 시험만 가능")
        ttk.Label(tab, textvariable=self._basic_reaction_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._basic_reaction_result = tk.Text(tab, height=12, state="disabled", wrap="word")
        self._basic_reaction_result.pack(fill="both", expand=True)
        self._set_basic_reaction_result("시험 전입니다. 사용자 요청 없이 기록·PC·모델에 접근하지 않습니다.")

    def _set_basic_reaction_result(self, message: str) -> None:
        self._basic_reaction_result.configure(state="normal")
        self._basic_reaction_result.delete("1.0", "end")
        self._basic_reaction_result.insert("1.0", message)
        self._basic_reaction_result.configure(state="disabled")

    def _reset_basic_reaction_test(self) -> None:
        self._basic_reaction_input.delete("1.0", "end")
        self._basic_reaction_input.insert("1.0", SAMPLE_REACTION_SCRIPT)
        self._basic_reaction_status.set("예시만 복원 · 실행/저장 없음")

    def _run_basic_reaction_test(self) -> None:
        try:
            report = run_basic_reaction_test(self._core_selection(),
                 self._basic_reaction_input.get("1.0", "end-1c"))
            self._basic_reaction_status.set(
                f"모의 대화 {'통과' if report.passed else '실패'} {report.passed_count}/{report.total}건 "
                "· 실제 AI 품질 미검증")
            self._set_basic_reaction_result(report.describe())
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._basic_reaction_status.set("입력·설정 검사 실패 · 기존 자료 유지")
            self._set_basic_reaction_result("실행 전 검증 실패: " + str(exc))

    def _build_response_speed_test(self, tab) -> None:
        """36단계 모의 응답 처리 시간 관찰. 사용자 버튼 동작만 허용."""
        ttk.Label(tab, text="원본 36단계 · 응답 속도 관찰 (모의 코어만)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="최대 30건의 채팅을 한 번씩 순서대로 처리하며 채팅별 처리 시간·중앙값·"
                  "P95를 관찰합니다. 속도에 인위적인 지연을 추가하거나 자동 합격 기준을 만들지 않습니다. "
                  "실제 AI 응답 품질/Windows 성능/자연스러움을 평가하지 않으며, 저장·PC 정보 조회·방송은 하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._speed_input = tk.Text(tab, height=7, wrap="word", font=("Malgun Gothic", 10))
        self._speed_input.pack(fill="x", pady=(0, 8))
        self._speed_input.insert("1.0", SAMPLE_SPEED_SCRIPT)
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="모의 응답 시간 측정 (수동)",
                   command=self._run_response_speed_test).pack(side="left")
        ttk.Button(controls, text="예시 복원", command=self._reset_response_speed_test).pack(side="left", padx=(8, 0))
        self._speed_status = tk.StringVar(value="미실행 · 실제 AI 속도 미측정")
        ttk.Label(tab, textvariable=self._speed_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._speed_result = tk.Text(tab, height=12, state="disabled", wrap="word")
        self._speed_result.pack(fill="both", expand=True)
        self._set_speed_result("측정 전입니다. 파일·네트워크·사용자 PC 정보를 조회하지 않습니다.")

    def _set_speed_result(self, message: str) -> None:
        self._speed_result.configure(state="normal")
        self._speed_result.delete("1.0", "end")
        self._speed_result.insert("1.0", message)
        self._speed_result.configure(state="disabled")

    def _reset_response_speed_test(self) -> None:
        self._speed_input.delete("1.0", "end")
        self._speed_input.insert("1.0", SAMPLE_SPEED_SCRIPT)
        self._speed_status.set("예시만 복원 · 측정/저장 없음")

    def _run_response_speed_test(self) -> None:
        try:
            report = run_response_speed_test(self._core_selection(),
                self._speed_input.get("1.0", "end-1c"))
            self._speed_status.set(
                f"모의 시간 관찰 {'완료' if report.completed else '중단'} "
                f"{len(report.turns)}/{report.total}건 · 자연스러움 미판정")
            self._set_speed_result(report.describe())
        except (KeyError, ValueError, TypeError, OverflowError) as exc:
            self._speed_status.set("입력·설정 검증 실패 · 기존 자료 유지")
            self._set_speed_result("실행 전 검사 실패: " + str(exc))

    def _build_all_chat_policy(self, tab) -> None:
        """37단계: 실시간 연결 없는 수동 모의 대기열의 전건 반응 원칙."""
        ttk.Label(tab, text="원본 37단계 · 전체 채팅 반응 원칙 (오프라인 모의)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="채팅을 하나씩 또는 최대 50건씩 직접 처리합니다. 같은 내용도 건별 번호를 부여하며 "
                  "선별·인위적 지연·자동 재시도는 없습니다. 오류가 나면 실패 건부터 대기하고 수동 재시도만 허용합니다. "
                  "기존 설정과 데이터는 변경하지 않으며 실제 채팅이나 방송에는 연결하지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._all_chat_session = None
        self._all_chat_input = tk.Text(tab, height=6, wrap="word", font=("Malgun Gothic", 10))
        self._all_chat_input.pack(fill="x")
        self._all_chat_input.insert("1.0", SAMPLE_REACTION_SCRIPT)
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=8)
        for caption, fn in (("채팅 접수", self._all_chat_append),
                            ("다음 1건", self._all_chat_next),
                            ("최대 50건", self._all_chat_batch),
                            ("실패 건 수동 재시도", self._all_chat_retry),
                            ("세션 초기화", self._all_chat_reset)):
            ttk.Button(controls, text=caption, command=fn).pack(side="left", padx=(0, 5))
        self._all_chat_status = tk.StringVar(value="미시작 · 접수 버튼을 눌러야 모의 세션 생성")
        ttk.Label(tab, textvariable=self._all_chat_status, wraplength=710).pack(anchor="w")
        self._all_chat_result = tk.Text(tab, height=13, state="disabled", wrap="word")
        self._all_chat_result.pack(fill="both", expand=True)

    def _all_chat_show(self, report) -> None:
        self._all_chat_status.set(
            f"모의 채팅 접수 {report.accepted}건 · 응답 {len(report.replied)}건 · "
            f"대기 {len(report.pending)}건 · {'오류로 중단' if report.failed_sequence else '전건 응답' if report.all_responded else '처리 대기'}")
        self._all_chat_result.configure(state="normal")
        self._all_chat_result.delete("1.0", "end")
        self._all_chat_result.insert("1.0", report.describe())
        self._all_chat_result.configure(state="disabled")

    def _all_chat_append(self) -> None:
        try:
            if self._all_chat_session is None:
                candidate = AllChatPolicySession(self._core_selection())
                candidate.append(self._all_chat_input.get("1.0", "end-1c"))
                self._all_chat_session = candidate
            else:
                self._all_chat_session.append(self._all_chat_input.get("1.0", "end-1c"))
            self._all_chat_show(self._all_chat_session.audit())
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self._all_chat_status.set("채팅 접수 실패 · 기존 접수/응답 유지: " + str(exc))

    def _all_chat_next(self) -> None:
        if self._all_chat_session is not None:
            self._all_chat_show(self._all_chat_session.run_next())
        else:
            self._all_chat_status.set("먼저 채팅 접수 버튼을 누르세요")

    def _all_chat_batch(self) -> None:
        if self._all_chat_session is not None:
            self._all_chat_show(self._all_chat_session.run_batch())
        else:
            self._all_chat_status.set("먼저 채팅 접수 버튼을 누르세요")

    def _all_chat_retry(self) -> None:
        if self._all_chat_session is None:
            self._all_chat_status.set("수동 재시도할 세션 없음")
            return
        try:
            self._all_chat_show(self._all_chat_session.run_next(manual_retry=True))
        except ValueError as exc:
            self._all_chat_status.set("수동 재시도 불가: " + str(exc))

    def _all_chat_reset(self) -> None:
        if self._all_chat_session is None:
            self._all_chat_status.set("초기화할 모의 세션 없음")
            return
        if not messagebox.askyesno("모의 세션 초기화", "현재 메모리의 접수·응답 기록을 초기화할까요? (기존 저장 자료에는 영향 없음)"):
            self._all_chat_status.set("초기화 취소 · 모의 대기열 유지")
            return
        self._all_chat_session = None
        self._all_chat_status.set("모의 세션 초기화 완료 · 파일/설정 변경 없음")
        self._all_chat_result.configure(state="normal")
        self._all_chat_result.delete("1.0", "end")
        self._all_chat_result.configure(state="disabled")

    def _build_idle_speech(self, tab) -> None:
        """원본 038: 채팅 우선 순위가 있는 수동 가상 시계 기반 발화 모의."""
        ttk.Label(tab, text="원본 38단계 · 무채팅 자발 발화 모의",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="기본 비활성. 운영자가 무채팅 기준·발화 예시를 직접 정하고, "
                  "가상 시간을 수동으로 진행합니다. 채팅이 1건이라도 대기하면 발화하지 않습니다. "
                  "이 화면은 실제 AI/음성/방송/타이머에 연결하지 않습니다.",
                  wraplength=715).pack(anchor="w", pady=(0, 8))
        self._idle_session = None
        self._idle_enabled = tk.BooleanVar(value=False)
        self._idle_threshold = tk.StringVar(value="10")
        self._idle_utterance = tk.StringVar(value="오늘은 어떤 이야기를 나눠볼까요?")
        self._idle_advance_seconds = tk.StringVar(value="10")
        ttk.Checkbutton(tab, text="모의 자발 발화 허용 (사용자가 직접 켬)",
                        variable=self._idle_enabled).pack(anchor="w")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="무채팅 기준(초)").pack(side="left")
        ttk.Entry(row, textvariable=self._idle_threshold, width=8).pack(side="left", padx=5)
        ttk.Label(row, text="수동 시간 이동(초)").pack(side="left", padx=(12, 0))
        ttk.Entry(row, textvariable=self._idle_advance_seconds, width=8).pack(side="left", padx=5)
        ttk.Label(tab, text="발화 예시 문구 (운영자 수정, 실제 AI 생성 아님)").pack(anchor="w")
        ttk.Entry(tab, textvariable=self._idle_utterance).pack(fill="x")
        ttk.Label(tab, text="채팅 대본 (발신자: 메시지, 중복 보존)").pack(anchor="w", pady=(8, 0))
        self._idle_chat_input = tk.Text(tab, height=3, wrap="word")
        self._idle_chat_input.pack(fill="x")
        self._idle_chat_input.insert("1.0", "시청자: 안녕\n시청자: ㅋㅋㅋ")
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=5)
        for label, fn in (("모의 규칙 적용", self._idle_configure),
                          ("채팅 접수", self._idle_receive),
                          ("대기 채팅 처리", self._idle_process),
                          ("실패 건 수동 재시도", self._idle_retry),
                          ("가상 시간 이동", self._idle_advance),
                          ("발화 후보 확인", self._idle_preview),
                          ("초기화", self._idle_reset)):
            ttk.Button(bar, text=label, command=fn).pack(side="left", padx=(0, 4))
        self._idle_status = tk.StringVar(value="미시작 · 기본 비활성 · 저장/방송 없음")
        ttk.Label(tab, textvariable=self._idle_status, wraplength=715).pack(anchor="w")
        self._idle_result = tk.Text(tab, height=12, state="disabled", wrap="word")
        self._idle_result.pack(fill="both", expand=True)

    def _idle_show(self, result) -> None:
        self._idle_status.set(result.reason)
        self._idle_result.configure(state="normal")
        self._idle_result.delete("1.0", "end")
        self._idle_result.insert("1.0", result.describe())
        self._idle_result.configure(state="disabled")

    def _idle_get_session(self):
        if self._idle_session is None:
            self._idle_session = IdleSpeechSession(self._core_selection())
        return self._idle_session

    def _idle_configure(self) -> None:
        try:
            seconds = int(self._idle_threshold.get())
            session = self._idle_get_session()
            self._idle_show(session.configure(enabled=self._idle_enabled.get(),
                                             threshold_seconds=seconds,
                                             utterance=self._idle_utterance.get()))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self._idle_status.set("모의 규칙 설정 실패 · 이전 상태 유지: " + str(exc))

    def _idle_receive(self) -> None:
        try:
            self._idle_show(self._idle_get_session().receive_chat(
                self._idle_chat_input.get("1.0", "end-1c")))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self._idle_status.set("채팅 접수 실패 · 이전 상태 유지: " + str(exc))

    def _idle_process(self) -> None:
        if self._idle_session is None:
            self._idle_status.set("먼저 모의 채팅을 접수하세요")
            return
        self._idle_show(self._idle_session.process_batch())

    def _idle_retry(self) -> None:
        if self._idle_session is None:
            self._idle_status.set("수동 재시도할 모의 세션 없음")
            return
        try:
            self._idle_show(self._idle_session.process_chat(manual_retry=True))
        except ValueError as exc:
            self._idle_status.set("수동 재시도 불가 · 이전 상태 유지: " + str(exc))

    def _idle_advance(self) -> None:
        try:
            self._idle_show(self._idle_get_session().advance(int(self._idle_advance_seconds.get())))
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self._idle_status.set("가상 시간 입력 오류 · 이전 상태 유지: " + str(exc))

    def _idle_preview(self) -> None:
        if self._idle_session is None:
            self._idle_status.set("먼저 모의 규칙을 적용하세요")
            return
        self._idle_show(self._idle_session.preview_if_idle())

    def _idle_reset(self) -> None:
        if not messagebox.askyesno("모의 자발 발화 초기화",
                                  "메모리의 모의 채팅과 발화 후보만 초기화할까요? 저장된 데이터는 변경하지 않습니다."):
            self._idle_status.set("초기화 취소 · 모의 상태 유지")
            return
        self._idle_session = None
        self._idle_enabled.set(False)
        self._idle_status.set("모의 상태 초기화 · 발화 기본 비활성 · 설정 파일 변경 없음")
        self._idle_result.configure(state="normal")
        self._idle_result.delete("1.0", "end")
        self._idle_result.configure(state="disabled")

    def _build_operator_feedback(self, tab) -> None:
        """Original 039: record operator requests without changing a live character."""
        ttk.Label(tab, text="원본 39단계 · 운영자 피드백 수정 준비", font=("Malgun Gothic", 13, "bold")).pack(anchor="w")
        ttk.Label(tab, text="문제 상황과 수정 지시를 운영자가 직접 작성합니다. 미리보기는 저장하지 않습니다. "
                  "기록·수정·삭제는 별도 확인 후 전용 로컬 JSON만 변경합니다. "
                  "캐릭터 설정·기억·AI 답변·방송에는 자동 적용되지 않습니다.",
                  wraplength=720).pack(anchor="w", pady=(4, 6))
        form = ttk.Frame(tab)
        form.pack(fill="x")
        ttk.Label(form, text="분류").grid(row=0, column=0, sticky="w")
        self._feedback_category = tk.StringVar(value=FEEDBACK_CATEGORIES[0])
        ttk.Combobox(form, textvariable=self._feedback_category, values=FEEDBACK_CATEGORIES,
                     state="readonly", width=19).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="기존 기록 순번 (수정·삭제할 때만)").grid(row=0, column=2, sticky="w", padx=(12, 4))
        self._feedback_sequence = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self._feedback_sequence, width=8).grid(row=0, column=3, sticky="w")
        ttk.Label(tab, text="운영자가 관찰한 문제 (500자 이하)").pack(anchor="w", pady=(4, 0))
        self._feedback_observation = tk.Text(tab, height=3, wrap="word")
        self._feedback_observation.pack(fill="x")
        ttk.Label(tab, text="운영자가 원하는 수정 방향 (500자 이하)").pack(anchor="w", pady=(5, 0))
        self._feedback_request = tk.Text(tab, height=3, wrap="word")
        self._feedback_request.pack(fill="x")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=7)
        ttk.Button(actions, text="수정 요청 미리보기", command=self._feedback_preview).pack(side="left")
        ttk.Button(actions, text="확인 후 추가", command=self._feedback_add).pack(side="left", padx=3)
        ttk.Button(actions, text="선택 순번 수정", command=self._feedback_revise).pack(side="left", padx=3)
        ttk.Button(actions, text="수동 목록 읽기", command=self._feedback_list).pack(side="left", padx=3)
        ttk.Button(actions, text="선택 순번 삭제", command=self._feedback_delete).pack(side="left", padx=3)
        self._feedback_status = tk.StringVar(value="미실행 · 기존 기록 자동 읽기 없음 · 실제 반영 없음")
        ttk.Label(tab, textvariable=self._feedback_status, wraplength=720).pack(anchor="w")
        self._feedback_result = tk.Text(tab, height=10, wrap="word", state="disabled")
        self._feedback_result.pack(fill="both", expand=True)

    def _feedback_show(self, status: str, result: str) -> None:
        self._feedback_status.set(status)
        self._feedback_result.configure(state="normal")
        self._feedback_result.delete("1.0", "end")
        self._feedback_result.insert("1.0", result)
        self._feedback_result.configure(state="disabled")

    def _feedback_draft(self):
        return draft_feedback(self._feedback_category.get(),
                              self._feedback_observation.get("1.0", "end-1c"),
                              self._feedback_request.get("1.0", "end-1c"))

    def _feedback_selected_sequence(self) -> int:
        raw = self._feedback_sequence.get().strip()
        if not raw.isdecimal() or int(raw) <= 0:
            raise ValueError("기록 순번에는 양의 정수를 입력해야 합니다.")
        return int(raw)

    def _feedback_preview(self) -> None:
        try:
            self._feedback_show("입력 검증 통과 · 미저장 · 미적용", self._feedback_draft().describe())
        except (ValueError, TypeError) as exc:
            self._feedback_show("입력 검증 실패", str(exc))

    def _feedback_add(self) -> None:
        try:
            draft = self._feedback_draft()
            if not messagebox.askyesno("피드백 추가 확인", "운영자가 입력한 수정 요청을 별도 로컬 기록에 추가할까요?\n실제 캐릭터에는 적용하지 않습니다.", parent=self):
                self._feedback_status.set("저장 취소 · 이전 기록 유지")
                return
            record = add_feedback(feedback_path(), draft, operator_confirmed=True)
            self._feedback_show("피드백 저장 완료 · AI 적용 없음", record.describe())
        except (ValueError, OSError) as exc:
            self._feedback_show("추가 실패 · 기존 설정 유지", str(exc))

    def _feedback_revise(self) -> None:
        try:
            sequence, draft = self._feedback_selected_sequence(), self._feedback_draft()
            if not messagebox.askyesno("수정 요청 변경 확인", f"기록 #{sequence}의 요청 내용만 바꿀까요?\n캐릭터는 변경하지 않습니다.", parent=self):
                self._feedback_status.set("변경 취소 · 기존 기록 유지")
                return
            record = revise_feedback(feedback_path(), sequence, draft, operator_confirmed=True)
            self._feedback_show("요청 기록 변경 완료 · AI 적용 없음", record.describe())
        except (ValueError, OSError) as exc:
            self._feedback_show("변경 실패 · 기존 기록 유지", str(exc))

    def _feedback_list(self) -> None:
        try:
            records = list_feedback(feedback_path())
            text = "\n\n".join(item.describe() for item in records) if records else "저장된 수정 요청이 없습니다."
            self._feedback_show(f"수동 조회 완료 · {len(records)}건 · 반영 대기", text)
        except (ValueError, OSError) as exc:
            self._feedback_show("수동 조회 실패", str(exc))

    def _feedback_delete(self) -> None:
        try:
            sequence = self._feedback_selected_sequence()
            if not messagebox.askyesno("삭제 확인 1/2", f"피드백 #{sequence} 기록을 삭제할까요?", parent=self):
                self._feedback_status.set("삭제 취소 · 기존 기록 유지")
                return
            if not messagebox.askyesno("삭제 확인 2/2", "삭제 후에는 복구되지 않습니다. 계속할까요?", parent=self):
                self._feedback_status.set("삭제 취소 · 기존 기록 유지")
                return
            removed = delete_feedback(feedback_path(), sequence, operator_confirmed=True)
            self._feedback_show("요청 기록 삭제 완료" if removed else "해당 기록 없음",
                                "캐릭터 설정·SQLite 기억과 실제 AI 동작은 변경하지 않았습니다.")
        except (ValueError, OSError) as exc:
            self._feedback_show("삭제 실패 · 기존 기록 유지", str(exc))

    def _build_character_dialogue_review(self, tab) -> None:
        """Original roadmap 040: structural mock + explicitly operator-marked turns."""
        ttk.Label(tab, text="원본 40단계 · 캐릭터 대화 1차 검증 (모의, 수동)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w")
        ttk.Label(tab, text="현재 화면의 캐릭터·취향·반응 방향·금기 입력만 미리봅니다. "
                  "채팅은 별도 메모리 모의 코어로 처리하며 지침을 실제 답변 생성에 적용하지 않습니다. "
                  "자연스러움 평가는 운영자만 표시할 수 있고 기록은 저장되지 않습니다.",
                  wraplength=720).pack(anchor="w", pady=5)
        self._character_dialogue_script = tk.Text(tab, height=6, wrap="word")
        self._character_dialogue_script.pack(fill="x")
        self._character_dialogue_script.insert("1.0", SAMPLE_CHARACTER_SCRIPT)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=5)
        ttk.Button(actions, text="모의 대화 구조 검사 (수동)",
                   command=self._run_character_dialogue_review).pack(side="left")
        ttk.Button(actions, text="예시 복원·평가 초기화",
                   command=self._reset_character_dialogue_review).pack(side="left", padx=5)
        self._character_dialogue_status = tk.StringVar(value="미실행 · 모의 답변·운영자 평가 없음")
        ttk.Label(tab, textvariable=self._character_dialogue_status, wraplength=720).pack(anchor="w")
        ratings = ttk.Frame(tab)
        ratings.pack(fill="x", pady=5)
        ttk.Label(ratings, text="순번").pack(side="left")
        self._character_dialogue_index = tk.StringVar(value="1")
        ttk.Entry(ratings, textvariable=self._character_dialogue_index, width=5).pack(side="left", padx=4)
        ttk.Label(ratings, text="운영자 평가").pack(side="left")
        self._character_dialogue_verdict = tk.StringVar(value=VERDICTS[0])
        ttk.Combobox(ratings, textvariable=self._character_dialogue_verdict,
                     state="readonly", values=VERDICTS, width=16).pack(side="left", padx=4)
        ttk.Label(ratings, text="메모 (500자 이하)").pack(side="left")
        self._character_dialogue_note = ttk.Entry(ratings, width=18)
        self._character_dialogue_note.pack(side="left", padx=4)
        ttk.Button(ratings, text="이 순번 평가 표시", command=self._mark_character_dialogue).pack(side="left")
        self._character_dialogue_result = tk.Text(tab, height=14, wrap="word", state="disabled")
        self._character_dialogue_result.pack(fill="both", expand=True)
        self._character_dialogue_report = None
        self._character_dialogue_snapshot = None
        self._character_dialogue_ratings = []
        self._character_dialogue_notes = []

    def _character_dialogue_inputs(self):
        """Pure GUI snapshot: changing any field invalidates prior manual ratings."""
        import copy
        selected = self._core_selection()
        draft = {key: field.get() for key, field in self._persona.items()}
        directions = {key: field.get() for key, field in self._reaction_inputs.items()}
        boundaries = self._boundary_lines()
        args = (self._character_dialogue_script.get("1.0", "end-1c"),
                self._preference_likes.get(), self._preference_dislikes.get(),
                directions, boundaries)
        return copy.deepcopy(selected), args

    def _character_dialogue_show(self, status, text):
        self._character_dialogue_status.set(status)
        self._character_dialogue_result.configure(state="normal")
        self._character_dialogue_result.delete("1.0", "end")
        self._character_dialogue_result.insert("1.0", text)
        self._character_dialogue_result.configure(state="disabled")

    def _run_character_dialogue_review(self) -> None:
        self._character_dialogue_report = None
        self._character_dialogue_snapshot = None
        self._character_dialogue_ratings = []
        self._character_dialogue_notes = []
        try:
            selected, args = self._character_dialogue_inputs()
            script, likes, dislikes, directions, boundaries = args
            report = review_character_dialogue(selected, script, likes=likes,
                   dislikes=dislikes, directions=directions, boundaries=boundaries)
            self._character_dialogue_report = report
            self._character_dialogue_snapshot = (selected, args)
            self._character_dialogue_ratings = [VERDICTS[0]] * report.mock.total
            self._character_dialogue_notes = [''] * report.mock.total
            self._character_dialogue_index.set('1')
            self._character_dialogue_show(
                f"모의 구조 {'통과' if report.structure_passed else '실패'} "
                f"{report.mock.passed_count}/{report.mock.total} · 운영자 평가 대기 · 저장 없음",
                report.describe())
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self._character_dialogue_show("입력·설정 검사 실패 · 평가 초기화", str(exc))

    def _mark_character_dialogue(self) -> None:
        try:
            report = self._character_dialogue_report
            if report is None:
                raise ValueError('먼저 모의 대화 검사를 실행하세요.')
            if self._character_dialogue_snapshot != self._character_dialogue_inputs():
                self._character_dialogue_report = None
                self._character_dialogue_snapshot = None
                self._character_dialogue_ratings = []
                self._character_dialogue_notes = []
                raise ValueError('캐릭터·지침·대본이 바뀌었습니다. 검사를 다시 실행하세요.')
            raw = self._character_dialogue_index.get().strip()
            if not raw.isdecimal() or not 1 <= int(raw) <= report.mock.total:
                raise ValueError('대화 순번이 올바르지 않습니다.')
            index = int(raw) - 1
            verdicts = list(self._character_dialogue_ratings)
            notes = list(self._character_dialogue_notes)
            verdicts[index] = self._character_dialogue_verdict.get()
            notes[index] = self._character_dialogue_note.get()
            assessment = assess_character_dialogue(report, verdicts, notes)
            self._character_dialogue_ratings = verdicts
            self._character_dialogue_notes = notes
            self._character_dialogue_show('운영자 수동 평가 표시 · 로컬 파일 저장 없음 · AI 동작 변경 없음',
                                          report.describe() + '\n\n=== 운영자 판정 ===\n' + assessment.describe())
        except (ValueError, TypeError, KeyError) as exc:
            self._character_dialogue_status.set('운영자 평가 거부 · ' + str(exc))

    def _reset_character_dialogue_review(self) -> None:
        self._character_dialogue_script.delete('1.0', 'end')
        self._character_dialogue_script.insert('1.0', SAMPLE_CHARACTER_SCRIPT)
        self._character_dialogue_report = None
        self._character_dialogue_snapshot = None
        self._character_dialogue_ratings = []
        self._character_dialogue_notes = []
        self._character_dialogue_index.set('1')
        self._character_dialogue_verdict.set(VERDICTS[0])
        self._character_dialogue_note.delete(0, 'end')
        self._character_dialogue_show('예시 복원 · 평가 초기화 · 저장 없음',
                                      '수동 시험 전 · 이전 평가를 보존하거나 승인 처리하지 않았습니다.')

    def _build_avatar_display_validation(self, tab) -> None:
        ttk.Label(tab, text="53단계 · 캐릭터 화면 표시 검증", font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=5)
        ttk.Label(tab, text="이미 구현된 Tk 2D 본 창·별도 창 또는 3D 미지원 안내를 검사합니다.\n"
                  "외부 모델·화면 캡처·장치 확인·방송을 실행하지 않으며, 실제 시인성은 운영자 검토가 필요합니다.",
                  wraplength=710, justify="left").pack(anchor="w", pady=7)
        ttk.Button(tab, text="현재 캐릭터 화면 검사", command=self._avatar_display_check).pack(anchor="w", pady=7)
        self._avatar_display_status = tk.StringVar(value="미검사 · 사용자 버튼을 누르면 현재 캔버스 상태만 확인")
        ttk.Label(tab, textvariable=self._avatar_display_status, wraplength=720).pack(anchor="w", pady=5)
        self._avatar_display_result = tk.Text(tab, height=18, wrap="word", state="disabled")
        self._avatar_display_result.pack(fill="both", expand=True)

    def _avatar_display_check(self) -> None:
        try:
            # No new window, filesystem inspection or external application launch.
            self._draw_avatar_canvases()
            try:
                name = self._current_persona()["name"]
            except ValueError:
                name = DEFAULTS["persona"]["name"]
            capture = self._avatar_capture_canvas
            if capture is not None and not capture.winfo_exists():
                capture = None
            report = audit_avatar_display(
                avatar=AVATARS[self._avatar.get()], name=name,
                speaking=bool(self._avatar_demo.get() or self._speaker.speaking),
                frame=self._avatar_frame, main_canvas=self._canvas,
                capture_canvas=capture,
                capture_background=self._avatar_capture_background.get(),
            )
            self._avatar_display_status.set("구조 검사 통과 · 실제 모델 미검증" if report.passed
                                            else "화면 표시 불일치 · 수정 필요")
            details = report.describe()
        except (ValueError, KeyError, tk.TclError) as exc:
            self._avatar_display_status.set("화면 표시 검사 실패")
            details = str(exc)
        self._avatar_display_result.configure(state="normal")
        self._avatar_display_result.delete("1.0", "end")
        self._avatar_display_result.insert("1.0", details)
        self._avatar_display_result.configure(state="disabled")

    def _build_avatar_voice_mouth(self, tab) -> None:
        """Original 055: manual mock voice segments drive a silent sample mouth canvas."""
        ttk.Label(tab, text='원본 55단계 · 가상 음성→내장 2D 입 움직임 (무음)',
                  font=('Malgun Gothic', 12, 'bold')).pack(anchor='w', pady=(0, 6))
        ttk.Label(tab, text='실제 마이크·스피커·음성/OS 조회 없음. 운영자 클릭으로 채팅을 1건씩 가상 전달하고, '
                  '생성된 입 프레임은 별도 버튼으로 한 장씩 확인합니다. 음소·파형 기반 동기화 아님.',
                  wraplength=730).pack(anchor='w')
        self._mouth_script = tk.Text(tab, height=3, wrap='word')
        self._mouth_script.pack(fill='x', pady=6)
        self._mouth_script.insert('1.0', '시청자: 안녕하세요!\n시청자: 안녕하세요!\n다른분: 오늘은 어때요?')
        self._mouth_script.bind('<<Modified>>', self._mouth_script_modified)
        self._mouth_script.edit_modified(False)
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text='가상 음성 식별자').pack(side='left')
        self._mouth_voice = tk.StringVar(value='모의 한국어 음성')
        ttk.Entry(row, textvariable=self._mouth_voice, width=19).pack(side='left', padx=8)
        self._mouth_fail_second = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text='두 번째 채팅 첫 전달 1회 중단',
                        variable=self._mouth_fail_second).pack(side='left')
        row2 = ttk.Frame(tab)
        row2.pack(fill='x', pady=4)
        ttk.Button(row2, text='무음 시험 시작/초기화', command=self._mouth_start).pack(side='left')
        ttk.Button(row2, text='채팅 1건 가상 전달/수동 재개', command=self._mouth_step).pack(side='left', padx=5)
        ttk.Button(row2, text='다음 입 프레임 보기', command=self._mouth_next_frame).pack(side='left')
        self._mouth_canvas = tk.Canvas(tab, height=265, width=370, highlightthickness=0)
        self._mouth_canvas.pack(anchor='w', pady=6)
        self._mouth_status = tk.StringVar(value='미실행 · 2D 선택 시 수동 검증 가능')
        ttk.Label(tab, textvariable=self._mouth_status, wraplength=740).pack(anchor='w')
        self._mouth_log = tk.Text(tab, height=7, wrap='word', state='disabled')
        self._mouth_log.pack(fill='both', expand=True)
        self._mouth_session = None
        self._mouth_cursor = 0
        self._mouth_draw_idle()
        for var in (self._avatar, self._avatar_expression, self._voice,
                    self._voice_rate, self._voice_volume, self._mouth_voice,
                    self._mouth_fail_second):
            var.trace_add('write', self._mouth_invalidate)

    def _mouth_script_modified(self, *_args) -> None:
        if self._mouth_script.edit_modified():
            self._mouth_script.edit_modified(False)
            self._mouth_invalidate()

    def _mouth_invalidate(self, *_args) -> None:
        self._mouth_session = None
        self._mouth_cursor = 0
        self._mouth_status.set('대본·음성·아바타·표정 변경 · 이전 모의 검증 무효')
        self._mouth_draw_idle()
        self._mouth_show('')

    def _mouth_show(self, text: str) -> None:
        self._mouth_log.configure(state='normal')
        self._mouth_log.delete('1.0', 'end')
        self._mouth_log.insert('1.0', text)
        self._mouth_log.configure(state='disabled')

    def _mouth_draw_idle(self) -> None:
        if AVATARS[self._avatar.get()] != '2d':
            if AVATARS[self._avatar.get()] == '3d':
                draw_unavailable_3d(self._mouth_canvas)
            else:
                self._mouth_canvas.delete('all')
                self._mouth_canvas.create_text(185, 120, text='아바타 미정 · 2D 선택 후 시험',
                                               tags=('aisting_avatar_undecided',))
            return
        try:
            name = self._current_persona()['name']
        except (AttributeError, KeyError, ValueError):
            name = DEFAULTS['persona']['name']
        draw_avatar(self._mouth_canvas, AvatarFrame(
            name, False, 4, expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()]))

    def _mouth_start(self) -> None:
        self._mouth_session = None
        self._mouth_cursor = 0
        self._mouth_draw_idle()
        try:
            name = self._current_persona()['name']
            self._mouth_session = VoiceMouthRehearsal(
                self._mouth_script.get('1.0', 'end-1c'),
                avatar=AVATARS[self._avatar.get()], name=name,
                expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()],
                voice_source=VOICES[self._voice.get()], voice_name=self._mouth_voice.get(),
                rate=int(self._voice_rate.get()), volume=int(self._voice_volume.get()),
                fail_second_once=self._mouth_fail_second.get())
            self._mouth_status.set('가상 시험 준비 · 실제 음성/방송 없음')
            self._mouth_show(self._mouth_session.describe())
        except (ValueError, TypeError, KeyError) as exc:
            self._mouth_status.set('가상 시험 준비 불가 · 사용자 선택 확인 필요')
            self._mouth_show(str(exc))

    def _mouth_step(self) -> None:
        if self._mouth_session is None:
            self._mouth_status.set('무음 시험 시작/초기화를 먼저 실행하세요.')
            return
        status = self._mouth_session.step()
        self._mouth_status.set(f'가상 처리 {status.state} · 완료 {len(status.completed)}건 · '
                               f'대기 {len(status.pending)}건 · 프레임 {len(self._mouth_session.cues)}개')
        self._mouth_show(self._mouth_session.describe())

    def _mouth_next_frame(self) -> None:
        if self._mouth_session is None:
            self._mouth_status.set('무음 시험 시작/초기화를 먼저 실행하세요.')
            return
        if self._mouth_cursor >= len(self._mouth_session.cues):
            self._mouth_draw_idle()
            self._mouth_status.set('표시할 새 입 프레임 없음 · 무음 / 실제 재생 없음')
            return
        cue = self._mouth_session.cues[self._mouth_cursor]
        self._mouth_cursor += 1
        draw_avatar(self._mouth_canvas, cue.frame)
        self._mouth_status.set(f'가상 채팅 {cue.chat_number}, 구간 {cue.segment_index} · '
                               f'입 프레임 {self._mouth_cursor}/{len(self._mouth_session.cues)} · 무음')

    def _build_avatar_voice_sync(self, tab) -> None:
        """Original 056: manual synthetic audio windows, never speaker output."""
        ttk.Label(tab, text='56단계 · 가상 음성/입 움직임 시간 정렬 (무음)',
                  font=('Malgun Gothic', 12, 'bold')).pack(anchor='w', pady=6)
        ttk.Label(tab, text='문자 수로 만든 가상 음성 시간표입니다. 실제 TTS 재생·파형·음소 동기화 및 장치 조회 없음. '
                  '사용자 버튼으로 채팅을 1건씩 가상 전달하고, 시각을 수동 이동해 확인하세요.',
                  wraplength=735).pack(anchor='w')
        self._sync_script = tk.Text(tab, height=3, wrap='word')
        self._sync_script.pack(fill='x', pady=5)
        self._sync_script.insert('1.0', '시청자: 안녕하세요!\n시청자: 안녕하세요!\n다른분: 오늘은 어때요?')
        self._sync_script.bind('<<Modified>>', self._sync_script_modified)
        self._sync_script.edit_modified(False)
        opts = ttk.Frame(tab); opts.pack(fill='x', pady=4)
        ttk.Label(opts, text='가상 음성 식별자').pack(side='left')
        self._sync_voice = tk.StringVar(value='모의 한국어 음성')
        ttk.Entry(opts, textvariable=self._sync_voice, width=18).pack(side='left', padx=5)
        ttk.Label(opts, text='문자당 가상 ms').pack(side='left')
        self._sync_char_ms = tk.StringVar(value='80')
        ttk.Entry(opts, textvariable=self._sync_char_ms, width=5).pack(side='left', padx=5)
        self._sync_fail_second = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text='두 번째 채팅 1회 중단', variable=self._sync_fail_second).pack(side='left')
        actions = ttk.Frame(tab); actions.pack(fill='x', pady=4)
        ttk.Button(actions, text='무음 시간표 초기화', command=self._sync_start).pack(side='left')
        ttk.Button(actions, text='채팅 1건 전달/수동 재개', command=self._sync_step).pack(side='left', padx=3)
        ttk.Button(actions, text='가상 시간 +100ms', command=self._sync_advance).pack(side='left', padx=3)
        ttk.Button(actions, text='0ms 되감기', command=lambda: self._sync_seek(0)).pack(side='left', padx=3)
        self._sync_clock = tk.StringVar(value='0')
        manual = ttk.Frame(tab); manual.pack(fill='x', pady=4)
        ttk.Label(manual, text='이동할 가상 시각(ms)').pack(side='left')
        ttk.Entry(manual, textvariable=self._sync_clock, width=9).pack(side='left', padx=5)
        ttk.Button(manual, text='가상 시각 보기', command=self._sync_seek_entry).pack(side='left')
        self._sync_canvas = tk.Canvas(tab, height=260, width=370, highlightthickness=0)
        self._sync_canvas.pack(anchor='w', pady=4)
        self._sync_status = tk.StringVar(value='미시험 · 2D 모의 시간표는 사용자 클릭으로만 생성')
        ttk.Label(tab, textvariable=self._sync_status, wraplength=735).pack(anchor='w', pady=3)
        self._sync_log = tk.Text(tab, height=7, wrap='word', state='disabled')
        self._sync_log.pack(fill='both', expand=True)
        self._sync_session = None
        self._sync_draw_idle()
        for var in (self._avatar, self._avatar_expression, self._voice,
                    self._voice_rate, self._voice_volume, self._sync_voice,
                    self._sync_char_ms, self._sync_fail_second):
            var.trace_add('write', self._sync_invalidate)

    def _sync_script_modified(self, *_args) -> None:
        if self._sync_script.edit_modified():
            self._sync_script.edit_modified(False)
            self._sync_invalidate()

    def _sync_invalidate(self, *_args) -> None:
        self._sync_session = None
        self._sync_clock.set('0')
        self._sync_status.set('시험 대본·목소리·아바타·표정·가상 시간 설정 변경 · 이전 결과 무효')
        self._sync_draw_idle()
        self._sync_show('')

    def _sync_draw_idle(self) -> None:
        if AVATARS[self._avatar.get()] != '2d':
            if AVATARS[self._avatar.get()] == '3d':
                draw_unavailable_3d(self._sync_canvas)
            else:
                self._sync_canvas.delete('all')
                self._sync_canvas.create_text(185, 120, text='아바타 미정 · 내장 2D 선택 후 시험')
            return
        try:
            name = self._current_persona()['name']
        except (AttributeError, KeyError, ValueError):
            name = DEFAULTS['persona']['name']
        draw_avatar(self._sync_canvas, AvatarFrame(
            name, False, 4, expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()]))

    def _sync_show(self, text: str) -> None:
        self._sync_log.configure(state='normal')
        self._sync_log.delete('1.0', 'end')
        self._sync_log.insert('1.0', text)
        self._sync_log.configure(state='disabled')

    def _sync_start(self) -> None:
        self._sync_session = None
        self._sync_clock.set('0')
        self._sync_draw_idle()
        try:
            name = self._current_persona()['name']
            self._sync_session = VirtualVoiceMouthSync(
                self._sync_script.get('1.0', 'end-1c'),
                avatar=AVATARS[self._avatar.get()], name=name,
                expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()],
                voice_source=VOICES[self._voice.get()], voice_name=self._sync_voice.get(),
                rate=int(self._voice_rate.get()), volume=int(self._voice_volume.get()),
                fail_second_once=self._sync_fail_second.get(),
                milliseconds_per_character=int(self._sync_char_ms.get()))
            self._sync_status.set('가상 시간표 준비 · 아직 음성 구간/입 동작 없음')
            self._sync_show(self._sync_session.describe())
        except (ValueError, TypeError, KeyError) as exc:
            self._sync_status.set('가상 동기화 시험 준비 불가 · 사용자 선택 확인 필요')
            self._sync_show(str(exc))

    def _sync_step(self) -> None:
        if self._sync_session is None:
            self._sync_status.set('먼저 무음 시간표 초기화를 실행하세요.')
            return
        result = self._sync_session.step()
        self._sync_status.set(f'가상 전달 {result.state} · 구간 {len(self._sync_session.windows)}개 · '
                              f'남은 채팅 {len(result.pending)}건 · 실제 재생 없음')
        self._sync_show(self._sync_session.describe())

    def _sync_seek_entry(self) -> None:
        try:
            self._sync_seek(int(self._sync_clock.get()))
        except (ValueError, TypeError) as exc:
            self._sync_status.set('유효한 정수 ms를 입력하세요. ' + str(exc))

    def _sync_seek(self, ms: int) -> None:
        if self._sync_session is None:
            self._sync_status.set('먼저 무음 시간표 초기화를 실행하세요.')
            return
        try:
            snapshot = self._sync_session.seek(ms)
        except ValueError as exc:
            self._sync_status.set(str(exc))
            return
        self._sync_clock.set(str(ms))
        draw_avatar(self._sync_canvas, snapshot.frame)
        self._sync_status.set(f'{ms}/{self._sync_session.duration_ms}ms · {snapshot.phase} · '
                              '무음·모의 시각 / 실제 립싱크 아님')

    def _sync_advance(self) -> None:
        if self._sync_session is None:
            self._sync_status.set('먼저 무음 시간표 초기화를 실행하세요.')
            return
        snapshot = self._sync_session.advance(100)
        self._sync_seek(snapshot.clock_ms)

    def _build_avatar_motion_review(self, tab) -> None:
        """Original 057: manual inspection of bundled sample expressions and movement."""
        ttk.Label(tab, text='57단계 · 표정 및 움직임 시험 (내장 2D · 무음)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text='운영자가 고른 표정으로 9개 프레임을 단계별로 미리보고 구조를 검사합니다. '
                  '실제 음성·정밀 립싱크·Live2D/VRM·방송 및 자연스러움 합격 판정은 하지 않습니다.',
                  wraplength=735).pack(anchor='w', pady=4)
        options = ttk.Frame(tab)
        options.pack(fill='x', pady=4)
        ttk.Label(options, text='배경').pack(side='left')
        self._motion_background = tk.StringVar(value='남색 스튜디오')
        ttk.Combobox(options, textvariable=self._motion_background,
                     values=tuple(BACKGROUND_COLORS), state='readonly', width=18).pack(side='left', padx=6)
        ttk.Label(options, text='표정은 「기본 표정 설정」 화면의 선택값을 이용합니다.',
                  wraplength=440).pack(side='left')
        buttons = ttk.Frame(tab)
        buttons.pack(fill='x', pady=5)
        ttk.Button(buttons, text='현재 설정으로 시험 준비', command=self._motion_start).pack(side='left')
        ttk.Button(buttons, text='이전 프레임', command=self._motion_previous).pack(side='left', padx=4)
        ttk.Button(buttons, text='다음 프레임', command=self._motion_next).pack(side='left', padx=4)
        ttk.Button(buttons, text='전체 9단계 구조 검사', command=self._motion_audit).pack(side='left', padx=4)
        self._motion_canvas = tk.Canvas(tab, width=370, height=350, highlightthickness=0)
        self._motion_canvas.pack(anchor='w', pady=4)
        self._motion_status = tk.StringVar(value='미시험 · 사용자 클릭 전 움직임 검사 없음')
        ttk.Label(tab, textvariable=self._motion_status, wraplength=735).pack(anchor='w', pady=3)
        self._motion_log = tk.Text(tab, height=6, wrap='word', state='disabled')
        self._motion_log.pack(fill='both', expand=True)
        self._motion_session = None
        self._motion_draw_idle()
        for var in (self._avatar, self._avatar_expression, self._persona_mode,
                    self._motion_background):
            var.trace_add('write', self._motion_invalidate)
        for entry in self._persona.values():
            entry.bind('<KeyRelease>', self._motion_invalidate, add='+')

    def _motion_output(self, message: str) -> None:
        self._motion_log.configure(state='normal')
        self._motion_log.delete('1.0', 'end')
        self._motion_log.insert('1.0', message)
        self._motion_log.configure(state='disabled')

    def _motion_draw_idle(self) -> None:
        choice = AVATARS.get(self._avatar.get())
        if choice != '2d':
            if choice == '3d':
                draw_unavailable_3d(self._motion_canvas)
            else:
                self._motion_canvas.delete('all')
                self._motion_canvas.create_text(185, 140, text='2D 선택 후 모의 시험 가능')
            return
        try:
            name = self._current_persona()['name']
            expression = AVATAR_EXPRESSIONS[self._avatar_expression.get()]
            pose = AvatarFrame(name, False, 4, background=self._motion_background.get(),
                               expression=expression)
            draw_avatar(self._motion_canvas, pose)
        except (ValueError, KeyError, tk.TclError):
            self._motion_canvas.delete('all')

    def _motion_invalidate(self, *_args) -> None:
        self._motion_session = None
        self._motion_status.set('아바타·캐릭터·표정·배경 설정 변경 · 이전 검사 무효')
        self._motion_draw_idle()
        self._motion_output('')

    def _motion_start(self) -> None:
        self._motion_session = None
        try:
            session = AvatarMotionReview(
                avatar=AVATARS[self._avatar.get()],
                name=self._current_persona()['name'],
                expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()],
                background=self._motion_background.get())
            self._motion_session = session
            self._motion_show_frame()
            self._motion_output('9개 샘플 프레임 · 클릭 전 검사는 실행되지 않았습니다.\n'
                                '실제 움직임 품질과 립싱크는 운영자 검토 대기')
        except (ValueError, KeyError, tk.TclError) as exc:
            self._motion_draw_idle()
            self._motion_status.set('모의 시험 준비 불가 · ' + str(exc))

    def _motion_show_frame(self) -> None:
        if self._motion_session is None:
            self._motion_status.set('먼저 현재 설정으로 시험을 준비하세요.')
            return
        label, pose = self._motion_session.current
        draw_avatar(self._motion_canvas, pose)
        self._motion_status.set(f'프레임 {self._motion_session.index + 1}/'
                                f'{self._motion_session.count} · {label} · '
                                '내장 2D 구조 미리보기 (무음)')

    def _motion_next(self) -> None:
        if self._motion_session is None:
            self._motion_show_frame()
            return
        self._motion_session.next()
        self._motion_show_frame()

    def _motion_previous(self) -> None:
        if self._motion_session is None:
            self._motion_show_frame()
            return
        self._motion_session.previous()
        self._motion_show_frame()

    def _motion_audit(self) -> None:
        if self._motion_session is None:
            self._motion_status.set('먼저 현재 설정으로 시험을 준비하세요.')
            return
        report = self._motion_session.audit(self._motion_canvas)
        self._motion_output(report.describe())
        self._motion_status.set('9개 화면 프레임 구조 검사 ' + ('통과' if report.passed else '실패') +
                                ' · 실제 품질/자연스러움 승인 대기')

    def _build_avatar_layout(self, tab) -> None:
        """058: independently saved, silent 640×360 local layout preview."""
        ttk.Label(tab, text='58단계 · 캐릭터 화면 배치 (내장 2D 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=4)
        ttk.Label(tab, text='가상 16:9 방송 화면에 내장 2D 샘플의 위치·크기만 미리 배치합니다. '
                  '실제 OBS 장면/Live2D/VRM 변경·방송·PC 장치 검색은 하지 않습니다.',
                  wraplength=730).pack(anchor='w', pady=3)
        controls = ttk.Frame(tab)
        controls.pack(fill='x', pady=5)
        self._layout_horizontal = tk.IntVar(value=75)
        self._layout_vertical = tk.IntVar(value=100)
        self._layout_size = tk.IntVar(value=70)
        for title, var, minimum, maximum in (
            ('가로 위치 %', self._layout_horizontal, 0, 100),
            ('세로 위치 %', self._layout_vertical, 0, 100),
            ('크기 %', self._layout_size, 40, 100),
        ):
            frame = ttk.Frame(controls)
            frame.pack(side='left', padx=(0, 13))
            ttk.Label(frame, text=title).pack(anchor='w')
            tk.Scale(frame, from_=minimum, to=maximum, orient='horizontal', length=170,
                     variable=var, resolution=1, showvalue=True).pack()
        back = ttk.Frame(tab)
        back.pack(fill='x', pady=3)
        ttk.Label(back, text='가상 배경').pack(side='left')
        self._layout_background = tk.StringVar(value='남색 스튜디오')
        ttk.Combobox(back, textvariable=self._layout_background,
                     values=tuple(BACKGROUND_COLORS), state='readonly', width=17).pack(side='left', padx=7)
        for title, action in (
            ('미리보기 갱신', self._layout_preview),
            ('기본 위치로', self._layout_reset),
            ('확인 후 저장', self._layout_save),
            ('수동 불러오기', self._layout_load),
            ('2회 확인 삭제', self._layout_delete),
        ):
            ttk.Button(back, text=title, command=action).pack(side='left', padx=3)
        self._layout_canvas = tk.Canvas(tab, width=640, height=360, highlightthickness=1,
                                        highlightbackground='#7f8da5', bg='#17223c')
        self._layout_canvas.pack(anchor='w', pady=5)
        self._layout_status = tk.StringVar(value='저장되지 않은 기본 배치 · 실제 방송 화면 미연결')
        ttk.Label(tab, textvariable=self._layout_status, wraplength=735).pack(anchor='w', pady=3)
        self._layout_snapshot = None
        for var in (self._layout_horizontal, self._layout_vertical, self._layout_size,
                    self._layout_background, self._avatar, self._avatar_expression,
                    self._persona_mode):
            var.trace_add('write', self._layout_invalidate)
        for entry in self._persona.values():
            entry.bind('<KeyRelease>', self._layout_invalidate, add='+')
        self._layout_preview(initial=True)

    def _layout_draft(self) -> AvatarLayout:
        return AvatarLayout(avatar=AVATARS[self._avatar.get()],
                            horizontal=self._layout_horizontal.get(),
                            vertical=self._layout_vertical.get(),
                            size=self._layout_size.get(), background=self._layout_background.get())

    def _layout_invalidate(self, *_args) -> None:
        self._layout_snapshot = None
        self._layout_status.set('배치·아바타·캐릭터·표정 변경 · 이전 미리보기 결과 무효')
        self._layout_preview(initial=True)

    def _layout_preview(self, *, initial: bool = False) -> None:
        try:
            draft = self._layout_draft()
            pose = AvatarFrame(self._current_persona()['name'], False, 4,
                               background=draft.background,
                               expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()])
            draw_layout_preview(self._layout_canvas, draft, pose)
            self._layout_snapshot = draft
            if not initial:
                self._layout_status.set(draft.describe())
        except (ValueError, KeyError, tk.TclError) as exc:
            self._layout_snapshot = None
            self._layout_canvas.delete('all')
            self._layout_canvas.configure(bg='#17223c')
            self._layout_canvas.create_text(320, 180, fill='white',
                text='2D 배치 미리보기 불가\n3D·미정은 2D 자동 대체 안 함',
                font=('Malgun Gothic', 14), tags=('aisting_layout_unavailable',))
            if not initial:
                self._layout_status.set('배치 미리보기 불가 · ' + str(exc))

    def _layout_reset(self) -> None:
        self._layout_horizontal.set(75)
        self._layout_vertical.set(100)
        self._layout_size.set(70)
        self._layout_background.set('남색 스튜디오')
        self._layout_preview()

    def _layout_save(self) -> None:
        try:
            draft = self._layout_draft()
            if self._layout_snapshot != draft:
                raise ValueError('미리보기 갱신 후 저장하세요.')
            if not messagebox.askyesno('배치 기록 저장',
                    '현재 내장 2D 가상 화면 배치를 로컬 JSON에 저장할까요?\nOBS나 방송에는 적용하지 않습니다.',
                    parent=self):
                self._layout_status.set('저장 취소 · 파일 변경 없음')
                return
            save_layout(layout_path(), draft, operator_confirmed=True)
            self._layout_status.set('확인 후 로컬 배치 초안 저장됨 · 실제 방송 미적용')
        except (ValueError, PermissionError, OSError) as exc:
            self._layout_status.set('배치 저장 불가 · ' + str(exc))

    def _layout_load(self) -> None:
        try:
            draft = load_layout(layout_path(), selected_avatar=AVATARS[self._avatar.get()])
            if draft is None:
                self._layout_status.set('저장된 화면 배치 없음')
                return
            self._layout_horizontal.set(draft.horizontal)
            self._layout_vertical.set(draft.vertical)
            self._layout_size.set(draft.size)
            self._layout_background.set(draft.background)
            self._layout_preview()
            self._layout_status.set('선택한 2D 기록 수동 불러오기 완료 · 실제 방송 미적용')
        except (ValueError, OSError) as exc:
            self._layout_status.set('불러오기 차단 · ' + str(exc))

    def _layout_delete(self) -> None:
        if not messagebox.askyesno('배치 삭제 확인 1', '저장된 내장 2D 배치 기록을 삭제할까요?', parent=self):
            self._layout_status.set('삭제 취소')
            return
        if not messagebox.askyesno('배치 삭제 확인 2', '한 번 더 확인: 배치 JSON만 삭제합니다.', parent=self):
            self._layout_status.set('2차 삭제 취소')
            return
        try:
            removed = delete_layout(layout_path(), operator_confirmed=True)
            self._layout_status.set('배치 기록 삭제 완료' if removed else '삭제할 기록 없음')
        except (ValueError, OSError) as exc:
            self._layout_status.set('삭제 실패 · ' + str(exc))

    def _build_avatar_endurance(self, tab) -> None:
        """059: accelerated, manual-only endurance and bounded Canvas redraw audit."""
        ttk.Label(tab, text='59단계 · 장시간 아바타 실행 모의 시험',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=4)
        ttk.Label(tab, text='가상 1·6·24시간의 모든 초 단위 상태를 계산하고, 실제 Tk 화면을 240회 반복 그립니다. '
                  '실제 24시간 실행이나 메모리 누수 검증은 아닙니다. 외부 장치·음성·방송 사용 안 함.',
                  wraplength=730).pack(anchor='w', pady=3)
        row = ttk.Frame(tab)
        row.pack(anchor='w', pady=5)
        ttk.Label(row, text='가상 시험 시간').pack(side='left')
        self._endurance_hours = tk.StringVar(value='24')
        ttk.Combobox(row, textvariable=self._endurance_hours, width=8,
                     values=tuple(str(x) for x in ALLOWED_HOURS),
                     state='readonly').pack(side='left', padx=7)
        ttk.Button(row, text='수동 모의 검사 시작', command=self._endurance_run).pack(side='left')
        self._endurance_canvas = tk.Canvas(tab, width=640, height=360,
                                           bg='#17223c', highlightthickness=1)
        self._endurance_canvas.pack(anchor='w', pady=5)
        self._endurance_status = tk.StringVar(value='시험 미실행 · 승인/실기기 검증 대기')
        ttk.Label(tab, textvariable=self._endurance_status,
                  wraplength=735, justify='left').pack(anchor='w', pady=3)
        self._endurance_result = None
        for var in (self._avatar, self._avatar_expression, self._persona_mode,
                    self._endurance_hours):
            var.trace_add('write', self._endurance_invalidate)
        for entry in self._persona.values():
            entry.bind('<KeyRelease>', self._endurance_invalidate, add='+')
        self._endurance_draw_idle()

    def _endurance_invalidate(self, *_args) -> None:
        self._endurance_result = None
        self._endurance_status.set('선택 변경 · 이전 장시간 모의 검사 결과 무효')
        self._endurance_draw_idle()

    def _endurance_draw_idle(self) -> None:
        try:
            choice = AVATARS[self._avatar.get()]
            if choice != '2d':
                if choice == '3d':
                    draw_unavailable_3d(self._endurance_canvas)
                else:
                    self._endurance_canvas.delete('all')
                    self._endurance_canvas.create_text(320, 180, text='2D 선택 후 모의 시험 가능',
                                                       fill='white')
                return
            name = self._current_persona()['name']
            pose = AvatarFrame(name, False, 4,
                               expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()])
            draw_layout_preview(self._endurance_canvas, AvatarLayout(), pose)
        except (ValueError, KeyError, tk.TclError):
            self._endurance_canvas.delete('all')

    def _endurance_run(self) -> None:
        self._endurance_result = None
        try:
            name = self._current_persona()['name']
            expression = AVATAR_EXPRESSIONS[self._avatar_expression.get()]
            result = run_virtual_endurance(
                avatar=AVATARS[self._avatar.get()], name=name,
                expression=expression, hours=int(self._endurance_hours.get()))
            low, high = audit_canvas_repetition(self._endurance_canvas,
                                                AvatarLayout(), result)
            self._endurance_result = result
            self._endurance_status.set(result.summary() +
                f'\n실제 Tk 화면 240회 다시 그리기: 객체 수 {low}~{high} (최대 40) · 통과')
        except (ValueError, KeyError, RuntimeError, tk.TclError) as exc:
            self._endurance_status.set('모의 시험 미완료/차단 · ' + str(exc))
            self._endurance_draw_idle()

    def _build_avatar_integration(self, tab) -> None:
        """060: manual integrated 2D sample/virtual voice/layout/endurance audit."""
        ttk.Label(tab, text='60단계 · 캐릭터 전체 작동 확인 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=4)
        ttk.Label(tab, text='현재 선택한 캐릭터·표정·배치와 Windows 무료 음성 방식을 이용해 '
                  '내장 2D 화면, 4표정, 가상 음성 중단/재개, 입 프레임, 가속 모의 장시간 상태를 검사합니다. '
                  '실제 소리·모델·OBS·Windows 실기기/자연스러움 검증은 아닙니다.',
                  wraplength=730).pack(anchor='w', pady=3)
        ttk.Button(tab, text='통합 모의 검사 수동 실행',
                   command=self._integration_run).pack(anchor='w', pady=5)
        self._integration_canvas = tk.Canvas(tab, width=640, height=360,
                                             bg='#17223c', highlightthickness=1)
        self._integration_canvas.pack(anchor='w', pady=5)
        self._integration_status = tk.StringVar(value='미시험 · 사용자 승인/실기기 검증 대기')
        ttk.Label(tab, textvariable=self._integration_status, wraplength=735,
                  justify='left').pack(anchor='w', pady=3)
        self._integration_report = None
        self._integration_log = tk.Text(tab, height=7, wrap='word', state='disabled')
        self._integration_log.pack(fill='both', expand=True)
        for var in (self._avatar, self._avatar_expression, self._persona_mode,
                    self._voice, self._voice_name, self._voice_rate, self._voice_volume,
                    self._layout_horizontal, self._layout_vertical, self._layout_size,
                    self._layout_background):
            var.trace_add('write', self._integration_invalidate)
        for entry in self._persona.values():
            entry.bind('<KeyRelease>', self._integration_invalidate, add='+')
        self._integration_draw_idle()

    def _integration_show(self, text: str) -> None:
        self._integration_log.configure(state='normal')
        self._integration_log.delete('1.0', 'end')
        self._integration_log.insert('1.0', text)
        self._integration_log.configure(state='disabled')

    def _integration_invalidate(self, *_args) -> None:
        self._integration_report = None
        self._integration_status.set('선택 변경 · 이전 통합 모의 검사 결과 무효')
        self._integration_show('')
        self._integration_draw_idle()

    def _integration_draw_idle(self) -> None:
        try:
            if AVATARS[self._avatar.get()] == '3d':
                draw_unavailable_3d(self._integration_canvas)
            elif AVATARS[self._avatar.get()] != '2d':
                self._integration_canvas.delete('all')
                self._integration_canvas.create_text(320, 180,
                    text='2D 선택 후 통합 모의 검사 가능', fill='white')
            else:
                layout = self._layout_draft()
                pose = AvatarFrame(self._current_persona()['name'], False, 4,
                    background=layout.background,
                    expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()])
                draw_layout_preview(self._integration_canvas, layout, pose)
        except (ValueError, KeyError, tk.TclError):
            self._integration_canvas.delete('all')

    def _integration_run(self) -> None:
        self._integration_report = None
        try:
            report = audit_avatar_integration(
                self._integration_canvas,
                avatar=AVATARS[self._avatar.get()],
                name=self._current_persona()['name'],
                expression=AVATAR_EXPRESSIONS[self._avatar_expression.get()],
                layout=self._layout_draft() if AVATARS[self._avatar.get()] == '2d' else AvatarLayout(),
                voice_source=VOICES[self._voice.get()],
                rate=int(self._voice_rate.get()), volume=int(self._voice_volume.get()))
            self._integration_report = report if report.passed else None
            self._integration_status.set(
                '내장 2D 통합 모의 검사 ' + ('통과' if report.passed else '실패') +
                ' · 실제 장치·모델·방송/사용자 최종 승인 미검증')
            self._integration_show(report.describe())
        except (ValueError, TypeError, KeyError, RuntimeError, tk.TclError) as exc:
            self._integration_status.set('통합 모의 검사 차단/미완료 · ' + str(exc))
            self._integration_show('실제 Windows/모델/음성/OBS 검증은 수행하지 않았습니다.')
            self._integration_draw_idle()

    def _build_platform_chat_connector(self, tab) -> None:
        """061: manually exercise a network-free multi-platform connection contract."""
        ttk.Label(tab, text='원본 61단계 · 방송 플랫폼 채팅 연결 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 9))
        ttk.Label(tab, text='방송 설정의 치지직·유튜브·트위치 선택을 그대로 사용합니다. '
                  '연결 버튼은 메모리 안의 가상 상태만 변경하며 계정 로그인·토큰·HTTP·웹소켓·'
                  '실제 채팅 수신·방송 송출은 하지 않습니다. 실제 연결은 구현·검증되지 않았습니다.',
                  wraplength=720).pack(anchor='w', pady=(0, 10))
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=6)
        ttk.Button(row, text='선택/계약 확인', command=self._platform_chat_preview).pack(side='left')
        ttk.Button(row, text='가상 연결 시작', command=self._platform_chat_connect).pack(side='left', padx=8)
        ttk.Button(row, text='가상 연결 해제', command=self._platform_chat_disconnect).pack(side='left')
        self._platform_chat_status = tk.StringVar(value='미연결 · 사용자 버튼을 눌러야 모의 상태 변경')
        ttk.Label(tab, textvariable=self._platform_chat_status, wraplength=720).pack(anchor='w', pady=6)
        self._platform_chat_log = tk.Text(tab, height=13, wrap='word', state='disabled')
        self._platform_chat_log.pack(fill='both', expand=True)
        self._platform_chat_session = None
        for flag in self._platforms.values():
            flag.trace_add('write', self._platform_chat_invalidate)
        self._platform_chat_preview()

    def _platform_chat_selected(self) -> list[str]:
        return [code for code, flag in self._platforms.items() if flag.get()]

    def _platform_chat_show(self, report) -> None:
        self._platform_chat_status.set(f'{report.phase} · 모의 연결 {len(report.connected)}개 · '
                                       f'시도 {report.attempts}회 · 실제 연결 0개')
        self._platform_chat_log.configure(state='normal')
        self._platform_chat_log.delete('1.0', 'end')
        self._platform_chat_log.insert('1.0', report.describe())
        self._platform_chat_log.configure(state='disabled')

    def _platform_chat_preview(self) -> None:
        if hasattr(self, "_mock_receiver"):
            self._mock_receiver.detach()  # retain already accepted synthetic chats
            self._mock_receive_show("가상 연결 재설정 · 기존 모의 채팅은 보존됨")
        self._platform_chat_session = OfflinePlatformChatConnector(self._platform_chat_selected())
        self._platform_chat_show(self._platform_chat_session.snapshot())

    def _platform_chat_invalidate(self, *_args) -> None:
        # Changing selected platforms must never retain a previous mock connection.
        self._platform_chat_preview()
        self._platform_chat_status.set('플랫폼 선택 변경 · 이전 모의 연결 무효 · 재확인 필요')

    def _platform_chat_connect(self) -> None:
        try:
            current = self._platform_chat_selected()
            if self._platform_chat_session is None or list(self._platform_chat_session.snapshot().selected) != current:
                self._platform_chat_session = OfflinePlatformChatConnector(current)
            self._platform_chat_show(self._platform_chat_session.connect())
        except ValueError as exc:
            self._platform_chat_status.set('모의 연결 차단 · ' + str(exc))

    def _platform_chat_disconnect(self) -> None:
        if self._platform_chat_session is None:
            self._platform_chat_preview()
        self._platform_chat_show(self._platform_chat_session.disconnect())
        if hasattr(self, "_mock_receiver"):
            self._mock_receiver.detach()
            self._mock_receive_show("가상 연결 해제 · 기존 모의 채팅은 보존됨")

    def _build_offline_chat_receiver(self, tab) -> None:
        """062: explicit synthetic reception, never an actual platform listener."""
        self._mock_receiver = OfflineChatReceiveBuffer()
        ttk.Label(tab, text='원본 62단계 · 채팅 메시지 수신 구조 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='61단계에서 가상 연결 후 여기서 수동으로 수신 준비하세요. '
                  '메시지를 직접 입력해 메모리 수신함에 넣습니다. 실제 채팅 수신·실시간 연결·'
                  '계정 접근·자동 타이머·AI 응답은 없습니다.', wraplength=730).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=6)
        ttk.Button(row, text='가상 수신 준비', command=self._mock_receive_attach).pack(side='left')
        ttk.Label(row, text='플랫폼').pack(side='left', padx=(12, 4))
        self._mock_receive_platform = tk.StringVar(value='chzzk')
        ttk.Combobox(row, textvariable=self._mock_receive_platform,
                     values=('chzzk', 'youtube', 'twitch'), state='readonly', width=13).pack(side='left')
        ttk.Label(row, text='닉네임').pack(side='left', padx=(10, 4))
        self._mock_receive_sender = tk.StringVar(value='시청자')
        ttk.Entry(row, textvariable=self._mock_receive_sender, width=16).pack(side='left')
        row2 = ttk.Frame(tab)
        row2.pack(fill='x', pady=6)
        ttk.Label(row2, text='가상 채팅').pack(side='left')
        self._mock_receive_text = tk.StringVar(value='안녕하세요')
        ttk.Entry(row2, textvariable=self._mock_receive_text, width=55).pack(side='left', padx=8)
        ttk.Button(row2, text='1건 수동 접수', command=self._mock_receive_inject).pack(side='left')
        self._mock_receive_status = tk.StringVar(value='미준비 · 실제 수신 0건')
        ttk.Label(tab, textvariable=self._mock_receive_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_receive_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_receive_log.pack(fill='both', expand=True)
        self._mock_receive_show('수동 입력 대기')

    def _mock_receive_show(self, note='') -> None:
        state = self._mock_receiver.snapshot()
        self._mock_receive_status.set(f'{note} · 모의 수신 {state.accepted_count}건 · '
                                      f'{"준비됨" if state.attached else "미준비"} · 실제 수신 0건')
        lines = [state.describe(), '', '최근 모의 채팅 (입력값):']
        lines.extend(f'{e.ordinal}. [{e.platform}] {e.sender}: {e.text}' for e in state.buffered[-10:])
        self._mock_receive_log.configure(state='normal')
        self._mock_receive_log.delete('1.0', 'end')
        self._mock_receive_log.insert('1.0', '\n'.join(lines))
        self._mock_receive_log.configure(state='disabled')

    def _mock_receive_attach(self) -> None:
        try:
            self._mock_receiver.attach(self._platform_chat_session)
            self._mock_receive_show('수동 가상 수신 준비 완료')
        except ValueError as exc:
            self._mock_receive_show('수신 준비 차단 · ' + str(exc))

    def _mock_receive_inject(self) -> None:
        try:
            self._mock_receiver.inject(self._mock_receive_platform.get(),
                                       self._mock_receive_sender.get(),
                                       self._mock_receive_text.get())
            self._mock_receive_show('가상 채팅 1건 수동 접수')
            self._mock_integrity_mark_stale()
            self._mock_reactions_mark_stale()
        except ValueError as exc:
            self._mock_receive_show('접수 차단 · ' + str(exc))

    def _build_offline_chat_order(self, tab) -> None:
        """063: operator-triggered FIFO audit of existing synthetic inbox."""
        self._mock_order = OfflineChatOrder(self._mock_receiver)
        ttk.Label(tab, text='원본 63단계 · 메시지 처리 순서 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='62단계에서 직접 접수한 가상 채팅을 수동 동기화하고 순서대로 1건씩 확인합니다. '
                  '같은 내용도 각각 보존하며, 모의 실패 시 현재 메시지를 유지합니다. '
                  '실제 플랫폼 수신·AI 응답·자동 처리·송출은 없습니다.',
                  wraplength=740).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=8)
        ttk.Button(row, text='수신함 수동 동기화', command=self._mock_order_sync).pack(side='left')
        ttk.Button(row, text='다음 1건 순서 확인', command=self._mock_order_next).pack(side='left', padx=5)
        ttk.Button(row, text='다음 1건 모의 실패', command=self._mock_order_fail).pack(side='left', padx=5)
        ttk.Button(row, text='수동 재개', command=self._mock_order_resume).pack(side='left')
        self._mock_order_status = tk.StringVar(value='순서 확인 대기 · 실제 메시지 0건')
        ttk.Label(tab, textvariable=self._mock_order_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_order_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_order_log.pack(fill='both', expand=True)
        self._mock_order_show('수동 동기화 대기')

    def _mock_order_show(self, note='') -> None:
        state = self._mock_order.snapshot()
        self._mock_order_status.set(f'{note} · 확인 {len(state.processed)}건 · '
                                    f'대기 {len(state.pending)}건 · 실제 메시지 0건')
        lines = [state.describe(), '', '대기 중인 채팅 (앞에서부터 최대 10건):']
        lines.extend(f'{e.ordinal}. [{e.platform}] {e.sender}: {e.text}' for e in state.pending[:10])
        self._mock_order_log.configure(state='normal')
        self._mock_order_log.delete('1.0', 'end')
        self._mock_order_log.insert('1.0', '\n'.join(lines))
        self._mock_order_log.configure(state='disabled')

    def _mock_order_sync(self) -> None:
        try:
            self._mock_order.sync()
            self._mock_order_show('수신 순서 동기화 완료')
            self._mock_integrity_mark_stale()
            self._mock_reactions_mark_stale()
        except ValueError as exc:
            self._mock_order_show('동기화 차단 · ' + str(exc))

    def _mock_order_next(self, *, fail=False) -> None:
        try:
            event = self._mock_order.acknowledge_next(simulate_failure=fail)
            self._mock_order_show(f'순서 확인 #{event.ordinal} · AI 응답 없음')
            self._mock_integrity_mark_stale()
            self._mock_reactions_mark_stale()
        except ValueError as exc:
            self._mock_order_show('처리 차단 · ' + str(exc))

    def _mock_order_fail(self) -> None:
        self._mock_order_next(fail=True)

    def _mock_order_resume(self) -> None:
        try:
            self._mock_order.resume()
            self._mock_order_show('운영자 수동 재개')
            self._mock_integrity_mark_stale()
            self._mock_reactions_mark_stale()
        except ValueError as exc:
            self._mock_order_show('재개 차단 · ' + str(exc))

    def _build_offline_chat_integrity(self, tab) -> None:
        """064: manual, read-only audit of the existing synthetic receiver/queue."""
        self._mock_integrity = OfflineChatIntegrity(self._mock_receiver, self._mock_order)
        ttk.Label(tab, text='원본 64단계 · 중복·누락 여부 확인 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='62단계 수동 수신함과 63단계 순서 관리 기록을 읽기 전용으로 비교합니다. '
                  '동일 내용은 정상 채팅일 수 있어 제거하지 않습니다. 미동기화는 누락이 아닙니다. '
                  '실제 플랫폼 ID·전송·누락 여부는 확인하지 않습니다.',
                  wraplength=740).pack(anchor='w')
        ttk.Button(tab, text='중복·누락 수동 점검', command=self._mock_integrity_run).pack(anchor='w', pady=9)
        self._mock_integrity_status = tk.StringVar(value='검사 전 · 실제 채팅 0건')
        ttk.Label(tab, textvariable=self._mock_integrity_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_integrity_log = tk.Text(tab, height=13, wrap='word', state='disabled')
        self._mock_integrity_log.pack(fill='both', expand=True)
        self._mock_integrity_show('수동 검사 대기 · 기존 채팅은 변경되지 않습니다.')

    def _mock_integrity_show(self, text: str) -> None:
        self._mock_integrity_log.configure(state='normal')
        self._mock_integrity_log.delete('1.0', 'end')
        self._mock_integrity_log.insert('1.0', text)
        self._mock_integrity_log.configure(state='disabled')

    def _mock_integrity_mark_stale(self) -> None:
        if hasattr(self, '_mock_integrity_status'):
            self._mock_integrity_status.set('수신·순서 상태 변경 · 이전 점검 결과 만료 · 다시 수동 검사 필요')
            self._mock_integrity_show('기존 검사 결과는 현재 상태를 나타내지 않습니다. 다시 수동 점검하세요.')

    def _mock_integrity_run(self) -> None:
        report = self._mock_integrity.inspect()
        self._mock_integrity_status.set(
            ('구조 오류 발견' if report.issues else '관찰된 메모리 구조 오류 없음')
            + f' · 반복 내용 {report.repeated_content_extra}건 · 미동기화 {report.unsynced}건 · 실제 채팅 0건')
        self._mock_integrity_show(report.describe())

    def _build_offline_chat_reactions(self, tab) -> None:
        """065: explicitly generate mock replies for each ordered 062 chat."""
        self._mock_reactions = OfflineChatReactions(self._mock_receiver, self._mock_order)
        ttk.Label(tab, text='원본 65단계 · 모든 채팅 기본 반응 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='62단계에서 수동 접수한 채팅을 63단계 순서로 동기화한 뒤 기존 모의 응답기로 각각 답합니다. '
                  '같은 내용도 모두 처리하며 실패한 선두 메시지는 보존합니다. '
                  '실제 플랫폼/AI 모델/음성/방송 연결은 없습니다.', wraplength=740).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=8)
        ttk.Button(row, text='순서 기록 수동 동기화', command=self._mock_reactions_sync).pack(side='left')
        ttk.Button(row, text='다음 1건 모의 응답', command=self._mock_reactions_next).pack(side='left', padx=4)
        ttk.Button(row, text='최대 50건 수동 처리', command=self._mock_reactions_batch).pack(side='left', padx=4)
        ttk.Button(row, text='다음 1건 모의 실패', command=self._mock_reactions_fail).pack(side='left', padx=4)
        ttk.Button(row, text='오류 수동 재개', command=self._mock_reactions_resume).pack(side='left')
        self._mock_reactions_status = tk.StringVar(value='모의 응답 대기 · 실제 AI 응답 0건')
        ttk.Label(tab, textvariable=self._mock_reactions_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_reactions_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_reactions_log.pack(fill='both', expand=True)
        self._mock_reactions_show('수동 동기화 대기')

    def _mock_reactions_show(self, note='') -> None:
        state = self._mock_reactions.snapshot()
        self._mock_reactions_status.set(f'{note} · 모의 응답 {len(state.responded)}건 · '
                                        f'대기 {len(state.pending)}건 · 미동기화 {state.unsynced}건 · 실제 AI 0건')
        self._mock_reactions_log.configure(state='normal')
        self._mock_reactions_log.delete('1.0', 'end')
        self._mock_reactions_log.insert('1.0', state.describe())
        self._mock_reactions_log.configure(state='disabled')

    def _mock_reactions_mark_stale(self) -> None:
        if hasattr(self, '_mock_reactions_status'):
            self._mock_reactions_status.set('수신·순서 상태 변경 · 모의 응답 현황은 다시 확인 필요')

    def _mock_reactions_sync(self) -> None:
        try:
            self._mock_reactions.sync()
            self._mock_reactions_show('응답 대기열 수동 동기화')
        except ValueError as exc:
            self._mock_reactions_show('동기화 차단 · ' + str(exc))

    def _mock_reactions_next(self, *, fail=False) -> None:
        try:
            item = self._mock_reactions.reply_next(simulate_failure=fail)
            self._mock_reactions_show(f'모의 응답 #{item.event.ordinal} 완료')
        except ValueError as exc:
            self._mock_reactions_show('응답 차단 · ' + str(exc))

    def _mock_reactions_batch(self) -> None:
        try:
            self._mock_reactions.reply_batch()
            self._mock_reactions_show('최대 50건 수동 모의 처리 완료')
        except ValueError as exc:
            self._mock_reactions_show('일괄 처리 중단 · ' + str(exc))

    def _mock_reactions_fail(self) -> None:
        self._mock_reactions_next(fail=True)

    def _mock_reactions_resume(self) -> None:
        try:
            self._mock_reactions.resume()
            self._mock_reactions_show('오류 후 운영자 수동 재개')
        except ValueError as exc:
            self._mock_reactions_show('재개 차단 · ' + str(exc))

    def _build_offline_chat_latency(self, tab) -> None:
        """066: manually time the existing 065 mock FIFO reply calls, no waits."""
        self._mock_latency = OfflineChatLatencyAudit(self._mock_reactions)
        ttk.Label(tab, text='원본 66단계 · 인위적 지연 없는 모의 채팅 응답 시간 관찰',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='62/63단계 모의 채팅을 먼저 수동 접수·순서 동기화한 뒤, '
                  '기존 65단계 모의 응답을 한 건씩 실제 호출하여 실행 시간만 측정합니다. '
                  '고의 대기·속도 합격 판정·자동 재시도는 없습니다. '
                  '실제 시청자 도착부터 응답까지의 시간이나 실제 AI/방송 속도는 아닙니다.',
                  wraplength=740).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=8)
        ttk.Button(row, text='65단계 기록 수동 동기화', command=self._mock_latency_sync).pack(side='left')
        ttk.Button(row, text='다음 1건 시간 측정', command=self._mock_latency_next).pack(side='left', padx=4)
        ttk.Button(row, text='최대 50건 수동 측정', command=self._mock_latency_batch).pack(side='left', padx=4)
        ttk.Button(row, text='현재 결과 새로 보기', command=self._mock_latency_refresh).pack(side='left')
        self._mock_latency_status = tk.StringVar(value='수동 모의 측정 대기 · 실제 채팅/AI 0건')
        ttk.Label(tab, textvariable=self._mock_latency_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_latency_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_latency_log.pack(fill='both', expand=True)
        self._mock_latency_show('측정 시작 전')

    def _mock_latency_show(self, note='') -> None:
        report = self._mock_latency.snapshot()
        self._mock_latency_status.set(f'{note} · 측정 {len(report.samples)}건 · '
                                      f'미측정 응답 {len(report.unmeasured_ordinals)}건 · '
                                      f'대기 {report.pending}건 · 실제 AI 0건')
        self._mock_latency_log.configure(state='normal')
        self._mock_latency_log.delete('1.0', 'end')
        self._mock_latency_log.insert('1.0', report.describe())
        self._mock_latency_log.configure(state='disabled')

    def _mock_latency_sync(self) -> None:
        try:
            self._mock_reactions.sync()
            self._mock_reactions_show('66단계 측정용 수동 동기화')
            self._mock_latency_show('65단계 기록 동기화 완료')
        except ValueError as exc:
            self._mock_latency_show('동기화 차단 · ' + str(exc))

    def _mock_latency_next(self) -> None:
        try:
            item = self._mock_latency.measure_next()
            self._mock_reactions_show('66단계 모의 응답 측정')
            self._mock_latency_show(f'#{item.ordinal} 처리 {item.elapsed_ms:.3f}ms (모의)')
        except ValueError as exc:
            self._mock_latency_show('측정 중단 · ' + str(exc))

    def _mock_latency_batch(self) -> None:
        try:
            self._mock_latency.measure_batch()
            self._mock_reactions_show('66단계 수동 측정 처리')
            self._mock_latency_show('최대 50건 모의 측정 완료')
        except ValueError as exc:
            self._mock_latency_show('측정 중단 · ' + str(exc))

    def _mock_latency_refresh(self) -> None:
        self._mock_latency_show('현재 메모리 상태 재확인')

    def _build_offline_viewer_context(self, tab) -> None:
        """067: explicitly enable same-viewer history for the existing FIFO mock port."""
        self._mock_viewer_context = OfflineViewerContext(self._mock_reactions)
        ttk.Label(tab, text='원본 67단계 · 시청자 대화 맥락 연결 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='62/63/65단계 기존 수신·순서·응답 기록을 사용합니다. '
                  '아직 응답하기 전에 시청자별 맥락을 수동 활성화하면 '
                  '동일 플랫폼+닉네임의 이전 성공 응답만 모의 답변 포트에 전달합니다. '
                  '닉네임은 실제 인증된 시청자 ID가 아닙니다.', wraplength=740).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=8)
        ttk.Button(row, text='시청자별 맥락 연결 활성화',
                   command=self._mock_viewer_context_enable).pack(side='left')
        ttk.Button(row, text='다음 대기 채팅 맥락 새로 보기',
                   command=self._mock_viewer_context_refresh).pack(side='left', padx=6)
        self._mock_viewer_context_status = tk.StringVar(value='시청자별 맥락 비활성 · 모의 답변만 지원')
        ttk.Label(tab, textvariable=self._mock_viewer_context_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_viewer_context_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_viewer_context_log.pack(fill='both', expand=True)
        self._mock_viewer_context_show('수동 활성화 대기')

    def _mock_viewer_context_show(self, note='') -> None:
        report = self._mock_viewer_context.snapshot()
        self._mock_viewer_context_status.set(
            f'{note} · {"활성" if report.enabled else "비활성"} · '
            f'응답 {report.replied}건 · 대기 {report.pending}건 · 실제 AI/플랫폼 0건')
        self._mock_viewer_context_log.configure(state='normal')
        self._mock_viewer_context_log.delete('1.0', 'end')
        self._mock_viewer_context_log.insert('1.0', report.describe())
        self._mock_viewer_context_log.configure(state='disabled')

    def _mock_viewer_context_enable(self) -> None:
        try:
            self._mock_viewer_context.enable()
            self._mock_viewer_context_show('시청자별 맥락 연결 활성화 · 65/66단계 수동 응답에 적용')
        except ValueError as exc:
            self._mock_viewer_context_show('활성화 차단 · ' + str(exc))

    def _mock_viewer_context_refresh(self) -> None:
        self._mock_viewer_context_show('현재 대기 채팅 맥락 수동 확인')

    def _build_offline_multi_viewer(self, tab) -> None:
        """068: operator-driven interleaved multi-viewer FIFO, existing 062-067."""
        self._mock_multi_viewer = OfflineMultiViewerDialogue(self._mock_reactions)
        ttk.Label(tab, text='원본 68단계 · 여러 시청자 대화 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='기존 수동 채팅 수신함/순서 관리/모의 응답을 그대로 사용합니다. '
                  '첫 응답 전에 시청자별 맥락을 활성화하고, 여러 가상 닉네임이 섞인 채팅을 '
                  '전체 FIFO 순서로 처리합니다. 시청자별 선별·우선순위·고의 지연·자동 재시도는 없습니다. '
                  '실제 계정/플랫폼/AI/방송 연결은 없습니다.', wraplength=740).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=8)
        ttk.Button(row, text='시청자별 맥락 수동 활성화',
                   command=self._mock_multi_activate).pack(side='left')
        ttk.Button(row, text='수신·순서 수동 동기화',
                   command=self._mock_multi_sync).pack(side='left', padx=4)
        ttk.Button(row, text='다음 1건 응답',
                   command=self._mock_multi_next).pack(side='left', padx=4)
        ttk.Button(row, text='최대 50건 수동 처리',
                   command=self._mock_multi_batch).pack(side='left', padx=4)
        row2 = ttk.Frame(tab)
        row2.pack(fill='x', pady=4)
        ttk.Button(row2, text='다음 1건 모의 실패',
                   command=self._mock_multi_fail).pack(side='left')
        ttk.Button(row2, text='오류 수동 재개',
                   command=self._mock_multi_resume).pack(side='left', padx=4)
        ttk.Button(row2, text='시청자별 현황 새로 보기',
                   command=self._mock_multi_refresh).pack(side='left', padx=4)
        self._mock_multi_status = tk.StringVar(value='수동 모의 대기 · 실제 채팅/AI 0건')
        ttk.Label(tab, textvariable=self._mock_multi_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_multi_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_multi_log.pack(fill='both', expand=True)
        self._mock_multi_show('첫 응답 전 활성화 필요')

    def _mock_multi_show(self, note='') -> None:
        report = self._mock_multi_viewer.snapshot()
        self._mock_multi_status.set(f'{note} · 시청자 {len(report.viewers)}명 · '
                                    f'응답 {report.replied}건 · 대기 {report.pending}건 · '
                                    f'미동기화 {report.unsynced}건 · 실제 AI 0건')
        self._mock_multi_log.configure(state='normal')
        self._mock_multi_log.delete('1.0', 'end')
        self._mock_multi_log.insert('1.0', report.describe())
        self._mock_multi_log.configure(state='disabled')

    def _mock_multi_activate(self) -> None:
        try:
            self._mock_multi_viewer.activate()
            self._mock_multi_show('시청자별 맥락 수동 활성화 완료')
        except ValueError as exc:
            self._mock_multi_show('활성화 차단 · ' + str(exc))

    def _mock_multi_sync(self) -> None:
        try:
            self._mock_multi_viewer.sync()
            self._mock_multi_show('수신·순서 수동 동기화 완료')
        except ValueError as exc:
            self._mock_multi_show('동기화 차단 · ' + str(exc))

    def _mock_multi_next(self, *, fail=False) -> None:
        try:
            item = self._mock_multi_viewer.reply_next(simulate_failure=fail)
            self._mock_multi_show(f'전체 FIFO #{item.event.ordinal} 모의 응답 완료')
        except ValueError as exc:
            self._mock_multi_show('응답 차단 · ' + str(exc))

    def _mock_multi_fail(self) -> None:
        self._mock_multi_next(fail=True)

    def _mock_multi_batch(self) -> None:
        try:
            self._mock_multi_viewer.reply_batch()
            self._mock_multi_show('최대 50건 수동 모의 처리 완료')
        except ValueError as exc:
            self._mock_multi_show('일괄 처리 중단 · ' + str(exc))

    def _mock_multi_resume(self) -> None:
        try:
            self._mock_multi_viewer.resume()
            self._mock_multi_show('응답 오류 운영자 수동 재개 · 재시도는 별도 버튼')
        except ValueError as exc:
            self._mock_multi_show('재개 차단 · ' + str(exc))

    def _mock_multi_refresh(self) -> None:
        self._mock_multi_show('시청자별 현황 수동 재확인')

    def _build_offline_chat_recovery(self, tab) -> None:
        """069: operator-only offline outage/recovery of the existing chat chain."""
        self._mock_chat_recovery = None
        ttk.Label(tab, text='원본 69단계 · 채팅 연결 장애 복구 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='61단계 가상 연결 + 62단계 수신 준비 후 장애를 수동 발생시킵니다. '
                  '가상 재연결과 수신 재준비는 별도 수동 버튼이며 기존 수신·순서·응답 기록을 유지합니다. '
                  '실제 플랫폼/계정/네트워크 연결·자동 재시도·실시간 누락 복구는 없습니다.',
                  wraplength=740).pack(anchor='w')
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=8)
        ttk.Button(row, text='모의 장애 발생', command=self._mock_recovery_outage).pack(side='left')
        ttk.Button(row, text='재연결 실패 1회 시험', command=self._mock_recovery_fail).pack(side='left', padx=5)
        ttk.Button(row, text='수동 가상 재연결', command=self._mock_recovery_reconnect).pack(side='left', padx=5)
        row2 = ttk.Frame(tab)
        row2.pack(fill='x', pady=4)
        ttk.Button(row2, text='수신 수동 재준비', command=self._mock_recovery_reattach).pack(side='left')
        ttk.Button(row2, text='보존 상태 확인', command=self._mock_recovery_refresh).pack(side='left', padx=5)
        self._mock_recovery_status = tk.StringVar(value='가상 장애 수동 시험 대기')
        ttk.Label(tab, textvariable=self._mock_recovery_status, wraplength=740).pack(anchor='w', pady=6)
        self._mock_recovery_log = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._mock_recovery_log.pack(fill='both', expand=True)
        self._mock_recovery_show('기존 61·62단계에서 수동 연결/수신 준비 필요')

    def _mock_recovery_show(self, note='') -> None:
        if self._mock_chat_recovery is None:
            detail = '장애 시험을 시작하지 않았습니다. 실제 연결/수신 0건.'
            self._mock_recovery_status.set(note)
        else:
            report = self._mock_chat_recovery.snapshot(self._platform_chat_session)
            detail = report.describe()
            self._mock_recovery_status.set(note + ' · ' + report.phase +
                                           ' · 기존 수신 ' + str(report.accepted) + '건')
        self._mock_recovery_log.configure(state='normal')
        self._mock_recovery_log.delete('1.0', 'end')
        self._mock_recovery_log.insert('1.0', detail)
        self._mock_recovery_log.configure(state='disabled')

    def _mock_recovery_outage(self) -> None:
        try:
            if (self._mock_chat_recovery is None or
                    self._mock_chat_recovery._connector is not self._platform_chat_session):
                self._mock_chat_recovery = OfflineChatConnectionRecovery(
                    self._platform_chat_session, self._mock_receiver,
                    self._mock_order, self._mock_reactions)
            self._mock_chat_recovery.inject_outage(self._platform_chat_session)
            self._mock_receive_show('모의 장애 · 수신 중단 · 기존 채팅 보존')
            self._platform_chat_show(self._platform_chat_session.snapshot())
            self._mock_recovery_show('장애 수동 발생')
        except ValueError as exc:
            self._mock_recovery_show('장애 시험 차단 · ' + str(exc))

    def _mock_recovery_reconnect(self, *, fail=False) -> None:
        try:
            if self._mock_chat_recovery is None:
                raise ValueError('먼저 장애를 수동 발생시키세요.')
            self._mock_chat_recovery.reconnect(self._platform_chat_session, fail_handshake=fail)
            self._platform_chat_show(self._platform_chat_session.snapshot())
            self._mock_recovery_show('재연결 1회 수동 시도')
        except ValueError as exc:
            self._mock_recovery_show('재연결 차단 · ' + str(exc))

    def _mock_recovery_fail(self) -> None:
        self._mock_recovery_reconnect(fail=True)

    def _mock_recovery_reattach(self) -> None:
        try:
            if self._mock_chat_recovery is None:
                raise ValueError('먼저 장애를 수동 발생시키세요.')
            self._mock_chat_recovery.reattach(self._platform_chat_session)
            self._mock_receive_show('수동 재준비 완료 · 기존 채팅 유지')
            self._mock_recovery_show('모의 복구 확인')
        except ValueError as exc:
            self._mock_recovery_show('수신 재준비 차단 · ' + str(exc))

    def _mock_recovery_refresh(self) -> None:
        self._mock_recovery_show('현재 연결/보존 상태 수동 재확인')

    def _build_offline_chat_communication_audit(self, tab) -> None:
        """070: isolated operator-triggered, network-free end-to-end drill."""
        ttk.Label(tab, text='원본 70단계 · 채팅 소통 전 과정 검증 (오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='방송 설정에서 선택한 플랫폼으로 별도 메모리 시나리오를 실행합니다. '
                  '기존 채팅/응답 세션과 설정은 변경하지 않습니다. 수동 연결·수신·FIFO·'
                  '여러 시청자 맥락·응답 실패/수동 재개·장애/수동 복구·전체 응답을 검사합니다. '
                  '실제 실시간 플랫폼/AI/방송 검증이나 사용자 최종 승인은 아닙니다.',
                  wraplength=740).pack(anchor='w')
        ttk.Button(tab, text='독립 오프라인 통합 시험 실행',
                   command=self._mock_communication_run).pack(anchor='w', pady=8)
        self._mock_communication_status = tk.StringVar(value='미실행 · 운영자 수동 시험 대기')
        ttk.Label(tab, textvariable=self._mock_communication_status,
                  wraplength=740).pack(anchor='w', pady=5)
        self._mock_communication_log = tk.Text(tab, height=17, wrap='word', state='disabled')
        self._mock_communication_log.pack(fill='both', expand=True)
        self._mock_communication_report = None
        for flag in self._platforms.values():
            flag.trace_add('write', self._mock_communication_invalidate)

    def _mock_communication_invalidate(self, *_args) -> None:
        self._mock_communication_report = None
        self._mock_communication_status.set('플랫폼 선택 변경 · 이전 통합 시험 결과 무효 · 재실행 필요')
        self._mock_communication_log.configure(state='normal')
        self._mock_communication_log.delete('1.0', 'end')
        self._mock_communication_log.insert('1.0', '플랫폼 선택이 변경되어 이전 오프라인 검증 결과를 폐기했습니다.')
        self._mock_communication_log.configure(state='disabled')

    def _mock_communication_run(self) -> None:
        self._mock_communication_report = None
        try:
            selected = self._platform_chat_selected()
            report = run_offline_chat_communication_audit(selected)
            self._mock_communication_report = report
            self._mock_communication_status.set(
                ('오프라인 통합 시험 통과' if report.passed else '오프라인 통합 시험 실패') +
                ' · 실제 플랫폼/Windows/사용자 승인 미검증')
            detail = report.describe()
        except ValueError as exc:
            self._mock_communication_status.set('오프라인 통합 시험 미실행 · ' + str(exc))
            detail = '검증 불가 · ' + str(exc) + '\n실제 플랫폼 연결/수신/송출은 실행하지 않았습니다.'
        self._mock_communication_log.configure(state='normal')
        self._mock_communication_log.delete('1.0', 'end')
        self._mock_communication_log.insert('1.0', detail)
        self._mock_communication_log.configure(state='disabled')

    def _build_broadcast_schedule(self, tab) -> None:
        """081: operator-editable weekly draft, NEVER registers a scheduler."""
        ttk.Label(tab, text='원본 81단계 · 방송 시작 일정 관리 (로컬 초안 / 자동 실행 불가)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='한국 시간(KST) 기준으로 요일·시각 초안을 수동 관리합니다. '
                  '현재 시각·PC 환경을 자동 조사하지 않으며, 예정 시각 계산에도 직접 입력한 날짜를 사용합니다. '
                  '저장은 운영자가 명시적으로 누를 때만 수행합니다. '
                  'OBS·방송 플랫폼·외부 서버·방송 자동 시작·공지 기능은 연결되지 않습니다.',
                  wraplength=735).pack(anchor='w', pady=4)
        ttk.Button(tab, text='083 시작부터 종료까지 통합 모의 감사 (송출 불가)',
                   command=self._full_cycle_audit_run).pack(anchor='w', pady=5)
        self._full_cycle_status = tk.StringVar(value='083 미검사 · 실제 시작·음성·종료 모두 비활성')
        ttk.Label(tab, textvariable=self._full_cycle_status, wraplength=735).pack(anchor='w', pady=3)
        self._schedule_draft = BroadcastScheduleDraft()
        self._start_control = OfflineStartController(self._schedule_draft)
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=5)
        self._schedule_weekday = tk.StringVar(value='월')
        self._schedule_start_time = tk.StringVar(value='19:30')
        ttk.Label(row, text='요일').pack(side='left')
        ttk.Combobox(row, textvariable=self._schedule_weekday, state='readonly',
                     values=WEEKDAYS, width=5).pack(side='left', padx=5)
        ttk.Label(row, text='시작 HH:MM').pack(side='left')
        ttk.Entry(row, textvariable=self._schedule_start_time, width=8).pack(side='left', padx=5)
        ttk.Button(row, text='일정 추가', command=self._schedule_add).pack(side='left', padx=5)
        ttk.Button(row, text='선택 일정 제거', command=self._schedule_remove).pack(side='left', padx=5)
        self._schedule_list = tk.Listbox(tab, height=5, width=38, exportselection=False)
        self._schedule_list.pack(anchor='w', pady=4)
        storage_row = ttk.Frame(tab)
        storage_row.pack(fill='x', pady=5)
        ttk.Button(storage_row, text='초안 로컬 저장 (수동)',
                   command=self._schedule_save).pack(side='left', padx=3)
        ttk.Button(storage_row, text='저장 초안 불러오기 (수동)',
                   command=self._schedule_load).pack(side='left', padx=3)
        ttk.Button(storage_row, text='저장 초안 파일 삭제 (수동)',
                   command=self._schedule_delete).pack(side='left', padx=3)
        preview = ttk.Frame(tab)
        preview.pack(fill='x', pady=5)
        self._schedule_reference = tk.StringVar(value='')
        ttk.Label(preview, text='수동 기준일시 YYYY-MM-DD HH:MM').pack(side='left')
        ttk.Entry(preview, textvariable=self._schedule_reference, width=19).pack(side='left', padx=5)
        ttk.Button(preview, text='다음 5개 예정 시각 계산 (방송 시작 안 함)',
                   command=self._schedule_preview).pack(side='left', padx=5)
        self._schedule_status = tk.StringVar(
            value='081 일정 초안 비어 있음 · 자동 시작 비활성 · 저장/불러오기 수동 · 최종 승인 대기')
        ttk.Label(tab, textvariable=self._schedule_status, wraplength=735).pack(anchor='w', pady=6)
        self._schedule_next = tk.StringVar(value='다음 시작 예고 없음 (실행/예약 아님)')
        ttk.Label(tab, textvariable=self._schedule_next, wraplength=735).pack(anchor='w')
        self._schedule_start_time.trace_add('write', self._schedule_input_changed)
        self._schedule_reference.trace_add('write', self._schedule_input_changed)
        mock_row = ttk.Frame(tab)
        mock_row.pack(fill='x', pady=6)
        ttk.Label(mock_row, text='082 자동 시작 제어 수동 시험 (실제 예약/송출 절대 안 함)').pack(side='left')
        ttk.Button(mock_row, text='시작 가능성 판정', command=self._start_control_inspect).pack(side='left', padx=4)
        ttk.Button(mock_row, text='가상 시작', command=self._start_control_simulate).pack(side='left', padx=4)
        ttk.Button(mock_row, text='가상 종료', command=self._start_control_finish).pack(side='left', padx=4)
        self._start_control_status = tk.StringVar(value='082 수동 미검사 · 실제 자동 시작/OBS 연결 없음')
        ttk.Label(tab, textvariable=self._start_control_status, wraplength=735).pack(anchor='w', pady=4)

    def _build_prebroadcast_notice(self, tab) -> None:
        """084: explicit text preview; no posting, generation service, or scheduler."""
        ttk.Label(tab, text='084 방송 전 공지 문구 생성 (로컬 검토용)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='캐릭터·콘텐츠·플랫폼의 현재 저장 설정과 운영자가 입력한 시각으로 '
                  '규칙 기반 문구만 만듭니다. 실제 AI 생성·게시·공지 예약·실제 방송 시작은 하지 않습니다. '
                  '설정 변경 후에는 다시 생성해야 합니다.', wraplength=730).pack(anchor='w', pady=4)
        row = ttk.Frame(tab)
        row.pack(anchor='w', pady=5)
        self._notice_when = tk.StringVar(value='')
        self._notice_topic = tk.StringVar(value='')
        ttk.Label(row, text='공지할 KST 시작 시각 YYYY-MM-DD HH:MM').pack(side='left')
        ttk.Entry(row, textvariable=self._notice_when, width=19).pack(side='left', padx=7)
        topic_row = ttk.Frame(tab)
        topic_row.pack(anchor='w', pady=5)
        ttk.Label(topic_row, text='방송 주제 (선택)').pack(side='left')
        ttk.Entry(topic_row, textvariable=self._notice_topic, width=60).pack(side='left', padx=7)
        ttk.Button(tab, text='공지 초안 수동 생성 (게시하지 않음)',
                   command=self._notice_make).pack(anchor='w', pady=8)
        self._notice_status = tk.StringVar(value='084 미생성 · 전송/예약 없음')
        ttk.Label(tab, textvariable=self._notice_status, wraplength=720).pack(anchor='w', pady=5)
        self._notice_text = tk.Text(tab, height=10, wrap='word', state='disabled')
        self._notice_text.pack(fill='both', expand=True, pady=7)
        self._notice_signature = None
        self._notice_draft = None
        self._notice_when.trace_add('write', self._notice_invalidate)
        self._notice_topic.trace_add('write', self._notice_invalidate)

    def _notice_invalidate(self, *_args) -> None:
        if hasattr(self, "_end_notice_status"):
            self._end_notice_invalidate()
        self._notice_signature = None
        self._notice_draft = None
        if hasattr(self, "_discord_notice_status"):
            self._discord_notice_clear()
        if hasattr(self, "_cafe_review_status"):
            self._cafe_review_clear()
        if hasattr(self, "_notice_variation_status"):
            self._notice_variation_clear()
        self._notice_status.set('084 입력 변경 · 이전 초안 무효 · 게시/예약 없음')
        self._notice_text.configure(state='normal')
        self._notice_text.delete('1.0', 'end')
        self._notice_text.configure(state='disabled')

    def _notice_make(self) -> None:
        self._notice_invalidate()
        try:
            draft = make_prebroadcast_notice(
                self.settings, parse_reference(self._notice_when.get()), self._notice_topic.get())
        except (ValueError, TypeError) as exc:
            self._notice_status.set('084 초안 생성 거부 · ' + str(exc) + ' · 게시 없음')
            return
        self._notice_text.configure(state='normal')
        self._notice_text.insert('1.0', draft.text)
        self._notice_text.configure(state='disabled')
        self._notice_signature = (self._notice_when.get(), self._notice_topic.get())
        self._notice_draft = draft
        self._notice_status.set(draft.describe())

    def _build_end_notice(self, tab) -> None:
        """089: virtual-only end notice, with explicit opt-in local JSON export."""
        ttk.Label(tab, text='089 방송 종료 공지 및 결과 기록 (실제 송출/게시 없음)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='먼저 방송 화면 미리보기에서 078 최대 시간 판정 후 079 예고·인사와 가상 종료를 완료하세요. '
                  '여기서는 입력한 KST 예정 시작 시각을 참고해 가상 기록만 만듭니다. 실제 시청자 수·방송 시간·OBS 상태는 측정하지 않습니다.',
                  wraplength=740).pack(anchor='w', pady=4)
        self._end_notice_start = tk.StringVar(value='')
        self._end_notice_note = tk.StringVar(value='')
        line = ttk.Frame(tab)
        line.pack(anchor='w', pady=5)
        ttk.Label(line, text='수동 예정 시작 KST (YYYY-MM-DD HH:MM)').pack(side='left')
        ttk.Entry(line, textvariable=self._end_notice_start, width=20).pack(side='left', padx=5)
        line2 = ttk.Frame(tab)
        line2.pack(anchor='w', pady=5)
        ttk.Label(line2, text='운영자 메모 (선택)').pack(side='left')
        ttk.Entry(line2, textvariable=self._end_notice_note, width=58).pack(side='left', padx=5)
        self._end_notice_start.trace_add('write', self._end_notice_invalidate)
        self._end_notice_note.trace_add('write', self._end_notice_invalidate)
        buttons = ttk.Frame(tab)
        buttons.pack(anchor='w', pady=7)
        ttk.Button(buttons, text='가상 종료 공지·결과 초안 만들기',
                   command=self._end_notice_make).pack(side='left', padx=4)
        ttk.Button(buttons, text='결과 JSON 수동 저장 (기존 파일 덮어쓰기 금지)',
                   command=self._end_notice_export).pack(side='left', padx=4)
        self._end_notice_status = tk.StringVar(value='089 미생성 · 실제 방송·게시·통계 미확인')
        ttk.Label(tab, textvariable=self._end_notice_status, wraplength=735).pack(anchor='w', pady=5)
        self._end_notice_text = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._end_notice_text.pack(fill='both', expand=True, pady=5)
        self._end_notice_result = None
        self._end_notice_signature = None

    def _end_notice_invalidate(self, *_args) -> None:
        if not hasattr(self, '_end_notice_status'):
            return
        self._end_notice_result = None
        self._end_notice_signature = None
        self._end_notice_status.set('089 입력·설정·가상 종료 변경 · 초안 무효 · 실제 송출/게시 없음')
        self._end_notice_text.configure(state='normal')
        self._end_notice_text.delete('1.0', 'end')
        self._end_notice_text.configure(state='disabled')

    def _end_notice_fingerprint(self):
        if self._closing_session is None or self._duration_report is None:
            raise ValueError('079 가상 종료와 078 시간 판정을 먼저 완료해야 합니다.')
        if self._scene_snapshot is None or self._scene_snapshot != self._broadcast_scene_draft():
            raise ValueError('현재 선택으로 방송 화면 미리보기를 다시 확인하세요.')
        return (self._closing_session.snapshot(), self._duration_report,
                self._broadcast_scene_draft(), self._end_notice_start.get(),
                self._end_notice_note.get())

    def _end_notice_make(self) -> None:
        self._end_notice_invalidate()
        try:
            fingerprint = self._end_notice_fingerprint()
            draft = create_offline_end_notice(
                self.settings, parse_reference(self._end_notice_start.get()),
                self._duration_report, self._closing_session.snapshot(),
                self._end_notice_note.get())
            self._end_notice_result = draft
            self._end_notice_signature = fingerprint
            self._end_notice_text.configure(state='normal')
            self._end_notice_text.insert('1.0', draft.text)
            self._end_notice_text.configure(state='disabled')
            self._end_notice_status.set(draft.describe())
        except (ValueError, TypeError, KeyError) as exc:
            self._end_notice_status.set('089 초안 생성 거부 · ' + str(exc) + ' · 실제 송출/게시 없음')

    def _end_notice_export(self) -> None:
        if self._end_notice_result is None:
            self._end_notice_status.set('089 먼저 가상 종료 초안을 생성하세요 · 파일 생성 없음')
            return
        try:
            if self._end_notice_signature != self._end_notice_fingerprint():
                raise ValueError('설정이나 가상 종료 상태 변경 · 다시 초안을 생성하세요.')
            from tkinter import filedialog
            from pathlib import Path
            target = filedialog.asksaveasfilename(
                parent=self, title='089 가상 결과 JSON 저장 (기존 파일 덮어쓰기 불가)',
                defaultextension='.json', filetypes=[('JSON', '*.json')])
            if not target:
                self._end_notice_status.set('089 운영자가 저장 취소 · 기존 자료 유지')
                return
            self._end_notice_result.export_json(Path(target))
            self._end_notice_status.set('089 운영자가 선택한 경로에 가상 결과만 저장 · 실제 방송/게시 아님')
        except (ValueError, OSError, KeyError) as exc:
            self._end_notice_status.set('089 결과 저장 거부/실패 · ' + str(exc) + ' · 기존 파일 덮어쓰기 없음')

    def _build_notice_variation(self, tab) -> None:
        """088 operator-driven, memory-only review; does not replace the 084 draft."""
        ttk.Label(tab, text='088 공지 문구 변주 및 운영자 설정 (오프라인 검토)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='084 공지 초안을 먼저 수동 생성하세요. 아래 옵션은 저장되지 않고 '
                  '다른 게시 준비 기능의 초안도 바꾸지 않습니다. AI 생성·실제 게시·예약 없음.',
                  wraplength=730).pack(anchor='w', pady=4)
        row = ttk.Frame(tab)
        row.pack(anchor='w', pady=5)
        self._notice_variation_style = tk.StringVar(value='친근')
        self._notice_variation_length = tk.StringVar(value='기본')
        self._notice_variation_number = tk.StringVar(value='1')
        self._notice_variation_emoji = tk.BooleanVar(value=False)
        self._notice_variation_lead = tk.StringVar(value='0')
        self._notice_variation_context = tk.StringVar(value='')
        ttk.Label(row, text='문구 분위기').pack(side='left')
        ttk.Combobox(row, textvariable=self._notice_variation_style, values=('친근', '차분', '활기'),
                     state='readonly', width=8).pack(side='left', padx=5)
        ttk.Label(row, text='길이').pack(side='left')
        ttk.Combobox(row, textvariable=self._notice_variation_length, values=('짧게', '기본', '자세히'),
                     state='readonly', width=8).pack(side='left', padx=5)
        ttk.Label(row, text='변주 번호').pack(side='left')
        ttk.Combobox(row, textvariable=self._notice_variation_number, values=('1', '2', '3'),
                     state='readonly', width=4).pack(side='left', padx=5)
        ttk.Checkbutton(row, text='이모지', variable=self._notice_variation_emoji).pack(side='left', padx=5)
        second = ttk.Frame(tab)
        second.pack(anchor='w', pady=5)
        ttk.Label(second, text='당일 맥락 (선택)').pack(side='left')
        ttk.Entry(second, textvariable=self._notice_variation_context, width=42).pack(side='left', padx=6)
        ttk.Label(second, text='공지 권장 시간차(분, 0=안 함 / 10~40)').pack(side='left')
        ttk.Entry(second, textvariable=self._notice_variation_lead, width=5).pack(side='left', padx=6)
        for state in (self._notice_variation_style, self._notice_variation_length,
                      self._notice_variation_number, self._notice_variation_emoji,
                      self._notice_variation_lead, self._notice_variation_context):
            state.trace_add('write', self._notice_variation_clear)
        ttk.Button(tab, text='공지 변주 수동 미리보기 (게시/예약 없음)',
                   command=self._notice_variation_make).pack(anchor='w', pady=8)
        self._notice_variation_status = tk.StringVar(value='088 미생성 · 실제 AI/게시/예약 없음')
        ttk.Label(tab, textvariable=self._notice_variation_status, wraplength=735).pack(anchor='w', pady=5)
        self._notice_variation_text = tk.Text(tab, height=12, wrap='word', state='disabled')
        self._notice_variation_text.pack(fill='both', expand=True, pady=5)

    def _notice_variation_clear(self, *_args) -> None:
        if not hasattr(self, '_notice_variation_status'):
            return
        self._notice_variation_status.set('088 공지/옵션 변경 · 이전 변주 무효 · 미게시')
        self._notice_variation_text.configure(state='normal')
        self._notice_variation_text.delete('1.0', 'end')
        self._notice_variation_text.configure(state='disabled')

    def _notice_variation_make(self) -> None:
        self._notice_variation_clear()
        try:
            if self._notice_draft is None or self._notice_signature != (
                    self._notice_when.get(), self._notice_topic.get()):
                raise ValueError('084 공지 초안을 먼저 생성해야 합니다.')
            current = make_prebroadcast_notice(
                self.settings, parse_reference(self._notice_when.get()), self._notice_topic.get())
            if current != self._notice_draft or self._notice_text.get('1.0', 'end-1c') != current.text:
                raise ValueError('084 원본 초안 또는 설정 변경이 감지됐습니다. 다시 생성하세요.')
            options = NoticeVariationOptions(
                style=self._notice_variation_style.get(), length=self._notice_variation_length.get(),
                variant_number=int(self._notice_variation_number.get()),
                emoji=self._notice_variation_emoji.get(), context=self._notice_variation_context.get(),
                lead_minutes=int(self._notice_variation_lead.get()))
            preview = make_notice_variation(current, self.settings, options)
        except (ValueError, TypeError) as exc:
            self._notice_variation_status.set('088 변주 생성 거부 · ' + str(exc) + ' · 미게시')
            return
        self._notice_variation_text.configure(state='normal')
        self._notice_variation_text.insert('1.0', preview.text)
        self._notice_variation_text.configure(state='disabled')
        self._notice_variation_status.set(preview.describe())

    def _build_naver_cafe_review(self, tab) -> None:
        """087 offline official API feasibility review; no credentials/network."""
        ttk.Label(tab, text='087 네이버 카페 공식 연동 사전 검토 (오프라인)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='084 방송 전 공지 초안을 먼저 생성하세요. 공식 API 지원 범위·현재 이용약관·'
                  '카페 권한은 이 환경에서 확인할 수 없으며 연결/인증/글쓰기/브라우저 자동화가 없습니다. '
                  '검토 보고서는 API 요청 본문이 아니라 읽기 전용 참고자료입니다.',
                  wraplength=735).pack(anchor='w', pady=5)
        ttk.Button(tab, text='카페 연동 가능 조건 수동 검토 (게시 불가)',
                   command=self._cafe_review_inspect).pack(anchor='w', pady=8)
        self._cafe_review_status = tk.StringVar(value='087 미검토 · 공식 API/권한 미확인 · 미게시')
        ttk.Label(tab, textvariable=self._cafe_review_status, wraplength=735).pack(anchor='w', pady=5)
        self._cafe_review_text = tk.Text(tab, height=16, wrap='word', state='disabled')
        self._cafe_review_text.pack(fill='both', expand=True, pady=7)

    def _cafe_review_clear(self) -> None:
        self._cafe_review_status.set('087 원본 공지/설정 변경 · 이전 검토 결과 무효 · 미게시')
        self._cafe_review_text.configure(state='normal')
        self._cafe_review_text.delete('1.0', 'end')
        self._cafe_review_text.configure(state='disabled')

    def _cafe_review_inspect(self) -> None:
        self._cafe_review_clear()
        try:
            if self._notice_draft is None or self._notice_signature != (
                    self._notice_when.get(), self._notice_topic.get()):
                raise ValueError('084 공지 초안을 먼저 새로 생성해야 합니다.')
            current = make_prebroadcast_notice(
                self.settings, parse_reference(self._notice_when.get()), self._notice_topic.get())
            if current != self._notice_draft or self._notice_text.get('1.0', 'end-1c') != current.text:
                raise ValueError('원본 공지나 현재 설정이 변경됐습니다. 084 초안을 다시 생성해야 합니다.')
            report = review_naver_cafe_official_link(current)
        except (ValueError, TypeError) as exc:
            self._cafe_review_status.set('087 사전 검토 거부 · ' + str(exc) + ' · 미게시')
            return
        self._cafe_review_text.configure(state='normal')
        self._cafe_review_text.insert('1.0', report.to_report_json())
        self._cafe_review_text.configure(state='disabled')
        self._cafe_review_status.set(report.describe())

    def _build_discord_notice_link(self, tab) -> None:
        """085 preview-only contract, never Discord login or delivery."""
        ttk.Label(tab, text='085 디스코드 공지 연결 모의 (완전 오프라인)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='먼저 「방송 전 공지 초안」 탭에서 문구를 생성하세요. '
                  '디스코드 채널/봇 토큰/웹훅을 입력받지 않고, 게시 가능한 연결을 만들지 않습니다. '
                  '방송 플랫폼 선택은 디스코드 채널 선택과 무관합니다.',
                  wraplength=735).pack(anchor='w', pady=5)
        ttk.Button(tab, text='디스코드 메시지 형식 수동 점검 (접속·전송 없음)',
                   command=self._discord_notice_inspect).pack(anchor='w', pady=8)
        self._discord_notice_status = tk.StringVar(value='085 미검사 · 채널/인증 없음 · 미게시')
        ttk.Label(tab, textvariable=self._discord_notice_status,
                  wraplength=735).pack(anchor='w', pady=4)
        self._discord_notice_text = tk.Text(tab, height=16, wrap='word', state='disabled')
        self._discord_notice_text.pack(fill='both', expand=True, pady=7)

    def _discord_notice_clear(self) -> None:
        self._discord_notice_status.set('085 원본 입력/설정 변경 · 이전 점검 무효 · 미게시')
        self._discord_notice_text.configure(state='normal')
        self._discord_notice_text.delete('1.0', 'end')
        self._discord_notice_text.configure(state='disabled')
        if hasattr(self, '_notice_post_status'):
            self._notice_post_clear()

    def _discord_notice_inspect(self) -> None:
        self._discord_notice_clear()
        try:
            if self._notice_draft is None or self._notice_signature != (
                    self._notice_when.get(), self._notice_topic.get()):
                raise ValueError('084 공지 초안을 먼저 새로 생성해야 합니다.')
            # Check the entire current settings snapshot, not just the text
            # widget, to catch direct changes before the save callback runs.
            current = make_prebroadcast_notice(
                self.settings, parse_reference(self._notice_when.get()), self._notice_topic.get())
            if current != self._notice_draft or self._notice_text.get('1.0', 'end-1c') != current.text:
                raise ValueError('초안/설정이 변경됐습니다. 084 초안을 다시 생성하세요.')
            preview = prepare_discord_notice_dry_run(current)
        except (ValueError, TypeError) as exc:
            self._discord_notice_status.set('085 연결 형식 검사 거부 · ' + str(exc) + ' · 미게시')
            return
        self._discord_notice_text.configure(state='normal')
        self._discord_notice_text.insert('1.0', preview.to_preview_json())
        self._discord_notice_text.configure(state='disabled')
        self._discord_notice_status.set(preview.describe())

    def _build_notice_post_rehearsal(self, tab) -> None:
        """086 manual local display only: no Discord API or broadcast start."""
        self._notice_post_rehearsal = OfflineNoticePostingRehearsal()
        ttk.Label(tab, text='086 방송 시작 공지 자동 게시 · 오프라인 화면 모의 시험',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='먼저 081 일정에 맞춰 082 가상 방송 시작을 수동 실행하고, '
                  '084 공지 초안을 같은 KST 시작 시각으로 생성하세요. '
                  '이 탭은 검토용 문구를 화면에 표시할 뿐 Discord 계정·채널·게시·예약·'
                  'OBS 연결은 없습니다. 같은 시각의 중복 가상 표시만 메모리에서 차단합니다.',
                  wraplength=735).pack(anchor='w', pady=5)
        ttk.Button(tab, text='가상 게시 조건 수동 확인 (실제 게시 불가)',
                   command=self._notice_post_inspect).pack(anchor='w', pady=4)
        ttk.Button(tab, text='공지 화면에 가상 표시 (실제 게시 불가)',
                   command=self._notice_post_simulate).pack(anchor='w', pady=4)
        self._notice_post_status = tk.StringVar(value='086 미검사 · 실제 게시/예약 불가')
        ttk.Label(tab, textvariable=self._notice_post_status, wraplength=735).pack(anchor='w', pady=5)
        self._notice_post_text = tk.Text(tab, height=14, wrap='word', state='disabled')
        self._notice_post_text.pack(fill='both', expand=True, pady=7)

    def _notice_post_clear(self) -> None:
        self._notice_post_status.set('086 입력/설정 변경 · 이전 화면 결과 무효 · 실제 게시 없음')
        self._notice_post_text.configure(state='normal')
        self._notice_post_text.delete('1.0', 'end')
        self._notice_post_text.configure(state='disabled')

    def _notice_post_current(self):
        # Fail closed if 084 GUI text, schedule fields, or settings changed
        # since the draft was generated. The in-memory seen ledger is retained.
        if self._notice_draft is None or self._notice_signature != (
                self._notice_when.get(), self._notice_topic.get()):
            raise ValueError('084 공지 초안을 다시 생성해야 합니다.')
        current = make_prebroadcast_notice(
            self.settings, parse_reference(self._notice_when.get()), self._notice_topic.get())
        if (current != self._notice_draft
                or self._notice_text.get('1.0', 'end-1c') != current.text):
            raise ValueError('공지 내용 또는 설정이 바뀌었습니다. 084 초안을 다시 생성하세요.')
        return current

    def _notice_post_inspect(self) -> None:
        self._notice_post_clear()
        try:
            decision = self._notice_post_rehearsal.inspect(
                self._notice_post_current(), self._start_control, self.settings)
            self._notice_post_status.set(decision.describe())
        except (ValueError, TypeError) as exc:
            self._notice_post_status.set('086 조건 검사 거부 · ' + str(exc) + ' · 실제 게시 없음')

    def _notice_post_simulate(self) -> None:
        self._notice_post_clear()
        try:
            draft = self._notice_post_current()
            def show_local(text: str) -> None:
                self._notice_post_text.configure(state='normal')
                try:
                    self._notice_post_text.insert('1.0', text)
                finally:
                    self._notice_post_text.configure(state='disabled')
            result = self._notice_post_rehearsal.simulate_display(
                draft, self._start_control, self.settings, show_local=show_local)
            self._notice_post_status.set(result.describe())
        except (ValueError, TypeError) as exc:
            self._notice_post_status.set('086 화면 모의 거부 · ' + str(exc) + ' · 실제 게시 없음')


    def _build_past_broadcast_memory(self, tab) -> None:
        ttk.Label(tab, text='092 과거 방송 기억 카드 · 운영자 수동 선택 / 실제 AI 기억 아님',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text='091단계 가상 기록 JSON만 직접 골라 읽습니다. 자동 스캔·수집·AI 검색·다음 방송 전송 없음. 개인/비밀정보 입력 금지.',
                  wraplength=720).pack(anchor='w', pady=4)
        self._past_memory = OfflinePastBroadcastMemory()
        self._past_memory_include_chat = tk.BooleanVar(value=False)
        self._past_memory_selected = tk.StringVar(value='')
        ttk.Checkbutton(tab, text='모의 채팅 문구도 기억 카드에 포함 (기본 OFF)',
                        variable=self._past_memory_include_chat).pack(anchor='w', pady=3)
        tools = ttk.Frame(tab)
        tools.pack(fill='x', pady=5)
        ttk.Button(tools, text='091 가상 회차 JSON 직접 선택', command=self._past_memory_import).pack(side='left', padx=3)
        ttk.Button(tools, text='기억 카드 수동 저장', command=self._past_memory_export).pack(side='left', padx=3)
        ttk.Button(tools, text='기억 카드 파일 검증 불러오기', command=self._past_memory_load).pack(side='left', padx=3)
        line = ttk.Frame(tab)
        line.pack(fill='x', pady=4)
        ttk.Label(line, text='카드 선택').pack(side='left')
        self._past_memory_combo = ttk.Combobox(line, textvariable=self._past_memory_selected,
                                                values=(), state='readonly', width=50)
        self._past_memory_combo.pack(side='left', padx=5)
        ttk.Button(line, text='선택 카드 삭제', command=self._past_memory_remove).pack(side='left', padx=3)
        self._past_memory_status = tk.StringVar(value='092 대기 · 자동 저장·검색·실제 방송 접근 없음')
        ttk.Label(tab, textvariable=self._past_memory_status, wraplength=720).pack(anchor='w', pady=4)
        self._past_memory_text = tk.Text(tab, height=14, wrap='word', state='disabled')
        self._past_memory_text.pack(fill='both', expand=True)
        self._past_memory_refresh('092 운영자 직접 선택만 · 실제 AI 장기기억 아님')

    def _past_memory_refresh(self, status: str) -> None:
        if hasattr(self, "_memory_recall"):
            self._memory_recall_demo = ''
            self._memory_recall = OfflineMemoryRecall(self._past_memory)
            self._memory_recall_refresh("092 기억 변경/검토 · 093 검색 결과 무효화")
        cards = self._past_memory.cards
        values = tuple(f'{i + 1}. {card.session_label}' for i, card in enumerate(cards))
        self._past_memory_combo.configure(values=values)
        self._past_memory_selected.set('')
        self._past_memory_status.set(f'{status} · 기억 카드 {len(cards)}개 · 실제 방송 미검증')
        self._past_memory_text.configure(state='normal')
        self._past_memory_text.delete('1.0', 'end')
        for i, card in enumerate(cards, 1):
            self._past_memory_text.insert('end', f'[{i}] {card.session_label} · 가상 문구 {len(card.excerpts)}건 · 모의 채팅 포함: {card.includes_mock_chat}\n')
            for excerpt in card.excerpts:
                self._past_memory_text.insert('end', f'  - {excerpt}\n')
        self._past_memory_text.configure(state='disabled')

    def _past_memory_import(self) -> None:
        source = filedialog.askopenfilename(title='091 가상 방송 기록 JSON 직접 선택',
                                            filetypes=[('JSON', '*.json')])
        if not source:
            self._past_memory_refresh('092 선택 취소 · 기억 변경 없음')
            return
        try:
            journal = OfflineBroadcastJournal.load_json(Path(source))
            self._past_memory.add_journal(journal, include_mock_chat=self._past_memory_include_chat.get())
            self._past_memory_refresh('092 검증된 가상 회차를 기억 카드로 수동 추가')
        except (OSError, ValueError, TypeError) as exc:
            self._past_memory_refresh('092 가져오기 거부: ' + str(exc))

    def _past_memory_remove(self) -> None:
        selected = self._past_memory_selected.get()
        values = self._past_memory_combo.cget('values')
        if not selected or selected not in values:
            self._past_memory_status.set('092 먼저 삭제할 기억 카드를 선택하세요.')
            return
        if not messagebox.askyesno('가상 기억 카드 삭제', '선택한 카드의 메모리 기록을 지울까요? 저장한 파일은 수정되지 않습니다.'):
            self._past_memory_status.set('092 삭제 취소 · 기존 기억 보존')
            return
        self._past_memory.remove_card(values.index(selected))
        self._past_memory_refresh('092 운영자 요청으로 기억 카드 삭제')

    def _past_memory_export(self) -> None:
        target = filedialog.asksaveasfilename(title='가상 기억 카드 JSON 수동 저장',
                                              defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not target:
            self._past_memory_refresh('092 저장 취소 · 파일 변경 없음')
            return
        try:
            self._past_memory.export_json(Path(target))
            self._past_memory_refresh('092 운영자가 지정한 로컬 JSON에 수동 저장 · 덮어쓰기 없음')
        except (OSError, ValueError, TypeError) as exc:
            self._past_memory_refresh('092 저장 실패: ' + str(exc))

    def _past_memory_load(self) -> None:
        source = filedialog.askopenfilename(title='가상 기억 카드 JSON 수동 검증 불러오기',
                                            filetypes=[('JSON', '*.json')])
        if not source:
            self._past_memory_refresh('092 읽기 취소 · 기존 기억 유지')
            return
        try:
            restored = OfflinePastBroadcastMemory.load_json(Path(source))
            if self._past_memory.cards and not messagebox.askyesno(
                    '기억 카드 교체', '기존 가상 기억 카드를 새 파일 내용으로 바꿀까요?'):
                self._past_memory_status.set('092 교체 취소 · 기존 기억 유지')
                return
            self._past_memory = restored
            self._past_memory_refresh('092 검증된 가상 기억 파일 수동 불러오기 완료')
        except (OSError, ValueError, TypeError) as exc:
            self._past_memory_refresh('092 파일 읽기 거부: ' + str(exc))

    def _build_program_recovery(self, tab) -> None:
        ttk.Label(tab, text='094 프로그램 오류 안전 복구 · 오프라인 모의 감사',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=7)
        ttk.Label(tab, text=('운영자 버튼으로 별도 가상 수신함에서 모의 오류를 주입합니다. '
                             '모의 메시지 보존 및 단일 복구만 확인합니다. 실제 OS/OBS/AI 복구 아님.'),
                  wraplength=720).pack(anchor='w', pady=5)
        ttk.Button(tab, text='094 오류→안전 복구→수동 재처리 모의 시험',
                   command=self._program_recovery_run).pack(anchor='w', pady=7)
        self._program_recovery_status = tk.StringVar(value='094 시험 대기 · 외부 프로그램·장치 연결 없음')
        ttk.Label(tab, textvariable=self._program_recovery_status, wraplength=720).pack(anchor='w')
        self._program_recovery_text = tk.Text(tab, height=15, wrap='word', state='disabled')
        self._program_recovery_text.pack(fill='both', expand=True, pady=8)

    def _program_recovery_run(self) -> None:
        self._program_recovery_text.configure(state='normal')
        self._program_recovery_text.delete('1.0', 'end')
        try:
            decisions = run_offline_program_recovery_audit()
            if len(decisions) != 4 or not decisions[1].resumed or decisions[1].reply_created:
                raise RecoveryDenied('모의 검사 상태가 예상과 달라 미통과 처리했습니다.')
        except (RecoveryDenied, ValueError, TypeError) as exc:
            self._program_recovery_status.set('094 모의 검사 미통과 · ' + str(exc))
        else:
            self._program_recovery_status.set('094 오프라인 모의 검사 통과 · 실제 프로그램 자동 복구 미검증')
            for index, result in enumerate(decisions, 1):
                self._program_recovery_text.insert('end', f'[{index}] {result.describe()}\n\n')
        finally:
            self._program_recovery_text.configure(state='disabled')

    def _build_broadcast_safety(self, tab) -> None:
        ttk.Label(tab, text='095 방송 중 이상 감지·안전 제어 · 오프라인 모의',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=7)
        ttk.Label(tab, text=('수동 버튼으로 새 가상 채팅 세션에서 정상/정체/연결 끊김/기록 손상을 시험합니다. '
                             '보류 상태는 실제 채팅·음성·OBS·방송을 차단하거나 제어하지 않습니다.'),
                  wraplength=720).pack(anchor='w', pady=4)
        ttk.Button(tab, text='095 안전 상태 통합 모의 감사 실행',
                   command=self._broadcast_safety_run).pack(anchor='w', pady=7)
        self._broadcast_safety_status = tk.StringVar(value='095 대기 · 실제 방송 상태 수집 없음')
        ttk.Label(tab, textvariable=self._broadcast_safety_status, wraplength=720).pack(anchor='w')
        self._broadcast_safety_text = tk.Text(tab, height=16, wrap='word', state='disabled')
        self._broadcast_safety_text.pack(fill='both', expand=True, pady=8)

    def _broadcast_safety_run(self) -> None:
        self._broadcast_safety_text.configure(state='normal')
        self._broadcast_safety_text.delete('1.0', 'end')
        try:
            outcomes = run_offline_broadcast_safety_audit()
            if len(outcomes) != 6:
                raise SafetyDenied('예상 검사 횟수가 일치하지 않습니다.')
            self._broadcast_safety_status.set('095 오프라인 6개 상태 감사 통과 · 실제 안전 제어 미검증')
            for name, outcome in outcomes:
                self._broadcast_safety_text.insert('end', f'[{name}]\n{outcome.describe()}\n\n')
        except (SafetyDenied, ValueError, TypeError) as exc:
            self._broadcast_safety_status.set('095 모의 검사 미통과 · ' + str(exc))
        finally:
            self._broadcast_safety_text.configure(state='disabled')

    def _build_operating_cost(self, tab) -> None:
        """096: manual non-persistent KRW calculator; no provider/OS/billing access."""
        ttk.Label(tab, text='096 API·서버·음성·전력 운영 비용 수동 계산',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text=('동일 기간의 사용량과 원화 단가를 직접 입력하세요. 빈칸은 무료가 아니라 미산정입니다. '
                             '현재 가격·실제 청구·사용량 자동 조회, 결제, 외부 연결, 파일 저장은 없습니다.'),
                  wraplength=720).pack(anchor='w', pady=3)
        frame = ttk.Frame(tab)
        frame.pack(anchor='w', pady=4)
        self._operating_cost_fields = {}
        for row, (key, name, unit, _divisor) in enumerate(COST_FIELDS):
            ttk.Label(frame, text=name).grid(row=row, column=0, sticky='w', padx=5, pady=3)
            usage = tk.StringVar(value='')
            rate = tk.StringVar(value='')
            self._operating_cost_fields[f'{key}_usage'] = usage
            self._operating_cost_fields[f'{key}_rate'] = rate
            ttk.Entry(frame, textvariable=usage, width=15).grid(row=row, column=1, padx=5)
            ttk.Label(frame, text=f'{unit}당 원화 단가').grid(row=row, column=2, padx=5)
            ttk.Entry(frame, textvariable=rate, width=15).grid(row=row, column=3, padx=5)
        ttk.Label(frame, text='사용량 (위 왼쪽 입력란)').grid(row=len(COST_FIELDS), column=1, sticky='w')
        ttk.Label(frame, text='단가 (위 오른쪽 입력란)').grid(row=len(COST_FIELDS), column=3, sticky='w')
        budget_line = ttk.Frame(tab)
        budget_line.pack(anchor='w', pady=5)
        ttk.Label(budget_line, text='동일 기간 예산(원, 선택)').pack(side='left')
        self._operating_cost_budget = tk.StringVar(value='')
        ttk.Entry(budget_line, textvariable=self._operating_cost_budget, width=18).pack(side='left', padx=8)
        ttk.Button(budget_line, text='수동 비용 점검', command=self._operating_cost_run).pack(side='left')
        self._operating_cost_status = tk.StringVar(value='096 대기 · 미입력 금액 0원으로 간주하지 않음')
        ttk.Label(tab, textvariable=self._operating_cost_status, wraplength=720).pack(anchor='w', pady=3)
        self._operating_cost_text = tk.Text(tab, height=9, wrap='word', state='disabled')
        self._operating_cost_text.pack(fill='both', expand=True, pady=4)
        for variable in (*self._operating_cost_fields.values(), self._operating_cost_budget):
            variable.trace_add('write', self._operating_cost_changed)

    def _operating_cost_changed(self, *_args) -> None:
        self._operating_cost_status.set('096 입력 변경 · 이전 예상 비용 무효화 · 다시 수동 점검 필요')
        self._operating_cost_text.configure(state='normal')
        self._operating_cost_text.delete('1.0', 'end')
        self._operating_cost_text.configure(state='disabled')

    def _operating_cost_run(self) -> None:
        self._operating_cost_text.configure(state='normal')
        self._operating_cost_text.delete('1.0', 'end')
        try:
            report = estimate_operating_cost(
                {key: var.get() for key, var in self._operating_cost_fields.items()},
                self._operating_cost_budget.get(),
            )
        except CostInputError as exc:
            self._operating_cost_status.set('096 계산 거부 · ' + str(exc))
        else:
            self._operating_cost_status.set('096 수동 추정 완료 · 실제 청구·예산 승인 미검증')
            self._operating_cost_text.insert('1.0', report.describe())
        finally:
            self._operating_cost_text.configure(state='disabled')

    def _build_unattended_endurance(self, tab) -> None:
        """097: run only when clicked, isolated synchronous deterministic virtual audit."""
        ttk.Label(tab, text='097 장시간 무인 방송 오프라인 가속 안정성 검사',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text=('수동 버튼 1회 = 가상 1시간(3,601틱) 또는 3시간(10,801틱)을 즉시 시뮬레이션합니다. '
                             '실제 1~3시간 기다리거나 방송을 시작하지 않습니다. '
                             '실제 Windows·OBS·TTS·아바타·시스템 메모리 누수 검사 아님.'),
                  wraplength=720).pack(anchor='w', pady=5)
        controls = ttk.Frame(tab)
        controls.pack(anchor='w', pady=4)
        ttk.Label(controls, text='가상 실행 길이').pack(side='left', padx=4)
        self._unattended_hours = tk.StringVar(value='1')
        ttk.Combobox(controls, textvariable=self._unattended_hours, values=('1', '3'),
                     state='readonly', width=8).pack(side='left', padx=4)
        ttk.Button(controls, text='097 독립 장시간 모의 검사',
                   command=self._unattended_run).pack(side='left', padx=5)
        self._unattended_status = tk.StringVar(value='097 대기 · 운영자가 직접 수동 실행 / 실제 방송 없음')
        ttk.Label(tab, textvariable=self._unattended_status, wraplength=720).pack(anchor='w', pady=6)
        self._unattended_text = tk.Text(tab, height=15, wrap='word', state='disabled')
        self._unattended_text.pack(fill='both', expand=True, pady=5)
        self._unattended_hours.trace_add('write', self._unattended_changed)

    def _unattended_changed(self, *_args) -> None:
        self._unattended_status.set('097 길이 변경 · 이전 모의 검증 결과 무효화')
        self._unattended_text.configure(state='normal')
        self._unattended_text.delete('1.0', 'end')
        self._unattended_text.configure(state='disabled')

    def _unattended_run(self) -> None:
        self._unattended_text.configure(state='normal')
        self._unattended_text.delete('1.0', 'end')
        try:
            raw = self._unattended_hours.get()
            if raw not in ('1', '3'):
                raise ValueError('1시간·3시간 중 선택하세요.')
            report = run_virtual_unattended_endurance(int(raw))
            self._unattended_status.set('097 가상 검사 ' + ('통과' if report.passed else '미통과')
                                        + ' · 실제 무인 방송 안정성은 미검증')
            self._unattended_text.insert('1.0', report.describe())
            self._unattended_text.insert('end', '\n가상 확인 표본(초 / 접수 / 응답 / 대기):\n')
            for sample in report.samples:
                self._unattended_text.insert('end',
                    f'{sample.virtual_second} / {sample.accepted} / {sample.responded} / {sample.pending}\n')
        except (ValueError, TypeError, RuntimeError) as exc:
            self._unattended_status.set('097 모의 검사 미통과 · ' + str(exc))
        finally:
            self._unattended_text.configure(state='disabled')

    def _build_multisession_stability(self, tab) -> None:
        """098: bounded sequential audits, never actual sessions or auto scheduling."""
        ttk.Label(tab, text='098 여러 회차 방송 반복 안정성 (가속 오프라인 모의)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text=('회차마다 새 독립 097 가상 세션을 실행합니다. 실제 방송·OS 시간 대기·'
                             'Windows·OBS·TTS·AI·아바타 작동 확인은 아닙니다. '
                             '미통과 회차를 자동 재시도하지 않습니다.'), wraplength=720).pack(anchor='w', pady=4)
        controls = ttk.Frame(tab)
        controls.pack(anchor='w', pady=4)
        ttk.Label(controls, text='반복 회차').pack(side='left', padx=3)
        self._multisession_rounds = tk.StringVar(value='3')
        ttk.Combobox(controls, textvariable=self._multisession_rounds,
                     values=('3', '5', '10'), state='readonly', width=7).pack(side='left', padx=3)
        ttk.Label(controls, text='회차당 가상 시간').pack(side='left', padx=3)
        self._multisession_hours = tk.StringVar(value='1')
        ttk.Combobox(controls, textvariable=self._multisession_hours,
                     values=('1', '3'), state='readonly', width=7).pack(side='left', padx=3)
        ttk.Button(controls, text='098 수동 다회차 검사',
                   command=self._multisession_run).pack(side='left', padx=6)
        self._multisession_status = tk.StringVar(value='098 대기 · 실제 방송 없음')
        ttk.Label(tab, textvariable=self._multisession_status, wraplength=720).pack(anchor='w', pady=5)
        self._multisession_text = tk.Text(tab, height=16, state='disabled', wrap='word')
        self._multisession_text.pack(fill='both', expand=True, pady=5)
        self._multisession_rounds.trace_add('write', self._multisession_changed)
        self._multisession_hours.trace_add('write', self._multisession_changed)

    def _multisession_changed(self, *_args) -> None:
        self._multisession_status.set('098 설정 변경 · 이전 모의 결과 무효화')
        self._multisession_text.configure(state='normal')
        self._multisession_text.delete('1.0', 'end')
        self._multisession_text.configure(state='disabled')

    def _multisession_run(self) -> None:
        self._multisession_text.configure(state='normal')
        self._multisession_text.delete('1.0', 'end')
        try:
            number = self._multisession_rounds.get()
            hours = self._multisession_hours.get()
            if number not in ('3', '5', '10') or hours not in ('1', '3'):
                raise ValueError('반복 회차 3/5/10 및 가상 시간 1/3만 선택합니다.')
            result = run_virtual_multisession_stability(int(number), int(hours))
            self._multisession_status.set('098 다회차 모의 검사 ' +
                ('통과' if result.passed else '미통과') + ' · 실제 반복 방송 미검증')
            self._multisession_text.insert('1.0', result.describe())
        except (ValueError, TypeError, RuntimeError) as exc:
            self._multisession_status.set('098 다회차 모의 검사 미통과 · ' + str(exc))
        finally:
            self._multisession_text.configure(state='disabled')

    def _build_operator_maintenance(self, tab) -> None:
        """099: explicit operator-only checklist, never release authorization."""
        ttk.Label(tab, text='099 운영자 점검 및 유지보수 (수동 자기보고)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text=('선택한 항목의 상태는 운영자 입력일 뿐, Windows·OBS·음성·아바타의 실제 검증이나 '
                             '방송 허가를 의미하지 않습니다. PC/계정/로그는 자동 조사하지 않습니다.'),
                  wraplength=720).pack(anchor='w', pady=4)
        self._maintenance = OfflineOperatorMaintenance()
        controls = ttk.Frame(tab)
        controls.pack(fill='x', pady=5)
        self._maintenance_selected = tk.StringVar(value=CHECKS[0][0])
        self._maintenance_mark = tk.StringVar(value=STATUSES[0])
        self._maintenance_labels = {key: label for key, label in CHECKS}
        self._maintenance_display = {label: key for key, label in CHECKS}
        self._maintenance_label = tk.StringVar(value=CHECKS[0][1])
        ttk.Label(controls, text='점검 항목').pack(side='left', padx=3)
        self._maintenance_combo = ttk.Combobox(controls, textvariable=self._maintenance_label,
                   values=tuple(label for _, label in CHECKS), width=45, state='readonly')
        self._maintenance_combo.pack(side='left', padx=3)
        self._maintenance_combo.bind('<<ComboboxSelected>>', self._maintenance_item_selected)
        ttk.Label(controls, text='운영자 상태').pack(side='left', padx=3)
        ttk.Combobox(controls, textvariable=self._maintenance_mark,
                     values=STATUSES, state='readonly', width=16).pack(side='left', padx=3)
        commands = ttk.Frame(tab)
        commands.pack(anchor='w', pady=5)
        ttk.Button(commands, text='선택 항목 수동 기록', command=self._maintenance_record).pack(side='left', padx=4)
        ttk.Button(commands, text='모두 대기로 초기화', command=self._maintenance_reset).pack(side='left', padx=4)
        ttk.Button(commands, text='점검표 수동 JSON 저장', command=self._maintenance_export).pack(side='left', padx=4)
        self._maintenance_status = tk.StringVar(value='099 운영자 점검 대기 · 실제 방송/최종 승인 미검증')
        ttk.Label(tab, textvariable=self._maintenance_status, wraplength=720).pack(anchor='w', pady=4)
        self._maintenance_text = tk.Text(tab, height=18, state='disabled', wrap='word')
        self._maintenance_text.pack(fill='both', expand=True)
        self._maintenance_render()

    def _maintenance_render(self) -> None:
        self._maintenance_text.configure(state='normal')
        self._maintenance_text.delete('1.0', 'end')
        self._maintenance_text.insert('1.0', self._maintenance.report().describe())
        self._maintenance_text.configure(state='disabled')

    def _maintenance_item_selected(self, _event=None) -> None:
        label = self._maintenance_label.get()
        self._maintenance_mark.set(next((x.status for x in self._maintenance.report().items
                                         if x.key == self._maintenance_display.get(label)), STATUSES[0]))

    def _maintenance_record(self) -> None:
        try:
            key = self._maintenance_display[self._maintenance_label.get()]
            self._maintenance.set_status(key, self._maintenance_mark.get())
            self._maintenance_status.set('099 운영자 입력 기록 · 실제 검증/승인 아님')
        except (KeyError, ValueError, TypeError) as exc:
            self._maintenance_status.set('099 기록 실패 · ' + str(exc))
        self._maintenance_render()

    def _maintenance_reset(self) -> None:
        self._maintenance.clear()
        self._maintenance_mark.set(STATUSES[0])
        self._maintenance_status.set('099 점검 입력 초기화 · 최종 승인 대기')
        self._maintenance_render()

    def _maintenance_export(self) -> None:
        chosen = filedialog.asksaveasfilename(parent=self, title='수동 점검표 저장 (기존 파일 덮어쓰기 금지)',
                                  defaultextension='.json', filetypes=[('JSON 파일', '*.json')])
        if not chosen:
            self._maintenance_status.set('099 파일 저장 취소 · 기존 자료 변경 없음')
            return
        try:
            export_maintenance_snapshot(self._maintenance.report(), Path(chosen))
            self._maintenance_status.set('099 점검표 저장 완료 · 운영자 자기보고만 포함 / 승인 아님')
        except (ValueError, TypeError, OSError) as exc:
            self._maintenance_status.set('099 저장 실패 · ' + str(exc))

    def _build_final_acceptance(self, tab) -> None:
        """100: review bundled *project* evidence only when clicked; never sign off."""
        ttk.Label(tab, text='100 최종 기능 검수 자료 (사용자 승인 대기)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text=('운영자가 검수 증빙을 살펴볼 수 있는 비승인 화면입니다. '
                              '버튼을 누를 때 동봉된 프로젝트 문서/기존 로그 6개만 검사하며, '
                              '테스트 재실행·Windows/OBS/음성/아바타 실제 검증을 뜻하지 않습니다. '
                              '사용자 PC·계정·환경 자료를 수집하지 않습니다.'),
                  wraplength=720).pack(anchor='w', pady=4)
        actions = ttk.Frame(tab)
        actions.pack(fill='x', pady=4)
        ttk.Button(actions, text='동봉 자료 수동 최종 검수',
                   command=self._final_acceptance_inspect).pack(side='left', padx=4)
        ttk.Button(actions, text='검수 자료 JSON 수동 저장 (승인 아님)',
                   command=self._final_acceptance_export).pack(side='left', padx=4)
        self._final_acceptance_report = build_final_acceptance(
            operator_report=self._maintenance.report())
        self._final_acceptance_status = tk.StringVar(value='100 자료 검토 전 · 출시 차단/승인 대기')
        ttk.Label(tab, textvariable=self._final_acceptance_status,
                  wraplength=720).pack(anchor='w', pady=4)
        self._final_acceptance_text = tk.Text(tab, height=21, wrap='word', state='disabled')
        self._final_acceptance_text.pack(fill='both', expand=True)
        self._final_acceptance_render()

    def _final_acceptance_render(self) -> None:
        self._final_acceptance_text.configure(state='normal')
        self._final_acceptance_text.delete('1.0', 'end')
        self._final_acceptance_text.insert('1.0', self._final_acceptance_report.describe())
        self._final_acceptance_text.configure(state='disabled')

    def _final_acceptance_inspect(self) -> None:
        try:
            # Only bundled six known project paths; no user file scans or device info.
            root = bundled_project_root()  # PyInstaller _MEIPASS or source root
            archived, roadmap_pending = inspect_bundled_project(root)
            self._final_acceptance_report = build_final_acceptance(
                archived, roadmap_pending, self._maintenance.report())
            self._final_acceptance_status.set('100 동봉 파일 검토 완료 · 실제 방송 미검증 · 출시 차단/사용자 승인 대기')
        except (OSError, ValueError, TypeError) as exc:
            self._final_acceptance_report = build_final_acceptance(
                operator_report=self._maintenance.report())
            self._final_acceptance_status.set('100 검수 미완료 · ' + str(exc))
        self._final_acceptance_render()

    def _final_acceptance_export(self) -> None:
        choice = filedialog.asksaveasfilename(
            parent=self, title='최종 검수 자료만 저장 (실제 승인 아님)',
            defaultextension='.json', filetypes=[('JSON 파일', '*.json')])
        if not choice:
            self._final_acceptance_status.set('100 저장 취소 · 기존 자료 유지/승인 대기')
            return
        try:
            # Refresh claims if 099 checklist changed: never copy stale statuses.
            self._final_acceptance_report = build_final_acceptance(
                self._final_acceptance_report.archived,
                self._final_acceptance_report.original_roadmap_pending,
                self._maintenance.report())
            export_final_acceptance(self._final_acceptance_report, Path(choice))
            self._final_acceptance_status.set('100 검수 자료 저장 완료 · 승인 아님/방송 허가 없음')
        except (OSError, ValueError, TypeError) as exc:
            self._final_acceptance_status.set('100 저장 실패 · ' + str(exc))
        self._final_acceptance_render()

    def _build_memory_recall(self, tab) -> None:
        ttk.Label(tab, text='093 가상 기억 검색 → 다음 가상 회차 참고 메모',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text='092 수동 기억 카드를 검색합니다. 선택한 기억 한 건의 참고 문구만 준비합니다. '
                  '실제 AI·채팅·음성·방송으로 전달하지 않습니다.', wraplength=720).pack(anchor='w', pady=4)
        self._memory_recall = OfflineMemoryRecall(self._past_memory)
        self._memory_recall_query = tk.StringVar(value='')
        self._memory_recall_selected = tk.StringVar(value='')
        self._memory_recall_next_question = tk.StringVar(value='')
        self._memory_recall_demo = ''
        self._memory_recall_status = tk.StringVar(value='093 대기 · 수동 검색 전용')
        self._memory_recall_query.trace_add('write', self._memory_recall_query_changed)
        self._memory_recall_next_question.trace_add('write', self._memory_recall_question_changed)
        query_line = ttk.Frame(tab)
        query_line.pack(fill='x', pady=3)
        ttk.Label(query_line, text='검색어').pack(side='left')
        ttk.Entry(query_line, textvariable=self._memory_recall_query, width=35).pack(side='left', padx=5)
        ttk.Button(query_line, text='수동 검색', command=self._memory_recall_search).pack(side='left', padx=3)
        ttk.Button(query_line, text='검색·연결 초기화', command=self._memory_recall_clear).pack(side='left', padx=3)
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text='검색 결과').pack(side='left')
        self._memory_recall_combo = ttk.Combobox(row, textvariable=self._memory_recall_selected,
                                                 values=(), width=46, state='readonly')
        self._memory_recall_combo.pack(side='left', padx=5)
        ttk.Button(row, text='선택 기억을 다음 가상 회차 참고로 준비',
                   command=self._memory_recall_prepare).pack(side='left', padx=4)
        demo_row = ttk.Frame(tab)
        demo_row.pack(fill='x', pady=4)
        ttk.Label(demo_row, text='다음 가상 회차 질문').pack(side='left')
        ttk.Entry(demo_row, textvariable=self._memory_recall_next_question, width=33).pack(side='left', padx=5)
        ttk.Button(demo_row, text='기존 모의 답변으로 시험', command=self._memory_recall_rehearse).pack(side='left', padx=4)
        ttk.Label(tab, textvariable=self._memory_recall_status, wraplength=720).pack(anchor='w', pady=4)
        self._memory_recall_text = tk.Text(tab, height=13, wrap='word', state='disabled')
        self._memory_recall_text.pack(fill='both', expand=True)

    def _memory_recall_refresh(self, status: str) -> None:
        hits = self._memory_recall.hits
        labels = tuple(f'{i + 1}. {hit.session_label}' for i, hit in enumerate(hits))
        self._memory_recall_combo.configure(values=labels)
        self._memory_recall_selected.set('')
        self._memory_recall_status.set(status + ' · 실제 AI/방송 연결 없음')
        self._memory_recall_text.configure(state='normal')
        self._memory_recall_text.delete('1.0', 'end')
        for i, hit in enumerate(hits, 1):
            self._memory_recall_text.insert('end', f'[{i}] {hit.session_label} · 일치 문구 {len(hit.matching_excerpts)}건\n')
        context = self._memory_recall.context
        if context is not None:
            self._memory_recall_text.insert('end', '\n' + context.preview() + '\n')
            if self._memory_recall_demo:
                self._memory_recall_text.insert('end', '\n[기존 무네트워크 모의 답변 포트]\n' + self._memory_recall_demo + '\n')
        self._memory_recall_text.configure(state='disabled')

    def _memory_recall_query_changed(self, *_unused) -> None:
        self._memory_recall_demo = ''
        self._memory_recall.clear()
        self._memory_recall_refresh('093 검색어 변경 · 이전 검색·연결 무효화')

    def _memory_recall_question_changed(self, *_unused) -> None:
        self._memory_recall_demo = ''
        self._memory_recall_refresh('093 다음 가상 질문 변경 · 이전 모의 답변 무효화')

    def _memory_recall_search(self) -> None:
        self._memory_recall_demo = ''
        try:
            self._memory_recall.search(self._memory_recall_query.get())
            self._memory_recall_refresh('093 수동 검색 결과')
        except (ValueError, TypeError) as exc:
            self._memory_recall.clear()
            self._memory_recall_refresh('093 검색 거부: ' + str(exc))

    def _memory_recall_prepare(self) -> None:
        self._memory_recall_demo = ''
        values = tuple(self._memory_recall_combo.cget('values'))
        selected = self._memory_recall_selected.get()
        try:
            if not selected or selected not in values:
                raise ValueError('검색 결과에서 한 회차를 직접 선택하세요.')
            self._memory_recall.prepare_for_next_mock_session(values.index(selected))
            self._memory_recall_refresh('093 운영자 수동 선택 참고 메모 준비 · 전송/AI 입력 없음')
        except (ValueError, TypeError) as exc:
            self._memory_recall_refresh('093 연결 거부: ' + str(exc))

    def _memory_recall_rehearse(self) -> None:
        self._memory_recall_demo = ''
        try:
            self._memory_recall_demo = self._memory_recall.rehearse_next_mock_reply(
                self._memory_recall_next_question.get())
            self._memory_recall_refresh('093 기존 무네트워크 모의 답변으로 다음 가상 회차 시험 완료')
        except (ValueError, TypeError) as exc:
            self._memory_recall_refresh('093 다음 가상 회차 모의 거부: ' + str(exc))

    def _memory_recall_clear(self) -> None:
        self._memory_recall_demo = ''
        self._memory_recall.clear()
        self._memory_recall_refresh('093 운영자 요청으로 검색·준비 결과 삭제')

    def _build_broadcast_journal(self, tab) -> None:
        ttk.Label(tab, text='091 방송 대화·사건 기록 · 수동 모의 입력·수동 JSON 저장만',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=5)
        ttk.Label(tab, text='실제 채팅 수집·녹음·방송 통계·장기기억 검색 없음. 모의 닉네임/내용에도 개인정보를 입력하지 마세요.',
                  wraplength=720).pack(anchor='w', pady=4)
        self._journal = OfflineBroadcastJournal()
        self._journal_label = tk.StringVar(value='가상 방송 회차')
        self._journal_kind = tk.StringVar(value=EVENT_KINDS[0])
        self._journal_note = tk.StringVar(value='')
        first = ttk.Frame(tab)
        first.pack(fill='x', pady=4)
        ttk.Label(first, text='가상 회차 이름').pack(side='left')
        ttk.Entry(first, textvariable=self._journal_label, width=24).pack(side='left', padx=5)
        ttk.Button(first, text='새 가상 회차 (메모리 초기화)', command=self._journal_reset).pack(side='left', padx=5)
        line = ttk.Frame(tab)
        line.pack(fill='x', pady=4)
        ttk.Combobox(line, textvariable=self._journal_kind, values=EVENT_KINDS,
                     state='readonly', width=18).pack(side='left')
        ttk.Entry(line, textvariable=self._journal_note, width=44).pack(side='left', padx=5)
        ttk.Button(line, text='가상 사건 추가', command=self._journal_add).pack(side='left')
        tools = ttk.Frame(tab)
        tools.pack(fill='x', pady=5)
        ttk.Button(tools, text='062 모의 채팅 수동 가져오기', command=self._journal_import_chats).pack(side='left', padx=3)
        ttk.Button(tools, text='JSON 수동 저장', command=self._journal_export).pack(side='left', padx=3)
        ttk.Button(tools, text='JSON 수동 검증 불러오기', command=self._journal_load).pack(side='left', padx=3)
        self._journal_status = tk.StringVar(value='091 가상 기록 0건 · 자동 수집·저장 없음')
        ttk.Label(tab, textvariable=self._journal_status, wraplength=720).pack(anchor='w', pady=4)
        self._journal_preview = tk.Text(tab, height=14, wrap='word', state='disabled')
        self._journal_preview.pack(fill='both', expand=True)
        self._journal_refresh('091 대기 · 실제 플랫폼·방송 기록 아님')

    def _journal_refresh(self, status: str) -> None:
        self._journal_status.set(f'{status} · 모의 기록 {len(self._journal.entries)}건 · 실제 방송 미검증')
        self._journal_preview.configure(state='normal')
        self._journal_preview.delete('1.0', 'end')
        for entry in self._journal.entries:
            self._journal_preview.insert('end', f'{entry.index}: {entry.kind} '
                                         f'{entry.platform} {entry.sender_mock} {entry.text}\n')
        self._journal_preview.configure(state='disabled')

    def _journal_reset(self) -> None:
        if self._journal.entries and not messagebox.askyesno(
                '미저장 가상 기록 초기화', '현재 메모리의 가상 기록이 사라집니다. 새 회차로 시작할까요?', parent=self):
            self._journal_refresh('091 초기화 취소 · 기존 기록 유지')
            return
        try:
            self._journal = OfflineBroadcastJournal(self._journal_label.get())
            self._journal_refresh('091 새 메모리 회차 · 이전 미저장 기록은 복구할 수 없음')
        except (ValueError, OSError) as exc:
            self._journal_refresh('091 새 회차 거부: ' + str(exc))

    def _journal_add(self) -> None:
        try:
            self._journal.add_mock_event(self._journal_kind.get(), self._journal_note.get())
            self._journal_note.set('')
            self._journal_refresh('091 운영자가 입력한 가상 사건만 추가')
        except ValueError as exc:
            self._journal_refresh('091 사건 추가 거부: ' + str(exc))

    def _journal_import_chats(self) -> None:
        try:
            count = self._journal.import_mock_chats(self._mock_receiver.snapshot())
            self._journal_refresh(f'091 운영자 요청으로 모의 채팅 {count}건 신규 가져옴')
        except ValueError as exc:
            self._journal_refresh('091 채팅 가져오기 거부: ' + str(exc))

    def _journal_export(self) -> None:
        target = filedialog.asksaveasfilename(parent=self, defaultextension='.json',
                                              filetypes=[('JSON', '*.json')])
        if not target:
            self._journal_refresh('091 저장 취소 · 파일 변경 없음')
            return
        try:
            if self._journal_label.get() != self._journal.session_label:
                raise ValueError('회차 이름이 바뀌었습니다. 새 회차 버튼으로 먼저 확정하세요.')
            from pathlib import Path
            self._journal.export_json(Path(target))
            self._journal_refresh('091 사용자가 지정한 JSON 파일에 수동 저장 · 덮어쓰기 없음')
        except (OSError, ValueError) as exc:
            self._journal_refresh('091 저장 실패: ' + str(exc))

    def _journal_load(self) -> None:
        target = filedialog.askopenfilename(parent=self, filetypes=[('JSON', '*.json')])
        if not target:
            self._journal_refresh('091 읽기 취소 · 기존 가상 기록 보존')
            return
        try:
            from pathlib import Path
            restored = OfflineBroadcastJournal.load_json(Path(target))
            self._journal = restored  # only replace after full integrity validation
            self._journal_label.set(restored.session_label)
            self._journal_refresh('091 사용자가 지정한 파일 검사·복구 완료 · 실제 방송 기록 아님')
        except (OSError, ValueError, TypeError) as exc:
            self._journal_refresh('091 파일 읽기 거부: ' + str(exc))

    def _build_automation_audit(self, tab) -> None:
        """090: isolated single-click offline integration only; NO real automation."""
        ttk.Label(tab, text='090 방송 자동화 전체 모의 감사 · 외부 송출/게시 불가',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        ttk.Label(tab, text='081 탭의 요일·시각 일정을 먼저 등록하세요. 아래 KST 시각을 직접 입력하고 '
                  '방송 설정에서 플랫폼 하나 이상·Windows 무료 음성을 명시적으로 선택해야 '
                  '077 무음 화면 문자열 검사를 수행할 수 있습니다. 3D/미정 아바타는 자동으로 2D로 바꾸지 않습니다. '
                  '기존 방송·채팅 세션을 사용하지 않으며 실제 시작, OBS, 게시, TTS 재생·파일 저장 없음.',
                  wraplength=735).pack(anchor='w', pady=5)
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=4)
        self._automation_audit_when = tk.StringVar(value='')
        self._automation_audit_topic = tk.StringVar(value='')
        ttk.Label(row, text='수동 KST 시각').pack(side='left')
        ttk.Entry(row, textvariable=self._automation_audit_when, width=20).pack(side='left', padx=5)
        ttk.Label(row, text='주제').pack(side='left', padx=(8, 0))
        ttk.Entry(row, textvariable=self._automation_audit_topic, width=24).pack(side='left', padx=5)
        self._automation_audit_when.trace_add('write', self._automation_audit_clear)
        self._automation_audit_topic.trace_add('write', self._automation_audit_clear)
        ttk.Button(tab, text='090 오프라인 시작·채팅·음성·화면·공지·종료 통합 감사',
                   command=self._automation_audit_run).pack(anchor='w', pady=5)
        self._automation_audit_status = tk.StringVar(value='090 미검사 · 실제 방송/공지/음성 없음')
        ttk.Label(tab, textvariable=self._automation_audit_status, wraplength=735).pack(anchor='w', pady=4)
        self._automation_audit_details = tk.Text(tab, height=8, wrap='word', state='disabled')
        self._automation_audit_details.pack(fill='x', pady=4)
        self._automation_audit_canvas = tk.Canvas(tab, width=640, height=360,
                                                   bg='#17223c', highlightthickness=0)
        self._automation_audit_canvas.pack(anchor='w', pady=4)
        self._automation_audit_canvas.create_text(320, 180,
            text='격리된 Canvas · 통합 감사 미실행 · 외부 방송 없음', fill='white')

    def _automation_audit_clear(self, *_args) -> None:
        if not hasattr(self, '_automation_audit_status'):
            return
        self._automation_audit_status.set('090 입력·일정·설정 변경 · 이전 통합 감사 무효 · 실제 방송 없음')
        self._automation_audit_details.configure(state='normal')
        self._automation_audit_details.delete('1.0', 'end')
        self._automation_audit_details.configure(state='disabled')
        self._automation_audit_canvas.delete('all')
        self._automation_audit_canvas.create_text(320, 180, text='이전 감사 무효 · 재검사 필요', fill='white')

    def _automation_audit_run(self) -> None:
        self._automation_audit_clear()
        try:
            # A separate Canvas and brand-new simulated controllers are used.
            report = run_offline_broadcast_automation_audit(
                self._schedule_draft, parse_reference(self._automation_audit_when.get()),
                self.settings, self._broadcast_scene_draft(), int(self._voice_volume.get()),
                self._automation_audit_canvas, topic=self._automation_audit_topic.get())
            lines = [f'{"통과" if item.ok else "실패"} · {item.name} · {item.detail}' for item in report.checks]
            self._automation_audit_status.set(report.describe())
        except (ValueError, TypeError, KeyError, tk.TclError) as exc:
            lines = ['입력·화면 초안 검증 거부 · ' + str(exc)]
            self._automation_audit_status.set('090 통합 모의 감사 미통과 · 실제 송출/게시 없음')
        self._automation_audit_details.configure(state='normal')
        self._automation_audit_details.insert('1.0', '\n'.join(lines))
        self._automation_audit_details.configure(state='disabled')

    def _full_cycle_audit_run(self) -> None:
        # Uses only a fresh isolated mock controller, never the operator's
        # in-progress stage 082 controller or any saved files.
        try:
            name = self._current_persona()['name']
            report = run_offline_full_cycle_audit(
                self._schedule_draft, parse_reference(self._schedule_reference.get()),
                self.settings, name)
            self._full_cycle_status.set(report.describe())
        except (ValueError, TypeError) as exc:
            self._full_cycle_status.set('083 오프라인 통합 감사 미통과 · ' + str(exc)
                                        + ' · 실제 송출 없음')

    def _schedule_input_changed(self, *_args) -> None:
        if hasattr(self, '_automation_audit_status'):
            self._automation_audit_clear()
        self._schedule_next.set('입력 변경 · 이전 예정 시각 계산 무효 · 방송 시작 없음')
        if hasattr(self, '_full_cycle_status'):
            self._full_cycle_status.set('083 입력 변경 · 이전 감사 무효 · 실제 방송 없음')
        if hasattr(self, '_start_control_status'):
            self._start_control_status.set('082 입력 변경 · 기존 판정 표시 무효 · 실제 방송 없음')

    def _schedule_refresh(self, message: str) -> None:
        if hasattr(self, '_automation_audit_status'):
            self._automation_audit_clear()
        self._start_control = OfflineStartController(self._schedule_draft)
        if hasattr(self, '_notice_post_status'):
            self._notice_post_clear()
        self._full_cycle_status.set('083 일정 변경 · 이전 통합 감사 무효 · 실제 송출 없음')
        self._start_control_status.set('082 일정 변경 · 가상 제어 기록 초기화 / 자동 실행 비활성')
        self._schedule_list.delete(0, 'end')
        for slot in self._schedule_draft.slots:
            self._schedule_list.insert('end', slot.label)
        self._schedule_next.set('일정 변경 · 다음 예정 시각 다시 계산 필요 / 자동 실행 없음')
        self._schedule_status.set(f'081 {message} · 초안 {len(self._schedule_draft.slots)}개 · '
                                  '실제 방송 자동 시작 비활성 · 최종 승인 대기')

    def _schedule_add(self) -> None:
        try:
            weekday = WEEKDAYS.index(self._schedule_weekday.get())
            draft = self._schedule_draft.add(weekday, self._schedule_start_time.get())
            self._schedule_draft = draft
            self._schedule_refresh('메모리 초안 추가 완료 (저장 안 됨)')
        except (ValueError, TypeError) as exc:
            self._schedule_status.set('081 일정 추가 거부 · ' + str(exc))

    def _schedule_remove(self) -> None:
        try:
            chosen = self._schedule_list.curselection()
            if len(chosen) != 1:
                raise ValueError('목록에서 제거할 일정 하나를 먼저 선택하세요.')
            slot = self._schedule_draft.slots[chosen[0]]
            self._schedule_draft = self._schedule_draft.remove(slot.weekday, slot.start_time)
            self._schedule_refresh('선택 일정 메모리 초안에서 제거 (저장 안 됨)')
        except (ValueError, IndexError) as exc:
            self._schedule_status.set('081 제거 거부 · ' + str(exc))

    def _schedule_preview(self) -> None:
        try:
            dates = self._schedule_draft.upcoming(parse_reference(self._schedule_reference.get()))
            self._schedule_next.set(('예정 시각(참고용·실행/예약 없음): ' +
                                     ', '.join(item.strftime('%Y-%m-%d %H:%M KST') for item in dates))
                                    if dates else '등록된 일정 없음 · 방송 자동 시작 없음')
            self._schedule_status.set('081 수동 날짜 기준 조회 완료 · 실제 시각 계측/방송 시작 없음')
        except ValueError as exc:
            self._schedule_next.set('이전 조회 결과 무효')
            self._schedule_status.set('081 예정 시각 계산 거부 · ' + str(exc))

    def _schedule_save(self) -> None:
        try:
            save_schedule(schedule_path(), self._schedule_draft, operator_confirmed=True)
            self._schedule_status.set('081 운영자 버튼으로 로컬 일정 초안 저장 · 자동 실행/송출 비활성')
        except (ValueError, OSError, PermissionError) as exc:
            self._schedule_status.set('081 로컬 초안 저장 실패 · ' + str(exc))

    def _schedule_load(self) -> None:
        try:
            draft = load_schedule(schedule_path())
            if draft is None:
                self._schedule_status.set('081 저장된 초안 없음 · 현재 메모리 초안 유지')
                return
            self._schedule_draft = draft
            self._schedule_refresh('수동으로 로컬 일정 초안 불러옴')
        except (ValueError, OSError, PermissionError) as exc:
            self._schedule_status.set('081 불러오기 실패 · 현재 초안 유지 · ' + str(exc))

    def _schedule_delete(self) -> None:
        try:
            deleted = delete_schedule(schedule_path(), operator_confirmed=True)
            self._schedule_status.set('081 ' + ('로컬 저장 초안 파일 삭제됨' if deleted else '삭제할 로컬 파일 없음') +
                                      ' · 메모리 초안 유지 / 방송 실행 없음')
        except (ValueError, OSError, PermissionError) as exc:
            self._schedule_status.set('081 로컬 저장 초안 삭제 실패 · ' + str(exc))

    def _start_control_inspect(self) -> None:
        try:
            decision = self._start_control.inspect(parse_reference(self._schedule_reference.get()), self.settings)
            self._start_control_status.set('082 ' + decision.code + ' · ' + decision.explanation)
        except (ValueError, TypeError) as exc:
            self._start_control_status.set('082 판정 거부 · ' + str(exc))

    def _start_control_simulate(self) -> None:
        try:
            when = parse_reference(self._schedule_reference.get())
            decision = self._start_control.simulate_start(when, self.settings)
            self._start_control_status.set('082 ' + decision.code + ' · ' + decision.explanation)
        except (ValueError, TypeError) as exc:
            self._start_control_status.set('082 가상 시작 거부 · ' + str(exc))

    def _start_control_finish(self) -> None:
        decision = self._start_control.simulate_finish()
        if hasattr(self, '_notice_post_status'):
            self._notice_post_clear()
        self._start_control_status.set('082 ' + decision.code + ' · ' + decision.explanation)

    def _build_broadcast_scene(self, tab) -> None:
        """071: manual, non-persistent 16:9 Canvas composition only."""
        ttk.Label(tab, text='원본 71단계 · 방송 화면 구성 (오프라인 미리보기)',
                  font=('Malgun Gothic', 13, 'bold')).pack(anchor='w', pady=(0, 7))
        ttk.Label(tab, text='현재 방송 설정의 플랫폼·콘텐츠·캐릭터·목소리·아바타 선택과 '
                  '기존 58단계 2D 배치를 읽어 로컬 자리표시자 화면을 그립니다. '
                  '실제 게임/채팅/장치 화면 캡처, OBS 연결, 음성 송출 및 방송은 하지 않습니다. '
                  '3D·미정 선택을 2D로 바꾸지 않습니다.',
                  wraplength=735).pack(anchor='w', pady=3)
        row = ttk.Frame(tab)
        row.pack(fill='x', pady=5)
        self._scene_show_title = tk.BooleanVar(value=True)
        self._scene_show_chat = tk.BooleanVar(value=True)
        ttk.Checkbutton(row, text='제목 오버레이', variable=self._scene_show_title).pack(side='left', padx=4)
        ttk.Checkbutton(row, text='가상 채팅 UI', variable=self._scene_show_chat).pack(side='left', padx=4)
        ttk.Button(row, text='현재 선택으로 미리보기 갱신',
                   command=self._broadcast_scene_preview).pack(side='left', padx=8)
        ttk.Button(row, text='아바타 화면 연결 점검 (오프라인)',
                   command=self._avatar_screen_link_check).pack(side='left', padx=5)
        voice_row = ttk.Frame(tab)
        voice_row.pack(fill='x', pady=3)
        ttk.Label(voice_row, text='무음 가상 대사').pack(side='left')
        self._scene_voice_text = tk.StringVar(value='안녕하세요! 아이스팅의 오프라인 방송 화면 시험입니다.')
        ttk.Entry(voice_row, textvariable=self._scene_voice_text, width=25).pack(side='left', padx=5)
        ttk.Button(voice_row, text='가상 음성 경로 준비',
                   command=self._broadcast_voice_prepare).pack(side='left', padx=2)
        ttk.Button(voice_row, text='다음 구간 표시',
                   command=self._broadcast_voice_next).pack(side='left', padx=2)
        ttk.Button(voice_row, text='중단 모의',
                   command=self._broadcast_voice_interrupt).pack(side='left', padx=2)
        self._scene_voice_status = tk.StringVar(value='음성 경로 미준비 · 실제 스피커/송출 없음')
        ttk.Label(tab, textvariable=self._scene_voice_status, wraplength=735).pack(anchor='w')
        self._scene_voice_link = None
        audit_row = ttk.Frame(tab)
        audit_row.pack(fill='x', pady=3)
        ttk.Button(audit_row, text='음량·방송 화면 점검 (오프라인)',
                   command=self._broadcast_output_check).pack(side='left')
        ttk.Label(audit_row, text='현재 음량 설정만 검사 · 소리/방송 측정 아님').pack(side='left', padx=8)
        self._scene_output_status = tk.StringVar(value='미실행 · 화면 갱신 후 수동 점검 필요')
        ttk.Label(tab, textvariable=self._scene_output_status, wraplength=735).pack(anchor='w')
        self._scene_output_report = None
        delivery_row = ttk.Frame(tab)
        delivery_row.pack(fill='x', pady=3)
        ttk.Button(delivery_row, text='송출 설정 초안 연결 (오프라인)',
                   command=self._broadcast_delivery_prepare).pack(side='left')
        ttk.Button(delivery_row, text='초안 JSON 보기',
                   command=self._broadcast_delivery_view).pack(side='left', padx=5)
        ttk.Label(delivery_row, text='74단계 화면 점검 후 수동 확인 · OBS/방송 연결 아님').pack(side='left', padx=8)
        self._scene_delivery_contract = None
        self._scene_delivery_window = None
        self._scene_delivery_status = tk.StringVar(value='미준비 · 송출 설정 연결 초안 없음 · 실제 송출 비활성')
        ttk.Label(tab, textvariable=self._scene_delivery_status, wraplength=735).pack(anchor='w')
        ttk.Button(tab, text='비공개 방송 절차 모의 시험 (오프라인·송출 불가)',
                   command=self._private_broadcast_rehearse).pack(anchor='w', pady=3)
        self._scene_private_rehearsal = None
        self._scene_private_status = tk.StringVar(value='076 미실행 · 실제 비공개 방송은 검증하지 않음')
        ttk.Label(tab, textvariable=self._scene_private_status, wraplength=735).pack(anchor='w')
        ttk.Button(tab, text='채팅·무음 음성·화면 통합 모의 시험 (송출 불가)',
                   command=self._chat_voice_screen_integration_check).pack(anchor='w', pady=3)
        self._scene_chat_voice_report = None
        self._scene_chat_voice_status = tk.StringVar(value='077 미실행 · 실제 소리/영상/시청자 연결 미검증')
        ttk.Label(tab, textvariable=self._scene_chat_voice_status, wraplength=735).pack(anchor='w')
        # 078: explicitly entered mock elapsed duration, NOT a live timer.
        duration_row = ttk.Frame(tab)
        duration_row.pack(fill='x', pady=3)
        self._duration_minimum = tk.StringVar(value='60')
        self._duration_maximum = tk.StringVar(value='180')
        self._duration_elapsed = tk.StringVar(value='0')
        for label, variable in (('최소(분)', self._duration_minimum),
                                ('최대(분)', self._duration_maximum),
                                ('가상 경과(분)', self._duration_elapsed)):
            ttk.Label(duration_row, text=label).pack(side='left', padx=(4, 0))
            ttk.Entry(duration_row, textvariable=variable, width=6).pack(side='left', padx=3)
        ttk.Button(duration_row, text='방송 시간 규칙 모의 점검 (종료 없음)',
                   command=self._broadcast_duration_check).pack(side='left', padx=5)
        self._duration_report = None
        self._duration_status = tk.StringVar(value='078 미점검 · 설정 60~180분 · 실제 방송 타이머 아님')
        ttk.Label(tab, textvariable=self._duration_status, wraplength=735).pack(anchor='w')
        for variable in (self._duration_minimum, self._duration_maximum, self._duration_elapsed):
            variable.trace_add('write', self._broadcast_duration_invalidate)
        # 079: closing rehearsal: local text only, virtual terminal state.
        closing_row = ttk.Frame(tab)
        closing_row.pack(fill='x', pady=3)
        ttk.Button(closing_row, text='마무리 멘트 모의 준비 (종료 송출 없음)',
                   command=self._broadcast_closing_prepare).pack(side='left', padx=3)
        ttk.Button(closing_row, text='다음 멘트 표시 / 가상 종료',
                   command=self._broadcast_closing_advance).pack(side='left', padx=3)
        self._closing_session = None
        self._closing_status = tk.StringVar(value='079 미준비 · 최대 방송 시간 판정 필요 · 실제 자동 종료 없음')
        self._closing_line = tk.StringVar(value='마무리 문구 없음 · 실제 발화/송출 없음')
        ttk.Label(tab, textvariable=self._closing_status, wraplength=735).pack(anchor='w')
        ttk.Label(tab, textvariable=self._closing_line, wraplength=735).pack(anchor='w')
        ttk.Button(tab, text='080 자동 종료 전체 모의 검증 (실제 송출 없음)',
                   command=self._broadcast_closing_audit).pack(anchor='w', pady=3)
        self._closing_audit_report = None
        self._closing_audit_status = tk.StringVar(
            value='080 미실행 · 가상 종료 절차만 검사 · 실제 방송 종료 미검증')
        ttk.Label(tab, textvariable=self._closing_audit_status, wraplength=735).pack(anchor='w')
        self._scene_canvas = tk.Canvas(tab, width=640, height=360,
                                       bg='#17223c', highlightthickness=1,
                                       highlightbackground='#7f8da5')
        self._scene_canvas.pack(anchor='w', pady=5)
        self._scene_status = tk.StringVar(value='미실행 · 운영자 버튼으로 화면 구성 미리보기')
        ttk.Label(tab, textvariable=self._scene_status, wraplength=735).pack(anchor='w', pady=4)
        self._scene_snapshot = None
        for var in (*self._platforms.values(), self._content, self._avatar, self._voice,
                    self._persona_mode, self._avatar_expression,
                    self._layout_horizontal, self._layout_vertical, self._layout_size,
                    self._layout_background, self._scene_show_title, self._scene_show_chat):
            var.trace_add('write', self._broadcast_scene_invalidate)
        for entry in self._persona.values():
            entry.bind('<KeyRelease>', self._broadcast_scene_invalidate, add='+')
        self._scene_voice_text.trace_add('write', self._broadcast_voice_invalidate)
        self._voice_volume.trace_add('write', self._broadcast_output_invalidate)
        self._broadcast_scene_invalidate()

    def _broadcast_scene_draft(self) -> BroadcastSceneDraft:
        avatar = AVATARS[self._avatar.get()]
        return BroadcastSceneDraft(
            platforms=tuple(self._platform_chat_selected()),
            content=CONTENTS[self._content.get()], avatar=avatar,
            voice=VOICES[self._voice.get()],
            persona_name=self._current_persona()['name'],
            layout=self._layout_draft() if avatar == '2d' else None,
            show_title=self._scene_show_title.get(),
            show_chat=self._scene_show_chat.get())

    def _broadcast_scene_invalidate(self, *_args) -> None:
        if hasattr(self, '_automation_audit_status'):
            self._automation_audit_clear()
        self._broadcast_voice_invalidate()
        self._scene_snapshot = None
        self._scene_canvas.delete('all')
        self._scene_canvas.configure(bg='#17223c')
        self._scene_canvas.create_text(320, 180,
            text='선택 변경 또는 미실행\n수동 미리보기 갱신 필요',
            fill='white', tags=('aisting_scene_stale',))
        self._scene_status.set('미리보기 무효 · 현재 선택으로 다시 갱신하세요. 실제 송출 없음.')

    def _broadcast_scene_preview(self) -> None:
        self._broadcast_output_invalidate()
        self._scene_snapshot = None
        try:
            draft = self._broadcast_scene_draft()
            expression = AVATAR_EXPRESSIONS[self._avatar_expression.get()]
            draw_broadcast_scene(self._scene_canvas, draft, expression=expression)
            self._scene_snapshot = draft
            self._scene_status.set(draft.describe())
        except (ValueError, KeyError, tk.TclError) as exc:
            self._scene_canvas.delete('all')
            self._scene_canvas.create_text(320, 180, text='화면 구성 미리보기 실패',
                                           fill='white', tags=('aisting_scene_error',))
            self._scene_status.set('미리보기 실패 · ' + str(exc) + ' · 송출하지 않았습니다.')

    def _avatar_screen_link_check(self) -> None:
        self._broadcast_output_invalidate()
        self._scene_snapshot = None
        try:
            draft = self._broadcast_scene_draft()
            expression = AVATAR_EXPRESSIONS[self._avatar_expression.get()]
            report = inspect_avatar_screen_link(self._scene_canvas, draft, expression)
            self._scene_snapshot = draft
            self._scene_status.set(report.detail + '\n' + draft.describe())
        except (ValueError, KeyError, tk.TclError) as exc:
            self._broadcast_scene_invalidate()
            self._scene_status.set('아바타 화면 연결 점검 실패 · ' + str(exc))

    def _broadcast_voice_invalidate(self, *_args) -> None:
        self._broadcast_output_invalidate()
        self._scene_voice_link = None
        self._scene_voice_status.set('대사/방송 선택 변경 · 음성 가상 연결 무효 · 수동 재준비 필요')
        if hasattr(self, '_scene_canvas'):
            self._scene_canvas.delete('aisting_scene_voice')

    def _broadcast_voice_prepare(self) -> None:
        self._broadcast_voice_invalidate()
        try:
            draft = self._broadcast_scene_draft()
            # Draw the exact draft to which the virtual route is bound.
            self._broadcast_scene_preview()
            if self._scene_snapshot != draft:
                raise ValueError('화면 미리보기 준비 실패')
            self._scene_voice_link = OfflineBroadcastVoiceLink(draft, self._scene_voice_text.get())
            self._scene_voice_status.set(self._scene_voice_link.status().detail + ' · 다음 구간 수동 표시 가능')
        except (ValueError, KeyError, tk.TclError) as exc:
            self._scene_voice_status.set('가상 음성 연결 준비 실패 · ' + str(exc))

    def _broadcast_voice_next(self, interrupt: bool = False) -> None:
        self._broadcast_output_invalidate()
        if self._scene_voice_link is None:
            self._scene_voice_status.set('먼저 가상 음성 경로를 수동으로 준비하세요.')
            return
        try:
            status = self._scene_voice_link.step(
                self._scene_canvas, self._broadcast_scene_draft(), interrupt=interrupt)
            self._scene_voice_status.set(status.state + ' · ' + status.detail)
        except (ValueError, KeyError, tk.TclError) as exc:
            self._broadcast_voice_invalidate()
            self._scene_voice_status.set('가상 경로 오류 · ' + str(exc) + ' · 음성/방송 미출력')

    def _broadcast_voice_interrupt(self) -> None:
        self._broadcast_voice_next(interrupt=True)

    def _private_broadcast_rehearse(self) -> None:
        """076: deterministic local rehearsal; no actual private stream."""
        self._scene_private_rehearsal = None
        try:
            if self._scene_snapshot is None:
                raise ValueError('먼저 화면/음량을 점검하고 송출 설정 초안을 준비하세요.')
            raw = self._voice_volume.get()
            if not raw.isascii() or not raw.isdecimal():
                raise ValueError('설정 음량은 0~100의 숫자여야 합니다.')
            report = rehearse_private_broadcast(
                self._scene_canvas, self._scene_snapshot, self._broadcast_scene_draft(),
                int(raw), self._scene_output_report, self._scene_delivery_contract,
                self._scene_voice_link)
            self._scene_private_rehearsal = report
            self._scene_private_status.set(report.describe())
        except (ValueError, KeyError, tk.TclError) as exc:
            self._scene_private_status.set('오프라인 비공개 방송 절차 모의 실패 · ' + str(exc)
                                           + ' · 실제 비공개 송출/접근범위는 미검증')

    def _chat_voice_screen_integration_check(self) -> None:
        """077: verify synthetic events on a separate unmounted local Canvas."""
        self._scene_chat_voice_report = None
        try:
            if self._scene_snapshot is None:
                raise ValueError('먼저 현재 선택으로 방송 화면 미리보기를 갱신하세요.')
            raw = self._voice_volume.get()
            if not raw.isascii() or not raw.isdecimal():
                raise ValueError('설정 음량은 0~100 숫자여야 합니다.')
            draft = self._broadcast_scene_draft()
            # Validate the VISIBLE current draft, then isolate all synthetic draws.
            checked = audit_broadcast_output(self._scene_canvas, self._scene_snapshot,
                                             draft, int(raw), self._scene_voice_link)
            if not checked.screen_ok:
                raise ValueError('현재 미리보기 화면에 오류: ' + '; '.join(checked.issues))
            temporary = tk.Canvas(self, width=640, height=360)
            try:
                report = run_offline_chat_voice_screen_integration(temporary, draft, int(raw))
            finally:
                temporary.destroy()
            self._scene_chat_voice_report = report
            self._scene_chat_voice_status.set(report.describe())
        except (ValueError, KeyError, tk.TclError) as exc:
            self._scene_chat_voice_status.set('077 모의 통합 시험 미통과 · ' + str(exc)
                                              + ' · 실제 소리/화면 송출은 미검증')

    def _broadcast_closing_invalidate(self) -> None:
        if hasattr(self, "_end_notice_status"):
            self._end_notice_invalidate()
        if hasattr(self, '_closing_audit_status'):
            self._closing_audit_report = None
            self._closing_audit_status.set('080 설정/화면 변경 · 이전 모의 검사 결과 무효 · 실제 방송 미검증')
        self._closing_session = None
        self._closing_line.set('079 선택/시간 변경 · 이전 문구·가상 종료 상태 무효')
        self._closing_status.set('079 종료 절차 초기화 · 다시 모의 준비 필요 · 실제 종료 없음')

    def _broadcast_closing_audit(self) -> None:
        """080: isolated local test cases, never touch live closing session."""
        self._closing_audit_report = None
        try:
            if self._scene_snapshot is None or self._scene_snapshot != self._broadcast_scene_draft():
                raise ValueError('먼저 현재 선택으로 방송 화면 미리보기를 갱신하세요.')
            fields = (self._duration_minimum.get(), self._duration_maximum.get())
            if any(not value.isascii() or not value.isdecimal() for value in fields):
                raise ValueError('최소/최대 시간은 분 단위 숫자여야 합니다.')
            report = run_offline_closing_audit(int(fields[0]), int(fields[1]),
                                               self._current_persona()['name'])
            self._closing_audit_report = report
            self._closing_audit_status.set(report.describe())
        except (ValueError, KeyError, RuntimeError, tk.TclError) as exc:
            self._closing_audit_status.set('080 오프라인 모의 검증 미통과 · ' + str(exc)
                                           + ' · 실제 방송 종료 미검증')

    def _broadcast_closing_prepare(self) -> None:
        self._broadcast_closing_invalidate()
        try:
            if self._scene_snapshot is None or self._scene_snapshot != self._broadcast_scene_draft():
                raise ValueError('먼저 현재 선택으로 화면 미리보기를 갱신하세요.')
            if self._duration_report is None or not self._duration_report.maximum_reached:
                raise ValueError('먼저 최대 시간 도달 모의 판정을 확인하세요.')
            session = OfflineBroadcastClosing(self._duration_report, self._current_persona()['name'])
            self._closing_session = session
            self._closing_status.set('079 준비 완료 · 예고 → 인사 → 가상 종료. 실제 음성/OBS 연결 없음')
        except (ValueError, KeyError) as exc:
            self._closing_status.set('079 모의 준비 실패 · ' + str(exc))

    def _broadcast_closing_advance(self) -> None:
        if self._closing_session is None:
            self._closing_status.set('079 먼저 모의 준비가 필요합니다 · 실제 종료 없음')
            return
        try:
            session = self._closing_session
            # Commit the displayed local text first, then acknowledge the phase.
            def display(text):
                self._closing_line.set(text + ' [화면 텍스트만 / 실제 음성 출력 없음]')
            result = session.advance(display)
            self._closing_status.set(result.phase + ' · ' + result.details)
        except (ValueError, RuntimeError, tk.TclError) as exc:
            self._closing_status.set('079 모의 단계 실패/보존 · ' + str(exc) + ' · 수동 재시도 필요')

    def _broadcast_duration_invalidate(self, *_args) -> None:
        if hasattr(self, '_closing_status'):
            self._broadcast_closing_invalidate()
        self._duration_report = None
        self._duration_status.set('078 입력/화면 선택 변경 · 이전 모의 판단 무효 · 실제 종료 없음')

    def _broadcast_duration_check(self) -> None:
        """078: explicit mock elapsed minutes only; no OBS or clocks started."""
        self._broadcast_duration_invalidate()
        try:
            fields = (self._duration_minimum.get(), self._duration_maximum.get(),
                      self._duration_elapsed.get())
            if any(not value.isascii() or not value.isdecimal() for value in fields):
                raise ValueError('시간 설정은 음수가 아닌 분 단위 정수로 입력하세요.')
            minimum, maximum, elapsed = map(int, fields)
            rules = BroadcastDurationRules(minimum, maximum)
            if elapsed > 10080:
                raise ValueError('가상 경과 시간은 최대 10080분까지만 검사합니다.')
            report = rules.evaluate(elapsed * 60)
            self._duration_report = report
            self._duration_status.set(report.description)
        except ValueError as exc:
            self._duration_status.set('078 시간 규칙 모의 판단 실패 · ' + str(exc)
                                      + ' · 실제 OBS/방송 종료 없음')

    def _broadcast_output_invalidate(self, *_args) -> None:
        if hasattr(self, '_automation_audit_status'):
            self._automation_audit_clear()
        if hasattr(self, '_duration_status'):
            self._broadcast_duration_invalidate()
        if hasattr(self, '_scene_chat_voice_status'):
            self._scene_chat_voice_report = None
            self._scene_chat_voice_status.set('선택/화면/음량 변경 · 077 모의 통합 결과 무효 · 재점검 필요')
        self._scene_private_rehearsal = None
        self._scene_private_status.set('설정/화면 변경 · 076 모의 시험 결과 무효 · 재실행 필요')
        if self._scene_delivery_window is not None:
            try:
                self._scene_delivery_window.destroy()
            except tk.TclError:
                pass
            self._scene_delivery_window = None
        self._scene_delivery_contract = None
        self._scene_delivery_status.set('설정/화면 변경 · 오프라인 송출 설정 초안 무효 · 실제 송출 비활성')
        self._scene_output_report = None
        self._scene_output_status.set('점검 결과 무효 · 현재 미리보기/음량 상태로 다시 수동 점검 필요')

    def _broadcast_output_check(self) -> None:
        """074: offline-only, read-only nominal volume and Canvas-tag audit."""
        self._broadcast_output_invalidate()
        try:
            if self._scene_snapshot is None:
                raise ValueError('먼저 방송 화면 미리보기를 수동으로 갱신하세요.')
            raw_volume = self._voice_volume.get()
            if not raw_volume.isascii() or not raw_volume.isdecimal():
                raise ValueError('음량은 0~100의 숫자로 입력하세요.')
            report = audit_broadcast_output(
                self._scene_canvas, self._scene_snapshot, self._broadcast_scene_draft(),
                int(raw_volume), self._scene_voice_link)
            self._scene_output_report = report
            self._scene_output_status.set(report.description)
        except (ValueError, KeyError, tk.TclError) as exc:
            self._scene_output_status.set('오프라인 점검 실패 · ' + str(exc)
                                          + ' · 실제 음성/영상/송출 검증 없음')

    def _broadcast_delivery_prepare(self) -> None:
        """075: bind ONLY validated local review selections; never create a stream."""
        self._scene_private_rehearsal = None
        self._scene_private_status.set('송출 설정 초안 재준비 · 076 모의 시험 결과 무효')
        if self._scene_delivery_window is not None:
            self._scene_delivery_window.destroy()
            self._scene_delivery_window = None
        self._scene_delivery_contract = None
        try:
            if self._scene_snapshot is None:
                raise ValueError('먼저 방송 화면을 갱신하고 74단계 점검을 수행하세요.')
            raw_volume = self._voice_volume.get()
            if not raw_volume.isascii() or not raw_volume.isdecimal():
                raise ValueError('설정 음량은 0~100의 숫자여야 합니다.')
            draft = prepare_offline_output_settings(
                self._scene_canvas, self._scene_snapshot, self._broadcast_scene_draft(),
                int(raw_volume), self._scene_output_report, self._scene_voice_link)
            self._scene_delivery_contract = draft
            self._scene_delivery_status.set(draft.describe())
        except (ValueError, KeyError, tk.TclError) as exc:
            self._scene_delivery_status.set('송출 설정 초안 연결 실패 · ' + str(exc)
                                            + ' · OBS/방송 연결 및 저장 0건')

    def _broadcast_delivery_view(self) -> None:
        """Operator-only, read-only JSON *review*; no export/OBS connection."""
        if self._scene_delivery_contract is None:
            self._scene_delivery_status.set('먼저 화면·음량 점검 후 송출 설정 초안을 준비하세요.')
            return
        if self._scene_delivery_window is not None:
            self._scene_delivery_window.lift()
            return
        window = tk.Toplevel(self)
        window.title('AISTING · 오프라인 송출 설정 검토 (전송 불가)')
        window.resizable(True, True)
        ttk.Label(window, text='검토 전용 · OBS/스피커/방송 연결 0건 · 스트림 정보 없음',
                  padding=8).pack(anchor='w')
        frame = ttk.Frame(window, padding=8)
        frame.pack(expand=True, fill='both')
        view = tk.Text(frame, width=76, height=22, wrap='word')
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=view.yview)
        view.configure(yscrollcommand=scrollbar.set)
        view.insert('1.0', self._scene_delivery_contract.review_json())
        view.configure(state='disabled')
        scrollbar.pack(side='right', fill='y')
        view.pack(side='left', expand=True, fill='both')
        self._scene_delivery_window = window
        window.protocol('WM_DELETE_WINDOW', lambda: self._broadcast_delivery_close())

    def _broadcast_delivery_close(self) -> None:
        if self._scene_delivery_window is not None:
            self._scene_delivery_window.destroy()
            self._scene_delivery_window = None

    def _build_avatar_expressions(self, tab) -> None:
        """054: operator-chosen emotion-free expression on existing 2D canvas only."""
        ttk.Label(tab, text="54단계 · 기본 표정 수동 설정 (기존 2D 샘플)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=5)
        ttk.Label(tab, text="표정은 사용자가 직접 선택합니다. AI 감정 자동 추론, 모델 파일 열기, "
                  "실제 Live2D/VRM 구동, OBS 송출은 하지 않습니다.", wraplength=710).pack(anchor="w")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=9)
        ttk.Label(row, text="표정").pack(side="left")
        ttk.Combobox(row, textvariable=self._avatar_expression,
                     values=tuple(AVATAR_EXPRESSIONS), state="readonly", width=20).pack(side="left", padx=8)
        ttk.Button(row, text="현재 화면에 적용", command=self._expression_apply).pack(side="left")
        ttk.Button(row, text="기본 표정으로", command=self._expression_reset).pack(side="left", padx=6)
        ttk.Label(tab, text="운영자 확인 후에만 별도 로컬 파일에 저장합니다. 앱 시작 시 자동 불러오지 않습니다.",
                  wraplength=700).pack(anchor="w")
        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=9)
        ttk.Button(buttons, text="표정 기록 저장", command=self._expression_save).pack(side="left")
        ttk.Button(buttons, text="수동 불러오기", command=self._expression_load).pack(side="left", padx=8)
        ttk.Button(buttons, text="저장 기록 삭제", command=self._expression_delete).pack(side="left")
        self._expression_status = tk.StringVar(value="기본 표정 · 저장/불러오기 없음 · 실제 모델 미검증")
        ttk.Label(tab, textvariable=self._expression_status, wraplength=700).pack(anchor="w", pady=8)
        self._expression_info = tk.StringVar(value="")
        ttk.Label(tab, textvariable=self._expression_info, wraplength=700,
                  justify="left").pack(anchor="w", pady=7)
        self._avatar_expression.trace_add("write", self._expression_changed)
        self._expression_apply()

    def _expression_choice(self) -> AvatarExpressionChoice:
        code = AVATARS.get(self._avatar.get())
        return AvatarExpressionChoice(code, AVATAR_EXPRESSIONS[self._avatar_expression.get()])

    def _expression_changed(self, *_args) -> None:
        if hasattr(self, "_expression_status"):
            self._expression_status.set("표정 선택 변경 · 현재 2D 샘플에만 반영 (저장 안 됨)")
        if hasattr(self, "_canvas"):
            self._expression_apply()

    def _expression_apply(self) -> None:
        try:
            choice = self._expression_choice()
            self._draw_avatar_canvases()
            canvases = [self._canvas]
            if self._avatar_capture_canvas is not None and self._avatar_capture_canvas.winfo_exists():
                canvases.append(self._avatar_capture_canvas)
            if not all(expression_matches(canvas, choice.expression) for canvas in canvases):
                self._expression_info.set("표정 반영 실패 · 화면 상태 불일치")
                self._expression_status.set("내장 2D 표정 검증 실패")
            else:
                self._expression_info.set(choice.describe() + "\n현재 Canvas 구조 검사: 일치 (실제 화면 품질 미검증)")
        except (ValueError, KeyError, tk.TclError) as exc:
            self._expression_info.set("표정 사용 불가: " + str(exc))
            if hasattr(self, "_expression_status"):
                self._expression_status.set("3D 외부 렌더러 표정 미지원 · 2D 임의 대체 없음")

    def _expression_reset(self) -> None:
        self._avatar_expression.set("기본")
        self._expression_apply()

    def _expression_save(self) -> None:
        try:
            choice = self._expression_choice()
        except (ValueError, KeyError) as exc:
            self._expression_status.set(str(exc))
            return
        if not messagebox.askyesno("기본 표정 저장", "선택한 2D 샘플 표정을 로컬에 저장할까요?\n"
                                  "실제 모델 적용·최종 승인은 아닙니다.", parent=self):
            self._expression_status.set("저장 취소 · 파일 변경 없음")
            return
        try:
            save_expression(expression_path(), choice, operator_confirmed=True)
            self._expression_status.set("2D 샘플 표정 기록 저장됨 · 실제 모델 미승인")
        except (ValueError, OSError, PermissionError) as exc:
            self._expression_status.set("저장 실패: " + str(exc))

    def _expression_load(self) -> None:
        try:
            current = self._expression_choice()
            loaded = load_expression(expression_path(), selected_avatar=current.avatar)
            if loaded is None:
                self._expression_status.set("저장된 표정 기록 없음")
            else:
                label = next(k for k, v in AVATAR_EXPRESSIONS.items() if v == loaded.expression)
                self._avatar_expression.set(label)
                self._expression_apply()
                self._expression_status.set("운영자 선택 표정 기록 수동 불러오기 완료")
        except (ValueError, OSError, PermissionError, KeyError) as exc:
            self._expression_status.set("불러오기 차단: " + str(exc))

    def _expression_delete(self) -> None:
        if not messagebox.askyesno("표정 기록 삭제", "저장한 2D 표정 기록을 삭제할까요?", parent=self):
            self._expression_status.set("삭제 취소")
            return
        if not messagebox.askyesno("표정 기록 최종 확인", "이 기록 삭제를 한 번 더 확인하시겠습니까?", parent=self):
            self._expression_status.set("2차 삭제 취소")
            return
        try:
            removed = delete_expression(expression_path(), operator_confirmed=True)
            self._expression_status.set("기록 삭제 완료" if removed else "삭제할 기록 없음")
        except (ValueError, OSError, PermissionError) as exc:
            self._expression_status.set("삭제 실패: " + str(exc))

    def _build_avatar_runtime_environment(self, tab) -> None:
        """052: offline avatar rendering candidate. Never launches a renderer."""
        ttk.Label(tab, text="원본 52단계 · 아바타 실행 환경 설정 (오프라인 초안)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="2D/3D에 맞는 렌더러 후보만 검토합니다. 외부 Live2D/VRM은 미연결·미설치 후보입니다. "
                  "PC 정보 확인·모델 열기·방송·프로그램 실행은 하지 않습니다.", wraplength=730).pack(anchor="w")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="렌더러 후보").pack(side="left")
        self._avatar_env_renderer = tk.StringVar(value="미정")
        ttk.Combobox(row, textvariable=self._avatar_env_renderer, state="readonly",
                     values=tuple(AVATAR_RENDERERS), width=36).pack(side="left", padx=6)
        ttk.Label(row, text="샘플 배경").pack(side="left")
        self._avatar_env_background = tk.StringVar(value="남색 스튜디오")
        self._avatar_env_background_box = ttk.Combobox(row, textvariable=self._avatar_env_background,
                        values=tuple(BACKGROUND_COLORS), state="disabled", width=17)
        self._avatar_env_background_box.pack(side="left", padx=6)
        self._avatar_env_renderer.trace_add("write", self._avatar_env_renderer_changed)
        ttk.Label(tab, text="운영자 구성 메모 (200자 이내 · 파일 경로 입력 금지)").pack(anchor="w")
        self._avatar_env_note = ttk.Entry(tab, width=74)
        self._avatar_env_note.pack(fill="x", pady=4)
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=8)
        for label, callback in (("후보 구성 검토", self._avatar_env_preview),
                                ("확인 후 초안 저장", self._avatar_env_save),
                                ("수동 불러오기", self._avatar_env_load),
                                ("2회 확인 삭제", self._avatar_env_delete)):
            ttk.Button(bar, text=label, command=callback).pack(side="left", padx=(0, 5))
        self._avatar_env_status = tk.StringVar(value="미확인 · 외부 렌더러 및 실제 아바타 모델 연결 없음")
        ttk.Label(tab, textvariable=self._avatar_env_status, wraplength=730).pack(anchor="w")
        self._avatar_env_result = tk.Text(tab, height=14, wrap="word", state="disabled")
        self._avatar_env_result.pack(fill="both", expand=True)
        self._avatar_runtime_environment_selection_changed()

    def _avatar_env_renderer_changed(self, *_args) -> None:
        if not hasattr(self, '_avatar_env_background_box'):
            return
        builtin = self._avatar_env_renderer.get() == '내장 2D 샘플 (기존 Tk 미리보기)'
        if not builtin:
            self._avatar_env_background.set('남색 스튜디오')
        self._avatar_env_background_box.configure(state='readonly' if builtin else 'disabled')
        if hasattr(self, '_avatar_env_status'):
            self._avatar_env_status.set('렌더러 후보 변경 · 이전 결과 무효')

    def _avatar_runtime_environment_selection_changed(self) -> None:
        self._avatar_env_renderer.set('미정')
        self._avatar_env_background.set('남색 스튜디오')
        self._avatar_env_note.delete(0, 'end')
        self._avatar_env_show('아바타 종류 변경 · 구성 화면 초기화',
                              '이전 2D/3D 후보 초안을 자동 재사용하지 않습니다. 기존 저장 파일은 보존합니다.')

    def _avatar_env_current(self) -> AvatarRuntimeDraft:
        return AvatarRuntimeDraft(avatar=AVATARS[self._avatar.get()],
               renderer=AVATAR_RENDERERS[self._avatar_env_renderer.get()],
               background=self._avatar_env_background.get(), note=self._avatar_env_note.get())

    def _avatar_env_show(self, status: str, message: str) -> None:
        self._avatar_env_status.set(status)
        self._avatar_env_result.configure(state='normal')
        self._avatar_env_result.delete('1.0', 'end')
        self._avatar_env_result.insert('1.0', message)
        self._avatar_env_result.configure(state='disabled')

    def _avatar_env_preview(self) -> None:
        try:
            draft = self._avatar_env_current()
            self._avatar_env_show('구성 후보 검토 · 실제 설치/호환성/권리 미확인', draft.describe())
        except (ValueError, KeyError, TypeError) as exc:
            self._avatar_env_show('호환성 검사 실패', str(exc))

    def _avatar_env_save(self) -> None:
        try:
            draft = self._avatar_env_current()
            if not messagebox.askyesno('아바타 환경 초안 저장',
                    '렌더러 후보 설정만 저장할까요?\n실제 모델·설치·PC 확인·렌더링·방송은 진행하지 않습니다.', parent=self):
                self._avatar_env_status.set('저장 취소 · 기존 기록 유지')
                return
            save_runtime_environment(runtime_environment_path(), draft, operator_confirmed=True)
            self._avatar_env_show('후보 초안 수동 저장 · 실제 구동 및 승인 대기', draft.describe())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._avatar_env_show('저장 실패 · 기록 유지', str(exc))

    def _avatar_env_load(self) -> None:
        try:
            draft = load_runtime_environment(runtime_environment_path(), selected_avatar=AVATARS[self._avatar.get()])
            if draft is None:
                self._avatar_env_show('저장 기록 없음', '현재 아바타 종류에 저장된 후보 초안이 없습니다.')
                return
            self._avatar_env_renderer.set(next(k for k, v in AVATAR_RENDERERS.items() if v == draft.renderer))
            self._avatar_env_background.set(draft.background)
            self._avatar_env_note.delete(0, 'end')
            self._avatar_env_note.insert(0, draft.note)
            self._avatar_env_show('저장된 같은 아바타 종류의 초안 수동 불러오기', draft.describe())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._avatar_env_show('불러오기 실패 · 기존 화면 유지', str(exc))

    def _avatar_env_delete(self) -> None:
        if not messagebox.askyesno('아바타 구성 삭제 1/2', '렌더러 후보 초안만 삭제할까요?', parent=self):
            return
        if not messagebox.askyesno('아바타 구성 삭제 2/2', '삭제하면 복구할 수 없습니다. 진행할까요?', parent=self):
            return
        try:
            removed = delete_runtime_environment(runtime_environment_path(), operator_confirmed=True)
            self._avatar_env_show('환경 초안 삭제 완료' if removed else '삭제할 기록 없음',
                                  '기존 방송 설정·모델 준비표·SQLite 기억은 변경하지 않았습니다.')
        except (ValueError, OSError) as exc:
            self._avatar_env_show('삭제 실패 · 기록 유지', str(exc))

    def _build_avatar_preparation(self, tab) -> None:
        """051: manual avatar provenance metadata, not actual model loading."""
        ttk.Label(tab, text="원본 51단계 · 승인된 아바타 준비 (수동 메타데이터)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="'방송 설정'에서 선택한 미정/2D/3D를 참조합니다. 파일·디렉터리·장치·계약서를 읽지 않으며 "
                  "사용 권한도 자동 확인하지 않습니다. 모델을 불러오거나 방송을 시작하지 않습니다.",
                  wraplength=730).pack(anchor="w", pady=4)
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=5)
        ttk.Label(row, text="모델 자료 출처").pack(side="left")
        self._avatar_prep_origin = tk.StringVar(value="미정")
        ttk.Combobox(row, textvariable=self._avatar_prep_origin, state="readonly",
                     values=tuple(AVATAR_ORIGINS), width=16).pack(side="left", padx=5)
        ttk.Label(row, text="별칭(파일 경로 아님, 48자 이내)").pack(side="left")
        self._avatar_prep_alias = ttk.Entry(row, width=24)
        self._avatar_prep_alias.pack(side="left", padx=5)
        self._avatar_prep_flags = []
        for caption in ("모델 사용권을 직접 확인했다", "화면 표시·방송 활용 범위를 직접 확인했다",
                        "동의·라이선스 증빙을 직접 검토했다"):
            flag = tk.BooleanVar(value=False)
            self._avatar_prep_flags.append(flag)
            ttk.Checkbutton(tab, text=caption, variable=flag).pack(anchor="w", pady=2)
        ttk.Label(tab, text="운영자 준비 메모 (200자 이하 · 개인정보/파일경로 입력 금지)").pack(anchor="w", pady=(8, 2))
        self._avatar_prep_note = ttk.Entry(tab, width=72)
        self._avatar_prep_note.pack(fill="x")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=8)
        for label, command in (("준비 초안 미리보기", self._avatar_prep_preview),
                               ("확인 후 로컬 저장", self._avatar_prep_save),
                               ("수동 불러오기", self._avatar_prep_load),
                               ("2회 확인 후 기록 삭제", self._avatar_prep_delete)):
            ttk.Button(actions, text=label, command=command).pack(side="left", padx=(0, 5))
        self._avatar_prep_status = tk.StringVar(value="미검토 · 모델 자료 자동 접근·준비 완료·권리 승인 없음")
        ttk.Label(tab, textvariable=self._avatar_prep_status, wraplength=730).pack(anchor="w")
        self._avatar_prep_result = tk.Text(tab, height=13, wrap="word", state="disabled")
        self._avatar_prep_result.pack(fill="both", expand=True)

    def _avatar_preparation_selection_changed(self) -> None:
        self._avatar_prep_origin.set("미정")
        self._avatar_prep_alias.delete(0, "end")
        for flag in self._avatar_prep_flags:
            flag.set(False)
        self._avatar_prep_note.delete(0, "end")
        self._avatar_prep_show("아바타 종류 변경 · 초안 화면 초기화",
                               "다른 아바타 종류의 권리 체크·별칭은 재사용하지 않습니다. 기존 저장 파일은 보존합니다.")

    def _avatar_prep_current(self) -> AvatarPreparation:
        return AvatarPreparation(avatar=AVATARS[self._avatar.get()],
              origin=AVATAR_ORIGINS[self._avatar_prep_origin.get()],
              alias=self._avatar_prep_alias.get(),
              rights_reviewed=self._avatar_prep_flags[0].get(),
              display_permission_reviewed=self._avatar_prep_flags[1].get(),
              evidence_reviewed=self._avatar_prep_flags[2].get(),
              note=self._avatar_prep_note.get())

    def _avatar_prep_show(self, status: str, message: str) -> None:
        self._avatar_prep_status.set(status)
        self._avatar_prep_result.configure(state="normal")
        self._avatar_prep_result.delete("1.0", "end")
        self._avatar_prep_result.insert("1.0", message)
        self._avatar_prep_result.configure(state="disabled")

    def _avatar_prep_preview(self) -> None:
        try:
            draft = self._avatar_prep_current()
            self._avatar_prep_show("수동 체크 기재 · 실제 모델 사용 승인 대기" if draft.checklist_ready
                                   else "준비 초안 · 실물/권리/설치 미확인", draft.describe())
        except (ValueError, KeyError, TypeError) as exc:
            self._avatar_prep_show("입력 확인 실패", str(exc))

    def _avatar_prep_save(self) -> None:
        try:
            draft = self._avatar_prep_current()
            if not messagebox.askyesno("아바타 준비 기록 저장", "입력한 자체 신고 초안만 로컬에 저장할까요?\n"
                  "실제 모델 열기·권리 승인·렌더링·방송·설치는 진행하지 않습니다.", parent=self):
                self._avatar_prep_status.set("저장 취소 · 기존 기록 유지")
                return
            save_preparation(preparation_path(), draft, operator_confirmed=True)
            self._avatar_prep_show("수동 확인 후 초안 저장 · 실제 아바타 사용 승인 대기", draft.describe())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._avatar_prep_show("저장 실패 · 기존 기록 유지", str(exc))

    def _avatar_prep_load(self) -> None:
        try:
            draft = load_preparation(preparation_path(), selected_avatar=AVATARS[self._avatar.get()])
            if draft is None:
                self._avatar_prep_show("저장 기록 없음", "이 아바타 종류에 대해 저장한 초안이 없습니다.")
                return
            self._avatar_prep_origin.set(next(k for k, v in AVATAR_ORIGINS.items() if v == draft.origin))
            self._avatar_prep_alias.delete(0, "end")
            self._avatar_prep_alias.insert(0, draft.alias)
            for flag, checked in zip(self._avatar_prep_flags,
                         (draft.rights_reviewed, draft.display_permission_reviewed, draft.evidence_reviewed)):
                flag.set(checked)
            self._avatar_prep_note.delete(0, "end")
            self._avatar_prep_note.insert(0, draft.note)
            self._avatar_prep_show("같은 아바타 종류의 저장 초안 수동 불러오기 완료", draft.describe())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._avatar_prep_show("불러오기 실패 · 현재 입력 보존", str(exc))

    def _avatar_prep_delete(self) -> None:
        if not messagebox.askyesno("아바타 기록 삭제 1/2", "아바타 메타데이터 초안만 삭제할까요?", parent=self):
            return
        if not messagebox.askyesno("아바타 기록 삭제 2/2", "삭제 후 복구되지 않습니다. 계속할까요?", parent=self):
            return
        try:
            removed = delete_preparation(preparation_path(), operator_confirmed=True)
            self._avatar_prep_show("아바타 준비 기록 삭제 완료" if removed else "삭제할 기록 없음",
                      "설정·SQLite 기억·사용자가 선택한 아바타 종류·모델 실물은 변경하지 않았습니다.")
        except (ValueError, OSError) as exc:
            self._avatar_prep_show("삭제 실패 · 기존 기록 유지", str(exc))

    def _build_voice_rights_review(self, tab) -> None:
        """041: rights checklist only; no audio access or model training."""
        ttk.Label(tab, text="원본 41단계 · 사용할 음성의 권리·동의 확인",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="'방송 설정'의 현재 목소리 확보 방식을 참조합니다. 실제 음성 파일이나 계약서 내용은 읽지 않습니다.\n"
                  "서류·동의 여부는 본인이 직접 확인하고 표시하세요. 체크해도 음성 학습·방송이 허가되거나 실행되지 않습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 9))
        self._voice_rights_checks = []
        for caption in ("이 음성 자료를 사용할 권리를 직접 확인했다",
                        "AI 학습·복제 이용에 대한 명시적 동의/권한을 확인했다",
                        "방송 이용에 대한 명시적 동의/권한을 확인했다",
                        "관련 동의·라이선스 범위를 직접 검토했다"):
            value = tk.BooleanVar(value=False)
            self._voice_rights_checks.append(value)
            ttk.Checkbutton(tab, text=caption, variable=value).pack(anchor="w", pady=2)
        ttk.Label(tab, text="운영자 메모 (선택 · 개인정보, 파일 경로, 실명 입력 금지, 240자 이내)",
                  wraplength=710).pack(anchor="w", pady=(9, 2))
        self._voice_rights_note = ttk.Entry(tab, width=76)
        self._voice_rights_note.pack(fill="x")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="권리 체크 미리보기", command=self._preview_voice_rights).pack(side="left")
        ttk.Button(actions, text="확인 후 기록 저장", command=self._save_voice_rights).pack(side="left", padx=5)
        ttk.Button(actions, text="기록 수동 불러오기", command=self._load_voice_rights).pack(side="left")
        ttk.Button(actions, text="기록 2회 확인 삭제", command=self._delete_voice_rights).pack(side="left", padx=5)
        self._voice_rights_status = tk.StringVar(value="미확인 · 기록 자동 생성 없음 · 음성 학습 및 방송 비활성")
        ttk.Label(tab, textvariable=self._voice_rights_status, wraplength=720).pack(anchor="w")
        self._voice_rights_result = tk.Text(tab, height=13, wrap="word", state="disabled")
        self._voice_rights_result.pack(fill="both", expand=True)
        # The rights attestation belongs to the chosen source. Changing the
        # voice in broadcast settings invalidates any *visible* prior checks.
        self._voice.trace_add("write", self._on_voice_rights_source_changed)

    def _on_voice_rights_source_changed(self, *_args) -> None:
        for value in self._voice_rights_checks:
            value.set(False)
        self._voice_rights_note.delete(0, "end")
        self._voice_rights_show("음성 출처 변경 · 권리 확인 초기화",
                                "다른 음성에 이전 권리 확인을 재사용하지 않습니다.\n"
                                "기존 별도 저장 기록과 방송 설정은 변경하지 않았습니다.")

    def _voice_rights_current(self) -> VoiceRightsReview:
        return VoiceRightsReview(
            source=VOICES[self._voice.get()],
            rights_checked=self._voice_rights_checks[0].get(),
            training_permission_checked=self._voice_rights_checks[1].get(),
            broadcast_permission_checked=self._voice_rights_checks[2].get(),
            evidence_reviewed=self._voice_rights_checks[3].get(),
            note=self._voice_rights_note.get(),
        )

    def _voice_rights_show(self, status: str, message: str) -> None:
        self._voice_rights_status.set(status)
        self._voice_rights_result.configure(state="normal")
        self._voice_rights_result.delete("1.0", "end")
        self._voice_rights_result.insert("1.0", message)
        self._voice_rights_result.configure(state="disabled")

    def _preview_voice_rights(self) -> None:
        try:
            current = self._voice_rights_current()
            status = "자체 신고 항목 채움 · 실제 사용 승인 대기" if current.checklist_complete else "확인 미완료 · 사용 승인 대기"
            self._voice_rights_show(status, current.describe())
        except (ValueError, KeyError, TypeError) as exc:
            self._voice_rights_show("입력 확인 실패", str(exc))

    def _save_voice_rights(self) -> None:
        try:
            current = self._voice_rights_current()
            if not messagebox.askyesno("음성 권리 기록 저장", "운영자가 직접 확인한 체크 상태만 로컬에 저장할까요?\n"
                                     "권리의 진위를 자동 확인하지 않으며 음성 복제·방송은 시작되지 않습니다.", parent=self):
                self._voice_rights_status.set("저장 취소 · 기존 기록 유지")
                return
            save_rights_review(rights_review_path(), current, operator_confirmed=True)
            self._voice_rights_show("운영자 확인 후 기록 저장 · 실제 사용 승인 대기", current.describe())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._voice_rights_show("저장 실패 · 기존 데이터 유지", str(exc))

    def _load_voice_rights(self) -> None:
        try:
            stored = load_rights_review(rights_review_path())
            if stored is None:
                self._voice_rights_show("저장 기록 없음", "음성 권리·동의에 관한 저장 기록이 없습니다.")
                return
            current_source = VOICES[self._voice.get()]
            if stored.source != current_source:
                self._voice_rights_show("음성 선택 불일치 · 불러오기 차단",
                    "저장된 음성 출처와 현재 방송 설정에서 선택한 음성이 다릅니다.\n"
                    "서로 다른 음성에 기존 권리 확인을 적용하지 않습니다. 현재 선택·체크값은 보존했습니다.")
                return
            for field, flag in zip(self._voice_rights_checks, (
                    stored.rights_checked, stored.training_permission_checked,
                    stored.broadcast_permission_checked, stored.evidence_reviewed)):
                field.set(flag)
            self._voice_rights_note.delete(0, "end")
            self._voice_rights_note.insert(0, stored.note)
            self._voice_rights_show("같은 음성 출처 기록 수동 불러오기 완료 · 실제 사용 승인 대기", stored.describe())
        except (ValueError, OSError, KeyError) as exc:
            self._voice_rights_show("불러오기 실패 · 현재 입력 유지", str(exc))

    def _delete_voice_rights(self) -> None:
        if not messagebox.askyesno("음성 기록 삭제 1/2", "음성 권리 자체 점검 기록만 삭제할까요?", parent=self):
            return
        if not messagebox.askyesno("음성 기록 삭제 2/2", "해당 파일을 삭제할까요? 기존 방송 설정은 유지됩니다.", parent=self):
            return
        try:
            removed = delete_rights_review(rights_review_path(), operator_confirmed=True)
            self._voice_rights_show("로컬 기록 삭제 완료" if removed else "삭제할 기록 없음",
                "현재 화면 입력·방송 설정·SQLite 기억은 변경하지 않았습니다.")
        except (ValueError, OSError) as exc:
            self._voice_rights_show("삭제 실패", str(exc))

    def _build_voice_quality_review(self, tab) -> None:
        ttk.Label(tab, text="원본 43단계 · 음성 자료 품질 수동 검토 (파일·마이크 접근 없음)",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w")
        ttk.Label(tab, text="42단계 저장 준비표를 버튼으로 불러온 뒤 별칭마다 4개 기준을 직접 기록하세요."
                            " 실제 분석/학습/송출은 하지 않습니다.", wraplength=730).pack(anchor="w", pady=(5, 9))
        ttk.Button(tab, text="42단계 준비표 수동 참조", command=self._load_quality_manifest).pack(anchor="w")
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(8, 3))
        ttk.Label(row, text="검토할 자료별칭").pack(side="left")
        self._quality_alias = tk.StringVar()
        self._quality_alias_widget = ttk.Combobox(row, textvariable=self._quality_alias,
                                                   state="readonly", width=33, values=())
        self._quality_alias_widget.pack(side="left", padx=8)
        self._quality_alias_widget.bind("<<ComboboxSelected>>", self._quality_choose_alias)
        self._quality_fields = []
        for code in CRITERIA:
            line = ttk.Frame(tab)
            line.pack(fill="x", pady=2)
            ttk.Label(line, text=CRITERION_LABELS[code], width=18).pack(side="left")
            val = tk.StringVar(value=ASSESSMENT_LABELS['unreviewed'])
            ttk.Combobox(line, textvariable=val, state="readonly", width=25,
                         values=tuple(ASSESSMENT_LABELS[x] for x in ASSESSMENTS)).pack(side="left", padx=8)
            self._quality_fields.append(val)
        ttk.Label(tab, text="운영자 참고 메모 (파일 경로·주소·개인정보 금지)").pack(anchor="w", pady=(5, 1))
        self._quality_note = ttk.Entry(tab, width=68)
        self._quality_note.pack(fill="x")
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=7)
        ttk.Button(actions, text="선택 항목 반영", command=self._quality_apply_item).pack(side="left")
        ttk.Button(actions, text="검토표 미리보기", command=self._quality_preview).pack(side="left", padx=5)
        ttk.Button(actions, text="확인 후 저장", command=self._quality_save).pack(side="left")
        actions2 = ttk.Frame(tab)
        actions2.pack(fill="x")
        ttk.Button(actions2, text="기록 수동 불러오기", command=self._quality_load).pack(side="left")
        ttk.Button(actions2, text="기록 2회 확인 삭제", command=self._quality_delete).pack(side="left", padx=5)
        ttk.Button(actions2, text="화면 초기화", command=self._quality_reset).pack(side="left")
        self._quality_status = tk.StringVar(value="검토 대기 · 음성 분석 및 실제 승인 없음")
        ttk.Label(tab, textvariable=self._quality_status, wraplength=730).pack(anchor="w", pady=5)
        self._quality_result = tk.Text(tab, height=8, wrap="word", state="disabled")
        self._quality_result.pack(fill="both", expand=True)
        self._quality_manifest = None
        self._quality_review = None
        self._voice.trace_add("write", self._quality_source_changed)

    def _quality_show(self, status: str, contents: str) -> None:
        self._quality_status.set(status)
        self._quality_result.configure(state="normal")
        self._quality_result.delete("1.0", "end")
        self._quality_result.insert("1.0", contents)
        self._quality_result.configure(state="disabled")

    def _quality_reset(self) -> None:
        self._quality_manifest = None
        self._quality_review = None
        self._quality_alias_widget.configure(values=())
        self._quality_alias.set("")
        for value in self._quality_fields:
            value.set(ASSESSMENT_LABELS['unreviewed'])
        self._quality_note.delete(0, "end")
        self._quality_show("화면 초기화 · 저장된 품질 기록 유지", "준비표 수동 참조부터 다시 시작하세요.")

    def _quality_source_changed(self, *_args) -> None:
        self._quality_reset()
        self._quality_show("음성 출처 변경 · 이전 평가 연결 무효화", "다른 음성 출처의 평가를 재사용하지 않습니다.")

    def _load_quality_manifest(self) -> None:
        try:
            plan = load_material_plan(material_plan_path())
            if plan is None:
                self._quality_reset()
                self._quality_show("준비표 없음", "42단계에서 자료별칭을 입력하고 저장하세요.")
                return
            if plan.source != VOICES[self._voice.get()]:
                self._quality_reset()
                self._quality_show("음성 출처 불일치 · 참조 차단", "42단계 저장 준비표의 음성 출처가 현재 선택과 다릅니다.")
                return
            self._quality_manifest = plan
            self._quality_review = blank_quality_review(plan)
            self._quality_alias_widget.configure(values=tuple(i.alias for i in plan.items))
            self._quality_alias.set(plan.items[0].alias if plan.items else "")
            self._quality_choose_alias()
            self._quality_show("준비표 수동 조회 완료 · 실제 자료 검증 아님", self._quality_review.summarize(plan))
        except (ValueError, OSError) as exc:
            self._quality_reset()
            self._quality_show("준비표 조회 실패", str(exc))

    def _quality_choose_alias(self, *_args) -> None:
        if self._quality_review is None:
            return
        item = next((i for i in self._quality_review.items if i.alias == self._quality_alias.get()), None)
        if item is None:
            return
        for var, choice in zip(self._quality_fields, item.assessments):
            var.set(ASSESSMENT_LABELS[choice])
        self._quality_note.delete(0, "end")
        self._quality_note.insert(0, item.note)

    def _quality_apply_item(self) -> None:
        try:
            if self._quality_manifest is None or self._quality_review is None:
                raise ValueError("42단계 준비표를 먼저 수동 참조하세요.")
            reverse = {label: code for code, label in ASSESSMENT_LABELS.items()}
            values = tuple(reverse[v.get()] for v in self._quality_fields)
            self._quality_review = set_quality_item(self._quality_review, self._quality_manifest,
                                                    self._quality_alias.get(), values,
                                                    self._quality_note.get())
            self._quality_show("선택 항목 화면 반영 · 아직 저장되지 않음",
                               self._quality_review.summarize(self._quality_manifest))
        except (KeyError, ValueError) as exc:
            self._quality_show("평가 입력 오류 · 기존 평가 유지", str(exc))

    def _quality_preview(self) -> None:
        try:
            if self._quality_manifest is None or self._quality_review is None:
                raise ValueError("42단계 준비표를 먼저 수동 참조하세요.")
            self._quality_show("품질 수동 검토 미리보기 · 실제 분석/승인 아님",
                               self._quality_review.summarize(self._quality_manifest))
        except ValueError as exc:
            self._quality_show("미리보기 실패", str(exc))

    def _quality_save(self) -> None:
        try:
            if self._quality_manifest is None or self._quality_review is None:
                raise ValueError("준비표를 먼저 수동 참조하세요.")
            # Operator clicked save: verify the manifest is still current on disk.
            current = load_material_plan(material_plan_path())
            if current != self._quality_manifest:
                raise ValueError("42단계 준비표가 변경되었습니다. 새 준비표를 다시 참조하세요.")
            if not messagebox.askyesno("음성 품질 관찰표 저장", "현재 운영자 메모만 저장합니다. 실제 음질·권리·학습·방송 승인과 무관합니다. 저장할까요?", parent=self):
                self._quality_status.set("저장 취소 · 기존 기록 유지")
                return
            save_quality_review(quality_review_path(), self._quality_review,
                                self._quality_manifest, operator_confirmed=True)
            self._quality_show("운영자 확인 후 메모 저장 · 품질 진위 미검증",
                               self._quality_review.summarize(self._quality_manifest))
        except (ValueError, OSError, PermissionError) as exc:
            self._quality_show("저장 실패 · 기존 기록 유지", str(exc))

    def _quality_load(self) -> None:
        try:
            if self._quality_manifest is None:
                raise ValueError("42단계 준비표를 먼저 수동 참조하세요.")
            current = load_material_plan(material_plan_path())
            if current != self._quality_manifest:
                raise ValueError("준비표가 변경되어 기존 평가를 불러올 수 없습니다.")
            stored = load_quality_review(quality_review_path(), self._quality_manifest)
            if stored is None:
                self._quality_show("저장된 평가 없음", "별도 품질 관찰 기록이 없습니다.")
                return
            self._quality_review = stored
            self._quality_choose_alias()
            self._quality_show("일치하는 수동 기록 불러오기 완료 · 품질 진위 미검증",
                               stored.summarize(self._quality_manifest))
        except (ValueError, OSError) as exc:
            self._quality_show("불러오기 차단 · 현재 평가 유지", str(exc))

    def _quality_delete(self) -> None:
        if not messagebox.askyesno("품질 기록 삭제 1/2", "별도 운영자 품질 기록을 삭제할까요?", parent=self):
            self._quality_status.set("삭제 취소")
            return
        if not messagebox.askyesno("품질 기록 삭제 2/2", "최종 삭제할까요? 준비표·권리·음성 파일은 변경하지 않습니다.", parent=self):
            self._quality_status.set("삭제 취소")
            return
        try:
            removed = delete_quality_review(quality_review_path(), operator_confirmed=True)
            self._quality_show("품질 기록 삭제 완료" if removed else "삭제할 기록 없음",
                               "품질 관찰 기록만 삭제했습니다. 현재 화면/42단계 자료 준비표는 유지됩니다.")
        except (ValueError, OSError) as exc:
            self._quality_show("삭제 실패", str(exc))

    def _build_synthesis_environment(self, tab) -> None:
        ttk.Label(tab, text="원본 44단계 · 한국어 음성 합성 환경 구성 초안",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w")
        ttk.Label(tab, text="현재 방송 설정의 목소리 확보 방식과 Windows 음성 설정을 읽기 전용으로 미리 봅니다. "
                            "실제 음성 조회·설치·재생·학습·방송은 하지 않습니다.",
                  wraplength=730).pack(anchor="w", pady=(6, 10))
        first = ttk.Frame(tab)
        first.pack(fill="x", pady=5)
        ttk.Button(first, text="현재 설정 미리보기", command=self._synth_preview).pack(side="left")
        ttk.Button(first, text="운영자 확인 후 초안 저장", command=self._synth_save).pack(side="left", padx=5)
        second = ttk.Frame(tab)
        second.pack(fill="x", pady=5)
        ttk.Button(second, text="기록 수동 불러오기", command=self._synth_load).pack(side="left")
        ttk.Button(second, text="2회 확인 후 기록 삭제", command=self._synth_delete).pack(side="left", padx=5)
        self._synth_status = tk.StringVar(value="구성 대기 · PC와 음성 파일 자동 조회 없음")
        ttk.Label(tab, textvariable=self._synth_status, wraplength=730).pack(anchor="w", pady=5)
        self._synth_result = tk.Text(tab, height=15, wrap="word", state="disabled")
        self._synth_result.pack(fill="both", expand=True)
        self._voice.trace_add("write", self._synth_source_changed)
        self._voice_rate.trace_add("write", self._synth_source_changed)
        self._voice_volume.trace_add("write", self._synth_source_changed)
        self._voice_name.trace_add("write", self._synth_source_changed)

    def _synth_source_changed(self, *_args) -> None:
        # No stored file is read and no configured state is auto-applied.
        self._synth_show("선택값 변경 · 기존 미리보기 무효 · 다시 확인 필요", "")

    def _synth_show(self, status: str, result: str) -> None:
        self._synth_status.set(status)
        self._synth_result.configure(state="normal")
        self._synth_result.delete("1.0", "end")
        self._synth_result.insert("1.0", result)
        self._synth_result.configure(state="disabled")

    def _synth_current(self):
        chosen = self._selected_voice()
        # An explicit selection from the voice list is respected; otherwise retain
        # the user's stored preference WITHOUT querying installed system voices.
        name = chosen.name if chosen is not None else self._voice_preferred_name
        profile = {"installed_voice_name": name,
                   "rate": int(self._voice_rate.get()),
                   "volume": int(self._voice_volume.get())}
        return build_synthesis_environment(VOICES[self._voice.get()], profile), profile

    def _synth_preview(self) -> None:
        try:
            draft, _ = self._synth_current()
            self._synth_show("한국어 TTS 환경 초안 · 실기기/모델 실행 확인 대기", draft.describe())
        except (ValueError, KeyError, TypeError) as exc:
            self._synth_show("음성 선택값 오류", str(exc))

    def _synth_save(self) -> None:
        try:
            draft, _ = self._synth_current()
            if not messagebox.askyesno("TTS 구성 초안 저장", "현재 선택값으로 별도 로컬 구성 초안만 저장할까요?\n"
                                     "음성 재생·설치·학습·방송은 시작하지 않습니다.", parent=self):
                self._synth_status.set("저장 취소 · 기존 기록 유지")
                return
            save_synthesis_environment(synthesis_environment_path(), draft, operator_confirmed=True)
            self._synth_show("운영자 확인 후 초안 저장 · 실제 TTS 작동 미검증", draft.describe())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._synth_show("저장 실패 · 기존 파일 유지", str(exc))

    def _synth_load(self) -> None:
        try:
            _draft, profile = self._synth_current()
            stored = load_synthesis_environment(synthesis_environment_path(),
                                                VOICES[self._voice.get()], profile)
            self._synth_show("일치하는 초안 불러오기 · 적용/재생 없음" if stored else "저장된 기록 없음",
                             stored.describe() if stored else "별도 음성 환경 초안이 없습니다.")
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self._synth_show("불러오기 차단 · 선택값은 유지", str(exc))

    def _synth_delete(self) -> None:
        if not messagebox.askyesno("TTS 환경 기록 삭제 1/2", "합성 환경 초안 파일만 삭제할까요?", parent=self):
            return
        if not messagebox.askyesno("TTS 환경 기록 삭제 2/2", "다시 확인합니다. 기존 방송 설정과 기억은 유지됩니다.", parent=self):
            return
        try:
            result = delete_synthesis_environment(synthesis_environment_path(), operator_confirmed=True)
            self._synth_show("구성 초안 삭제 완료" if result else "삭제할 구성 초안 없음",
                             "현재 음성 선택·기존 설정·SQLite 기억은 그대로 유지됩니다.")
        except (ValueError, OSError) as exc:
            self._synth_show("삭제 실패", str(exc))

    def _build_voice_output_validation(self, tab) -> None:
        ttk.Label(tab, text="원본 45단계 · 기본 한국어 음성 출력 경로 (비재생 모의 시험)",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(1, 8))
        ttk.Label(tab, text="기존 '무료 한국어 음성'에 실제 PC 수동 듣기 기능이 있습니다. 이 탭은 스피커·OS 정보 조회 없이 구간 분할과 중단/실패 보존만 시험합니다.",
                  wraplength=740).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="모의 시험 문장 (1~6000자 · 사용자 입력)").pack(anchor="w")
        self._voice_output_text = tk.Text(tab, height=4, wrap="word")
        self._voice_output_text.pack(fill="x", pady=(2, 7))
        self._voice_output_text.insert("1.0", "안녕하세요. 오늘도 와 주셔서 고마워요! 무슨 이야기를 나눠볼까요?")
        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Label(row, text="가상 출력 결과").pack(side="left")
        self._voice_output_mode = tk.StringVar(value="전부 전달")
        ttk.Combobox(row, textvariable=self._voice_output_mode, state="readonly", width=23,
                     values=("전부 전달", "2번째 구간 중단", "2번째 구간 오류")).pack(side="left", padx=(8, 8))
        ttk.Button(row, text="구간 출력 모의 실행", command=self._run_voice_output_validation).pack(side="left")
        self._voice_output_status = tk.StringVar(value="미실행 · 실제 소리/OS 조회 없음")
        ttk.Label(tab, textvariable=self._voice_output_status, wraplength=740).pack(anchor="w", pady=(9, 4))
        self._voice_output_result = tk.Text(tab, height=13, wrap="word", state="disabled")
        self._voice_output_result.pack(fill="both", expand=True)
        ttk.Label(tab, text="실제 음질과 한국어 목소리는 사용자 PC에서 본인이 직접 확인해야 합니다. 자동 송출·학습·음성 복제 없음.",
                  wraplength=740).pack(anchor="w", pady=(7, 0))
        self._voice.trace_add("write", self._voice_output_change)
        self._voice_rate.trace_add("write", self._voice_output_change)
        self._voice_volume.trace_add("write", self._voice_output_change)
        self._voice_name.trace_add("write", self._voice_output_change)

    def _voice_output_change(self, *_args) -> None:
        self._voice_output_status.set("음성 설정 변경 · 이전 모의 시험 결과 무효")
        self._voice_output_show("")

    def _voice_output_show(self, contents: str) -> None:
        self._voice_output_result.configure(state="normal")
        self._voice_output_result.delete("1.0", "end")
        self._voice_output_result.insert("1.0", contents)
        self._voice_output_result.configure(state="disabled")

    def _run_voice_output_validation(self) -> None:
        try:
            source = VOICES[self._voice.get()]
            profile = {"installed_voice_name": self._voice_preferred_name,
                       "rate": int(self._voice_rate.get()),
                       "volume": int(self._voice_volume.get())}
            # GUI installed voice selection, if manually selected, takes precedence.
            voice = self._selected_voice()
            if voice is not None:
                profile["installed_voice_name"] = voice.name
            mode = self._voice_output_mode.get()
            if mode not in ("전부 전달", "2번째 구간 중단", "2번째 구간 오류"):
                raise ValueError("가상 출력 상태가 올바르지 않습니다.")
            def virtual_output(_part: str, index: int) -> bool:
                if mode == "2번째 구간 중단" and index == 2:
                    return False
                if mode == "2번째 구간 오류" and index == 2:
                    raise RuntimeError("가상 오류")
                return True
            result = rehearse_korean_output(
                self._voice_output_text.get("1.0", "end-1c"),
                source=source, profile=profile, virtual_play=virtual_output)
            self._voice_output_show(result.describe())
            self._voice_output_status.set("모의 시험 완료 · " + result.state + " · 실제 스피커 출력 없음")
        except (ValueError, TypeError) as exc:
            self._voice_output_show(str(exc))
            self._voice_output_status.set("모의 시험 입력 오류 · 실제 스피커 출력 없음")

    def _build_selected_voice_routing(self, tab) -> None:
        """Roadmap 046: verify operator voice selection to mock backend, no OS calls."""
        ttk.Label(tab, text="원본 46단계 · 선택한 목소리 적용 경로 (비재생 모의 시험)",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(0, 9))
        ttk.Label(tab, text="방송 설정에서 'Windows 무료 음성' 선택 후 '무료 한국어 음성'에서 운영자가 확인/선택한 음성을 사용합니다. 음성 목록 조회는 별도 버튼을 직접 눌렀을 때만 실행됩니다.",
                  wraplength=730).pack(anchor="w", pady=(0, 7))
        self._route_text = tk.Text(tab, height=3, wrap="word")
        self._route_text.pack(fill="x", pady=(0, 7))
        self._route_text.insert("1.0", "안녕하세요. 오늘도 함께해요!")
        self._route_text.bind("<<Modified>>", self._route_text_modified)
        self._route_text.edit_modified(False)
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(1, 7))
        ttk.Label(row, text="가상 재생 상태").pack(side="left")
        self._route_mode = tk.StringVar(value="전부 전달")
        ttk.Combobox(row, textvariable=self._route_mode, state="readonly", width=20,
                     values=("전부 전달", "2번째 구간 중단", "2번째 구간 오류")).pack(side="left", padx=8)
        self._route_mode.trace_add("write", self._route_changed)
        ttk.Button(row, text="선택 목소리 전달 모의 실행", command=self._run_selected_voice_routing).pack(side="left")
        self._route_status = tk.StringVar(value="미실행 · 실제 목소리/OS/오디오 조회 없음")
        ttk.Label(tab, textvariable=self._route_status, wraplength=730).pack(anchor="w", pady=(4, 7))
        self._route_result = tk.Text(tab, height=14, wrap="word", state="disabled")
        self._route_result.pack(fill="both", expand=True)
        ttk.Label(tab, text="이 결과는 가상 출력 경로만 검사합니다. 실제 설치·음성 재생·목소리 일치·음질 합격 아님.",
                  wraplength=730).pack(anchor="w", pady=(7, 0))
        for var in (self._voice, self._voice_name, self._voice_rate, self._voice_volume):
            var.trace_add("write", self._route_changed)

    def _route_text_modified(self, *_args) -> None:
        if self._route_text.edit_modified():
            self._route_text.edit_modified(False)
            self._route_changed()

    def _route_changed(self, *_args) -> None:
        self._route_status.set("입력 또는 목소리 설정 변경 · 이전 모의 결과 무효")
        self._route_show("")

    def _route_show(self, value: str) -> None:
        self._route_result.configure(state="normal")
        self._route_result.delete("1.0", "end")
        self._route_result.insert("1.0", value)
        self._route_result.configure(state="disabled")

    def _run_selected_voice_routing(self) -> None:
        try:
            voice = self._selected_voice()
            selected_name = "" if voice is None else voice.name
            mode = self._route_mode.get()
            if mode not in ("전부 전달", "2번째 구간 중단", "2번째 구간 오류"):
                raise ValueError("가상 재생 상태 오류")
            def virtual_speak(_part: str, _voice: KoreanVoice, _rate: int,
                              _volume: int, index: int) -> bool:
                if index == 2 and mode == "2번째 구간 중단":
                    return False
                if index == 2 and mode == "2번째 구간 오류":
                    raise RuntimeError("virtual playback error")
                return True
            report = rehearse_selected_voice(
                self._route_text.get("1.0", "end-1c"),
                source=VOICES[self._voice.get()], selected_name=selected_name,
                available_voices=self._voices.values(),
                profile={"installed_voice_name": selected_name,
                         "rate": int(self._voice_rate.get()),
                         "volume": int(self._voice_volume.get())},
                virtual_speak=virtual_speak,
            )
            self._route_show(report.describe())
            self._route_status.set("모의 시험 완료 · " + report.state + " · 실제 음성 출력 없음")
        except (ValueError, TypeError) as exc:
            self._route_show(str(exc))
            self._route_status.set("선택 목소리 모의 시험 입력 오류 · 실제 출력 없음")

    def _build_pronunciation_review(self, tab) -> None:
        """047: operator notes only. No microphone, audio, device or OS access."""
        ttk.Label(tab, text="원본 47단계 · 발음 및 억양 수동 검토",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="실제 음성을 듣거나 분석하지 않습니다. 아래 문장에 대해 운영자가 판단을 직접 기록합니다.\n"
                  "평가가 양호여도 실제 음성 품질·재생·학습·방송 승인이 아닙니다.",
                  wraplength=730).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="시험 문장 (한 줄에 1문장, 최대 12개 · 개인정보/경로 입력 금지)").pack(anchor="w")
        self._pron_text = tk.Text(tab, height=4, wrap="word")
        self._pron_text.pack(fill="x", pady=(2, 6))
        self._pron_text.insert("1.0", "안녕하세요, 오늘 방송에 와 주셔서 고마워요.\n정말요? 그다음 이야기도 들려주세요!\nㅋㅋㅋ 너무 재미있네요.")
        self._pron_text.bind("<<Modified>>", self._pron_text_changed)
        self._pron_text.edit_modified(False)
        ttk.Button(tab, text="현재 목소리 설정으로 새 평가표 만들기", command=self._pron_create).pack(anchor="w", pady=(0, 5))
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 5))
        ttk.Label(controls, text="평가 문장").pack(side="left")
        self._pron_index = tk.StringVar()
        self._pron_index_widget = ttk.Combobox(controls, textvariable=self._pron_index,
                                                state="readonly", width=36, values=())
        self._pron_index_widget.pack(side="left", padx=6, fill="x", expand=True)
        self._pron_index_widget.bind("<<ComboboxSelected>>", self._pron_select)
        self._pron_pronunciation = tk.StringVar(value=PRON_LABELS['unreviewed'])
        self._pron_intonation = tk.StringVar(value=PRON_LABELS['unreviewed'])
        choices = tuple(PRON_LABELS.values())
        criteria = ttk.Frame(tab)
        criteria.pack(fill="x", pady=(0, 5))
        for name, variable in (("발음", self._pron_pronunciation), ("억양", self._pron_intonation)):
            ttk.Label(criteria, text=name).pack(side="left")
            ttk.Combobox(criteria, textvariable=variable, state="readonly",
                         values=choices, width=22).pack(side="left", padx=(5, 12))
        note_line = ttk.Frame(tab)
        note_line.pack(fill="x", pady=(0, 6))
        ttk.Label(note_line, text="운영자 메모").pack(side="left")
        self._pron_note = ttk.Entry(note_line)
        self._pron_note.pack(side="left", fill="x", expand=True, padx=(8, 0))
        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(0, 7))
        for label, callback in (("이 문장 평가 반영", self._pron_apply),
                                ("미리보기", self._pron_preview),
                                ("확인 후 저장", self._pron_save),
                                ("수동 불러오기", self._pron_load),
                                ("2회 확인 삭제", self._pron_delete)):
            ttk.Button(buttons, text=label, command=callback).pack(side="left", padx=(0, 4))
        self._pron_status = tk.StringVar(value="미평가 · 로컬 음성/장치 조회 없음 · 자동 저장 없음")
        ttk.Label(tab, textvariable=self._pron_status, wraplength=730).pack(anchor="w", pady=(0, 5))
        self._pron_result = tk.Text(tab, height=12, wrap="word", state="disabled")
        self._pron_result.pack(fill="both", expand=True)
        self._pron_review = None
        for var in (self._voice, self._voice_name, self._voice_rate, self._voice_volume):
            var.trace_add("write", self._pron_invalidate)

    def _pron_text_changed(self, *_args) -> None:
        if self._pron_text.edit_modified():
            self._pron_text.edit_modified(False)
            self._pron_invalidate()

    def _pron_invalidate(self, *_args) -> None:
        self._pron_review = None
        self._pron_index_widget.configure(values=())
        self._pron_index.set("")
        self._pron_status.set("목소리 설정 또는 문장 변경 · 이전 평가 무효화")
        self._pron_show("")

    def _pron_show(self, text: str) -> None:
        self._pron_result.configure(state="normal")
        self._pron_result.delete("1.0", "end")
        self._pron_result.insert("1.0", text)
        self._pron_result.configure(state="disabled")

    def _pron_context(self):
        source = VOICES[self._voice.get()]
        profile = {"installed_voice_name": self._voice_preferred_name if source == "windows_system" else "",
                   "rate": int(self._voice_rate.get()), "volume": int(self._voice_volume.get())}
        # Read the selected text field without querying installed OS voices.
        if source == "windows_system":
            name = self._voice_name.get()
            if not name.endswith(" (ko-KR)"):
                raise ValueError("Windows 한국어 목소리를 직접 선택한 뒤 검토하세요.")
            profile["installed_voice_name"] = name[:-8]
        return source, profile, parse_phrases(self._pron_text.get("1.0", "end-1c"))

    def _pron_create(self) -> None:
        try:
            source, profile, phrases = self._pron_context()
            self._pron_review = blank_pronunciation_review(source, profile, phrases)
            self._pron_index_widget.configure(values=tuple(f"{n}. {v[:26]}" for n, v in enumerate(phrases, 1)))
            self._pron_index.set(self._pron_index_widget.cget("values")[0])
            self._pron_select()
            self._pron_show(self._pron_review.describe())
            self._pron_status.set("평가표 생성 · 미평가 상태 · 별도 저장 없음")
        except (ValueError, KeyError, TypeError) as exc:
            self._pron_invalidate()
            self._pron_show(str(exc))
            self._pron_status.set("평가표 생성 실패 · 이전 평가 사용 불가")

    def _pron_select(self, *_args) -> None:
        if self._pron_review is None:
            return
        try:
            index = self._pron_index_widget.cget('values').index(self._pron_index.get())
            item = self._pron_review.items[index]
        except (ValueError, IndexError):
            return
        self._pron_pronunciation.set(PRON_LABELS[item.pronunciation])
        self._pron_intonation.set(PRON_LABELS[item.intonation])
        self._pron_note.delete(0, "end")
        self._pron_note.insert(0, item.note)

    def _pron_apply(self) -> None:
        try:
            if self._pron_review is None:
                raise ValueError("평가표를 먼저 만드세요.")
            source, profile, phrases = self._pron_context()
            if not self._pron_review.matches(source, profile, phrases):
                raise ValueError("목소리 설정 또는 문장 변경 · 평가 무효화")
            index = self._pron_index_widget.cget('values').index(self._pron_index.get())
            reverse = {v: k for k, v in PRON_LABELS.items()}
            self._pron_review = update_pronunciation_item(
                self._pron_review, index, reverse[self._pron_pronunciation.get()],
                reverse[self._pron_intonation.get()], self._pron_note.get())
            self._pron_show(self._pron_review.describe())
            self._pron_status.set("화면에 평가 반영 · 저장 전 · 실제 음성 검증 아님")
        except (ValueError, KeyError, TypeError) as exc:
            self._pron_status.set("평가 입력 오류 · 기존 평가 유지")
            self._pron_show(str(exc))

    def _pron_preview(self) -> None:
        try:
            if self._pron_review is None:
                raise ValueError("평가표를 먼저 만드세요.")
            source, profile, phrases = self._pron_context()
            if not self._pron_review.matches(source, profile, phrases):
                raise ValueError("설정/문장이 변경되어 이전 평가를 표시할 수 없습니다.")
            self._pron_show(self._pron_review.describe())
            self._pron_status.set("운영자 평가 미리보기 · 실제 청취 검증 아님")
        except (ValueError, KeyError) as exc:
            self._pron_show(str(exc))
            self._pron_status.set("미리보기 실패")

    def _pron_save(self) -> None:
        try:
            if self._pron_review is None:
                raise ValueError("저장할 평가표가 없습니다.")
            source, profile, phrases = self._pron_context()
            if not self._pron_review.matches(source, profile, phrases):
                raise ValueError("설정/문장 변경 · 저장 차단")
            if not messagebox.askyesno("발음·억양 관찰표 저장", "직접 작성한 평가와 메모를 로컬에 저장할까요?\n실제 음성 품질 승인과 무관합니다.", parent=self):
                self._pron_status.set("저장 취소 · 기존 데이터 유지")
                return
            save_pronunciation_review(pronunciation_review_path(), self._pron_review,
                                      source, profile, phrases, operator_confirmed=True)
            self._pron_status.set("수동 확인 후 저장 완료 · 실제 음성 검증 아님")
        except (ValueError, KeyError, OSError) as exc:
            self._pron_show(str(exc))
            self._pron_status.set("저장 실패 · 기존 기록 보존")

    def _pron_load(self) -> None:
        try:
            source, profile, phrases = self._pron_context()
            loaded = load_pronunciation_review(pronunciation_review_path(), source, profile, phrases)
            if loaded is None:
                self._pron_status.set("저장된 평가표 없음")
                return
            self._pron_review = loaded
            self._pron_index_widget.configure(values=tuple(f"{n}. {v[:26]}" for n, v in enumerate(phrases, 1)))
            self._pron_index.set(self._pron_index_widget.cget('values')[0])
            self._pron_select()
            self._pron_show(loaded.describe())
            self._pron_status.set("현재 음성·문장과 일치한 수동 평가표 불러오기 완료")
        except (ValueError, KeyError, OSError) as exc:
            self._pron_show(str(exc))
            self._pron_status.set("불러오기 차단 · 현재 평가 유지")

    def _pron_delete(self) -> None:
        for prompt in ("저장된 발음·억양 평가표를 삭제할까요?", "다시 확인합니다. 평가 기록을 정말 삭제할까요?"):
            if not messagebox.askyesno("발음·억양 기록 삭제", prompt, parent=self):
                self._pron_status.set("삭제 취소")
                return
        try:
            deleted = delete_pronunciation_review(pronunciation_review_path(), operator_confirmed=True)
            self._pron_status.set("수동 평가표 삭제 완료" if deleted else "삭제할 기록 없음")
        except (ValueError, OSError) as exc:
            self._pron_show(str(exc))
            self._pron_status.set("삭제 실패")

    def _build_emotion_review(self, tab) -> None:
        """048: operator-only emotional intention/observation notes; no TTS or device I/O."""
        ttk.Label(tab, text="원본 48단계 · 감정 표현 수동 테스트",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="어떤 감정으로 말해야 할지 운영자가 직접 정하고, 실제 청취 후 판단을 기록합니다.\n"
                  "소리를 자동 재생·분석·생성하지 않습니다. '적절' 선택은 기술 검증/학습/방송 승인과 무관합니다.",
                  wraplength=735).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="평가 문장 (한 줄에 한 문장 · 최대 12건 · 개인정보/경로 제외)").pack(anchor="w")
        self._emotion_text = tk.Text(tab, height=4, wrap="word")
        self._emotion_text.pack(fill="x", pady=(2, 6))
        self._emotion_text.insert("1.0", "오늘 와줘서 정말 반가워요!\n헉, 진짜 그렇게 됐어요?\n오늘은 조금 차분하게 이야기해볼게요.")
        self._emotion_text.bind("<<Modified>>", self._emotion_text_changed)
        self._emotion_text.edit_modified(False)
        ttk.Button(tab, text="선택한 목소리로 새 감정 평가표 만들기", command=self._emotion_create).pack(anchor="w", pady=(0, 6))
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=(0, 5))
        ttk.Label(bar, text="평가할 문장").pack(side="left")
        self._emotion_index = tk.StringVar()
        self._emotion_index_widget = ttk.Combobox(bar, textvariable=self._emotion_index,
                                                    state="readonly", width=35, values=())
        self._emotion_index_widget.pack(side="left", padx=6, fill="x", expand=True)
        self._emotion_index_widget.bind("<<ComboboxSelected>>", self._emotion_select)
        emotion_row = ttk.Frame(tab)
        emotion_row.pack(fill="x", pady=(0, 5))
        ttk.Label(emotion_row, text="의도한 감정 (운영자 직접 기재)").pack(side="left")
        self._emotion_intent = ttk.Entry(emotion_row, width=30)
        self._emotion_intent.pack(side="left", padx=(6, 12), fill="x", expand=True)
        ttk.Label(emotion_row, text="운영자 평가").pack(side="left")
        self._emotion_verdict = tk.StringVar(value=EMOTION_LABELS['unreviewed'])
        ttk.Combobox(emotion_row, textvariable=self._emotion_verdict, state="readonly",
                     values=tuple(EMOTION_LABELS.values()), width=21).pack(side="left", padx=6)
        note_row = ttk.Frame(tab)
        note_row.pack(fill="x", pady=(0, 6))
        ttk.Label(note_row, text="개선 메모").pack(side="left")
        self._emotion_note = ttk.Entry(note_row)
        self._emotion_note.pack(side="left", fill="x", expand=True, padx=(8, 0))
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 7))
        for label, command in (("이 문장 평가 반영", self._emotion_apply),
                               ("미리보기", self._emotion_preview),
                               ("확인 후 저장", self._emotion_save),
                               ("수동 불러오기", self._emotion_load),
                               ("2회 확인 삭제", self._emotion_delete)):
            ttk.Button(controls, text=label, command=command).pack(side="left", padx=(0, 4))
        self._emotion_status = tk.StringVar(value="미평가 · 자동 청취/저장/학습/방송 없음")
        ttk.Label(tab, textvariable=self._emotion_status, wraplength=730).pack(anchor="w", pady=(0, 5))
        self._emotion_result = tk.Text(tab, height=12, wrap="word", state="disabled")
        self._emotion_result.pack(fill="both", expand=True)
        self._emotion_review = None
        for var in (self._voice, self._voice_name, self._voice_rate, self._voice_volume):
            var.trace_add('write', self._emotion_invalidate)

    def _emotion_text_changed(self, *_args) -> None:
        if self._emotion_text.edit_modified():
            self._emotion_text.edit_modified(False)
            self._emotion_invalidate()

    def _emotion_show(self, text: str) -> None:
        self._emotion_result.configure(state="normal")
        self._emotion_result.delete("1.0", "end")
        self._emotion_result.insert("1.0", text)
        self._emotion_result.configure(state="disabled")

    def _emotion_invalidate(self, *_args) -> None:
        self._emotion_review = None
        self._emotion_index_widget.configure(values=())
        self._emotion_index.set("")
        self._emotion_intent.delete(0, "end")
        self._emotion_note.delete(0, "end")
        self._emotion_verdict.set(EMOTION_LABELS['unreviewed'])
        self._emotion_status.set("목소리 또는 시험 문장 변경 · 이전 평가 무효화")
        self._emotion_show("")

    def _emotion_context(self):
        source = VOICES[self._voice.get()]
        profile = {"installed_voice_name": "", "rate": int(self._voice_rate.get()),
                   "volume": int(self._voice_volume.get())}
        if source == 'windows_system':
            display_name = self._voice_name.get()
            if not display_name.endswith(' (ko-KR)'):
                raise ValueError('Windows 한국어 목소리를 직접 선택한 뒤 시험하세요.')
            profile['installed_voice_name'] = display_name[:-8]
        return source, profile, parse_phrases(self._emotion_text.get('1.0', 'end-1c'))

    def _emotion_create(self) -> None:
        try:
            source, profile, phrases = self._emotion_context()
            self._emotion_review = blank_emotion_review(source, profile, phrases)
            values = tuple(f'{i}. {v[:26]}' for i, v in enumerate(phrases, 1))
            self._emotion_index_widget.configure(values=values)
            self._emotion_index.set(values[0])
            self._emotion_select()
            self._emotion_show(self._emotion_review.describe())
            self._emotion_status.set('평가표 생성 · 모든 문장 미평가 · 자동 저장 없음')
        except (ValueError, KeyError, TypeError) as exc:
            self._emotion_invalidate()
            self._emotion_show(str(exc))
            self._emotion_status.set('평가표 생성 실패 · 기존 평가 무효화')

    def _emotion_select(self, *_args) -> None:
        if self._emotion_review is None:
            return
        try:
            index = self._emotion_index_widget.cget('values').index(self._emotion_index.get())
            item = self._emotion_review.items[index]
        except (ValueError, IndexError):
            return
        self._emotion_intent.delete(0, 'end')
        self._emotion_intent.insert(0, item.intended_emotion)
        self._emotion_note.delete(0, 'end')
        self._emotion_note.insert(0, item.note)
        self._emotion_verdict.set(EMOTION_LABELS[item.verdict])

    def _emotion_apply(self) -> None:
        try:
            if self._emotion_review is None:
                raise ValueError('평가표를 먼저 생성하세요.')
            source, profile, phrases = self._emotion_context()
            if not self._emotion_review.matches(source, profile, phrases):
                raise ValueError('설정 또는 문장 변경 · 이전 평가 무효화')
            index = self._emotion_index_widget.cget('values').index(self._emotion_index.get())
            lookup = {label: key for key, label in EMOTION_LABELS.items()}
            self._emotion_review = update_emotion_item(
                self._emotion_review, index, self._emotion_intent.get(),
                lookup[self._emotion_verdict.get()], self._emotion_note.get())
            self._emotion_show(self._emotion_review.describe())
            self._emotion_status.set('화면에 운영자 평가 반영 · 저장 전 · 실제 청취 품질 검증 아님')
        except (ValueError, KeyError, TypeError) as exc:
            self._emotion_show(str(exc))
            self._emotion_status.set('평가 입력 오류 · 기존 평가 유지')

    def _emotion_preview(self) -> None:
        try:
            if self._emotion_review is None:
                raise ValueError('평가표를 먼저 생성하세요.')
            source, profile, phrases = self._emotion_context()
            if not self._emotion_review.matches(source, profile, phrases):
                raise ValueError('목소리 또는 문장이 변경되어 이전 평가를 표시할 수 없습니다.')
            self._emotion_show(self._emotion_review.describe())
            self._emotion_status.set('운영자 기재 내용 미리보기 · 실제 음성 분석 아님')
        except (ValueError, KeyError) as exc:
            self._emotion_show(str(exc))
            self._emotion_status.set('미리보기 실패')

    def _emotion_save(self) -> None:
        try:
            if self._emotion_review is None:
                raise ValueError('저장할 평가표가 없습니다.')
            source, profile, phrases = self._emotion_context()
            if not self._emotion_review.matches(source, profile, phrases):
                raise ValueError('목소리 또는 문장 변경 · 저장 차단')
            if not messagebox.askyesno('감정 표현 평가표 저장',
                    '운영자가 입력한 감정 방향과 평가 메모를 로컬에 저장할까요?\n실제 음성 검증이나 사용 승인과 무관합니다.', parent=self):
                self._emotion_status.set('저장 취소 · 기존 기록 유지')
                return
            save_emotion_review(emotion_review_path(), self._emotion_review,
                                source, profile, phrases, operator_confirmed=True)
            self._emotion_status.set('수동 확인 후 기록 저장 · 실제 청취 검증 아님')
        except (ValueError, KeyError, OSError) as exc:
            self._emotion_show(str(exc))
            self._emotion_status.set('저장 실패 · 기존 기록 보존')

    def _emotion_load(self) -> None:
        try:
            source, profile, phrases = self._emotion_context()
            loaded = load_emotion_review(emotion_review_path(), source, profile, phrases)
            if loaded is None:
                self._emotion_status.set('저장된 감정 표현 기록 없음')
                return
            self._emotion_review = loaded
            values = tuple(f'{i}. {v[:26]}' for i, v in enumerate(phrases, 1))
            self._emotion_index_widget.configure(values=values)
            self._emotion_index.set(values[0])
            self._emotion_select()
            self._emotion_show(loaded.describe())
            self._emotion_status.set('현재 목소리·문장과 일치한 기록만 불러옴')
        except (ValueError, KeyError, OSError) as exc:
            self._emotion_show(str(exc))
            self._emotion_status.set('불러오기 차단 · 기존 평가 유지')

    def _emotion_delete(self) -> None:
        for question in ('저장된 감정 표현 평가표를 삭제할까요?', '다시 확인합니다. 정말 삭제할까요?'):
            if not messagebox.askyesno('감정 표현 기록 삭제', question, parent=self):
                self._emotion_status.set('삭제 취소')
                return
        try:
            deleted = delete_emotion_review(emotion_review_path(), operator_confirmed=True)
            self._emotion_status.set('평가 기록 삭제 완료' if deleted else '삭제할 기록 없음')
        except (ValueError, OSError) as exc:
            self._emotion_show(str(exc))
            self._emotion_status.set('삭제 실패')

    def _build_dialogue_voice_link(self, tab) -> None:
        """Roadmap 049: mock replies flow into virtual voice one operator click at a time."""
        ttk.Label(tab, text="원본 49단계 · AI 대사 → 음성 출력 연결 (완전 모의)",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="운영자 입력 채팅 → 오프라인 모의 AI 대사 → 가상 목소리 구간 전달."
                  " 실제 모델·OS 목록·스피커·방송은 사용하지 않습니다."
                  " 가상 목소리 이름은 실제 설치/선택된 음성 인증이 아닙니다.",
                  wraplength=730).pack(anchor="w", pady=(0, 7))
        self._link_script = tk.Text(tab, height=4, wrap="word")
        self._link_script.pack(fill="x")
        self._link_script.insert("1.0", "시청자: 안녕하세요!\n시청자: 안녕하세요!\n다른분: 오늘 방송은 어떤가요?")
        self._link_script.bind('<<Modified>>', self._link_script_modified)
        self._link_script.edit_modified(False)
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(8, 6))
        ttk.Label(row, text="가상 시험 목소리").pack(side="left")
        self._link_voice_name = tk.StringVar(value="모의 한국어 음성")
        ttk.Entry(row, textvariable=self._link_voice_name, width=20).pack(side="left", padx=(6, 12))
        ttk.Label(row, text="가상 오류").pack(side="left")
        self._link_mode = tk.StringVar(value="없음")
        ttk.Combobox(row, state="readonly", textvariable=self._link_mode, width=18,
                     values=("없음", "첫 구간 중단", "첫 구간 오류", "두번째 채팅 중단")).pack(side="left", padx=6)
        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=(3, 7))
        ttk.Button(buttons, text="시험 시작/초기화", command=self._link_start).pack(side="left")
        ttk.Button(buttons, text="1건 수동 처리/재시도", command=self._link_step).pack(side="left", padx=7)
        ttk.Button(buttons, text="대기 채팅 모두 모의 처리", command=self._link_batch).pack(side="left")
        self._link_status = tk.StringVar(value="미실행 · 실제 소리/AI/파일 저장 없음")
        ttk.Label(tab, textvariable=self._link_status, wraplength=730).pack(anchor="w", pady=(5, 5))
        self._link_result = tk.Text(tab, height=13, state="disabled", wrap="word")
        self._link_result.pack(fill="both", expand=True)
        self._link_session = None
        for var in (self._voice, self._voice_name, self._voice_rate, self._voice_volume,
                    self._link_voice_name, self._link_mode):
            var.trace_add('write', self._link_invalidate)

    def _link_script_modified(self, *_args) -> None:
        if self._link_script.edit_modified():
            self._link_script.edit_modified(False)
            self._link_invalidate()

    def _link_invalidate(self, *_args) -> None:
        self._link_session = None
        self._link_status.set("대본·음성 설정·오류 조건 변경 · 이전 시험 무효")
        self._link_show("")

    def _link_show(self, text: str) -> None:
        self._link_result.configure(state="normal")
        self._link_result.delete("1.0", "end")
        self._link_result.insert("1.0", text)
        self._link_result.configure(state="disabled")

    def _link_start(self) -> None:
        self._link_session = None
        try:
            source = VOICES[self._voice.get()]
            name = self._link_voice_name.get()
            mode = self._link_mode.get()
            if mode not in ("없음", "첫 구간 중단", "첫 구간 오류", "두번째 채팅 중단"):
                raise ValueError("가상 오류 시나리오를 확인하세요.")
            profile = {'installed_voice_name': name,
                       'rate': int(self._voice_rate.get()),
                       'volume': int(self._voice_volume.get())}
            def virtual_dispatch(_part: str, _voice: KoreanVoice, _rate: int,
                                 _volume: int, index: int) -> bool:
                if index != 1:
                    return True
                if mode == '첫 구간 중단':
                    return False
                if mode == '첫 구간 오류':
                    raise RuntimeError('virtual error')
                if mode == '두번째 채팅 중단' and self._link_session is not None and len(self._link_session.completed) == 1:
                    return False
                return True
            self._link_session = DialogueVoiceLink(
                self._link_script.get('1.0', 'end-1c'), source=source,
                selected_name=name, available_voices=[KoreanVoice(name)],
                profile=profile, virtual_speak=virtual_dispatch)
            self._link_show(self._link_session.status().describe())
            self._link_status.set("시험 준비 · 사용자가 처리 버튼을 누를 때만 가상 전달")
        except (ValueError, TypeError, KeyError) as exc:
            self._link_show(str(exc))
            self._link_status.set("모의 연결 시험 입력 오류 · 실제 출력 없음")

    def _link_step(self) -> None:
        if self._link_session is None:
            self._link_status.set("시험 시작/초기화를 먼저 눌러 주세요.")
            return
        result = self._link_session.step()
        self._link_show(result.describe())
        self._link_status.set("모의 처리 · " + result.state + " · 실제 음성 출력 없음")

    def _link_batch(self) -> None:
        if self._link_session is None:
            self._link_status.set("시험 시작/초기화를 먼저 눌러 주세요.")
            return
        result = self._link_session.run_manual_batch()
        self._link_show(result.describe())
        self._link_status.set("수동 일괄 모의 · " + result.state + " · 실제 음성 출력 없음")

    def _build_voice_final_verification(self, tab) -> None:
        """050: operator-triggered virtual chain checklist, not real TTS sign-off."""
        ttk.Label(tab, text="원본 50단계 · 목소리 작동 통합 점검 (모의 경로)",
                  font=("Malgun Gothic", 12, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="기존 채팅→AI 대사→선택 목소리 가상 전달을 정상·중단·오류로 점검합니다. "
                  "스피커/OS 음성 조회/실제 AI 연결 없이 실행하며, 실제 음질의 최종 승인과 별개입니다.",
                  wraplength=730).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="모의 채팅 대본 (닉네임: 내용, 2~30건)").pack(anchor="w")
        self._voice_final_script = tk.Text(tab, height=4, wrap="word")
        self._voice_final_script.pack(fill="x", pady=(3, 6))
        self._voice_final_script.insert('1.0', '시청자: 안녕!\n시청자: 안녕!\n다른분: 좋은 하루입니다')
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 7))
        ttk.Label(row, text="가상 음성 식별자 (실제 설치 확인 아님)").pack(side="left")
        self._voice_final_name = tk.StringVar(value="모의 한국어 음성")
        ttk.Entry(row, textvariable=self._voice_final_name, width=24).pack(side="left", padx=8)
        ttk.Button(row, text="오프라인 통합 점검 실행", command=self._run_voice_final_verification).pack(side="left")
        self._voice_final_status = tk.StringVar(value="미실행 · 사용자 버튼만 점검 · 실제 출력 승인 대기")
        ttk.Label(tab, textvariable=self._voice_final_status, wraplength=730).pack(anchor="w", pady=5)
        self._voice_final_result = tk.Text(tab, height=16, wrap="word", state="disabled")
        self._voice_final_result.pack(fill="both", expand=True)
        self._voice_final_script.bind('<<Modified>>', self._voice_final_modified)
        self._voice_final_script.edit_modified(False)
        for var in (self._voice, self._voice_name, self._voice_rate,
                    self._voice_volume, self._voice_final_name):
            var.trace_add('write', self._voice_final_invalidate)

    def _voice_final_modified(self, *_args) -> None:
        if self._voice_final_script.edit_modified():
            self._voice_final_script.edit_modified(False)
            self._voice_final_invalidate()

    def _voice_final_invalidate(self, *_args) -> None:
        self._voice_final_status.set('대본 또는 목소리 설정 변경 · 이전 가상 점검 무효 · 실제 승인 대기')
        self._voice_final_show('')

    def _voice_final_show(self, text: str) -> None:
        self._voice_final_result.configure(state="normal")
        self._voice_final_result.delete("1.0", "end")
        self._voice_final_result.insert("1.0", text)
        self._voice_final_result.configure(state="disabled")

    def _run_voice_final_verification(self) -> None:
        try:
            report = verify_voice_chain(
                self._voice_final_script.get('1.0', 'end-1c'),
                source=VOICES[self._voice.get()],
                selected_name=self._voice_final_name.get(),
                profile={'installed_voice_name': self._voice_final_name.get(),
                         'rate': int(self._voice_rate.get()),
                         'volume': int(self._voice_volume.get())},
            )
            self._voice_final_show(report.describe())
            self._voice_final_status.set('가상 통합 점검 ' + ('통과' if report.offline_pass else '미통과')
                                         + ' · 실제 음성/Windows 승인 대기')
        except (ValueError, TypeError, KeyError) as exc:
            self._voice_final_show(str(exc))
            self._voice_final_status.set('입력 또는 목소리 방식 오류 · 실제 출력 없음')

    def _build_voice_material_plan(self, tab) -> None:
        """042: operator metadata draft only; no audio files or devices accessed."""
        ttk.Label(tab, text="원본 42단계 · 승인된 음성 자료 준비표 (실물 파일 접근 없음)",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 7))
        ttk.Label(tab, text="사용자가 직접 자료별칭과 예상 길이만 적습니다. 실제 파일 경로, 개인정보, 파일명, 계약서, 녹음 내용은 입력하지 마세요.\n"
                  "권리 체크는 41단계 기록을 수동 확인할 때만 읽으며, 어떤 경우에도 실제 사용·학습·방송 승인이 아닙니다.",
                  wraplength=720).pack(anchor="w", pady=(0, 6))
        ttk.Label(tab, text="자료별칭 | 예상 길이(초) · 한 줄에 1건, 최대 20건 · 파일 열기/자동 검색 없음").pack(anchor="w")
        self._voice_material_lines = tk.Text(tab, height=5, wrap="none")
        self._voice_material_lines.pack(fill="x", pady=(2, 7))
        ttk.Label(tab, text="준비 메모 (선택 · 한 줄 180자 이하 · 개인정보/경로 기재 금지)").pack(anchor="w")
        self._voice_material_note = ttk.Entry(tab, width=76)
        self._voice_material_note.pack(fill="x", pady=(2, 6))
        first = ttk.Frame(tab)
        first.pack(fill="x")
        ttk.Button(first, text="준비표 미리보기", command=self._preview_voice_material).pack(side="left")
        ttk.Button(first, text="41단계 권리 체크 수동 참조", command=self._check_voice_material_rights).pack(side="left", padx=4)
        ttk.Button(first, text="확인 후 초안 저장", command=self._save_voice_material).pack(side="left")
        second = ttk.Frame(tab)
        second.pack(fill="x", pady=(4, 6))
        ttk.Button(second, text="준비표 수동 불러오기", command=self._load_voice_material).pack(side="left")
        ttk.Button(second, text="준비표 2회 확인 삭제", command=self._delete_voice_material).pack(side="left", padx=4)
        ttk.Button(second, text="입력 초기화", command=self._reset_voice_material).pack(side="left")
        self._voice_material_status = tk.StringVar(value="수동 준비 대기 · 실물 음성/학습/방송 접근 없음")
        ttk.Label(tab, textvariable=self._voice_material_status, wraplength=720).pack(anchor="w")
        self._voice_material_result = tk.Text(tab, height=10, wrap="word", state="disabled")
        self._voice_material_result.pack(fill="both", expand=True)
        self._voice_material_rights = None  # not automatically read from disk
        self._voice.trace_add("write", self._on_voice_material_source_changed)

    def _on_voice_material_source_changed(self, *_args) -> None:
        self._voice_material_lines.delete("1.0", "end")
        self._voice_material_note.delete(0, "end")
        self._voice_material_rights = None
        self._voice_material_show("음성 출처 변경 · 준비표 입력 초기화",
                                  "다른 음성 출처의 준비표나 권리 진술을 자동으로 재사용하지 않습니다.\n"
                                  "별도 저장된 기존 준비표, 방송 설정, SQLite 기억은 변경하지 않았습니다.")

    def _voice_material_current(self) -> VoiceMaterialDraft:
        return parse_material_lines(self._voice_material_lines.get("1.0", "end-1c"),
                                    VOICES[self._voice.get()], self._voice_material_note.get())

    def _voice_material_show(self, status: str, contents: str) -> None:
        self._voice_material_status.set(status)
        self._voice_material_result.configure(state="normal")
        self._voice_material_result.delete("1.0", "end")
        self._voice_material_result.insert("1.0", contents)
        self._voice_material_result.configure(state="disabled")

    def _preview_voice_material(self) -> None:
        try:
            plan = self._voice_material_current()
            self._voice_material_show("수동 준비표 미리보기 · 실물 검증/사용 승인 대기",
                                      plan.outline(self._voice_material_rights))
        except (ValueError, TypeError, KeyError) as exc:
            self._voice_material_show("입력 확인 실패", str(exc))

    def _check_voice_material_rights(self) -> None:
        try:
            review = load_rights_review(rights_review_path())
            if review is None or review.source != VOICES[self._voice.get()]:
                self._voice_material_rights = None
                self._voice_material_show("권리 체크 미확인 · 출처 불일치 또는 기록 없음",
                                          "실물 법적 권리·사용 승인을 확인하지 않았습니다. 준비표 초안은 작성 가능합니다.")
                return
            self._voice_material_rights = review
            self._voice_material_show("41단계 권리 자체 신고 수동 조회 · 실제 사용 승인 대기",
                                      self._voice_material_current().outline(review))
        except (ValueError, KeyError, OSError) as exc:
            self._voice_material_rights = None
            self._voice_material_show("권리 체크 수동 조회 실패", str(exc))

    def _save_voice_material(self) -> None:
        try:
            plan = self._voice_material_current()
            if not messagebox.askyesno("음성 준비표 초안 저장", "별칭과 예상 길이만 로컬 JSON에 저장할까요?\n"
                                     "실제 음성 파일을 찾거나 수집하지 않으며 학습·방송도 승인하지 않습니다.", parent=self):
                self._voice_material_status.set("저장 취소 · 기존 준비표 유지")
                return
            save_material_plan(material_plan_path(), plan, operator_confirmed=True)
            self._voice_material_show("확인 후 준비표 초안 저장 · 실제 사용 승인 대기",
                                      plan.outline(self._voice_material_rights))
        except (ValueError, KeyError, OSError, PermissionError) as exc:
            self._voice_material_show("저장 실패 · 기존 준비표 유지", str(exc))

    def _load_voice_material(self) -> None:
        try:
            saved = load_material_plan(material_plan_path())
            if saved is None:
                self._voice_material_show("저장된 준비표 없음", "수동으로 저장한 자료 목록이 없습니다.")
                return
            if saved.source != VOICES[self._voice.get()]:
                self._voice_material_show("음성 선택 불일치 · 불러오기 차단",
                                          "다른 출처에 저장된 자료별칭은 재사용할 수 없습니다. 현재 입력은 유지됩니다.")
                return
            self._voice_material_lines.delete("1.0", "end")
            self._voice_material_lines.insert("1.0", "\n".join(f"{item.alias} | {item.declared_seconds}" for item in saved.items))
            self._voice_material_note.delete(0, "end")
            self._voice_material_note.insert(0, saved.note)
            self._voice_material_show("같은 출처 준비표 수동 불러오기 · 사용 승인 대기",
                                      saved.outline(self._voice_material_rights))
        except (ValueError, KeyError, OSError) as exc:
            self._voice_material_show("불러오기 실패 · 기존 입력 유지", str(exc))

    def _delete_voice_material(self) -> None:
        if not messagebox.askyesno("준비표 삭제 1/2", "별도 음성 준비표 JSON만 삭제할까요?", parent=self):
            return
        if not messagebox.askyesno("준비표 삭제 2/2", "최종 삭제할까요? 음성 자료와 기존 설정은 건드리지 않습니다.", parent=self):
            return
        try:
            deleted = delete_material_plan(material_plan_path(), operator_confirmed=True)
            self._voice_material_show("준비표 삭제 완료" if deleted else "삭제할 준비표 없음",
                                      "현재 입력·권리 기록·방송 설정·SQLite 기억은 유지됩니다.")
        except (ValueError, OSError) as exc:
            self._voice_material_show("준비표 삭제 실패", str(exc))

    def _reset_voice_material(self) -> None:
        self._voice_material_lines.delete("1.0", "end")
        self._voice_material_note.delete(0, "end")
        self._voice_material_show("입력 초기화 · 저장된 준비표 유지",
                                  "새 자료별칭을 수동으로 입력할 수 있습니다. 저장 파일은 변경하지 않았습니다.")

    def _build_preferences_review(self, tab) -> None:
        ttk.Label(tab, text="32단계 · 성격·취향 프롬프트 미리보기 (저장/AI 호출 없음)").pack(anchor="w")
        self._preference_likes = tk.StringVar()
        self._preference_dislikes = tk.StringVar()
        for title, variable in (("좋아하는 것 (선택)", self._preference_likes), ("싫어하는 것 (선택)", self._preference_dislikes)):
            ttk.Label(tab, text=title).pack(anchor="w")
            ttk.Entry(tab, textvariable=variable).pack(fill="x")
        ttk.Button(tab, text="현재 캐릭터·취향 미리보기", command=self._run_preferences_review).pack(anchor="w", pady=8)
        self._preferences_status = tk.StringVar(value="미실행 · 입력은 저장되지 않습니다")
        ttk.Label(tab, textvariable=self._preferences_status).pack(anchor="w")
        self._preferences_text = tk.Text(tab, height=14, state="disabled", wrap="word")
        self._preferences_text.pack(fill="both", expand=True)

    def _run_preferences_review(self) -> None:
        try:
            mode = PERSONA_MODES[self._persona_mode.get()]
            draft = {key: entry.get() for key, entry in self._persona.items()}
            report = review_preferences(mode, draft, self._preference_likes.get(), self._preference_dislikes.get())
            message = report.describe()
            self._preferences_status.set("미리보기 완료 · 저장/모델 연결 없음")
        except (ValueError, TypeError, KeyError) as exc:
            message = "입력 오류: " + str(exc)
            self._preferences_status.set("입력 확인 실패")
        self._preferences_text.configure(state="normal")
        self._preferences_text.delete("1.0", "end")
        self._preferences_text.insert("1.0", message)
        self._preferences_text.configure(state="disabled")

    def _build_persona_input_review(self, tab) -> None:
        ttk.Label(tab, text="31단계 · 현재 캐릭터 입력 및 프롬프트 확인 (저장 없음)").pack(anchor="w")
        ttk.Button(tab, text="현재 선택 캐릭터 확인", command=self._run_persona_input_review).pack(anchor="w", pady=8)
        self._persona_input_status = tk.StringVar(value="미실행 · 사용자 요청 시에만 확인")
        ttk.Label(tab, textvariable=self._persona_input_status).pack(anchor="w")
        self._persona_input_text = tk.Text(tab, height=15, state="disabled", wrap="word")
        self._persona_input_text.pack(fill="both", expand=True)

    def _run_persona_input_review(self) -> None:
        try:
            mode = PERSONA_MODES[self._persona_mode.get()]
            draft = {key: entry.get() for key, entry in self._persona.items()}
            message = review_persona_input(mode, draft).describe()
            self._persona_input_status.set("입력 검증 통과 · 실제 AI 미연결")
        except (ValueError, TypeError, KeyError) as exc:
            message = "캐릭터 입력 확인 실패: " + str(exc)
            self._persona_input_status.set("입력 확인 실패")
        self._persona_input_text.configure(state="normal")
        self._persona_input_text.delete("1.0", "end")
        self._persona_input_text.insert("1.0", message)
        self._persona_input_text.configure(state="disabled")

    def _build_brain_review(self, tab) -> None:
        ttk.Label(tab, text="30단계 · AI 두뇌 1차 점검 (모의 전용)").pack(anchor="w")
        ttk.Button(tab, text="오프라인 모의 두뇌 점검", command=self._run_brain_review).pack(anchor="w", pady=8)
        self._brain_review_status = tk.StringVar(value="미실행 · 자동 PC 조회 없음")
        ttk.Label(tab, textvariable=self._brain_review_status).pack(anchor="w")
        self._brain_review_text = tk.Text(tab, height=15, state="disabled", wrap="word")
        self._brain_review_text.pack(fill="both", expand=True)

    def _run_brain_review(self) -> None:
        try:
            report = review_brain(self.settings)
            message = report.describe()
            self._brain_review_status.set("모의 점검 통과 · 실제 모델 미검증" if report.mock_ready else "모의 점검 실패")
        except (ValueError, TypeError, KeyError):
            message = "점검 실패: 설정 확인 필요 (실제 연결 없음)"
            self._brain_review_status.set("점검 실패")
        self._brain_review_text.configure(state="normal")
        self._brain_review_text.delete("1.0", "end")
        self._brain_review_text.insert("1.0", message)
        self._brain_review_text.configure(state="disabled")

    def _build_continuity(self, tab) -> None:
        ttk.Label(tab, text="29단계 · 저장 기록과 새 대화 연속성 확인",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="사용자가 검증 버튼을 누를 때만 전용 응답 기록 DB를 읽습니다. "
                  "가장 최근 저장 세션의 성공 응답을 새 채팅에 전달할 맥락으로 구조 검사합니다. "
                  "DB 변경·AI 호출·PC 정보 조회·실제 방송은 없습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        self._continuity_script = tk.Text(tab, height=5, wrap="word")
        self._continuity_script.pack(fill="x")
        self._continuity_script.insert("1.0", "시청자: 지난 대화를 이어서 할까요?\n시청자: 방금 질문을 다시 할게요.")
        ttk.Button(tab, text="저장 기록 읽고 연속성 구조 검증 (수동)",
                   command=self._run_continuity).pack(anchor="w", pady=8)
        self._continuity_status = tk.StringVar(value="미실행 · DB 자동 접근 없음")
        ttk.Label(tab, textvariable=self._continuity_status, wraplength=710).pack(anchor="w")
        self._continuity_view = tk.Text(tab, height=14, wrap="word", state="disabled")
        self._continuity_view.pack(fill="both", expand=True)

    def _run_continuity(self) -> None:
        try:
            report = check_saved_continuity(
                ResponseRecordStore(response_records_path()),
                self._continuity_script.get("1.0", "end-1c"))
            message = report.describe()
            self._continuity_status.set("구조 검증 통과" if report.passed else "구조 검증 실패")
        except (OSError, ValueError, sqlite3.DatabaseError) as exc:
            message = "검증 불가: " + str(exc)
            self._continuity_status.set("검증 불가 · 기존 기록 변경 없음")
        self._continuity_view.configure(state="normal")
        self._continuity_view.delete("1.0", "end")
        self._continuity_view.insert("1.0", message)
        self._continuity_view.configure(state="disabled")

    def _build_response_records(self, tab) -> None:
        """28단계: 성공한 모의 코어 답변을 사용자 확인 후에만 별도 로컬 DB에 기록."""
        ttk.Label(tab, text="28단계 · 모의 응답 기록 수동 저장",
                  font=("Malgun Gothic", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="기본 코어 수동 실행 탭에서 성공한 답변만 저장합니다. "
                  "저장·조회·삭제 버튼을 누르기 전에는 DB를 만들거나 읽지 않습니다. "
                  "기존 방송 설정/SQLite 기억은 건드리지 않으며 자동 저장·실제 방송·AI 연결은 없습니다.",
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, text="전용 저장 경로: " + str(response_records_path()),
                  wraplength=710).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=(0, 8))
        ttk.Button(row, text="저장 후보 미리보기", command=self._preview_response_records).pack(side="left")
        ttk.Button(row, text="확인 후 응답 저장", command=self._save_response_records).pack(side="left", padx=(7, 0))
        ttk.Button(row, text="저장 기록 30건 조회", command=self._load_response_records).pack(side="left", padx=(7, 0))
        ttk.Button(row, text="전체 기록 삭제 (2회 확인)", command=self._clear_response_records).pack(side="right")
        self._response_record_status = tk.StringVar(value="미실행 · 저장/조회/삭제 자동 실행 없음")
        ttk.Label(tab, textvariable=self._response_record_status, wraplength=710).pack(anchor="w", pady=(0, 8))
        self._response_record_view = tk.Text(tab, height=15, wrap="word", state="disabled",
                                             font=("Malgun Gothic", 10))
        self._response_record_view.pack(fill="both", expand=True)
        self._set_response_record_report("기록 저장은 기본 꺼짐입니다. 먼저 모의 코어에서 대본을 수동 실행하세요.\n"
                                         "이전 응답은 별도 확인 전까지 PC에 기록되지 않습니다.")

    def _set_response_record_report(self, report: str) -> None:
        self._response_record_view.configure(state="normal")
        self._response_record_view.delete("1.0", "end")
        self._response_record_view.insert("1.0", report)
        self._response_record_view.configure(state="disabled")

    def _preview_response_records(self) -> None:
        try:
            if self._core_session is None:
                raise ValueError("먼저 기본 코어 수동 실행 탭에서 모의 답변을 생성해 주세요.")
            snapshot = snapshot_core_responses(self._core_session)
        except (TypeError, ValueError) as exc:
            self._response_record_status.set("저장 후보 없음 · 파일 접근 없음")
            self._set_response_record_report(str(exc))
            return
        self._response_record_status.set(f"성공 응답 {len(snapshot.records)}건 미리보기 · 아직 저장하지 않음")
        self._set_response_record_report(snapshot.describe())

    def _save_response_records(self) -> None:
        try:
            if self._core_session is None:
                raise ValueError("저장할 모의 코어 성공 답변이 없습니다.")
            snapshot = snapshot_core_responses(self._core_session)
        except (TypeError, ValueError) as exc:
            self._response_record_status.set("저장 후보 없음 · DB 변경 없음")
            self._set_response_record_report(str(exc))
            return
        if not messagebox.askyesno(
            "응답 기록 저장 확인",
            f"성공한 모의 답변 {len(snapshot.records)}건을 내 PC의 별도 SQLite에 저장할까요?\n"
            "닉네임·채팅 내용·답변이 기록됩니다.\n"
            "실패/대기 입력, 설정, 기존 기억은 저장/변경하지 않습니다.\n\n"
            + str(response_records_path()), parent=self,
        ):
            self._response_record_status.set("저장 취소 · 파일 변경 없음")
            return
        try:
            result = ResponseRecordStore(response_records_path()).save(snapshot, confirmed=True)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._response_record_status.set("저장 실패 · 기존 응답 기록 유지")
            self._set_response_record_report("저장 실패: " + str(exc))
            return
        self._response_record_status.set(
            f"신규 {result.inserted}건 · 기존 중복 {result.already_saved}건 · 총 {result.total_in_file}건")
        self._set_response_record_report("사용자 확인 후 별도 DB 저장 완료.\n"
                                         "기존 설정·SQLite 기억·대기열·모의 이력은 그대로입니다.\n"
                                         "실제 모델/방송 연결 없음.")

    def _load_response_records(self) -> None:
        try:
            rows = ResponseRecordStore(response_records_path()).recent(30)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._response_record_status.set("기록 조회 실패 · DB 변경 없음")
            self._set_response_record_report("조회 실패: " + str(exc))
            return
        self._response_record_status.set(f"저장 기록 최근 {len(rows)}건 조회 · 읽기 전용")
        self._set_response_record_report(
            "저장 기록이 없습니다." if not rows else
            "28단계 · 별도 SQLite 응답 기록 (최근 저장 순서, 최대 30건)\n\n" +
            "\n\n".join(f"#{row.turn_no} {row.sender}: {row.input_text}\nAI(모의): {row.reply_text}"
                         for row in rows))

    def _clear_response_records(self) -> None:
        if not messagebox.askyesno(
            "기록 삭제 1차 확인", "28단계 전용 SQLite에 저장된 응답 기록을 모두 삭제할까요?\n"
            "기존 채팅 기억/설정은 그대로 유지됩니다.", parent=self,
        ):
            self._response_record_status.set("기록 삭제 취소 · 변경 없음")
            return
        if not messagebox.askyesno(
            "기록 삭제 최종 확인", "삭제한 응답 기록은 이 화면에서 복구할 수 없습니다.\n"
            "정말 전용 응답 기록을 전부 삭제할까요?", parent=self,
        ):
            self._response_record_status.set("최종 확인 취소 · 변경 없음")
            return
        try:
            count = ResponseRecordStore(response_records_path()).clear(confirmed=True)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self._response_record_status.set("삭제 실패 · 다른 사용자 데이터 변경 없음")
            self._set_response_record_report("삭제 실패: " + str(exc))
            return
        self._response_record_status.set(f"확인 후 전용 응답 기록 {count}건 삭제")
        self._set_response_record_report("전용 응답 기록만 삭제했습니다. 기존 설정·SQLite 기억·모의 세션은 그대로입니다.")

    def _build_development_review(self, tab) -> None:
        """10단계는 승인 강제 없이 사전 검토만 제공; 사용자 명시 클릭만 기록."""
        ttk.Label(tab, text="10단계 · 전체 개발 기준 최종 검토", font=("Malgun Gothic", 13, "bold")).pack(
            anchor="w", pady=(2, 8))
        ttk.Label(tab, text="이 단계는 개발 설계 기준만 확인합니다. 실제 방송·PC 설치·결제·계정 연결은 별도 승인 사항입니다.",
                  wraplength=690).pack(anchor="w", pady=(0, 8))
        self._review_text = tk.Text(tab, height=17, wrap="word", state="disabled",
                                    font=("Malgun Gothic", 9))
        self._review_text.pack(fill="both", expand=True, pady=(0, 9))
        ttk.Button(tab, text="개발 기준 검사 (PC 내부 파일만 읽기)", command=self._refresh_review).pack(
            anchor="w", pady=(0, 5))
        self._review_confirmation = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            tab, variable=self._review_confirmation,
            text="나는 설계 기준만 검토했으며, 실제 방송·설치·결제는 별도 승인해야 함을 이해합니다.",
        ).pack(anchor="w", pady=(5, 5))
        row = ttk.Frame(tab)
        row.pack(anchor="w", pady=(0, 9))
        ttk.Button(row, text="개발 기준 최종 승인 기록 (수동)", command=self._approve_review).pack(side="left")
        ttk.Button(row, text="내 PC 승인 기록 취소", command=self._revoke_review).pack(
            side="left", padx=(8, 0))
        self._review_status = tk.StringVar(value="검사 전 · 승인 기록 자동 생성 안 함")
        ttk.Label(tab, textvariable=self._review_status, wraplength=690).pack(anchor="w")
        self._review_report = None

    def _review_has_unsaved_changes(self) -> bool:
        """화면에서 바꾼 미저장 선택값을 과거 설정 기준으로 승인하지 않도록 방지."""
        try:
            viewed = {
                "platforms": [code for code, check in self._platforms.items() if check.get()],
                "content": CONTENTS[self._content.get()],
                "avatar": AVATARS[self._avatar.get()],
                "voice": VOICES[self._voice.get()],
                "persona_mode": PERSONA_MODES[self._persona_mode.get()],
                "persona": {key: item.get().strip() for key, item in self._persona.items()},
                "voice_profile": validate_voice_profile({
                    "installed_voice_name": self._voice_preferred_name,
                    "rate": int(self._voice_rate.get()),
                    "volume": int(self._voice_volume.get()),
                }),
            }
        except (ValueError, KeyError, TypeError):
            return True
        return any(viewed[key] != self.settings[key] for key in viewed)

    def _refresh_review(self) -> None:
        """운영자가 검사 버튼을 누른 때에만 번들 내 정책/로드맵을 읽는다."""
        self._review_report = None
        if self._review_has_unsaved_changes():
            self._review_status.set("방송 설정에 저장되지 않은 변경이 있습니다 · 승인 기록 생성 차단")
            self._review_text.configure(state="normal")
            self._review_text.delete("1.0", "end")
            self._review_text.insert("1.0", "10단계 검토는 마지막 PC 저장 설정 기준입니다.\n"
                                              "먼저 '방송 설정'에서 변경한 내용을 저장하거나 되돌려 주세요.\n"
                                              "미저장 설정으로 잘못된 승인 기록을 만들지 않습니다.")
            self._review_text.configure(state="disabled")
            return
        try:
            policy, roadmap = load_review_sources()
            report = evaluate_review(policy, roadmap, self.settings)
            self._review_report = report
            approved, approval_message = approval_status(report, approval_path())
            message = report.describe()
            message += "\n\n현재 PC 승인 기록: " + approval_message
            message += "\n(이 기록은 신원 인증/전자서명이 아니며 PC 저장 확인용입니다.)"
            self._review_status.set(
                "현재 검토 항목 전부 통과 · " + ("수동 승인 기록 있음" if approved else "운영자 승인 대기")
                if report.ready else "검토 항목 오류 · 승인 기록 생성 차단"
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            message = "검토 자료를 읽지 못했습니다. 승인 기록 생성이 차단됩니다.\n" + str(exc)
            self._review_status.set("검토 실패 · 승인 불가")
        self._review_text.configure(state="normal")
        self._review_text.delete("1.0", "end")
        self._review_text.insert("1.0", message)
        self._review_text.configure(state="disabled")

    def _approve_review(self) -> None:
        """체크박스와 재검사 및 확인 대화상자를 거쳐야 수동 기록을 저장한다."""
        if not self._review_confirmation.get():
            messagebox.showwarning("검토 확인 필요", "먼저 설계 기준의 범위를 확인하고 체크해 주세요.", parent=self)
            return
        self._refresh_review()
        if self._review_report is None or not self._review_report.ready:
            messagebox.showwarning("승인 불가", "기획 기준 검사를 모두 통과한 뒤 승인할 수 있습니다.", parent=self)
            return
        if not messagebox.askyesno(
            "10단계 최종 검토 확인",
            "AISTING 개발 기준만 확인하여 이 PC에 승인 기록을 저장할까요?\n"
            "이것은 방송 시작, PC 설치, 유료 결제, 계정 연결 승인이 아닙니다.",
            parent=self,
        ):
            return
        try:
            record_approval(self._review_report, approval_path(), operator_confirmed=True)
        except (OSError, ValueError, PermissionError) as exc:
            messagebox.showerror("PC 승인 기록 실패", str(exc), parent=self)
            return
        self._review_confirmation.set(False)
        self._refresh_review()
        self._status.set("10단계 개발 기준에 대한 사용자 수동 확인만 PC에 저장했어. 실제 방송은 시작되지 않아.")

    def _revoke_review(self) -> None:
        if not messagebox.askyesno(
            "개발 기준 승인 기록 취소",
            "PC에 남긴 설계 기준 승인 기록만 삭제할까요? 기타 설정/대화 기억은 유지됩니다.", parent=self,
        ):
            return
        try:
            revoke_approval(approval_path(), operator_confirmed=True)
        except OSError as exc:
            messagebox.showerror("취소 실패", str(exc), parent=self)
            return
        self._review_confirmation.set(False)
        self._refresh_review()
        self._status.set("개발 기준 승인 기록을 취소했어. 기존 PC 설정과 대화 기억은 유지했어.")

    def _build_about(self, tab) -> None:
        info = (
            "독립 Windows 프로그램 소스 개발본\n\n"
            "현재 기능: 플랫폼·콘텐츠·기본/직접 캐릭터 선택과 PC 로컬 저장 · 모의 시청자 채팅 FIFO · "
            "선택적 로컬 AI 텍스트 테스트 · PC 기본 한국어 음성 수동 미리 듣기 · 간단한 2D 샘플\n\n"
            "아직 미구현: 실제 스트리밍 플랫폼 채팅 수신, OBS 자동 송출, "
            "정밀 립싱크, 완전한 무인 방송\n\n"
            "네트워크: 기본 모드 0회. 로컬 AI를 직접 선택해 시작한 경우에만 "
            "127.0.0.1로 요청\n\n"
            "운영 정책: 모든 채팅 순서 처리 · 임의 응답 지연 없음 · 비용 0원 · "
            "외부 계정 연동/설치/예약 없음"
        )
        ttk.Label(tab, text=info, justify="left", wraplength=680,
                  font=("Malgun Gothic", 11)).pack(anchor="w", pady=20)


def main() -> None:
    AistingApp().mainloop()
