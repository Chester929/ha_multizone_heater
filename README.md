# Multizone Heater Integration

Home Assistant custom integration to efficiently manage multizone heating systems with individual zone valves and temperature sensors.

## Overview

This integration provides an efficient, asynchronous Python-based solution for managing multizone heating systems. Unlike blueprint-based automations, this integration leverages Home Assistant's native async capabilities for better performance and more responsive control.

## Features

- **Async Operation**: All valve control operations are executed asynchronously for maximum performance
- **Multiple Zone Support**: Configure unlimited heating zones, each with its own temperature sensor and valve
- **Temperature Aggregation**: Choose how to aggregate zone temperatures (average, minimum, or maximum)
- **Safety Features**: Ensures a minimum number of valves remain open to protect heating systems
- **Main Climate Integration**: Optional integration with a main climate entity for coordinated control
- **UI Configuration**: Easy setup through Home Assistant's configuration UI
- **Real-time Updates**: Instant response to temperature changes across all zones

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
   - **Step 1**: Configure main settings
     - **Main Climate Entity** (optional): Select your main climate/thermostat entity
     - **Temperature Aggregation**: Choose how to calculate overall temperature (average, minimum, or maximum)
     - **Temperature Aggregation Weight**: Fine-tune temperature calculation using a percentage slider (0% = minimum, 50% = average, 100% = maximum)
     - **Minimum Valves Open**: Number of valves to keep open at all times (default: 1)
   
   - **Step 2**: Add zones
     - **Zone Name**: Name for the zone (e.g., "Living Room", "Bedroom")
     - **Temperature Sensor**: Select the temperature sensor for this zone
     - **Valve Switch**: Select the switch entity controlling this zone's valve
     - **Opening Offset Below Target**: Temperature offset below target to trigger valve opening (default: 0.5°C)
     - **Closing Offset Above Target**: Temperature offset above target to trigger valve closing (default: 0.0°C, creates hysteresis)
     - **Add Another Zone**: Check to add more zones, uncheck to finish

## Usage

Once configured, the integration creates a climate entity that:

- Displays the aggregated temperature from all zones
- Allows you to set a target temperature
- Automatically controls zone valves based on individual zone temperatures
- Maintains minimum valve count for system safety
- Coordinates with main climate entity if configured

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

For each zone, the integration uses a hysteresis band to prevent rapid valve cycling:

1. **When valve is closed**: Opens when temperature drops below `(target - opening_offset)`
2. **When valve is open**: Closes when temperature rises above `(target + closing_offset)`
3. This creates a deadband that prevents the valve from rapidly switching on/off

**Example with target = 21°C, opening_offset = 0.5°C, closing_offset = 0.2°C:**
- Valve opens when temperature < 20.5°C
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
