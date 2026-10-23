"""Secure Login and Authentication View for Hospital Management System — Q08.
Supports salted PBKDF2 password authentication and quick role switcher pills for review demoing.
"""
from typing import Callable, Optional
import customtkinter as ctk

from config.constants import (
    APP_NAME,
    STUDENT_BRANCH,
    STUDENT_NAME,
    STUDENT_SECTION,
)
from services.auth_service import login


class LoginView(ctk.CTkFrame):
    """Modern clinical authentication view with quick demo credentials switcher."""

    def __init__(self, master, on_login_success: Callable[[dict], None], **kwargs):
        super().__init__(master, fg_color=("#F8FAFC", "#0A0F1D"), **kwargs)
        self.on_login_success = on_login_success

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct centered login card and demo switcher buttons."""
        # Outer centered container
        center_frame = ctk.CTkFrame(
            self,
            width=460,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=12,
        )
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        pad = ctk.CTkFrame(center_frame, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=32, pady=28)

        # 1. Hospital Brand Header
        logo_lbl = ctk.CTkLabel(
            pad,
            text="🏥 Hospital Management System",
            font=ctk.CTkFont(size=20, weight="bold"),
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
        meta_lbl.pack(pady=(0, 16))

        # Separator line
        ctk.CTkFrame(pad, height=1, fg_color=("#E2E8F0", "#1E2D4A")).pack(fill="x", pady=(0, 16))

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
            height=36,
            corner_radius=6,
        )
        self.username_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            pad,
            text="Password",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

        self.password_entry = ctk.CTkEntry(
            pad,
            placeholder_text="Enter password",
            show="•",
            height=36,
            corner_radius=6,
        )
        self.password_entry.pack(fill="x", pady=(0, 10))

        # Enter key triggers login
        self.username_entry.bind("<Return>", lambda e: self._attempt_login())
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        # Error Banner
        self.error_lbl = ctk.CTkLabel(
            pad,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#EF4444",
            wraplength=380,
            anchor="w",
        )
        self.error_lbl.pack(fill="x", pady=(0, 8))

        # Sign In Button
        self.login_btn = ctk.CTkButton(
            pad,
            text="🔐  Sign In",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=40,
            corner_radius=6,
            command=self._attempt_login,
        )
        self.login_btn.pack(fill="x", pady=(0, 16))

        # 3. Quick Role Switcher (For seamless Review Demo)
        demo_box = ctk.CTkFrame(
            pad,
            fg_color=("#F8FAFC", "#0C152B"),
            border_width=1,
            border_color=("#E2E8F0", "#1E2D4A"),
            corner_radius=8,
        )
        demo_box.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(
            demo_box,
            text="⚡ Quick Role Switcher (Demo Review):",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(6, 4))

        roles_row = ctk.CTkFrame(demo_box, fg_color="transparent")
        roles_row.pack(fill="x", padx=6, pady=(0, 6))
        roles_row.grid_columnconfigure((0, 1), weight=1)

        demo_accounts = [
            ("👑 Administrator", "admin", "Admin@123", 0, 0),
            ("👩‍💼 Reception Staff", "staff_reception", "Staff@123", 0, 1),
            ("👨‍⚕️ Physician", "dr_arun", "Doctor@123", 1, 0),
            ("👤 Patient", "patient_aarav", "Patient@123", 1, 1),
        ]

        for label, u, p, r, c in demo_accounts:
            btn = ctk.CTkButton(
                roles_row,
                text=label,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=("#FFFFFF", "#17254A"),
                text_color=("#0F172A", "#F8FAFC"),
                hover_color=("#E2E8F0", "#223862"),
                border_width=1,
                border_color=("#CBD5E1", "#243666"),
                height=28,
                command=lambda un=u, pw=p: self._fill_and_login(un, pw),
            )
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="ew")

        # Focus username by default
        self.after(100, lambda: self.username_entry.focus_force())

    def _fill_and_login(self, username: str, password: str) -> None:
        """Auto-fill credentials and immediately sign in."""
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
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
            self.error_lbl.configure(text=msg)
            self.login_btn.configure(state="normal", text="🔐  Sign In")
