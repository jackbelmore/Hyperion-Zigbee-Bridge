#!/usr/bin/env python3
"""
Hyperion Command Center
A Retro-Vaporwave Dashboard for your Zigbee Lights
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import json
import os
import subprocess
import threading
import time
import paho.mqtt.client as mqtt
import random

# Configuration
CONFIG_FILE = "C:\\Users\\Box\\bridge_config.json"
BRIDGE_SCRIPT = "C:\\Users\\Box\\hyperion_zigbee_bridge.py"

# Vaporwave Palette
COLORS = {
    "bg": "#2D2B55",       # Deep Navy
    "card": "#1E1C3B",     # Darker Navy
    "fg": "#FFFFFF",       # White
    "pink": "#FF6AC1",     # Hot Pink
    "cyan": "#57FFF5",     # Cyan
    "yellow": "#FFE66D",   # Soft Yellow
    "dim": "#666699"       # Dim Text
}

class HyperionCommandCenter:
    def __init__(self, root):
        self.root = root
        self.root.title("💠 HYPERION COMMAND CENTER")
        self.root.geometry("650x750")
        self.root.configure(bg=COLORS["bg"])
        
        self.config = {}
        self.mqtt_client = None
        self.bridge_process = None
        
        self.load_config()
        self.setup_mqtt()
        self.check_bridge_status()
        
        self.create_ui()

    # ================= SYSTEM LOGIC =================

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {"devices": [], "recent_colors": []}
        except Exception as e:
            print(f"Config Error: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def setup_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"hyp_gui_{random.randint(1000,9999)}")
            self.mqtt_client.connect(self.config.get("mqtt_broker", "127.0.0.1"), 1883)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"MQTT Error: {e}")

    def check_bridge_status(self):
        pass

    def toggle_bridge(self):
        if self.bridge_process and self.bridge_process.poll() is None:
            self.bridge_process.terminate()
            self.bridge_process = None
            self.status_lbl.config(text="SYSTEM STATUS: OFFLINE", fg=COLORS["pink"])
            self.btn_bridge.config(text="⚡ START SYSTEM", bg=COLORS["cyan"], fg=COLORS["bg"])
        else:
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                self.bridge_process = subprocess.Popen(
                    ["python", BRIDGE_SCRIPT],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.status_lbl.config(text="SYSTEM STATUS: ONLINE", fg=COLORS["cyan"])
                self.btn_bridge.config(text="🛑 SHUTDOWN SYSTEM", bg=COLORS["pink"], fg="white")
            except Exception as e:
                messagebox.showerror("Error", f"Could not start bridge: {e}")

    def send_manual_color(self, device_idx, hex_color):
        if not self.mqtt_client: return
        device = self.config["devices"][device_idx]
        topic = device["topic"]
        
        h = hex_color.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        
        payload = {"state": "ON", "color": {"r": r, "g": g, "b": b}}
        self.mqtt_client.publish(topic, json.dumps(payload))
        
        history = self.config.get("recent_colors", [])
        if hex_color not in history:
            history.insert(0, hex_color)
            self.config["recent_colors"] = history[:6]
            self.save_config()
            self.refresh_history()

    def send_manual_temp(self, device_idx, mireds):
        if not self.mqtt_client: return
        device = self.config["devices"][device_idx]
        payload = {"state": "ON", "color_temp": int(mireds)}
        self.mqtt_client.publish(device["topic"], json.dumps(payload))

    def set_manual_brightness(self, device_idx, val):
        if not self.mqtt_client: return
        device = self.config["devices"][device_idx]
        payload = {"brightness": int(float(val)), "state": "ON"}
        self.mqtt_client.publish(device["topic"], json.dumps(payload))

    # ================= UI CONSTRUCTION =================

    def create_ui(self):
        style = ttk.Style()
        style.theme_use('alt')
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["card"], foreground=COLORS["dim"], padding=[20, 10], font=("Courier New", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COLORS["pink"])], foreground=[("selected", "white")])

        tk.Label(self.root, text="HYPERION COMMAND CENTER", font=("Segoe UI", 24, "bold"), bg=COLORS["bg"], fg=COLORS["cyan"]).pack(pady=(20, 5))
        
        self.status_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.status_lbl = tk.Label(self.status_frame, text="SYSTEM STATUS: WAITING...", font=("Courier New", 12, "bold"), bg=COLORS["bg"], fg=COLORS["dim"])
        self.status_lbl.pack(side=tk.LEFT)
        
        self.btn_bridge = tk.Button(
            self.status_frame, text="⚡ START SYSTEM", 
            font=("Segoe UI", 10, "bold"), bg=COLORS["cyan"], fg=COLORS["bg"],
            activebackground=COLORS["pink"], activeforeground="white",
            relief=tk.FLAT, padx=15, pady=5,
            command=self.toggle_bridge
        )
        self.btn_bridge.pack(side=tk.RIGHT)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.tab_sync = tk.Frame(notebook, bg=COLORS["bg"])
        notebook.add(self.tab_sync, text="SYNC CONFIG")
        self.build_sync_tab()

        self.tab_manual = tk.Frame(notebook, bg=COLORS["bg"])
        notebook.add(self.tab_manual, text="MANUAL CONTROL")
        self.build_manual_tab()

        self.tab_settings = tk.Frame(notebook, bg=COLORS["bg"])
        notebook.add(self.tab_settings, text="SETTINGS")
        self.build_settings_tab()
        
        self.root.after(500, self.toggle_bridge)

    def build_sync_tab(self):
        # Header
        tk.Label(self.tab_sync, text="SYNC CONTROL (Toggle & Brightness)", font=("Courier New", 12), bg=COLORS["bg"], fg=COLORS["pink"]).pack(pady=10)
        
        self.sync_vars = []
        
        for i, device in enumerate(self.config.get("devices", [])):
            frame = tk.Frame(self.tab_sync, bg=COLORS["card"], pady=10, padx=15)
            frame.pack(fill=tk.X, pady=5)
            
            # Row 1: Checkbox & Status
            header = tk.Frame(frame, bg=COLORS["card"])
            header.pack(fill=tk.X)

            var = tk.BooleanVar(value=device.get("enabled", False))
            self.sync_vars.append(var)
            
            def on_toggle(idx=i, v=var):
                self.config["devices"][idx]["enabled"] = v.get()
                self.save_config()
                self.refresh_manual_tab()

            cb = tk.Checkbutton(
                header, text=device["name"].upper(), variable=var,
                font=("Segoe UI", 12, "bold"),
                bg=COLORS["card"], fg=COLORS["cyan"],
                selectcolor=COLORS["bg"], activebackground=COLORS["card"], activeforeground=COLORS["pink"],
                command=on_toggle
            )
            cb.pack(side=tk.LEFT)
            
            # Row 2: Brightness Scaling
            slider_row = tk.Frame(frame, bg=COLORS["card"])
            slider_row.pack(fill=tk.X, pady=(5,0))
            
            tk.Label(slider_row, text="SYNC MAX:", font=("Courier New", 8), bg=COLORS["card"], fg=COLORS["dim"]).pack(side=tk.LEFT)
            
            current_mult = device.get("brightness_multiplier", 1.0)
            if current_mult == -1: current_mult = 1.0 # Handle 'max' as 100%

            def on_sync_bright(val, idx=i):
                v = float(val)
                self.config["devices"][idx]["brightness_multiplier"] = v
                self.save_config()
            
            scale = tk.Scale(
                slider_row, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                bg=COLORS["card"], fg="white", highlightthickness=0, troughcolor=COLORS["bg"],
                command=lambda v, idx=i: on_sync_bright(v, idx),
                showvalue=0
            )
            scale.set(current_mult)
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            tk.Label(slider_row, text="100%", font=("Courier New", 8), bg=COLORS["card"], fg=COLORS["dim"]).pack(side=tk.RIGHT)

    def build_manual_tab(self):
        self.manual_container = tk.Frame(self.tab_manual, bg=COLORS["bg"])
        self.manual_container.pack(fill=tk.BOTH, expand=True)
        self.refresh_manual_tab()

    def refresh_manual_tab(self):
        for widget in self.manual_container.winfo_children():
            widget.destroy()

        tk.Label(self.manual_container, text="MANUAL OVERRIDE", font=("Courier New", 12), bg=COLORS["bg"], fg=COLORS["pink"]).pack(pady=10)

        # Color History (Only relevant for RGB devices, but show anyway)
        hist_frame = tk.Frame(self.manual_container, bg=COLORS["bg"])
        hist_frame.pack(fill=tk.X, pady=10)
        tk.Label(hist_frame, text="HISTORY (RGB):", bg=COLORS["bg"], fg=COLORS["dim"], font=("Courier New", 10)).pack(side=tk.LEFT)
        self.history_frame = tk.Frame(hist_frame, bg=COLORS["bg"])
        self.history_frame.pack(side=tk.LEFT, padx=10)
        self.refresh_history()

        # Device List
        for i, device in enumerate(self.config.get("devices", [])):
            if device.get("enabled", True):
                continue 

            card = tk.Frame(self.manual_container, bg=COLORS["card"], padx=10, pady=10)
            card.pack(fill=tk.X, pady=5)

            # Name & Type
            dtype = device.get("type", "rgb").upper()
            tk.Label(card, text=f"{device['name']} ({dtype})", font=("Segoe UI", 11, "bold"), bg=COLORS["card"], fg="white").pack(anchor="w")

            controls = tk.Frame(card, bg=COLORS["card"])
            controls.pack(fill=tk.X, pady=5)

            # CONTROLS BASED ON TYPE
            if device.get("type") == "cct":
                # Temperature Slider
                tk.Label(controls, text="TEMP:", font=("Courier New", 9), bg=COLORS["card"], fg=COLORS["yellow"]).pack(side=tk.LEFT)
                temp_scale = tk.Scale(
                    controls, from_=150, to=370, orient=tk.HORIZONTAL, length=200,
                    bg=COLORS["card"], fg=COLORS["yellow"], highlightthickness=0, showvalue=0,
                    troughcolor=COLORS["bg"],
                    command=lambda v, idx=i: self.send_manual_temp(idx, v)
                )
                temp_scale.set(370) # Default mid-warm
                temp_scale.pack(side=tk.LEFT, padx=10)
                tk.Label(controls, text="COOL <-> WARM", font=("Courier New", 7), bg=COLORS["card"], fg=COLORS["dim"]).pack(side=tk.LEFT)

            else:
                # RGB Color Picker
                def pick_color(idx=i):
                    color = colorchooser.askcolor(title=f"Color for {self.config['devices'][idx]['name']}")
                    if color[1]:
                        self.send_manual_color(idx, color[1])

                btn_col = tk.Button(controls, text="🎨 COLOR", bg=COLORS["pink"], fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, command=pick_color)
                btn_col.pack(side=tk.LEFT)

            # Brightness Slider (Common)
            bright_frame = tk.Frame(card, bg=COLORS["card"])
            bright_frame.pack(fill=tk.X, pady=(5,0))
            tk.Label(bright_frame, text="BRIGHT:", font=("Courier New", 9), bg=COLORS["card"], fg=COLORS["cyan"]).pack(side=tk.LEFT)
            
            slider = tk.Scale(
                bright_frame, from_=0, to=254, orient=tk.HORIZONTAL,
                bg=COLORS["card"], fg=COLORS["cyan"], highlightthickness=0, showvalue=0,
                troughcolor=COLORS["bg"],
                command=lambda v, idx=i: self.set_manual_brightness(idx, v)
            )
            slider.set(254)
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def refresh_history(self):
        for w in self.history_frame.winfo_children(): w.destroy()
        for color in self.config.get("recent_colors", []):
            tk.Button(
                self.history_frame, bg=color, width=3, relief=tk.FLAT,
                activebackground=color,
                command=lambda c=color: self.apply_history_color(c)
            ).pack(side=tk.LEFT, padx=2)

    def apply_history_color(self, color):
        for i, device in enumerate(self.config.get("devices", [])):
            if not device.get("enabled", True) and device.get("type", "rgb") == "rgb":
                self.send_manual_color(i, color)

    def build_settings_tab(self):
        card = tk.Frame(self.tab_settings, bg=COLORS["card"], padx=20, pady=20)
        card.pack(fill=tk.X, pady=20)

        tk.Label(card, text="WARMTH INTENSITY (Sunset Factor)", font=("Segoe UI", 11), bg=COLORS["card"], fg=COLORS["yellow"]).pack(anchor="w")
        scale_warmth = tk.Scale(
            card, from_=0.5, to=2.5, resolution=0.1, orient=tk.HORIZONTAL,
            bg=COLORS["card"], fg="white", highlightthickness=0, troughcolor=COLORS["bg"],
            command=lambda v: self.update_setting("color_warmth", float(v))
        )
        scale_warmth.set(self.config.get("color_warmth", 1.5))
        scale_warmth.pack(fill=tk.X, pady=(0, 20))

        tk.Label(card, text="SYNC DELAY (Seconds)", font=("Segoe UI", 11), bg=COLORS["card"], fg=COLORS["cyan"]).pack(anchor="w")
        scale_throt = tk.Scale(
            card, from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
            bg=COLORS["card"], fg="white", highlightthickness=0, troughcolor=COLORS["bg"],
            command=lambda v: self.update_setting("throttle_interval", float(v))
        )
        scale_throt.set(self.config.get("throttle_interval", 1.0))
        scale_throt.pack(fill=tk.X)

    def update_setting(self, key, val):
        self.config[key] = val
        self.save_config()

if __name__ == "__main__":
    root = tk.Tk()
    app = HyperionCommandCenter(root)
    root.mainloop()
