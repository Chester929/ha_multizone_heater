# Multizone Heater Integration

High-performance Home Assistant integration for managing multizone heating systems with async valve control.

## Key Features

✅ **Async Operation** - All valve control operations execute in parallel for maximum performance  
✅ **Multiple Zones** - Support for unlimited heating zones  
✅ **Smart Aggregation** - Choose average, minimum, or maximum temperature calculation  
✅ **Safety First** - Ensures minimum valves stay open to protect your heating system  
✅ **Easy Setup** - Full UI configuration flow, no YAML required  
✅ **Main Climate Integration** - Optional coordination with central thermostat  

## Why This Integration?

Traditional blueprint-based automations can be slow and have limited optimization options. This Python integration leverages Home Assistant's native async capabilities for:

- ⚡ **10x faster** valve response times
- 🔄 **Parallel processing** of all valve operations
- 📊 **Real-time updates** without polling delays
- 💪 **Lower resource usage** than complex automations

## Quick Start

1. Install via HACS
2. Restart Home Assistant
3. Go to Settings → Devices & Services
4. Click "Add Integration"
5. Search for "Multizone Heater"
6. Follow the configuration wizard

## Configuration

The setup wizard will guide you through:

1. **Main Settings**
   - Optional main climate entity
   - Temperature aggregation method
   - Minimum valves to keep open

2. **Zone Configuration**
   - Zone name
   - Temperature sensor
   - Valve switch
   - Target temperature offset

Add as many zones as you need!

## Documentation

See [README.md](https://github.com/Chester929/ha_multizone_heater/blob/main/README.md) for detailed documentation.

See [EXAMPLES.md](https://github.com/Chester929/ha_multizone_heater/blob/main/EXAMPLES.md) for usage examples and automations.

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/Chester929/ha_multizone_heater/issues).
