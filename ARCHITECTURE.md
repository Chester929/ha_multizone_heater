# Architecture Overview

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Home Assistant Core                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Multizone Heater Integration                      │  │
│  │                                                           │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  Climate Entity (MultizoneHeaterClimate)           │  │  │
│  │  │  - Aggregates temperatures from all zones          │  │  │
│  │  │  - Controls target temperature                     │  │  │
│  │  │  - Manages HVAC mode (Heat/Cool/Off)               │  │  │
│  │  │  - Async valve control coordinator                 │  │  │
│  │  │  - Cooling mode detection and support              │  │  │
│  │  │  - Fallback zone management                        │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                         │                                 │  │
│  │                         │                                 │  │
│  │         ┌───────────────┴────────────────┐               │  │
│  │         │                                │               │  │
│  │         ▼                                ▼               │  │
│  │  ┌─────────────┐                 ┌─────────────┐        │  │
│  │  │ Temperature │                 │   Valve     │        │  │
│  │  │   Source    │◄───monitors────►│   Control   │        │  │
│  │  │  Tracking   │                 │   (Async)   │        │  │
│  │  │ (Sensors &  │                 │  Parallel   │        │  │
│  │  │  Climates)  │                 │  Execution  │        │  │
│  │  └─────────────┘                 └─────────────┘        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │                    │
                          │                    │
          ┌───────────────┴──────┐             └──────────────┐
          │                      │                            │
          ▼                      ▼                            ▼
┌──────────────────┐  ┌──────────────────┐      ┌──────────────────────┐
│ Temperature      │  │  Zone Climate    │      │    Valve Switches    │
│ Sensors          │  │  Entities         │      │                      │
│                  │  │                  │      │  • Physical Valves   │
│ • Zone 1 Sensor  │  │ • Zone 1 Climate │      │  • Zone 1 Valve      │
│ • Zone 2 Sensor  │  │ • Zone 2 Climate │      │  • Zone 2 Valve      │
│ • ... unlimited  │  │ • ... unlimited  │      │  • ... unlimited     │
│                  │  │                  │      │                      │
│                  │  │ Virtual Switches │      │ Fallback Zones:      │
│                  │  │ • Zone 1 Virtual │      │  • Always open when  │
│                  │  │ • Zone 2 Virtual │      │    all satisfied     │
│                  │  │ (conflict-free)  │      │  • Open in cooling   │
└──────────────────┘  └──────────────────┘      └──────────────────────┘
```

## Data Flow

### 1. Temperature Monitoring (Event-Driven)
Temperature Sensor State Change
        │
        ▼
Event Listener (async_track_state_change_event)
        │
        ▼
Climate Entity Update Triggered
        │
        ▼
Calculate Aggregated Temperature
  • Average: mean(all_temps)
  • Minimum: min(all_temps)
  • Maximum: max(all_temps)
        │
        ▼
Update Current Temperature
        │
        ▼
Trigger Valve Control (if needed)
```

### 2. Valve Control Logic (Async)

```
Valve Control Request
        │
        ▼
Acquire Update Lock (prevents race conditions)
        │
        ▼
For Each Zone in Parallel:
  ├─► Read current temperature
  ├─► Compare to (target - offset)
  └─► Determine should_open
        │
        ▼
Calculate Required Valves
        │
        ▼
Apply Safety Logic
  • Ensure min_valves_open
  • Keep extra valves if needed
        │
        ▼
Build Async Tasks List
  ├─► Turn ON tasks for zones needing heat
  └─► Turn OFF tasks for satisfied zones
        │
        ▼
Execute All Tasks in Parallel
  asyncio.gather(*tasks)
        │
        ▼
Release Update Lock
```

### 3. HVAC Mode Changes

```
Set HVAC Mode Request
        │
        ├─► If Mode = OFF
        │   ├─► Turn off all valves (except min_valves_open)
        │   └─► Turn off main climate (if configured)
        │
        ├─► If Mode = HEAT
        │   ├─► Turn on main climate in HEAT mode (if configured)
        │   └─► Control valves based on zone temps + hysteresis
        │
        └─► If Mode = COOL (if main climate supports it)
            ├─► Turn on main climate in COOL mode
            ├─► Open ONLY fallback zone valves
            ├─► Close all non-fallback valves
            └─► Log warnings for zones without cooling support
```

