"""Secure Login and Authentication View for Hospital Management System — Q08.
Supports salted PBKDF2 password authentication, credential verification,
show/hide password toggle, and academic demo role quick-fill buttons.
"""
from typing import Callable, Dict, Optional
import customtkinter as ctk

from config.constants import (
    APP_NAME,
    STUDENT_BRANCH,
    STUDENT_NAME,
    STUDENT_SECTION,
)
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
            "label": "🏥  Reception Staff",
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
        super().__init__(master, fg_color=("#F8FAFC", "#0A0F1D"), **kwargs)
        self.on_login_success = on_login_success
        self._password_visible = False
        self._selected_role: Optional[str] = None
        self.role_buttons: Dict[str, ctk.CTkButton] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct centered login card, credentials input, and role quick-fill buttons."""
        # Outer centered container (responsive, fits 1280x720 at 150% DPI without clipping)
        center_frame = ctk.CTkFrame(
            self,
            width=480,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=12,
        )
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        pad = ctk.CTkFrame(center_frame, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        # 1. Hospital Brand Header
        logo_lbl = ctk.CTkLabel(
            pad,
            text="🏥 Hospital Management System",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
        )
        logo_lbl.pack(pady=(0, 2))

        sub_lbl = ctk.CTkLabel(
            pad,
            text="Q08 — Improve User Satisfaction System",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        sub_lbl.pack(pady=(0, 2))

        meta_lbl = ctk.CTkLabel(
            pad,
            text=f"{STUDENT_NAME} • Roll: 2410302011 • {STUDENT_SECTION} ({STUDENT_BRANCH})",
            font=ctk.CTkFont(size=10),
            text_color=("#64748B", "#94A3B8"),
        )
        meta_lbl.pack(pady=(0, 10))

        # Separator line
        ctk.CTkFrame(pad, height=1, fg_color=("#E2E8F0", "#1E2D4A")).pack(fill="x", pady=(0, 10))

        # 2. Form Inputs
        ctk.CTkLabel(
            pad,
            text="Username or Email",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        self.username_entry = ctk.CTkEntry(
            pad,
            placeholder_text="Enter username (e.g. admin)",
            height=34,
            corner_radius=6,
        )
        self.username_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            pad,
            text="Password",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        pwd_row = ctk.CTkFrame(pad, fg_color="transparent")
        pwd_row.pack(fill="x", pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            pwd_row,
            placeholder_text="Enter password",
            show="•",
            height=34,
            corner_radius=6,
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_pwd_btn = ctk.CTkButton(
            pwd_row,
            text="👁 Show",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            height=34,
            corner_radius=6,
            fg_color=("#E2E8F0", "#1E293B"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#334155"),
            border_width=1,
            border_color=("#CBD5E1", "#334155"),
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
            font=ctk.CTkFont(size=11),
            text_color="#EF4444",
            wraplength=420,
            anchor="w",
        )
        self.error_lbl.pack(fill="x", pady=(0, 6))

        # Sign In Button (Required for actual authentication — role buttons do not auto-login)
        self.login_btn = ctk.CTkButton(
            pad,
            text="🔐  Sign In",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=38,
            corner_radius=6,
            command=self._attempt_login,
        )
        self.login_btn.pack(fill="x", pady=(0, 10))

        # 3. Four Role Quick-Fill Buttons (Replacing static credentials table)
        quickfill_box = ctk.CTkFrame(
            pad,
            fg_color=("#F8FAFC", "#0C152B"),
            border_width=1,
            border_color=("#E2E8F0", "#1E2D4A"),
            corner_radius=8,
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
                height=34,
                corner_radius=6,
                fg_color=("#F1F5F9", "#1E293B"),
                text_color=("#1E293B", "#F1F5F9"),
                hover_color=("#E2E8F0", "#334155"),
                border_width=1,
                border_color=("#CBD5E1", "#334155"),
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
                    fg_color=("#E0F2FE", "#0369A1"),
                    text_color=("#0284C7", "#F0F9FF"),
                    hover_color=("#BAE6FD", "#0284C7"),
                    border_width=2,
                    border_color=("#0284C7", "#38BDF8"),
                )
            else:
                btn.configure(
                    fg_color=("#F1F5F9", "#1E293B"),
                    text_color=("#1E293B", "#F1F5F9"),
                    hover_color=("#E2E8F0", "#334155"),
                    border_width=1,
                    border_color=("#CBD5E1", "#334155"),
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
            self.login_btn.configure(state="normal", text="🔐  Sign In")
            self.on_login_success(user)
        else:
            self.error_lbl.configure(text=msg or "Invalid username or password. Please try again.")
            self.login_btn.configure(state="normal", text="🔐  Sign In")
