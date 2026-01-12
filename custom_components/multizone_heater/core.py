"""Core computation logic for multizone heater.

This module contains pure, testable functions for calculating zone and main
climate targets. These functions are independent of Home Assistant runtime
and can be unit tested without HA dependencies.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class ZoneData:
    """Data for a single zone."""
    
    name: str
    current_temp: float | None
    target_temp: float
    target_offset: float
    target_offset_closing: float
    is_valve_open: bool


def compute_main_target(
    zones: list[ZoneData],
    hvac_mode: Literal["heat", "cool"],
    compensation_factor: float,
    all_satisfied_mode: int,
    main_min_temp: float,
    main_max_temp: float,
) -> tuple[float | None, bool]:
    """Calculate desired main climate target and determine operating mode.
    
    Args:
        zones: List of zone data with temperatures and targets
        hvac_mode: Current HVAC mode ("heat" or "cool")
        compensation_factor: Factor for compensation-based target (0.0-1.0)
        all_satisfied_mode: Slider value for holding mode (0-100)
            0% = min target, 50% = avg target, 100% = max target
        main_min_temp: Minimum allowed main climate temperature
        main_max_temp: Maximum allowed main climate temperature
    
    Returns:
        Tuple of (desired_main_temp, is_holding_mode)
        - desired_main_temp: Calculated target temperature for main climate, or None
        - is_holding_mode: True if all zones satisfied/overheated (holding mode),
                          False if any zone needs action (heating/cooling mode)
    
    Heating mode logic:
        - Zones needing heat use compensation: zone_target + factor * (target - current)
        - Main target is max of all needing heat
        
    Cooling mode logic:
        - Zones needing cooling use compensation: zone_target - factor * (current - target)
        - Main target is min of all needing cooling
        
    Holding mode logic (all zones satisfied):
        - Interpolates between min/avg/max zone targets using slider
        - 0-50: interpolate between min and avg
        - 50-100: interpolate between avg and max
    """
    zone_targets = []
    per_zone_desired_main = []
    zones_needing_action = []
    
    for zone in zones:
        if zone.current_temp is None:
            continue
            
        zone_targets.append(zone.target_temp)
        
        # Get satisfaction bounds
        if hvac_mode == "heat":
            lower_bound = zone.target_temp - zone.target_offset
            upper_bound = zone.target_temp + zone.target_offset_closing
        else:  # cool
            lower_bound = zone.target_temp - zone.target_offset_closing
            upper_bound = zone.target_temp + zone.target_offset
        
        # Determine if zone needs the current HVAC mode action
        # In heating mode: only zones needing heat (current < target) contribute
        # In cooling mode: only zones needing cooling (current > target) contribute
        if hvac_mode == "heat":
            # Zone needs heat if below lower bound (underheated)
            needs_mode_action = zone.current_temp < lower_bound
            if needs_mode_action:
                deficit = zone.target_temp - zone.current_temp
                zone_desired_main = zone.target_temp + compensation_factor * deficit
                zones_needing_action.append(zone.name)
                per_zone_desired_main.append(zone_desired_main)
        else:  # cool
            # Zone needs cooling if above upper bound (overheated)
            needs_mode_action = zone.current_temp > upper_bound
            if needs_mode_action:
                surplus = zone.current_temp - zone.target_temp
                zone_desired_main = zone.target_temp - compensation_factor * surplus
                zones_needing_action.append(zone.name)
                per_zone_desired_main.append(zone_desired_main)
    
    # Calculate desired main climate target
    desired_main = None
    is_holding_mode = False
    
    if zones_needing_action and per_zone_desired_main:
        # Heating/cooling mode: zones need action - use compensation-based target
        if hvac_mode == "heat":
            desired_main = max(per_zone_desired_main)
        else:  # cool
            desired_main = min(per_zone_desired_main)
        is_holding_mode = False
    elif zone_targets:
        # Holding mode: All zones satisfied - use slider-based interpolation
        min_target = min(zone_targets)
        max_target = max(zone_targets)
        avg_target = sum(zone_targets) / len(zone_targets)
        
        weight = all_satisfied_mode
        if weight <= 50:
            ratio = weight / 50.0
            desired_main = min_target + (avg_target - min_target) * ratio
        else:
            ratio = (weight - 50) / 50.0
            desired_main = avg_target + (max_target - avg_target) * ratio
        is_holding_mode = True
    
    if desired_main is not None:
        # Round and clamp to configured range
        desired_main = round(desired_main, 1)
        desired_main = max(main_min_temp, min(main_max_temp, desired_main))
    
    return desired_main, is_holding_mode


def compute_zone_targets(
    zones: list[ZoneData],
    hvac_mode: Literal["heat", "cool"],
) -> dict[str, dict[str, float]]:
    """Calculate target information for each zone.
    
    Args:
        zones: List of zone data
        hvac_mode: Current HVAC mode ("heat" or "cool")
    
    Returns:
        Dictionary mapping zone name to target info dict with keys:
        - target: Zone target temperature
        - lower_bound: Lower bound of satisfaction range
        - upper_bound: Upper bound of satisfaction range
    """
    result = {}
    
    for zone in zones:
        # Calculate satisfaction bounds based on HVAC mode
        if hvac_mode == "heat":
            # Heating: satisfied range is [target - opening_offset, target + closing_offset]
            lower_bound = zone.target_temp - zone.target_offset
            upper_bound = zone.target_temp + zone.target_offset_closing
        else:  # cool
            # Cooling: satisfied range is [target - closing_offset, target + opening_offset]
            lower_bound = zone.target_temp - zone.target_offset_closing
            upper_bound = zone.target_temp + zone.target_offset
        
        result[zone.name] = {
            "target": round(zone.target_temp, 1),
            "lower_bound": round(lower_bound, 1),
            "upper_bound": round(upper_bound, 1),
        }
    
    return result
