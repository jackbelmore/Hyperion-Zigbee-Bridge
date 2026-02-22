#!/usr/bin/env python3
"""
Hyperion Vaporwave Dashboard v4.0
Features: Persistent State, Grey-Out Logic, Responsive Visualizer
"""

import sys
import argparse
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from CTkColorPicker import CTkColorPicker
import json
import os
import subprocess
import threading
import time
import random
from PIL import Image, ImageTk, ImageDraw, ImageEnhance
import pystray
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "bridge_config.json")
BRIDGE_SCRIPT = os.path.join(SCRIPT_DIR, "hyperion_zigbee_bridge.py")
BG_IMAGE = os.path.join(SCRIPT_DIR, "background.jpg")
ICON_ICO = os.path.join(SCRIPT_DIR, "icon.ico")
ICON_PNG = os.path.join(SCRIPT_DIR, "icon.png")

# Theme
THEME = {
    "bg": "#050505",
    "pink": "#ff0055",
    "cyan": "#00f3ff",
    "yellow": "#ffd900",
    "orange": "#ff5e00",
    "white": "#ffffff",
    "dim": "#aaaaaa",
    "disabled": "#444444"
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class PulseButton(ctk.CTkButton):
    def __init__(self, *args, **kwargs):
        self.base_color = kwargs.get("fg_color", THEME["pink"])
        self.hover_color = kwargs.get("hover_color", THEME["cyan"])
        super().__init__(*args, **kwargs)
        self.configure(command=self._animate_click)
        self._user_command = kwargs.get("command", None)

    def _animate_click(self):
        print(f"[UI] Button Clicked: {self.cget('text')}")
        threading.Thread(target=self._pulse, daemon=True).start()
        if self._user_command:
            self._user_command()

    def _pulse(self):
        try:
            if not self.winfo_exists(): return
            self.configure(fg_color=THEME["white"], text_color="#000000")
            time.sleep(0.05)

            if not self.winfo_exists(): return
            self.configure(fg_color=self.hover_color, text_color=THEME["white"])
            time.sleep(0.1)

            if not self.winfo_exists(): return
            self.configure(fg_color=self.base_color)
        except (tk.TclError, RuntimeError):
            pass # Widget was likely destroyed during refresh


class RainbowArcadeButton(ctk.CTkButton):
    """Ultra-flashy rainbow-cycling arcade button for game launcher."""

    def __init__(self, *args, **kwargs):
        self._user_command = kwargs.pop("command", None)
        kwargs["command"] = self._on_click
        super().__init__(*args, **kwargs)

        self.rainbow_colors = [
            THEME["pink"],     # Neon Pink
            THEME["orange"],   # Orange
            THEME["yellow"],   # Yellow
            "#00ff00",         # Green
            THEME["cyan"],     # Cyan
            "#0055ff",         # Blue
            "#aa00ff",         # Purple
        ]
        self.color_index = 0
        self.animating = True
        self.intro_flash_duration = 3.0  # Flash for 3 seconds only
        self._start_rainbow_cycle()

    def _start_rainbow_cycle(self):
        """Cycle through rainbow colors for 3 seconds at startup, then stop."""
        def cycle():
            start_time = time.time()
            while self.animating:
                try:
                    if not self.winfo_exists():
                        break

                    elapsed = time.time() - start_time
                    if elapsed >= self.intro_flash_duration:
                        # Stop flashing, set to final color (pink)
                        self.configure(fg_color=THEME["pink"])
                        break

                    self.configure(fg_color=self.rainbow_colors[self.color_index])
                    self.color_index = (self.color_index + 1) % len(self.rainbow_colors)
                    time.sleep(0.3)
                except (tk.TclError, RuntimeError):
                    break

        threading.Thread(target=cycle, daemon=True).start()

    def _on_click(self):
        """Launch sequence animation before executing command."""
        if self._user_command:
            threading.Thread(target=self._launch_sequence, daemon=True).start()

    def _launch_sequence(self):
        """Epic launch sequence with countdown and flashing."""
        try:
            original_text = self.cget("text")

            # Flash rapidly
            for _ in range(6):
                if not self.winfo_exists(): return
                self.configure(fg_color=THEME["white"], text_color="#000000")
                time.sleep(0.05)
                self.configure(fg_color="#000000", text_color=THEME["white"])
                time.sleep(0.05)

            # Countdown
            for count in [3, 2, 1]:
                if not self.winfo_exists(): return
                self.configure(text=f"🚀 {count} 🚀", fg_color=THEME["orange"])
                time.sleep(0.4)

            # LAUNCH!
            if not self.winfo_exists(): return
            self.configure(text="💥 LAUNCH! 💥", fg_color=THEME["cyan"])
            time.sleep(0.3)

            # Execute the actual command
            if self._user_command:
                self._user_command()

            # Flash success
            for _ in range(4):
                if not self.winfo_exists(): return
                self.configure(fg_color=THEME["pink"])
                time.sleep(0.1)
                self.configure(fg_color=THEME["yellow"])
                time.sleep(0.1)

            # Restore
            if not self.winfo_exists(): return
            self.configure(text=original_text)

        except (tk.TclError, RuntimeError):
            pass

    def destroy(self):
        """Stop animation thread when destroyed."""
        self.animating = False
        super().destroy()


class VaporwaveColorPicker(ctk.CTkFrame):
    """Embedded color picker with vaporwave theming for manual light control."""

    # Preset colors matching vaporwave aesthetic
    PRESETS = [
        ("#ff0055", "NEON"),      # Neon Pink
        ("#00f3ff", "CYBER"),     # Cyber Cyan
        ("#ffd900", "SUN"),       # Acid Yellow
        ("#a855f7", "VIOLET"),    # Purple
        ("#ff5e00", "FLAME"),     # Orange
        ("#39ff14", "MATRIX"),    # Neon Green
    ]

    def __init__(self, master, device_idx, on_color_change, initial_color="#ff0055"):
        super().__init__(master, fg_color="transparent")

        self.device_idx = device_idx
        self.on_color_change = on_color_change
        self.current_color = initial_color

        self._build_ui()

    def _build_ui(self):
        # Main horizontal layout
        main_row = ctk.CTkFrame(self, fg_color="transparent")
        main_row.pack(fill="x", pady=5)

        # Left: Color wheel
        wheel_frame = ctk.CTkFrame(main_row, fg_color="#111111", corner_radius=8)
        wheel_frame.pack(side="left", padx=(0, 15))

        self.color_picker = CTkColorPicker(
            wheel_frame,
            width=150,
            initial_color=self.current_color,
            corner_radius=8,
            command=self._on_color_select
        )
        self.color_picker.pack(padx=10, pady=10)

        # Center: Brightness + Preview
        center_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        center_frame.pack(side="left", fill="y", padx=10)

        # Brightness label
        ctk.CTkLabel(
            center_frame,
            text="BRIGHTNESS",
            font=("Consolas", 10),
            text_color=THEME["cyan"]
        ).pack(pady=(0, 5))

        # Vertical brightness slider
        self.brightness_slider = ctk.CTkSlider(
            center_frame,
            from_=1,
            to=254,
            orientation="vertical",
            height=100,
            button_color=THEME["pink"],
            progress_color=THEME["yellow"],
            command=self._on_brightness_change
        )
        self.brightness_slider.set(254)
        self.brightness_slider.pack(pady=5)

        # Brightness value label
        self.brightness_label = ctk.CTkLabel(
            center_frame,
            text="254",
            font=("Consolas", 10),
            text_color=THEME["dim"]
        )
        self.brightness_label.pack()

        # Right side: Preview + Presets
        right_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        right_frame.pack(side="left", fill="y", padx=10)

        # Preview section
        ctk.CTkLabel(
            right_frame,
            text="PREVIEW",
            font=("Consolas", 10),
            text_color=THEME["cyan"]
        ).pack(pady=(0, 5))

        # Color preview swatch
        self.preview_swatch = ctk.CTkButton(
            right_frame,
            text="",
            width=50,
            height=50,
            corner_radius=8,
            fg_color=self.current_color,
            hover=False
        )
        self.preview_swatch.pack(pady=5)

        # Hex value display
        self.hex_label = ctk.CTkLabel(
            right_frame,
            text=self.current_color.upper(),
            font=("Consolas", 10),
            text_color=THEME["white"]
        )
        self.hex_label.pack()

        # Presets section
        presets_frame = ctk.CTkFrame(main_row, fg_color="transparent")
        presets_frame.pack(side="left", fill="y", padx=(20, 0))

        ctk.CTkLabel(
            presets_frame,
            text="PRESETS",
            font=("Consolas", 10),
            text_color=THEME["cyan"]
        ).pack(pady=(0, 5))

        # Preset buttons grid (2 columns)
        preset_grid = ctk.CTkFrame(presets_frame, fg_color="transparent")
        preset_grid.pack()

        for i, (color, name) in enumerate(self.PRESETS):
            row = i // 2
            col = i % 2

            btn = ctk.CTkButton(
                preset_grid,
                text="",
                width=28,
                height=28,
                corner_radius=4,
                fg_color=color,
                hover_color=color,
                command=lambda c=color: self._apply_preset(c)
            )
            btn.grid(row=row, column=col, padx=2, pady=2)

    def _on_color_select(self, color):
        """Called when the color wheel selection changes."""
        print(f"[ColorPicker] Color selected: {color} (type: {type(color).__name__})")
        self.current_color = color
        self.preview_swatch.configure(fg_color=color)
        self.hex_label.configure(text=color.upper())

        if self.on_color_change:
            print(f"[ColorPicker] Calling on_color_change for device {self.device_idx}")
            self.on_color_change(self.device_idx, color)

    def _on_brightness_change(self, value):
        """Called when brightness slider changes."""
        brightness = int(value)
        self.brightness_label.configure(text=str(brightness))
        print(f"[ColorPicker] Brightness changed: {brightness}")

        if self.on_color_change:
            print(f"[ColorPicker] Sending brightness {brightness} for device {self.device_idx}")
            self.on_color_change(self.device_idx, self.current_color, brightness)

    def _apply_preset(self, color):
        """Apply a preset color."""
        self.current_color = color
        self.preview_swatch.configure(fg_color=color)
        self.hex_label.configure(text=color.upper())

        # Update the color picker widget if supported
        try:
            self.color_picker.set(color)
        except:
            pass

        if self.on_color_change:
            self.on_color_change(self.device_idx, color)


class VaporwaveApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("💠 HYPERION COMMAND")
        self.geometry("1100x800")
        # Root uses dark color as fallback
        self.configure(fg_color=THEME["bg"])
        
        if os.path.exists(ICON_ICO):
            self.iconbitmap(ICON_ICO)
        
        self.config = {}
        self.load_config()
        self.mqtt_client = None
        self.bridge_process = None
        self.hyperion_process = None
        self.tray_icon = None
        self.alert_running = True
        self.raw_bg_image = None
        self.orbs = {}
        
        self.setup_mqtt()
        
        # Create main container that will hold the background and all UI elements
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Configure container grid
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.setup_background()
        self.create_sidebar()
        self.create_main_area()

        # Ensure background is behind all grid widgets (critical for transparency)
        if hasattr(self, 'bg_label'):
            self.bg_label.lower()

        self.setup_tray()
        self.check_bridge_running()

        # Initial Viz Update
        self.after(1000, self.refresh_visualizer_state)

        # Start periodic Hyperion status check
        self.check_hyperion_status()

    def setup_background(self):
        if os.path.exists(BG_IMAGE):
            try:
                self.raw_bg_image = Image.open(BG_IMAGE)
                self.apply_bg_brightness(self.config.get("bg_brightness", 0.5))
            except: pass
        self.bind("<Configure>", self.resize_bg)

    def apply_bg_brightness(self, val):
        if not self.raw_bg_image: return
        enhancer = ImageEnhance.Brightness(self.raw_bg_image)
        dark_img = enhancer.enhance(val)
        # Get current window size or use default
        w = self.winfo_width() if self.winfo_width() > 1 else 1100
        h = self.winfo_height() if self.winfo_height() > 1 else 800

        # Convert to PhotoImage for Canvas
        resized_img = dark_img.resize((w, h), Image.Resampling.LANCZOS)
        self.current_bg_photo = ImageTk.PhotoImage(resized_img)

        if hasattr(self, 'bg_canvas'):
            self.bg_canvas.delete("all")
            self.bg_canvas.create_image(0, 0, image=self.current_bg_photo, anchor="nw")
        else:
            # Use Canvas for background - better layering with transparent widgets
            self.bg_canvas = tk.Canvas(self.main_container, highlightthickness=0)
            self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_canvas.create_image(0, 0, image=self.current_bg_photo, anchor="nw")
            self.bg_canvas.lower()  # Send to back

    def resize_bg(self, event):
        if hasattr(self, 'raw_bg_image') and (event.widget == self):
            # Reapply brightness with new window size
            self.apply_bg_brightness(self.config.get("bg_brightness", 0.5))

    # ================= LOGIC =================

    def is_hyperion_running(self):
        """Check if Hyperion process is currently running."""
        if self.hyperion_process and self.hyperion_process.poll() is None:
            return True
        # Also check for Hyperion running independently (not started by us)
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    if 'hyperiond' in proc.info['name'].lower():
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            # psutil not available, just check our own process
            pass
        return False

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {"devices": []}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def setup_mqtt(self):
        if mqtt is None:
            print("[MQTT] ERROR: paho-mqtt library not found. Run 'pip install paho-mqtt'")
            return

        try:
            # Handle version compatibility for CallbackAPIVersion (introduced in paho-mqtt 2.0.0)
            try:
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"vap_gui_{random.randint(1000,9999)}")
            except AttributeError:
                # Fallback for older paho-mqtt versions (< 2.0.0)
                self.mqtt_client = mqtt.Client(client_id=f"vap_gui_{random.randint(1000,9999)}")
            
            def on_connect(client, userdata, flags, rc, properties=None):
                if rc == 0:
                    print("[MQTT] Connected successfully to broker")
                else:
                    print(f"[MQTT] Connection failed with code {rc}")
            
            self.mqtt_client.on_connect = on_connect
            broker = self.config.get("mqtt_broker", "127.0.0.1")
            print(f"[MQTT] Connecting to {broker}...")
            self.mqtt_client.connect(broker, 1883)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"[MQTT] Setup Failed: {e}")

    # ================= TRAY =================
    
    def setup_tray(self):
        if os.path.exists(ICON_PNG):
            image = Image.open(ICON_PNG)
        else:
            image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(image)
            d.ellipse([4, 4, 60, 60], fill=THEME["white"])
            d.rectangle([20, 20, 44, 44], fill=THEME["pink"])

        def show_window(icon, item):
            self.deiconify()
            self.lift()

        def exit_app(icon, item):
            if self.bridge_process:
                self.bridge_process.terminate()
            if self.hyperion_process:
                self.hyperion_process.terminate()
            icon.stop()
            self.destroy()

        menu = pystray.Menu(pystray.MenuItem("Dashboard", show_window, default=True), pystray.MenuItem("Exit", exit_app))
        self.tray_icon = pystray.Icon("hyperion", image, "Hyperion", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    # ================= UI HELPERS =================

    def get_card_color(self):
        opacity = self.config.get("ui_opacity", 0.5)
        if opacity < 0.05:  # Very low = transparent
            return "transparent"
        # Cards need more visibility for text readability
        val = int(25 + (opacity * 30))  # Range: 25 to 55
        return f"#{val:02x}{val:02x}{val:02x}"

    def get_main_color(self):
        opacity = self.config.get("main_opacity", 0.3)
        if opacity < 0.15:  # Threshold for full transparency
            return "transparent"
        # Higher opacity = more visible grey
        val = int(20 + (opacity * 25))  # Range: 20 to 45
        return f"#{val:02x}{val:02x}{val:02x}"

    def refresh_visualizer_state(self):
        # Update orbs based on config state
        for i, device in enumerate(self.config.get("devices", [])):
            device_type = device.get("type", "rgb")
            if not device.get("physical_state", True):
                self.update_orb_color(i, "#222222")  # Off
            elif device.get("enabled", False) and device_type == "rgb":
                self.update_orb_color(i, THEME["pink"])  # Syncing (RGB only)
            else:
                self.update_orb_color(i, THEME["cyan"])  # Manual On (or CCT)

    # ================= TABS =================

    def show_sync(self):
        self.clear_content()
        card_bg = self.get_card_color()
        
        for i, device in enumerate(self.config.get("devices", [])):
            # Load State
            is_phys_on = device.get("physical_state", True)
            
            # Grey Out Logic
            border_col = "#444" if is_phys_on else "#222"
            text_col = THEME["white"] if is_phys_on else THEME["disabled"]
            power_col = THEME["cyan"] if is_phys_on else THEME["dim"]
            
            card = ctk.CTkFrame(self.content_area, fg_color=card_bg, corner_radius=10, border_width=1, border_color=border_col)
            card.pack(fill="x", pady=5)
            
            # --- POWER BUTTON ---
            def toggle_power(idx=i):
                curr = self.config["devices"][idx].get("physical_state", True)
                new_s = not curr
                
                # Update State First
                self.config["devices"][idx]["physical_state"] = new_s
                self.save_config()
                
                # Send Command
                self.send_power_toggle(idx, new_s)
                
                # Refresh UI (This destroys the current button, hence the PulseButton fix)
                self.show_sync()
                self.refresh_visualizer_state()

            power_btn = PulseButton(card, text="⏻", width=40, font=("Consolas", 14, "bold"),
                                   fg_color=power_col, hover_color=THEME["white"],
                                   command=toggle_power)
            power_btn.pack(side="left", padx=(15, 5), pady=15)

            # --- SYNC SWITCH (Only for RGB lights) ---
            device_type = device.get("type", "rgb")

            if device_type == "rgb":
                # RGB lights: Show sync switch
                is_sync_on = ctk.BooleanVar(value=device.get("enabled", False))

                def toggle_sync(v=is_sync_on, idx=i):
                    new_state = v.get()
                    self.config["devices"][idx]["enabled"] = new_state
                    self.save_config()

                    # Auto-start Hyperion if toggling to sync mode and Hyperion not running
                    if new_state and not self.is_hyperion_running():
                        hyperion_exe = self.config.get("hyperion_executable", "")
                        if hyperion_exe and os.path.exists(hyperion_exe):
                            print(f"[UI] Auto-starting Hyperion for device {self.config['devices'][idx]['name']}")
                            self.toggle_hyperion_manual()
                        else:
                            messagebox.showwarning("Hyperion Not Running",
                                "You enabled Hyperion sync, but Hyperion is not running.\n"
                                "Please set Hyperion executable path in Settings or start it manually.")

                    self.refresh_ui_keep_tab()
                    self.refresh_visualizer_state()

                sw_state = "normal" if is_phys_on else "disabled"
                sw = ctk.CTkSwitch(card, text=device["name"].upper(), variable=is_sync_on, command=toggle_sync, state=sw_state,
                                  progress_color=THEME["cyan"], button_color=THEME["white"], button_hover_color=THEME["pink"],
                                  font=("Consolas", 14, "bold"), text_color=text_col)
                sw.pack(side="left", padx=10, pady=20)

                # --- SLIDER ---
                val = device.get("brightness_multiplier", 1.0)
                slider_color = THEME["yellow"] if is_sync_on.get() else THEME["cyan"]
                if not is_phys_on: slider_color = THEME["dim"]

                def slide(v, idx=i):
                    self.config["devices"][idx]["brightness_multiplier"] = v
                    self.save_config()

                    # Smart brightness logic:
                    # - If not synced (enabled=false): Always send MQTT
                    # - If synced (enabled=true) but Hyperion not running: Send MQTT
                    # - If synced AND Hyperion running: Don't send (Hyperion will control it)
                    device_enabled = self.config["devices"][idx].get("enabled", False)
                    if not device_enabled or not self.is_hyperion_running():
                        self.set_manual_brightness(idx, v * 254)

                sw_state = "normal" if is_phys_on else "disabled"
                sl = ctk.CTkSlider(card, from_=0, to=1, command=lambda v, idx=i: slide(v, idx), state=sw_state,
                                  button_color=THEME["pink"] if is_phys_on else THEME["dim"], progress_color=slider_color)
                sl.set(val)
                sl.pack(side="right", padx=20, fill="x", expand=True)

                # Add brightness percentage label with warning for low brightness
                brightness_pct = int(val * 100)
                brightness_text = f"{brightness_pct}%"
                if brightness_pct < 30:
                    brightness_text += " ⚠"  # Warning for low brightness
                ctk.CTkLabel(card, text=brightness_text, font=("Consolas", 10),
                            text_color=THEME["yellow"] if brightness_pct < 30 else THEME["dim"]).pack(side="right", padx=5)
            else:
                # CCT lights: Show label only (no sync switch)
                label_text = device["name"].upper() + " [CCT - MANUAL ONLY]"
                ctk.CTkLabel(card, text=label_text, font=("Consolas", 14, "bold"),
                            text_color=text_col).pack(side="left", padx=10, pady=20)

                # Force enabled=false for CCT lights
                if device.get("enabled", False):
                    self.config["devices"][i]["enabled"] = False
                    self.save_config()

                # --- SLIDER (brightness only) ---
                val = device.get("brightness_multiplier", 1.0)
                slider_color = THEME["cyan"]
                if not is_phys_on: slider_color = THEME["dim"]

                def slide(v, idx=i):
                    self.config["devices"][idx]["brightness_multiplier"] = v
                    self.save_config()
                    # Always send brightness command for immediate feedback
                    self.set_manual_brightness(idx, v * 254)

                sw_state = "normal" if is_phys_on else "disabled"
                sl = ctk.CTkSlider(card, from_=0, to=1, command=lambda v, idx=i: slide(v, idx), state=sw_state,
                                  button_color=THEME["pink"] if is_phys_on else THEME["dim"], progress_color=slider_color)
                sl.set(val)
                sl.pack(side="right", padx=20, fill="x", expand=True)

        # SCENES
        ctk.CTkLabel(self.content_area, text="SCENES", font=("Consolas", 14, "bold"), text_color=THEME["dim"]).pack(pady=(30, 5))
        grid = ctk.CTkFrame(self.content_area, fg_color="transparent")
        grid.pack(fill="x", pady=5)
        
        scenes = [("📖 READ", "READ", THEME["orange"]), ("☀ DAY", "DAY", THEME["yellow"]), ("🎬 MOVIE", "MOVIE", THEME["pink"]), ("🌑 NIGHT", "NIGHT", "#6600cc")]
        for idx, (label, mode, col) in enumerate(scenes):
            PulseButton(grid, text=label, fg_color=col, text_color="black" if mode=="DAY" else "white", 
                       font=("Consolas", 12, "bold"), height=50, command=lambda m=mode: self.apply_scene(m)).grid(row=0, column=idx, padx=5, sticky="ew")
            grid.grid_columnconfigure(idx, weight=1)

    # ================= REST OF UI =================

    def create_sidebar(self):
        col = self.get_base_color()
        # Sidebar is child of main_container (not root) so it can show bg_label when transparent
        self.sidebar = ctk.CTkFrame(self.main_container, width=220, corner_radius=0, fg_color=col)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.lift()  # Ensure sidebar is above background
        
        title = ctk.CTkLabel(self.sidebar, text="HYPERION", font=("Consolas", 26, "bold"), text_color=THEME["cyan"])
        title.pack(pady=40)
        
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.pack(pady=10)
        self.status_indic = ctk.CTkButton(self.status_frame, text="", width=15, height=15, corner_radius=10, fg_color=THEME["pink"], hover=False)
        self.status_indic.pack(side="left", padx=5)
        ctk.CTkLabel(self.status_frame, text="BRIDGE STATUS", font=("Consolas", 10)).pack(side="left")

        # Hyperion status
        self.hyperion_status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.hyperion_status_frame.pack(pady=10)
        self.hyperion_status_indic = ctk.CTkButton(self.hyperion_status_frame, text="", width=15, height=15, corner_radius=10, fg_color=THEME["pink"], hover=False)
        self.hyperion_status_indic.pack(side="left", padx=5)
        ctk.CTkLabel(self.hyperion_status_frame, text="HYPERION STATUS", font=("Consolas", 10)).pack(side="left")

        self.create_menu_btn("DASHBOARD", self.show_sync)
        self.create_menu_btn("MANUAL OVR", self.show_manual)
        self.create_menu_btn("SETTINGS", self.show_settings)

        # Manual Hyperion control button
        self.btn_hyperion = PulseButton(self.sidebar, text="START HYPERION", height=35, font=("Consolas", 11, "bold"),
                                        fg_color=THEME["orange"], hover_color=THEME["yellow"], command=self.toggle_hyperion_manual)
        self.btn_hyperion.pack(fill="x", pady=5, padx=20)

        # ARCADE MODE - Rainbow animated button
        ctk.CTkLabel(self.sidebar, text="━━━━━━━━━━━━━━━━", font=("Consolas", 8), text_color=THEME["dim"]).pack(pady=(20, 5))
        self.arcade_button = RainbowArcadeButton(
            self.sidebar,
            text="🎮 ARCADE MODE 🎮",
            height=50,
            font=("Consolas", 13, "bold"),
            fg_color=THEME["pink"],
            text_color="#000000",
            command=self.launch_arcade_game
        )
        self.arcade_button.pack(fill="x", pady=10, padx=20)
        ctk.CTkLabel(self.sidebar, text="WW2 DOGFIGHT SIMULATOR", font=("Consolas", 7), text_color=THEME["yellow"]).pack()

        self.alert_label = ctk.CTkLabel(self.sidebar, text="⬇ CLICK TO START ⬇", font=("Consolas", 14, "bold"), text_color=THEME["yellow"])
        self.alert_label.pack(side="bottom", pady=(0, 5))
        
        self.btn_bridge = PulseButton(self.sidebar, text="INITIATE LINK", height=40, font=("Consolas", 12, "bold"), 
                                     fg_color=THEME["pink"], hover_color=THEME["cyan"], command=self.toggle_bridge)
        self.btn_bridge.pack(side="bottom", pady=(0, 30), padx=20, fill="x")
        threading.Thread(target=self._animate_alert, daemon=True).start()

    def create_menu_btn(self, text, cmd):
        ctk.CTkButton(self.sidebar, text=text, fg_color="transparent", text_color=THEME["white"], 
                     hover_color=THEME["pink"], anchor="w", font=("Consolas", 12), command=cmd).pack(fill="x", pady=2, padx=10)

    def create_main_area(self):
        # Main frame is child of main_container (not root) so it can show bg_label when transparent
        self.main_frame = ctk.CTkFrame(self.main_container, fg_color=self.get_main_color())
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_frame.lift()  # Ensure main area is above background
        
        # Keep canvas frame with dark background for visualization visibility
        self.twin_frame = ctk.CTkFrame(self.main_frame, height=300, fg_color="#050505")
        self.twin_frame.pack(fill="x", pady=(0, 20))
        self.twin_frame.pack_propagate(False)
        
        self.create_digital_twin_canvas()

        self.content_area = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent", label_text="")
        self.content_area.pack(fill="both", expand=True)
        self.show_sync() 

        # LOGO (Top Right Overlay)
        if os.path.exists(ICON_PNG):
            try:
                logo_img = ctk.CTkImage(Image.open(ICON_PNG), size=(100, 100))
                self.logo_label = ctk.CTkLabel(self.main_frame, text="", image=logo_img)
                self.logo_label.place(relx=1.0, x=-10, y=0, anchor="ne")
                self.logo_label.lift()
            except: pass

    def create_digital_twin_canvas(self):
        self.canvas = tk.Canvas(self.twin_frame, bg="#050505", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Bigger Scale
        w, h = 800, 300
        cx, cy = w/2, h/2
        
        self.canvas.create_rectangle(cx-140, cy-80, cx+140, cy+80, outline=THEME["cyan"], width=4)
        self.canvas.create_line(cx-140, cy+90, cx+140, cy+90, fill=THEME["pink"], width=3)
        
        self.orbs = {}
        # Massive Orbs
        self.orbs[0] = self.create_orb(cx, cy, 160, "GLEDOPTO") 
        self.orbs[1] = self.create_orb(cx-220, cy+40, 60, "TRADFRI")
        self.orbs[2] = self.create_orb(cx+220, cy-60, 70, "AQARA")

    def create_orb(self, x, y, size, label):
        glow = self.canvas.create_oval(x-size, y-size, x+size, y+size, fill="", outline="#333333", width=2, dash=(4, 4))
        core = self.canvas.create_oval(x-20, y-20, x+20, y+20, fill="#222222", outline=THEME["white"], width=2)
        self.canvas.create_text(x, y+size+20, text=label, fill=THEME["dim"], font=("Consolas", 10, "bold"))
        return {"glow": glow, "core": core}

    def update_orb_color(self, idx, color_hex):
        if idx in self.orbs:
            self.canvas.itemconfig(self.orbs[idx]["core"], fill=color_hex)
            self.canvas.itemconfig(self.orbs[idx]["glow"], outline=color_hex)

    # ================= OTHERS =================

    def clear_content(self):
        for widget in self.content_area.winfo_children(): widget.destroy()

    def refresh_ui_keep_tab(self):
        self.show_sync() # Simplified refresh

    def show_manual(self):
        self.clear_content()
        card_bg = self.get_card_color()
        for i, device in enumerate(self.config.get("devices", [])):
            if device.get("enabled", True): continue

            card = ctk.CTkFrame(self.content_area, fg_color=card_bg, corner_radius=10, border_width=1, border_color="#444")
            card.pack(fill="x", pady=10)

            # Device header row
            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.pack(fill="x", padx=20, pady=(15, 5))

            ctk.CTkLabel(
                header_row,
                text=device["name"].upper(),
                font=("Consolas", 16, "bold"),
                text_color=THEME["cyan"]
            ).pack(side="left")

            # Device type badge
            dtype = device.get("type", "rgb").upper()
            ctk.CTkLabel(
                header_row,
                text=f"[{dtype}]",
                font=("Consolas", 10),
                text_color=THEME["dim"]
            ).pack(side="right")

            # Controls container
            controls = ctk.CTkFrame(card, fg_color="transparent")
            controls.pack(fill="x", padx=10, pady=(0, 15))

            if device.get("type") == "cct":
                # CCT: Temperature Slider
                temp_row = ctk.CTkFrame(controls, fg_color="transparent")
                temp_row.pack(fill="x", pady=5)

                ctk.CTkLabel(temp_row, text="COOL", font=("Consolas", 10, "bold"), text_color=THEME["cyan"]).pack(side="left")
                ts = ctk.CTkSlider(
                    temp_row,
                    from_=150,
                    to=370,
                    command=lambda v, idx=i: self.send_manual_temp(idx, v),
                    button_color=THEME["yellow"],
                    progress_color=THEME["orange"]
                )
                ts.set(370)
                ts.pack(side="left", fill="x", expand=True, padx=10)
                ctk.CTkLabel(temp_row, text="WARM", font=("Consolas", 10, "bold"), text_color=THEME["yellow"]).pack(side="left")

                # Brightness slider for CCT
                bright_row = ctk.CTkFrame(controls, fg_color="transparent")
                bright_row.pack(fill="x", pady=5)
                ctk.CTkLabel(bright_row, text="BRIGHTNESS", font=("Consolas", 10), text_color=THEME["dim"]).pack(side="left")
                bs = ctk.CTkSlider(
                    bright_row,
                    from_=1,
                    to=254,
                    command=lambda v, idx=i: self.set_manual_brightness(idx, v),
                    button_color=THEME["cyan"],
                    progress_color=THEME["dim"]
                )
                bs.set(254)
                bs.pack(side="left", fill="x", expand=True, padx=10)
            else:
                # RGB: Embedded Color Picker
                def make_color_handler(idx):
                    def handler(device_idx, color, brightness=None):
                        self.send_manual_color(device_idx, color)
                        self.update_orb_color(device_idx, color)
                        if brightness is not None:
                            self.set_manual_brightness(device_idx, brightness)
                    return handler

                picker = VaporwaveColorPicker(
                    controls,
                    device_idx=i,
                    on_color_change=make_color_handler(i),
                    initial_color=THEME["pink"]
                )
                picker.pack(fill="x", pady=5)

    def show_settings(self):
        self.clear_content()
        card = ctk.CTkFrame(self.content_area, fg_color="transparent", corner_radius=10, border_width=1, border_color="#444")
        card.pack(fill="x", pady=10)

        # Hyperion Executable Path
        ctk.CTkLabel(card, text="HYPERION EXECUTABLE PATH", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(20,5))
        hyperion_path_frame = ctk.CTkFrame(card, fg_color="transparent")
        hyperion_path_frame.pack(fill="x", padx=20, pady=(0,5))

        hyperion_path_entry = ctk.CTkEntry(hyperion_path_frame, placeholder_text="Path to hyperiond.exe")
        hyperion_path_entry.insert(0, self.config.get("hyperion_executable", ""))
        hyperion_path_entry.pack(side="left", fill="x", expand=True, padx=(0,5))

        def browse_hyperion():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="Select Hyperion Executable",
                filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
            )
            if path:
                hyperion_path_entry.delete(0, tk.END)
                hyperion_path_entry.insert(0, path)
                self.update_setting("hyperion_executable", path)

        ctk.CTkButton(hyperion_path_frame, text="BROWSE", width=80, command=browse_hyperion).pack(side="left")
        ctk.CTkLabel(card, text="Optional: Auto-start Hyperion when clicking INITIATE LINK", font=("Consolas", 8), text_color=THEME["dim"]).pack(anchor="w", padx=20, pady=(0,10))

        # Color Warmth
        ctk.CTkLabel(card, text="COLOR WARMTH (REDUCE BLUE/GREEN)", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(20,5))
        warmth_slider = ctk.CTkSlider(card, from_=1.0, to=3.0, command=lambda v: self.update_setting("color_warmth", v), button_color=THEME["orange"])
        warmth_slider.set(self.config.get("color_warmth", 2.5))
        warmth_slider.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="Lower = More Blue/Green | Higher = Warmer/Orange/Red", font=("Consolas", 8), text_color=THEME["dim"]).pack(anchor="w", padx=20)

        # Throttle Interval
        ctk.CTkLabel(card, text="THROTTLE INTERVAL (seconds)", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(20,5))
        throttle_slider = ctk.CTkSlider(card, from_=0.1, to=2.0, command=lambda v: self.update_setting("throttle_interval", v), button_color=THEME["cyan"])
        throttle_slider.set(self.config.get("throttle_interval", 1.0))
        throttle_slider.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="Lower = Faster updates (more MQTT traffic) | Higher = Slower (less traffic)", font=("Consolas", 8), text_color=THEME["dim"]).pack(anchor="w", padx=20, pady=(0,20))

        # UI Opacity Settings
        ctk.CTkLabel(card, text="BACKGROUND BRIGHTNESS", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(10,5))
        bg = ctk.CTkSlider(card, from_=0.1, to=1.0, command=lambda v: self.update_setting("bg_brightness", v), button_color=THEME["cyan"])
        bg.set(self.config.get("bg_brightness", 0.5))
        bg.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="Higher = Brighter background visible through transparent UI", font=("Consolas", 8), text_color=THEME["yellow"]).pack(anchor="w", padx=20, pady=(0,20))

        ctk.CTkLabel(card, text="UI CARD VISIBILITY", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(10,5))
        ui = ctk.CTkSlider(card, from_=0.0, to=1.0, command=lambda v: self.update_setting("ui_opacity", v), button_color=THEME["white"])
        ui.set(self.config.get("ui_opacity", 0.5))
        ui.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="Below 5% = Transparent | Higher = More visible (text readability)", font=("Consolas", 8), text_color=THEME["dim"]).pack(anchor="w", padx=20, pady=(0,20))

        # Base Frame Opacity (Sidebar)
        ctk.CTkLabel(card, text="SIDEBAR OPACITY", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(10,5))
        base = ctk.CTkSlider(card, from_=0.0, to=1.0, command=lambda v: self.update_setting("base_opacity", v), button_color=THEME["yellow"])
        base.set(self.config.get("base_opacity", 0.8))
        base.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="Below 15% = Fully transparent | Higher = More visible", font=("Consolas", 8), text_color=THEME["dim"]).pack(anchor="w", padx=20, pady=(0,20))

        # Main Area Opacity (NEW)
        ctk.CTkLabel(card, text="MAIN AREA OPACITY", font=("Consolas", 12)).pack(anchor="w", padx=20, pady=(10,5))
        main_opacity_slider = ctk.CTkSlider(card, from_=0.0, to=1.0, command=lambda v: self.update_setting("main_opacity", v), button_color=THEME["pink"])
        main_opacity_slider.set(self.config.get("main_opacity", 0.3))
        main_opacity_slider.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(card, text="Below 15% = Fully transparent | Higher = More visible", font=("Consolas", 8), text_color=THEME["dim"]).pack(anchor="w", padx=20, pady=(0,20))

    # ================= COMMS =================

    def toggle_bridge(self):
        if self.bridge_process and self.bridge_process.poll() is None:
            # Stop both bridge and Hyperion
            print("[UI] Stopping bridge...")
            self.bridge_process.terminate()
            self.bridge_process = None

            if self.hyperion_process and self.hyperion_process.poll() is None:
                print("[UI] Stopping Hyperion...")
                self.hyperion_process.terminate()
                self.hyperion_process = None

            self.status_indic.configure(fg_color=THEME["pink"])
            self.btn_bridge.configure(text="INITIATE LINK", fg_color=THEME["pink"])
            self.alert_label.pack(side="bottom", pady=(0, 5), before=self.btn_bridge)
        else:
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                # Start Hyperion first (if executable configured)
                hyperion_exe = self.config.get("hyperion_executable", "")
                if hyperion_exe and os.path.exists(hyperion_exe):
                    print(f"[UI] Starting Hyperion from {hyperion_exe}")
                    self.hyperion_process = subprocess.Popen(
                        [hyperion_exe],
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    # Wait for Hyperion to initialize
                    time.sleep(2)
                else:
                    print("[UI] Warning: Hyperion executable not configured or not found")
                    print("[UI] Bridge will attempt to connect to existing Hyperion instance")

                # Start bridge
                print("[UI] Starting bridge...")
                self.bridge_process = subprocess.Popen(
                    [sys.executable, BRIDGE_SCRIPT],
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                self.status_indic.configure(fg_color=THEME["cyan"])
                self.btn_bridge.configure(text="TERMINATE LINK", fg_color=THEME["cyan"])
                self.alert_label.pack_forget()
            except Exception as e:
                messagebox.showerror("Error", f"Could not start bridge: {e}")

    def toggle_hyperion_manual(self):
        """Manually start/stop Hyperion without affecting bridge."""
        if self.hyperion_process and self.hyperion_process.poll() is None:
            print("[UI] Stopping Hyperion manually...")
            self.hyperion_process.terminate()
            self.hyperion_process = None
            self.hyperion_status_indic.configure(fg_color=THEME["pink"])
            self.btn_hyperion.configure(text="START HYPERION", fg_color=THEME["orange"])
        else:
            hyperion_exe = self.config.get("hyperion_executable", "")
            if hyperion_exe and os.path.exists(hyperion_exe):
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    print(f"[UI] Starting Hyperion from {hyperion_exe}")
                    self.hyperion_process = subprocess.Popen(
                        [hyperion_exe],
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self.hyperion_status_indic.configure(fg_color=THEME["cyan"])
                    self.btn_hyperion.configure(text="STOP HYPERION", fg_color=THEME["cyan"])
                except Exception as e:
                    messagebox.showerror("Error", f"Could not start Hyperion: {e}")
            else:
                messagebox.showwarning("Configuration Required",
                    "Please set Hyperion executable path in Settings first")

    def check_hyperion_status(self):
        """Periodically check if Hyperion is running and update indicator."""
        if self.is_hyperion_running():
            self.hyperion_status_indic.configure(fg_color=THEME["cyan"])
            self.btn_hyperion.configure(text="STOP HYPERION", fg_color=THEME["cyan"])
        else:
            self.hyperion_status_indic.configure(fg_color=THEME["pink"])
            self.btn_hyperion.configure(text="START HYPERION", fg_color=THEME["orange"])

        # Check again in 2 seconds
        self.after(2000, self.check_hyperion_status)

    def launch_arcade_game(self):
        """Launch the WW2 Dogfight arcade game with screen flash effect."""
        # Screen flash effect
        threading.Thread(target=self._arcade_launch_flash, daemon=True).start()

        # Locate the game
        game_paths = [
            os.path.join(os.path.dirname(SCRIPT_DIR), "Git-Command-Builder", "GitSyncGUI", "main.py"),
            os.path.join(os.path.dirname(SCRIPT_DIR), "Git-Command-Builder", "GitSyncGUI", "vfx_engine.py"),
            "C:\\Users\\Box\\Documents\\GitHub\\Git-Command-Builder\\GitSyncGUI\\main.py",
            "C:\\Users\\Box\\Documents\\GitHub\\Git-Command-Builder\\GitSyncGUI\\vfx_engine.py",
        ]

        game_script = None
        for path in game_paths:
            if os.path.exists(path):
                game_script = path
                break

        if game_script:
            try:
                print(f"[ARCADE] Launching game from: {game_script}")
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.Popen(
                    [sys.executable, game_script],
                    startupinfo=startupinfo
                )
            except Exception as e:
                messagebox.showerror("Launch Failed", f"Could not start arcade game:\n{e}")
        else:
            messagebox.showwarning(
                "Game Not Found",
                "WW2 Dogfight game not found!\n\n"
                "Expected location:\n"
                "C:\\Users\\Box\\Documents\\GitHub\\Git-Command-Builder\\GitSyncGUI\\main.py"
            )

    def _arcade_launch_flash(self):
        """Create a screen flash effect when launching arcade."""
        try:
            original_bg = self.configure("fg_color")

            # Flash sequence
            flash_colors = [
                THEME["white"],
                THEME["cyan"],
                THEME["pink"],
                THEME["yellow"],
                THEME["cyan"],
                THEME["bg"]
            ]

            for color in flash_colors:
                if not self.winfo_exists(): return
                self.configure(fg_color=color)
                time.sleep(0.05)

            # Restore
            if not self.winfo_exists(): return
            self.configure(fg_color=THEME["bg"])

        except (tk.TclError, RuntimeError):
            pass

    def check_bridge_running(self):
        self.status_indic.configure(fg_color=THEME["pink"])
        self.alert_label.pack(side="bottom", pady=(0, 5), before=self.btn_bridge)

    def _animate_alert(self):
        colors = [THEME["yellow"], THEME["pink"], THEME["cyan"], THEME["white"]]
        i = 0
        while self.alert_running:
            if self.bridge_process is None: 
                try:
                    self.alert_label.configure(text_color=colors[i % len(colors)])
                    i += 1
                except: pass
            time.sleep(0.2)

    def send_power_toggle(self, idx, state):
        if not self.mqtt_client: return
        t = self.config["devices"][idx]["topic"]
        # Explicitly ensure boolean state for ON/OFF command
        cmd = "ON" if bool(state) else "OFF"
        payload = {"state": cmd}
        print(f"[DEBUG] MQTT Publish -> Topic: {t} | Payload: {payload}")
        try:
            result = self.mqtt_client.publish(t, json.dumps(payload), qos=1)
            result.wait_for_publish(timeout=1.0)
            if result.rc != 0:
                print(f"[ERROR] MQTT Publish failed with code: {result.rc}")
        except Exception as e:
            print(f"[ERROR] MQTT Exception during publish: {e}")

    def send_manual_color(self, idx, hex_c):
        print(f"[MQTT] send_manual_color called: idx={idx}, color={hex_c}")
        if not self.mqtt_client:
            print("[MQTT] ERROR: No MQTT client!")
            return
        t = self.config["devices"][idx]["topic"]
        h = hex_c.lstrip('#')
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        payload = {"state":"ON", "color":{"r":r,"g":g,"b":b}, "transition":0.1}
        print(f"[MQTT] Publishing to {t}: {payload}")
        self.mqtt_client.publish(t, json.dumps(payload))

    def send_manual_temp(self, idx, mireds):
        if not self.mqtt_client: return
        t = self.config["devices"][idx]["topic"]
        self.mqtt_client.publish(t, json.dumps({"state":"ON", "color_temp":int(mireds), "transition":0.1}))

    def set_manual_brightness(self, idx, val):
        if not self.mqtt_client: return
        t = self.config["devices"][idx]["topic"]
        self.mqtt_client.publish(t, json.dumps({"state":"ON", "brightness":int(val), "transition":0.1}))

    def get_base_color(self):
        opacity = self.config.get("base_opacity", 0.8)
        if opacity < 0.15:  # Threshold for full transparency
            return "transparent"
        # Higher opacity = more visible grey
        val = int(20 + (opacity * 25))  # Range: 20 to 45
        return f"#{val:02x}{val:02x}{val:02x}"

    def update_setting(self, key, val):
        self.config[key] = val
        self.save_config()
        if key == "bg_brightness":
            self.apply_bg_brightness(val)
        elif key == "ui_opacity":
            self.refresh_card_colors()
        elif key == "base_opacity":
            self.refresh_base_colors()
        elif key == "main_opacity":
            self.refresh_main_colors()

    def refresh_base_colors(self):
        col = self.get_base_color()
        try:
            self.sidebar.configure(fg_color=col)
        except: pass

    def refresh_main_colors(self):
        col = self.get_main_color()
        try:
            self.main_frame.configure(fg_color=col)
        except: pass

    def refresh_card_colors(self):
        new_color = self.get_card_color()
        for widget in self.content_area.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                try:
                    widget.configure(fg_color=new_color)
                except: pass

    def apply_scene(self, mode):
        threading.Thread(target=self._apply_scene_thread, args=(mode,), daemon=True).start()

    def _apply_scene_thread(self, mode):
        try:
            if mode != "MOVIE" and self.bridge_process: self.toggle_bridge() 
            elif mode == "MOVIE" and not self.bridge_process: self.toggle_bridge() 

            if mode == "MOVIE": time.sleep(0.5)

            for i, dev in enumerate(self.config["devices"]):
                dev["physical_state"] = True 
                
                if mode == "MOVIE":
                    dev["enabled"] = True
                    dev["brightness_multiplier"] = 1.0
                elif mode == "READ":
                    dev["enabled"] = False 
                    if dev.get("type") == "cct":
                        self.send_manual_temp(i, 370)
                        self.set_manual_brightness(i, 76)
                    else:
                        self.send_manual_color(i, "#ff4400")
                        self.set_manual_brightness(i, 76)
                elif mode == "DAY":
                    dev["enabled"] = False
                    if dev.get("type") == "cct":
                        self.send_manual_temp(i, 250)
                        self.set_manual_brightness(i, 254)
                    else:
                        self.send_manual_color(i, "#ffaa00")
                        self.set_manual_brightness(i, 254)
                elif mode == "NIGHT":
                    dev["enabled"] = False
                    if dev.get("type") == "cct":
                        self.send_manual_temp(i, 370)
                        self.set_manual_brightness(i, 25)
                    else:
                        self.send_manual_color(i, "#220044")
                        self.set_manual_brightness(i, 50)

            self.save_config()
            self.after(0, self.show_sync)
            self.after(0, self.refresh_visualizer_state)
        except Exception as e:
            print(f"Scene Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", choices=["on", "off"], help="Set all lights on/off")
    args = parser.parse_args()

    if args.state:
        # Headless Mode
        print(f"[HEADLESS] Setting lights to {args.state.upper()}...")
        
        # Load Config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        else:
            print("[HEADLESS] Config file not found!")
            sys.exit(1)

        # Connect MQTT
        if mqtt:
            try:
                # Setup Client
                try:
                    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"vap_cli_{random.randint(1000,9999)}")
                except AttributeError:
                    client = mqtt.Client(client_id=f"vap_cli_{random.randint(1000,9999)}")
                
                broker = config.get("mqtt_broker", "127.0.0.1")
                client.connect(broker, 1883)
                client.loop_start()
                time.sleep(0.5) # Wait for connection

                # Send Commands
                cmd = "ON" if args.state == "on" else "OFF"
                
                for i, dev in enumerate(config.get("devices", [])):
                    topic = dev.get("topic")
                    if topic:
                        payload = {"state": cmd}
                        client.publish(topic, json.dumps(payload), qos=1)
                        print(f"[HEADLESS] Sent {cmd} to {dev.get('name')}")
                        
                        # Update Config State
                        dev["physical_state"] = (cmd == "ON")
                
                client.loop_stop()
                client.disconnect()
                
                # Save Config State
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=4)
                    
            except Exception as e:
                print(f"[HEADLESS] Error: {e}")
        else:
            print("[HEADLESS] paho-mqtt not installed")

    else:
        app = VaporwaveApp()
        app.mainloop()