### 4. Virtual Switch Pattern (Zone Climate Coordination)

```
Zone Climate Entity (e.g., Generic Thermostat)
        │
        ├─► Reads zone temperature
        ├─► Determines heating need
        └─► Controls Virtual Switch (input_boolean)
                  │
                  ▼
        Multizone Heater Integration
                  │
                  ├─► Monitors Virtual Switch state
                  ├─► Coordinates with other zones
                  ├─► Applies safety logic
                  └─► Controls Physical Valve
                            │
                            ▼
                  Physical Valve Switch
                  (actual hardware control)

Benefits:
• No conflicts - clean separation
• Zone climate keeps target temperature
• Integration handles coordination
• Physical valve controlled by integration only
```

### 5. Cooling Mode Operation

```
Main Climate has COOL support?
        │
        ├─► YES: Add COOL to HVAC modes
        │   │
        │   └─► User sets Mode to COOL
        │       │
        │       ├─► Validate zone climate entities
        │       │   └─► Log warnings if no cooling support
        │       │
        │       ├─► Open fallback zone valves
        │       ├─► Close non-fallback valves
        │       └─► Set main climate to COOL
        │
        └─► NO: Only HEAT and OFF modes available
```

### 6. Fallback Zone Management

```
All Zones Satisfied OR Cooling Mode?
        │
        ├─► Get fallback zone valve entities
        │
        ├─► Open fallback zone valves
        │   └─► Ensures pump safety
        │
        └─► Close non-fallback valves (if in cooling)
            OR keep based on temperature (if heating)
```

## Async Performance Benefits

### Traditional Blueprint Approach
```
Trigger → Wait → Action 1 → Wait → Action 2 → Wait → Action 3 → Done
Total Time: Sum of all waits and actions
```

### This Integration's Async Approach
```
Trigger → Action 1 ┐
Trigger → Action 2 ├─► Execute in Parallel → Done
Trigger → Action 3 ┘
Total Time: Max of individual actions (typically 1/Nth the time)
```

## Key Classes and Methods

### MultizoneHeaterClimate (climate.py)

**Properties:**
- `current_temperature` - Aggregated temperature from all zones
- `target_temperature` - User-set target temperature
- `hvac_mode` - Current mode (HEAT, COOL, or OFF)
- `hvac_action` - Current action (HEATING, COOLING, IDLE, or OFF)
- `hvac_modes` - Available modes (dynamically set based on main climate capabilities)
- `_supports_cooling` - Boolean flag indicating cooling support
- `_fallback_zone_names` - List of fallback zone names for pump safety

**Key Methods:**
- `async_set_temperature(temperature)` - Set target temperature and trigger valve control
- `async_set_hvac_mode(mode)` - Change HVAC mode (HEAT/COOL/OFF) and coordinate with main climate
- `async_update()` - Calculate aggregated temperature and update HVAC action
- `_async_control_valves()` - Main valve control logic for heating mode with hysteresis
- `_async_control_valves_for_cooling()` - Valve control for cooling mode (fallback zones only)
- `_async_get_valve_states()` - Query current state of all physical valves
- `_async_turn_off_all_valves()` - Turn off valves except minimum required
- `_async_call_service_with_error_handling()` - Wrapper for safe service calls with logging

**Temperature Aggregation Logic:**
```python
# Based on configured method
if aggregation == "average":
    temp = mean(zone_temps)
elif aggregation == "minimum":
    temp = min(zone_temps)
elif aggregation == "maximum":
    temp = max(zone_temps)
else:
    # Weight-based (0-100%)
    if weight <= 50:
        temp = min + (avg - min) * (weight / 50)
    else:
        temp = avg + (max - avg) * ((weight - 50) / 50)
```

