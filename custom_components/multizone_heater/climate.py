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
    DEFAULT_VALVE_TRANSITION_DELAY,
    DEFAULT_ZONE_TARGET_CHANGE_DELAY,
    DOMAIN,
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
    _attr_entity_registry_enabled_default = False  # Hidden by default, runs in background
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
        # Track pending timers for debouncing (separate for valve and main climate)
        self._zone_target_change_valve_timer = None
        self._zone_target_change_main_timer = None
        # Track pending delayed valve closing task
        self._delayed_valve_close_task = None

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

            For zone climate target temperature changes:
            - Debounces BOTH valve control AND main climate updates (run in parallel)

            For other changes (current temperature, virtual switch):
            - Triggers valve control immediately
            - Triggers main climate update immediately
            """
            # Check if this is a target temperature change in a zone climate entity
            is_zone_target_change = False
            if event.data.get("new_state") and event.data.get("old_state"):
                new_state = event.data["new_state"]
                old_state = event.data["old_state"]

                # Check if the entity is a climate entity
                if new_state.domain == "climate":
                    new_target = new_state.attributes.get("temperature")
                    old_target = old_state.attributes.get("temperature")

                    # Detect target temperature changes (not current temperature)
                    if new_target is not None and old_target is not None:
                        try:
                            if abs(float(new_target) - float(old_target)) >= 0.01:
                                is_zone_target_change = True
                                _LOGGER.debug(
                                    "Zone climate %s target changed from %.1f to %.1f - debouncing valve and main climate updates",
                                    new_state.entity_id,
                                    float(old_target),
                                    float(new_target),
                                )
                        except (ValueError, TypeError):
                            pass

            self.async_schedule_update_ha_state(True)

            if is_zone_target_change and self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
                # For zone target changes, debounce BOTH valve control and main climate update
                # These run as separate parallel async tasks

                # Cancel existing valve timer if present
                if self._zone_target_change_valve_timer and not self._zone_target_change_valve_timer.done():
                    try:
                        self._zone_target_change_valve_timer.cancel()
                    except Exception:
                        pass  # Timer might have just completed

                # Cancel existing main climate timer if present
                if self._zone_target_change_main_timer and not self._zone_target_change_main_timer.done():
                    try:
                        self._zone_target_change_main_timer.cancel()
                    except Exception:
                        pass  # Timer might have just completed

                # Create both debounced tasks - they run in parallel
                self._zone_target_change_valve_timer = self.hass.async_create_task(
                    self._async_delayed_valve_control()
                )
                self._zone_target_change_main_timer = self.hass.async_create_task(
                    self._async_delayed_main_climate_update()
                )

            elif self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
                # For non-target changes (temperature sensor updates, virtual switch, etc.)
                # trigger both valve control and main climate update immediately (in parallel)
                self.hass.async_create_task(self._async_control_valves())
                self.hass.async_create_task(self._async_update_main_climate())

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
                """Handle main climate changes.

                When main climate HVAC mode changes to OFF, close all valves except fallback zones.
                When main climate is in any other mode, manage valves normally.
                """
                # Get the new state
                new_state = event.data.get("new_state")
                if new_state:
                    main_hvac_mode = new_state.state
                    _LOGGER.debug("Main climate HVAC mode changed to: %s", main_hvac_mode)

                    # If main climate is OFF, close all valves except fallback zones
                    if main_hvac_mode == HVACMode.OFF:
                        _LOGGER.info("Main climate is OFF - closing all valves except fallback zones")
                        self.hass.async_create_task(self._async_close_valves_except_fallback())

                self.async_schedule_update_ha_state(True)

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, self._main_climate_entity, async_climate_changed
                )
            )

        # Set up periodic reconciliation to ensure valve states are correct
        # This catches any missed events or state inconsistencies
        async def async_reconcile(_now):
            """Periodic reconciliation of valve states and main climate."""
            if self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
                _LOGGER.debug("Running periodic reconciliation")
                # Run valve control and main climate update in parallel for better performance
                await asyncio.gather(
                    self._async_control_valves(),
                    self._async_update_main_climate(),
                    return_exceptions=True
                )

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                async_reconcile,
                timedelta(seconds=DEFAULT_RECONCILIATION_INTERVAL)
            )
        )

        # Initial update
        await self.async_update()

        # Trigger initial valve control and main climate update if in active mode
        # Run in parallel for better startup performance
        if self._hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            await asyncio.gather(
                self._async_control_valves(),
                self._async_update_main_climate(),
                return_exceptions=True
            )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        # Cancel any pending debounce timers to prevent resource leaks
        if self._zone_target_change_valve_timer and not self._zone_target_change_valve_timer.done():
            try:
                self._zone_target_change_valve_timer.cancel()
                _LOGGER.debug("Cancelled pending valve debounce timer during cleanup")
            except Exception as err:
                _LOGGER.warning("Error cancelling valve debounce timer: %s", err)

        if self._zone_target_change_main_timer and not self._zone_target_change_main_timer.done():
            try:
                self._zone_target_change_main_timer.cancel()
                _LOGGER.debug("Cancelled pending main climate debounce timer during cleanup")
            except Exception as err:
                _LOGGER.warning("Error cancelling main climate debounce timer: %s", err)

        # Cancel pending delayed valve closing task
        if self._delayed_valve_close_task and not self._delayed_valve_close_task.done():
            try:
                self._delayed_valve_close_task.cancel()
                _LOGGER.debug("Cancelled pending delayed valve close task during cleanup")
            except Exception as err:
                _LOGGER.warning("Error cancelling delayed valve close task: %s", err)

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
                    blocking=False,
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
        """Set new target hvac mode for this integration.

        Note: This sets the multizone heater's mode, NOT the main climate.
        The main climate HVAC mode is managed externally by the user.
        """
        self._hvac_mode = hvac_mode

        if hvac_mode == HVACMode.OFF:
            # Turn off all valves except fallback zones
            await self._async_turn_off_all_valves()
        elif hvac_mode == HVACMode.HEAT:
            # Control valves based on zone temperatures and update main climate
            await asyncio.gather(
                self._async_control_valves(),
                self._async_update_main_climate(),
                return_exceptions=True
            )
        elif hvac_mode == HVACMode.COOL:
            # Open fallback zone valves, close others during cooling and update main climate
            await asyncio.gather(
                self._async_control_valves_for_cooling(),
                self._async_update_main_climate(),
                return_exceptions=True
            )

        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        # This entity is used for control only, not for temperature display
        # Current temperature is intentionally not set
        self._current_temperature = None

        # Update HVAC action based on valve states and mode
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_action = HVACAction.OFF
        elif self._hvac_mode == HVACMode.COOL:
            # In cooling mode, check if any valves are open
            valve_states = await self._async_get_valve_states()
            if any(valve_states.values()):
                self._hvac_action = HVACAction.COOLING
            else:
                self._hvac_action = HVACAction.IDLE
        elif self._hvac_mode == HVACMode.HEAT:
            # In heating mode, check if any valves are open
            valve_states = await self._async_get_valve_states()
            if any(valve_states.values()):
                self._hvac_action = HVACAction.HEATING
            else:
                self._hvac_action = HVACAction.IDLE
        else:
            self._hvac_action = HVACAction.IDLE

    async def _async_delayed_valve_control(self) -> None:
        """Execute valve control after debounce delay."""
        try:
            await asyncio.sleep(DEFAULT_ZONE_TARGET_CHANGE_DELAY)
            _LOGGER.debug("Valve debounce delay complete - executing valve control")
            await self._async_control_valves()
        except asyncio.CancelledError:
            _LOGGER.debug("Valve debounce timer cancelled - newer target change received")
            raise  # Re-raise to ensure proper cancellation
        except Exception as err:
            _LOGGER.error("Error in delayed valve control: %s", err, exc_info=True)
        finally:
            self._zone_target_change_valve_timer = None

    async def _async_delayed_main_climate_update(self) -> None:
        """Execute main climate update after debounce delay."""
        try:
            await asyncio.sleep(DEFAULT_ZONE_TARGET_CHANGE_DELAY)
            _LOGGER.debug("Main climate debounce delay complete - updating main climate")
            await self._async_update_main_climate()
        except asyncio.CancelledError:
            _LOGGER.debug("Main climate debounce timer cancelled - newer target change received")
            raise  # Re-raise to ensure proper cancellation
        except Exception as err:
            _LOGGER.error("Error in delayed main climate update: %s", err, exc_info=True)
        finally:
            self._zone_target_change_main_timer = None

    async def _async_update_main_climate(self) -> None:
        """Update main climate target temperature based on zone needs.

        This method calculates and updates the main climate target temperature
        separately from valve control, allowing for debounced updates when zone
        targets change rapidly (e.g., slider adjustments).

        Note: This method does NOT use _update_lock to allow parallel execution
        with valve control. It only reads zone states, which is safe for concurrent access.
        """
        if self._hvac_mode not in (HVACMode.HEAT, HVACMode.COOL):
            return

        if not self._main_climate_entity:
            return

        # Calculate desired main climate target using helper method
        desired_main, is_holding_mode = self._calculate_desired_main_target()

        # Log the mode and target
        if desired_main is not None:
            if is_holding_mode:
                _LOGGER.debug(
                    "Main climate update: Holding mode (all zones satisfied), desired=%.1f°C (slider=%d%%)",
                    desired_main,
                    self._all_satisfied_mode,
                )
            else:
                _LOGGER.debug(
                    "Main climate update: Heating mode (zones need action), desired=%.1f°C",
                    desired_main,
                )

        # Update main climate target if needed
        if desired_main is not None:
            # Get the current target from the main climate entity
            # This ensures we detect external changes to the target temperature
            current_main_target = None
            climate_state = self.hass.states.get(self._main_climate_entity)
            if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                temp_attr = climate_state.attributes.get("temperature")
                if temp_attr is not None:
                    try:
                        current_main_target = float(temp_attr)
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Unable to parse target temperature from main climate %s",
                            self._main_climate_entity,
                        )

            # Only update if change exceeds threshold
            # Compare with actual current target, not just our cached value
            cached_target = self._last_main_target if self._last_main_target is not None else 0.0
            
            if current_main_target is not None:
                should_update = abs(desired_main - current_main_target) >= self._main_change_threshold
            else:
                # If we can't read the current target, use our cached value as fallback
                should_update = self._last_main_target is None or abs(desired_main - self._last_main_target) >= self._main_change_threshold

            if should_update:
                if current_main_target is not None:
                    _LOGGER.info(
                        "Updating main climate %s from %.1f°C to %.1f°C (change %.1f°C)",
                        self._main_climate_entity,
                        current_main_target,
                        desired_main,
                        abs(desired_main - current_main_target),
                    )
                else:
                    _LOGGER.info(
                        "Updating main climate %s to %.1f°C (current target unavailable)",
                        self._main_climate_entity,
                        desired_main,
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
                    _LOGGER.debug("Main climate update service call succeeded")
                except Exception as err:
                    _LOGGER.error(
                        "Failed to set main climate temperature to %.1f°C: %s",
                        desired_main,
                        err,
                    )
            else:
                if current_main_target is not None:
                    _LOGGER.debug(
                        "Skipping main climate update: current=%.1f°C, desired=%.1f°C, change=%.1f°C (threshold=%.1f°C)",
                        current_main_target,
                        desired_main,
                        abs(desired_main - current_main_target),
                        self._main_change_threshold,
                    )
                else:
                    _LOGGER.debug(
                        "Skipping main climate update: current target unknown, cached=%.1f°C, desired=%.1f°C (threshold=%.1f°C)",
                        cached_target,
                        desired_main,
                        self._main_change_threshold,
                    )

    def _get_zone_satisfaction_bounds(
        self, zone_target: float, target_offset: float, target_offset_closing: float
    ) -> tuple[float, float]:
        """Calculate satisfaction bounds for a zone based on HVAC mode.

        Args:
            zone_target: Target temperature for the zone
            target_offset: Opening offset (threshold below target for heating, above for cooling)
            target_offset_closing: Closing offset (threshold above target for heating, below for cooling)

        Returns:
            Tuple of (lower_bound, upper_bound) defining the satisfaction range
        """
        if self._hvac_mode == HVACMode.HEAT:
            # Heating: satisfied range is [target - opening_offset, target + closing_offset]
            lower_bound = zone_target - target_offset
            upper_bound = zone_target + target_offset_closing
        else:  # COOL mode
            # Cooling: satisfied range is [target - closing_offset, target + opening_offset]
            lower_bound = zone_target - target_offset_closing
            upper_bound = zone_target + target_offset

        return lower_bound, upper_bound

    def _get_zone_status(
        self, current_temp: float, lower_bound: float, upper_bound: float
    ) -> str:
        """Determine zone satisfaction status based on temperature and bounds.

        Args:
            current_temp: Current zone temperature
            lower_bound: Lower bound of satisfaction range
            upper_bound: Upper bound of satisfaction range

        Returns:
            Status string: 'underheated', 'overheated', 'satisfied', or 'undercooled'
        """
        if self._hvac_mode == HVACMode.HEAT:
            if current_temp < lower_bound:
                return "underheated"
            elif current_temp > upper_bound:
                return "overheated"
            else:
                return "satisfied"
        else:  # COOL mode
            if current_temp > upper_bound:
                return "overheated"
            elif current_temp < lower_bound:
                return "undercooled"
            else:
                return "satisfied"

    def _calculate_desired_main_target(self) -> tuple[float | None, bool]:
        """Calculate desired main climate target without updating it.

        Returns:
            Tuple of (desired_main_temp, is_holding_mode)
            - desired_main_temp: Calculated target temperature for main climate, or None
            - is_holding_mode: True if all zones are satisfied/overheated (holding mode),
                              False if any zone is underheated (heating mode)
        """
        zone_targets = []
        per_zone_desired_main = []
        zones_needing_action = []

        for zone in self._zones:
            current_temp = self._get_zone_temperature(zone)
            if current_temp is None:
                _LOGGER.debug(
                    "Skipping zone %s: no temperature available",
                    zone.get(CONF_ZONE_NAME, "unknown")
                )
                continue

            valve_entity = zone.get(CONF_VALVE_SWITCH)
            if not valve_entity:
                _LOGGER.debug(
                    "Skipping zone %s: no valve configured",
                    zone.get(CONF_ZONE_NAME, "unknown")
                )
                continue

            zone_target = self._get_zone_target_temperature(zone)
            zone_targets.append(zone_target)

            target_offset = zone.get(CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET)
            target_offset_closing = zone.get(CONF_TARGET_TEMP_OFFSET_CLOSING, DEFAULT_TARGET_TEMP_OFFSET_CLOSING)

            # Calculate compensation-based desired main temperature
            deficit = zone_target - current_temp
            zone_desired_main = zone_target + self._compensation_factor * deficit

            # Get satisfaction bounds
            lower_bound, upper_bound = self._get_zone_satisfaction_bounds(
                zone_target, target_offset, target_offset_closing
            )

            # Zone needs action if outside satisfaction range (underheated or overheated)
            needs_action = current_temp < lower_bound or current_temp > upper_bound

            _LOGGER.debug(
                "Zone %s: current=%.1f°C, target=%.1f°C, bounds=[%.1f, %.1f]°C, needs_action=%s",
                zone.get(CONF_ZONE_NAME, valve_entity),
                current_temp,
                zone_target,
                lower_bound,
                upper_bound,
                needs_action,
            )

            if needs_action:
                zones_needing_action.append(valve_entity)
                per_zone_desired_main.append(zone_desired_main)

        # Calculate desired main climate target
        desired_main = None
        is_holding_mode = False

        if zones_needing_action and per_zone_desired_main:
            # Heating mode: zones need action - use compensation-based target
            if self._hvac_mode == HVACMode.HEAT:
                desired_main = max(per_zone_desired_main)
            else:  # COOL
                desired_main = min(per_zone_desired_main)
            is_holding_mode = False
        elif zone_targets:
            # Holding mode: All zones satisfied - use slider-based interpolation
            min_target = min(zone_targets)
            max_target = max(zone_targets)
            avg_target = sum(zone_targets) / len(zone_targets)

            weight = self._all_satisfied_mode
            if weight <= 50:
                ratio = weight / 50.0
                desired_main = min_target + (avg_target - min_target) * ratio
            else:
                ratio = (weight - 50) / 50.0
                desired_main = avg_target + (max_target - avg_target) * ratio
            is_holding_mode = True

        if desired_main is not None:
            # Round and clamp to configured range
            desired_main = round(desired_main, 1)
            desired_main = max(self._main_min_temp, min(self._main_max_temp, desired_main))

        _LOGGER.debug(
            "Main target calculation complete: desired=%.1f°C, is_holding=%s, zones_needing_action=%d, zone_targets=%s",
            desired_main if desired_main is not None else 0.0,
            is_holding_mode,
            len(zones_needing_action),
            zone_targets,
        )

        return desired_main, is_holding_mode

    async def _async_control_valves(self) -> None:
        """Control valve states based on zone temperatures.

        This method focuses solely on valve control for immediate response to
        temperature changes. Main climate target updates are handled separately
        in _async_update_main_climate() which can be debounced.
        """
        async with self._update_lock:
            if self._hvac_mode not in (HVACMode.HEAT, HVACMode.COOL):
                return

            current_time = time.time()

            # First, calculate what the main climate target would be
            # This is needed to determine valve state for satisfied zones
            desired_main_target, is_holding_mode = self._calculate_desired_main_target()

            # Collect zone data and determine which valves should be open
            zones_needing_action = []

            for zone in self._zones:
                # Get temperature from zone climate or sensor
                current_temp = self._get_zone_temperature(zone)
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
                zone_target = self._get_zone_target_temperature(zone)

                # Get current valve state (or virtual switch state)
                check_state = self.hass.states.get(check_entity)
                is_currently_open = check_state and check_state.state == STATE_ON

                # Get satisfaction bounds using helper method
                lower_bound, upper_bound = self._get_zone_satisfaction_bounds(
                    zone_target, target_offset, target_offset_closing
                )

                # Get zone status
                zone_status = self._get_zone_status(current_temp, lower_bound, upper_bound)

                # Determine if valve should be open with hysteresis
                if self._hvac_mode == HVACMode.HEAT:
                    if zone_status == "underheated":
                        # Zone needs heat - always open valve
                        should_open = True

                        # Check reopen suppression for closed valves
                        if not is_currently_open and valve_entity in self._valve_no_reopen_until:
                            if current_time < self._valve_no_reopen_until[valve_entity]:
                                should_open = False
                                _LOGGER.debug(
                                    "Zone %s: Underheated but reopen suppressed for %.0fs",
                                    zone.get(CONF_ZONE_NAME, valve_entity),
                                    self._valve_no_reopen_until[valve_entity] - current_time,
                                )
                            else:
                                # Suppression expired
                                del self._valve_no_reopen_until[valve_entity]

                    elif zone_status == "overheated":
                        # Zone is overheated - always close valve
                        should_open = False

                    else:  # zone_status == "satisfied"
                        # Zone is satisfied - decision depends on mode and main climate target
                        if is_holding_mode:
                            # Holding mode: all zones satisfied/overheated - open valve to maintain temp
                            should_open = True
                        elif desired_main_target is not None:
                            # Heating mode: some zones need heat
                            # Open valve only if zone target >= main target (won't overheat)
                            should_open = zone_target >= desired_main_target

                            _LOGGER.debug(
                                "Zone %s: Satisfied in heating mode, zone_target=%.1f°C, main_target=%.1f°C, should_open=%s",
                                zone.get(CONF_ZONE_NAME, valve_entity),
                                zone_target,
                                desired_main_target,
                                should_open,
                            )
                        else:
                            # No main target calculated - close valve to be safe
                            should_open = False

                        # Apply physical close anticipation for open valves
                        if is_currently_open and should_open:
                            physical_close_threshold = upper_bound - self._physical_close_anticipation
                            if current_temp >= physical_close_threshold:
                                should_open = False

                                # Set reopen suppression if closing early
                                if current_temp < upper_bound:
                                    self._valve_no_reopen_until[valve_entity] = current_time + self._valve_transition_delay
                                    _LOGGER.debug(
                                        "Zone %s: Early physical close at %.1f°C (threshold %.1f°C), reopen suppressed for %ds",
                                        zone.get(CONF_ZONE_NAME, valve_entity),
                                        current_temp,
                                        physical_close_threshold,
                                        self._valve_transition_delay,
                                    )

                else:  # COOL mode
                    if zone_status == "overheated":
                        # Zone needs cooling - open valve
                        should_open = True
                    elif zone_status == "undercooled":
                        # Zone is too cold - close valve
                        should_open = False
                    else:  # satisfied
                        # In cooling mode, use similar logic as heating
                        if is_holding_mode:
                            should_open = True
                        elif desired_main_target is not None:
                            # Open valve only if zone target <= main target
                            should_open = zone_target <= desired_main_target
                        else:
                            should_open = False

                _LOGGER.debug(
                    "Zone %s: temp=%.1f°C, target=%.1f°C, range=[%.1f, %.1f]°C, status=%s, mode=%s, should_open=%s",
                    zone.get(CONF_ZONE_NAME, valve_entity),
                    current_temp,
                    zone_target,
                    lower_bound,
                    upper_bound,
                    zone_status,
                    "holding" if is_holding_mode else "heating",
                    should_open,
                )

                if should_open:
                    zones_needing_action.append(valve_entity)

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

            # Two-phase valve operation: open first, then close
            # Delay closing only when at minimum valve threshold to ensure safety

            # Cancel any pending delayed close task
            if self._delayed_valve_close_task and not self._delayed_valve_close_task.done():
                try:
                    self._delayed_valve_close_task.cancel()
                    _LOGGER.debug("Cancelled previous delayed valve close task")
                except Exception:
                    pass

            # Phase 1: Turn on valves that are currently off (immediate, non-blocking)
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

            # Phase 2: Close valves with delay only when necessary for safety
            valves_actually_turning_off = [v for v in valves_to_turn_off if current_valve_states.get(v)]
            if valves_actually_turning_off:
                # Count currently open valves (before opening new ones in Phase 1)
                # This determines if we need delay to ensure pump safety
                currently_open_count = sum(1 for v in current_valve_states.values() if v)

                # Delay closing only if:
                # 1. We're opening valves AND closing valves, AND
                # 2. We're at or near the minimum valve threshold
                # This ensures a valve is fully open before closing another for pump safety
                needs_delay = (
                    valves_actually_turning_on and
                    currently_open_count <= self._min_valves_open
                )

                if needs_delay:
                    # Delay the close for safety - ensure new valve is fully open first
                    _LOGGER.debug(
                        "Delaying valve close (at minimum threshold: %d open, min=%d)",
                        currently_open_count,
                        self._min_valves_open
                    )
                    self._delayed_valve_close_task = self.hass.async_create_task(
                        self._async_delayed_valve_close(valves_actually_turning_off)
                    )
                else:
                    # Close immediately - enough valves open for safety
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

                    if valves_actually_turning_on:
                        reason = f"sufficient valves open ({currently_open_count} > min {self._min_valves_open})"
                    else:
                        reason = "no valves being opened"

                    _LOGGER.debug(
                        "Phase 2: Turning OFF %d valves immediately (%s): %s",
                        len(valves_actually_turning_off),
                        reason,
                        valves_actually_turning_off
                    )
                    await asyncio.gather(*tasks, return_exceptions=True)

    def _get_zone_temperature(self, zone: dict[str, Any]) -> float | None:
        """Get current temperature from zone climate entity or sensor.

        Args:
            zone: Zone configuration dict

        Returns:
            Current temperature or None if unavailable
        """
        # Try zone climate entity first
        if zone.get(CONF_ZONE_CLIMATE):
            climate_state = self.hass.states.get(zone[CONF_ZONE_CLIMATE])
            if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                temp_attr = climate_state.attributes.get("current_temperature")
                if temp_attr is not None:
                    try:
                        return float(temp_attr)
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Unable to parse current temperature from climate %s",
                            zone[CONF_ZONE_CLIMATE],
                        )

        # Fall back to temperature sensor
        if zone.get(CONF_TEMPERATURE_SENSOR):
            sensor_state = self.hass.states.get(zone[CONF_TEMPERATURE_SENSOR])
            if sensor_state and sensor_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    return float(sensor_state.state)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Unable to parse temperature from sensor %s",
                        zone[CONF_TEMPERATURE_SENSOR],
                    )

        return None

    def _get_zone_target_temperature(self, zone: dict[str, Any]) -> float:
        """Get target temperature from zone climate entity or use default.

        Args:
            zone: Zone configuration dict

        Returns:
            Target temperature (from zone climate or multizone heater default)
        """
        # Try to get from zone climate entity
        if zone.get(CONF_ZONE_CLIMATE):
            climate_state = self.hass.states.get(zone[CONF_ZONE_CLIMATE])
            if climate_state and climate_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                target_attr = climate_state.attributes.get("temperature")
                if target_attr is not None:
                    try:
                        return float(target_attr)
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Unable to parse target temperature from climate %s, using default",
                            zone[CONF_ZONE_CLIMATE],
                        )

        # Fall back to multizone heater target
        return self._target_temperature

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

    async def _async_delayed_valve_close(self, valves_to_close: list[str]) -> None:
        """Close valves after transition delay (non-blocking).

        Args:
            valves_to_close: List of valve entity IDs to close after delay
        """
        try:
            _LOGGER.debug("Waiting %ds for valve transition before closing %d valves",
                         self._valve_transition_delay, len(valves_to_close))
            await asyncio.sleep(self._valve_transition_delay)

            # Close the valves
            tasks = []
            for valve_entity in valves_to_close:
                domain = valve_entity.split('.')[0] if '.' in valve_entity else 'switch'
                tasks.append(
                    self._async_call_service_with_error_handling(
                        domain,
                        SERVICE_TURN_OFF,
                        {"entity_id": valve_entity},
                        f"turn off valve {valve_entity}",
                    )
                )

            _LOGGER.debug("Phase 2 (delayed): Turning OFF %d valves: %s", len(valves_to_close), valves_to_close)
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            _LOGGER.debug("Delayed valve close task cancelled")
            raise
        except Exception as err:
            _LOGGER.error("Error in delayed valve close: %s", err, exc_info=True)
        finally:
            self._delayed_valve_close_task = None

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

    async def _async_close_valves_except_fallback(self) -> None:
        """Close all valves except fallback zones.

        This is called when the main climate HVAC mode is OFF.
        We keep fallback zones open to maintain pump safety.
        """
        async with self._update_lock:
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
                                f"turn off valve {valve_entity} (main climate is OFF)",
                            )
                        )

            # Execute all valve changes in parallel
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                _LOGGER.info(
                    "Main climate OFF: Closed %d non-fallback valve(s), keeping %d fallback valve(s) open",
                    len(tasks),
                    len(fallback_valve_entities)
                )
