"""Constants for the Multizone Heater integration."""

DOMAIN = "multizone_heater"

# Configuration keys
CONF_ZONES = "zones"
CONF_ZONE_NAME = "zone_name"
CONF_ZONE_CLIMATE = "zone_climate"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_VALVE_SWITCH = "valve_switch"
CONF_VIRTUAL_SWITCH = "virtual_switch"
CONF_TARGET_TEMP_OFFSET = "target_temp_offset"
CONF_TARGET_TEMP_OFFSET_CLOSING = "target_temp_offset_closing"
CONF_MAIN_CLIMATE = "main_climate"
CONF_MAIN_TEMP_SENSOR = "main_temp_sensor"
CONF_MIN_VALVES_OPEN = "min_valves_open"
CONF_FALLBACK_ZONES = "fallback_zones"
CONF_COMPENSATION_FACTOR = "compensation_factor"
CONF_VALVE_TRANSITION_DELAY = "valve_transition_delay"
CONF_MAIN_MIN_TEMP = "main_min_temp"
CONF_MAIN_MAX_TEMP = "main_max_temp"
CONF_MAIN_CHANGE_THRESHOLD = "main_change_threshold"
CONF_PHYSICAL_CLOSE_ANTICIPATION = "physical_close_anticipation"
CONF_ALL_SATISFIED_MODE = "all_satisfied_mode"

# Defaults
DEFAULT_TARGET_TEMP_OFFSET = 0.5
DEFAULT_TARGET_TEMP_OFFSET_CLOSING = 0.0
DEFAULT_MIN_VALVES_OPEN = 1
DEFAULT_HVAC_ACTION_DEADBAND = 0.5  # Temperature deadband for HVAC action determination
DEFAULT_COMPENSATION_FACTOR = 0.66  # Corridor compensation factor
DEFAULT_VALVE_TRANSITION_DELAY = 60  # Seconds to wait between valve operations
DEFAULT_MAIN_MIN_TEMP = 18.0  # Minimum main climate temperature
DEFAULT_MAIN_MAX_TEMP = 30.0  # Maximum main climate temperature
DEFAULT_MAIN_CHANGE_THRESHOLD = 0.1  # Minimum change to update main climate
DEFAULT_PHYSICAL_CLOSE_ANTICIPATION = 0.6  # Early close offset for physical valves
DEFAULT_ALL_SATISFIED_MODE = 50  # 0-100%, where 0=min, 50=avg, 100=max
DEFAULT_RECONCILIATION_INTERVAL = 5  # Seconds between periodic valve reconciliation checks
DEFAULT_ZONE_TARGET_CHANGE_DELAY = 5  # Seconds to wait after zone target change before updating main climate
