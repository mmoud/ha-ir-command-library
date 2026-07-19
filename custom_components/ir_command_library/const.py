"""Constants for IR Command Library."""

from typing import Final

DOMAIN: Final = "ir_command_library"
PLATFORMS: Final = ["button"]

SERVICE_LEARN_COMMAND: Final = "learn_command"
SERVICE_REGISTER_COMMAND: Final = "register_command"
SERVICE_REMOVE_COMMAND: Final = "remove_command"

CONF_CONTROLLER: Final = "controller"
CONF_AREA: Final = "area"
CONF_DEVICE: Final = "device"
CONF_COMMAND: Final = "command"
CONF_COMMAND_TYPE: Final = "command_type"
CONF_ALTERNATIVE: Final = "alternative"
CONF_TIMEOUT: Final = "timeout"
CONF_COMMAND_BUTTON: Final = "command_button"

STORAGE_KEY: Final = f"{DOMAIN}.catalog"
STORAGE_VERSION: Final = 1
STATIC_URL: Final = f"/api/{DOMAIN}/ir-command-library-card.js"