**Valve Control Logic (Heating Mode):**
```python
for zone in zones:
    # Get temperature from climate entity or sensor
    current_temp = get_zone_temperature(zone)
    
    # Check virtual switch if present, otherwise physical valve
    check_entity = zone.virtual_switch or zone.valve
    is_open = state(check_entity) == ON
    
    # Hysteresis logic
    if is_open:
        should_open = current_temp < (target + closing_offset)
    else:
        should_open = current_temp < (target - opening_offset)
    
    if should_open:
        zones_needing_heat.append(zone.valve)
```

**Valve Control Logic (Cooling Mode):**
```python
async def _async_control_valves_for_cooling():
    # Get fallback zone valve entities
    fallback_valves = [zone.valve for zone in zones 
                       if zone.name in fallback_zone_names]
    
    # Open only fallback valves
    for valve in fallback_valves:
        await turn_on(valve)
    
    # Close all non-fallback valves
    for valve in all_valves:
        if valve not in fallback_valves:
            await turn_off(valve)
```
- `hvac_mode` - Current mode (HEAT/OFF)
- `hvac_action` - Current action (HEATING/IDLE/OFF)

**Async Methods:**
- `async_set_temperature()` - Sets target and triggers valve control
- `async_set_hvac_mode()` - Changes mode and coordinates with main climate
- `async_update()` - Calculates aggregated temperature and HVAC action
- `_async_control_valves()` - Main valve control logic with parallel execution
- `_async_get_valve_states()` - Reads current valve states
- `_async_turn_off_all_valves()` - Safely turns off valves

### MultizoneHeaterConfigFlow (config_flow.py)

**Steps:**
1. `async_step_user()` - Main settings configuration
2. `async_step_add_zone()` - Add zones one by one

**Features:**
- Multi-step wizard
- Entity selectors for sensors and switches
- Validation and error handling
- Options flow for runtime configuration changes

## Configuration Storage

Configuration is stored in Home Assistant's config entries:

```python
{
    CONF_MAIN_CLIMATE: "climate.main_thermostat",  # Optional
    CONF_TEMPERATURE_AGGREGATION: "average",        # average/minimum/maximum
    CONF_MIN_VALVES_OPEN: 1,                       # Safety minimum
    CONF_ZONES: [
        {
            CONF_ZONE_NAME: "Living Room",
            CONF_TEMPERATURE_SENSOR: "sensor.living_room_temp",
            CONF_VALVE_SWITCH: "switch.living_room_valve",
            CONF_TARGET_TEMP_OFFSET: 0.5
        },
        # ... more zones
    ]
}
```

## Safety Mechanisms

1. **Minimum Valves Open**: Prevents pump damage by ensuring at least N valves stay open
2. **Async Locking**: Prevents race conditions during valve updates
3. **State Validation**: Handles unavailable/unknown sensor states gracefully
4. **Deadband Logic**: Prevents rapid cycling near target temperature
5. **Main Climate Coordination**: Optional coordination prevents conflicts

## Integration Lifecycle

```
Installation
    │
    ▼
Config Flow (UI Setup)
    │
    ▼
async_setup_entry()
    ├─► Create device entry
    ├─► Load configuration
    └─► Setup climate platform
        │
        ▼
    MultizoneHeaterClimate.__init__()
        │
        ▼
    async_added_to_hass()
        ├─► Register state change listeners
        └─► Initial update
            │
            ▼
        Running (Event-Driven)
        ├─► Temperature changes → Update & Control Valves
        ├─► User commands → Execute Actions
        └─► Main climate changes → Sync State
            │
            ▼
    Unload/Reload
    └─► async_unload_entry()
        └─► Cleanup listeners and resources
```

## Performance Characteristics

- **Response Time**: Sub-second for temperature changes
- **Valve Control**: Parallel execution (all valves update simultaneously)
- **Memory Usage**: Minimal (single climate entity, cached states)
- **CPU Usage**: Event-driven (only processes when changes occur)
- **Scalability**: O(n) for n zones, with parallel execution

## Future Enhancement Areas

While not currently implemented, the architecture supports:

- Zone prioritization
- PID temperature control
- Predictive heating based on weather
- Energy usage tracking
- Per-zone scheduling
- Window/door sensors integration
