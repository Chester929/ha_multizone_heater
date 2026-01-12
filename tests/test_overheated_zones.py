"""Test to verify overheated/overcooled zones don't incorrectly affect main target."""
import sys
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "multizone_heater"))

import pytest

from core import (
    ZoneData,
    compute_main_target,
)


class TestOverheatedZones:
    """Tests for overheated zones in heating mode."""

    def test_overheated_zone_in_heating_mode(self):
        """Test that overheated zones don't pull down main target in heating mode.
        
        This is the actual scenario from the issue:
        - Koupelna patro: 23.5°C / 23.7°C (satisfied)
        - Koupelna prizemi: 23.9°C / 24.0°C (satisfied)
        - Loznice: 21.9°C / 20.5°C (overheated by 1.4°C)
        - Pracovna: 22.5°C / 22.5°C (satisfied)
        
        Expected: Since only Loznice needs action (but it's overheated, not needing heat),
        all zones are effectively satisfied from a heating perspective.
        Main target should use the slider-based interpolation, not 19.6°C.
        """
        zones = [
            ZoneData(
                name="Koupelna patro",
                current_temp=23.5,
                target_temp=23.7,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Koupelna prizemi",
                current_temp=23.9,
                target_temp=24.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Loznice",
                current_temp=21.9,
                target_temp=20.5,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
            ),
            ZoneData(
                name="Pracovna",
                current_temp=22.5,
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
        
        # Since no zones actually need HEATING (only Loznice is outside bounds but it's overheated),
        # we should be in holding mode
        assert is_holding is True, "Should be in holding mode - no zones need heating"
        
        # At 50% slider, should be average of all zone targets
        # Average of [23.7, 24.0, 20.5, 22.5] = 22.675
        expected_avg = (23.7 + 24.0 + 20.5 + 22.5) / 4
        assert target is not None
        assert abs(target - expected_avg) < 0.1, f"Expected ~{expected_avg}°C, got {target}°C"
        
        # Definitely NOT 19.6°C
        assert target > 20.0, f"Target {target}°C should not be pulled down by overheated zone"

    def test_mixed_zones_some_needing_heat_some_overheated(self):
        """Test with mix of zones needing heat and overheated zones."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=18.0,  # Needs heat: 2°C deficit
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=24.0,  # Overheated: 2°C surplus
                target_temp=22.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
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
        
        # Should NOT be in holding mode - Zone1 needs heat
        assert is_holding is False, "Should be in heating mode - Zone1 needs heat"
        
        # Should calculate based on Zone1 only (needs heat)
        # Zone1: 20 + 0.66 * 2 = 21.32
        # Zone2 should be IGNORED (overheated, doesn't need heat)
        assert target is not None
        expected = 20.0 + 0.66 * 2.0  # 21.32
        assert abs(target - expected) < 0.1, f"Expected ~{expected}°C, got {target}°C"

    def test_only_overheated_zones_in_heating_mode(self):
        """Test when all zones are overheated in heating mode."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=21.0,  # Overheated by 1°C
                target_temp=20.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
            ),
            ZoneData(
                name="Zone2",
                current_temp=23.0,  # Overheated by 1°C
                target_temp=22.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
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
        
        # No zones need heat, so should be in holding mode
        assert is_holding is True, "Should be in holding mode - no zones need heating"
        
        # Should use slider-based interpolation
        # Average of [20.0, 22.0] = 21.0
        assert target == 21.0, f"Expected 21.0°C (average), got {target}°C"


class TestOvercooledZones:
    """Tests for overcooled zones in cooling mode."""

    def test_overcooled_zone_in_cooling_mode(self):
        """Test that overcooled zones don't pull up main target in cooling mode."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=28.0,  # Needs cooling: 2°C surplus
                target_temp=26.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=True,
            ),
            ZoneData(
                name="Zone2",
                current_temp=22.0,  # Overcooled: 2°C deficit
                target_temp=24.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
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
        
        # Should NOT be in holding mode - Zone1 needs cooling
        assert is_holding is False, "Should be in cooling mode - Zone1 needs cooling"
        
        # Should calculate based on Zone1 only (needs cooling)
        # Zone1: 26 - 0.66 * 2 = 24.68
        # Zone2 should be IGNORED (overcooled, doesn't need cooling)
        assert target is not None
        expected = 26.0 - 0.66 * 2.0  # 24.68
        assert abs(target - expected) < 0.1, f"Expected ~{expected}°C, got {target}°C"

    def test_only_overcooled_zones_in_cooling_mode(self):
        """Test when all zones are overcooled in cooling mode."""
        zones = [
            ZoneData(
                name="Zone1",
                current_temp=24.0,  # Overcooled by 2°C
                target_temp=26.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
            ),
            ZoneData(
                name="Zone2",
                current_temp=22.0,  # Overcooled by 2°C
                target_temp=24.0,
                target_offset=0.5,
                target_offset_closing=0.0,
                is_valve_open=False,
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
        
        # No zones need cooling, so should be in holding mode
        assert is_holding is True, "Should be in holding mode - no zones need cooling"
        
        # Should use slider-based interpolation
        # Average of [26.0, 24.0] = 25.0
        assert target == 25.0, f"Expected 25.0°C (average), got {target}°C"
