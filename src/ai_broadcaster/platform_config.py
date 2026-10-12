"""Operator-controlled platform configuration; no account or API linking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Names here describe supported *future selections*, not implemented adapters.
PLATFORM_CANDIDATES = frozenset({"youtube", "chzzk", "twitch"})


@dataclass(frozen=True)
class PlatformConfig:
    selected_platform: str | None = None
    operator_approved: bool = False
    external_broadcast_enabled: bool = False

    @classmethod
    def from_dict(cls, source: dict[str, Any]) -> "PlatformConfig":
        if not isinstance(source, dict):
            raise TypeError("platform config must be an object")
        for key in ("operator_approved", "external_broadcast_enabled"):
            if type(source.get(key, False)) is not bool:
                raise ValueError(f"{key} must be boolean")
        item = cls(
            selected_platform=source.get("selected_platform"),
            operator_approved=source.get("operator_approved", False),
            external_broadcast_enabled=source.get("external_broadcast_enabled", False),
        )
        if item.selected_platform is not None and item.selected_platform not in PLATFORM_CANDIDATES:
            raise ValueError("unknown platform; operator must choose a supported platform")
        if item.external_broadcast_enabled and not (item.operator_approved and item.selected_platform):
            raise PermissionError("broadcast requires selected platform and explicit approval")
        return item

    def assert_can_broadcast(self) -> None:
        if not (self.operator_approved and self.external_broadcast_enabled and self.selected_platform):
            raise PermissionError("external broadcast not approved")
        # Deliberate fail-closed guard until a real integration is tested.
        raise NotImplementedError("external broadcast adapter has not been implemented")
