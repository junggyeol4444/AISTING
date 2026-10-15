"""Platform-independent offline chat simulation with optional loopback Ollama.

Chat input is manually typed and never fetched from actual streaming platforms.
A failed reply remains at the queue head for explicit retries.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from typing import Iterator
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPHandler, HTTPRedirectHandler, ProxyHandler, build_opener

from .offline_settings import data_dir
from .content_modes import content_guidance, validate_content
from .persona_modes import chosen_persona, persona_guidance

MAX_LINES = 500
MAX_SCRIPT_SIZE = 100_000


@dataclass(frozen=True)
class ChatMessage:
    sender: str
    text: str


@dataclass(frozen=True)
class Answer:
    original: ChatMessage
    reply: str


def parse_script(script: str) -> list[ChatMessage]:
    if not isinstance(script, str) or not script.strip():
        raise ValueError("닉네임: 채팅 형식으로 입력해 주세요.")
    if len(script) > MAX_SCRIPT_SIZE:
        raise ValueError("대본이 너무 깁니다 (100,000자 제한).")
    result = []
    for line_no, line in enumerate(script.splitlines(), 1):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"{line_no}번째 줄: 닉네임: 내용 형식이 필요합니다.")
        sender, text = (x.strip() for x in line.split(":", 1))
        if not (1 <= len(sender) <= 100 and 1 <= len(text) <= 4000):
            raise ValueError(f"{line_no}번째 줄: 닉네임(100자 이하), 내용(4000자 이하)을 확인하세요.")
        result.append(ChatMessage(sender, text))
        if len(result) > MAX_LINES:
            raise ValueError("한 번에 최대 500개까지만 입력할 수 있습니다.")
    if not result:
        raise ValueError("실제 채팅 내용을 입력해 주세요.")
    return result


class ReplyGenerator(Protocol):
    def generate(self, chat: ChatMessage, history: list[Answer]) -> str: ...


class MockReplyGenerator:
    def generate(self, chat: ChatMessage, history: list[Answer]) -> str:
        return f"{chat.sender}님, '{chat.text[:300]}' 채팅에 대한 모의 답변이에요."


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalOllamaGenerator:
    """ONLY local 127.0.0.1 Ollama requests, once the operator selects it."""

    def __init__(self, model: str, *, port: int = 11434, content: str = "undecided",
                 persona: dict[str, str] | None = None) -> None:
        if (not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", model)
                or "://" in model or model.startswith("/")):
            raise ValueError("올바른 로컬 모델 이름을 입력해 주세요.")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("로컬 모델 포트가 올바르지 않습니다.")
        self.model, self.port = model, port
        self.content = validate_content(content)
        self.persona = chosen_persona("default", {}) if persona is None else chosen_persona("custom", persona)
        self._opener = build_opener(ProxyHandler({}), HTTPHandler(), _NoRedirect())

    def set_content(self, content: str) -> None:
        """다음 수동 연습부터 적용한다. 외부 연결은 일으키지 않는다."""
        self.content = validate_content(content)

    def set_persona(self, fields: dict[str, str]) -> None:
        """다음 로컬 AI 요청에서만 적용. 모델 호출은 하지 않는다."""
        self.persona = chosen_persona("custom", fields)

    def generate(self, chat: ChatMessage, history: list[Answer]) -> str:
        prompt = (
            persona_guidance(self.persona) + " 한국어로 자연스럽게 대답해. "
            "인위적으로 답변을 지연하거나 채팅을 선별하지 마. "
            + content_guidance(self.content)
        )
        messages = [{"role": "system", "content": prompt}]
        for prior in history[-8:]:
            messages.append({"role": "user", "content": f"{prior.original.sender}: {prior.original.text}"})
            messages.append({"role": "assistant", "content": prior.reply})
        messages.append({"role": "user", "content": f"{chat.sender}: {chat.text}"})
        request = Request(
            f"http://127.0.0.1:{self.port}/api/chat",
            data=json.dumps({"model": self.model, "stream": False, "messages": messages}, ensure_ascii=False).encode("utf-8"),
            method="POST", headers={"Content-Type": "application/json"},
        )
        try:
            with self._opener.open(request, timeout=30) as response:
                raw = response.read(1_000_001)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise RuntimeError("로컬 AI 응답 실패: PC에서 Ollama를 실행했는지 확인해 주세요.") from exc
        if len(raw) > 1_000_000:
            raise ValueError("AI 응답이 너무 큽니다.")
        try:
            message = json.loads(raw.decode("utf-8"))["message"]["content"]
        except (KeyError, ValueError, TypeError, UnicodeError) as exc:
            raise ValueError("로컬 모델 응답 형식 오류") from exc
        if not isinstance(message, str) or not message.strip() or len(message) > 6000:
            raise ValueError("로컬 모델 응답 길이/내용이 잘못됐습니다.")
        return message


class LocalMemory:
    """Explicit local SQLite memory with closed handles and non-destructive legacy checks.

    A pre-existing file is accepted only if it has the legacy AISTING history
    schema. Do not silently add a table to a different SQLite database.
    """

    _COLUMNS = (
        ("id", "INTEGER", 0, 1),
        ("sender", "TEXT", 1, 0),
        ("question", "TEXT", 1, 0),
        ("answer", "TEXT", 1, 0),
    )

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else data_dir() / "conversation.sqlite3"
        self._guard_path()
        if self.path.exists():
            # Open an existing database without creating/changing it. Legacy
            # history rows remain untouched, even when the store is reopened.
            with self._connection():
                pass
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._guard_path()
        # Exclusive creation prevents a newly appearing unrelated file from
        # being opened and modified between existence check and SQLite open.
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with self._connection(initializing=True) as db:
                db.execute("CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                           "sender TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL)")
        except BaseException:
            # Only remove the file created by this constructor on failure.
            self.path.unlink(missing_ok=True)
            raise

    def _guard_path(self) -> None:
        for part in (self.path, *self.path.parents):
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise ValueError("SQLite 기억 경로에 링크/정션을 사용할 수 없습니다.")
        if self.path.exists() and not self.path.is_file():
            raise ValueError("SQLite 기억 경로가 일반 파일이 아닙니다.")

    @classmethod
    def _validate_existing(cls, db: sqlite3.Connection) -> None:
        objects = db.execute(
            "SELECT type, name FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' AND type IN ('table','view','trigger')"
        ).fetchall()
        if objects != [("table", "history")]:
            raise ValueError("기존 SQLite 파일은 AISTING 대화 기억 DB가 아닙니다. 변경하지 않습니다.")
        columns = tuple((row[1], row[2].upper(), row[3], row[5])
                        for row in db.execute("PRAGMA table_info(history)"))
        if columns != cls._COLUMNS or db.execute("PRAGMA application_id").fetchone()[0] != 0:
            raise ValueError("기존 대화 기억 DB의 테이블 구조/식별자가 다릅니다. 변경하지 않습니다.")

    @contextmanager
    def _connection(self, *, initializing: bool = False) -> Iterator[sqlite3.Connection]:
        self._guard_path()
        # mode=rw refuses to create a missing file during a later read/write.
        # The constructor alone creates a new file explicitly.
        db = (sqlite3.connect(self.path, timeout=5) if initializing else
              sqlite3.connect(self.path.absolute().as_uri() + "?mode=rw", uri=True, timeout=5))
        try:
            with db:
                if not initializing:
                    self._validate_existing(db)
                yield db
        finally:
            db.close()

    def append(self, answer: Answer) -> None:
        with self._connection() as db:
            db.execute("INSERT INTO history(sender,question,answer) VALUES(?,?,?)", (answer.original.sender, answer.original.text, answer.reply))
            db.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 2000)")

    def recent(self, limit: int = 8) -> list[Answer]:
        if type(limit) is not int or not 0 <= limit <= 50:
            raise ValueError("기억 건수 범위 오류")
        if limit == 0:
            return []
        with self._connection() as db:
            rows = db.execute("SELECT sender,question,answer FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [Answer(ChatMessage(s, q), a) for s, q, a in reversed(rows)]

    def clear(self) -> None:
        with self._connection() as db:
            db.execute("DELETE FROM history")


class ChatRehearsal:
    def __init__(self, generator: ReplyGenerator | None = None, *, memory: LocalMemory | None = None) -> None:
        self.generator = generator or MockReplyGenerator()
        self.memory = memory
        self.pending: deque[ChatMessage] = deque()
        self.completed: list[Answer] = []
        self.prepared: Answer | None = None
        self.memory_errors: list[str] = []
        self.accepted = 0

    def add_script(self, script: str) -> int:
        items = parse_script(script)
        self.pending.extend(items)
        self.accepted += len(items)
        return len(items)

    def process_next(self, deliver) -> Answer | None:
        if not self.pending:
            return None
        head = self.pending[0]
        if self.prepared is None:
            previous = self.memory.recent(8) if self.memory else self.completed[-8:]
            reply = self.generator.generate(head, previous)
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("모델이 빈 응답을 반환했습니다.")
            self.prepared = Answer(head, reply)
        answer = self.prepared
        deliver(answer)
        self.pending.popleft()
        self.completed.append(answer)
        self.prepared = None
        if self.memory:
            try:
                self.memory.append(answer)
            except (OSError, sqlite3.Error, ValueError) as exc:
                # LocalMemory rejects a replaced/foreign database with ValueError.
                # Delivery already succeeded, so keep the completed reply and
                # report the persistence failure instead of claiming it can be
                # retried from the pending queue.
                self.memory_errors.append(str(exc))
        return answer
