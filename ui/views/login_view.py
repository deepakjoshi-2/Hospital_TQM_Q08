"""Secure Premium Clinical Login and Authentication View for Hospital Management System — Q08.
Recreated inspired by CityCare Hospital modern healthcare interface:
- Full-screen hospital environment background (reception on left, corridor on right, glowing ECG & badges)
  using the exact same hospital background asset in both Dark and Light themes.
- Centered floating glassmorphic login card with glowing cyan border (Dark) / clean white with subtle blue border (Light)
- Brand header with hospital building silhouette and ECG pulse accents
- Form inputs with icons, cyan border highlights, and show/hide password toggle
- Gradient primary Sign In button
- Translucent Demo Role Quick-Fill panel with 2x2 role selector grid
- Supports dynamic responsive scaling and instant theme switching without background flicker
- 100% preserves existing salted PBKDF2 authentication, credentials, and test APIs
"""
import os
from typing import Callable, Dict, Optional
import customtkinter as ctk
from PIL import Image

from config.constants import APP_NAME
from services.auth_service import get_user_by_username, login


class LoginView(ctk.CTkFrame):
    """Modern clinical authentication view enforcing credential entry and verification."""

    DEMO_ACCOUNTS = {
        "admin": {
            "key": "admin",
            "label": "🛡️  Administrator",
            "username": "admin",
            "password": "Admin@123",
            "role": "Hospital Administrator",
        },
        "staff": {
            "key": "staff",
            "label": "👤  Reception Staff",
            "username": "staff_reception",
            "password": "Staff@123",
            "role": "Staff",
        },
        "doctor": {
            "key": "doctor",
            "label": "🩺  Doctor",
            "username": "dr_arun",
            "password": "Doctor@123",
            "role": "Doctor",
        },
        "patient": {
            "key": "patient",
            "label": "👤  Patient",
            "username": "patient_aarav",
            "password": "Patient@123",
            "role": "Patient",
        },
    }

    def __init__(self, master, on_login_success: Callable[[dict], None], **kwargs):
        # Base frame preserves the deep dark environment underlying the background
        super().__init__(master, fg_color=("#070D1E", "#070D1E"), **kwargs)
        self.on_login_success = on_login_success
        self._password_visible = False
        self._selected_role: Optional[str] = None
        self.role_buttons: Dict[str, ctk.CTkButton] = {}
        self._bg_img: Optional[ctk.CTkImage] = None
        self._last_w = 0
        self._last_h = 0

        self._build_ui()
        self.bind("<Configure>", self._on_resize)

    def _build_ui(self) -> None:
        """Construct full-screen hospital background, glassmorphism login card, and inputs."""
        # 1. Full-screen Hospital Background Image (identical asset across Dark & Light themes)
        self._init_background()

        # 2. Centered Glassmorphic Login Card
        # Proportioned to comfortably fit 1280x720 at 150% scaling without vertical clipping
        # Dark: Deep midnight navy glassmorphic card with cyan glowing border
        # Light: Clean white / light icy-blue card with subtle blue border
        self.center_frame = ctk.CTkFrame(
            self,
            width=460,
            fg_color=("#FFFFFF", "#0A1832"),
            border_width=2,
            border_color=("#38BDF8", "#00D2FF"),
            corner_radius=16,
        )
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")

        pad = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=26, pady=16)

        # 3. Hospital Brand Header inside Card
        self._init_brand_header(pad)

        # 4. Form Inputs
        # Username section
        ctk.CTkLabel(
            pad,
            text="✉ Username or Email",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0F172A", "#FFFFFF"),
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        self.username_entry = ctk.CTkEntry(
            pad,
            placeholder_text="👤  Enter username or email",
            height=34,
            corner_radius=8,
            fg_color=("#F0F7FF", "#061329"),
            border_color=("#0284C7", "#00D2FF"),
            border_width=1.5,
            text_color=("#0F172A", "#FFFFFF"),
            placeholder_text_color=("#64748B", "#64748B"),
        )
        self.username_entry.pack(fill="x", pady=(0, 8))

        # Password section
        ctk.CTkLabel(
            pad,
            text="🔒 Password",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0F172A", "#FFFFFF"),
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        pwd_row = ctk.CTkFrame(pad, fg_color="transparent")
        pwd_row.pack(fill="x", pady=(0, 6))

        self.password_entry = ctk.CTkEntry(
            pwd_row,
            placeholder_text="🔒  Enter password",
            show="•",
            height=34,
            corner_radius=8,
            fg_color=("#F0F7FF", "#061329"),
            border_color=("#0284C7", "#00D2FF"),
            border_width=1.5,
            text_color=("#0F172A", "#FFFFFF"),
            placeholder_text_color=("#64748B", "#64748B"),
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_pwd_btn = ctk.CTkButton(
            pwd_row,
            text="👁 Show",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=76,
            height=34,
            corner_radius=8,
            fg_color=("#E0F2FE", "#0B1D3A"),
            text_color=("#0284C7", "#00D2FF"),
            hover_color=("#BAE6FD", "#162E56"),
            border_width=1.5,
            border_color=("#0284C7", "#00D2FF"),
            command=self._toggle_password_visibility,
        )
        self.toggle_pwd_btn.pack(side="right")

        # Track manual edits to dynamically update role button selection highlights
        self.username_entry.bind("<KeyRelease>", self._on_entry_changed)
        self.password_entry.bind("<KeyRelease>", self._on_entry_changed)

        # Enter key triggers login
        self.username_entry.bind("<Return>", lambda e: self._attempt_login())
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        # Error Banner (inline notification without crash)
        self.error_lbl = ctk.CTkLabel(
            pad,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#EF4444",
            wraplength=400,
            anchor="w",
        )
        self.error_lbl.pack(fill="x", pady=(0, 4))

        # Sign In Button (Gradient cyan-blue appearance, matching CityCare reference)
        self.login_btn = ctk.CTkButton(
            pad,
            text="➔] Sign In",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0284C7", "#00A8E8"),
            hover_color=("#0369A1", "#0096C7"),
            text_color="#FFFFFF",
            height=36,
            corner_radius=8,
            command=self._attempt_login,
        )
        self.login_btn.pack(fill="x", pady=(0, 8))

        # 5. Four Role Quick-Fill Buttons Container (Translucent panel with accent border)
        quickfill_box = ctk.CTkFrame(
            pad,
            fg_color=("#F0F7FF", "#071328"),
            border_width=1.5,
            border_color=("#0284C7", "#00D2FF"),
            corner_radius=10,
        )
        quickfill_box.pack(fill="x", pady=(2, 0))

        header_row = ctk.CTkFrame(quickfill_box, fg_color="transparent")
        header_row.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            header_row,
            text="⚡ Demo Role Quick-Fill (Click to populate credentials):",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="w",
        ).pack(side="left")

        # 2x2 Grid of Role Quick-Fill Buttons
        grid_frame = ctk.CTkFrame(quickfill_box, fg_color="transparent")
        grid_frame.pack(fill="x", padx=8, pady=(0, 8))
        grid_frame.grid_columnconfigure(0, weight=1, uniform="demo_roles")
        grid_frame.grid_columnconfigure(1, weight=1, uniform="demo_roles")

        role_grid_positions = [
            ("admin", 0, 0),
            ("staff", 0, 1),
            ("doctor", 1, 0),
            ("patient", 1, 1),
        ]

        for role_key, row, col in role_grid_positions:
            role_info = self.DEMO_ACCOUNTS[role_key]
            btn = ctk.CTkButton(
                grid_frame,
                text=role_info["label"],
                font=ctk.CTkFont(size=11, weight="bold"),
                height=32,
                corner_radius=6,
                fg_color=("#FFFFFF", "#0B1E3F"),
                text_color=("#0F172A", "#F1F5F9"),
                hover_color=("#F1F5F9", "#163060"),
                border_width=1,
                border_color=("#CBD5E1", "#1E3E75"),
                command=lambda k=role_key: self._on_role_btn_clicked(k),
            )
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            self.role_buttons[role_key] = btn

        # Convenience references for testing & direct access
        self.role_btn_admin = self.role_buttons["admin"]
        self.role_btn_staff = self.role_buttons["staff"]
        self.role_btn_doctor = self.role_buttons["doctor"]
        self.role_btn_patient = self.role_buttons["patient"]

        # Focus username entry on launch
        self.after(100, lambda: self.username_entry.focus_force())

    def _init_background(self) -> None:
        """Initialize the full-screen hospital environment background.
        
        CRITICAL: Uses the exact same hospital background image asset in both
        Dark Mode and Light Mode. Zero recoloring, zero tinting, zero theme-dependent
        filtering.
        """
        bg_path = "ui/assets/login_bg.png"
        if not os.path.exists(bg_path):
            bg_path = "ui/assets/login_bg_dark.png"

        if os.path.exists(bg_path):
            try:
                with Image.open(bg_path) as im:
                    self._pil_bg = im.copy()
                # Pass the exact same image to both light_image and dark_image
                self._bg_img = ctk.CTkImage(
                    light_image=self._pil_bg,
                    dark_image=self._pil_bg,
                    size=(1280, 720),
                )
                self.bg_label = ctk.CTkLabel(self, image=self._bg_img, text="")
                self.bg_label.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            except Exception:
                self.bg_label = None
        else:
            self.bg_label = None

    def _init_brand_header(self, parent: ctk.CTkFrame) -> None:
        """Construct the hospital brand icon, title, and ECG heartbeat lines."""
        # Hospital brand silhouette icon
        icon_dark = "ui/assets/hospital_brand_dark.png"
        icon_light = "ui/assets/hospital_brand_light.png"
        if os.path.exists(icon_dark) and os.path.exists(icon_light):
            try:
                with Image.open(icon_dark) as im_d:
                    pil_d = im_d.copy()
                with Image.open(icon_light) as im_l:
                    pil_l = im_l.copy()
                self.brand_icon_img = ctk.CTkImage(light_image=pil_l, dark_image=pil_d, size=(68, 36))
                icon_lbl = ctk.CTkLabel(parent, image=self.brand_icon_img, text="")
                icon_lbl.pack(pady=(0, 2))
            except Exception:
                pass

        # Title: Hospital Management System (Dark navy in Light mode, White in Dark mode)
        title_lbl = ctk.CTkLabel(
            parent,
            text="Hospital Management System",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#0F172A", "#FFFFFF"),
        )
        title_lbl.pack(pady=(0, 2))

        # Subtitle with ECG accent dashes: ─── Q08 – Improve User Satisfaction System ───
        sub_lbl = ctk.CTkLabel(
            parent,
            text="─── Q08 – Improve User Satisfaction System ───",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0284C7", "#00D2FF"),
        )
        sub_lbl.pack(pady=(0, 8))

        # Separator line
        ctk.CTkFrame(parent, height=1, fg_color=("#E2E8F0", "#16345E")).pack(fill="x", pady=(0, 8))

    def _on_resize(self, event) -> None:
        """Dynamically update background image size to cover window without flicker."""
        if event.widget == self and self.bg_label and hasattr(self, "_pil_bg") and self._bg_img:
            w = max(400, event.width)
            h = max(300, event.height)
            if abs(w - self._last_w) > 40 or abs(h - self._last_h) > 40:
                self._last_w = w
                self._last_h = h
                try:
                    self._bg_img.configure(size=(w, h))
                except Exception:
                    pass

    def _on_role_btn_clicked(self, role_key: str) -> None:
        """Populate form fields with selected role's demo credentials without auto-submitting.
        
        Validates account existence in SQLite before populating to ensure demo integrity.
        """
        role_data = self.DEMO_ACCOUNTS.get(role_key)
        if not role_data:
            return

        username = role_data["username"]
        password = role_data["password"]

        # Security requirement: check if demo account exists in the database
        user_record = get_user_by_username(username)
        if not user_record:
            self.error_lbl.configure(
                text=f"Demo account '{username}' ({role_data['role']}) not found in database. Please run seed."
            )
            self._update_role_highlight(None)
            return

        # Clear error label
        self.error_lbl.configure(text="")

        # Populate username and password fields
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)

        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)

        # Preserve password masking if not explicitly toggled
        if not self._password_visible:
            self.password_entry.configure(show="•")

        # Visually highlight the selected role button
        self._update_role_highlight(role_key)

    def _on_entry_changed(self, event=None) -> None:
        """Dynamically evaluate whether form inputs match any demo role to update highlights."""
        curr_u = self.username_entry.get().strip()
        curr_p = self.password_entry.get()

        matched_key = None
        for r_key, r_info in self.DEMO_ACCOUNTS.items():
            if curr_u == r_info["username"] and curr_p == r_info["password"]:
                matched_key = r_key
                break

        self._update_role_highlight(matched_key)

    def _update_role_highlight(self, selected_key: Optional[str]) -> None:
        """Update visual button styling to clearly indicate the selected demo role."""
        self._selected_role = selected_key
        for r_key, btn in self.role_buttons.items():
            if r_key == selected_key:
                btn.configure(
                    fg_color=("#E0F2FE", "#0284C7"),
                    text_color=("#0284C7", "#FFFFFF"),
                    hover_color=("#BAE6FD", "#0369A1"),
                    border_width=2,
                    border_color=("#0284C7", "#00D2FF"),
                )
            else:
                btn.configure(
                    fg_color=("#FFFFFF", "#0B1E3F"),
                    text_color=("#0F172A", "#F1F5F9"),
                    hover_color=("#F1F5F9", "#163060"),
                    border_width=1,
                    border_color=("#CBD5E1", "#1E3E75"),
                )

    def get_selected_role(self) -> Optional[str]:
        """Return the currently highlighted role key ('admin', 'staff', 'doctor', 'patient', or None)."""
        return self._selected_role

    def select_role(self, role_key: str) -> None:
        """Public helper to trigger role quick-fill (for UI automation & testing)."""
        self._on_role_btn_clicked(role_key)

    def _toggle_password_visibility(self) -> None:
        """Toggle password field masking between masked and plaintext."""
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.password_entry.configure(show="")
            self.toggle_pwd_btn.configure(text="🔒 Hide")
        else:
            self.password_entry.configure(show="•")
            self.toggle_pwd_btn.configure(text="👁 Show")

    def _fill_and_login(self, username: str, password: str) -> None:
        """Helper method to populate credentials and submit login for testing backward compatibility."""
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
        self._on_entry_changed()
        self._attempt_login()

    def _attempt_login(self) -> None:
        """Validate credentials against PBKDF2 database records."""
        self.error_lbl.configure(text="")
        u = self.username_entry.get().strip()
        p = self.password_entry.get()

        if not u or not p:
            self.error_lbl.configure(text="Please enter both username and password.")
            return

        self.login_btn.configure(state="disabled", text="Authenticating...")
        self.update_idletasks()

        ok, user, msg = login(u, p)
        if ok and user:
            self.login_btn.configure(state="normal", text="➔] Sign In")
            self.on_login_success(user)
        else:
            self.error_lbl.configure(text=msg or "Invalid username or password. Please try again.")
            self.login_btn.configure(state="normal", text="➔] Sign In")
