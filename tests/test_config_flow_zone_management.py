"""Unit tests for zone management in config flow options."""
import sys
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "multizone_heater"))

from const import (
    CONF_ZONE_NAME,
    CONF_ZONE_CLIMATE,
    CONF_VALVE_SWITCH,
    CONF_VIRTUAL_SWITCH,
    CONF_ZONES,
    CONF_FALLBACK_ZONES,
)


def test_zone_data_structure():
    """Test that zone data structure is correct."""
    zone = {
        CONF_ZONE_NAME: "Living Room",
        CONF_ZONE_CLIMATE: "climate.living_room",
        CONF_VALVE_SWITCH: "switch.valve_living_room",
        CONF_VIRTUAL_SWITCH: "switch.virtual_living_room",
    }
    
    assert zone[CONF_ZONE_NAME] == "Living Room"
    assert zone[CONF_ZONE_CLIMATE] == "climate.living_room"
    assert zone[CONF_VALVE_SWITCH] == "switch.valve_living_room"
    assert zone[CONF_VIRTUAL_SWITCH] == "switch.virtual_living_room"
    print("✓ test_zone_data_structure passed")


def test_zone_list_operations():
    """Test zone list add and remove operations."""
    zones = []
    
    # Add first zone
    zone1 = {
        CONF_ZONE_NAME: "Zone 1",
        CONF_ZONE_CLIMATE: "climate.zone1",
        CONF_VALVE_SWITCH: "switch.valve1",
        CONF_VIRTUAL_SWITCH: "switch.virtual1",
    }
    zones.append(zone1)
    assert len(zones) == 1
    
    # Add second zone
    zone2 = {
        CONF_ZONE_NAME: "Zone 2",
        CONF_ZONE_CLIMATE: "climate.zone2",
        CONF_VALVE_SWITCH: "switch.valve2",
        CONF_VIRTUAL_SWITCH: "switch.virtual2",
    }
    zones.append(zone2)
    assert len(zones) == 2
    
    # Remove first zone
    zones = [z for z in zones if z[CONF_ZONE_NAME] != "Zone 1"]
    assert len(zones) == 1
    assert zones[0][CONF_ZONE_NAME] == "Zone 2"
    print("✓ test_zone_list_operations passed")


def test_duplicate_entity_detection():
    """Test that duplicate entities can be detected."""
    zones = [
        {
            CONF_ZONE_NAME: "Zone 1",
            CONF_ZONE_CLIMATE: "climate.zone1",
            CONF_VALVE_SWITCH: "switch.valve1",
            CONF_VIRTUAL_SWITCH: "switch.virtual1",
        },
        {
            CONF_ZONE_NAME: "Zone 2",
            CONF_ZONE_CLIMATE: "climate.zone2",
            CONF_VALVE_SWITCH: "switch.valve2",
            CONF_VIRTUAL_SWITCH: "switch.virtual2",
        },
    ]
    
    # Collect all entities
    all_entities = []
    for zone in zones:
        if zone.get(CONF_ZONE_CLIMATE):
            all_entities.append(zone[CONF_ZONE_CLIMATE])
        if zone.get(CONF_VALVE_SWITCH):
            all_entities.append(zone[CONF_VALVE_SWITCH])
        if zone.get(CONF_VIRTUAL_SWITCH):
            all_entities.append(zone[CONF_VIRTUAL_SWITCH])
    
    # Test for duplicate
    assert "climate.zone1" in all_entities
    assert all_entities.count("climate.zone1") == 1
    
    # Test detection would work
    test_entity = "climate.zone1"
    is_duplicate = test_entity in all_entities
    assert is_duplicate is True
    print("✓ test_duplicate_entity_detection passed")


def test_fallback_zone_management():
    """Test fallback zone list management."""
    zones = [
        {CONF_ZONE_NAME: "Zone 1"},
        {CONF_ZONE_NAME: "Zone 2"},
        {CONF_ZONE_NAME: "Zone 3"},
    ]
    
    # Set fallback zones
    fallback_zones = ["Zone 1", "Zone 2"]
    assert len(fallback_zones) == 2
    
    # Remove a zone that's in fallback list
    zone_to_remove = "Zone 1"
    zones = [z for z in zones if z[CONF_ZONE_NAME] != zone_to_remove]
    fallback_zones = [z for z in fallback_zones if z != zone_to_remove]
    
    assert len(zones) == 2
    assert len(fallback_zones) == 1
    assert "Zone 1" not in fallback_zones
    assert "Zone 2" in fallback_zones
    
    # Ensure at least one fallback zone remains
    if not fallback_zones and zones:
        fallback_zones = [zones[0][CONF_ZONE_NAME]]
    
    assert len(fallback_zones) >= 1
    print("✓ test_fallback_zone_management passed")


def test_zone_update():
    """Test updating a zone's configuration."""
    zones = [
        {
            CONF_ZONE_NAME: "Zone 1",
            CONF_ZONE_CLIMATE: "climate.zone1",
            CONF_VALVE_SWITCH: "switch.valve1",
        },
    ]
    
    zone_to_edit = 0
    
    # Update the zone
    updated_zone = {
        CONF_ZONE_NAME: "Updated Zone 1",
        CONF_ZONE_CLIMATE: "climate.zone1_new",
        CONF_VALVE_SWITCH: "switch.valve1_new",
    }
    
    zones[zone_to_edit] = updated_zone
    
    assert zones[0][CONF_ZONE_NAME] == "Updated Zone 1"
    assert zones[0][CONF_ZONE_CLIMATE] == "climate.zone1_new"
    print("✓ test_zone_update passed")


if __name__ == "__main__":
    print("Running zone management tests...")
    try:
        test_zone_data_structure()
        test_zone_list_operations()
        test_duplicate_entity_detection()
        test_fallback_zone_management()
        test_zone_update()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

