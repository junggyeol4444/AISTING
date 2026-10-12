"""외부 의존성 없는 로컬 PC 설정 화면.

사용법: python scripts/settings_server.py
주소: http://127.0.0.1:8765
인터넷에 노출하지 않는다. 실제 방송/결제/연동 기능 없음.
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ai_broadcaster.operator_settings import (  # noqa: E402
    DEFAULT_FILE, SettingsError, load_settings, save_settings,
)

HTML_FILE = ROOT / "web" / "settings.html"
MAX_BYTES = 16384


class SettingsHandler(BaseHTTPRequestHandler):
    store_path = DEFAULT_FILE

    def _allowed_origin(self) -> bool:
        # DNS rebinding / cross-site POST 방어. 본인 PC의 루프백 접근만 허용.
        host = self.headers.get("Host", "")
        if host.split(":")[0] not in ("127.0.0.1", "localhost"):
            return False
        origin = self.headers.get("Origin")
        return not origin or origin == "http://" + host

    def _response(self, code: int, payload: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; "
            "script-src 'unsafe-inline'; connect-src 'self'; "
            "base-uri 'none'; form-action 'self'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._response(code, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if not self._allowed_origin():
            self._json(403, {"error": "로컬 PC에서만 이용할 수 있습니다."})
            return
        path = urlsplit(self.path).path
        if path == "/":
            self._response(
                200, HTML_FILE.read_bytes(), "text/html; charset=utf-8"
            )
        elif path == "/api/settings":
            try:
                self._json(200, load_settings(self.store_path))
            except (OSError, SettingsError, ValueError) as e:
                self._json(500, {"error": str(e)})
        else:
            self._json(404, {"error": "없는 경로입니다."})

    def do_POST(self) -> None:
        if not self._allowed_origin():
            self._json(403, {"error": "허용되지 않은 요청입니다."})
            return
        if urlsplit(self.path).path != "/api/settings":
            self._json(404, {"error": "없는 경로입니다."})
            return
        if self.headers.get("Content-Type", "").split(";")[0].lower() != "application/json":
            self._json(415, {"error": "JSON 형식만 저장할 수 있습니다."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "본문 크기 형식 오류"})
            return
        if not 0 < length <= MAX_BYTES:
            self._json(413, {"error": "설정 크기 제한 초과"})
            return
        try:
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
            saved = save_settings(raw, self.store_path)
        except (ValueError, TypeError, SettingsError, UnicodeDecodeError) as e:
            self._json(400, {"error": str(e)})
            return
        except OSError:
            self._json(500, {"error": "설정 파일 저장 실패"})
            return
        self._json(200, saved)

    def log_message(self, fmt: str, *args: object) -> None:
        # 요청 경로 외에 개인정보/본문/비밀번호는 기록하지 않는다.
        return


def main() -> None:
    # 외부 기기에서 접근하지 못하게 IPv4 루프백에만 바인딩한다.
    address = ("127.0.0.1", 8765)
    with ThreadingHTTPServer(address, SettingsHandler) as server:
        print("AISTING PC 설정 화면: http://127.0.0.1:8765")
        print("설정은 PC의 data/operator_settings.json에 저장됩니다.")
        print("종료하려면 Ctrl+C")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
