"""Sensor platform for Multizone Heater integration."""
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MultizoneCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Multizone Heater sensors from a config entry."""
    coordinator: MultizoneCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    entities: list[SensorEntity] = []
    
    # Add main target sensor
    entities.append(MainTargetSensor(coordinator, config_entry))
    
    # Add zone sensors
    # We'll create sensors for each zone based on zone configuration
    # For now, we'll wait for first coordinator update to get zone names
    await coordinator.async_config_entry_first_refresh()
    
    # Only create zone sensors if we have both zone_targets and zone_states data
    if (coordinator.data and 
        "zone_targets" in coordinator.data and 
        "zone_states" in coordinator.data):
        # Get the intersection of zones that exist in both structures
        # to ensure consistent sensor availability
        zone_names = set(coordinator.data["zone_targets"].keys()) & set(coordinator.data["zone_states"].keys())
        
        for zone_name in zone_names:
            # Add zone target sensor
            entities.append(ZoneTargetSensor(coordinator, config_entry, zone_name))
            # Add zone current temperature sensor
            entities.append(ZoneCurrentTemperatureSensor(coordinator, config_entry, zone_name))
            # Add zone valve state sensor
            entities.append(ZoneValveStateSensor(coordinator, config_entry, zone_name))
    
    async_add_entities(entities)


class MainTargetSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing the computed main climate target temperature."""

    _attr_has_entity_name = True
    _attr_name = "Main Target Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: MultizoneCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the main target sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_main_target"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Multizone Heater",
            model="Multizone Controller",
        )

    @property
    def native_value(self) -> float | None:
        """Return the computed main target temperature."""
        if self.coordinator.data:
            return self.coordinator.data.get("main_target")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "is_holding_mode": self.coordinator.data.get("is_holding_mode", False),
            "hvac_mode": self.coordinator.data.get("hvac_mode", "off"),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class ZoneTargetSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing per-zone computed target information."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: MultizoneCoordinator,
        config_entry: ConfigEntry,
        zone_name: str,
    ) -> None:
        """Initialize the zone target sensor."""
        super().__init__(coordinator)
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Target"
        self._attr_unique_id = f"{config_entry.entry_id}_zone_{zone_name}_target"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Multizone Heater",
            model="Multizone Controller",
        )

    @property
    def native_value(self) -> float | None:
        """Return the zone target temperature."""
        if self.coordinator.data and "zone_targets" in self.coordinator.data:
            zone_data = self.coordinator.data["zone_targets"].get(self._zone_name)
            if zone_data:
                return zone_data.get("target")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "zone_targets" not in self.coordinator.data:
            return {}
        
        zone_data = self.coordinator.data["zone_targets"].get(self._zone_name)
        if not zone_data:
            return {}
        
        return {
            "lower_bound": zone_data.get("lower_bound"),
            "upper_bound": zone_data.get("upper_bound"),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class ZoneCurrentTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing current temperature for a zone."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: MultizoneCoordinator,
        config_entry: ConfigEntry,
        zone_name: str,
    ) -> None:
        """Initialize the zone current temperature sensor."""
        super().__init__(coordinator)
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Current Temperature"
        self._attr_unique_id = f"{config_entry.entry_id}_zone_{zone_name}_current_temp"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Multizone Heater",
            model="Multizone Controller",
        )

    @property
    def native_value(self) -> float | None:
        """Return the zone current temperature."""
        if self.coordinator.data and "zone_states" in self.coordinator.data:
            zone_data = self.coordinator.data["zone_states"].get(self._zone_name)
            if zone_data:
                return zone_data.get("current_temp")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or "zone_states" not in self.coordinator.data:
            return {}
        
        zone_data = self.coordinator.data["zone_states"].get(self._zone_name)
        if not zone_data:
            return {}
        
        return {
            "target_temp": zone_data.get("target_temp"),
            "target_offset": zone_data.get("target_offset"),
            "target_offset_closing": zone_data.get("target_offset_closing"),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success


class ZoneValveStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor exposing valve state for a zone."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MultizoneCoordinator,
        config_entry: ConfigEntry,
        zone_name: str,
    ) -> None:
        """Initialize the zone valve state sensor."""
        super().__init__(coordinator)
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Valve State"
        self._attr_unique_id = f"{config_entry.entry_id}_zone_{zone_name}_valve_state"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Multizone Heater",
            model="Multizone Controller",
        )

    def _get_valve_state(self) -> bool | None:
        """Get the valve open state from coordinator data."""
        if self.coordinator.data and "zone_states" in self.coordinator.data:
            zone_data = self.coordinator.data["zone_states"].get(self._zone_name)
            if zone_data:
                return zone_data.get("is_valve_open")
        return None

    @property
    def native_value(self) -> str | None:
        """Return the zone valve state."""
        is_open = self._get_valve_state()
        if is_open is None:
            return None  # Unknown state
        return "open" if is_open else "closed"

    @property
    def icon(self) -> str:
        """Return the icon based on valve state."""
        is_open = self._get_valve_state()
        if is_open is None:
            return "mdi:valve"  # Unknown state
        return "mdi:valve-open" if is_open else "mdi:valve-closed"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
