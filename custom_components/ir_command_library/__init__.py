"""Turn learned remote commands into reusable Home Assistant buttons."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .catalog import IRCommandCatalog
from .const import (
    CONF_ALTERNATIVE,
    CONF_AREA,
    CONF_COMMAND,
    CONF_COMMAND_BUTTON,
    CONF_COMMAND_TYPE,
    CONF_CONTROLLER,
    CONF_DEVICE,
    CONF_TIMEOUT,
    DOMAIN,
    PLATFORMS,
    SERVICE_LEARN_COMMAND,
    SERVICE_REGISTER_COMMAND,
    SERVICE_REMOVE_COMMAND,
    STATIC_PATH,
    STATIC_URL,
)
from .coordinator import IRCommandCoordinator
from .models import IRCommand

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

LEARN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONTROLLER): cv.entity_id,
        vol.Required(CONF_AREA): cv.string,
        vol.Required(CONF_DEVICE): cv.string,
        vol.Required(CONF_COMMAND): cv.string,
        vol.Optional(CONF_COMMAND_TYPE, default="ir"): vol.In({"ir", "rf"}),
        vol.Optional(CONF_ALTERNATIVE, default=False): cv.boolean,
        vol.Optional(CONF_TIMEOUT, default=30): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=120)
        ),
    }
)

REGISTER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONTROLLER): cv.entity_id,
        vol.Required(CONF_AREA): cv.string,
        vol.Required(CONF_DEVICE): cv.string,
        vol.Required(CONF_COMMAND): cv.string,
    }
)

REMOVE_SCHEMA = vol.Schema(
    {vol.Required(CONF_COMMAND_BUTTON): cv.entity_id}
)


@dataclass(slots=True)
class IRCommandRuntime:
    """Runtime objects shared by services and entities."""

    catalog: IRCommandCatalog
    coordinator: IRCommandCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static assets and GUI-editable service actions."""
    frontend = Path(__file__).parent / "frontend" / "ir-command-library-card.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_PATH, str(frontend), cache_headers=True)]
    )

    async def handle_learn(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        command = _command_from_data(call.data)
        remote_data = {
            "device": command.device,
            "command": command.command,
            "command_type": call.data[CONF_COMMAND_TYPE],
            "alternative": call.data[CONF_ALTERNATIVE],
            "timeout": call.data[CONF_TIMEOUT],
        }
        await hass.services.async_call(
            "remote",
            "learn_command",
            remote_data,
            target={CONF_ENTITY_ID: command.controller},
            blocking=True,
            context=call.context,
        )
        await runtime.catalog.async_add(command)
        runtime.coordinator.async_publish()

    async def handle_register(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        command = _command_from_data(call.data)
        await runtime.catalog.async_add(command)
        runtime.coordinator.async_publish()

    async def handle_remove(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        entity_id = call.data[CONF_COMMAND_BUTTON]
        state = hass.states.get(entity_id)
        if state is None or not entity_id.startswith("button."):
            raise ServiceValidationError("Select an IR Command Library button")
        attrs = state.attributes
        try:
            command = IRCommand.create(
                controller=attrs["ir_controller"],
                area=attrs["ir_area"],
                device=attrs["ir_device"],
                command=attrs["ir_command"],
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ServiceValidationError(
                "The selected entity is not an IR Command Library button"
            ) from err

        await hass.services.async_call(
            "remote",
            "delete_command",
            {"device": command.device, "command": command.command},
            target={CONF_ENTITY_ID: command.controller},
            blocking=True,
            context=call.context,
        )
        await runtime.catalog.async_remove(command.key)
        runtime.coordinator.async_publish()

    hass.services.async_register(
        DOMAIN, SERVICE_LEARN_COMMAND, handle_learn, schema=LEARN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REGISTER_COMMAND, handle_register, schema=REGISTER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_COMMAND, handle_remove, schema=REMOVE_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the local catalog and its generated buttons."""
    catalog = IRCommandCatalog(hass)
    await catalog.async_load()
    coordinator = IRCommandCoordinator(hass, catalog)
    await coordinator.async_config_entry_first_refresh()

    runtime = IRCommandRuntime(catalog, coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.data[DOMAIN]["runtime"] = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data[DOMAIN].pop("runtime", None)
    return unloaded


def _runtime(hass: HomeAssistant) -> IRCommandRuntime:
    runtime = hass.data.get(DOMAIN, {}).get("runtime")
    if runtime is None:
        raise HomeAssistantError(
            "Set up IR Command Library in Settings > Devices & services first"
        )
    return runtime


def _command_from_data(data: dict) -> IRCommand:
    try:
        return IRCommand.create(
            controller=data[CONF_CONTROLLER],
            area=data[CONF_AREA],
            device=data[CONF_DEVICE],
            command=data[CONF_COMMAND],
        )
    except (KeyError, TypeError, ValueError) as err:
        raise ServiceValidationError("Invalid command metadata") from err
