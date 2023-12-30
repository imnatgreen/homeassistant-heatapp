"""Support climate platform for heatapp radiators."""
from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_WHOLE, UnitOfTemperature
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
    """Set up heatapp radiator from Config Entry."""
    hub: heatapp.HeatappHub = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def async_add_radiator(rad_id: int) -> None:
        """Add heatapp radiator."""
        radiator = HeatappRadiator(hub, heatapp.HeatappRadiator(hub, rad_id))
        async_add_entities([radiator])

    # add all available radiators
    for i in hub.radiator_ids:
        async_add_radiator(i)

    # # register listener for new lights
    # config_entry.async_on_unload(
    #     controller.subscribe(async_add_light, event_filter=EventType.RESOURCE_ADDED)
    # )


class HeatappRadiator(ClimateEntity):
    """Representation of a heatapp radiator."""

    def __init__(
        self, hub: heatapp.HeatappHub, radiator: heatapp.HeatappRadiator
    ) -> None:
        """Initialize the radiator."""
        self.hub = hub
        self.radiator = radiator

        self._attr_unique_id = f"{hub.idu}_{radiator.rad_id}"
        self._attr_name = f"heatapp {radiator.rad_id}"
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_hvac_modes = [HVACMode.HEAT]
        self._attr_max_temp = 30
        self._attr_min_temp = 0
        self._attr_precision = PRECISION_WHOLE
        self._attr_supported_features = ClimateEntityFeature(1)
        self._attr_target_temperature_step = 1
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        self._attr_current_temperature: float | None = None
        self._attr_hvac_action: HVACAction | None = None
        self._attr_target_temperature: float | None = None

    def set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        target = kwargs.get(ATTR_TEMPERATURE)
        self.radiator.set_temperature(target)
        self._attr_target_temperature = target

    def update(self) -> None:
        """Get new data from the radiator."""
        r = self.radiator.get_temperature()
        if r is not None:
            self._attr_current_temperature = r["current"]
            self._attr_target_temperature = r["target"]
            self._attr_hvac_action = (
                HVACAction.HEATING if r["target"] > r["current"] else HVACAction.IDLE
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer="Elkatherm",
            sw_version=self.radiator.firmware,
            serial_number=self.radiator.serial,
            model=f"{self.radiator.power}W",
            via_device=(DOMAIN, self.hub.device_id),
        )
