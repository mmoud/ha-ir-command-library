"""Private local catalog storage for IR Command Library."""

from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import IRCommand


class IRCommandCatalog:
    """Persist command names and routing metadata, never learned payloads."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store[dict](hass, STORAGE_VERSION, STORAGE_KEY, private=True)
        self._commands: dict[str, IRCommand] = {}
        self._lock = asyncio.Lock()

    @property
    def commands(self) -> dict[str, IRCommand]:
        """Return a snapshot of catalog commands."""
        return dict(self._commands)

    async def async_load(self) -> None:
        """Load and validate catalog records."""
        stored = await self._store.async_load() or {}
        records = stored.get("commands", []) if isinstance(stored, dict) else []
        commands: dict[str, IRCommand] = {}
        for record in records:
            command = IRCommand.from_dict(record)
            if command is not None:
                commands[command.key] = command
        self._commands = commands

    async def async_add(self, command: IRCommand) -> bool:
        """Add or replace a command record and return whether it was new."""
        async with self._lock:
            added = command.key not in self._commands
            self._commands[command.key] = command
            await self._async_save()
            return added

    async def async_remove(self, key: str) -> bool:
        """Remove a command record and report whether it existed."""
        async with self._lock:
            if self._commands.pop(key, None) is None:
                return False
            await self._async_save()
            return True

    async def _async_save(self) -> None:
        await self._store.async_save(
            {"commands": [item.as_dict() for item in self._commands.values()]}
        )
