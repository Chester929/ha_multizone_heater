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
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
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
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_MAIN_CLIMATE,
    CONF_MIN_VALVES_OPEN,
    CONF_TARGET_TEMP_OFFSET,
    CONF_TEMPERATURE_AGGREGATION,
    CONF_TEMPERATURE_SENSOR,
    CONF_VALVE_SWITCH,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DEFAULT_HVAC_ACTION_DEADBAND,
    DEFAULT_MIN_VALVES_OPEN,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TEMPERATURE_AGGREGATION,
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
    min_valves_open = config.get(CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN)

    entities = [
        MultizoneHeaterClimate(
            hass,
            config_entry,
            zones,
            main_climate,
            temperature_aggregation,
            min_valves_open,
        )
    ]

    async_add_entities(entities)


class MultizoneHeaterClimate(ClimateEntity):
    """Representation of a Multizone Heater climate device."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        zones: list[dict[str, Any]],
        main_climate: str | None,
        temperature_aggregation: str,
        min_valves_open: int,
    ) -> None:
        """Initialize the multizone heater."""
        self.hass = hass
        self._config_entry = config_entry
        self._zones = zones
        self._main_climate_entity = main_climate
        self._temperature_aggregation = temperature_aggregation
        self._min_valves_open = min_valves_open

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
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

        self._update_lock = asyncio.Lock()
        self._last_valve_states = {}

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Track all temperature sensors
        sensor_entities = [zone[CONF_TEMPERATURE_SENSOR] for zone in self._zones]
        
        @callback
        def async_sensor_changed(event):
            """Handle temperature sensor changes."""
            self.async_schedule_update_ha_state(True)

        for sensor in sensor_entities:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, sensor, async_sensor_changed
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
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self._main_climate_entity,
                    ATTR_TEMPERATURE: temperature,
                },
                blocking=True,
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
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {
                        "entity_id": self._main_climate_entity,
                        "hvac_mode": HVACMode.OFF,
                    },
                    blocking=True,
                )
        elif hvac_mode == HVACMode.HEAT:
            # Turn on main climate if configured
            if self._main_climate_entity:
                await self.hass.services.async_call(
                    "climate",
                    "set_hvac_mode",
                    {
                        "entity_id": self._main_climate_entity,
                        "hvac_mode": HVACMode.HEAT,
                    },
                    blocking=True,
                )
            
            # Control valves based on zone temperatures
            await self._async_control_valves()

        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        # Calculate aggregated current temperature
        temperatures = []
        for zone in self._zones:
            sensor_entity = zone[CONF_TEMPERATURE_SENSOR]
            state = self.hass.states.get(sensor_entity)
            
            if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    temp = float(state.state)
                    temperatures.append(temp)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        "Unable to parse temperature from %s: %s",
                        sensor_entity,
                        state.state,
                    )

        if temperatures:
            if self._temperature_aggregation == TEMP_AGG_AVERAGE:
                self._current_temperature = sum(temperatures) / len(temperatures)
            elif self._temperature_aggregation == TEMP_AGG_MIN:
                self._current_temperature = min(temperatures)
            elif self._temperature_aggregation == TEMP_AGG_MAX:
                self._current_temperature = max(temperatures)
        else:
            self._current_temperature = None

        # Update HVAC action
        if self._hvac_mode == HVACMode.OFF:
            self._hvac_action = HVACAction.OFF
        elif self._current_temperature is not None and self._target_temperature is not None:
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

    async def _async_control_valves(self) -> None:
        """Control valve states based on zone temperatures."""
        async with self._update_lock:
            if self._hvac_mode != HVACMode.HEAT:
                return

            tasks = []
            zones_needing_heat = []

            for zone in self._zones:
                sensor_entity = zone[CONF_TEMPERATURE_SENSOR]
                valve_entity = zone[CONF_VALVE_SWITCH]
                target_offset = zone.get(CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET)

                state = self.hass.states.get(sensor_entity)
                
                if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                    try:
                        current_temp = float(state.state)
                        zone_target = self._target_temperature

                        # Determine if valve should be open
                        should_open = current_temp < (zone_target - target_offset)
                        
                        if should_open:
                            zones_needing_heat.append(valve_entity)

                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Unable to parse temperature from %s", sensor_entity
                        )

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
                    tasks.append(
                        self.hass.services.async_call(
                            "switch",
                            SERVICE_TURN_ON,
                            {"entity_id": valve_entity},
                            blocking=False,
                        )
                    )

            # Turn off valves asynchronously
            for valve_entity in valves_to_turn_off:
                if current_valve_states.get(valve_entity):
                    tasks.append(
                        self.hass.services.async_call(
                            "switch",
                            SERVICE_TURN_OFF,
                            {"entity_id": valve_entity},
                            blocking=False,
                        )
                    )

            # Execute all valve changes in parallel
            if tasks:
                await asyncio.gather(*tasks)

            # Update cached valve states
            self._last_valve_states = {
                valve: valve in valves_to_turn_on
                for valve in current_valve_states
            }

    async def _async_get_valve_states(self) -> dict[str, bool]:
        """Get current states of all valves."""
        valve_states = {}
        for zone in self._zones:
            valve_entity = zone[CONF_VALVE_SWITCH]
            state = self.hass.states.get(valve_entity)
            
            if state:
                valve_states[valve_entity] = state.state == STATE_ON
            else:
                valve_states[valve_entity] = False

        return valve_states

    async def _async_turn_off_all_valves(self) -> None:
        """Turn off all valves except minimum required."""
        async with self._update_lock:
            valve_entities = [zone[CONF_VALVE_SWITCH] for zone in self._zones]
            tasks = []

            # Determine which valves to keep open
            valves_to_keep_open = valve_entities[:self._min_valves_open]

            for valve_entity in valve_entities:
                if valve_entity not in valves_to_keep_open:
                    tasks.append(
                        self.hass.services.async_call(
                            "switch",
                            SERVICE_TURN_OFF,
                            {"entity_id": valve_entity},
                            blocking=False,
                        )
                    )

            if tasks:
                await asyncio.gather(*tasks)
