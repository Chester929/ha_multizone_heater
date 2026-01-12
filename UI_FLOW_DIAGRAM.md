# UI Flow Diagram

This document shows the navigation flow of the enhanced zone management UI.

## Initial Setup Flow

```
Start Integration Setup
         |
         v
┌─────────────────────────────────────┐
│   Step 1: Main Settings             │
│                                     │
│  • Main Climate Entity              │
│  • Main Temp Sensor Override        │
│  • Min Valves Open                  │
│  • Compensation Factor              │
│  • Valve Transition Delay           │
│  • Main Min/Max Temp                │
│  • Main Change Threshold            │
│  • Physical Close Anticipation      │
│  • All Satisfied Mode (slider)      │
└─────────────────────────────────────┘
         |
         v
┌─────────────────────────────────────┐
│   Step 2: Add Zones                 │
│                                     │
│  • Zone Name                        │
│  • Zone Climate Entity (required)   │
│  • Physical Valve Switch            │
│  • Virtual Switch                   │
│  • Opening Offset Below Target      │
│  • Closing Offset Above Target      │
│  • [✓] Add Another Zone             │
└─────────────────────────────────────┘
         |
         |--- [Add Another checked] --->┐
         |                               |
         v                               |
    [Continue]                           |
         |                               |
         |<------------------------------┘
         v
┌─────────────────────────────────────┐
│   Step 3: Fallback Zones            │
│                                     │
│  Select zones to remain open:       │
│  [ ] Zone 1                         │
│  [✓] Zone 2                         │
│  [✓] Zone 3                         │
│                                     │
│  At least one required              │
└─────────────────────────────────────┘
         |
         v
    Integration Created!
```

## Options Flow (After Setup)

```
Configure Integration
         |
         v
┌─────────────────────────────────────┐
│   Configuration Menu                │
│                                     │
│  Choose what to configure:          │
│                                     │
│  • Global Settings                  │
│  • Manage Zones                     │
└─────────────────────────────────────┘
         |
         |
    ┌────┴────┐
    |         |
    v         v
┌─────┐   ┌──────┐
│  A  │   │  B   │
└─────┘   └──────┘

A: Global Settings Path
═══════════════════════

┌─────────────────────────────────────┐
│   Global Settings                   │
│                                     │
│  • Min Valves Open                  │
│  • Compensation Factor              │
│  • Valve Transition Delay           │
│  • Main Min/Max Temp                │
│  • Main Change Threshold            │
│  • Physical Close Anticipation      │
│  • All Satisfied Mode (slider)      │
│                                     │
│  [Save]  [Cancel]                   │
└─────────────────────────────────────┘
         |
         v
    Settings Updated!


B: Manage Zones Path
════════════════════

┌─────────────────────────────────────┐
│   Zone Management Menu              │
│                                     │
│  Choose an action:                  │
│                                     │
│  • Add New Zone                     │
│  • Edit Existing Zone               │
│  • Remove Zone                      │
│  • Configure Fallback Zones         │
└─────────────────────────────────────┘
         |
    ┌────┼────┬────────┬────────┐
    |    |    |        |        |
    v    v    v        v        v
   B1   B2   B3       B4       B5


B1: Add New Zone
────────────────

┌─────────────────────────────────────┐
│   Add New Zone                      │
│                                     │
│  Zone Name: [____________]          │
│  Zone Climate: [dropdown v]         │
│  Valve Switch: [dropdown v]         │
│  Virtual Switch: [dropdown v]       │
│  Opening Offset: [0.3]              │
│  Closing Offset: [0.3]              │
│                                     │
│  Currently configured zones: 2      │
│                                     │
│  [Add Zone]  [Cancel]               │
└─────────────────────────────────────┘
         |
         v
    Zone Added!
         |
         v
   Back to Zone Management Menu


B2: Edit Existing Zone
──────────────────────

┌─────────────────────────────────────┐
│   Select Zone to Edit               │
│                                     │
│  Zone: [Living Room    v]           │
│        [Bedroom       ]             │
│        [Kitchen       ]             │
│                                     │
│  [Continue]  [Cancel]               │
└─────────────────────────────────────┘
         |
         v
┌─────────────────────────────────────┐
│   Edit Zone: Living Room            │
│                                     │
│  Zone Name: [Living Room____]       │
│  Zone Climate: [climate.lr v]       │
│  Valve Switch: [switch.lr v]        │
│  Virtual Switch: [switch.vr v]      │
│  Opening Offset: [0.5]              │
│  Closing Offset: [0.2]              │
│                                     │
│  [Save Changes]  [Cancel]           │
└─────────────────────────────────────┘
         |
         v
    Zone Updated!
         |
         v
   Back to Zone Management Menu


B3: Remove Zone
───────────────

┌─────────────────────────────────────┐
│   Remove Zone                       │
│                                     │
│  Zone to Remove: [Kitchen    v]     │
│                  [Bedroom   ]       │
│                  [Living Rm ]       │
│                                     │
│  Note: Cannot remove last zone      │
│                                     │
│  [Remove]  [Cancel]                 │
└─────────────────────────────────────┘
         |
         v
    Zone Removed!
    (Fallback zones auto-updated)
         |
         v
   Back to Zone Management Menu


B4: Configure Fallback Zones
─────────────────────────────

┌─────────────────────────────────────┐
│   Configure Fallback Zones          │
│                                     │
│  Select zones to keep open:         │
│                                     │
│  [✓] Living Room                    │
│  [ ] Bedroom                        │
│  [✓] Kitchen                        │
│                                     │
│  At least one required              │
│                                     │
│  [Save]  [Cancel]                   │
└─────────────────────────────────────┘
         |
         v
    Fallback Zones Updated!
         |
         v
   Back to Zone Management Menu
```

