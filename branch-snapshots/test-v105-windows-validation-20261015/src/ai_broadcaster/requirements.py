"""단계 1: 기획안 핵심 불변 조건과 100단계 로드맵 검증.

외부 패키지나 방송 플랫폼 계정은 사용하지 않습니다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def validate(config: dict[str, Any], roadmap: dict[str, Any]) -> list[str]:
    """핵심 기획과 충돌하는 설정 또는 로드맵 오류를 한국어 문자열로 반환."""
    errors: list[str] = []
    defaults = config.get('defaults', {})
    expected_defaults = {
        'respond_to_all_chats': True,
        'forced_response_delay': False,
        'preemptively_skip_chats': False,
        'operator_judges_naturalness': True,
    }
    for key, expected in expected_defaults.items():
        if defaults.get(key) is not expected:
            errors.append(f'핵심 원칙 위반: defaults.{key} = {expected!r} 필요')

    controls = config.get('control', {})
    disallowed = (
        'install_without_operator_approval',
        'charge_without_operator_approval',
        'publish_without_operator_approval',
        'broadcast_enabled_by_default',
        'clone_voice_without_permission',
    )
    for key in disallowed:
        if controls.get(key) is not False:
            errors.append(f'운영자 승인 원칙 위반: control.{key}는 false 필수')
    if controls.get('operator_decisions_require_approval') is not True:
        errors.append('설치·계정·비용 등 운영자 결정 사항의 승인이 필요합니다.')

    # 9단계: 운영 서버는 내 PC이고, GitHub는 프로그램의 실행 서버가 아니다.
    if config.get('operator_decisions', {}).get('hosting_option') != 'local_pc':
        errors.append('9단계 PC 로컬 운영: 실행 장소는 내 PC여야 하며 원격 서버 의존은 허용하지 않습니다.')
    step_nine = next((step for step in roadmap.get('steps', []) if step.get('number') == 9), {})
    if (step_nine.get('status') != 'completed' or 'PC 로컬' not in step_nine.get('title', '')):
        errors.append('9단계 PC 로컬 운영 방식의 구현 및 검증 상태를 유지해 주세요.')

    # 운영자가 플랫폼을 개발 전에 하나 고르는 게 아니다. 런타임 복수 선택 방식이 확정됐다.
    if config.get('operator_decisions', {}).get('broadcast_platform') != 'runtime_multi_select_optional':
        errors.append('방송 플랫폼은 프로그램 내 복수 선택(미선택 허용) 방식이어야 합니다.')
    choices = config.get('operator_decisions', {})
    choice_modes = {
        'content_concept': 'runtime_select_chat_game_both',
        'persona': 'runtime_default_or_custom',
        'avatar_type_and_asset': 'runtime_choose_2d_or_3d_asset_use_requires_approval',
    }
    for choice, expected in choice_modes.items():
        if choices.get(choice) != expected:
            errors.append(f'선택형 설정 원칙 위반: {choice}')
    step_three = next((step for step in roadmap.get('steps', []) if step.get('number') == 3), {})
    if (step_three.get('status') != 'completed' or
            '프로그램 내 자유로운 복수 선택' not in step_three.get('title', '')):
        errors.append('3단계는 플랫폼 사전 확정이 아닌 프로그램 선택형 설계 완료 상태여야 합니다.')

    step_four = next((step for step in roadmap.get('steps', []) if step.get('number') == 4), {})
    if (step_four.get('status') != 'completed' or
            '수다·게임·둘 다·미선택' not in step_four.get('title', '')):
        errors.append('4단계는 방송 콘텐츠 4가지 런타임 선택형 설정 검증 완료 상태여야 합니다.')

    step_five = next((step for step in roadmap.get('steps', []) if step.get('number') == 5), {})
    if (step_five.get('status') != 'completed' or
            '기본값/직접 만들기 선택형' not in step_five.get('title', '')):
        errors.append('5단계는 캐릭터 기본값/직접 만들기 런타임 선택형 구현 완료여야 합니다.')

    # 6단계도 특정 성격·말투를 사전에 하나 확정하는 게 아니라 편집 가능한 초안이다.
    step_six = next((step for step in roadmap.get('steps', []) if step.get('number') == 6), {})
    if (step_six.get('status') != 'completed' or
            '운영자 선택형' not in step_six.get('title', '')):
        errors.append('6단계는 운영자 선택형 성격·말투 초안 작성 완료 상태여야 합니다.')

    # 7단계도 특정 목소리를 고르는 사전 확정이 아니라, 프로그램에서 선택/변경하는 방식이다.
    if choices.get('voice_source_and_consent') != 'runtime_optional_source_no_clone_without_permission':
        errors.append('목소리 확보 방식은 프로그램 안에서 선택하며, 승인 없이 복제할 수 없습니다.')
    step_seven = next((step for step in roadmap.get('steps', []) if step.get('number') == 7), {})
    if (step_seven.get('status') != 'completed' or
            '선택형 설정' not in step_seven.get('title', '')):
        errors.append('7단계 목소리 확보 방식은 프로그램 내 선택형으로 검증되어야 합니다.')

    # 8단계도 형태 자체를 미리 정하는 게 아니다. 미정/2D/3D를 PC에서 선택·변경.
    step_eight = next((step for step in roadmap.get('steps', []) if step.get('number') == 8), {})
    if (step_eight.get('status') != 'completed' or
            '선택형 설정' not in step_eight.get('title', '')):
        errors.append('8단계 아바타 형태는 프로그램 내 미정/2D/3D 선택형이어야 합니다.')

    steps = roadmap.get('steps', [])
    if roadmap.get('total_steps') != 100 or len(steps) != 100:
        errors.append('로드맵은 정확히 100단계여야 합니다.')
    numbers = [s.get('number') for s in steps]
    if numbers != list(range(1, 101)):
        errors.append('단계 번호는 1~100까지 연속이어야 합니다.')
    allowed_statuses = {'pending', 'in_progress', 'blocked', 'review', 'completed'}
    for step in steps:
        if not step.get('title') or step.get('status') not in allowed_statuses:
            errors.append(f"단계 내용 또는 상태 오류: {step.get('number')}")
    return errors


def status(roadmap: dict[str, Any]) -> dict[str, Any]:
    steps = roadmap['steps']
    completed = sum(s['status'] == 'completed' for s in steps)
    current = next((s for s in steps if s['status'] != 'completed'), None)
    return {'completed': completed, 'total': len(steps), 'current': current}


def validate_features(features: dict[str, Any]) -> list[str]:
    """Validate the legacy feature inventory without activating any integrations.

    This schema describes *planned* capabilities, not verified live features.
    """
    if not isinstance(features, dict):
        return ['기능 목록은 JSON 객체여야 합니다.']
    errors: list[str] = []
    all_ids: set[str] = set()
    for section in ('required', 'optional'):
        items = features.get(section)
        if not isinstance(items, list):
            errors.append(f'{section}는 목록이어야 합니다.')
            continue
        if section == 'required' and not items:
            errors.append('필수 기능 목록은 비어 있을 수 없습니다.')
        for index, item in enumerate(items):
            key = item.get('id') if isinstance(item, dict) else None
            if not isinstance(key, str) or not key.strip():
                errors.append(f'{section}[{index}]의 ID가 잘못됐습니다.')
            elif key in all_ids:
                errors.append(f'중복 기능 ID: {key}')
            else:
                all_ids.add(key)
    mandatory_ids = {'conversation', 'chat', 'tts', 'avatar', 'broadcast',
                     'lifecycle', 'notices', 'memory', 'operations'}
    required_ids = {
        item.get('id') for item in features.get('required', [])
        if isinstance(item, dict) and isinstance(item.get('id'), str)
    } if isinstance(features.get('required'), list) else set()
    for missing in sorted(mandatory_ids - required_ids):
        errors.append(f'필수 기능 누락: {missing}')
    actions = features.get('no_default_actions')
    if not isinstance(actions, list) or '실제 방송 시작' not in actions:
        errors.append('실제 방송은 승인 없이 시작할 수 없습니다.')
    return errors
