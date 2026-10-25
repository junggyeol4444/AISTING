"""권리 확인된 동일 실제 GPT-SoVITS PCM WAV로 공식 Cubism 입 움직임 구동.

AISTING의 기존 Windows WebView2 안에 이미 열린 공식 Live2D 모델만 사용.
한 건의 실제 PCM 음량 윤곽을 공식 _wavFileHandler.getRms() 경로에
한시적으로 전달한다. 가짜 모델·음성·입 관측값은 생성하지 않는다.
JS 콜백이 실제 renderer에서 호출되고 Cubism 파라미터가 변화했는지
별도로 관찰한다. OBS 화면 캡처·송출·시청자 수신은 여기서 증명 못 한다.
"""
from __future__ import annotations

import json
import math
import re

from .voice_waveform_meter_match import _rms_pcm16_windows

_TOKEN = re.compile(r"[0-9a-f]{32}\Z")


def authorized_pcm_envelope(wav_bytes: bytes) -> tuple[float, ...]:
    """실제 반환된 16-bit PCM WAV 전체를 최대 8초 관찰 범위에서만 처리."""
    result = _rms_pcm16_windows(wav_bytes)
    if (not 8 <= len(result) <= 160 or max(result) < 0.01
            or len(result) < 8 or any(not math.isfinite(x) for x in result)):
        raise ValueError(
            "공식 Cubism에 연결할 16비트 PCM WAV(0.4~8초)의 유효 음량이 없습니다.")
    return tuple(round(x, 6) for x in result)


def _valid_token(token: str) -> bool:
    return type(token) is str and _TOKEN.fullmatch(token) is not None


def start_pcm_driver_script(envelope: tuple[float, ...], token: str) -> str:
    """원본 Cubism 모델의 음성 입 매개변수 경로만 일시 구동한다."""
    if not _valid_token(token):
        raise ValueError("승인된 동일 발화 요청 식별자가 유효하지 않습니다.")
    if (not isinstance(envelope, tuple) or not 8 <= len(envelope) <= 160
            or any(type(x) not in (float, int)
                   or not math.isfinite(x) or not 0 <= x <= 1
                   for x in envelope)):
        raise ValueError("실제 WAV 음량 배열 형식이 유효하지 않습니다.")
    data = json.dumps(envelope, separators=(",", ":"))
    nonce = json.dumps(token)
    # The official WebGL model remains the actual renderer. We only provide
    # this authorized PCM envelope as its short-lived getRms() input.
    return (
        "(() => {"
        "if(location.origin!=='http://127.0.0.1:12393')return {ok:false};"
        "if(window.__aistingAuthorizedPcm)return {ok:false};"
        "const manager=window.getLive2DManager?.()||"
        "window.LAppLive2DManager?.getInstance?.();"
        "const model=manager?.getModel?.(0);"
        "const ids=model?._lipSyncIds;"
        "const wav=model?._wavFileHandler;"
        "const canvas=document.getElementById('canvas');"
        "if(!canvas||canvas.width<1||canvas.height<1||!model||"
        "model._lipsync!==true||!ids||ids.getSize?.()<1||"
        "typeof wav?.getRms!=='function'||"
        "typeof model?._model?.getParameterValueById!=='function')"
        "return {ok:false};"
        "let previous;"
        "try{previous=Number(wav.getRms());}catch(_e){return {ok:false};}"
        "if(!Number.isFinite(previous)||previous>0.02)return {ok:false};"
        "const levels=" + data + ";"
        "const token=" + nonce + ";"
        "const original=wav.getRms;"
        "const started=performance.now();"
        "const state={token,model,wav,original,started,closed:false,"
        "calls:0,positiveCalls:0,samples:0,changes:0,"
        "firstMouth:null,lastMouth:null,low:null,high:null,"
        "lastParameter:null,timer:null,expiry:null,reason:null};"
        "const cleanup=()=>{if(state.closed)return;"
        "state.closed=true;"
        "if(wav.getRms===state.wrapper)wav.getRms=original;"
        "if(state.timer!==null)clearInterval(state.timer);"
        "if(state.expiry!==null)clearTimeout(state.expiry);};"
        "state.cleanup=cleanup;"
        "state.wrapper=function(){"
        "const elapsed=performance.now()-started;"
        "if(manager.getModel(0)!==model){state.reason='모델변경';cleanup();return 0;}"
        "if(elapsed>=levels.length*50){state.reason='끝';cleanup();return 0;}"
        "const index=Math.floor(Math.max(0,elapsed)/50);"
        "const value=levels[index]||0;"
        "state.calls++;if(value>0.01)state.positiveCalls++;"
        "return value;};"
        "wav.getRms=state.wrapper;"
        "state.timer=setInterval(()=>{"
        "if(state.closed)return;"
        "try{"
        "const actual=Number(model._model.getParameterValueById(ids.at(0)));"
        "if(!Number.isFinite(actual))return;"
        "state.samples++;"
        "state.low=state.low===null?actual:Math.min(state.low,actual);"
        "state.high=state.high===null?actual:Math.max(state.high,actual);"
        "if(state.lastParameter!==null&&Math.abs(state.lastParameter-actual)>0.01){"
        "state.changes++;const now=performance.now();"
        "if(state.firstMouth===null)state.firstMouth=now;"
        "state.lastMouth=now;}"
        "state.lastParameter=actual;"
        "}catch(_error){state.reason='실제모델값오류';cleanup();}"
        "},50);"
        "state.expiry=setTimeout(()=>{"
        "if(!state.closed){state.reason='시간초과';cleanup();}"
        "},levels.length*50+1000);"
        "window.__aistingAuthorizedPcm=state;"
        "return {ok:true,token,lipSyncIds:ids.getSize(),duration:levels.length*0.05};"
        "})()"
    )


def finish_pcm_driver_script(token: str) -> str:
    """실제 관찰 수치 반환 후 원본 음성 입 구동 함수를 무조건 복원."""
    if not _valid_token(token):
        raise ValueError("완료할 동일 발화 식별자가 유효하지 않습니다.")
    nonce = json.dumps(token)
    return (
        "(() => {"
        "const state=window.__aistingAuthorizedPcm;"
        "if(!state||state.token!==" + nonce + ")return {ok:false};"
        "state.cleanup();"
        "delete window.__aistingAuthorizedPcm;"
        "return {ok:true,calls:state.calls,positiveCalls:state.positiveCalls,"
        "samples:state.samples,changes:state.changes,"
        "mouthRange:state.low===null?null:state.high-state.low,"
        "mouthFirstMs:state.firstMouth===null?null:state.firstMouth-state.started,"
        "mouthLastMs:state.lastMouth===null?null:state.lastMouth-state.started,"
        "reason:state.reason||'종료요청'};"
        "})()"
    )
