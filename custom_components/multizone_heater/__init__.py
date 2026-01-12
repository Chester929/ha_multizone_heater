"""The Multizone Heater integration."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_ALL_SATISFIED_MODE,
    CONF_COMPENSATION_FACTOR,
    CONF_MAIN_CLIMATE,
    CONF_MAIN_MAX_TEMP,
    CONF_MAIN_MIN_TEMP,
    CONF_MAIN_TEMP_SENSOR,
    CONF_TARGET_TEMP_OFFSET,
    CONF_TARGET_TEMP_OFFSET_CLOSING,
    CONF_TEMPERATURE_SENSOR,
    CONF_UPDATE_INTERVAL,
    CONF_VALVE_SWITCH,
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DEFAULT_ALL_SATISFIED_MODE,
    DEFAULT_COMPENSATION_FACTOR,
    DEFAULT_MAIN_MAX_TEMP,
    DEFAULT_MAIN_MIN_TEMP,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TARGET_TEMP_OFFSET_CLOSING,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import MultizoneCoordinator
from .core import ZoneData

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Multizone Heater from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Get configuration
    config = entry.data
    zones_config = config.get(CONF_ZONES, [])
    main_climate = config.get(CONF_MAIN_CLIMATE)
    main_temp_sensor = config.get(CONF_MAIN_TEMP_SENSOR)
    compensation_factor = config.get(CONF_COMPENSATION_FACTOR, DEFAULT_COMPENSATION_FACTOR)
    all_satisfied_mode = config.get(CONF_ALL_SATISFIED_MODE, DEFAULT_ALL_SATISFIED_MODE)
    main_min_temp = config.get(CONF_MAIN_MIN_TEMP, DEFAULT_MAIN_MIN_TEMP)
    main_max_temp = config.get(CONF_MAIN_MAX_TEMP, DEFAULT_MAIN_MAX_TEMP)
    update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    
    # Create async getter callables for coordinator
    async def get_external_target() -> float | None:
        """Get the external main climate target temperature."""
        if main_climate:
            state = hass.states.get(main_climate)
            if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                temp_attr = state.attributes.get("temperature")
                if temp_attr is not None:
                    try:
                        return float(temp_attr)
                    except (ValueError, TypeError):
                        _LOGGER.warning("Unable to parse target from main climate %s", main_climate)
        return None
    
    async def get_zone_data() -> list[ZoneData]:
        """Get zone sensor data."""
        zones = []
        for zone_config in zones_config:
            zone_name = zone_config.get(CONF_ZONE_NAME, "Unknown")
            
            # Get current temperature
            current_temp = None
            if zone_config.get(CONF_ZONE_CLIMATE):
                climate_state = hass.states.get(zone_config[CONF_ZONE_CLIMATE])
                if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    temp_attr = climate_state.attributes.get("current_temperature")
                    if temp_attr is not None:
                        try:
                            current_temp = float(temp_attr)
                        except (ValueError, TypeError):
                            pass
            
            if current_temp is None and zone_config.get(CONF_TEMPERATURE_SENSOR):
                sensor_state = hass.states.get(zone_config[CONF_TEMPERATURE_SENSOR])
                if sensor_state and sensor_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    try:
                        current_temp = float(sensor_state.state)
                    except (ValueError, TypeError):
                        pass
            
            # Get target temperature
            target_temp = 20.0  # Default
            if zone_config.get(CONF_ZONE_CLIMATE):
                climate_state = hass.states.get(zone_config[CONF_ZONE_CLIMATE])
                if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    target_attr = climate_state.attributes.get("temperature")
                    if target_attr is not None:
                        try:
                            target_temp = float(target_attr)
                        except (ValueError, TypeError):
                            pass
            
            # Get valve state
            is_valve_open = False
            if zone_config.get(CONF_VALVE_SWITCH):
                valve_state = hass.states.get(zone_config[CONF_VALVE_SWITCH])
                if valve_state:
                    is_valve_open = valve_state.state == "on"
            
            zones.append(ZoneData(
                name=zone_name,
                current_temp=current_temp,
                target_temp=target_temp,
                target_offset=zone_config.get(CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET),
                target_offset_closing=zone_config.get(CONF_TARGET_TEMP_OFFSET_CLOSING, DEFAULT_TARGET_TEMP_OFFSET_CLOSING),
                is_valve_open=is_valve_open,
            ))
        
        return zones
    
    async def get_hvac_mode() -> str:
        """Get current HVAC mode from main climate."""
        if main_climate:
            state = hass.states.get(main_climate)
            if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                return state.state
        return "off"
    
    # Create coordinator
    coordinator = MultizoneCoordinator(
        hass=hass,
        update_interval=update_interval,
        external_target_getter=get_external_target,
        zone_sensor_getter=get_zone_data,
        hvac_mode_getter=get_hvac_mode,
        compensation_factor=compensation_factor,
        all_satisfied_mode=all_satisfied_mode,
        main_min_temp=main_min_temp,
        main_max_temp=main_max_temp,
    )
    
    # Store coordinator and config
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "config": entry.data,
    }

    # Create device registry entry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="Multizone Heater",
        model="Multizone Controller",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
