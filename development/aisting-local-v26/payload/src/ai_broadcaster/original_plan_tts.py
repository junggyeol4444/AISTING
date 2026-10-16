"""Actual Open-LLM-VTuber GPT-SoVITS configuration (original plan section 7-3).

This is a surgical patch of the real upstream conf.yaml, *not* a fake voice
engine. There are no downloads, model training, network calls or audio here.
Only a user-approved change to an existing official upstream configuration.
"""
from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import urlsplit

from .original_plan_studio import check_official_project, _quoted_yaml
from .original_plan_config_io import decode_official_utf8, replace_official_config_with_backup


class VoiceConfigurationError(ValueError):
    """The official installation or rights-approved material is incomplete."""


def inspect_reference_audio_container(reference_audio: Path) -> str:
    """Read-only check of an existing WAV/FLAC *container*, not voice quality.

    A filename extension alone is not enough to configure the real GPT-SoVITS
    engine. Read only container headers; never decode, play or train on audio.
    Do not infer rights, language, intelligibility or model compatibility.
    """
    path = Path(reference_audio)
    if path.is_symlink() or not path.is_file():
        raise VoiceConfigurationError('실제 참조 음성 일반 파일이 필요합니다 (링크 제외).')
    size = path.stat().st_size
    suffix = path.suffix.lower()
    if suffix not in ('.wav', '.flac'):
        raise VoiceConfigurationError('WAV 또는 FLAC 참조 음성을 선택하세요.')
    try:
        with path.open('rb') as audio:
            if suffix == '.flac':
                header = audio.read(8)
                if len(header) != 8 or header[:4] != b'fLaC' or (header[4] & 0x7f) != 0:
                    raise VoiceConfigurationError('FLAC STREAMINFO 헤더를 찾지 못했습니다.')
                length = int.from_bytes(header[5:8], 'big')
                if length != 34 or size < 8 + length:
                    raise VoiceConfigurationError('FLAC STREAMINFO 길이가 유효하지 않습니다.')
                streaminfo = audio.read(34)
                min_block = int.from_bytes(streaminfo[:2], 'big')
                max_block = int.from_bytes(streaminfo[2:4], 'big')
                sample_rate = int.from_bytes(streaminfo[10:13], 'big') >> 4
                if min_block < 16 or max_block < min_block or sample_rate == 0:
                    raise VoiceConfigurationError('FLAC 음성 형식 메타데이터가 유효하지 않습니다.')
                return f'FLAC 헤더 확인 · {sample_rate}Hz · {size}바이트 (실제 합성 미검증)'
            head = audio.read(12)
            if len(head) != 12 or head[:4] not in (b'RIFF', b'RF64') or head[8:] != b'WAVE':
                raise VoiceConfigurationError('WAV RIFF/RF64 WAVE 헤더를 찾지 못했습니다.')
            declared_end = 8 + int.from_bytes(head[4:8], 'little')
            if head[:4] == b'RIFF' and declared_end > size:
                raise VoiceConfigurationError('WAV 선언된 길이가 실제 파일보다 큽니다.')
            riff_end = size if head[:4] == b'RF64' else declared_end
            if riff_end < 44:
                raise VoiceConfigurationError('WAV 헤더가 손상되었거나 비어 있습니다.')
            found_fmt = False
            found_data = False
            sample_rate = 0
            while audio.tell() + 8 <= riff_end:
                chunk = audio.read(8)
                if len(chunk) != 8:
                    break
                tag, length = chunk[:4], int.from_bytes(chunk[4:], 'little')
                position = audio.tell()
                if tag == b'fmt ':
                    if length < 16 or position + 16 > size:
                        raise VoiceConfigurationError('WAV fmt 청크가 손상되었습니다.')
                    fields = audio.read(16)
                    channels = int.from_bytes(fields[2:4], 'little')
                    sample_rate = int.from_bytes(fields[4:8], 'little')
                    if int.from_bytes(fields[:2], 'little') == 0 or channels == 0 or sample_rate == 0:
                        raise VoiceConfigurationError('WAV 음성 형식 정보가 유효하지 않습니다.')
                    found_fmt = True
                if tag == b'data' and length > 0:
                    if head[:4] == b'RF64' or position + length <= size:
                        found_data = True
                next_pos = position + length + (length & 1)
                if next_pos > riff_end or next_pos <= position:
                    if tag == b'data' and head[:4] == b'RF64' and found_data:
                        break  # RF64 data length may be 0xffffffff; ds64 holds real length.
                    raise VoiceConfigurationError('WAV 청크 길이가 실제 파일 크기와 맞지 않습니다.')
                audio.seek(next_pos)
            if not (found_fmt and found_data):
                raise VoiceConfigurationError('WAV fmt/data 음성 청크가 존재하지 않습니다.')
            return f'WAV 헤더 확인 · {sample_rate}Hz · {size}바이트 (실제 합성 미검증)'
    except OSError as exc:
        raise VoiceConfigurationError('참조 음성 파일을 읽을 수 없습니다.') from exc


def validate_local_gpt_sovits_url(api_url: str) -> str:
    """Only explicit loopback GPT-SoVITS endpoints; no paid/remote API guess."""
    if not isinstance(api_url, str) or len(api_url) > 512 or api_url != api_url.strip():
        raise VoiceConfigurationError('GPT-SoVITS API 주소를 확인하세요.')
    try:
        parsed = urlsplit(api_url)
        port = parsed.port
    except ValueError as exc:
        raise VoiceConfigurationError('GPT-SoVITS API 포트가 올바르지 않습니다.') from exc
    if (parsed.scheme != 'http' or not 1 <= (port or 0) <= 65535 or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or port is None or parsed.username is not None or parsed.password is not None
            or parsed.path != '/tts' or parsed.query or parsed.fragment):
        raise VoiceConfigurationError('승인되지 않은 외부/유료 API를 사용하지 않습니다. 로컬 http://127.0.0.1:포트/tts만 허용합니다.')
    return api_url


