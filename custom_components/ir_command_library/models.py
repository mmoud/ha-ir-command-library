"""Data models for IR Command Library."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class IRCommand:
    """A named command stored by a Home Assistant remote entity."""

    controller: str
    area: str
    device: str
    command: str

    @property
    def key(self) -> str:
        """Return a stable, non-reversible identifier."""
        raw = "\0".join((self.controller, self.area, self.device, self.command))
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    @property
    def device_name(self) -> str:
        """Return a friendly device name."""
        return pretty_name(self.device)

    @property
    def command_name(self) -> str:
        """Return a friendly command name."""
        return pretty_name(self.command)

    def as_dict(self) -> dict[str, str]:
        """Serialize the command without learned IR/RF payload data."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> IRCommand | None:
        """Load one validated catalog record."""
        if not isinstance(value, dict):
            return None
        try:
            return cls.create(
                controller=value["controller"],
                area=value["area"],
                device=value["device"],
                command=value["command"],
            )
        except (KeyError, TypeError, ValueError):
            return None

    @classmethod
    def create(
        cls,
        *,
        controller: object,
        area: object,
        device: object,
        command: object,
    ) -> IRCommand:
        """Create a normalized and bounded command record."""
        values = {
            "controller": _bounded(controller, 255),
            "area": _bounded(area, 100),
            "device": _bounded(device, 100),
            "command": _bounded(command, 100),
        }
        if not values["controller"].startswith("remote."):
            raise ValueError("controller must be a remote entity")
        return cls(**values)


def pretty_name(value: str) -> str:
    """Turn storage-safe names into voice-friendly names."""
    return " ".join(part.capitalize() for part in re.split(r"[_.-]+", value) if part)


def _bounded(value: Any, maximum: int) -> str:
    text = str(value).strip()
    if not text or len(text) > maximum or "\0" in text:
        raise ValueError("invalid command metadata")
    return text
