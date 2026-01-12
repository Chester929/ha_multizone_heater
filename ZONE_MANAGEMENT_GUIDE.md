# Zone Management UI Improvements

This document describes the enhanced zone management UI introduced in version 1.1.0 of the Multizone Heater integration.

## Overview

The integration now features a modern, menu-based configuration interface that allows dynamic management of heating zones at any time after the initial setup.

## Key Features

### 1. Menu-Based Options Flow

When you configure the integration (Settings → Devices & Services → Multizone Heater → Configure), you now see a clear menu with two options:

- **Global Settings**: Configure system-wide parameters
- **Manage Zones**: Add, edit, remove zones and configure fallback zones

### 2. Dynamic Zone Management

#### Add New Zones
- Navigate to: Configure → Manage Zones → Add New Zone
- Fill in zone details:
  - Zone Name
  - Zone Climate Entity
  - Physical Valve Switch (optional)
  - Virtual Switch (optional)
  - Temperature offsets
- Zones can be added at any time without recreating the integration

#### Edit Existing Zones
- Navigate to: Configure → Manage Zones → Edit Existing Zone
- Select the zone you want to modify
- Update any field (name, entities, offsets)
- Changes take effect immediately

#### Remove Zones
- Navigate to: Configure → Manage Zones → Remove Zone
- Select the zone to remove
- Safety check: Cannot remove the last zone
- Fallback zones are automatically updated if a removed zone was configured as fallback

#### Manage Fallback Zones
- Navigate to: Configure → Manage Zones → Configure Fallback Zones
- Select which zones should remain open when all zones are satisfied
- At least one fallback zone must be selected for pump safety

### 3. Enhanced User Experience

#### Clear Navigation
- Intuitive menu structure
- Descriptive titles and help text
- Step-by-step guidance

#### Dynamic Information
- Live zone count during configuration
- Helpful tips and placeholders
- Clear validation messages

#### Safety Features
- Duplicate entity detection across all zones
- Automatic fallback zone management
- Validation at each step
- Cannot remove the last zone

## Migration from Previous Versions

Existing configurations are fully compatible. No action required.

When you first open the configuration after upgrading:
1. You'll see the new menu interface
2. All your zones and settings are preserved
3. You can immediately start using the new zone management features

## Configuration Workflow Examples

### Example 1: Adding a New Zone to Existing Setup

**Scenario**: You have 2 zones configured and want to add a 3rd zone for a new room.

**Steps**:
1. Go to Settings → Devices & Services
2. Find "Multizone Heater" and click "Configure"
3. Select "Manage Zones"
4. Select "Add New Zone"
5. Enter details for the new zone:
   - Zone Name: "New Room"
   - Zone Climate: climate.new_room
   - (Configure valves if using)
6. Save
7. Optionally add the new zone to fallback zones via "Configure Fallback Zones"

**Result**: New zone is immediately active in the integration.

### Example 2: Updating Zone Temperature Offsets

**Scenario**: You want to fine-tune the opening/closing temperature offsets for better comfort.

**Steps**:
1. Go to Settings → Devices & Services
2. Find "Multizone Heater" and click "Configure"
3. Select "Manage Zones"
4. Select "Edit Existing Zone"
5. Choose the zone to modify
6. Adjust "Opening Offset Below Target" or "Closing Offset Above Target"
7. Save

**Result**: New offsets are applied immediately.

### Example 3: Removing a Zone

**Scenario**: You've removed radiators from a room and no longer need that zone.

**Steps**:
1. Go to Settings → Devices & Services
2. Find "Multizone Heater" and click "Configure"
3. Select "Manage Zones"
4. Select "Remove Zone"
5. Choose the zone to remove
6. Confirm

**Result**: Zone is removed. If it was a fallback zone, the fallback zones list is automatically updated.

### Example 4: Changing Global Settings

**Scenario**: You want to adjust the compensation factor after monitoring system performance.

**Steps**:
1. Go to Settings → Devices & Services
2. Find "Multizone Heater" and click "Configure"
3. Select "Global Settings"
4. Adjust "Compensation Factor" (e.g., from 0.66 to 0.75)
5. Save

**Result**: New compensation factor is applied to all zones.

## UI Components Used

The integration uses Home Assistant's native UI components:

- **Menu Selector**: For main navigation
- **Entity Selector**: For choosing climate entities, switches, sensors
- **Number Selector (Box)**: For precise numeric inputs
- **Number Selector (Slider)**: For intuitive percentage-based inputs
- **Select Selector (Dropdown)**: For choosing zones to edit/remove
- **Select Selector (List)**: For multi-select fallback zones

These components provide:
- Consistent look and feel with Home Assistant
- Native accessibility support
- Responsive design for mobile devices
- Theme compatibility (light/dark mode)

## Benefits Over Previous Version

| Feature | Before | After |
|---------|--------|-------|
| Add zones | Only during initial setup | Anytime via options flow |
| Edit zones | Manual YAML or recreate integration | Direct UI editing |
| Remove zones | Manual YAML or recreate integration | One-click removal |
| Fallback zones | Set once during setup | Update anytime |
| Navigation | Single long form | Organized menu system |
| Help text | Static descriptions | Dynamic tips and placeholders |

## Technical Details

### Configuration Storage

- All configuration is stored in Home Assistant's config entry data
- Changes update the config entry immediately
- Integration reloads automatically when configuration changes
- No YAML files required

### Validation

The enhanced UI includes comprehensive validation:
- Zone climate entity is required
- Physical valve and virtual switch must be paired
- Duplicate entities are detected across all zones
- Temperature ranges are validated
- At least one fallback zone must be selected
- Cannot remove the last zone

### Backward Compatibility

The changes are fully backward compatible:
- Existing configurations load without modification
- Old-style options flow still works (redirects to new menu)
- No breaking changes to stored configuration format

## Troubleshooting

### Menu Not Appearing

If you don't see the new menu interface:
1. Ensure you're running version 1.1.0 or later
2. Clear your browser cache
3. Restart Home Assistant to reload translations

### Cannot Edit Zones

If the "Edit Existing Zone" option is disabled:
- This means no zones are configured
- Add at least one zone first via "Add New Zone"

### Changes Not Saving

If configuration changes don't persist:
1. Check Home Assistant logs for errors
2. Ensure you have write permissions to the config directory
3. Verify the integration is not in a disabled state

### Fallback Zones Error

If you cannot save fallback zones:
- At least one fallback zone must be selected
- Ensure the zones you're selecting still exist
- Try removing and re-adding fallback zones

## Future Enhancements

Potential future improvements to the zone management UI:
- Bulk zone import/export
- Zone templates for common configurations
- Zone grouping for easier management
- Visual zone status dashboard
- Configuration validation before save

## Related Documentation

- [README.md](README.md) - Main integration documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting guide
- [EXAMPLES.md](EXAMPLES.md) - Configuration examples
