"""Actual Open-LLM-VTuber GPT-SoVITS configuration (original plan section 7-3).

This is a surgical patch of the real upstream conf.yaml, *not* a fake voice
engine. There are no downloads, model training, network calls or audio here.
Only a user-approved change to an existing official upstream configuration.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
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
                # STREAMINFO alone is not an audio recording. Follow the
                # actual FLAC metadata chain without decoding, playing or
                # training; require a plausible first audio-frame sync after
                # the final metadata block. A frame sync is NOT a sound/voice
                # quality guarantee (decoding belongs to the real TTS engine).
                last_metadata = bool(header[4] & 0x80)
                while not last_metadata:
                    block = audio.read(4)
                    if len(block) != 4 or (block[0] & 0x7f) in (0, 127):
                        raise VoiceConfigurationError('FLAC 메타데이터 블록이 손상되었습니다.')
                    length = int.from_bytes(block[1:4], 'big')
                    if audio.tell() + length > size:
                        raise VoiceConfigurationError('FLAC 메타데이터 길이가 실제 파일보다 큽니다.')
                    last_metadata = bool(block[0] & 0x80)
                    audio.seek(length, 1)
                if size - audio.tell() < 8:
                    raise VoiceConfigurationError('FLAC 파일에 실제 음성 프레임이 없습니다.')
                frame_sync = audio.read(2)
                if frame_sync[0] != 0xff or (frame_sync[1] & 0xfe) != 0xf8:
                    raise VoiceConfigurationError('FLAC 메타데이터 뒤에 음성 프레임이 없습니다.')
                return f'FLAC 헤더 확인 · {sample_rate}Hz · {size}바이트 (실제 합성 미검증)'
            head = audio.read(12)
            if len(head) != 12 or head[:4] not in (b'RIFF', b'RF64') or head[8:] != b'WAVE':
                raise VoiceConfigurationError('WAV RIFF/RF64 WAVE 헤더를 찾지 못했습니다.')
            declared_end = 8 + int.from_bytes(head[4:8], 'little')
            if head[:4] == b'RIFF' and declared_end != size:
                # Bytes outside the RIFF container are not part of the
                # reference recording, even when its fmt/data chunks decode.
                raise VoiceConfigurationError('WAV 선언된 길이가 실제 파일 크기와 다릅니다.')
            rf64 = head[:4] == b'RF64'
            if rf64 and head[4:8] != b'\xff' * 4:
                raise VoiceConfigurationError('RF64 파일 크기 표식이 유효하지 않습니다.')
            riff_end = size if rf64 else declared_end
            rf64_data_size = None
            ds64_seen = False
            if riff_end < 44:
                raise VoiceConfigurationError('WAV 헤더가 손상되었거나 비어 있습니다.')
            found_fmt = False
            found_data = False
            data_chunks = 0
            sample_rate = 0
            pcm_frame_size = None
            while audio.tell() + 8 <= riff_end:
                chunk = audio.read(8)
                if len(chunk) != 8:
                    break
                tag, length = chunk[:4], int.from_bytes(chunk[4:], 'little')
                position = audio.tell()
                if rf64 and tag == b'ds64':
                    if ds64_seen or length < 28 or position + length > size:
                        raise VoiceConfigurationError('RF64 ds64 청크가 손상되었습니다.')
                    header64 = audio.read(28)
                    declared_riff64, rf64_data_size, _samples64, table_count = (
                        int.from_bytes(header64[:8], 'little'),
                        int.from_bytes(header64[8:16], 'little'),
                        int.from_bytes(header64[16:24], 'little'),
                        int.from_bytes(header64[24:28], 'little'),
                    )
                    if (table_count > (length - 28) // 12
                            or declared_riff64 + 8 != size
                            or declared_riff64 + 8 < position + length
                            or rf64_data_size < 1):
                        raise VoiceConfigurationError('RF64 실제 데이터 길이가 잘못되었습니다.')
                    riff_end = declared_riff64 + 8
                    ds64_seen = True
                if tag == b'fmt ':
                    if found_fmt:
                        raise VoiceConfigurationError('WAV fmt 청크가 중복되었습니다.')
                    if length < 16 or position + 16 > size:
                        raise VoiceConfigurationError('WAV fmt 청크가 손상되었습니다.')
                    fields = audio.read(16)
                    format_tag = int.from_bytes(fields[:2], 'little')
                    channels = int.from_bytes(fields[2:4], 'little')
                    sample_rate = int.from_bytes(fields[4:8], 'little')
                    byte_rate = int.from_bytes(fields[8:12], 'little')
                    block_align = int.from_bytes(fields[12:14], 'little')
                    bits_per_sample = int.from_bytes(fields[14:16], 'little')
                    if format_tag == 0 or channels == 0 or sample_rate == 0:
                        raise VoiceConfigurationError('WAV 음성 형식 정보가 유효하지 않습니다.')
                    if format_tag == 0xfffe:
                        # WAVE_FORMAT_EXTENSIBLE is a common Windows recorder
                        # format. Its 16-byte base header is not sufficient:
                        # the extra 24 bytes identify the actual PCM/float
                        # encoding and valid sample/channel layout. Without
                        # this check malformed or unknown audio was accepted
                        # as a rights-approved GPT-SoVITS reference.
                        if length < 40 or position + 40 > riff_end:
                            raise VoiceConfigurationError('WAV 확장 fmt 청크가 잘렸습니다.')
                        extension = audio.read(24)
                        if len(extension) != 24:
                            raise VoiceConfigurationError('WAV 확장 fmt 데이터가 잘렸습니다.')
                        extension_size = int.from_bytes(extension[:2], 'little')
                        valid_bits = int.from_bytes(extension[2:4], 'little')
                        channel_mask = int.from_bytes(extension[4:8], 'little')
                        subtype = extension[8:24]
                        if extension_size < 22 or extension_size > length - 18:
                            raise VoiceConfigurationError('WAV 확장 fmt 길이가 잘못되었습니다.')
                        if subtype == bytes.fromhex('0100000000001000800000aa00389b71'):
                            format_tag = 1  # WAVE_FORMAT_PCM subtype
                        elif subtype == bytes.fromhex('0300000000001000800000aa00389b71'):
                            format_tag = 3  # WAVE_FORMAT_IEEE_FLOAT subtype
                        else:
                            raise VoiceConfigurationError('WAV 확장 fmt 인코딩을 지원하지 않습니다.')
                        if (not 1 <= valid_bits <= bits_per_sample
                                or (format_tag == 3 and valid_bits != bits_per_sample)
                                or (channel_mask != 0 and channel_mask.bit_count() != channels)):
                            raise VoiceConfigurationError('WAV 확장 샘플·채널 정보가 유효하지 않습니다.')
                    # For uncompressed PCM/IEEE-float WAV, header fields must
                    # describe the same number of bytes per audio frame.
                    # GPT-SoVITS uses the selected reference in its real
                    # decoder; a corrupt fmt header must not pass inspection.
                    # Leave compressed/extended WAV format-specific parsing
                    # to the real decoder instead of guessing its layout.
                    if format_tag in (1, 3):
                        if (bits_per_sample == 0 or bits_per_sample % 8
                                or (format_tag == 3 and bits_per_sample not in (32, 64))):
                            raise VoiceConfigurationError('WAV PCM/float 비트 깊이가 잘못되었습니다.')
                        pcm_frame_size = channels * (bits_per_sample // 8)
                        if (block_align != pcm_frame_size
                                or byte_rate != sample_rate * pcm_frame_size):
                            raise VoiceConfigurationError('WAV PCM/float 프레임·전송률 정보가 일치하지 않습니다.')
                    found_fmt = True
                actual_length = length
                if rf64 and tag == b'data':
                    if not ds64_seen or rf64_data_size is None:
                        raise VoiceConfigurationError('RF64 ds64 정보 없이 음성 데이터를 읽을 수 없습니다.')
                    if length == 0xffffffff:
                        actual_length = rf64_data_size
                    elif length != rf64_data_size:
                        raise VoiceConfigurationError('RF64 데이터 길이 정보가 서로 다릅니다.')
                if tag == b'data':
                    data_chunks += 1
                    if data_chunks > 1:
                        raise VoiceConfigurationError('WAV data 청크가 중복되었습니다.')
                if tag == b'data' and not found_fmt:
                    # Standard RIFF/RF64 decoders (including Python wave) need
                    # the format description before the audio payload. Do not
                    # accept a reference the real decoder cannot open.
                    raise VoiceConfigurationError('WAV fmt 청크보다 data 청크가 먼저 나왔습니다.')
                if tag == b'data' and actual_length > 0:
                    if pcm_frame_size is not None and actual_length % pcm_frame_size:
                        raise VoiceConfigurationError('WAV PCM/float data 길이가 프레임 크기와 맞지 않습니다.')
                    if position + actual_length <= riff_end:
                        found_data = True
                next_pos = position + actual_length + (actual_length & 1)
                if next_pos > riff_end or next_pos <= position:
                    raise VoiceConfigurationError('WAV 청크 길이가 실제 파일 크기와 맞지 않습니다.')
                audio.seek(next_pos)
            if audio.tell() != riff_end:
                # The old loop silently accepted 1..7 leftover bytes that
                # could not even form a complete RIFF chunk header.
                raise VoiceConfigurationError('WAV 마지막 청크 헤더가 잘렸습니다.')
            if rf64 and not ds64_seen:
                raise VoiceConfigurationError('RF64 ds64 크기 정보를 찾지 못했습니다.')
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
@dataclass(frozen=True)
class ActualGptSovitsSynthesis:
    """Result from real local inference; no speaker output, OBS, or avatar implied."""
    sample_rate: int
    channels: int
    frame_count: int
    wav_bytes: int


def synthesize_local_gpt_sovits(
    reference_audio: Path,
    reference_text: str,
    utterance: str,
    *,
    api_url: str = "http://127.0.0.1:9880/tts",
    operator_approved: bool = False,
    rights_confirmed: bool = False,
    play_to_speaker: bool = False,
    timeout: float = 120.0,
) -> ActualGptSovitsSynthesis:
    """Call the ACTUAL GPT-SoVITS inference engine with upstream-compatible args.

    A separate one-shot operator confirmation must approve using the local
    voice material and generating speech. No upload to remote hosts, model
    training, file writes, or OBS actions. Speaker preview additionally
    requires explicit opt-in. The official frontend remains the owner of
    Live2D playback/lip-sync during actual conversation.
    """
    if operator_approved is not True or rights_confirmed is not True:
        raise PermissionError("사용 권리 확인과 이번 실제 음성 합성 승인이 모두 필요합니다.")
    # The separate speaker opt-in must be an actual boolean. An accidental
    # truthy value must never silently turn into a synth-only request.
    if type(play_to_speaker) is not bool:
        raise VoiceConfigurationError("스피커 미리듣기 승인 값이 올바르지 않습니다.")
    if not isinstance(utterance, str) or not 1 <= len(utterance.strip()) <= 200:
        raise VoiceConfigurationError("시험 발화는 1~200글자여야 합니다.")
    if any(ord(ch) < 32 for ch in utterance):
        raise VoiceConfigurationError("시험 발화에 제어 문자를 사용할 수 없습니다.")
    if type(timeout) not in (int, float) or not 1 <= timeout <= 180:
        raise VoiceConfigurationError("실제 합성 제한 시간이 잘못되었습니다.")
    ref = Path(reference_audio)
    inspect_reference_audio_container(ref)
    if not isinstance(reference_text, str) or not 1 <= len(reference_text.strip()) <= 500:
        raise VoiceConfigurationError("참조 음성의 실제 녹음 문장을 입력해야 합니다.")
    endpoint = validate_local_gpt_sovits_url(api_url)
    import http.client
    from io import BytesIO
    from urllib.parse import urlencode, urlsplit
    import wave
    parts = urlsplit(endpoint)
    params = {
        "text": utterance.strip(),
        "text_lang": "ko",
        "ref_audio_path": str(ref.resolve(strict=True)),
        "prompt_lang": "ko",
        "prompt_text": reference_text.strip(),
        "text_split_method": "cut5",
        "batch_size": "1",
        "media_type": "wav",
        "streaming_mode": "false",
    }
    target = "/tts?" + urlencode(params)
    # The endpoint was already restricted to loopback above. Respect its
    # actual address family (127.0.0.1 / localhost / ::1), and let http.client
    # generate the matching Host header including the non-default port.
    conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=float(timeout))
    try:
        conn.request("GET", target, headers={
            "Accept": "audio/wav, audio/x-wav, application/octet-stream"
        })
        response = conn.getresponse()
        if response.status != 200:
            raise VoiceConfigurationError(
                "GPT-SoVITS 실제 합성 HTTP 상태 오류: " + str(response.status)
            )
        # A small test utterance still has bounded, potentially large output.
        # http.client.read(amount) may return a *short* body without raising
        # IncompleteRead, even when Content-Length advertises more bytes.
        # A complete WAV prefix must not conceal a truncated HTTP response.
        declared_http_length = response.getheader("Content-Length")
        content = response.read(20_000_001)
        if len(content) > 20_000_000:
            raise VoiceConfigurationError("합성 음성이 20MB 상한을 초과했습니다.")
        # In chunked HTTP responses the decoded payload length takes precedence.
        if declared_http_length is not None and not response.chunked:
            if (not declared_http_length.isdecimal()
                    or int(declared_http_length) != len(content)):
                raise VoiceConfigurationError("GPT-SoVITS HTTP 응답 길이가 실제 수신 데이터와 다릅니다.")
        if len(content) < 44 or content[:4] != b"RIFF" or content[8:12] != b"WAVE":
            raise VoiceConfigurationError("GPT-SoVITS가 실제 WAV 음성을 반환하지 않았습니다.")
        # Python's wave decoder can accept a RIFF header claiming *more*
        # bytes than the HTTP response actually contains, provided the PCM
        # data chunk itself is complete. Such a file is structurally broken
        # and may fail in the actual Windows audio path. Reject it before
        # reporting successful synthesis or playing any sound.
        riff_end = 8 + int.from_bytes(content[4:8], "little")
        if riff_end < 44 or riff_end != len(content):
            # A complete HTTP body may still contain bytes outside its RIFF
            # container (including an appended second WAV). Such bytes are
            # not part of the decoded audio; do not report a clean voice file.
            raise VoiceConfigurationError("GPT-SoVITS 합성 WAV의 RIFF 선언 길이가 실제 응답과 다릅니다.")
        # Python wave reads the FIRST data chunk and silently ignores later
        # RIFF chunks, including a second data chunk. It also rounds down an
        # odd-sized 16-bit/stereo PCM chunk to whole frames. Verify the exact
        # chunk boundaries before treating the HTTP response as usable audio.
        chunk_offset = 12
        data_sizes = []
        fmt_count = 0
        extensible_pcm_fmt_offset = None
        while chunk_offset < riff_end:
            if chunk_offset + 8 > riff_end:
                raise VoiceConfigurationError("GPT-SoVITS 합성 WAV 청크 헤더가 잘렸습니다.")
            chunk_tag = content[chunk_offset:chunk_offset + 4]
            chunk_size = int.from_bytes(content[chunk_offset + 4:chunk_offset + 8], "little")
            chunk_start = chunk_offset + 8
            chunk_end = chunk_start + chunk_size
            padded_end = chunk_end + (chunk_size & 1)
            if padded_end > riff_end:
                raise VoiceConfigurationError("GPT-SoVITS 합성 WAV 청크 크기가 잘못되었습니다.")
            if chunk_tag == b"fmt ":
                fmt_count += 1
                if fmt_count != 1 or chunk_size < 16 or data_sizes:
                    # Python wave uses the first fmt chunk. A second or late
                    # conflicting fmt must not be passed to Windows playback.
                    raise VoiceConfigurationError("GPT-SoVITS 합성 WAV fmt 청크가 중복·손상되었습니다.")
                fmt = content[chunk_start:chunk_end]
                format_tag = int.from_bytes(fmt[0:2], "little")
                channels = int.from_bytes(fmt[2:4], "little")
                rate = int.from_bytes(fmt[4:8], "little")
                byte_rate = int.from_bytes(fmt[8:12], "little")
                block_align = int.from_bytes(fmt[12:14], "little")
                bits = int.from_bytes(fmt[14:16], "little")
                if format_tag == 0xfffe:
                    # Windows WAVE_FORMAT_EXTENSIBLE PCM: validate its actual
                    # subtype rather than treating the 0xfffe tag as PCM.
                    pcm_guid = bytes.fromhex('0100000000001000800000aa00389b71')
                    extension_size = int.from_bytes(fmt[16:18], "little") if chunk_size >= 18 else 0
                    valid_bits = int.from_bytes(fmt[18:20], "little") if chunk_size >= 20 else 0
                    channel_mask = int.from_bytes(fmt[20:24], "little") if chunk_size >= 24 else 0
                    if (chunk_size < 40 or not 22 <= extension_size <= chunk_size - 18
                            or not 1 <= valid_bits <= bits
                            or (channel_mask != 0 and channel_mask.bit_count() != channels)
                            or fmt[24:40] != pcm_guid):
                        raise VoiceConfigurationError("GPT-SoVITS 합성 WAV fmt 확장 PCM 형식이 잘못되었습니다.")
                    extensible_pcm_fmt_offset = chunk_start
                elif format_tag != 1:
                    raise VoiceConfigurationError("GPT-SoVITS 합성 WAV fmt PCM 인코딩이 아닙니다.")
                if (channels < 1 or rate < 1 or bits < 8 or bits % 8
                        or block_align != channels * (bits // 8)
                        or byte_rate != rate * block_align):
                    # wave.open ignores corrupt block-align and byte-rate
                    # headers even though Windows audio devices use them.
                    raise VoiceConfigurationError("GPT-SoVITS 합성 WAV fmt 프레임·전송률 정보가 잘못되었습니다.")
            if chunk_tag == b"data":
                if fmt_count != 1:
                    raise VoiceConfigurationError("GPT-SoVITS 합성 WAV fmt 이전에 data 청크가 있습니다.")
                data_sizes.append(chunk_size)
            chunk_offset = padded_end
        if fmt_count != 1 or len(data_sizes) != 1:
            raise VoiceConfigurationError("GPT-SoVITS 합성 WAV fmt/data 청크는 각각 정확히 하나여야 합니다.")
        # Python 3.11's wave reader does not recognize WAVE_FORMAT_EXTENSIBLE
        # (0xfffe), even when its subtype is ordinary PCM. All 40-byte fmt
        # fields, subtype, channels, bit depth, rate and frame boundaries have
        # already been checked above. Decode an IN-MEMORY inspection copy with
        # the equivalent PCM tag; keep the original upstream WAV bytes intact
        # for any separately approved Windows speaker playback.
        decoder_content = content
        if extensible_pcm_fmt_offset is not None:
            at = extensible_pcm_fmt_offset
            decoder_content = content[:at] + b'\x01\x00' + content[at + 2:]
        with wave.open(BytesIO(decoder_content), "rb") as wav:
            if (wav.getnframes() < 1 or wav.getframerate() < 1
                    or wav.getnchannels() < 1 or wav.getsampwidth() < 1):
                raise VoiceConfigurationError("합성 WAV에 유효한 소리 프레임이 없습니다.")
            # A RIFF header can claim valid frames even if the HTTP body ends
            # mid-audio. Verify the *actual* PCM data before reporting success.
            expected_pcm_bytes = wav.getnframes() * wav.getnchannels() * wav.getsampwidth()
            if data_sizes[0] != expected_pcm_bytes:
                raise VoiceConfigurationError("GPT-SoVITS 합성 WAV data 길이가 PCM 프레임과 맞지 않습니다.")
            pcm = wav.readframes(wav.getnframes())
            if len(pcm) != expected_pcm_bytes:
                raise VoiceConfigurationError("GPT-SoVITS 합성 WAV의 실제 음성 프레임이 잘렸습니다.")
            # A syntactically valid WAV may contain nothing but digital silence.
            # For unsigned 8-bit PCM the silent midpoint is 0x80; signed PCM
            # (16/24/32-bit) uses all-zero samples. Do not report this as an
            # audible voice response or attempt the approved speaker preview.
            if (all(value == 128 for value in pcm) if wav.getsampwidth() == 1
                    else not any(pcm)):
                raise VoiceConfigurationError("GPT-SoVITS 합성 WAV에 실제 음성 신호가 없습니다.")
            # A constant nonzero PCM value (including stereo DC offsets) is
            # not speech. Check changes across *frames*, not across channels:
            # two constant stereo channels can differ while both are DC.
            frame_size = wav.getnchannels() * wav.getsampwidth()
            first_frame = pcm[:frame_size]
            if wav.getnframes() > 1 and pcm == first_frame * wav.getnframes():
                raise VoiceConfigurationError("GPT-SoVITS 합성 WAV에 시간에 따른 음성 신호 변화가 없습니다.")
            report = ActualGptSovitsSynthesis(
                sample_rate=wav.getframerate(),
                channels=wav.getnchannels(),
                frame_count=wav.getnframes(),
                wav_bytes=len(content),
            )
        if play_to_speaker is True:
            # Only an explicitly approved, one-shot Windows speaker preview.
            # SND_MEMORY plays directly from bounded WAV bytes: no files,
            # no recording, no broadcasting, and no training side effects.
            import sys
            if sys.platform != 'win32':
                raise VoiceConfigurationError('실제 스피커 재생은 Windows 전용입니다.')
            try:
                import winsound
                winsound.PlaySound(
                    content, winsound.SND_MEMORY | winsound.SND_NODEFAULT
                )
            except (OSError, RuntimeError, ImportError) as exc:
                raise VoiceConfigurationError('Windows에서 GPT-SoVITS 음성 재생을 완료하지 못했습니다.') from exc
        return report
    except (OSError, http.client.HTTPException, EOFError, wave.Error) as exc:
        raise VoiceConfigurationError("실제 로컬 GPT-SoVITS 요청 또는 WAV 검사 실패") from exc
    finally:
        conn.close()
