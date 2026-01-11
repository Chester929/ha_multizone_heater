"""Constants for the Multizone Heater integration."""

DOMAIN = "multizone_heater"

# Configuration keys
CONF_ZONES = "zones"
CONF_ZONE_NAME = "zone_name"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_VALVE_SWITCH = "valve_switch"
CONF_TARGET_TEMP_OFFSET = "target_temp_offset"
CONF_TARGET_TEMP_OFFSET_CLOSING = "target_temp_offset_closing"
CONF_MAIN_CLIMATE = "main_climate"
CONF_TEMPERATURE_AGGREGATION = "temperature_aggregation"
CONF_TEMPERATURE_AGGREGATION_WEIGHT = "temperature_aggregation_weight"
CONF_MIN_VALVES_OPEN = "min_valves_open"

# Defaults
DEFAULT_TARGET_TEMP_OFFSET = 0.5
DEFAULT_TARGET_TEMP_OFFSET_CLOSING = 0.0
DEFAULT_TEMPERATURE_AGGREGATION = "average"
DEFAULT_TEMPERATURE_AGGREGATION_WEIGHT = 50  # 0-100%, where 0=min, 50=avg, 100=max
DEFAULT_MIN_VALVES_OPEN = 1
DEFAULT_HVAC_ACTION_DEADBAND = 0.5  # Temperature deadband for HVAC action determination

# Temperature aggregation methods
TEMP_AGG_AVERAGE = "average"
TEMP_AGG_MIN = "minimum"
TEMP_AGG_MAX = "maximum"

TEMPERATURE_AGGREGATION_OPTIONS = [
    TEMP_AGG_AVERAGE,
    TEMP_AGG_MIN,
    TEMP_AGG_MAX,
]
