"""Support sensor platform for heatapp radiators."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .heatapp import heatapp


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up heatapp radiator energy sensor from Config Entry."""
    hub: heatapp.HeatappHub = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def async_add_sensor(rad_id: int) -> None:
        """Add heatapp radiator energy sensor."""
        sensor = HeatappEnergySensor(hub, heatapp.HeatappRadiator(hub, rad_id))
        async_add_entities([sensor])

    # add all available radiators
    for i in hub.radiator_ids:
        async_add_sensor(i)


class HeatappEnergySensor(SensorEntity):
    """Representation of a heatapp radiator energy sensor."""

    def __init__(
        self, hub: heatapp.HeatappHub, radiator: heatapp.HeatappRadiator
    ) -> None:
        """Initialize the radiator energy sensor."""
        self.hub = hub
        self.radiator = radiator

        self._attr_unique_id = f"{hub.idu}_{radiator.rad_id}"
        self._attr_name = f"heatapp {radiator.rad_id} energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    def update(self) -> None:
        """Get new data from the radiator."""
        r = self.radiator.get_energy_usage()
        self._attr_native_value = r

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(identifiers={(DOMAIN, self.unique_id)})
