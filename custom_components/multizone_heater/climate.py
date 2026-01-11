"""Climate platform for Multizone Heater integration."""
import asyncio
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_FALLBACK_ZONES,
    CONF_MAIN_CLIMATE,
    CONF_MIN_VALVES_OPEN,
    CONF_TARGET_TEMP_OFFSET,
    CONF_TARGET_TEMP_OFFSET_CLOSING,
    CONF_TEMPERATURE_AGGREGATION,
    CONF_TEMPERATURE_AGGREGATION_WEIGHT,
    CONF_TEMPERATURE_SENSOR,
    CONF_VALVE_SWITCH,
    CONF_VIRTUAL_SWITCH,
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DEFAULT_HVAC_ACTION_DEADBAND,
    DEFAULT_MIN_VALVES_OPEN,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TARGET_TEMP_OFFSET_CLOSING,
    DEFAULT_TEMPERATURE_AGGREGATION,
    DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT,
    DOMAIN,
    TEMP_AGG_AVERAGE,
    TEMP_AGG_MAX,
    TEMP_AGG_MIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Multizone Heater climate from a config entry."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    zones = config.get(CONF_ZONES, [])
    main_climate = config.get(CONF_MAIN_CLIMATE)
    temperature_aggregation = config.get(
        CONF_TEMPERATURE_AGGREGATION, DEFAULT_TEMPERATURE_AGGREGATION
    )
    temperature_aggregation_weight = config.get(
        CONF_TEMPERATURE_AGGREGATION_WEIGHT, DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
    )
    min_valves_open = config.get(CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN)
    fallback_zones = config.get(CONF_FALLBACK_ZONES, [])

    entities = [
        MultizoneHeaterClimate(
            hass,
            config_entry,
            zones,
            main_climate,
            temperature_aggregation,
            temperature_aggregation_weight,
            min_valves_open,
            fallback_zones,
        )
    ]

    async_add_entities(entities)


