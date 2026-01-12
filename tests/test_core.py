"""Unit tests for core computation logic."""
import sys
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "multizone_heater"))

import pytest

from core import (
    ZoneData,
    compute_main_target,
    compute_zone_targets,
)


class TestComputeMainTarget:
    """Tests for compute_main_target function."""

    def test_heating_mode_zones_needing_heat(self):
        """Test heating mode when zones need heat."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=18.0,
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=19.0,
                target_temp=22.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=50,
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        # Zone1 needs +2°C, Zone2 needs +3°C
        # Zone1 target: 20 + 0.66 * 2 = 21.32
        # Zone2 target: 22 + 0.66 * 3 = 23.98
        # Should take max
        assert target is not None
        assert abs(target - 24.0) < 0.1  # Rounded
        assert is_holding is False

    def test_holding_mode_all_zones_satisfied(self):
        """Test holding mode when all zones are satisfied."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.0,
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=22.0,
                target_temp=22.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        # Test at 50% (average)
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=50,
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        # Should interpolate: at 50%, should be average of 20 and 22 = 21
        assert target == 21.0
        assert is_holding is True

    def test_holding_mode_min_slider(self):
        """Test holding mode with slider at 0% (min)."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.0,
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=25.0,
                target_temp=25.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=0,  # Min
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        # Should be minimum target
        assert target == 20.0
        assert is_holding is True

    def test_holding_mode_max_slider(self):
        """Test holding mode with slider at 100% (max)."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.0,
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=25.0,
                target_temp=25.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=100,  # Max
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        # Should be maximum target
        assert target == 25.0
        assert is_holding is True

    def test_cooling_mode_zones_needing_cooling(self):
        """Test cooling mode when zones need cooling."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=26.0,
                target_temp=24.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=28.0,
                target_temp=25.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="cool",
            compensation_factor=0.66,
            all_satisfied_mode=50,
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        # Zone1 surplus: 26 - 24 = 2, target: 24 - 0.66*2 = 22.68
        # Zone2 surplus: 28 - 25 = 3, target: 25 - 0.66*3 = 23.02
        # Should take min in cooling mode
        assert target is not None
        assert abs(target - 22.7) < 0.1
        assert is_holding is False

    def test_clamping_to_min_max(self):
        """Test that target is clamped to min/max range."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=10.0,
                target_temp=15.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        target, _ = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=1.0,  # Higher factor to exceed max
            all_satisfied_mode=50,
            main_min_temp=18.0,
            main_max_temp=20.0,  # Lower max to trigger clamping
        )
        
        # Computed would be 15 + 1.0*5 = 20.0, exactly at max
        assert target == 20.0

    def test_no_zones_with_temperature(self):
        """Test when no zones have temperature data."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=None,
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=50,
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        assert target is None
        assert is_holding is False


class TestComputeZoneTargets:
    """Tests for compute_zone_targets function."""

    def test_heating_mode_bounds(self):
        """Test satisfaction bounds in heating mode."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.0,
                target_temp=21.0,
                target_offset=0.5,
                target_offset_closing=0.3,
                is_valve_open=True,
            ),
        ]
        
        result = compute_zone_targets(zones, "heat")
        
        assert "Zone1" in result
        assert result["Zone1"]["target"] == 21.0
        # Heating: [target - opening_offset, target + closing_offset]
        assert result["Zone1"]["lower_bound"] == 20.5  # 21 - 0.5
        assert result["Zone1"]["upper_bound"] == 21.3  # 21 + 0.3

    def test_cooling_mode_bounds(self):
        """Test satisfaction bounds in cooling mode."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=22.0,
                target_temp=23.0,
                target_offset=0.5,
                target_offset_closing=0.3,
                is_valve_open=True,
            ),
        ]
        
        result = compute_zone_targets(zones, "cool")
        
        assert "Zone1" in result
        assert result["Zone1"]["target"] == 23.0
        # Cooling: [target - closing_offset, target + opening_offset]
        assert result["Zone1"]["lower_bound"] == 22.7  # 23 - 0.3
        assert result["Zone1"]["upper_bound"] == 23.5  # 23 + 0.5

    def test_multiple_zones(self):
        """Test with multiple zones."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.0,
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=22.0,
                target_temp=22.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        result = compute_zone_targets(zones, "heat")
        
        assert len(result) == 2
        assert "Zone1" in result
        assert "Zone2" in result
        assert result["Zone1"]["target"] == 20.0
        assert result["Zone2"]["target"] == 22.0
