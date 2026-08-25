import tkinter as tk
from tkinter import ttk, messagebox
import os
from dotenv import load_dotenv, set_key, find_dotenv
from rtsp_config import load_rtsp_config, set_rtsp_config, get_rtsp_config, cleanup_rtsp_config, delete_rtsp_config
import sys
import settings_service
from notification_service import NotificationService

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class SettingsPage:
    def __init__(self, root, main_app):
        self.root = root
        self.main_app = main_app
        self.settings_frame = None
        self.rtsp_widgets = {}  # Store RTSP widgets per device
        
        # Use same color scheme as main app
        self.bg_dark = "#0a0a0a"
        self.bg_darker = "#000000"
        self.bg_card = "#1a1a1a"
        self.bg_header = "#111111"
        self.bg_input = "#2a2a2a"
        self.text_primary = "#ffffff"
        self.text_secondary = "#b0b0b0"
        self.accent = "#00d4ff"
        self.accent_hover = "#00b8e6"
        self.success = "#00ff88"
        self.error = "#ff4444"
        
        self.create_settings_page()
        
    def create_settings_page(self):
        """Create settings page UI"""
        # Hide main frame
        self.main_app.main_frame.pack_forget()
        
        # Create settings frame
        self.settings_frame = tk.Frame(self.root, bg=self.bg_dark)
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = tk.Frame(self.settings_frame, bg=self.bg_header, height=70)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Add subtle border effect
        border_frame = tk.Frame(header_frame, bg="#1a1a1a", height=1)
        border_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Back button
        back_btn = tk.Button(
            header_frame,
            text="← Back",
            font=("Segoe UI", 12),
            bg=self.bg_card,
            fg=self.text_primary,
            activebackground=self.accent,
            activeforeground=self.bg_dark,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.go_back,
            padx=20,
            pady=8,
            bd=0,
            highlightthickness=0
        )
        back_btn.pack(side=tk.LEFT, padx=30, pady=15)
        
        # Add hover effect
        def on_enter_back(e):
            back_btn.config(bg="#2a2a2a")
        def on_leave_back(e):
            back_btn.config(bg=self.bg_card)
        back_btn.bind("<Enter>", on_enter_back)
        back_btn.bind("<Leave>", on_leave_back)
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="Settings",
            font=("Segoe UI", 20, "bold"),
            bg=self.bg_header,
            fg=self.text_primary
        )
        title_label.pack(side=tk.LEFT, padx=30, pady=20)
        
        # Content area with scrollbar
        canvas = tk.Canvas(self.settings_frame, bg=self.bg_dark, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_dark)
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        def on_mousewheel_windows(event):
            # Windows and Mac - event.delta
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def on_mousewheel_linux(event):
            # Linux - event.num
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
        
        def bind_mousewheel(event):
            # Windows and Mac
            canvas.bind_all("<MouseWheel>", on_mousewheel_windows)
            # Linux
            canvas.bind_all("<Button-4>", on_mousewheel_linux)
            canvas.bind_all("<Button-5>", on_mousewheel_linux)
        
        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)
        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Store canvas reference
        self.settings_canvas = canvas
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Main content container
        content_frame = tk.Frame(scrollable_frame, bg=self.bg_dark)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=60, pady=50)
        
        # API Credentials Section
        self.create_api_section(content_frame)

        # Alert / Notifications Section
        self.create_notifications_section(content_frame)
        
        # RTSP Configuration Section
        self.create_rtsp_section(content_frame)
        
        # Save button at bottom
        self.create_save_button(content_frame)
    
    def create_api_section(self, parent):
        """Create API credentials section"""
        # API section card
        api_card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT)
        api_card.pack(fill=tk.X, pady=(0, 30))
        
        # Section title
        api_title = tk.Label(
            api_card,
            text="API Credentials",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        )
        api_title.pack(pady=(30, 20), padx=40, anchor="w")
        
        # Input container
        input_container = tk.Frame(api_card, bg=self.bg_card)
        input_container.pack(fill=tk.X, padx=40, pady=(0, 30))
        
        # Load .env file
        dotenv_path = resource_path(".env")
        load_dotenv(dotenv_path)
        current_auth = os.getenv("Authorization", "")
        current_x_term = os.getenv("X-Term-Id", "")
        
        # Authorization field
        auth_label = tk.Label(
            input_container,
            text="Authorization",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor="w"
        )
        auth_label.pack(fill=tk.X, pady=(0, 8))
        
        self.auth_entry = tk.Entry(
            input_container,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            highlightcolor=self.accent
        )
        self.auth_entry.insert(0, current_auth)
        self.auth_entry.pack(fill=tk.X, pady=(0, 20), ipady=12, ipadx=15)
        
        # X-Term-Id field
        xterm_label = tk.Label(
            input_container,
            text="X-Term-Id",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
            anchor="w"
        )
        xterm_label.pack(fill=tk.X, pady=(0, 8))
        
        self.xterm_entry = tk.Entry(
            input_container,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            highlightcolor=self.accent
        )
        self.xterm_entry.insert(0, current_x_term)
        self.xterm_entry.pack(fill=tk.X, pady=(0, 0), ipady=12, ipadx=15)

    def create_notifications_section(self, parent):
        """Create the Alert & Notifications settings section."""
        notif_settings = settings_service.load_settings()

        card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT)
        card.pack(fill=tk.X, pady=(0, 30))

        # --- Section title ---
        tk.Label(
            card,
            text="🔔 Alert & Notification Settings",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
        ).pack(pady=(30, 5), padx=40, anchor="w")

        tk.Label(
            card,
            text="Choose when you'd like to be alerted and how.",
            font=("Segoe UI", 10),
            bg=self.bg_card,
            fg=self.text_secondary,
        ).pack(padx=40, anchor="w", pady=(0, 20))

        content = tk.Frame(card, bg=self.bg_card)
        content.pack(fill=tk.X, padx=40, pady=(0, 30))

        # --- Alert types ---
        self._notif_motion_var = tk.BooleanVar(value=notif_settings.get("alert_motion", True))
        self._notif_person_var = tk.BooleanVar(value=notif_settings.get("alert_person", True))
        self._notif_vehicle_var = tk.BooleanVar(value=notif_settings.get("alert_vehicle", False))

        tk.Label(
            content,
            text="Alert me when the camera detects:",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_card,
            fg=self.text_primary,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        def _chk(parent, text, var, row, col):
            cb = tk.Checkbutton(
                parent,
                text=text,
                variable=var,
                font=("Segoe UI", 11),
                bg=self.bg_card,
                fg=self.text_primary,
                activebackground=self.bg_card,
                activeforeground=self.text_primary,
                selectcolor=self.bg_input,
                relief=tk.FLAT,
                cursor="hand2",
            )
            cb.grid(row=row, column=col, sticky="w", padx=(0, 20), pady=4)
            return cb

        _chk(content, "Any Movement", self._notif_motion_var, 1, 0)
        _chk(content, "A Person", self._notif_person_var, 1, 1)
        _chk(content, "A Vehicle  (AI cameras only)", self._notif_vehicle_var, 1, 2)

        tk.Label(
            content,
            text="Note: Person & vehicle detection requires a camera model with AI detection\n"
                 "(e.g. C120, C225, C325WB). Older models support movement only.",
            font=("Segoe UI", 9),
            bg=self.bg_card,
            fg=self.text_secondary,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 16))

        # --- Sound toggle ---
        self._notif_sound_var = tk.BooleanVar(value=notif_settings.get("alert_sound", True))
        sound_row = tk.Frame(content, bg=self.bg_card)
        sound_row.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 8))
        tk.Checkbutton(
            sound_row,
            text="Play a sound with each alert",
            variable=self._notif_sound_var,
            font=("Segoe UI", 11),
            bg=self.bg_card,
            fg=self.text_primary,
            activebackground=self.bg_card,
            activeforeground=self.text_primary,
            selectcolor=self.bg_input,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        # --- Debounce ---
        debounce_row = tk.Frame(content, bg=self.bg_card)
        debounce_row.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 8))
        tk.Label(
            debounce_row,
            text="Wait at least",
            font=("Segoe UI", 11),
            bg=self.bg_card,
            fg=self.text_primary,
        ).pack(side=tk.LEFT)

        self._notif_debounce_var = tk.StringVar(
            value=str(notif_settings.get("debounce_seconds", 30))
        )
        debounce_entry = tk.Entry(
            debounce_row,
            textvariable=self._notif_debounce_var,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            width=5,
            justify="center",
        )
        debounce_entry.pack(side=tk.LEFT, padx=8, ipady=4)
        tk.Label(
            debounce_row,
            text="seconds between alerts for the same camera and event type.",
            font=("Segoe UI", 11),
            bg=self.bg_card,
            fg=self.text_primary,
        ).pack(side=tk.LEFT)

        # --- Quiet hours ---
        self._notif_quiet_var = tk.BooleanVar(
            value=notif_settings.get("quiet_hours_enabled", False)
        )
        quiet_row = tk.Frame(content, bg=self.bg_card)
        quiet_row.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 4))
        tk.Checkbutton(
            quiet_row,
            text="Don't disturb me between",
            variable=self._notif_quiet_var,
            font=("Segoe UI", 11),
            bg=self.bg_card,
            fg=self.text_primary,
            activebackground=self.bg_card,
            activeforeground=self.text_primary,
            selectcolor=self.bg_input,
            relief=tk.FLAT,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        self._notif_quiet_start_var = tk.StringVar(
            value=notif_settings.get("quiet_hours_start", "22:00")
        )
        self._notif_quiet_end_var = tk.StringVar(
            value=notif_settings.get("quiet_hours_end", "07:00")
        )
        tk.Entry(
            quiet_row,
            textvariable=self._notif_quiet_start_var,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            width=6,
            justify="center",
        ).pack(side=tk.LEFT, padx=6, ipady=4)
        tk.Label(quiet_row, text="and", font=("Segoe UI", 11),
                 bg=self.bg_card, fg=self.text_primary).pack(side=tk.LEFT)
        tk.Entry(
            quiet_row,
            textvariable=self._notif_quiet_end_var,
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            width=6,
            justify="center",
        ).pack(side=tk.LEFT, padx=6, ipady=4)
        tk.Label(quiet_row, text="(HH:MM, 24-hour clock)",
                 font=("Segoe UI", 9),
                 bg=self.bg_card, fg=self.text_secondary).pack(side=tk.LEFT, padx=4)

        # --- Test / Restore buttons ---
        btn_row = tk.Frame(content, bg=self.bg_card)
        btn_row.grid(row=6, column=0, columnspan=3, sticky="w", pady=(16, 0))

        def _test_notification():
            svc = NotificationService(settings_service.load_settings())
            svc.test_notification("Test Camera")

        def _restore_defaults():
            import copy
            defaults = copy.deepcopy(settings_service.DEFAULTS)
            self._notif_motion_var.set(defaults["alert_motion"])
            self._notif_person_var.set(defaults["alert_person"])
            self._notif_vehicle_var.set(defaults["alert_vehicle"])
            self._notif_sound_var.set(defaults["alert_sound"])
            self._notif_debounce_var.set(str(defaults["debounce_seconds"]))
            self._notif_quiet_var.set(defaults["quiet_hours_enabled"])
            self._notif_quiet_start_var.set(defaults["quiet_hours_start"])
            self._notif_quiet_end_var.set(defaults["quiet_hours_end"])
            messagebox.showinfo("Restored", "Alert settings reset to defaults.\nClick Save to apply.")

        test_btn = tk.Button(
            btn_row,
            text="🔔  Test Notification",
            font=("Segoe UI", 11),
            bg=self.accent,
            fg=self.bg_dark,
            activebackground=self.accent_hover,
            activeforeground=self.bg_dark,
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=8,
            command=_test_notification,
        )
        test_btn.pack(side=tk.LEFT, padx=(0, 12))

        restore_btn = tk.Button(
            btn_row,
            text="↺  Restore Defaults",
            font=("Segoe UI", 11),
            bg=self.bg_input,
            fg=self.text_primary,
            activebackground="#3a3a3a",
            activeforeground=self.text_primary,
            relief=tk.FLAT,
            cursor="hand2",
            padx=16,
            pady=8,
            command=_restore_defaults,
        )
        restore_btn.pack(side=tk.LEFT)

    def create_rtsp_section(self, parent):
        """Create RTSP configuration section"""
        # RTSP section card
        rtsp_card = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT)
        rtsp_card.pack(fill=tk.X, pady=(0, 30))
        
        # Section title
        rtsp_title = tk.Label(
            rtsp_card,
            text="RTSP Configuration",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_card,
            fg=self.text_primary
        )
        rtsp_title.pack(pady=(30, 20), padx=40, anchor="w")
        
        # Get devices from main app - only use devices that are currently loaded
        devices = self.main_app.devices_data
        
        if not devices:
            no_devices_label = tk.Label(
                rtsp_card,
                text="No devices found. Please configure API credentials and reload.",
                font=("Segoe UI", 11),
                bg=self.bg_card,
                fg=self.text_secondary
            )
            no_devices_label.pack(pady=20, padx=40)
            return
        
        # Filter devices to only include those with valid device_id
        valid_devices = []
        for device in devices:
            device_id = device.get('device_id')
            if device_id and isinstance(device, dict):
                valid_devices.append(device)
        
        if not valid_devices:
            no_devices_label = tk.Label(
                rtsp_card,
                text="No valid devices found.",
                font=("Segoe UI", 11),
                bg=self.bg_card,
                fg=self.text_secondary
            )
            no_devices_label.pack(pady=20, padx=40)
            return
        
        # Container for device RTSP configs
        devices_container = tk.Frame(rtsp_card, bg=self.bg_card)
        devices_container.pack(fill=tk.X, padx=40, pady=(0, 30))
        
        # Create RTSP config for each valid device only
        for device in valid_devices:
            self.create_device_rtsp_config(devices_container, device)
    
    def create_device_rtsp_config(self, parent, device):
        """Create RTSP configuration UI for a single device"""
        device_id = device.get('device_id')
        device_name = device.get('name', 'Unknown Camera')
        device_model = device.get('device_name', 'Unknown Device')
        private_ip = device.get('private_ip', 'N/A')
        public_ip = device.get('public_ip', 'N/A')
        
        # Device card
        device_card = tk.Frame(parent, bg="#252525", relief=tk.FLAT)
        device_card.pack(fill=tk.X, pady=(0, 20))
        
        # Device header
        device_header = tk.Frame(device_card, bg="#252525")
        device_header.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        device_name_label = tk.Label(
            device_header,
            text=f"{device_name} ({device_model})",
            font=("Segoe UI", 12, "bold"),
            bg="#252525",
            fg=self.text_primary,
            anchor="w"
        )
        device_name_label.pack(side=tk.LEFT)
        
        # IP info
        ip_info = tk.Label(
            device_header,
            text=f"Private: {private_ip} | Public: {public_ip}",
            font=("Segoe UI", 9),
            bg="#252525",
            fg=self.text_secondary,
            anchor="e"
        )
        ip_info.pack(side=tk.RIGHT)
        
        # Input container
        input_container = tk.Frame(device_card, bg="#252525")
        input_container.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # Load existing RTSP config
        rtsp_config = get_rtsp_config(device_id)
        
        # Username field
        username_label = tk.Label(
            input_container,
            text="Username",
            font=("Segoe UI", 10, "bold"),
            bg="#252525",
            fg=self.text_primary,
            anchor="w"
        )
        username_label.pack(fill=tk.X, pady=(0, 5))
        
        username_entry = tk.Entry(
            input_container,
            font=("Segoe UI", 10),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            highlightcolor=self.accent
        )
        username_entry.insert(0, rtsp_config.get("username", ""))
        username_entry.pack(fill=tk.X, pady=(0, 15), ipady=10, ipadx=12)
        
        # Password field
        password_label = tk.Label(
            input_container,
            text="Password",
            font=("Segoe UI", 10, "bold"),
            bg="#252525",
            fg=self.text_primary,
            anchor="w"
        )
        password_label.pack(fill=tk.X, pady=(0, 5))
        
        password_entry = tk.Entry(
            input_container,
            font=("Segoe UI", 10),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            highlightcolor=self.accent,
            show="*"
        )
        password_entry.insert(0, rtsp_config.get("password", ""))
        password_entry.pack(fill=tk.X, pady=(0, 15), ipady=10, ipadx=12)
        
        # IP Type selection
        ip_type_label = tk.Label(
            input_container,
            text="IP Address Type",
            font=("Segoe UI", 10, "bold"),
            bg="#252525",
            fg=self.text_primary,
            anchor="w"
        )
        ip_type_label.pack(fill=tk.X, pady=(0, 5))
        
        ip_type_var = tk.StringVar(value=rtsp_config.get("ip_type", "private"))
        ip_type_combo = ttk.Combobox(
            input_container,
            textvariable=ip_type_var,
            values=["private", "public", "custom"],
            state="readonly",
            font=("Segoe UI", 10),
            width=20
        )
        ip_type_combo.pack(fill=tk.X, pady=(0, 15), ipady=8)
        
        # Style the combobox for dark theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox",
                        fieldbackground=self.bg_input,
                        background=self.bg_input,
                        foreground=self.text_primary,
                        borderwidth=1,
                        relief=tk.FLAT,
                        arrowcolor=self.text_primary)
        style.map("TCombobox",
                 fieldbackground=[("readonly", self.bg_input)],
                 selectbackground=[("readonly", "#3a3a3a")],
                 selectforeground=[("readonly", self.text_primary)],
                 background=[("readonly", self.bg_input)])
        
        # Custom IP field (only shown when custom is selected)
        custom_ip_label = tk.Label(
            input_container,
            text="Custom IP Address",
            font=("Segoe UI", 10, "bold"),
            bg="#252525",
            fg=self.text_primary,
            anchor="w"
        )
        
        custom_ip_entry = tk.Entry(
            input_container,
            font=("Segoe UI", 10),
            bg=self.bg_input,
            fg=self.text_primary,
            insertbackground=self.text_primary,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            highlightcolor=self.accent
        )
        custom_ip_entry.insert(0, rtsp_config.get("custom_ip", ""))
        
        def toggle_custom_ip(*args):
            if ip_type_var.get() == "custom":
                custom_ip_label.pack(fill=tk.X, pady=(0, 5), after=ip_type_combo)
                custom_ip_entry.pack(fill=tk.X, pady=(0, 15), ipady=10, ipadx=12, after=custom_ip_label)
            else:
                custom_ip_label.pack_forget()
                custom_ip_entry.pack_forget()
        
        ip_type_var.trace("w", toggle_custom_ip)
        toggle_custom_ip()  # Initial state
        
        # Store widgets for this device (only store widget references, not labels)
        self.rtsp_widgets[device_id] = {
            'username': username_entry,
            'password': password_entry,
            'ip_type': ip_type_var,
            'custom_ip': custom_ip_entry,
            'device': device,
            'device_id': device_id  # Store device_id separately
        }
        
        # Delete button container
        button_container = tk.Frame(device_card, bg="#252525")
        button_container.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        delete_btn = tk.Button(
            button_container,
            text="🗑 Delete RTSP Config",
            font=("Segoe UI", 10),
            bg=self.error,
            fg=self.text_primary,
            activebackground="#cc3333",
            activeforeground=self.text_primary,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda d=device_id: self.delete_rtsp_config(d),
            padx=15,
            pady=8,
            bd=0,
            highlightthickness=0
        )
        delete_btn.pack(side=tk.RIGHT)
        
        # Add hover effect
        def on_enter_delete(e):
            delete_btn.config(bg="#cc3333")
        def on_leave_delete(e):
            delete_btn.config(bg=self.error)
        delete_btn.bind("<Enter>", on_enter_delete)
        delete_btn.bind("<Leave>", on_leave_delete)
    
    def delete_rtsp_config(self, device_id):
        """Delete RTSP configuration for a device"""
        # Confirm deletion
        device_widgets = self.rtsp_widgets.get(device_id)
        if not device_widgets:
            return
        
        device = device_widgets.get('device')
        device_name = device.get('name', 'Unknown Camera') if device else 'Unknown Camera'
        
        result = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete the RTSP configuration for '{device_name}'?\n\nThis will clear all RTSP settings for this camera."
        )
        
        if not result:
            return
        
        # Delete from config file
        try:
            deleted = delete_rtsp_config(device_id)
            if deleted:
                # Clear the input fields in the UI
                username_entry = device_widgets.get('username')
                password_entry = device_widgets.get('password')
                ip_type_var = device_widgets.get('ip_type')
                custom_ip_entry = device_widgets.get('custom_ip')
                
                if self.is_widget_valid(username_entry):
                    username_entry.delete(0, tk.END)
                if self.is_widget_valid(password_entry):
                    password_entry.delete(0, tk.END)
                if ip_type_var:
                    ip_type_var.set("private")
                if self.is_widget_valid(custom_ip_entry):
                    custom_ip_entry.delete(0, tk.END)
                
                messagebox.showinfo(
                    "Success",
                    f"RTSP configuration deleted for '{device_name}'."
                )
            else:
                messagebox.showwarning(
                    "Not Found",
                    f"No RTSP configuration found for '{device_name}'."
                )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete RTSP configuration: {str(e)}"
            )
    
    def is_widget_valid(self, widget):
        """Check if a widget is still valid and accessible"""
        try:
            if widget is None:
                return False
            # Try to access a property that all tkinter widgets have
            widget.winfo_exists()
            return True
        except (tk.TclError, AttributeError):
            return False
    
    def create_save_button(self, parent):
        """Create save button"""
        button_container = tk.Frame(parent, bg=self.bg_dark)
        button_container.pack(pady=30)
        
        save_btn = tk.Button(
            button_container,
            text="Save All Settings",
            font=("Segoe UI", 13, "bold"),
            bg=self.accent,
            fg=self.bg_dark,
            activebackground=self.accent_hover,
            activeforeground=self.bg_dark,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.save_all_settings,
            padx=40,
            pady=14,
            bd=0,
            highlightthickness=0
        )
        save_btn.pack()
        
        # Info label
        info_label = tk.Label(
            button_container,
            text="Note: API credentials saved to .env, RTSP config saved to rtsp_config.json",
            font=("Segoe UI", 10),
            bg=self.bg_dark,
            fg=self.text_secondary
        )
        info_label.pack(pady=(15, 0))
    
    def save_all_settings(self):
        """Save all settings (API and RTSP)"""
        # Save API credentials
        try:
            # Check if widgets still exist
            if not hasattr(self, 'auth_entry') or not hasattr(self, 'xterm_entry'):
                messagebox.showerror(
                    "Error",
                    "Settings page was closed. Please try again."
                )
                return
            
            # Check if widgets are valid
            if not self.is_widget_valid(self.auth_entry) or not self.is_widget_valid(self.xterm_entry):
                messagebox.showerror(
                    "Error",
                    "Settings page was closed. Please try again."
                )
                return
            
            # Try to access widgets
            try:
                authorization = str(self.auth_entry.get()).strip()
                x_term_id = str(self.xterm_entry.get()).strip()
            except (tk.TclError, AttributeError, RuntimeError) as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to read settings: {str(e)}\nPlease try again."
                )
                return
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Unexpected error: {str(e)}"
            )
            return
        
        if not authorization or not x_term_id:
            messagebox.showwarning(
                "Validation Error",
                "Please fill in both Authorization and X-Term-Id fields."
            )
            return
        
        try:
            # Save API credentials
            env_path = find_dotenv()
            if not env_path:
                env_path = os.path.join(os.getcwd(), ".env")
                with open(env_path, "w") as f:
                    f.write("")
            
            set_key(env_path, "Authorization", authorization)
            set_key(env_path, "X-Term-Id", x_term_id)
            load_dotenv(override=True)

            # Save notification settings
            try:
                notif_settings = settings_service.load_settings()
                notif_settings["alert_motion"] = bool(self._notif_motion_var.get())
                notif_settings["alert_person"] = bool(self._notif_person_var.get())
                notif_settings["alert_vehicle"] = bool(self._notif_vehicle_var.get())
                notif_settings["alert_sound"] = bool(self._notif_sound_var.get())
                try:
                    debounce = max(0, int(self._notif_debounce_var.get()))
                except (ValueError, AttributeError):
                    debounce = 30
                notif_settings["debounce_seconds"] = debounce
                notif_settings["quiet_hours_enabled"] = bool(self._notif_quiet_var.get())
                qh_start = str(self._notif_quiet_start_var.get()).strip()
                qh_end = str(self._notif_quiet_end_var.get()).strip()
                # Validate HH:MM format (24-hour) for quiet hours
                import re as _re
                _hhmm = _re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
                if not _hhmm.match(qh_start):
                    messagebox.showwarning(
                        "Invalid Time",
                        f"Quiet hours start time '{qh_start}' is not valid.\n"
                        "Please use HH:MM in 24-hour format (e.g. 22:00).\n"
                        "Reverting to previous value."
                    )
                    qh_start = notif_settings.get("quiet_hours_start", "22:00")
                if not _hhmm.match(qh_end):
                    messagebox.showwarning(
                        "Invalid Time",
                        f"Quiet hours end time '{qh_end}' is not valid.\n"
                        "Please use HH:MM in 24-hour format (e.g. 07:00).\n"
                        "Reverting to previous value."
                    )
                    qh_end = notif_settings.get("quiet_hours_end", "07:00")
                notif_settings["quiet_hours_start"] = qh_start
                notif_settings["quiet_hours_end"] = qh_end
                notif_settings["first_run"] = False
                settings_service.save_settings(notif_settings)
                # Push live update to EventAdapter + NotificationService if available
                if hasattr(self.main_app, 'notification_service') and self.main_app.notification_service:
                    self.main_app.notification_service.update_settings(notif_settings)
                if hasattr(self.main_app, 'event_adapter') and self.main_app.event_adapter:
                    self.main_app.event_adapter.update_settings(notif_settings)
            except Exception:
                pass  # notification settings save failure is non-fatal
            
            # Get list of valid device IDs from current devices_data
            valid_device_ids = []
            if hasattr(self.main_app, 'devices_data') and self.main_app.devices_data:
                for device in self.main_app.devices_data:
                    device_id = device.get('device_id')
                    if device_id:
                        valid_device_ids.append(device_id)
            
            # Clean up RTSP configs for devices that no longer exist
            cleanup_rtsp_config(valid_device_ids)
            
            # Save RTSP configurations only for valid devices
            rtsp_configs_saved = 0
            for device_id, widgets in list(self.rtsp_widgets.items()):
                # Only process devices that are in the current devices_data
                if device_id not in valid_device_ids:
                    continue
                
                try:
                    # Check if widgets exist and are valid
                    if not isinstance(widgets, dict):
                        continue
                    
                    if 'username' not in widgets or 'password' not in widgets:
                        continue
                    
                    # Get widget references
                    username_widget = widgets.get('username')
                    password_widget = widgets.get('password')
                    ip_type_var = widgets.get('ip_type')
                    custom_ip_widget = widgets.get('custom_ip')
                    
                    # Check if widgets are valid before accessing
                    if not self.is_widget_valid(username_widget):
                        continue
                    if not self.is_widget_valid(password_widget):
                        continue
                    if ip_type_var is None:
                        continue
                    
                    # Try to get widget values
                    try:
                        username = str(username_widget.get()).strip()
                        password = str(password_widget.get()).strip()
                        ip_type = str(ip_type_var.get())
                        custom_ip = ""
                        
                        if ip_type == "custom" and custom_ip_widget and self.is_widget_valid(custom_ip_widget):
                            try:
                                custom_ip = str(custom_ip_widget.get()).strip()
                            except (tk.TclError, AttributeError):
                                custom_ip = ""
                        
                        set_rtsp_config(device_id, username, password, ip_type, custom_ip)
                        rtsp_configs_saved += 1
                    except (tk.TclError, AttributeError, KeyError, RuntimeError) as e:
                        # Skip if widget was destroyed or invalid
                        continue
                except Exception as e:
                    # Skip this device if there's any error
                    continue
            
            messagebox.showinfo(
                "Success",
                f"Settings saved successfully!\nAPI credentials saved.\nRTSP configs saved: {rtsp_configs_saved}"
            )
            
            # Update main app
            try:
                self.main_app.check_env_config()
                self.main_app.load_devices()
            except:
                pass
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror(
                "Error",
                f"Failed to save settings:\n{str(e)}\n\nDetails:\n{error_details}"
            )
    
    def go_back(self):
        """Go back to main page"""
        self.hide()
        self.main_app.show_main_page()
    
    def show(self):
        """Show settings page"""
        # Recreate settings page to refresh device list
        if self.settings_frame:
            try:
                # Unbind mouse wheel if canvas exists
                if hasattr(self, 'settings_canvas'):
                    try:
                        self.settings_canvas.unbind_all("<MouseWheel>")
                        self.settings_canvas.unbind_all("<Button-4>")
                        self.settings_canvas.unbind_all("<Button-5>")
                    except:
                        pass
                self.settings_frame.destroy()
            except:
                pass
        self.rtsp_widgets = {}
        self.create_settings_page()
    
    def hide(self):
        """Hide settings page"""
        if self.settings_frame:
            self.settings_frame.pack_forget()
