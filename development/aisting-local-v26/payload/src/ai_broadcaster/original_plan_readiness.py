"""Inspect *real, existing* Open-LLM-VTuber configuration and Live2D assets.

No network, server start, installation, audio capture/playback or file writes.
This is a PRE-FLIGHT static inspection, never proof of working AI, voice or
avatar animation. The user's actual runtime remains the acceptance test.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .original_plan_studio import StageOneUnavailable, check_official_project


@dataclass(frozen=True)
class CoreFileInspection:
    character_name: str
    agent_type: str
    llm_backend: str
    tts_engine: str
    live2d_model_name: str
    live2d_asset_files: int
    issues: tuple[str, ...]


def _read_utf8(path: Path, limit: int = 2_000_000) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise StageOneUnavailable(f'기존 파일 없음/링크/비정상 크기: {path.name}')
    try:
        return path.read_text('utf-8-sig')
    except (OSError, UnicodeError) as exc:
        raise StageOneUnavailable(f'기존 파일을 읽을 수 없음: {path.name}') from exc


def _select_block(lines: list[str], parent: tuple[int, int], key: str, level: int) -> tuple[int, int]:
    """Select a unique, exact-indentation YAML map without evaluating YAML.

    Only the official upstream flat keys are inspected; unknown or advanced
    YAML constructs produce 'unknown', not a guessed configuration. All source
    is preserved byte-for-byte.
    """
    start, stop = parent
    prefix = ' ' * level
    pattern = re.compile(r'^' + re.escape(prefix + key) + r':(?:\s|$)')
    hits = [i for i in range(start, stop) if pattern.match(lines[i])]
    if len(hits) != 1:
        raise StageOneUnavailable(f'공식 YAML 경로 확인 실패: {key} (일치 {len(hits)})')
    at = hits[0]
    for idx in range(at + 1, stop):
        line = lines[idx]
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        width = len(line) - len(line.lstrip(' '))
        if width <= level:
            return at + 1, idx
    return at + 1, stop


def _scalar(lines: list[str], parent: tuple[int, int], key: str, level: int) -> str:
    start, stop = parent
    prefix = ' ' * level
    pat = re.compile(r'^' + re.escape(prefix + key) + r':\s*(.*)$')
    matches = [m.group(1) for i in range(start, stop) if (m := pat.match(lines[i]))]
    if len(matches) != 1:
        raise StageOneUnavailable(f'공식 YAML 값 확인 실패: {key}')
    raw = matches[0].strip()
    if raw.startswith("'"):
        m = re.fullmatch(r"'((?:[^']|'')*)'(?:\s*#.*)?", raw)
        if not m:
            raise StageOneUnavailable(f'읽을 수 없는 YAML 값: {key}')
        return m.group(1).replace("''", "'")
    if raw.startswith('"'):
        decoder = json.JSONDecoder()
        try:
            value, end = decoder.raw_decode(raw)
        except ValueError as exc:
            raise StageOneUnavailable(f'읽을 수 없는 YAML 값: {key}') from exc
        if not isinstance(value, str) or (raw[end:].strip() and not raw[end:].lstrip().startswith('#')):
            raise StageOneUnavailable(f'읽을 수 없는 YAML 값: {key}')
        return value
    value = raw.split(' #', 1)[0].strip()
    if not value or value[0] in '|>&*![{':
        raise StageOneUnavailable(f'단일 값이 아닌 YAML 필드: {key}')
    return value


def _contained_regular_file(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or '..' in relative.parts:
        raise StageOneUnavailable('Live2D 모델 파일에 프로젝트 밖 경로가 있습니다.')
    target = root / relative
    if target.is_symlink() or not target.is_file():
        raise StageOneUnavailable('필수 Live2D 모델 파일 없음: ' + str(relative))
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise StageOneUnavailable('Live2D 파일이 공식 프로젝트 밖을 가리킵니다.')
    return target


def _live2d_assets(model: dict[str, Any], root: Path, model_path: Path) -> int:
    """Check the actual Cubism model3.json asset references, not a thumbnail."""
    refs = model.get('FileReferences')
    if not isinstance(refs, dict) or not isinstance(refs.get('Moc'), str):
        raise StageOneUnavailable('Live2D 모델에서 실제 Cubism Moc 참조를 찾을 수 없습니다.')
    required: list[str] = [refs['Moc']]
    for key in ('Physics', 'Pose', 'UserData', 'DisplayInfo'):
        if key in refs:
            if not isinstance(refs[key], str):
                raise StageOneUnavailable('Live2D 파일 참조 형식이 잘못되었습니다: ' + key)
            required.append(refs[key])
    for key in ('Textures', 'Expressions'):
        items = refs.get(key, [])
        if not isinstance(items, list):
            raise StageOneUnavailable('Live2D 파일 목록 형식 오류: ' + key)
        for item in items:
            value = item if key == 'Textures' else (item.get('File') if isinstance(item, dict) else None)
            if not isinstance(value, str):
                raise StageOneUnavailable('Live2D 파일 참조 오류: ' + key)
            required.append(value)
    motions = refs.get('Motions', {})
    if not isinstance(motions, dict):
        raise StageOneUnavailable('Live2D 모션 목록 오류')
    for entries in motions.values():
        if not isinstance(entries, list):
            raise StageOneUnavailable('Live2D 모션 그룹 형식 오류')
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get('File'), str):
                raise StageOneUnavailable('Live2D 모션 파일 형식 오류')
            required.append(entry['File'])
    count = 0
    for name in required:
        if not name or '\\' in name:
            raise StageOneUnavailable('Live2D 경로 형식 오류')
        rel = model_path.parent / Path(name)
        _contained_regular_file(root, rel)
        count += 1
    return count


def inspect_existing_official_core(folder: str | Path) -> CoreFileInspection:
    """Inspect only files selected by operator; no mutation or runtime probes."""
    root = check_official_project(folder)
    text = _read_utf8(root / 'conf.yaml')
    lines = text.splitlines()
    all_lines = (0, len(lines))
    character = _select_block(lines, all_lines, 'character_config', 0)
    name = _scalar(lines, character, 'character_name', 2)
    model_name = _scalar(lines, character, 'live2d_model_name', 2)
    tts = _select_block(lines, character, 'tts_config', 2)
    engine = _scalar(lines, tts, 'tts_model', 4)
    agent = _select_block(lines, character, 'agent_config', 2)
    agent_type = _scalar(lines, agent, 'conversation_agent_choice', 4)
    llm = '확인되지 않음 (선택한 에이전트별 설정 확인 필요)'
    if agent_type == 'basic_memory_agent':
        agents = _select_block(lines, agent, 'agent_settings', 4)
        memory = _select_block(lines, agents, 'basic_memory_agent', 6)
        llm = _scalar(lines, memory, 'llm_provider', 8)

    issues: list[str] = []
    if engine == 'gpt_sovits_tts':
        # Only inspect reference settings; do not contact the model API or
        # access audio bytes. A valid path is not proof of voice synthesis.
        try:
            sovits = _select_block(lines, tts, 'gpt_sovits_tts', 4)
            ref_path = _scalar(lines, sovits, 'ref_audio_path', 6)
            prompt_text = _scalar(lines, sovits, 'prompt_text', 6)
            if not ref_path:
                issues.append('GPT-SoVITS의 참조 음성 경로가 비어 있습니다.')
            else:
                ref = Path(ref_path)
                if not ref.is_absolute():
                    issues.append('GPT-SoVITS 참조 음성은 상대경로: 실제 음성 서버 측 경로 확인 필요')
                elif ref.is_symlink() or not ref.is_file():
                    issues.append('GPT-SoVITS의 실제 참조 음성 파일을 찾을 수 없습니다.')
                else:
                    from .original_plan_tts import (inspect_reference_audio_container,
                                                     VoiceConfigurationError)
                    try:
                        inspect_reference_audio_container(ref)
                    except VoiceConfigurationError as exc:
                        issues.append('GPT-SoVITS 참조 음성 컨테이너 오류: ' + str(exc))
            if not prompt_text:
                issues.append('GPT-SoVITS 참조 음성의 실제 녹음 문구가 비어 있습니다.')
        except StageOneUnavailable as exc:
            issues.append('GPT-SoVITS 설정 확인 실패: ' + str(exc))
    count = 0
    try:
        index = json.loads(_read_utf8(root / 'model_dict.json'))
        if not isinstance(index, list):
            raise StageOneUnavailable('model_dict.json 목록 형식 오류')
        matches = [e for e in index if isinstance(e, dict) and e.get('name') == model_name]
        if len(matches) != 1:
            raise StageOneUnavailable('현재 지정된 Live2D 모델이 공식 목록에 유일하게 존재하지 않습니다.')
        url = matches[0].get('url')
        if not isinstance(url, str) or not url.startswith('/live2d-models/') or not url.endswith('.model3.json'):
            raise StageOneUnavailable('선택한 Live2D 모델 경로가 공식 로컬 형식이 아닙니다.')
        model_path = Path(url.lstrip('/'))
        model_file = _contained_regular_file(root, model_path)
        model = json.loads(_read_utf8(model_file))
        if not isinstance(model, dict):
            raise StageOneUnavailable('Live2D 모델 정의가 유효한 JSON 객체가 아닙니다.')
        count = _live2d_assets(model, root, model_path)
    except (OSError, UnicodeError, ValueError, StageOneUnavailable) as exc:
        issues.append(str(exc))
    return CoreFileInspection(name, agent_type, llm, engine, model_name, count, tuple(issues))
