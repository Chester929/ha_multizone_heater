# Multizone Heater Integration

Home Assistant custom integration to efficiently manage multizone heating/cooling systems with individual zone valves, temperature sensors, and optional zone climate entities.

## Overview

This integration provides an efficient, asynchronous Python-based solution for managing multizone heating and cooling systems. It monitors your main climate entity (boiler/HVAC) and intelligently controls individual zone valves based on zone temperatures and the main climate's operating state.

## Features

### Core Functionality
- **Main Climate Monitoring**: Respects and monitors your main climate entity (boiler) - does not control its HVAC mode
- **Temperature Display**: Uses the main climate's temperature sensor (typically in corridor) for accurate display
- **Smart Valve Control**: Manages individual zone valves based on zone temperatures and main climate state
- **Multiple Zone Support**: Configure unlimited heating/cooling zones, each with its own temperature sensor and valve
- **Zone Climate Entities**: Support for zone climate entities (e.g., Generic Thermostat) with virtual switch pattern to prevent conflicts
- **Safety Features**: Ensures fallback zones remain open to protect heating systems when main climate is OFF
- **Fallback Zones**: Mandatory fallback zones ensure pump safety during cooling and when main climate is OFF
- **UI Configuration**: Easy setup through Home Assistant's configuration UI (no YAML required)
- **Real-time Updates**: Instant response to temperature and main climate state changes via event-driven architecture

### Advanced Features
- **Valve Hysteresis**: Separate opening and closing temperature offsets prevent rapid valve cycling
- **Virtual Switch Pattern**: Clean separation between zone climate control and physical valve control
- **Input Validation**: Prevents duplicate entity usage across zones
- **Error Handling**: Comprehensive error handling for all service calls
- **Temperature Unit Support**: Automatically uses Home Assistant's configured temperature unit
- **Intelligent Main Climate Target Control**: Per-zone compensation logic calculates optimal main climate target based on actual zone needs
- **Valve Transition Delay**: Two-phase valve operation prevents pump issues by opening valves before closing others
- **Physical Close Anticipation**: Early valve closing prevents temperature overshoot with reopen suppression
- **All-Satisfied Slider**: Configurable main climate target when all zones are satisfied (interpolates between min/avg/max)
- **Non-Blocking Updates**: Main climate updates are asynchronous and threshold-based to minimize unnecessary calls

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
     - **Main Climate Entity** (required): Select your main climate/thermostat entity (boiler controller). Its temperature sensor will be used for display.
     - **Main Temperature Sensor Override** (optional): Override the main climate's temperature sensor with a specific sensor
     - **Main Target When All Zones Satisfied** (slider 0-100%): What to set the main climate target when all zones have reached their targets
       - 0% = Use lowest zone target (energy efficient)
       - 50% = Use average zone target (balanced approach, default)
       - 100% = Use highest zone target (keeps boiler warmer)
       - This prevents the boiler from shutting down completely while maintaining efficiency
     - **Minimum Valves Open**: Number of valves to keep open at all times for system safety (default: 1)
     - **Compensation Factor**: Corridor compensation for main climate target (default: 0.66, range: 0.0-1.0)
     - **Valve Transition Delay**: Seconds to wait between opening and closing valves (default: 60s, range: 5-300s)
     - **Main Min/Max Temperature**: Temperature range for main climate (default: 18.0-30.0°C)
     - **Main Change Threshold**: Minimum temperature change to update main climate (default: 0.1°C)
     - **Physical Close Anticipation**: Early close offset to prevent overshoot (default: 0.6°C)
   
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

### Managing Zones After Setup

**New in v1.1.0**: You can now manage zones at any time without recreating the integration!

1. Go to **Settings** → **Devices & Services**
2. Find **Multizone Heater** and click **Configure**
3. Choose from the menu:
   - **Global Settings**: Update system-wide parameters
   - **Manage Zones**: Add, edit, remove zones, or configure fallback zones

**Zone Management Options:**
- **Add New Zone**: Add additional zones to your system
- **Edit Existing Zone**: Modify zone settings, change entities, or adjust temperature offsets
- **Remove Zone**: Remove zones you no longer need (cannot remove the last zone)
- **Configure Fallback Zones**: Update which zones remain open during cooling or when all zones are satisfied

For detailed information, see [ZONE_MANAGEMENT_GUIDE.md](ZONE_MANAGEMENT_GUIDE.md).

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

### Temperature Display

The integration displays the current temperature from your **main climate entity's temperature sensor** (typically located in the corridor). This provides an accurate reading of the central heating system's performance.

- If a **Main Temperature Sensor Override** is configured, it uses that sensor instead
- Otherwise, it reads the temperature from the main climate entity itself
- Individual zone temperatures are used for valve control, not for display

**Important:** The integration does NOT aggregate zone temperatures. It shows the actual corridor/main temperature as reported by your main climate entity.

### Main Climate HVAC Mode Monitoring

The integration **monitors** (does not control) the main climate's HVAC mode:

