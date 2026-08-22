"""Constants for IR Command Library."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "ir_command_library"
PLATFORMS: Final = [Platform.BUTTON]

SERVICE_LEARN_COMMAND: Final = "learn_command"
SERVICE_REGISTER_COMMAND: Final = "register_command"
SERVICE_REMOVE_COMMAND: Final = "remove_command"
SERVICE_IMPORT_LEGACY_CATALOG: Final = "import_legacy_catalog"
SERVICE_REPAIR_LEGACY_CONTROLLER_LABELS: Final = "repair_legacy_controller_labels"
SERVICE_CLEANUP_LEGACY_ORPHANED_DEVICES: Final = "cleanup_legacy_orphaned_devices"

CONF_CONTROLLER: Final = "controller"
CONF_AREA: Final = "area"
CONF_DEVICE: Final = "device"
CONF_COMMAND: Final = "command"
CONF_COMMAND_TYPE: Final = "command_type"
CONF_ALTERNATIVE: Final = "alternative"
CONF_TIMEOUT: Final = "timeout"
CONF_COMMAND_BUTTON: Final = "command_button"
CONF_TODO_ENTITY: Final = "todo_entity"

STORAGE_KEY: Final = f"{DOMAIN}.catalog"
STORAGE_VERSION: Final = 1
VERSION: Final = "1.0.10"
STATIC_PATH: Final = f"/api/{DOMAIN}/ir-command-library-card.js"
STATIC_URL: Final = f"{STATIC_PATH}?v={VERSION}"
