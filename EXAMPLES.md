# Multizone Heater - Example Usage

This document provides examples of how to use the Multizone Heater integration in various scenarios.

## Basic Setup Example

### Scenario: 3-Zone Heating System

You have a heating system with:
- Living room with temperature sensor `sensor.living_room_temperature` and valve `switch.living_room_valve`
- Bedroom with temperature sensor `sensor.bedroom_temperature` and valve `switch.bedroom_valve`
- Kitchen with temperature sensor `sensor.kitchen_temperature` and valve `switch.kitchen_valve`

### Configuration Steps

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Multizone Heater"
4. Configure main settings:
   - Leave **Main Climate Entity** empty (no main thermostat)
   - **Temperature Aggregation**: Select "average"
   - **Minimum Valves Open**: Enter 1

5. Add first zone:
   - **Zone Name**: "Living Room"
   - **Temperature Sensor**: `sensor.living_room_temperature`
   - **Valve Switch**: `switch.living_room_valve`
   - **Target Temperature Offset**: 0.5
   - **Add Another Zone**: ✓ (checked)

6. Add second zone:
   - **Zone Name**: "Bedroom"
   - **Temperature Sensor**: `sensor.bedroom_temperature`
   - **Valve Switch**: `switch.bedroom_valve`
   - **Target Temperature Offset**: 0.5
   - **Add Another Zone**: ✓ (checked)

7. Add third zone:
   - **Zone Name**: "Kitchen"
   - **Temperature Sensor**: `sensor.kitchen_temperature`
   - **Valve Switch**: `switch.kitchen_valve`
   - **Target Temperature Offset**: 0.5
   - **Add Another Zone**: ✗ (unchecked) - finish setup

## Advanced Example with Main Climate

### Scenario: Integrated with Central Thermostat

You have a central boiler controlled by `climate.main_thermostat` and want the multizone system to coordinate with it.

Configuration changes from basic example:
- **Main Climate Entity**: Select `climate.main_thermostat`

This will:
- Set the main thermostat target when you change the multizone heater target
- Turn on/off the main thermostat when you change HVAC mode
- Coordinate heating operations between zones and main system

## Usage in Automations

### Example 1: Schedule-Based Heating

```yaml
automation:
  - alias: "Morning Heat Up"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.multizone_heater_3_zones
        data:
          hvac_mode: heat
      - service: climate.set_temperature
        target:
          entity_id: climate.multizone_heater_3_zones
        data:
          temperature: 21

  - alias: "Night Cool Down"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.multizone_heater_3_zones
        data:
          temperature: 18
```

### Example 2: Presence-Based Control

```yaml
automation:
  - alias: "Home - Turn On Heating"
    trigger:
      - platform: state
        entity_id: binary_sensor.home_occupied
        to: "on"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.multizone_heater_3_zones
        data:
          hvac_mode: heat

  - alias: "Away - Turn Off Heating"
    trigger:
      - platform: state
        entity_id: binary_sensor.home_occupied
        to: "off"
        for:
          hours: 1
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.multizone_heater_3_zones
        data:
          hvac_mode: "off"
```

### Example 3: Temperature Override per Time of Day

```yaml
automation:
  - alias: "Dynamic Temperature Control"
    trigger:
      - platform: time
        at: "06:00:00"
      - platform: time
        at: "09:00:00"
      - platform: time
        at: "17:00:00"
      - platform: time
        at: "22:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.multizone_heater_3_zones
        data:
          temperature: >
            {% set hour = now().hour %}
            {% if 6 <= hour < 9 %}
              21
            {% elif 9 <= hour < 17 %}
              19
            {% elif 17 <= hour < 22 %}
              21
            {% else %}
              17
            {% endif %}
```

## Dashboard Card Example

### Simple Thermostat Card

```yaml
type: thermostat
entity: climate.multizone_heater_3_zones
```

### Detailed Card with Zone Information

```yaml
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.multizone_heater_3_zones
  - type: entities
    title: Zone Details
    entities:
      - entity: sensor.living_room_temperature
        name: Living Room Temp
      - entity: switch.living_room_valve
        name: Living Room Valve
      - entity: sensor.bedroom_temperature
        name: Bedroom Temp
      - entity: switch.bedroom_valve
        name: Bedroom Valve
      - entity: sensor.kitchen_temperature
        name: Kitchen Temp
      - entity: switch.kitchen_valve
        name: Kitchen Valve
```

## Temperature Aggregation Methods

### Average (Default)
Best for: Balanced heating across all zones
- Uses the mean temperature of all zones
- Good for even heating distribution

### Minimum
Best for: Ensuring all zones reach target
- Uses the coldest zone's temperature
- Guarantees all zones get warm enough
- May overheat warmer zones

### Maximum
Best for: Energy efficiency
- Uses the warmest zone's temperature
- Reduces unnecessary heating
- Some zones may not reach target

## Safety Features

### Minimum Valves Open

The integration ensures a configurable minimum number of valves remain open at all times. This is important for:

- **Pump Protection**: Some heating systems require at least one valve open to prevent pump damage
- **System Pressure**: Maintains proper water pressure in the system
- **Circulation**: Ensures water keeps circulating

**Default**: 1 valve minimum

When all zones are satisfied and would normally close all valves, the integration keeps the configured minimum number open (typically the first N zones in your configuration).

## Performance Benefits vs. Blueprints

This Python integration provides significant performance improvements:

1. **Async Execution**: All valve operations execute in parallel, not sequentially
2. **Event-Driven**: Responds instantly to temperature changes without polling delays
3. **Efficient State Management**: Internal caching reduces Home Assistant state lookups
4. **No Automation Delays**: No delay between trigger and action as in blueprints
5. **Resource Usage**: Lower CPU and memory usage than complex blueprint automations

## Troubleshooting

### Valves Don't Open/Close

Check:
1. Temperature sensors are reporting valid values
2. Target temperature offset is appropriate for your system
3. Switch entities are working correctly
4. Review integration logs for errors

### Temperature Shows "Unavailable"

Check:
1. All temperature sensors are online and reporting
2. Sensor values are numeric
3. No sensors in STATE_UNKNOWN or STATE_UNAVAILABLE

### Integration Not Responding

Check:
1. Home Assistant logs for errors
2. Verify entities haven't been renamed or deleted
3. Try reloading the integration
