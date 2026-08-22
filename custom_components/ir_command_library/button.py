"""Button entities for learned IR and RF commands."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IRCommandCoordinator
from .models import IRCommand


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create buttons and keep the platform synchronized with the catalog."""
    coordinator: IRCommandCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: dict[str, IRCommandButton] = {}

    def sync_entities() -> None:
        # A coordinator can briefly have no published data while Home Assistant
        # is starting.  Treat that as an empty catalog; a later publish will
        # add the saved commands through the registered listener.
        current = set(coordinator.data or {})
        known = set(entities)

        new_entities = [
            IRCommandButton(coordinator, coordinator.data[key])
            for key in sorted(current - known)
        ]
        for entity in new_entities:
            entities[entity.command_key] = entity
        if new_entities:
            async_add_entities(new_entities)

        removed_keys = known - current
        if removed_keys:
            hass.async_create_task(remove_entities(removed_keys))

    async def remove_entities(removed_keys: set[str]) -> None:
        registry = er.async_get(hass)
        for key in removed_keys:
            entity = entities.pop(key, None)
            if entity is None:
                continue
            entity_id = entity.entity_id
            await entity.async_remove()
            if entity_id and registry.async_get(entity_id):
                registry.async_remove(entity_id)

    entry.async_on_unload(coordinator.async_add_listener(sync_entities))
    sync_entities()


class IRCommandButton(CoordinatorEntity[IRCommandCoordinator], ButtonEntity):
    """A momentary button that sends one learned command."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: IRCommandCoordinator, command: IRCommand) -> None:
        super().__init__(coordinator)
        self._command = command
        self._attr_unique_id = f"command_{command.key}"
        self._attr_name = command.command_name
        self._attr_icon = command_icon(command.command)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{command.controller}|{command.area}|{command.device}")},
            name=command.device_name,
            manufacturer="IR Command Library",
            model="Learned remote command group",
            suggested_area=command.area,
        )

    @property
    def command_key(self) -> str:
        return self._command.key

    @property
    def available(self) -> bool:
        controller = self.hass.states.get(self._command.controller)
        return (
            self._command.key in self.coordinator.data
            and controller is not None
            and controller.state not in {"unavailable", "unknown"}
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "ir_area": self._command.area,
            "ir_controller": self._command.controller,
            "ir_device": self._command.device,
            "ir_device_name": self._command.device_name,
            "ir_command": self._command.command,
            "ir_command_name": self._command.command_name,
        }

    async def async_press(self) -> None:
        await self.hass.services.async_call(
            "remote",
            "send_command",
            {"device": self._command.device, "command": self._command.command},
            target={"entity_id": self._command.controller},
            blocking=True,
        )


def command_icon(command: str) -> str:
    """Choose a Material Design icon for common commands."""
    value = command.lower().replace("_", " ").replace("-", " ").strip()
    exact = {
        "power": "mdi:power",
        "on": "mdi:power",
        "off": "mdi:power-off",
        "up": "mdi:chevron-up",
        "down": "mdi:chevron-down",
        "left": "mdi:chevron-left",
        "right": "mdi:chevron-right",
        "ok": "mdi:checkbox-marked-circle-outline",
        "enter": "mdi:checkbox-marked-circle-outline",
        "play": "mdi:play",
        "pause": "mdi:pause",
        "stop": "mdi:stop",
        "mute": "mdi:volume-mute",
        "home": "mdi:home",
        "menu": "mdi:menu",
        "back": "mdi:arrow-u-left-top",
    }
    if value in exact:
        return exact[value]
    if value.isdigit() and len(value) == 1:
        return f"mdi:numeric-{value}-circle-outline"
    if "volume up" in value or value == "vol up":
        return "mdi:volume-plus"
    if "volume down" in value or value == "vol down":
        return "mdi:volume-minus"
    if "channel up" in value:
        return "mdi:chevron-up-circle-outline"
    if "channel down" in value:
        return "mdi:chevron-down-circle-outline"
    if "input" in value or "hdmi" in value or "source" in value:
        return "mdi:video-input-hdmi"
    return "mdi:remote"
