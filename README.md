# Hyperion Zigbee Bridge & Command Center

A Vaporwave-styled dashboard and bridge to sync your Zigbee RGB lights (via Zigbee2MQTT) with Hyperion screen capture. Features real-time color synchronization, manual override controls, and a retro cyberpunk interface.

![Hyperion Command Center Dashboard](hyperion_dashboard.png)

## Features

- **🎨 Real-time Color Sync:** Automatically syncs Zigbee RGB lights with your screen content via Hyperion.NG ambient color capture
- **🔥 Deep Warmth Mode:** Intelligent color-shifting algorithm that transitions colors to deep orange/red tones for a cozy, warm atmosphere
- **🎛️ Hybrid Light Control:** Toggle individual lights between automatic sync and manual control modes
- **💡 Per-Light Brightness Control:** Adjust brightness multipliers for each light (0-100%, hardware max override)
- **🌈 Manual Override:** Full manual control when needed - set custom RGB colors, color temperature (CCT), or brightness
- **⚡ Preset Scenes:** Quick-access scene buttons (READ, DAY, MOVIE, NIGHT) with pre-configured color profiles
- **🎮 Vaporwave Dashboard:** Custom retro cyberpunk UI built with CustomTkinter featuring cyan/pink neon styling
- **📊 Real-time Status:** Visual indicators for bridge and Hyperion connection status
- **⚙️ Configurable Throttling:** Adjust color update frequency to balance responsiveness vs. MQTT load

## Prerequisites

- **Hyperion.NG** (Running on port 8090)
- **Zigbee2MQTT** (Mosquitto broker on port 1883)
- **Python 3.10+**

## Prerequisites

- **Hyperion.NG** (v0.13+) - Ambient lighting capture tool running on port 8090
- **Zigbee2MQTT** - Zigbee device bridge with Mosquitto MQTT broker on port 1883
- **Python 3.10+** - For running the dashboard and bridge
- **Zigbee RGB/CCT Lights** - Compatible devices (tested with Gledopto, Tradfri, Aqara)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jackbelmore/Hyperion-Zigbee-Bridge.git
   cd Hyperion-Zigbee-Bridge
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your setup:
   ```bash
   cp bridge_config.example.json bridge_config.json
   ```
   Edit `bridge_config.json` with your:
   - Zigbee2MQTT device topics
   - Hyperion WebSocket URL (default: ws://127.0.0.1:8090/json-rpc)
   - MQTT broker address and credentials (if needed)

## Quick Start

**Windows (Easiest):**
```bash
Double-click launch_hyperion.bat
```

**Command Line:**
```bash
python hyperion_command_center.py
```

### Dashboard Layout

**Left Sidebar:**
- **BRIDGE STATUS** - Connection status to Zigbee2MQTT
- **HYPERION STATUS** - Connection status to Hyperion.NG
- **Navigation Menu** - Dashboard, Manual Override, Settings
- **Arcade Mode** - Activates preset scene buttons
- **Initiate Link** - Manual device linking (if needed)

**Main Area - Light Control:**
- **Sync Toggle** - Enable/disable automatic color sync per light
- **Brightness Slider** - Adjust max brightness during sync mode
- **Brightness ⚠️ Badge** - Shows if light is at hardware max
- **Manual Color Control** - When light is disabled from sync (if applicable)

**Preset Scenes (Bottom):**
Quick-access buttons for pre-configured lighting scenes (READ, DAY, MOVIE, NIGHT)

### Configuration

Edit `bridge_config.json` to customize:

```json
{
    "hyperion_url": "ws://127.0.0.1:8090/json-rpc",
    "mqtt_broker": "127.0.0.1",
    "mqtt_port": 1883,
    "throttle_interval": 0.6,
    "color_warmth": 3.0,
    "devices": [
        {
            "name": "Desk Light",
            "topic": "zigbee2mqtt/Desk/set",
            "brightness_multiplier": 0.8,
            "type": "rgb"
        }
    ]
}
```

**Configuration Options:**
- `throttle_interval` - Seconds between color updates (lower = more responsive, higher = less MQTT traffic)
- `color_warmth` - Intensity of deep warmth mode (0.0 = off, 5.0+ = very warm)
- `brightness_multiplier` - Max brightness for this light (1.0 = 100%, 0.5 = 50%, -1 = hardware max)
- `type` - Light type: `rgb` (full color) or `cct` (color temperature only)

## License

MIT License - See LICENSE file for details.

## Support

For issues, feature requests, or questions, please open an issue on GitHub.

