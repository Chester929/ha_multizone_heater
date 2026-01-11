"""Config flow for Multizone Heater integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

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
    DEFAULT_MAIN_CHANGE_THRESHOLD,
    DEFAULT_MAIN_MAX_TEMP,
    DEFAULT_MAIN_MIN_TEMP,
    DEFAULT_MIN_VALVES_OPEN,
    DEFAULT_PHYSICAL_CLOSE_ANTICIPATION,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TARGET_TEMP_OFFSET_CLOSING,
    DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT,
    DEFAULT_VALVE_TRANSITION_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class MultizoneHeaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multizone Heater."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._zones = []
        self._main_climate = None
        self._main_temp_sensor = None
        self._temperature_aggregation_weight = DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
        self._min_valves_open = DEFAULT_MIN_VALVES_OPEN
        self._fallback_zones = []
        self._compensation_factor = DEFAULT_COMPENSATION_FACTOR
        self._valve_transition_delay = DEFAULT_VALVE_TRANSITION_DELAY
        self._main_min_temp = DEFAULT_MAIN_MIN_TEMP
        self._main_max_temp = DEFAULT_MAIN_MAX_TEMP
        self._main_change_threshold = DEFAULT_MAIN_CHANGE_THRESHOLD
        self._physical_close_anticipation = DEFAULT_PHYSICAL_CLOSE_ANTICIPATION
        self._all_satisfied_mode = DEFAULT_ALL_SATISFIED_MODE

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._main_climate = user_input.get(CONF_MAIN_CLIMATE)
            self._main_temp_sensor = user_input.get(CONF_MAIN_TEMP_SENSOR)
            self._temperature_aggregation_weight = user_input.get(
                CONF_TEMPERATURE_AGGREGATION_WEIGHT, DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
            )
            self._min_valves_open = user_input.get(
                CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN
            )
            self._compensation_factor = user_input.get(
                CONF_COMPENSATION_FACTOR, DEFAULT_COMPENSATION_FACTOR
            )
            self._valve_transition_delay = user_input.get(
                CONF_VALVE_TRANSITION_DELAY, DEFAULT_VALVE_TRANSITION_DELAY
            )
            self._main_min_temp = user_input.get(
                CONF_MAIN_MIN_TEMP, DEFAULT_MAIN_MIN_TEMP
            )
            self._main_max_temp = user_input.get(
                CONF_MAIN_MAX_TEMP, DEFAULT_MAIN_MAX_TEMP
            )
            
            # Validate main_min_temp < main_max_temp
            if self._main_min_temp >= self._main_max_temp:
                errors["base"] = "invalid_temp_range"
                # Don't process further if validation fails
            else:
                self._main_change_threshold = user_input.get(
                    CONF_MAIN_CHANGE_THRESHOLD, DEFAULT_MAIN_CHANGE_THRESHOLD
                )
                self._physical_close_anticipation = user_input.get(
                    CONF_PHYSICAL_CLOSE_ANTICIPATION, DEFAULT_PHYSICAL_CLOSE_ANTICIPATION
                )
                self._all_satisfied_mode = user_input.get(
                    CONF_ALL_SATISFIED_MODE, DEFAULT_ALL_SATISFIED_MODE
                )

                if not errors:
                    return await self.async_step_add_zone()

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_MAIN_CLIMATE): EntitySelector(
                    EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(CONF_MAIN_TEMP_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_TEMPERATURE_AGGREGATION_WEIGHT, default=DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=100, step=1, mode=NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_MIN_VALVES_OPEN, default=DEFAULT_MIN_VALVES_OPEN
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=10, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_COMPENSATION_FACTOR, default=DEFAULT_COMPENSATION_FACTOR
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0, max=1.0, step=0.01, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_VALVE_TRANSITION_DELAY, default=DEFAULT_VALVE_TRANSITION_DELAY
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=300, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAIN_MIN_TEMP, default=DEFAULT_MAIN_MIN_TEMP
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5.0, max=25.0, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAIN_MAX_TEMP, default=DEFAULT_MAIN_MAX_TEMP
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=20.0, max=40.0, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAIN_CHANGE_THRESHOLD, default=DEFAULT_MAIN_CHANGE_THRESHOLD
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0, max=1.0, step=0.05, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_PHYSICAL_CLOSE_ANTICIPATION, default=DEFAULT_PHYSICAL_CLOSE_ANTICIPATION
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0, max=2.0, step=0.1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_ALL_SATISFIED_MODE, default=DEFAULT_ALL_SATISFIED_MODE
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=100, step=1, mode=NumberSelectorMode.SLIDER
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle adding a zone."""
        errors = {}

        if user_input is not None:
            # Validate zone configuration
            zone_climate = user_input.get(CONF_ZONE_CLIMATE)
            temp_sensor = user_input.get(CONF_TEMPERATURE_SENSOR)
            valve_switch = user_input.get(CONF_VALVE_SWITCH)
            virtual_switch = user_input.get(CONF_VIRTUAL_SWITCH)

            # Validate that at least one temperature source is provided
            if not zone_climate and not temp_sensor:
                errors[CONF_ZONE_CLIMATE] = "need_temp_source"
                errors[CONF_TEMPERATURE_SENSOR] = "need_temp_source"

            # Validate that both valve and virtual switch are provided together
            if valve_switch and not virtual_switch:
                errors[CONF_VIRTUAL_SWITCH] = "need_virtual_switch"
            elif virtual_switch and not valve_switch:
                errors[CONF_VALVE_SWITCH] = "need_physical_valve"

            # Check for duplicate entities across all zones
            if not errors:
                all_entities = []
                for zone in self._zones:
                    if zone.get(CONF_ZONE_CLIMATE):
                        all_entities.append(zone[CONF_ZONE_CLIMATE])
                    if zone.get(CONF_TEMPERATURE_SENSOR):
                        all_entities.append(zone[CONF_TEMPERATURE_SENSOR])
                    if zone.get(CONF_VALVE_SWITCH):
                        all_entities.append(zone[CONF_VALVE_SWITCH])
                    if zone.get(CONF_VIRTUAL_SWITCH):
                        all_entities.append(zone[CONF_VIRTUAL_SWITCH])

                # Check for duplicates in current input
                if zone_climate and zone_climate in all_entities:
                    errors[CONF_ZONE_CLIMATE] = "duplicate_entity"
                if temp_sensor and temp_sensor in all_entities:
                    errors[CONF_TEMPERATURE_SENSOR] = "duplicate_entity"
                if valve_switch and valve_switch in all_entities:
                    errors[CONF_VALVE_SWITCH] = "duplicate_entity"
                if virtual_switch and virtual_switch in all_entities:
                    errors[CONF_VIRTUAL_SWITCH] = "duplicate_entity"

            if not errors:
                if user_input.get("add_another"):
                    # Add the zone
                    zone_data = {
                        CONF_ZONE_NAME: user_input[CONF_ZONE_NAME],
                        CONF_ZONE_CLIMATE: zone_climate,
                        CONF_TEMPERATURE_SENSOR: temp_sensor,
                        CONF_VALVE_SWITCH: valve_switch,
                        CONF_VIRTUAL_SWITCH: virtual_switch,
                        CONF_TARGET_TEMP_OFFSET: user_input.get(
                            CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET
                        ),
                        CONF_TARGET_TEMP_OFFSET_CLOSING: user_input.get(
                            CONF_TARGET_TEMP_OFFSET_CLOSING, DEFAULT_TARGET_TEMP_OFFSET_CLOSING
                        ),
                    }
                    self._zones.append(zone_data)

                    # Return to add another zone
                    return await self.async_step_add_zone()
                else:
                    # Check if we need to add the current zone
                    if user_input.get(CONF_ZONE_NAME):
                        zone_data = {
                            CONF_ZONE_NAME: user_input[CONF_ZONE_NAME],
                            CONF_ZONE_CLIMATE: zone_climate,
                            CONF_TEMPERATURE_SENSOR: temp_sensor,
                            CONF_VALVE_SWITCH: valve_switch,
                            CONF_VIRTUAL_SWITCH: virtual_switch,
                            CONF_TARGET_TEMP_OFFSET: user_input.get(
                                CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET
                            ),
                            CONF_TARGET_TEMP_OFFSET_CLOSING: user_input.get(
                                CONF_TARGET_TEMP_OFFSET_CLOSING, DEFAULT_TARGET_TEMP_OFFSET_CLOSING
                            ),
                        }
                        self._zones.append(zone_data)

                    # Validate that at least one zone was added
                    if not self._zones:
                        errors["base"] = "no_zones"
                        return self.async_show_form(
                            step_id="add_zone",
                            data_schema=self._get_zone_schema(),
                            errors=errors,
                        )

                    # Move to fallback zone selection
                    return await self.async_step_fallback_zones()

        return self.async_show_form(
            step_id="add_zone",
            data_schema=self._get_zone_schema(),
            errors=errors,
        )

    async def async_step_fallback_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle selecting fallback zones."""
        errors = {}

        if user_input is not None:
            fallback_zones = user_input.get(CONF_FALLBACK_ZONES, [])
            
            # Validate at least one fallback zone is selected
            if not fallback_zones:
                errors[CONF_FALLBACK_ZONES] = "need_fallback"
            else:
                self._fallback_zones = fallback_zones
                
                # Create the config entry
                return self.async_create_entry(
                    title=f"Multizone Heater ({len(self._zones)} zones)",
                    data={
                        CONF_MAIN_CLIMATE: self._main_climate,
                        CONF_MAIN_TEMP_SENSOR: self._main_temp_sensor,
                        CONF_TEMPERATURE_AGGREGATION_WEIGHT: self._temperature_aggregation_weight,
                        CONF_MIN_VALVES_OPEN: self._min_valves_open,
                        CONF_FALLBACK_ZONES: self._fallback_zones,
                        CONF_ZONES: self._zones,
                        CONF_COMPENSATION_FACTOR: self._compensation_factor,
                        CONF_VALVE_TRANSITION_DELAY: self._valve_transition_delay,
                        CONF_MAIN_MIN_TEMP: self._main_min_temp,
                        CONF_MAIN_MAX_TEMP: self._main_max_temp,
                        CONF_MAIN_CHANGE_THRESHOLD: self._main_change_threshold,
                        CONF_PHYSICAL_CLOSE_ANTICIPATION: self._physical_close_anticipation,
                        CONF_ALL_SATISFIED_MODE: self._all_satisfied_mode,
                    },
                )

        # Build list of zone names for selection
        zone_options = [zone[CONF_ZONE_NAME] for zone in self._zones]

        data_schema = vol.Schema(
            {
                vol.Required(CONF_FALLBACK_ZONES): SelectSelector(
                    SelectSelectorConfig(
                        options=zone_options,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="fallback_zones",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Select at least one zone to keep open when all zones are satisfied or during cooling mode. This ensures pump safety."
            },
        )

    def _get_zone_schema(self):
        """Get the schema for adding a zone."""
        return vol.Schema(
            {
                vol.Required(CONF_ZONE_NAME): str,
                vol.Optional(CONF_ZONE_CLIMATE): EntitySelector(
                    EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(CONF_TEMPERATURE_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_VALVE_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Optional(CONF_VIRTUAL_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Optional(
                    CONF_TARGET_TEMP_OFFSET, default=DEFAULT_TARGET_TEMP_OFFSET
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=5, step=0.1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_TARGET_TEMP_OFFSET_CLOSING, default=DEFAULT_TARGET_TEMP_OFFSET_CLOSING
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=5, step=0.1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required("add_another", default=False): bool,
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Multizone Heater."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            # Validate main_min_temp < main_max_temp
            main_min = user_input.get(CONF_MAIN_MIN_TEMP, DEFAULT_MAIN_MIN_TEMP)
            main_max = user_input.get(CONF_MAIN_MAX_TEMP, DEFAULT_MAIN_MAX_TEMP)
            
            if main_min >= main_max:
                errors["base"] = "invalid_temp_range"
            
            if not errors:
                # Update the config entry
                return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TEMPERATURE_AGGREGATION_WEIGHT,
                    default=self.config_entry.data.get(
                        CONF_TEMPERATURE_AGGREGATION_WEIGHT, DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=100, step=1, mode=NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    CONF_MIN_VALVES_OPEN,
                    default=self.config_entry.data.get(
                        CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=10, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_COMPENSATION_FACTOR,
                    default=self.config_entry.data.get(
                        CONF_COMPENSATION_FACTOR, DEFAULT_COMPENSATION_FACTOR
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0, max=1.0, step=0.01, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_VALVE_TRANSITION_DELAY,
                    default=self.config_entry.data.get(
                        CONF_VALVE_TRANSITION_DELAY, DEFAULT_VALVE_TRANSITION_DELAY
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=300, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAIN_MIN_TEMP,
                    default=self.config_entry.data.get(
                        CONF_MAIN_MIN_TEMP, DEFAULT_MAIN_MIN_TEMP
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5.0, max=25.0, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAIN_MAX_TEMP,
                    default=self.config_entry.data.get(
                        CONF_MAIN_MAX_TEMP, DEFAULT_MAIN_MAX_TEMP
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=20.0, max=40.0, step=0.5, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_MAIN_CHANGE_THRESHOLD,
                    default=self.config_entry.data.get(
                        CONF_MAIN_CHANGE_THRESHOLD, DEFAULT_MAIN_CHANGE_THRESHOLD
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0, max=1.0, step=0.05, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_PHYSICAL_CLOSE_ANTICIPATION,
                    default=self.config_entry.data.get(
                        CONF_PHYSICAL_CLOSE_ANTICIPATION, DEFAULT_PHYSICAL_CLOSE_ANTICIPATION
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0, max=2.0, step=0.1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_ALL_SATISFIED_MODE,
                    default=self.config_entry.data.get(
                        CONF_ALL_SATISFIED_MODE, DEFAULT_ALL_SATISFIED_MODE
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=100, step=1, mode=NumberSelectorMode.SLIDER
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
