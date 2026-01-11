"""Climate platform for Multizone Heater integration."""
import asyncio
from datetime import timedelta
import logging
import time
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
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from .const import (
    CONF_ALL_SATISFIED_MODE,
    CONF_COMPENSATION_FACTOR,
    CONF_FALLBACK_ZONES,
    CONF_MAIN_CHANGE_THRESHOLD,
    CONF_MAIN_CLIMATE,
    CONF_MAIN_MAX_TEMP,
    CONF_MAIN_MIN_TEMP,
    CONF_MAIN_TEMP_SENSOR,
    CONF_MIN_VALVES_OPEN,
    CONF_PHYSICAL_CLOSE_ANTICIPATION,
    CONF_TARGET_TEMP_OFFSET,
    CONF_TARGET_TEMP_OFFSET_CLOSING,
    CONF_TEMPERATURE_AGGREGATION,
    CONF_TEMPERATURE_AGGREGATION_WEIGHT,
    CONF_TEMPERATURE_SENSOR,
    CONF_VALVE_SWITCH,
    CONF_VALVE_TRANSITION_DELAY,
    CONF_VIRTUAL_SWITCH,
    CONF_ZONE_CLIMATE,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DEFAULT_ALL_SATISFIED_MODE,
    DEFAULT_COMPENSATION_FACTOR,
    DEFAULT_HVAC_ACTION_DEADBAND,
    DEFAULT_MAIN_CHANGE_THRESHOLD,
    DEFAULT_MAIN_MAX_TEMP,
    DEFAULT_MAIN_MIN_TEMP,
    DEFAULT_MIN_VALVES_OPEN,
    DEFAULT_PHYSICAL_CLOSE_ANTICIPATION,
    DEFAULT_RECONCILIATION_INTERVAL,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TARGET_TEMP_OFFSET_CLOSING,
    DEFAULT_TEMPERATURE_AGGREGATION,
    DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT,
    DEFAULT_VALVE_TRANSITION_DELAY,
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
    main_temp_sensor = config.get(CONF_MAIN_TEMP_SENSOR)
    temperature_aggregation = config.get(
        CONF_TEMPERATURE_AGGREGATION, DEFAULT_TEMPERATURE_AGGREGATION
    )
    temperature_aggregation_weight = config.get(
        CONF_TEMPERATURE_AGGREGATION_WEIGHT, DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
    )
    min_valves_open = config.get(CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN)
    fallback_zones = config.get(CONF_FALLBACK_ZONES, [])
    compensation_factor = config.get(CONF_COMPENSATION_FACTOR, DEFAULT_COMPENSATION_FACTOR)
    valve_transition_delay = config.get(CONF_VALVE_TRANSITION_DELAY, DEFAULT_VALVE_TRANSITION_DELAY)
    main_min_temp = config.get(CONF_MAIN_MIN_TEMP, DEFAULT_MAIN_MIN_TEMP)
    main_max_temp = config.get(CONF_MAIN_MAX_TEMP, DEFAULT_MAIN_MAX_TEMP)
    main_change_threshold = config.get(CONF_MAIN_CHANGE_THRESHOLD, DEFAULT_MAIN_CHANGE_THRESHOLD)
    physical_close_anticipation = config.get(CONF_PHYSICAL_CLOSE_ANTICIPATION, DEFAULT_PHYSICAL_CLOSE_ANTICIPATION)
    all_satisfied_mode = config.get(CONF_ALL_SATISFIED_MODE, DEFAULT_ALL_SATISFIED_MODE)

    entities = [
        MultizoneHeaterClimate(
            hass,
            config_entry,
            zones,
            main_climate,
            main_temp_sensor,
            temperature_aggregation,
            temperature_aggregation_weight,
            min_valves_open,
            fallback_zones,
            compensation_factor,
            valve_transition_delay,
            main_min_temp,
            main_max_temp,
            main_change_threshold,
            physical_close_anticipation,
            all_satisfied_mode,
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
        main_temp_sensor: str | None,
        temperature_aggregation: str,
        temperature_aggregation_weight: int,
        min_valves_open: int,
        fallback_zones: list[str],
        compensation_factor: float,
        valve_transition_delay: int,
        main_min_temp: float,
        main_max_temp: float,
        main_change_threshold: float,
        physical_close_anticipation: float,
        all_satisfied_mode: int,
    ) -> None:
        """Initialize the multizone heater."""
        self.hass = hass
        self._config_entry = config_entry
        self._zones = zones
        self._main_climate_entity = main_climate
        self._main_temp_sensor = main_temp_sensor
        self._temperature_aggregation = temperature_aggregation
        self._temperature_aggregation_weight = temperature_aggregation_weight
        # Ensure min_valves_open is always an integer to prevent TypeError in range()
        # Convert to int to handle cases where it may have been stored as a float
        try:
            self._min_valves_open = int(min_valves_open)
            _LOGGER.debug(
                "Initialized min_valves_open: %s (type: %s, original: %s)",
                self._min_valves_open,
                type(self._min_valves_open).__name__,
                min_valves_open,
            )
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid min_valves_open value %s, using default %s",
                min_valves_open,
                DEFAULT_MIN_VALVES_OPEN,
            )
            self._min_valves_open = DEFAULT_MIN_VALVES_OPEN
        self._fallback_zone_names = fallback_zones
        self._compensation_factor = float(compensation_factor)
        self._valve_transition_delay = int(valve_transition_delay)
        self._main_min_temp = float(main_min_temp)
        self._main_max_temp = float(main_max_temp)
        self._main_change_threshold = float(main_change_threshold)
        self._physical_close_anticipation = float(physical_close_anticipation)
        self._all_satisfied_mode = int(all_satisfied_mode)

        # Track per-valve reopen suppression timestamps
        self._valve_no_reopen_until = {}
        # Track last main climate target to avoid unnecessary updates
        self._last_main_target = None

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
        
        # Track main temp sensor if configured
        if self._main_temp_sensor:
            tracked_entities.append(self._main_temp_sensor)
        
        @callback
        def async_sensor_changed(event):
            """Handle temperature sensor changes.
            
            Triggers valve control which is serialized via _update_lock.
            Multiple concurrent calls are safe - they will queue and execute sequentially.
            """
            self.async_schedule_update_ha_state(True)
            # Trigger valve control when zone states change
            if self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
                self.hass.async_create_task(self._async_control_valves())

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

        # Set up periodic reconciliation to ensure valve states are correct
        # This catches any missed events or state inconsistencies
        async def async_reconcile(_now):
            """Periodic reconciliation of valve states."""
            if self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
                _LOGGER.debug("Running periodic valve reconciliation")
                await self._async_control_valves()

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                async_reconcile,
                timedelta(seconds=DEFAULT_RECONCILIATION_INTERVAL)
            )
        )

        # Initial update
        await self.async_update()

        # Trigger initial valve control if in active mode
        if self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            await self._async_control_valves()

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
        """Control valve states based on zone temperatures with compensation logic."""
        async with self._update_lock:
            if self._hvac_mode not in (HVACMode.HEAT, HVACMode.COOL):
                return

            current_time = time.time()
            
            # Collect zone data for analysis
            zone_data = []
            zones_needing_action = []
            zone_targets = []
            per_zone_desired_main = []
            
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

                valve_entity = zone.get(CONF_VALVE_SWITCH)
                virtual_switch = zone.get(CONF_VIRTUAL_SWITCH)
                
                if not valve_entity:
                    continue
                
                # Check if zone needs action based on virtual switch state (or valve state if no virtual)
                check_entity = virtual_switch if virtual_switch else valve_entity
                target_offset = zone.get(CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET)
                target_offset_closing = zone.get(CONF_TARGET_TEMP_OFFSET_CLOSING, DEFAULT_TARGET_TEMP_OFFSET_CLOSING)

                # Get zone target temperature from zone climate entity if available
                zone_target = self._target_temperature  # Default fallback
                if zone.get(CONF_ZONE_CLIMATE):
                    climate_state = self.hass.states.get(zone[CONF_ZONE_CLIMATE])
                    if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                        target_attr = climate_state.attributes.get("temperature")
                        if target_attr is not None:
                            try:
                                zone_target = float(target_attr)
                            except (ValueError, TypeError):
                                _LOGGER.warning(
                                    "Unable to parse target temperature from climate %s, using default",
                                    zone[CONF_ZONE_CLIMATE],
                                )
                zone_targets.append(zone_target)

                # Get current valve state (or virtual switch state)
                check_state = self.hass.states.get(check_entity)
                is_currently_open = check_state and check_state.state == STATE_ON

                # Calculate compensation-based desired main temperature
                deficit = zone_target - current_temp
                
                if self._hvac_mode == HVACMode.HEAT:
                    # For heating: per_zone_desired_main = zone_target + compensation_factor * (zone_target - zone_current)
                    zone_desired_main = zone_target + self._compensation_factor * deficit
                    
                    # Determine if valve should be open with hysteresis
                    if is_currently_open:
                        # Use closing offset for already-open valves
                        # Apply physical close anticipation for early closing
                        physical_close_threshold = zone_target + target_offset_closing - self._physical_close_anticipation
                        should_open = current_temp < physical_close_threshold
                        
                        # If closing early, set reopen suppression
                        if not should_open and current_temp < (zone_target + target_offset_closing):
                            self._valve_no_reopen_until[valve_entity] = current_time + self._valve_transition_delay
                            _LOGGER.debug(
                                "Zone %s: Early physical close at %.1f°C (threshold %.1f°C), reopen suppressed for %ds",
                                zone.get(CONF_ZONE_NAME, valve_entity),
                                current_temp,
                                physical_close_threshold,
                                self._valve_transition_delay,
                            )
                    else:
                        # Use opening offset for closed valves
                        should_open = current_temp < (zone_target - target_offset)
                        
                        # Check reopen suppression
                        if should_open and valve_entity in self._valve_no_reopen_until:
                            if current_time < self._valve_no_reopen_until[valve_entity]:
                                should_open = False
                                _LOGGER.debug(
                                    "Zone %s: Reopen suppressed for %.0fs",
                                    zone.get(CONF_ZONE_NAME, valve_entity),
                                    self._valve_no_reopen_until[valve_entity] - current_time,
                                )
                            else:
                                # Suppression expired
                                del self._valve_no_reopen_until[valve_entity]
                else:  # COOL mode
                    # For cooling: per_zone_desired_main = zone_target - compensation_factor * (zone_current - zone_target)
                    # Simplified: zone_target + compensation_factor * deficit (deficit is negative for cooling)
                    zone_desired_main = zone_target + self._compensation_factor * deficit
                    
                    # For cooling, inverse logic
                    if is_currently_open:
                        should_open = current_temp > (zone_target - target_offset_closing)
                    else:
                        should_open = current_temp > (zone_target + target_offset)
                
                _LOGGER.debug(
                    "Zone %s: temp=%.1f°C, target=%.1f°C, deficit=%.1f°C, desired_main=%.1f°C, should_open=%s",
                    zone.get(CONF_ZONE_NAME, valve_entity),
                    current_temp,
                    zone_target,
                    deficit,
                    zone_desired_main,
                    should_open,
                )
                
                zone_data.append({
                    'valve': valve_entity,
                    'zone_name': zone.get(CONF_ZONE_NAME, valve_entity),
                    'current_temp': current_temp,
                    'zone_target': zone_target,
                    'should_open': should_open,
                    'zone_desired_main': zone_desired_main,
                })
                
                if should_open:
                    zones_needing_action.append(valve_entity)
                    per_zone_desired_main.append(zone_desired_main)

            # Calculate desired main climate target
            desired_main = None
            if zones_needing_action and per_zone_desired_main:
                # Zones need action - use compensation-based target
                if self._hvac_mode == HVACMode.HEAT:
                    # For heating: max of per-zone desired
                    desired_main = max(per_zone_desired_main)
                else:  # COOL
                    # For cooling: min of per-zone desired
                    desired_main = min(per_zone_desired_main)
                
                _LOGGER.debug(
                    "Zones needing action: %d, desired_main=%.1f°C (mode=%s)",
                    len(zones_needing_action),
                    desired_main,
                    self._hvac_mode,
                )
            elif zone_targets:
                # All zones satisfied - use slider-based interpolation
                min_target = min(zone_targets)
                max_target = max(zone_targets)
                avg_target = sum(zone_targets) / len(zone_targets)
                
                # Interpolate based on all_satisfied_mode (0=min, 50=avg, 100=max)
                weight = self._all_satisfied_mode
                if weight <= 50:
                    ratio = weight / 50.0
                    desired_main = min_target + (avg_target - min_target) * ratio
                else:
                    ratio = (weight - 50) / 50.0
                    desired_main = avg_target + (max_target - avg_target) * ratio
                
                _LOGGER.debug(
                    "All zones satisfied: min=%.1f, avg=%.1f, max=%.1f, slider=%d%%, desired_main=%.1f°C",
                    min_target,
                    avg_target,
                    max_target,
                    weight,
                    desired_main,
                )

            # Update main climate target if needed
            if desired_main is not None and self._main_climate_entity:
                # Round to 0.1°C and clamp to configured range
                desired_main = round(desired_main, 1)
                desired_main = max(self._main_min_temp, min(self._main_max_temp, desired_main))
                
                # Only update if change exceeds threshold
                if self._last_main_target is None or abs(desired_main - self._last_main_target) >= self._main_change_threshold:
                    _LOGGER.debug(
                        "Updating main climate from %.1f°C to %.1f°C (change %.1f°C >= threshold %.1f°C)",
                        self._last_main_target if self._last_main_target is not None else 0.0,
                        desired_main,
                        abs(desired_main - (self._last_main_target or 0.0)),
                        self._main_change_threshold,
                    )
                    
                    try:
                        await self.hass.services.async_call(
                            "climate",
                            "set_temperature",
                            {
                                "entity_id": self._main_climate_entity,
                                ATTR_TEMPERATURE: desired_main,
                            },
                            blocking=False,
                        )
                        self._last_main_target = desired_main
                    except Exception as err:
                        _LOGGER.error(
                            "Failed to set main climate temperature to %.1f°C: %s",
                            desired_main,
                            err,
                        )

            # Get current valve states
            current_valve_states = await self._async_get_valve_states()

            # Determine which valves to turn on/off
            valves_to_turn_on = set()
            valves_to_turn_off = set()

            for valve_entity in current_valve_states:
                if valve_entity in zones_needing_action:
                    valves_to_turn_on.add(valve_entity)
                else:
                    valves_to_turn_off.add(valve_entity)

            # Ensure minimum valves are open (heating mode only)
            if self._hvac_mode == HVACMode.HEAT and len(valves_to_turn_on) < self._min_valves_open:
                # Keep some valves open even if not needed - prefer fallback zones
                available_valves = list(valves_to_turn_off)
                
                # Sort to prefer fallback zones
                fallback_valves = []
                non_fallback_valves = []
                for valve in available_valves:
                    zone_name = None
                    for zone in self._zones:
                        if zone.get(CONF_VALVE_SWITCH) == valve:
                            zone_name = zone.get(CONF_ZONE_NAME)
                            break
                    
                    if zone_name in self._fallback_zone_names:
                        fallback_valves.append(valve)
                    else:
                        non_fallback_valves.append(valve)
                
                # Prioritize fallback zones
                sorted_valves = fallback_valves + non_fallback_valves
                
                needed = self._min_valves_open - len(valves_to_turn_on)
                _LOGGER.debug(
                    "Ensuring minimum valves open: current=%s, minimum=%s, needed=%s",
                    len(valves_to_turn_on),
                    self._min_valves_open,
                    needed,
                )
                for i in range(min(needed, len(sorted_valves))):
                    valve = sorted_valves[i]
                    valves_to_turn_on.add(valve)
                    valves_to_turn_off.discard(valve)

            # Two-phase valve operation: open first, wait, then close
            # Phase 1: Turn on valves that are currently off
            valves_actually_turning_on = [v for v in valves_to_turn_on if not current_valve_states.get(v)]
            if valves_actually_turning_on:
                tasks = []
                for valve_entity in valves_actually_turning_on:
                    domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                    tasks.append(
                        self._async_call_service_with_error_handling(
                            domain,
                            SERVICE_TURN_ON,
                            {"entity_id": valve_entity},
                            f"turn on valve {valve_entity}",
                        )
                    )
                
                _LOGGER.debug("Phase 1: Turning ON %d valves: %s", len(valves_actually_turning_on), valves_actually_turning_on)
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait for valve transition if we're also closing valves
                valves_actually_turning_off = [v for v in valves_to_turn_off if current_valve_states.get(v)]
                if valves_actually_turning_off:
                    _LOGGER.debug("Waiting %ds for valve transition before closing", self._valve_transition_delay)
                    await asyncio.sleep(self._valve_transition_delay)

            # Phase 2: Turn off valves that are currently on
            valves_actually_turning_off = [v for v in valves_to_turn_off if current_valve_states.get(v)]
            if valves_actually_turning_off:
                tasks = []
                for valve_entity in valves_actually_turning_off:
                    domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                    tasks.append(
                        self._async_call_service_with_error_handling(
                            domain,
                            SERVICE_TURN_OFF,
                            {"entity_id": valve_entity},
                            f"turn off valve {valve_entity}",
                        )
                    )
                
                _LOGGER.debug("Phase 2: Turning OFF %d valves: %s", len(valves_actually_turning_off), valves_actually_turning_off)
                await asyncio.gather(*tasks, return_exceptions=True)

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
