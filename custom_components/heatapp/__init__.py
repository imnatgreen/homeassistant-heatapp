"""The heatapp integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .heatapp import heatapp

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up heatapp from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    try:
        hub = heatapp.HeatappHub(entry.data[CONF_HOST], entry.data[CONF_PORT])
    except ConnectionError as ex:
        raise ConfigEntryNotReady(f"Error connecting to the hub: {ex}") from ex

    if not hub.ready():
        raise ConfigEntryNotReady(
            f"No valid response from {entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        )

    hass.data[DOMAIN][entry.entry_id] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, hub.device_id)},
        manufacturer="heatapp",
        name="heatapp",
        model=hub.device_id.split("/")[0],
        sw_version=hub.firmware,
        serial_number=hub.device_id,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
