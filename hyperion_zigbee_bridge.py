#!/usr/bin/env python3
"""
Hyperion.NG to Zigbee2MQTT Bridge
Captures screen colors from Hyperion and synchronizes Zigbee lights with throttled updates.
"""

import json
import time
import threading
import random
import websocket
import paho.mqtt.client as mqtt
from collections import deque

import os

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_FILE = "C:\\Users\\Box\\bridge_config.json"
config = {}
last_config_load = 0

def load_config():
    """Load configuration from JSON file."""
    global config, last_config_load, mqtt_client
    try:
        # Check if file has changed
        current_mtime = os.path.getmtime(CONFIG_FILE)
        if current_mtime > last_config_load:
            with open(CONFIG_FILE, 'r') as f:
                new_config = json.load(f)
                config = new_config
                last_config_load = current_mtime
                print(f"[Config] Loaded settings from {CONFIG_FILE}")
                return True
    except FileNotFoundError:
        print(f"[Config] Error: {CONFIG_FILE} not found!")
    except Exception as e:
        print(f"[Config] Error loading config: {e}")
    return False

# Initial load
load_config()

# Hyperion WebSocket Configuration
HYPERION_WS_URL = config.get("hyperion_url", "ws://127.0.0.1:8090/json-rpc")

# MQTT/Zigbee2MQTT Configuration
MQTT_BROKER_HOST = config.get("mqtt_broker", "127.0.0.1")
MQTT_BROKER_PORT = config.get("mqtt_port", 1883)
MQTT_USERNAME = ""
MQTT_PASSWORD = ""

# ============================================================================
# GLOBALS & STATE
# ============================================================================

latest_color = {"r": 255, "g": 255, "b": 255}
last_publish_time = 0
ws_connected = False
mqtt_connected = False
stop_event = threading.Event()



# ============================================================================
# COLOR CONVERSION UTILITIES
# ============================================================================

def rgb_to_xy(r, g, b):
    """
    Convert RGB (0-255) to XY color space (CIE 1931) for Zigbee lights.
    Returns (x, y, brightness) tuple.
    """
    # Normalize RGB values to 0-1
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    # Apply gamma correction
    r = pow((r + 0.055) / 1.055, 2.4) if r > 0.04045 else r / 12.92
    g = pow((g + 0.055) / 1.055, 2.4) if g > 0.04045 else g / 12.92
    b = pow((b + 0.055) / 1.055, 2.4) if b > 0.04045 else b / 12.92

    # Convert to XYZ
    X = r * 0.649926 + g * 0.103455 + b * 0.197109
    Y = r * 0.234327 + g * 0.743075 + b * 0.022598
    Z = r * 0.000000 + g * 0.053077 + b * 1.035763

    # Calculate xy
    total = X + Y + Z
    if total == 0:
        return (0.0, 0.0, 0)

    x = X / total
    y = Y / total

    # Brightness (0-254 for Zigbee)
    brightness = int(Y * 254)
    if brightness < 1:
        brightness = 1

    return (round(x, 4), round(y, 4), brightness)


# ============================================================================
# MQTT CLIENT SETUP
# ============================================================================

def on_mqtt_connect(client, userdata, flags, rc, properties=None):
    """MQTT connection callback."""
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print(f"[MQTT] Connected to broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    else:
        mqtt_connected = False
        print(f"[MQTT] Connection failed with code {rc}")


def on_mqtt_disconnect(client, userdata, disconnect_flags, rc, properties=None):
    """MQTT disconnection callback."""
    global mqtt_connected
    mqtt_connected = False
    if rc != 0:
        print(f"[MQTT] Unexpected disconnection (code {rc}). Will auto-reconnect...")


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"hyperion_bridge_{random.randint(1000,9999)}")
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_disconnect = on_mqtt_disconnect
# Increase keep-alive to prevent disconnections
mqtt_client._keepalive = 120  # 2 minutes


def mqtt_connect():
    """Establish MQTT connection with retry logic."""
    while not stop_event.is_set():
        try:
            if not mqtt_connected:
                print("[MQTT] Attempting to connect...")
                mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=120)
                mqtt_client.loop_start()
                time.sleep(2)  # Give it more time to establish connection
            else:
                break
        except Exception as e:
            print(f"[MQTT] Connection error: {e}. Retrying in 3 seconds...")
            time.sleep(3)


def mqtt_publish_color(r, g, b):
    """Publish color to all configured Zigbee2MQTT lights with individual brightness settings."""
    global mqtt_client, mqtt_connected, config

    # Check for config updates
    load_config()

    # Ensure MQTT is connected before publishing
    if not mqtt_connected:
        print("[MQTT] Not connected. Attempting reconnection...")
        mqtt_connect()

    if mqtt_connected:
        # Convert RGB to XY color space for Zigbee lights
        x, y, _ = rgb_to_xy(r, g, b)  # Ignore brightness from conversion

        # Publish to all configured devices
        published_count = 0
        devices = config.get("devices", [])
        transition_time = config.get("transition_time", 0.1)

        for device in devices:
            if not device.get("enabled", True):
                continue
            
            topic = device.get("topic")
            brightness_mult = device.get("brightness_multiplier", 1.0)
            
            # Calculate brightness
            if brightness_mult == -1:
                device_brightness = 254
            else:
                device_brightness = int(brightness_mult * 254)
                if device_brightness < 1: device_brightness = 1
                elif device_brightness > 254: device_brightness = 254

            payload = {
                "state": "ON",
                "color": {"x": x, "y": y},
                "brightness": device_brightness,
                "transition": transition_time
            }
            payload_str = json.dumps(payload)

            try:
                result = mqtt_client.publish(topic, payload_str, qos=0)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    published_count += 1
            except Exception as e:
                print(f"[MQTT] Publish error to {topic}: {e}")

        if published_count > 0:
            pass # Suppress log spam for cleaner output, or logging could be added back if needed
    else:
        print("[MQTT] Cannot publish - broker not connected")


