# Next Steps for Testing

## What Was Fixed

This update addresses all three issues you reported:

1. ✅ **Climate entity hidden** - Only sensors visible in UI by default
2. ✅ **Main climate updates improved** - More reliable updates with better logging
3. ✅ **Calculation debugging** - Tools to diagnose the 19.5°C issue

## How to Test

### 1. Update Your Installation

```bash
# If using HACS, update the integration
# Or manually copy the updated files to your custom_components directory
```

### 2. Restart Home Assistant

After updating, restart Home Assistant completely.

### 3. Verify Climate Entity is Hidden

1. Go to **Settings → Devices & Services**
2. Find **Multizone Heater** integration
3. Click on the device
4. You should see only **sensor entities** (no climate entity by default)
5. The sensors should include:
   - Main Target Temperature
   - Per-zone targets, current temperatures, and valve states

### 4. Enable Debug Logging

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.multizone_heater: debug
```

Then reload the logger or restart Home Assistant.

### 5. Monitor the Logs

Go to **Settings → System → Logs** and look for messages from `custom_components.multizone_heater`.

You should see messages like:

```
DEBUG (MainThread) [custom_components.multizone_heater.climate] Zone Living Room: current=20.2°C, target=20.0°C, bounds=[19.5, 20.5]°C, needs_action=False
DEBUG (MainThread) [custom_components.multizone_heater.climate] Zone Bedroom: current=22.3°C, target=22.5°C, bounds=[22.0, 23.0]°C, needs_action=False
DEBUG (MainThread) [custom_components.multizone_heater.climate] Main target calculation complete: desired=21.2°C, is_holding=True, zones_needing_action=0, zone_targets=[20.0, 22.5]
DEBUG (MainThread) [custom_components.multizone_heater.coordinator] Coordinator calculated main_target=21.2°C, is_holding=True from 2 zones (slider=50%)
INFO (MainThread) [custom_components.multizone_heater.climate] Updating main climate climate.your_boiler from 21.0°C to 21.2°C (change 0.2°C)
DEBUG (MainThread) [custom_components.multizone_heater.climate] Main climate update service call succeeded
```

### 6. Check Issue #3 (19.5°C Calculation)

Look at the debug logs to find:

**A) What zone targets are being used:**
```
Main target calculation complete: ... zone_targets=[X, Y, Z]
```

**B) Whether zones are satisfied:**
```
Zone X: current=A°C, target=B°C, bounds=[C, D]°C, needs_action=True/False
```

**C) What the slider is set to:**
```
Coordinator calculated main_target=X°C, is_holding=Y from Z zones (slider=N%)
```

**D) Final calculated value:**
```
Coordinator calculated main_target=19.5°C, is_holding=True from 3 zones (slider=50%)
```

### 7. Diagnose the 19.5°C Issue

Based on the logs, check:

1. **Are all 3 zones being included?**
   - Look for 3 zone messages
   - Check if any zones are skipped (look for "Skipping zone" messages)

2. **What are the actual zone targets?**
   - Are they really 20.0, 21.25, and 22.5 as expected?
   - Or are they different?

3. **Are zones truly satisfied?**
   - Check if `needs_action=True` for any zone
   - If any zone needs action, it uses compensation mode, not holding mode

4. **What's the slider set to?**
   - Should be 50% for average
   - Check the actual value in logs

5. **What are the satisfaction bounds?**
   - With closing_offset=0.0, bounds are very tight
   - Example: target=20.0, bounds=[19.5, 20.0] - even 20.1°C is "overheated"

### 8. Common Causes of 19.5°C

Based on our analysis:

**Scenario A: Zone is overheated**
```
Zone Living Room: current=20.1°C, target=20.0°C, bounds=[19.5, 20.0]°C, needs_action=True
```
- Zone is 0.1°C above target → needs action (overheated)
- Uses compensation: 20.0 + 0.66 × (20.0 - 20.1) = 19.93°C
- If multiple zones are overheated, could produce ~19.5°C

**Solution:** Increase `closing_offset` to 0.3-0.5 to widen satisfaction range.

**Scenario B: Zone has different target**
```
zone_targets=[18.0, 20.0, 22.5]
```
- If one zone has target 18.0 instead of 20.0
- Average at 50% would be (18+20+22.5)/3 = 20.17°C, not 19.5°C
- But if min_temp is 19.5, it could clamp to 19.5

**Solution:** Check actual zone climate entity targets.

**Scenario C: Only 2 zones included**
```
Skipping zone Z: no valve configured
Main target calculation complete: ... zone_targets=[20.0, 19.0]
```
- If only 2 zones are used and one has target 19.0
- Average at 50% = (20.0 + 19.0) / 2 = 19.5°C ✓ This matches!

**Solution:** Ensure all zones have valves configured.

### 9. Verify Main Climate Updates (Issue #2)

Check for these INFO level messages:

```
INFO (MainThread) [custom_components.multizone_heater.climate] Updating main climate climate.your_boiler from 21.0°C to 21.2°C (change 0.2°C)
DEBUG (MainThread) [custom_components.multizone_heater.climate] Main climate update service call succeeded
```

If you don't see these messages:
- Check if integration HVAC mode is set to HEAT or COOL (not OFF)
- Verify main climate entity is available
- Look for error messages

### 10. Report Results

After testing, please share:

1. **Issue #1 (Climate entity):** 
   - Can you confirm climate entity is hidden?
   - Are sensors visible and working?

2. **Issue #2 (Main climate updates):**
   - Do you see "Updating main climate" messages?
   - Is your main climate entity actually being updated?

3. **Issue #3 (19.5°C calculation):**
   - What do the logs show for zone_targets?
   - Are zones satisfied or needs_action=True?
   - What's the slider setting?
   - Can you paste relevant log excerpts?

## Re-enabling Climate Entity (Optional)

If you want to see the climate entity:

1. Go to **Settings → Entities**
2. Search for your multizone heater
3. Find the climate entity (it will show as "Disabled")
4. Click on it
5. Click "Enable"
6. Refresh your dashboard

## Need Help?

See **TROUBLESHOOTING.md** for detailed diagnostic procedures and examples.

## Summary

✅ All three issues have been addressed
✅ Changes are minimal and backward compatible
✅ Comprehensive logging and documentation added
✅ Ready for testing

The logging will reveal exactly what's happening with your system and help diagnose the 19.5°C issue.
