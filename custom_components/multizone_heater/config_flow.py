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
    CONF_MAIN_CLIMATE,
    CONF_MIN_VALVES_OPEN,
    CONF_TARGET_TEMP_OFFSET,
    CONF_TEMPERATURE_AGGREGATION,
    CONF_TEMPERATURE_SENSOR,
    CONF_VALVE_SWITCH,
    CONF_ZONE_NAME,
    CONF_ZONES,
    DEFAULT_MIN_VALVES_OPEN,
    DEFAULT_TARGET_TEMP_OFFSET,
    DEFAULT_TEMPERATURE_AGGREGATION,
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
        self._min_valves_open = DEFAULT_MIN_VALVES_OPEN

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
                    CONF_MIN_VALVES_OPEN, default=DEFAULT_MIN_VALVES_OPEN
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=10, mode=NumberSelectorMode.BOX
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
            if user_input.get("add_another"):
                # Add the zone
                zone_data = {
                    CONF_ZONE_NAME: user_input[CONF_ZONE_NAME],
                    CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                    CONF_VALVE_SWITCH: user_input[CONF_VALVE_SWITCH],
                    CONF_TARGET_TEMP_OFFSET: user_input.get(
                        CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET
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
                        CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                        CONF_VALVE_SWITCH: user_input[CONF_VALVE_SWITCH],
                        CONF_TARGET_TEMP_OFFSET: user_input.get(
                            CONF_TARGET_TEMP_OFFSET, DEFAULT_TARGET_TEMP_OFFSET
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

                # Create the config entry
                return self.async_create_entry(
                    title=f"Multizone Heater ({len(self._zones)} zones)",
                    data={
                        CONF_MAIN_CLIMATE: self._main_climate,
                        CONF_TEMPERATURE_AGGREGATION: self._temperature_aggregation,
                        CONF_MIN_VALVES_OPEN: self._min_valves_open,
                        CONF_ZONES: self._zones,
                    },
                )

        return self.async_show_form(
            step_id="add_zone",
            data_schema=self._get_zone_schema(),
            errors=errors,
        )

    def _get_zone_schema(self):
        """Get the schema for adding a zone."""
        return vol.Schema(
            {
                vol.Required(CONF_ZONE_NAME): str,
                vol.Required(CONF_TEMPERATURE_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_VALVE_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain="switch")
                ),
                vol.Optional(
                    CONF_TARGET_TEMP_OFFSET, default=DEFAULT_TARGET_TEMP_OFFSET
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
                    CONF_MIN_VALVES_OPEN,
                    default=self.config_entry.data.get(
                        CONF_MIN_VALVES_OPEN, DEFAULT_MIN_VALVES_OPEN
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=10, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
