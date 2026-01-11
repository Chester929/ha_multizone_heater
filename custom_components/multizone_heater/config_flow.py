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
    DEFAULT_MIN_VALVES_OPEN,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TARGET_TEMP_OFFSET_CLOSING,
    DEFAULT_TEMPERATURE_AGGREGATION,
    DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT,
    DOMAIN,
    TEMPERATURE_AGGREGATION_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class MultizoneHeaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multizone Heater."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._zones = []
        self._main_climate = None
        self._temperature_aggregation = DEFAULT_TEMPERATURE_AGGREGATION
        self._temperature_aggregation_weight = DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
        self._min_valves_open = DEFAULT_MIN_VALVES_OPEN
        self._fallback_zones = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._main_climate = user_input.get(CONF_MAIN_CLIMATE)
            self._temperature_aggregation = user_input.get(
                CONF_TEMPERATURE_AGGREGATION, DEFAULT_TEMPERATURE_AGGREGATION
            )
            self._temperature_aggregation_weight = user_input.get(
                CONF_TEMPERATURE_AGGREGATION_WEIGHT, DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT
            )
            self._min_valves_open = user_input.get(
                CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN
            )

            return await self.async_step_add_zone()

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_MAIN_CLIMATE): EntitySelector(
                    EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(
                    CONF_TEMPERATURE_AGGREGATION, default=DEFAULT_TEMPERATURE_AGGREGATION
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=TEMPERATURE_AGGREGATION_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
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
                        CONF_TEMPERATURE_AGGREGATION: self._temperature_aggregation,
                        CONF_TEMPERATURE_AGGREGATION_WEIGHT: self._temperature_aggregation_weight,
                        CONF_MIN_VALVES_OPEN: self._min_valves_open,
                        CONF_FALLBACK_ZONES: self._fallback_zones,
                        CONF_ZONES: self._zones,
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
            # Update the config entry
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_TEMPERATURE_AGGREGATION,
                    default=self.config_entry.data.get(
                        CONF_TEMPERATURE_AGGREGATION, DEFAULT_TEMPERATURE_AGGREGATION
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=TEMPERATURE_AGGREGATION_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
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
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