## Key UI Elements

### Selectors Used

1. **EntitySelector** - For choosing entities (climate, switch, sensor)
   - Filters by domain (e.g., only climate entities)
   - Shows friendly names
   - Provides entity search

2. **NumberSelector (Box Mode)** - For precise numeric values
   - Min/max constraints
   - Step increments
   - Unit display (°C, seconds)

3. **NumberSelector (Slider Mode)** - For percentage values
   - Visual slider
   - 0-100 range
   - Real-time preview

4. **SelectSelector (Dropdown)** - For single selection
   - Zone selection for edit/remove
   - Clean interface

5. **SelectSelector (List)** - For multiple selection
   - Fallback zones selection
   - Shows all options
   - Multi-select checkboxes

### Validation Points

```
User Input Validation
         |
         v
┌─────────────────────────────────────┐
│  Validation Checks                  │
│                                     │
│  ✓ Zone climate is required         │
│  ✓ Valve + Virtual switch paired    │
│  ✓ No duplicate entities            │
│  ✓ Temperature range valid          │
│  ✓ At least one fallback zone       │
│  ✓ Cannot remove last zone          │
└─────────────────────────────────────┘
         |
         |--- [Validation Failed] --->┐
         |                             |
         v                             v
    [Accept]                    [Show Error]
         |                             |
         v                             |
   Save to Config                      |
         |                             |
         v                             |
   Reload Integration                  |
         |                             |
         v                             |
    [Success]<-----------------------┘
                                 [Retry]
```

## User Journey Examples

### Journey 1: First-Time User

```
Install Integration
        ↓
Configure Main Settings (Step 1)
        ↓
Add First Zone (Step 2)
        ↓
Check "Add Another Zone"
        ↓
Add Second Zone (Step 2)
        ↓
Uncheck "Add Another Zone"
        ↓
Select Fallback Zones (Step 3)
        ↓
Integration Created ✓
```

### Journey 2: Existing User Adding Zone

```
Open Configuration
        ↓
Select "Manage Zones"
        ↓
Select "Add New Zone"
        ↓
Fill in zone details
        ↓
Save
        ↓
Zone Added ✓
        ↓
Optionally: Add to fallback zones
```

### Journey 3: Existing User Editing Zone

```
Open Configuration
        ↓
Select "Manage Zones"
        ↓
Select "Edit Existing Zone"
        ↓
Choose zone from dropdown
        ↓
Modify settings
        ↓
Save Changes
        ↓
Zone Updated ✓
```

## Mobile vs Desktop Experience

The UI is fully responsive and works on both mobile and desktop:

**Mobile**:
- Full-screen dialogs
- Large touch targets
- Scrollable forms
- Native keyboard for inputs

**Desktop**:
- Modal dialogs
- Compact forms
- Mouse/keyboard navigation
- Hover tooltips

**Both**:
- Same functionality
- Same validation
- Same visual design
- Theme-aware (light/dark mode)
