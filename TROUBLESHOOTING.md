# Troubleshooting Guide

## Connection Issues

### "Connection refused on port 1883"

**Problem:** MQTT broker is not running or not listening on port 1883.

**Solutions:**

1. **Windows - Verify Mosquitto is running:**
   ```powershell
   Get-Process mosquitto
   ```
   If not found, start it:
   ```powershell
   & 'C:\Program Files\Mosquitto\mosquitto.exe'
   ```

2. **Linux - Check Mosquitto status:**
   ```bash
   sudo systemctl status mosquitto
   # or start if not running
   sudo systemctl start mosquitto
   ```

3. **macOS - Check Mosquitto:**
   ```bash
   brew services list | grep mosquitto
   # Start if needed
   brew services start mosquitto
   ```

4. **Test connection:**
   ```bash
   mosquitto_pub -h localhost -t test -m "hello"
   ```

---

### "Hyperion WebSocket connection timeout (port 8090)"

**Problem:** Hyperion.NG is not running or not listening on port 8090.

**Solutions:**

1. **Verify Hyperion is running:**
   - Windows: Check System Tray for Hyperion icon
   - Linux: `systemctl status hyperiond`
   - macOS: Check Applications folder

2. **Check port 8090 is open:**
   ```bash
   # Windows (PowerShell)
   Test-NetConnection localhost -Port 8090
   
   # Linux/macOS
   nc -zv localhost 8090
   ```

3. **Verify Hyperion config:**
   - Open http://localhost:8090 in browser
   - Check if web UI loads
   - If not, restart Hyperion service

