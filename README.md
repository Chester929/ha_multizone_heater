# Multizone Heater Integration

Home Assistant custom integration to efficiently manage multizone heating/cooling systems with individual zone valves, temperature sensors, and optional zone climate entities.

## Overview

This integration provides an efficient, asynchronous Python-based solution for managing multizone heating and cooling systems. Unlike blueprint-based automations, this integration leverages Home Assistant's native async capabilities for better performance, more responsive control, and advanced features like zone climate coordination and cooling mode support.

## Features

### Core Functionality
- **Async Operation**: All valve control operations are executed asynchronously in parallel for maximum performance
- **Multiple Zone Support**: Configure unlimited heating/cooling zones, each with its own temperature sensor and valve
- **Zone Climate Entities**: Support for zone climate entities (e.g., Generic Thermostat) with virtual switch pattern to prevent conflicts
- **Temperature Aggregation**: Choose how to aggregate zone temperatures (average, minimum, maximum, or percentage-based)
- **Cooling Mode Support**: Automatically detects and supports cooling if main climate entity has cooling capability
- **Safety Features**: Ensures a minimum number of valves remain open to protect heating systems
- **Fallback Zones**: Mandatory fallback zones ensure pump safety during cooling and when all zones are satisfied
- **Main Climate Integration**: Optional integration with a main climate entity for coordinated control
- **UI Configuration**: Easy setup through Home Assistant's configuration UI (no YAML required)
- **Real-time Updates**: Instant response to temperature changes across all zones via event-driven architecture

### Advanced Features
- **Valve Hysteresis**: Separate opening and closing temperature offsets prevent rapid valve cycling
- **Percentage-Based Aggregation**: Fine-tune temperature calculation with 0-100% slider (0%=min, 50%=avg, 100%=max)
- **Virtual Switch Pattern**: Clean separation between zone climate control and physical valve control
- **Input Validation**: Prevents duplicate entity usage across zones
- **Error Handling**: Comprehensive error handling for all service calls
- **Temperature Unit Support**: Automatically uses Home Assistant's configured temperature unit

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/Chester929/ha_multizone_heater` as an Integration
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/multizone_heater` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Through the UI

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Multizone Heater"
4. Follow the configuration steps:
   
   - **Step 1: Main Settings**
     - **Main Climate Entity** (optional): Select your main climate/thermostat entity (e.g., boiler controller)
     - **Temperature Aggregation Method**: Choose preset method (average, minimum, or maximum)
     - **Temperature Aggregation Weight**: Fine-tune with 0-100% slider (0% = minimum, 50% = average, 100% = maximum)
     - **Minimum Valves Open**: Number of valves to keep open at all times for system safety (default: 1)
   
   - **Step 2: Add Zones**
     - **Zone Name**: Name for the zone (e.g., "Living Room", "Bedroom")
     - **Zone Climate Entity** (optional): Climate entity for the zone (provides temperature and can be coordinated)
     - **Temperature Sensor Override** (optional): Override temperature source with a specific sensor
     - **Physical Valve Switch** (optional): Physical valve entity - REQUIRED if using virtual switch
     - **Virtual Switch** (optional): Virtual/helper switch controlled by zone climate - REQUIRED if using physical valve
     - **Opening Offset Below Target**: Temperature offset below target to trigger valve opening (default: 0.5°C)
     - **Closing Offset Above Target**: Temperature offset above target to trigger valve closing (default: 0.0°C)
     - **Add Another Zone**: Check to add more zones, uncheck to finish
   
   - **Step 3: Fallback Zones** (REQUIRED)
     - **Fallback Zones**: Select at least one zone to keep open when all zones are satisfied or during cooling mode
     - This ensures pump safety by preventing all valves from closing simultaneously

### Zone Configuration Patterns

**Pattern 1: Zone Climate + Virtual Switch Pattern (Recommended for Generic Thermostat)**
- Best for zones with Generic Thermostat climate entities
- Prevents conflicts where both climate entity and integration try to control the same valve
- Setup:
  1. Create a virtual/helper switch for each zone (`input_boolean.zone_virtual_valve`)
  2. Configure Generic Thermostat to control the virtual switch (not physical valve)
  3. Provide: Zone Climate + Physical Valve + Virtual Switch
- How it works:
  - Generic Thermostat controls virtual switch based on zone temperature
  - Integration monitors virtual switch AND controls physical valve
  - Integration coordinates across zones while respecting individual zone requests

**Pattern 2: Zone Climate Only**
- For zones with climate entities that don't control valves
- Provide: Zone Climate only
- Integration reads temperature from climate entity
- No valve control for this zone (monitoring only)

**Pattern 3: Temperature Sensor + Valve**
- For zones without climate entities
- Provide: Temperature Sensor + Physical Valve
- Integration directly reads sensor and controls valve

### Important Notes