# ============================================================================
# WEBSOCKET HANDLERS
# ============================================================================

def on_ws_open(ws):
    """WebSocket open handler - subscribe to Hyperion LED stream."""
    global ws_connected
    ws_connected = True
    print(f"[WebSocket] Connected to Hyperion at {HYPERION_WS_URL}")

    # Send the subscription command to start receiving LED color updates
    subscribe_command = {
        "command": "ledcolors",
        "subcommand": "ledstream-start"
    }
    ws.send(json.dumps(subscribe_command))
    print("[WebSocket] Sent ledstream-start subscription")


def on_ws_message(ws, message):
    """
    WebSocket message handler - receive Hyperion LED color updates.
    This runs at ~60 FPS from Hyperion. We extract the color and throttle output.
    """
    global latest_color, last_publish_time

    try:
        data = json.loads(message)

        # Check if this is a ledcolors-ledstream-update message
        if data.get("command") == "ledcolors-ledstream-update":
            # LED data is nested in data.leds and is a flat array [R, G, B]
            led_data = data.get("data", {})
            leds = led_data.get("leds", [])

            if leds and len(leds) >= 3:
                # Calculate average color from all configured LEDs
                num_leds = len(leds) // 3
                if num_leds > 0:
                    r_avg = sum(leds[i] for i in range(0, len(leds), 3)) // num_leds
                    g_avg = sum(leds[i] for i in range(1, len(leds), 3)) // num_leds
                    b_avg = sum(leds[i] for i in range(2, len(leds), 3)) // num_leds
                    r, g, b = r_avg, g_avg, b_avg
                else:
                    r, g, b = 0, 0, 0

                # Apply color warmth filter
                warmth = config.get("color_warmth", 1.0)
                
                # Base Warmth: Reduce Blue
                if warmth > 1.0:
                    # Linearly reduce blue: at 2.0 warmth, blue is divided by 4
                    b = int(b / (1 + (warmth - 1.0) * 3))
                
                # Deep Warmth: Reduce Green (shifts Yellow -> Orange -> Red)
                if warmth > 1.2:
                    # Start reducing green slightly to remove "lime" tints
                    factor = (warmth - 1.2) * 0.8  # at 2.0, factor is 0.64
                    g = int(g * (1.0 - factor))

                # Ensure bounds
                r = min(255, max(0, r))
                g = min(255, max(0, g))
                b = min(255, max(0, b))

                # Store latest color
                latest_color = {"r": r, "g": g, "b": b}

                # Apply non-blocking throttle
                throttle_interval = config.get("throttle_interval", 1.0)
                current_time = time.time()
                if current_time - last_publish_time >= throttle_interval:
                    mqtt_publish_color(r, g, b)
                    last_publish_time = current_time

    except json.JSONDecodeError as e:
        print(f"[WebSocket] JSON parse error: {e}")
    except Exception as e:
        print(f"[WebSocket] Message handler error: {e}")


def on_ws_error(ws, error):
    """WebSocket error handler."""
    print(f"[WebSocket] Error: {error}")


def on_ws_close(ws, close_status_code, close_msg):
    """WebSocket close handler."""
    global ws_connected
    ws_connected = False
    print(f"[WebSocket] Closed (code={close_status_code}, msg={close_msg}). Will reconnect...")


# ============================================================================
# WEBSOCKET CONNECTION & RECONNECTION
# ============================================================================

def websocket_connect():
    """
    Establish WebSocket connection to Hyperion with auto-reconnect logic.
    """
    while not stop_event.is_set():
        try:
            print(f"[WebSocket] Attempting to connect to {HYPERION_WS_URL}...")
            ws = websocket.WebSocketApp(
                HYPERION_WS_URL,
                on_open=on_ws_open,
                on_message=on_ws_message,
                on_error=on_ws_error,
                on_close=on_ws_close
            )
            ws.run_forever(reconnect=5)  # Auto-reconnect every 5 seconds if closed
        except Exception as e:
            print(f"[WebSocket] Connection error: {e}. Retrying in 5 seconds...")
            if not stop_event.is_set():
                time.sleep(5)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point - start MQTT and WebSocket connections."""
    print("=" * 70)
    print("Hyperion.NG to Zigbee2MQTT Bridge")
    print("=" * 70)
    print(f"Hyperion: {HYPERION_WS_URL}")
    print(f"MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    
    devices = config.get("devices", [])
    print(f"Controlling {len(devices)} configured device(s):")
    for i, dev in enumerate(devices, 1):
        name = dev.get("name", "Unknown")
        enabled = "ENABLED" if dev.get("enabled", True) else "DISABLED"
        brightness = dev.get("brightness_multiplier", 1.0)
        b_str = "Max" if brightness == -1 else f"{int(brightness*100)}%"
        print(f"  {i}. {name} ({b_str}) [{enabled}]")
        
    throttle = config.get("throttle_interval", 1.0)
    print(f"Throttle Rate: 1 update per {throttle}s ({1/throttle:.1f} Hz)")
    print("=" * 70)
    print("Press Ctrl+C to exit")
    print("=" * 70)
    print()

    # Start MQTT connection in background thread
    mqtt_thread = threading.Thread(target=mqtt_connect, daemon=True)
    mqtt_thread.start()

    # Start WebSocket connection (this blocks in run_forever)
    try:
        websocket_connect()
    except KeyboardInterrupt:
        print("\n\n[Main] Keyboard interrupt received, shutting down...")
        stop_event.set()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("[Main] Goodbye!")
        import sys
        sys.exit(0)


if __name__ == "__main__":
    main()
