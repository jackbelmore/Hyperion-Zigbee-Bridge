# Hyperion Zigbee Bridge & Command Center

A Vaporwave-styled dashboard and bridge to sync your Zigbee lights (via Zigbee2MQTT) with Hyperion screen capture.

![Vaporwave UI](https://via.placeholder.com/600x400?text=Hyperion+Command+Center)

## Features

- **Real-time Sync:** Syncs Zigbee RGB lights with your screen content via Hyperion.
- **Deep Warmth Mode:** Intelligent algorithm to shift colors to deep orange/red for a cozy atmosphere.
- **Hybrid Control:** Toggle individual lights between "Sync Mode" and "Manual Mode".
- **Manual Override:** Control brightness and color (RGB or Temp) for lights not currently syncing.
- **Retro UI:** A custom Vaporwave/Cyberpunk dashboard built with Tkinter.

## Prerequisites

- **Hyperion.NG** (Running on port 8090)
- **Zigbee2MQTT** (Mosquitto broker on port 1883)
- **Python 3.10+**

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/yourusername/Hyperion-Zigbee-Bridge.git
   cd Hyperion-Zigbee-Bridge
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Setup Config:
   Copy `bridge_config.example.json` to `bridge_config.json` and update with your device topics.

## Usage

**Launch the Command Center:**
Double-click `launch_hyperion.bat` or run:
```bash
python hyperion_command_center.py
```

### Dashboard Controls
- **Start System:** Launches the background bridge process.
- **Sync Config:** Enable/Disable lights for sync. Sliders control max brightness *during* sync.
- **Manual Control:** Control lights that are disabled in Sync Config.
- **Settings:** Adjust the "Warmth" intensity and sync throttle rate.

## Configuration

Edit `bridge_config.json` manually or via the UI.

```json
{
    "devices": [
        {
            "name": "Desk Light",
            "topic": "zigbee2mqtt/Desk/set",
            "brightness_multiplier": 1.0,
            "type": "rgb"
        }
    ]
}
```

- **type:** `rgb` or `cct` (for temperature-only lights).
- **brightness_multiplier:** `1.0` (100%), `0.5` (50%), or `-1` (Force Hardware Max).

## License

MIT