4. **Check Hyperion logs:**
   - Windows: `%APPDATA%\Hyperion\`
   - Linux: `/home/user/.config/hyperion/`
   - macOS: `~/.config/hyperion/`

---

### "MQTT authentication failed"

**Problem:** MQTT broker requires username/password.

**Solutions:**

1. **Update bridge_config.json with credentials:**
   ```json
   {
     "mqtt_broker": "127.0.0.1",
     "mqtt_port": 1883,
     "mqtt_username": "your_username",
     "mqtt_password": "your_password"
   }
   ```

2. **Restart the bridge application**

3. **Verify credentials work:**
   ```bash
   mosquitto_pub -h localhost -u username -P password -t test -m "hello"
   ```

---

## Color & Brightness Issues

### "Lights are not changing color at all"

**Problem:** Bridge is running but lights don't respond.

**Checklist:**

1. **Verify device topics in config:**
   ```bash
   # Check Zigbee2MQTT device list
   mosquitto_sub -t 'zigbee2mqtt/bridge/devices'
   ```

2. **Compare device names in Zigbee2MQTT vs bridge_config.json:**
   - In Zigbee2MQTT UI, find exact device name
   - Update bridge_config.json to match exactly
   - Case-sensitive!

3. **Test manual MQTT publish:**
   ```bash
   mosquitto_pub -t "zigbee2mqtt/YourLightName/set" \
     -m '{"xy":[0.3,0.4],"brightness":254}'
   ```

4. **Check UI status indicators:**
   - MQTT Status should be "Connected"
   - Hyperion Status should be "Connected"
   - Both red = not communicating

5. **Verify light is enabled in dashboard:**
   - Check "Sync Config" toggle for each light

---

### "Colors look wrong (too bright/dim)"

**Problem:** Light colors are not matching screen colors.

**Solutions:**

1. **Adjust brightness multiplier in config:**
   ```json
   {
     "name": "Desk Light",
     "topic": "zigbee2mqtt/Desk/set",
     "brightness_multiplier": 0.5,  // Reduce to 50%
     "type": "rgb"
   }
   ```

2. **Reduce color throttle for more updates:**
   ```json
   "throttle_interval": 0.3  // More frequent updates (default 0.6)
   ```

3. **Disable Deep Warmth Mode temporarily:**
   - In Settings tab, set "Warmth" slider to 0.0
   - Test if colors are correct
   - If yes, adjust warmth gradually

---

### "Color changes are very slow/laggy"

**Problem:** Large delay between screen and light color change.

**Solutions:**

1. **Reduce throttle_interval:**
   ```json
   "throttle_interval": 0.2  // Lower = more responsive
   ```

2. **Check Hyperion refresh rate:**
   - Settings → General → Framerate (should be 30+ FPS)

3. **Verify MQTT broker performance:**
   ```bash
   # Monitor MQTT traffic
   mosquitto_sub -t 'zigbee2mqtt/#' -v
   ```

4. **Check system resources:**
   - Open Task Manager (Windows) or top (Linux)
   - Verify CPU/RAM are not maxed out

---

## Dashboard/UI Issues

### "Dashboard window is not responding"

**Problem:** UI is frozen or very slow.

**Solutions:**

1. **Force restart:**
   - Close application (Ctrl+C in terminal)
   - Wait 5 seconds
   - Restart: `python hyperion_command_center.py`

2. **Check for errors in terminal:**
   - Look for red error messages
   - Screenshot and search GitHub issues

3. **Verify Python version:**
   ```bash
   python --version  # Should be 3.10+
   ```

4. **Reinstall dependencies:**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

---

### "Color picker not showing colors correctly"

**Problem:** Color picker is black/not displaying gradient.

**Solutions:**

1. **Restart dashboard:** Close and reopen application

2. **Verify background image exists:**
   - Should be `background.jpg` in same directory
   - If missing, adjust opacity sliders first

3. **Check CustomTkinter installation:**
   ```bash
   pip install --upgrade customtkinter
   ```

---

### "Settings not saving"

**Problem:** Changes to config don't persist after restart.

**Solutions:**

1. **Verify bridge_config.json is not read-only:**
   ```bash
   # Windows (PowerShell)
   (Get-Item bridge_config.json).Attributes
   
   # Linux/macOS
   ls -la bridge_config.json
   ```

2. **Check file permissions:**
   - Right-click file → Properties → Security (Windows)
   - Or: `chmod 644 bridge_config.json` (Linux/macOS)

3. **Ensure JSON is valid:**
   - Use https://jsonlint.com to validate bridge_config.json
   - Common issues: trailing commas, missing quotes

---

## Device-Specific Issues

### "Gledopto LED Strip not responding"

**Problem:** Gledopto devices work in Zigbee2MQTT but not in bridge.

**Solutions:**

1. **Check device supports RGB:**
   - Gledopto has RGB and CCT-only models
   - Set `type: "rgb"` for RGB models

2. **Verify correct topic:**
   ```json
   "topic": "zigbee2mqtt/Gledopto LED Strip/set"  // Exact name from Zigbee2MQTT
   ```

3. **Test with manual command:**
   ```bash
   mosquitto_pub -t "zigbee2mqtt/Gledopto LED Strip/set" \
     -m '{"xy":[0.3,0.4],"brightness":254}'
   ```

---

### "IKEA Tradfri not changing brightness"

**Problem:** Color changes but brightness doesn't sync.

**Solutions:**

1. **Verify device supports brightness:**
   - Tradfri bulbs: Yes
   - Tradfri remotes: No
   - Check Zigbee2MQTT documentation

2. **Check config has brightness_multiplier:**
   ```json
   {
     "name": "Tradfri",
     "topic": "zigbee2mqtt/Tradfri/set",
     "brightness_multiplier": 1.0,  // Must have this
     "type": "rgb"
   }
   ```

---

### "Aqara Ceiling Light only changes temperature (not RGB)"

**Problem:** Aqara light appears to be CCT-only.

**Solutions:**

1. **Change device type:**
   ```json
   {
     "name": "Aqara Ceiling Light",
     "type": "cct"  // Change from "rgb" to "cct"
   }
   ```

2. **Restart bridge**

3. **Light should now respond to color temperature changes**

---

## Performance Issues

### "Application uses too much CPU"

**Problem:** Dashboard or bridge consuming significant CPU.

**Solutions:**

1. **Increase throttle interval:**
   ```json
   "throttle_interval": 1.0  // Wait longer between updates
   ```

2. **Check for infinite loops:**
   - Terminal should show periodic updates, not rapid spam
   - If rapid spam, kill and investigate

3. **Reduce Hyperion frame rate:**
   - Hyperion Settings → General → Framerate (set to 15 FPS)

---

### "Memory usage grows over time (leak)"

**Problem:** App slowly uses more RAM until system slows down.

**Solutions:**

1. **Restart application daily** (temporary fix)

2. **Check for WebSocket reconnection loops:**
   - Look for repeated "Reconnecting..." messages
   - May indicate unstable Hyperion connection

3. **Update Python and dependencies:**
   ```bash
   pip install --upgrade websocket-client paho-mqtt customtkinter
   ```

---

## File System Issues

### "Config file corrupted after edit"

**Problem:** App won't start; JSON parsing error.

**Solutions:**

1. **Validate JSON:**
   - Copy config contents to https://jsonlint.com
   - Fix syntax errors

2. **Restore from example:**
   ```bash
   cp bridge_config.example.json bridge_config.json
   # Re-enter your settings manually
   ```

3. **Check for encoding issues:**
   - Edit in UTF-8 encoding
   - Some editors add BOM (Byte Order Mark)

---

### ".gitignore not working (sensitive files committed)"

**Problem:** Files you wanted to exclude are in version history.

**Solutions:**

1. **Clear git cache:**
   ```bash
   git rm --cached bridge_config.json
   git commit -m "Remove sensitive config from tracking"
   ```

2. **Verify .gitignore:**
   ```bash
   cat .gitignore  # Should include bridge_config.json
   ```

3. **Remove from git history (advanced):**
   - Use `git-filter-branch` (caution: rewrites history)
   - For secrets, rotate credentials immediately

---

## Getting Help

### Before posting an issue:

1. **Collect diagnostic info:**
   ```bash
   python --version
   pip list | grep -E "websocket|mqtt|customtkinter"
   cat bridge_config.json | head -10
   ```

2. **Check existing issues:**
   - Search GitHub issues for similar problems
   - May already have solution

3. **Enable debug logging:**
   - Add `logging.basicConfig(level=logging.DEBUG)` to code
   - Run and capture full output

4. **Post error details:**
   - Full error message
   - Python version
   - OS (Windows/Linux/macOS)
   - Steps to reproduce
   - Diagnostic info from above

---

## Common Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Nothing works | Restart all: bridge, Mosquitto, Hyperion, dashboard |
| No colors | Check device topics in Zigbee2MQTT match config |
| Slow response | Lower `throttle_interval` in config |
| App crashes | Update dependencies: `pip install -r requirements.txt --upgrade` |
| Settings lost | Verify `bridge_config.json` is not read-only |
| High CPU | Increase `throttle_interval` or reduce Hyperion FPS |
