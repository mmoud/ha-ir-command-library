"""Turn learned remote commands into reusable Home Assistant buttons."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

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
    CONF_TODO_ENTITY,
    DOMAIN,
    PLATFORMS,
    SERVICE_IMPORT_LEGACY_CATALOG,
    SERVICE_CLEANUP_LEGACY_ORPHANED_DEVICES,
    SERVICE_LEARN_COMMAND,
    SERVICE_REPAIR_LEGACY_CONTROLLER_LABELS,
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

IMPORT_LEGACY_SCHEMA = vol.Schema(
    {vol.Required(CONF_TODO_ENTITY): cv.entity_id}
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

    async def handle_import_legacy_catalog(call: ServiceCall) -> dict[str, int] | None:
        """Import catalog metadata from the original To-do-list prototype."""
        runtime = _runtime(hass)
        todo_entity = call.data[CONF_TODO_ENTITY]
        if not todo_entity.startswith("todo."):
            raise ServiceValidationError("Select a To-do list entity")

        response = await hass.services.async_call(
            "todo",
            "get_items",
            {"status": ["needs_action", "completed"]},
            target={CONF_ENTITY_ID: todo_entity},
            blocking=True,
            return_response=True,
            context=call.context,
        )
        list_data = response.get(todo_entity, {}) if isinstance(response, dict) else {}
        items = list_data.get("items", []) if isinstance(list_data, dict) else []
        imported = 0
        skipped = 0
        for item in items:
            summary = item.get("summary") if isinstance(item, dict) else None
            command = IRCommand.from_legacy_summary(summary)
            if command is None:
                skipped += 1
                continue
            imported += await runtime.catalog.async_add(command)

        runtime.coordinator.async_publish()
        result = {
            "imported": imported,
            "already_present": max(len(items) - skipped - imported, 0),
            "skipped": skipped,
            "catalog_total": len(runtime.catalog.commands),
        }
        return result if call.return_response else None

    async def handle_repair_legacy_controller_labels(
        call: ServiceCall,
    ) -> dict[str, int] | None:
        """Repair prototype controller display labels in catalog metadata only."""
        runtime = _runtime(hass)
        repaired = await runtime.catalog.async_repair_legacy_controller_labels()
        runtime.coordinator.async_publish()
        result = {"repaired": repaired, "catalog_total": len(runtime.catalog.commands)}
        return result if call.return_response else None

    async def handle_cleanup_legacy_orphaned_devices(
        call: ServiceCall,
    ) -> dict[str, int] | None:
        """Remove only orphaned device records made by the legacy label bug."""
        runtime = _runtime(hass)
        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        legacy_identifiers = {
            (
                DOMAIN,
                f"{command.controller} [{command.area}]|Imported|{command.device}",
            )
            for command in runtime.catalog.commands.values()
        }
        removed = 0
        skipped_with_entities = 0
        for device in list(device_registry.devices.values()):
            if not (device.identifiers & legacy_identifiers):
                continue
            if any(entry.device_id == device.id for entry in entity_registry.entities.values()):
                skipped_with_entities += 1
                continue
            device_registry.async_remove_device(device.id)
            removed += 1

        result = {
            "removed": removed,
            "skipped_with_entities": skipped_with_entities,
        }
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN, SERVICE_LEARN_COMMAND, handle_learn, schema=LEARN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REGISTER_COMMAND, handle_register, schema=REGISTER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_COMMAND, handle_remove, schema=REMOVE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_LEGACY_CATALOG,
        handle_import_legacy_catalog,
        schema=IMPORT_LEGACY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEANUP_LEGACY_ORPHANED_DEVICES,
        handle_cleanup_legacy_orphaned_devices,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REPAIR_LEGACY_CONTROLLER_LABELS,
        handle_repair_legacy_controller_labels,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.OPTIONAL,
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
    # The button platform registers its catalog listener while it is forwarded.
    # Publish after that point so commands restored from storage are added even
    # when this config entry starts with a non-empty catalog.
    coordinator.async_publish()
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