def make_official_gpt_sovits_config(source: str, reference_audio: Path, reference_text: str,
                                    *, api_url: str = 'http://127.0.0.1:9880/tts') -> str:
    """Edit only the official GPT-SoVITS keys; keep all LLM and Live2D keys.

    Requires explicit existing local WAV/FLAC + matching spoken transcript.
    Training a voice clone remains a separate authorized operator step.
    """
    ref = Path(reference_audio)
    inspect_reference_audio_container(ref)
    api_url = validate_local_gpt_sovits_url(api_url)
    if not isinstance(reference_text, str) or not 1 <= len(reference_text.strip()) <= 500:
        raise VoiceConfigurationError('실제 참조 음성에 녹음된 문장을 입력하세요 (1~500자).')
    try:
        _quoted_yaml(reference_text.strip())
    except ValueError as exc:
        raise VoiceConfigurationError(str(exc)) from exc
    if not isinstance(source, str) or not source:
        raise VoiceConfigurationError('공식 conf.yaml이 비어 있습니다.')
    lines = source.splitlines(keepends=True)
    ending = '\r\n' if '\r\n' in source else '\n'
    # Upstream Open-LLM-VTuber config_templates/conf.default.yaml:
    # character_config: (0), tts_config: (2), tts_model (4),
    # gpt_sovits_tts: (4), voice options (6).
    config_locs = [i for i, line in enumerate(lines) if re.match(r'^character_config:(?:\s|$)', line)]
    if len(config_locs) != 1:
        raise VoiceConfigurationError('공식 character_config 구성을 찾을 수 없습니다.')
    # Validate actual hierarchy, not just arbitrary keys anywhere in YAML.
    top = config_locs[0]
    end = next((i for i in range(top + 1, len(lines)) if lines[i].strip()
                and not lines[i].startswith((' ', '#'))), len(lines))
    tts_matches = [i for i in range(top + 1, end)
                   if re.match(r'^  tts_config:(?:\s|$)', lines[i])]
    if len(tts_matches) != 1:
        raise VoiceConfigurationError('공식 character_config.tts_config가 없습니다.')
    tts_start = tts_matches[0] + 1
    tts_end = next((i for i in range(tts_start, end) if lines[i].strip()
                    and not lines[i].startswith(('    ', '      ', '        ', '#'))), end)
    sub = lines[tts_start:tts_end]
    tts_model_matches = [i for i, line in enumerate(sub)
                         if re.match(r'^    tts_model:(?:\s|$)', line)]
    sovits_matches = [i for i, line in enumerate(sub)
                      if re.match(r'^    gpt_sovits_tts:(?:\s|$)', line)]
    if len(tts_model_matches) != 1 or len(sovits_matches) != 1:
        raise VoiceConfigurationError('공식 TTS 엔진/gpt_sovits_tts 항목 불일치')
    engine_i = tts_start + tts_model_matches[0]
    block_i = tts_start + sovits_matches[0]
    block_end = next((i for i in range(block_i + 1, tts_end)
                      if lines[i].strip() and re.match(r'^    \S', lines[i])), tts_end)
    options = {
        'api_url': api_url,
        'text_lang': 'ko',
        'ref_audio_path': str(ref.resolve(strict=True)),
        'prompt_lang': 'ko',
        'prompt_text': reference_text.strip(),
    }
    # Preserve formatting and all original downstream TTS/LLM/Live2D fields.
    for key, value in options.items():
        matches = [i for i in range(block_i + 1, block_end)
                   if re.match(r'^      ' + re.escape(key) + r':(?:\s|$)', lines[i])]
        if len(matches) != 1:
            raise VoiceConfigurationError('기존 GPT-SoVITS 설정 필드 누락/중복: ' + key)
        lines[matches[0]] = '      ' + key + ': ' + _quoted_yaml(value) + ending
    lines[engine_i] = "    tts_model: 'gpt_sovits_tts'" + ending
    return ''.join(lines)


def apply_official_gpt_sovits(folder: str | Path, reference_audio: Path,
                              reference_text: str, *,
                              api_url: str = 'http://127.0.0.1:9880/tts') -> tuple[Path, Path | None]:
    """Write actual official conf.yaml after explicit operator approval.

    Keep a unique original byte-for-byte backup and fail on concurrent edits.
    """
    root = check_official_project(folder)
    conf = root / 'conf.yaml'
    if conf.is_symlink() or not conf.is_file():
        raise VoiceConfigurationError('공식 conf.yaml 일반 파일이 필요합니다.')
    before = conf.read_bytes()
    if len(before) > 1_000_000:
        raise VoiceConfigurationError('conf.yaml이 비정상적으로 큽니다.')
    try:
        original_text, bom = decode_official_utf8(before)
        updated = make_official_gpt_sovits_config(original_text,
                                                  reference_audio, reference_text, api_url=api_url)
        after = bom + updated.encode('utf-8')
        backup = replace_official_config_with_backup(conf, before, after, label='gpt-sovits')
    except (UnicodeError, ValueError, OSError, RuntimeError) as exc:
        raise VoiceConfigurationError(str(exc)) from exc
    return conf, backup
