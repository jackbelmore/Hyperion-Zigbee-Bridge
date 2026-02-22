# System Architecture

## Overview

Hyperion-Zigbee-Bridge is a real-time color synchronization system that bridges screen capture data with smart light control.

```
┌─────────────────────────────────────────────────────────────────┐
│                          System Architecture                     │
└─────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │  Hyperion.NG    │
                         │  (Screen Color  │
                         │   Capture)      │
                         └────────┬────────┘
                                  │
                         (WebSocket JSON-RPC)
                                  │
                    ┌─────────────▼──────────────┐
                    │  Bridge Process            │
                    │  (hyperion_zigbee_bridge)  │
                    │                            │
                    │  ┌──────────────────────┐  │
                    │  │  Color Processor     │  │
                    │  │  • RGB→XY conversion │  │
                    │  │  • Warmth algorithm  │  │
                    │  │  • Throttling logic  │  │
                    │  └──────────────────────┘  │
                    │                            │
                    │  ┌──────────────────────┐  │
                    │  │  Config Manager      │  │
                    │  │  • Device mapping    │  │
                    │  │  • Hot reload        │  │
                    │  └──────────────────────┘  │
                    └─────────────┬──────────────┘
                                  │
                         (MQTT Publish)
                                  │
                    ┌─────────────▼──────────────┐
                    │   Mosquitto Broker         │
                    │   (Port: 1883)             │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Zigbee2MQTT             │
                    │   (Device Bridge)         │
                    └─────────────┬──────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           │                      │                      │
      ┌────▼────┐           ┌────▼────┐           ┌────▼────┐
      │ Zigbee  │           │ Zigbee  │           │ Zigbee  │
      │ LED     │           │ Desk    │           │ Aqara   │
      │ Strip   │           │ Light   │           │ Ceiling │
      └────┬────┘           └────┬────┘           └────┬────┘
           │                      │                      │
           └──────────────────────┼──────────────────────┘
```

## Component Architecture

### 1. **Hyperion Integration**
- **Protocol:** WebSocket (JSON-RPC)
- **Port:** 8090
- **Purpose:** Receives ambient color data from screen capture
- **Interface:** `websocket.WebSocketApp`
- **Data Format:** JSON messages with RGB color values

### 2. **Color Processing Pipeline**

#### RGB→XY Color Space Conversion
```
RGB (8-bit: 0-255)
    ↓
[Normalize to 0-1 range]
    ↓
[Apply gamma correction]
    ↓
[Matrix transform to XY]
    ↓
XY Color Space (Zigbee standard)
    ↓
[Publish to MQTT]
```

**Why:** Zigbee devices use CIE 1931 XY color space, not RGB. Conversion ensures compatibility across different light brands.

#### Deep Warmth Algorithm
- Shifts detected colors toward orange/red spectrum
- Formula: Adjusts hue angle and saturation based on `color_warmth` parameter
- Purpose: Creates cozy ambient lighting effect

#### Throttling Mechanism
- **Problem:** Publishing every color change (60+ FPS) overwhelms MQTT broker
- **Solution:** Configurable `throttle_interval` (default: 0.6s)
- **Implementation:** Thread-safe deque + timestamp comparison
- **Benefit:** Smooth visual effect + reduced network load

### 3. **MQTT Bridge**
- **Broker:** Mosquitto (port 1883)
- **Protocol:** MQTT v3.1.1
- **Connection:** Persistent, with automatic reconnect
- **Topics:** One per light device (configurable)
- **Message Format:** JSON with device-specific commands

**Example MQTT Message:**
```json
{
  "xy": [0.3, 0.4],
  "brightness": 254,
  "transition": 0.1
}
```

### 4. **Dashboard UI**
- **Framework:** CustomTkinter (modern tkinter wrapper)
- **Architecture:** MVC pattern
  - **Model:** `Config` (device list, settings)
  - **View:** Vaporwave UI components (CTkButton, CTkSlider, etc.)
  - **Controller:** Event handlers for user interactions

