"""Catalog coordinator for IR Command Library."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .catalog import IRCommandCatalog
from .const import DOMAIN
from .models import IRCommand

_LOGGER = logging.getLogger(__name__)


class IRCommandCoordinator(DataUpdateCoordinator[dict[str, IRCommand]]):
    """Publish catalog changes to button entities without polling."""

    def __init__(self, hass: HomeAssistant, catalog: IRCommandCatalog) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.catalog = catalog
        # Button-platform setup consumes ``coordinator.data`` immediately.  Seed
        # it from storage so commands are restored on Home Assistant startup,
        # before any service call publishes a catalog change.
        self.async_set_updated_data(catalog.commands)

    async def _async_update_data(self) -> dict[str, IRCommand]:
        return self.catalog.commands

    def async_publish(self) -> None:
        """Publish a new catalog snapshot immediately."""
        self.async_set_updated_data(self.catalog.commands)
