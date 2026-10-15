"""24단계: 승인 전 네트워크 없는 AI 연결 프로토콜 시험과 승인 후 loopback 조회.

앱 시작/탭 열기/모의 시험에는 어떤 PC/네트워크 조회도 없다.
실제 시험은 운영자 확인을 받은 경우에만 고정된 127.0.0.1:11434/api/tags에
한 번 GET한다. 모델 다운로드/실행/생성/외부 서버/프록시/리다이렉트 없음.
"""
from __future__ import annotations

import http.client
import json
from dataclasses import dataclass
from typing import Callable

from .core_ai_connection import (
    CoreAIConnectionPlan, LOOPBACK_HOST, LOOPBACK_PORT, validate_core_ai_plan,
)

TAGS_PATH = "/api/tags"
MAX_RESPONSE_BYTES = 262144
TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class ConnectionCheckResult:
    status: str
    model_name: str
    simulated: bool

    @property
    def model_available(self) -> bool:
        return self.status == "model_available"

    def describe(self) -> str:
        labels = {
            "model_available": "로컬 서비스 응답 형식 정상 · 선택 모델 이름 일치",
            "model_missing": "서비스 응답 형식 정상 · 선택 모델 없음",
            "invalid_response": "서비스 응답을 검증할 수 없음",
            "http_error": "서비스가 정상 상태 코드(200)를 반환하지 않음",
            "connection_error": "로컬 서비스 접속 실패/시간 초과",
            "mock_mode": "모의 답변 모드 · 실제 모델 연결 불필요",
        }
        if self.status not in labels:
            raise ValueError("알 수 없는 연결 시험 상태")
        mode = "오프라인 가상 응답 시험 (실제 연결 증거 아님)" if self.simulated else "사용자 승인 후 로컬 조회 결과"
        return "\n".join((
            "24단계 · AI 연결 시험", f"시험 종류: {mode}",
            f"선택 모델: {self.model_name or '(없음)'}",
            f"판정: {labels[self.status]}",
            "고정 경로: 127.0.0.1:11434/api/tags (실제 시험 승인 시에만)",
            "모델 생성·다운로드·프로세스 시작·외부 서버·계정 연결·방송 송출 없음",
            "코어 실행은 여전히 모의 답변만 사용하며 기존 설정/기억을 변경하지 않음",
            "Windows 실기기에서의 연결 성공은 이 환경에서 검증되지 않음",
            "10단계 최종 승인 및 11단계 이후 PC 실확인 대기 · 공식 9/100",
        ))


def evaluate_tags(plan: CoreAIConnectionPlan, status_code: int, body: bytes,
                  content_type: str = "application/json", *, simulated: bool = True) -> ConnectionCheckResult:
    """읽은 바이트만 검증. 외부/시스템 동작 없음; 성공 판정은 엄격한 모델 이름 일치."""
    validate_core_ai_plan(plan)
    if plan.mode != "local_ollama":
        return ConnectionCheckResult("mock_mode", "", simulated)
    if type(status_code) is not int or status_code != 200:
        return ConnectionCheckResult("http_error", plan.model_name, simulated)
    if (type(body) is not bytes or len(body) > MAX_RESPONSE_BYTES
            or type(content_type) is not str
            or content_type.split(";", 1)[0].strip().lower() != "application/json"):
        return ConnectionCheckResult("invalid_response", plan.model_name, simulated)
    try:
        record = json.loads(body.decode("utf-8"))
    except (UnicodeError, ValueError):
        return ConnectionCheckResult("invalid_response", plan.model_name, simulated)
    if type(record) is not dict or type(record.get("models")) is not list:
        return ConnectionCheckResult("invalid_response", plan.model_name, simulated)
    models = record["models"]
    if len(models) > 1024 or any(
        type(item) is not dict or type(item.get("name")) is not str
        or len(item["name"]) > 200 for item in models
    ):
        return ConnectionCheckResult("invalid_response", plan.model_name, simulated)
    names = {item["name"] for item in models}
    return ConnectionCheckResult("model_available" if plan.model_name in names else "model_missing",
                                 plan.model_name, simulated)


def simulate_connection_test(plan: CoreAIConnectionPlan, scenario: str = "available") -> ConnectionCheckResult:
    """모의 /api/tags 프로토콜. 어떠한 포트에도 접속하지 않는다."""
    validate_core_ai_plan(plan)
    if scenario not in ("available", "missing", "invalid", "http_error"):
        raise ValueError("지원하지 않는 오프라인 시험 시나리오")
    if plan.mode == "mock":
        return ConnectionCheckResult("mock_mode", "", True)
    if scenario == "available":
        data = json.dumps({"models": [{"name": plan.model_name}]}).encode("utf-8")
    elif scenario == "missing":
        data = b'{"models": []}'
    else:
        data = b'{"unexpected": true}'
    return evaluate_tags(plan, 503 if scenario == "http_error" else 200, data)


def _fetch_loopback_tags() -> tuple[int, bytes, str]:
    """명시적 호출 시에만 단일 고정 IP/포트/경로로 요청. 프록시·리다이렉트 미사용."""
    connection = http.client.HTTPConnection(LOOPBACK_HOST, LOOPBACK_PORT, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", TAGS_PATH, headers={"Accept": "application/json", "Connection": "close"})
        response = connection.getresponse()
        # 리다이렉트는 따라가지 않으며 body는 상한 + 1 바이트만 읽는다.
        return response.status, response.read(MAX_RESPONSE_BYTES + 1), response.getheader("Content-Type", "")
    finally:
        connection.close()


def probe_local_model(plan: CoreAIConnectionPlan, *, operator_confirmed: bool = False,
                      transport: Callable[[], tuple[int, bytes, str]] | None = None) -> ConnectionCheckResult:
    """실제 PC 조회는 승인 없이는 불가. 주입 transport는 네트워크 없는 테스트용."""
    validate_core_ai_plan(plan)
    if operator_confirmed is not True:
        raise PermissionError("운영자 승인 없이 PC 로컬 서비스에 접속할 수 없습니다.")
    if plan.mode != "local_ollama":
        return ConnectionCheckResult("mock_mode", "", False)
    fetch = _fetch_loopback_tags if transport is None else transport
    try:
        status, body, content_type = fetch()
    except (OSError, TimeoutError, http.client.HTTPException):
        return ConnectionCheckResult("connection_error", plan.model_name, False)
    return evaluate_tags(plan, status, body, content_type, simulated=False)
