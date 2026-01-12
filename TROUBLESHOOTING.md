# Troubleshooting Guide

## Issue: Climate Entity Visible in UI

**Problem:** The integration shows a climate entity in the UI, but you want to see only sensors.

**Solution (as of v1.0.1):** The climate entity is now hidden by default. It still runs in the background to control valves and update the main climate, but won't appear in your dashboards unless you manually enable it.

To verify:
1. Go to **Settings → Devices & Services**
2. Find the Multizone Heater integration
3. Click on it to see the device
4. The climate entity should be disabled by default
5. You should see only the sensor entities

If you need to interact with the climate entity directly:
1. Go to **Settings → Entities**
2. Search for your multizone heater
3. Find the climate entity (it will be disabled)
4. Click on it and enable it

## Issue: Main Climate Not Updating

**Problem:** The "Main Target Temperature" sensor shows the correct calculated value, but your actual main climate entity (boiler/thermostat) is not being updated to that temperature.

**Possible Causes and Solutions:**

### 1. HVAC Mode is OFF
The integration only updates the main climate when its HVAC mode is set to HEAT or COOL.

**Check:**
- Is the integration's HVAC mode set to HEAT or COOL?
- Go to the climate entity (if enabled) or check the mode

**Solution:**
- Set the integration to HEAT or COOL mode
- The main climate will be updated immediately

### 2. Change Threshold
The integration has a change threshold (default 0.1°C) to avoid excessive updates.

**Check the logs:**
```yaml
logger:
  default: info
  logs:
    custom_components.multizone_heater: debug
```

Look for messages like:
- `"Updating main climate..."` - Update is happening
- `"Skipping main climate update: current=X, desired=Y, change=Z"` - Update skipped due to threshold

**Solution:**
If updates are being skipped unnecessarily, you can adjust the threshold in the integration configuration.

### 3. Main Climate Entity Issues
The main climate entity might not be responding to service calls.

**Check:**
1. Can you manually set the temperature on your main climate entity?
2. Try calling the service manually:
   ```yaml
   service: climate.set_temperature
   target:
     entity_id: climate.your_main_climate
   data:
     temperature: 22
   ```

**Solution:**
- Ensure your main climate entity is working properly
- Check for errors in the Home Assistant logs
- Verify the entity_id is correct in the integration configuration

### 4. Service Call Failures
The integration might be failing to call the service.

**Check the logs for:**
- `"Failed to set main climate temperature..."` - Service call failed
- `"Main climate update service call succeeded"` - Service call worked

**Solution:**
- Review error messages in the logs
- Ensure the main climate entity supports `climate.set_temperature` service
- Check entity permissions

## Issue: Incorrect Main Target Calculation

**Problem:** The main target temperature sensor shows an unexpected value (e.g., 19.5°C instead of 21.25°C).

The calculation logic has been thoroughly tested and is correct. If you're seeing an unexpected value, it's likely due to:

### 1. Zones Not Satisfied
Zones might not be within the "satisfied" bounds.

**Understanding Satisfaction Bounds:**
In HEATING mode, a zone is satisfied when:
```
target - opening_offset <= current_temp <= target + closing_offset
```

Example:
- Zone target: 20°C
- Opening offset: 0.5°C
- Closing offset: 0.0°C
- Satisfied range: 19.5°C to 20.0°C

If current temp is:
- 19.4°C → Underheated (needs heat)
- 19.6°C → Satisfied
- 20.1°C → Overheated (needs action to cool down)

**Check the logs:**
```
Zone ZoneName: current=X°C, target=Y°C, bounds=[A, B]°C, needs_action=True/False
```

**Solution:**
- Review actual zone temperatures vs targets
- Check your offset configuration
- Zones outside bounds will use compensation-based calculation

### 2. Different Zone Targets
The zone target temperatures might be different from what you expect.

**Check the logs:**
```
Main target calculation complete: desired=X°C, is_holding=True/False, zones_needing_action=N, zone_targets=[20.0, 22.5, ...]
```

The `zone_targets` list shows all targets being used in the calculation.

**Possible causes:**
- Zone climate entities have different targets set
- Some zones without climate entities use the multizone heater's default target

**Solution:**
- Verify each zone climate entity's target temperature
- Set targets explicitly on each zone climate entity

### 3. Zones Without Valves
Zones without valve configuration are excluded from the main target calculation.

**Check the logs:**
```
Skipping zone ZoneName: no valve configured
```

**Solution:**
- Ensure all zones that should affect the main target have a valve configured
- Zones without valves won't influence the main climate target

### 4. Configuration Values
Check your configuration values.

**Check:**
- Main min/max temperature: Default 18.0-30.0°C
  - If min_temp is 19.5°C, values below will be clamped
- All Satisfied Mode slider: Default 50% (average)
  - 0% = minimum target
  - 50% = average target  
  - 100% = maximum target
- Compensation factor: Default 0.66

**Solution:**
- Review configuration in the integration settings
- Adjust if needed

### 5. Overheated Zones
If zones are overheated (temperature > target + closing_offset), they still trigger "needs action" and use compensation calculation, not holding mode.

**Check the logs:**
```
Zone ZoneName: current=20.5°C, target=20.0°C, bounds=[19.5, 20.0]°C, needs_action=True
```

If closing_offset is 0.0, even 0.1°C above target counts as overheated.

**Solution:**
- Increase closing_offset to create a wider satisfaction range
- This prevents zones from constantly switching between satisfied/overheated

## Enabling Debug Logging

To diagnose issues, enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.multizone_heater: debug
```

After making this change:
1. Restart Home Assistant or reload the logger configuration
2. Wait for the integration to run (5-30 seconds)
3. Check the logs in **Settings → System → Logs**

You should see detailed information about:
- Zone temperatures and targets
- Satisfaction bounds for each zone
- Which zones need action
- Calculated main target
- Main climate update attempts and results

## Example Debug Log Analysis

### Good Scenario (All zones satisfied)
```
Zone Living Room: current=20.2°C, target=20.0°C, bounds=[19.5, 20.5]°C, needs_action=False
Zone Bedroom: current=22.3°C, target=22.5°C, bounds=[22.0, 23.0]°C, needs_action=False
Main target calculation complete: desired=21.2°C, is_holding=True, zones_needing_action=0, zone_targets=[20.0, 22.5]
Coordinator calculated main_target=21.2°C, is_holding=True from 2 zones (slider=50%)
Updating main climate climate.boiler from 21.0°C to 21.2°C (change 0.2°C)
Main climate update service call succeeded
```

### Problem Scenario (Zone overheated)
```
Zone Living Room: current=20.5°C, target=20.0°C, bounds=[19.5, 20.0]°C, needs_action=True
Zone Bedroom: current=22.3°C, target=22.5°C, bounds=[22.0, 23.0]°C, needs_action=False
Main target calculation complete: desired=19.7°C, is_holding=False, zones_needing_action=1, zone_targets=[20.0, 22.5]
```

Analysis: Living room is overheated (20.5 > 20.0 upper bound), so it needs action.
With compensation: 20.0 + 0.66 * (20.0 - 20.5) = 20.0 - 0.33 = 19.67 ≈ 19.7°C

**Solution:** Increase closing_offset for zones to create wider satisfaction range.

## Getting Help

If you're still experiencing issues after reviewing this guide:

1. Enable debug logging
2. Collect logs showing:
   - Zone calculations
   - Main target calculations
   - Main climate update attempts
3. Post in the GitHub issues with:
   - Your configuration
   - The log excerpts
   - What you expected vs what happened
