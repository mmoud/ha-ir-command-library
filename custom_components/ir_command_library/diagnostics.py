"""Privacy-preserving diagnostics for IR Command Library."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, int | str]:
    """Return counts only; omit command names, entities, areas, and payloads."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    commands = list(coordinator.data.values())
    return {
        "integration": DOMAIN,
        "command_count": len(commands),
        "controller_count": len({item.controller for item in commands}),
        "device_group_count": len(
            {(item.controller, item.area, item.device) for item in commands}
        ),
    }