- **Temperature Source**: At least one of Zone Climate OR Temperature Sensor must be provided per zone
- **Valve Control**: If providing a physical valve, virtual switch is REQUIRED (virtual switch pattern prevents conflicts)
- **No Duplicates**: Each entity can only be used once across all zones (validated during configuration)
- **Fallback Zones**: At least one fallback zone MUST be selected for pump safety
- **Cooling Support**: If main climate supports cooling, the integration will automatically add cooling mode

## Usage

Once configured, the integration creates a climate entity that:

- Displays the aggregated temperature from all zones
- Allows you to set a target temperature that applies to all zones
- Supports HEAT, COOL (if main climate supports it), and OFF modes
- Automatically controls zone valves based on individual zone temperatures and current mode
- Maintains minimum valve count for system safety
- Opens only fallback zones during cooling mode (non-fallback zones close)
- Coordinates with main climate entity if configured
- Provides real-time HVAC action indication (HEATING, COOLING, IDLE, OFF)

### Example Automation

You can use the climate entity in automations:

```yaml
automation:
  - alias: "Morning Heating"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.multizone_heater
        data:
          temperature: 21
```

## How It Works

### Temperature Aggregation

The integration monitors temperature sensors in all configured zones and aggregates them based on your chosen method:

- **Average**: Uses the mean temperature across all zones
- **Minimum**: Uses the coldest zone's temperature (ensures all zones reach target)
- **Maximum**: Uses the warmest zone's temperature
- **Weight-based (0-100% slider)**: Allows fine-grained control between minimum and maximum
  - 0% = Uses minimum temperature (coldest zone)
  - 50% = Uses average temperature (mean of all zones)
  - 100% = Uses maximum temperature (warmest zone)
  - Values between interpolate smoothly (e.g., 25% is halfway between min and average)

### Valve Control Logic with Hysteresis

#### Heating Mode
For each zone in heating mode, the integration uses a hysteresis band to prevent rapid valve cycling:

1. **When valve is closed**: Opens when temperature drops below `(target - opening_offset)`
2. **When valve is open**: Closes when temperature rises above `(target + closing_offset)`
3. This creates a deadband that prevents the valve from rapidly switching on/off

**Example with target = 21°C, opening_offset = 0.5°C, closing_offset = 0.2°C:**
- Valve opens when temperature < 20.5°C
- Valve closes when temperature > 21.2°C
- Between 20.5°C and 21.2°C, valve maintains its current state

#### Cooling Mode
When the integration is in cooling mode (if main climate supports it):

1. **Only fallback zone valves remain open** - ensures pump safety
2. **All non-fallback zone valves are closed** - prevents zones without cooling support from interfering
3. **Main climate is set to COOL mode** - coordinates cooling operation
4. **Warning logs** are generated for zones that don't support cooling

**Why this approach:**
- Many zone climate entities (e.g., Generic Thermostat configured for heating only) don't support cooling
- Closing non-fallback valves during cooling prevents conflicts
- Fallback zones ensure the system maintains flow for pump safety
- Main climate handles the actual cooling operation

### Fallback Zones

Fallback zones serve two critical purposes:

1. **Pump Safety**: Ensures at least one valve is always open to maintain system flow
2. **Cooling Mode**: Keeps designated zones active during cooling while others close

**When fallback zones are used:**
- All zones are satisfied (temperature reached) - fallback valves stay open
- Cooling mode is active - only fallback valves stay open
- System transitions between modes - fallback valves provide continuity
- Valve closes when temperature > 21.2°C
- Between 20.5°C and 21.2°C, valve maintains its current state
4. Ensures the configured minimum number of valves remain open

All valve operations are executed asynchronously in parallel for maximum efficiency.

### Safety Features

- **Minimum Valves Open**: Prevents all valves from closing simultaneously, which could damage some heating systems
- **Async Locking**: Prevents race conditions when updating valve states
- **State Validation**: Handles unavailable or invalid sensor readings gracefully

## Performance Advantages

Compared to blueprint-based automation solutions, this integration offers:

1. **Native Async Support**: All operations use Python's asyncio for non-blocking execution
2. **Parallel Valve Control**: Multiple valves can be controlled simultaneously
3. **Efficient State Tracking**: Internal state management reduces unnecessary calls
4. **Event-Driven Updates**: Responds instantly to temperature changes without polling
5. **Optimized Calculations**: Efficient temperature aggregation algorithms

## Troubleshooting

### Integration Not Appearing

- Ensure the integration files are in the correct directory
- Restart Home Assistant after installation
- Check Home Assistant logs for any error messages

### Valves Not Responding

- Verify that valve switch entities are working correctly
- Check that temperature sensors are reporting valid values
- Review the integration logs for any errors

### Temperature Not Updating

- Ensure temperature sensors are updating regularly
- Verify sensor entities are in the correct domain (sensor)
- Check for STATE_UNKNOWN or STATE_UNAVAILABLE in sensor states

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is provided as-is for use with Home Assistant.

## Credits

Created as a high-performance alternative to blueprint-based multizone heating automations.
