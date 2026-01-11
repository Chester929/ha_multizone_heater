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
│  │  │  - Manages HVAC mode (Heat/Off)                    │  │  │
│  │  │  - Async valve control coordinator                 │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                         │                                 │  │
│  │                         │                                 │  │
│  │         ┌───────────────┴────────────────┐               │  │
│  │         │                                │               │  │
│  │         ▼                                ▼               │  │
│  │  ┌─────────────┐                 ┌─────────────┐        │  │
│  │  │ Temperature │                 │   Valve     │        │  │
│  │  │   Sensor    │◄───monitors────►│   Control   │        │  │
│  │  │  Tracking   │                 │   (Async)   │        │  │
│  │  └─────────────┘                 └─────────────┘        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │                    │
                          │                    │
          ┌───────────────┘                    └──────────────┐
          │                                                    │
          ▼                                                    ▼
┌──────────────────────┐                          ┌──────────────────────┐
│  Temperature Sensors │                          │    Valve Switches    │
│                      │                          │                      │
│  • Zone 1 Sensor     │                          │  • Zone 1 Valve      │
│  • Zone 2 Sensor     │                          │  • Zone 2 Valve      │
│  • Zone 3 Sensor     │                          │  • Zone 3 Valve      │
│  • ... (unlimited)   │                          │  • ... (unlimited)   │
└──────────────────────┘                          └──────────────────────┘
```

## Data Flow

### 1. Temperature Monitoring (Event-Driven)

```
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
        │   ├─► Turn off all valves (except min)
        │   └─► Turn off main climate (if configured)
        │
        └─► If Mode = HEAT
            ├─► Turn on main climate (if configured)
            └─► Control valves based on zone temps
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
