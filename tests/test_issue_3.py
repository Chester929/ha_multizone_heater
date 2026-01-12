"""Test to reproduce Issue #3 - incorrect main target calculation."""
import sys
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "multizone_heater"))

import pytest

from core import (
    ZoneData,
    compute_main_target,
)


class TestIssue3Reproduction:
    """Tests to reproduce Issue #3 from problem statement."""

    def test_three_zones_satisfied_50_percent_slider(self):
        """Test with 3 zones satisfied, lowest 20°C, highest 22.5°C.
        
        Problem statement: "I have 3 zones satisfied, the lowest target is 20 
        and the highest target is 22.5. And main target temperature sensor shows 19.5 ... 
        however it should be 50 percent between low and high (mean average target) 
        so it definitely cannot be 19.5"
        
        Expected: At 50% slider, should show average of all zone targets.
        With targets [20.0, 21.25, 22.5], average = 21.25°C
        """
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.0,  # Satisfied
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=21.25,  # Satisfied
                target_temp=21.25,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone3",
                current_temp=22.5,  # Satisfied
                target_temp=22.5,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        # Test with 50% slider (should give average)
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=50,
            main_min_temp=18.0,
            main_max_temp=30.0,
        )
        
        # Should be in holding mode since all zones are satisfied
        assert is_holding is True, "Should be in holding mode when all zones satisfied"
        
        # Calculate expected average
        expected_avg = (20.0 + 21.25 + 22.5) / 3.0
        assert target is not None, "Target should not be None"
        
        # Should be very close to average (allowing for rounding)
        assert abs(target - expected_avg) < 0.1, f"Target {target}°C should be close to average {expected_avg}°C"
        
        # Definitely should NOT be 19.5
        assert target >= 20.0, f"Target {target}°C should be at least the minimum target 20.0°C"

    def test_three_zones_with_19_5_min_temp(self):
        """Test if 19.5°C could come from min_temp clamping."""
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
                current_temp=22.5,
                target_temp=22.5,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
        ]
        
        # If min_temp is set to 19.5, calculation should still work correctly
        target, is_holding = compute_main_target(
            zones=zones,
            hvac_mode="heat",
            compensation_factor=0.66,
            all_satisfied_mode=50,
            main_min_temp=19.5,  # Set to the problematic value
            main_max_temp=30.0,
        )
        
        assert is_holding is True
        assert target is not None
        # Average of 20.0 and 22.5 is 21.25
        assert abs(target - 21.25) < 0.1, f"Target should be ~21.25°C, got {target}°C"
        # Should NOT be clamped to 19.5
        assert target > 19.5, f"Target {target}°C should not be clamped to min_temp"

    def test_underheated_zones_compensation(self):
        """Test what happens if zones are actually underheated, not satisfied."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=18.0,  # 2°C below target
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=21.0,  # 1.5°C below target
                target_temp=22.5,
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
        
        # Should NOT be in holding mode - zones need heat
        assert is_holding is False, "Should be in heating mode when zones are underheated"
        
        # Zone1: 20 + 0.66 * (20 - 18) = 20 + 1.32 = 21.32
        # Zone2: 22.5 + 0.66 * (22.5 - 21) = 22.5 + 0.99 = 23.49
        # Should take max = 23.49 ≈ 23.5
        assert target is not None
        assert target >= 23.0, f"Target {target}°C should use compensation for underheated zones"

    def test_very_tight_satisfaction_bounds(self):
        """Test with closing_offset = 0 which creates very tight bounds."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=20.1,  # Slightly above target
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,  # Very tight upper bound
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=22.6,  # Slightly above target
                target_temp=22.5,
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
        
        # With closing_offset=0, upper_bound = target + 0 = target
        # Zone1: current=20.1 > upper_bound=20.0 → overheated (not needing heat)
        # Zone2: current=22.6 > upper_bound=22.5 → overheated (not needing heat)
        # Both zones are overheated, so no zones need HEATING
        # In heating mode, overheated zones are ignored
        # Should be in holding mode with slider-based interpolation
        
        assert is_holding is True, "Should be in holding mode - no zones need heating"
        assert target is not None
        # Average of [20.0, 22.5] = 21.25
        assert abs(target - 21.25) < 0.1, f"Expected ~21.25°C (average), got {target}°C"