**Key Components:**
- `PulseButton` - Animated status indicators
- `RainbowArcadeButton` - Colorful preset scene buttons
- `VaporwaveColorPicker` - Custom color wheel
- Real-time config synchronization

### 5. **Configuration Management**
- **Format:** JSON (`bridge_config.json`)
- **Hot Reload:** Detects file changes and reloads without restarting
- **Validation:** Device topics, MQTT broker address, Hyperion URL
- **Fallbacks:** Sensible defaults for all parameters

## Data Flow

### Normal Operation Flow

```
1. Hyperion captures screen (30 FPS)
   ↓
2. WebSocket sends RGB color to bridge
   ↓
3. Bridge receives message in ws_on_message()
   ↓
4. Color added to processing queue
   ↓
5. Background thread checks throttle_interval
   ↓
6. If time elapsed:
   a) Apply warmth algorithm (if enabled)
   b) Convert RGB→XY
   c) Calculate brightness
   ↓
7. MQTT publishes to each enabled device
   ↓
8. Zigbee2MQTT sends command to device
   ↓
9. Physical light changes color
   (Typical latency: 100-300ms)
```

### User-Initiated Control Flow

```
User interacts with Dashboard
   ↓
Button/Slider event triggered
   ↓
Manual control handler called
   ↓
Direct MQTT publish (no Hyperion sync)
   ↓
Zigbee device updates
```

## Threading Model

### Thread Safety

- **Main Thread:** UI event loop (CustomTkinter)
- **WebSocket Thread:** Hyperion connection (websocket library)
- **MQTT Thread:** Broker connection (paho-mqtt)
- **Color Processing:** Queue-based (thread-safe deque)

**Synchronization:**
- No locks needed; uses queue-based message passing
- Each thread owns its connection
- Shared state (config) is read-only after startup

## Error Handling & Resilience

### Connection Management
- Automatic reconnection on WebSocket disconnect
- MQTT broker reconnection with exponential backoff
- Graceful fallback if Hyperion unavailable
- Status indicators in UI

### Data Validation
- Device topic validation
- RGB value bounds checking (0-255)
- XY coordinate validation
- MQTT payload size limits

## Performance Characteristics

| Metric | Target | Implementation |
|--------|--------|-----------------|
| Color latency | <300ms | Throttle + direct MQTT |
| Memory footprint | <50MB | Efficient UI + config caching |
| CPU usage | <3% idle | Event-driven, no polling |
| MQTT bandwidth | <1MB/day | Throttling at 0.6s intervals |

## Extension Points

### Adding Support for New Light Types

1. **Create new device class** in config:
   ```json
   {
     "name": "New Light",
     "topic": "zigbee2mqtt/NewLight/set",
     "type": "rgb",
     "brightness_multiplier": 1.0
   }
   ```

2. **Update Zigbee2MQTT** with device definition
3. **Test with dashboard** - no code changes needed

### Custom Color Algorithms

- Modify `apply_warmth()` function in `hyperion_zigbee_bridge.py`
- Add new parameter to config
- Reload bridge to apply

### UI Themes

- Modify `THEME` dictionary in `hyperion_vaporwave.py`
- Update colors, fonts, layouts
- No backend changes needed

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Capture** | Hyperion.NG | Screen color detection |
| **Transport** | WebSocket (Hyperion) + MQTT (Zigbee) | Async data transfer |
| **Processing** | Python 3.10+ | Color math, threading |
| **UI** | CustomTkinter | Modern desktop dashboard |
| **Devices** | Zigbee2MQTT | Smart light control |
| **Broker** | Mosquitto | MQTT message routing |

## Security Considerations

- MQTT credentials stored in local config (not version controlled)
- `.gitignore` prevents accidental credential commits
- WebSocket connection to Hyperion (local, no auth required)
- No external API keys or tokens

## Future Architecture Improvements

1. **Database** - Store light history, create automation scenes
2. **REST API** - Allow remote control via HTTP
3. **Machine Learning** - Learn preferred lighting based on activity
4. **Voice Control** - Alexa/Google Home integration
5. **Mobile App** - React Native companion app