- **When main climate is OFF**: Closes all valves except fallback zones for pump safety
- **When main climate is HEAT/COOL/IDLE**: Manages valves normally based on zone temperatures
- You control the main climate's HVAC mode externally (manually or via other automations)
- The integration only updates the main climate's **target temperature**, not its HVAC mode

### Main Climate Compensation Logic

The integration uses intelligent compensation to set the optimal main climate target based on individual zone needs:

#### Heating Mode Compensation
For each zone needing heat, the integration calculates a per-zone desired main temperature:
```
per_zone_desired_main = zone_target + compensation_factor × (zone_target - zone_current)
```

**Example:** Zone at 20°C with target 23°C and compensation factor 0.66:
- Deficit = 23 - 20 = 3°C
- Desired main = 23 + 0.66 × 3 = 23 + 1.98 = **24.98°C** (rounded to 25.0°C)

The integration then uses the **maximum** of all per-zone desired temperatures as the main climate target, clamped to the configured min/max range (default 18-30°C).

**Multi-zone example:** Two zones with targets 23°C and 27°C at deficits of 3°C and 5°C:
- Zone 1 desired: 23 + 0.66 × 3 = 24.98°C
- Zone 2 desired: 27 + 0.66 × 5 = 30.3°C
- Main target = max(24.98, 30.3) = **30.0°C** (clamped to max)

#### Cooling Mode Compensation
For cooling, the logic is inversed:
```
per_zone_desired_main = zone_target - compensation_factor × (zone_current - zone_target)
```

The integration uses the **minimum** of all per-zone desired temperatures.

#### All Zones Satisfied Behavior
When all zones are satisfied (no heating/cooling needed), the integration uses the **Main Target When All Zones Satisfied** slider to set the main climate target:

- **0%**: Uses **lowest zone target**
  - Most energy efficient
  - Boiler runs at minimum necessary temperature
  
- **50%** (default): Uses **average zone target**
  - Balanced approach
  - Keeps boiler ready for quick response
  
- **100%**: Uses **highest zone target**
  - Keeps boiler warmest
  - Fastest response when zones need heat again

**Why is this needed?** This prevents the main climate from shutting down completely while maintaining efficiency. When all zones are satisfied, the boiler needs a target temperature to maintain - this slider controls what that target is.

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

#### Physical Close Anticipation
To prevent temperature overshoot, the integration can close physical valves early:

- **Physical close threshold** = `(target + closing_offset) - physical_close_anticipation`
- **Default**: 0.6°C anticipation
- When a valve closes early, it cannot reopen for the configured valve transition delay period

**Example with target = 21°C, closing_offset = 0.2°C, anticipation = 0.6°C:**
- Normal close threshold: 21.2°C
- Physical close threshold: 21.2 - 0.6 = **20.6°C**
- Valve closes at 20.6°C instead of 21.2°C, preventing overshoot
- Reopen suppressed for 60s (default valve transition delay)

#### Valve Transition Delay
To ensure pump safety and smooth operation, the integration uses two-phase valve control:

1. **Phase 1**: Open valves that need to be turned on
2. **Wait**: Sleep for the configured valve transition delay (default: 60 seconds)
3. **Phase 2**: Close valves that need to be turned off

This ensures the pump always has adequate flow during transitions and prevents water hammer effects.

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
- Ensures the configured minimum number of valves remain open

All valve operations are executed asynchronously for maximum efficiency.

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

For comprehensive troubleshooting guidance, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Quick Tips

**Climate Entity Hidden:**
The climate entity is hidden by default as of v1.0.1. It runs in the background to control valves and update the main climate. To see only sensors in your UI (recommended), leave it disabled. You can manually enable it in **Settings → Entities** if needed.

**Main Climate Not Updating:**
Enable debug logging to see detailed information about updates:
```yaml
logger:
  default: info
  logs:
    custom_components.multizone_heater: debug
```

Look for messages about main climate updates. Common causes:
- HVAC mode is OFF (updates only happen in HEAT/COOL mode)
- Change threshold preventing updates (default 0.1°C)
- Main climate entity not responding

**Unexpected Main Target Value:**
The calculation logic is correct and thoroughly tested. If you see an unexpected value:
- Check zone satisfaction bounds (zones might not be "satisfied")
- Verify zone target temperatures
- Review configuration (min/max temps, slider position)
- Check debug logs for detailed zone calculations

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

### TypeError: 'float' object cannot be interpreted as an integer

This error was fixed in version 0.0.2. If you encounter this issue:

1. **Update to the latest version** - The fix ensures `min_valves_open` is always stored as an integer
2. **Reconfigure the integration** - Go to Settings → Devices & Services → Multizone Heater → Configure and save the settings again
3. **Enable debug logging** to verify the fix:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.multizone_heater: debug
   ```
4. Check the logs for a message like: `Initialized min_valves_open: 2 (type: int, original: 2.0)`

The integration now automatically converts float values to integers and includes debug logging to help diagnose configuration issues.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is provided as-is for use with Home Assistant.

## Credits

Created as a high-performance alternative to blueprint-based multizone heating automations.
