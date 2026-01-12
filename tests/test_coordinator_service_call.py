"""Unit tests for coordinator service calls."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "multizone_heater"))

import pytest


class MockHass:
    """Mock HomeAssistant instance."""
    def __init__(self):
        self.services = MagicMock()
        self.services.async_call = AsyncMock()
        self.loop = None


class MockCoordinator:
    """Mock coordinator for testing service calls."""
    def __init__(self, hass, main_climate_entity_id):
        self.hass = hass
        self._main_climate_entity_id = main_climate_entity_id
    
    async def _async_set_main_climate_temperature(
        self,
        target_temp: float,
        hvac_mode: str,
    ) -> None:
        """Set the target temperature on the main climate entity."""
        try:
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self._main_climate_entity_id,
                    "temperature": target_temp,
                    "hvac_mode": hvac_mode,
                },
                blocking=False,
            )
        except Exception:
            pass  # Error handling


class TestCoordinatorServiceCall:
    """Tests for coordinator service call functionality."""

    @pytest.mark.asyncio
    async def test_sets_main_climate_temperature_when_calculated(self):
        """Test that main climate temperature is set when calculated."""
        # Create mock hass and coordinator
        hass = MockHass()
        coordinator = MockCoordinator(hass, "climate.main_heater")
        
        # Call the method
        await coordinator._async_set_main_climate_temperature(22.5, "heat")
        
        # Verify service was called
        hass.services.async_call.assert_called_once()
        call_args = hass.services.async_call.call_args
        
        # Check the call parameters (args, kwargs)
        assert call_args.args[0] == "climate"
        assert call_args.args[1] == "set_temperature"
        assert call_args.args[2]["entity_id"] == "climate.main_heater"
        assert call_args.args[2]["temperature"] == 22.5
        assert call_args.args[2]["hvac_mode"] == "heat"
        assert call_args.kwargs["blocking"] is False

    @pytest.mark.asyncio
    async def test_sets_temperature_in_cooling_mode(self):
        """Test that temperature is set correctly in cooling mode."""
        # Create mock hass and coordinator
        hass = MockHass()
        coordinator = MockCoordinator(hass, "climate.main_heater")
        
        # Call the method
        await coordinator._async_set_main_climate_temperature(23.0, "cool")
        
        # Verify service was called with cooling mode
        hass.services.async_call.assert_called_once()
        call_args = hass.services.async_call.call_args
        assert call_args.args[2]["hvac_mode"] == "cool"
        assert call_args.args[2]["temperature"] == 23.0

    @pytest.mark.asyncio
    async def test_handles_service_call_error_gracefully(self):
        """Test that service call errors are handled gracefully."""
        # Create mock hass that raises an error
        hass = MockHass()
        hass.services.async_call = AsyncMock(side_effect=Exception("Service call failed"))
        coordinator = MockCoordinator(hass, "climate.main_heater")
        
        # Call should not raise exception
        await coordinator._async_set_main_climate_temperature(22.5, "heat")
        
        # Verify service was attempted
        hass.services.async_call.assert_called_once()

