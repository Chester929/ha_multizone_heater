"""DataUpdateCoordinator for multizone heater."""
from datetime import timedelta
import logging
from typing import Any, Callable, Awaitable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .core import ZoneData, compute_main_target, compute_zone_targets

_LOGGER = logging.getLogger(__name__)


class MultizoneCoordinator(DataUpdateCoordinator):
    """Coordinator to manage multizone heater data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        update_interval: int,
        external_target_getter: Callable[[], Awaitable[float | None]],
        zone_sensor_getter: Callable[[], Awaitable[list[ZoneData]]],
        hvac_mode_getter: Callable[[], Awaitable[str]],
        compensation_factor: float,
        all_satisfied_mode: int,
        main_min_temp: float,
        main_max_temp: float,
    ) -> None:
        """Initialize the coordinator.
        
        Args:
            hass: Home Assistant instance
            update_interval: Update interval in seconds
            external_target_getter: Async callable to get external main climate target
            zone_sensor_getter: Async callable to get zone sensor data
            hvac_mode_getter: Async callable to get current HVAC mode
            compensation_factor: Compensation factor for target calculation
            all_satisfied_mode: Slider value for holding mode (0-100)
            main_min_temp: Minimum main climate temperature
            main_max_temp: Maximum main climate temperature
        """
        super().__init__(
            hass,
            _LOGGER,
            name="Multizone Heater",
            update_interval=timedelta(seconds=update_interval),
        )
        self._external_target_getter = external_target_getter
        self._zone_sensor_getter = zone_sensor_getter
        self._hvac_mode_getter = hvac_mode_getter
        self._compensation_factor = compensation_factor
        self._all_satisfied_mode = all_satisfied_mode
        self._main_min_temp = main_min_temp
        self._main_max_temp = main_max_temp

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from sensors and compute targets.
        
        Returns:
            Dictionary with computed data:
            - main_target: Computed main climate target temperature
            - is_holding_mode: Whether in holding mode (all zones satisfied)
            - zone_targets: Dictionary of per-zone target info
            - zone_states: Dictionary of per-zone state info (current_temp, valve_state)
            - hvac_mode: Current HVAC mode
        
        Raises:
            UpdateFailed: If sensor reads fail
        """
        try:
            # Get current HVAC mode
            hvac_mode = await self._hvac_mode_getter()
            if hvac_mode not in ("heat", "cool"):
                # If mode is off or invalid, return minimal data
                return {
                    "main_target": None,
                    "is_holding_mode": False,
                    "zone_targets": {},
                    "zone_states": {},
                    "hvac_mode": hvac_mode,
                }
            
            # Get zone data
            zones = await self._zone_sensor_getter()
            if not zones:
                _LOGGER.warning("No zone data available")
                return {
                    "main_target": None,
                    "is_holding_mode": False,
                    "zone_targets": {},
                    "zone_states": {},
                    "hvac_mode": hvac_mode,
                }
            
            # Compute main target using core logic
            main_target, is_holding_mode = compute_main_target(
                zones=zones,
                hvac_mode=hvac_mode,
                compensation_factor=self._compensation_factor,
                all_satisfied_mode=self._all_satisfied_mode,
                main_min_temp=self._main_min_temp,
                main_max_temp=self._main_max_temp,
            )
            
            # Compute zone targets
            zone_targets = compute_zone_targets(
                zones=zones,
                hvac_mode=hvac_mode,
            )
            
            # Build zone states for sensor exposure
            zone_states = {}
            for zone in zones:
                zone_states[zone.name] = {
                    "current_temp": zone.current_temp,
                    "target_temp": zone.target_temp,
                    "is_valve_open": zone.is_valve_open,
                    "target_offset": zone.target_offset,
                    "target_offset_closing": zone.target_offset_closing,
                }
            
            _LOGGER.debug(
                "Updated data: main_target=%.1f°C, is_holding=%s, zones=%d",
                main_target if main_target is not None else 0.0,
                is_holding_mode,
                len(zone_targets),
            )
            
            return {
                "main_target": main_target,
                "is_holding_mode": is_holding_mode,
                "zone_targets": zone_targets,
                "zone_states": zone_states,
                "hvac_mode": hvac_mode,
            }
            
        except Exception as err:
            _LOGGER.error("Error updating multizone heater data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error communicating with sensors: {err}") from err