class MultizoneHeaterClimate(ClimateEntity):
    """Representation of a Multizone Heater climate device."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_min_temp = 5.0
    _attr_max_temp = 35.0
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zones: list[dict[str, Any]],
        main_climate: str | None,
        temperature_aggregation: str,
        temperature_aggregation_weight: int,
        min_valves_open: int,
        fallback_zones: list[str],
    ) -> None:
        """Initialize the multizone heater."""
        self.hass = hass
        self._config_entry = config_entry
        self._zones = zones
        self._main_climate_entity = main_climate
        self._temperature_aggregation = temperature_aggregation
        self._temperature_aggregation_weight = temperature_aggregation_weight
        self._min_valves_open = min_valves_open
        self._fallback_zone_names = fallback_zones

        # Use Home Assistant's configured temperature unit
        self._attr_temperature_unit = hass.config.units.temperature_unit

        self._attr_unique_id = f"{config_entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Multizone Heater",
            model="Multizone Controller",
        )

        self._current_temperature = None
        self._target_temperature = 20.0
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.OFF
        self._supports_cooling = False
        
        # Determine supported HVAC modes based on main climate
        if main_climate:
            main_state = hass.states.get(main_climate)
            if main_state:
                main_hvac_modes = main_state.attributes.get("hvac_modes", [])
                self._supports_cooling = HVACMode.COOL in main_hvac_modes or "cool" in main_hvac_modes
        
        # Set available HVAC modes
        if self._supports_cooling:
            self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        else:
            self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

        self._update_lock = asyncio.Lock()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Validate cooling support for zones if main climate supports cooling
        if self._supports_cooling:
            for zone in self._zones:
                if zone.get(CONF_ZONE_CLIMATE):
                    zone_state = self.hass.states.get(zone[CONF_ZONE_CLIMATE])
                    if zone_state:
                        zone_hvac_modes = zone_state.attributes.get("hvac_modes", [])
                        if HVACMode.COOL not in zone_hvac_modes and "cool" not in zone_hvac_modes:
                            _LOGGER.warning(
                                "Zone '%s' climate entity does not support cooling. "
                                "Valve will be closed during cooling mode for this zone.",
                                zone.get(CONF_ZONE_NAME, zone.get(CONF_ZONE_CLIMATE))
                            )
        
        # Track all temperature sources (zone climate entities and sensors)
        tracked_entities = []
        for zone in self._zones:
            if zone.get(CONF_ZONE_CLIMATE):
                tracked_entities.append(zone[CONF_ZONE_CLIMATE])
            if zone.get(CONF_TEMPERATURE_SENSOR):
                tracked_entities.append(zone[CONF_TEMPERATURE_SENSOR])
            if zone.get(CONF_VIRTUAL_SWITCH):
                tracked_entities.append(zone[CONF_VIRTUAL_SWITCH])
        
        @callback
        def async_sensor_changed(event):
            """Handle temperature sensor changes."""
            self.async_schedule_update_ha_state(True)

        for entity in tracked_entities:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, entity, async_sensor_changed
                )
            )

        # Track main climate entity if configured
        if self._main_climate_entity:
            @callback
            def async_climate_changed(event):
                """Handle main climate changes."""
                self.async_schedule_update_ha_state(True)

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._main_climate_entity, async_climate_changed
                )
            )

        # Initial update
        await self.async_update()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation mode."""
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current running hvac operation."""
        return self._hvac_action

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._target_temperature = temperature

        # If main climate is configured, update its target temperature
        if self._main_climate_entity:
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {
                        "entity_id": self._main_climate_entity,
                        ATTR_TEMPERATURE: temperature,
                    },
                    blocking=True,
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to set temperature on main climate %s: %s",
                    self._main_climate_entity,
                    err,
                )

        await self._async_control_valves()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self._hvac_mode = hvac_mode

        if hvac_mode == HVACMode.OFF:
            # Turn off all valves except minimum required
            await self._async_turn_off_all_valves()
            
            # Turn off main climate if configured
            if self._main_climate_entity:
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {
                            "entity_id": self._main_climate_entity,
                            "hvac_mode": HVACMode.OFF,
                        },
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to turn off main climate %s: %s",
                        self._main_climate_entity,
                        err,
                    )
        elif hvac_mode == HVACMode.HEAT:
            # Turn on main climate if configured
            if self._main_climate_entity:
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {
                            "entity_id": self._main_climate_entity,
                            "hvac_mode": HVACMode.HEAT,
                        },
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to turn on main climate %s: %s",
                        self._main_climate_entity,
                        err,
                    )
            
            # Control valves based on zone temperatures
            await self._async_control_valves()
        elif hvac_mode == HVACMode.COOL:
            # Turn on main climate in cooling mode if configured
            if self._main_climate_entity:
                try:
                    await self.hass.services.async_call(
                        "climate",
                        "set_hvac_mode",
                        {
                            "entity_id": self._main_climate_entity,
                            "hvac_mode": HVACMode.COOL,
                        },
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to set cooling on main climate %s: %s",
                        self._main_climate_entity,
                        err,
                    )
            
            # Open fallback zone valves, close others during cooling
            await self._async_control_valves_for_cooling()

        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        # Calculate aggregated current temperature
        temperatures = []
        for zone in self._zones:
            # Try to get temperature from zone climate entity first, then sensor
            temp = None
            
            if zone.get(CONF_ZONE_CLIMATE):
                climate_state = self.hass.states.get(zone[CONF_ZONE_CLIMATE])
                if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    temp_attr = climate_state.attributes.get("current_temperature")
                    if temp_attr is not None:
                        try:
                            temp = float(temp_attr)
                        except (ValueError, TypeError):
                            _LOGGER.warning(
                                "Unable to parse temperature from climate %s",
                                zone[CONF_ZONE_CLIMATE],
                            )
            
            # If no temp from climate entity, try sensor override
            if temp is None and zone.get(CONF_TEMPERATURE_SENSOR):
                sensor_state = self.hass.states.get(zone[CONF_TEMPERATURE_SENSOR])
                if sensor_state and sensor_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    try:
                        temp = float(sensor_state.state)
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Unable to parse temperature from %s: %s",
                            zone[CONF_TEMPERATURE_SENSOR],
                            sensor_state.state,
                        )
            
            if temp is not None:
                temperatures.append(temp)

        if temperatures:
            if self._temperature_aggregation == TEMP_AGG_AVERAGE:
                self._current_temperature = sum(temperatures) / len(temperatures)
            elif self._temperature_aggregation == TEMP_AGG_MIN:
                self._current_temperature = min(temperatures)
            elif self._temperature_aggregation == TEMP_AGG_MAX:
                self._current_temperature = max(temperatures)
            else:
                # Use weight-based aggregation (0% = min, 50% = avg, 100% = max)
                min_temp = min(temperatures)
                max_temp = max(temperatures)
                avg_temp = sum(temperatures) / len(temperatures)
                
                # Interpolate between min and avg (0-50%) or avg and max (50-100%)
                weight = self._temperature_aggregation_weight
                if weight <= 50:
                    # Interpolate between min and avg
                    ratio = weight / 50.0
                    self._current_temperature = min_temp + (avg_temp - min_temp) * ratio
                else:
                    # Interpolate between avg and max
                    ratio = (weight - 50) / 50.0
                    self._current_temperature = avg_temp + (max_temp - avg_temp) * ratio
        else:
            self._current_temperature = None

        # Update HVAC action
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_action = HVACAction.OFF
        elif self._hvac_mode == HVACMode.COOL:
            if self._current_temperature is not None and self._target_temperature is not None:
                if self._current_temperature > self._target_temperature + DEFAULT_HVAC_ACTION_DEADBAND:
                    self._hvac_action = HVACAction.COOLING
                elif self._current_temperature < self._target_temperature - DEFAULT_HVAC_ACTION_DEADBAND:
                    self._hvac_action = HVACAction.IDLE
                else:
                    self._hvac_action = HVACAction.IDLE
            else:
                self._hvac_action = HVACAction.IDLE
        elif self._hvac_mode == HVACMode.HEAT:
            if self._current_temperature is not None and self._target_temperature is not None:
                if self._current_temperature < self._target_temperature - DEFAULT_HVAC_ACTION_DEADBAND:
                    self._hvac_action = HVACAction.HEATING
                elif self._current_temperature > self._target_temperature + DEFAULT_HVAC_ACTION_DEADBAND:
                    self._hvac_action = HVACAction.IDLE
                else:
                    # In deadband
                    valve_states = await self._async_get_valve_states()
                    if any(valve_states.values()):
                        self._hvac_action = HVACAction.HEATING
                    else:
                        self._hvac_action = HVACAction.IDLE
            else:
                self._hvac_action = HVACAction.IDLE
        else:
            self._hvac_action = HVACAction.IDLE

    async def _async_control_valves(self) -> None:
        """Control valve states based on zone temperatures (heating mode)."""
        async with self._update_lock:
            if self._hvac_mode != HVACMode.HEAT:
                return

            tasks = []
            zones_needing_heat = []

            for zone in self._zones:
                # Get temperature from zone climate or sensor
                current_temp = None
                if zone.get(CONF_ZONE_CLIMATE):
                    climate_state = self.hass.states.get(zone[CONF_ZONE_CLIMATE])
                    if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                        temp_attr = climate_state.attributes.get("current_temperature")
                        if temp_attr is not None:
                            try:
                                current_temp = float(temp_attr)
                            except (ValueError, TypeError):
                                pass
                
                if current_temp is None and zone.get(CONF_TEMPERATURE_SENSOR):
                    sensor_state = self.hass.states.get(zone[CONF_TEMPERATURE_SENSOR])
                    if sensor_state and sensor_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                        try:
                            current_temp = float(sensor_state.state)
                        except (ValueError, TypeError):
                            pass

                if current_temp is None:
                    continue

                # Determine which switch to use for checking state
                # Use virtual switch if available (for coordination with zone climate)
                # Otherwise use physical valve
                valve_entity = zone.get(CONF_VALVE_SWITCH)
                virtual_switch = zone.get(CONF_VIRTUAL_SWITCH)
                
                if not valve_entity:
                    continue
                
                # Check if zone needs heating based on virtual switch state (or valve state if no virtual)
                check_entity = virtual_switch if virtual_switch else valve_entity
                target_offset = zone.get(CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET)
                target_offset_closing = zone.get(CONF_TARGET_TEMP_OFFSET_CLOSING, DEFAULT_TARGET_TEMP_OFFSET_CLOSING)

                zone_target = self._target_temperature

                # Get current valve state (or virtual switch state)
                check_state = self.hass.states.get(check_entity)
                is_currently_open = check_state and check_state.state == STATE_ON

                # Determine if valve should be open with hysteresis
                # If valve is currently closed, open when below (target - offset)
                # If valve is currently open, close when above (target + offset_closing)
                if is_currently_open:
                    # Use closing offset for already-open valves
                    should_open = current_temp < (zone_target + target_offset_closing)
                else:
                    # Use opening offset for closed valves
                    should_open = current_temp < (zone_target - target_offset)
                
                if should_open:
                    zones_needing_heat.append(valve_entity)

            # Get current valve states
            current_valve_states = await self._async_get_valve_states()

            # Determine which valves to turn on/off
            valves_to_turn_on = set()
            valves_to_turn_off = set()

            for valve_entity in current_valve_states:
                if valve_entity in zones_needing_heat:
                    valves_to_turn_on.add(valve_entity)
                else:
                    valves_to_turn_off.add(valve_entity)

            # Ensure minimum valves are open
            if len(valves_to_turn_on) < self._min_valves_open:
                # Keep some valves open even if not needed
                available_valves = list(valves_to_turn_off)
                needed = self._min_valves_open - len(valves_to_turn_on)
                for i in range(min(needed, len(available_valves))):
                    valve = available_valves[i]
                    valves_to_turn_on.add(valve)
                    valves_to_turn_off.discard(valve)

            # Turn on valves asynchronously
            for valve_entity in valves_to_turn_on:
                if not current_valve_states.get(valve_entity):
                    # Extract domain from entity_id to support non-switch valves
                    domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                    tasks.append(
                        self._async_call_service_with_error_handling(
                            domain,
                            SERVICE_TURN_ON,
                            {"entity_id": valve_entity},
                            f"turn on valve {valve_entity}",
                        )
                    )

            # Turn off valves asynchronously
            for valve_entity in valves_to_turn_off:
                if current_valve_states.get(valve_entity):
                    # Extract domain from entity_id to support non-switch valves
                    domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                    tasks.append(
                        self._async_call_service_with_error_handling(
                            domain,
                            SERVICE_TURN_OFF,
                            {"entity_id": valve_entity},
                            f"turn off valve {valve_entity}",
                        )
                    )

            # Execute all valve changes in parallel
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Update cached valve states
            self._last_valve_states = {
                valve: valve in valves_to_turn_on
                for valve in current_valve_states
            }

    async def _async_get_valve_states(self) -> dict[str, bool]:
        """Get current states of all physical valves."""
        valve_states = {}
        for zone in self._zones:
            valve_entity = zone.get(CONF_VALVE_SWITCH)
            if not valve_entity:
                continue
                
            state = self.hass.states.get(valve_entity)
            
            if state:
                valve_states[valve_entity] = state.state == STATE_ON
            else:
                valve_states[valve_entity] = False

        return valve_states

    async def _async_call_service_with_error_handling(
        self, domain: str, service: str, service_data: dict, operation: str
    ) -> None:
        """Call a service with error handling."""
        try:
            await self.hass.services.async_call(
                domain,
                service,
                service_data,
                blocking=False,
            )
        except Exception as err:
            _LOGGER.error("Failed to %s: %s", operation, err)

    async def _async_turn_off_all_valves(self) -> None:
        """Turn off all valves except minimum required."""
        async with self._update_lock:
            valve_entities = [zone.get(CONF_VALVE_SWITCH) for zone in self._zones if zone.get(CONF_VALVE_SWITCH)]
            tasks = []

            # Determine which valves to keep open
            valves_to_keep_open = valve_entities[:self._min_valves_open]

            for valve_entity in valve_entities:
                if valve_entity not in valves_to_keep_open:
                    # Extract domain from entity_id to support non-switch valves
                    domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                    tasks.append(
                        self._async_call_service_with_error_handling(
                            domain,
                            SERVICE_TURN_OFF,
                            {"entity_id": valve_entity},
                            f"turn off valve {valve_entity}",
                        )
                    )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _async_control_valves_for_cooling(self) -> None:
        """Control valves for cooling mode - open only fallback zones."""
        async with self._update_lock:
            if self._hvac_mode != HVACMode.COOL:
                return

            tasks = []
            fallback_valve_entities = []
            
            # Get fallback zone valve entities
            for zone in self._zones:
                zone_name = zone.get(CONF_ZONE_NAME)
                if zone_name in self._fallback_zone_names:
                    valve_entity = zone.get(CONF_VALVE_SWITCH)
                    if valve_entity:
                        fallback_valve_entities.append(valve_entity)

            # Get all valve entities
            all_valve_entities = [zone.get(CONF_VALVE_SWITCH) for zone in self._zones if zone.get(CONF_VALVE_SWITCH)]
            
            # Get current valve states
            current_valve_states = await self._async_get_valve_states()

            # Open fallback zone valves
            for valve_entity in fallback_valve_entities:
                if not current_valve_states.get(valve_entity):
                    domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                    tasks.append(
                        self._async_call_service_with_error_handling(
                            domain,
                            SERVICE_TURN_ON,
                            {"entity_id": valve_entity},
                            f"turn on fallback valve {valve_entity}",
                        )
                    )

            # Close all non-fallback valves
            for valve_entity in all_valve_entities:
                if valve_entity not in fallback_valve_entities:
                    if current_valve_states.get(valve_entity):
                        domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                        tasks.append(
                            self._async_call_service_with_error_handling(
                                domain,
                                SERVICE_TURN_OFF,
                                {"entity_id": valve_entity},
                                f"turn off valve {valve_entity} for cooling",
                            )
                        )

            # Execute all valve changes in parallel
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
            _LOGGER.info(
                "Cooling mode: Opened %d fallback zone valve(s), closed %d non-fallback valve(s)",
                len(fallback_valve_entities),
                len(all_valve_entities) - len(fallback_valve_entities)
            )
