"""Secure Login and Authentication View for Hospital Management System — Q08.
Supports salted PBKDF2 password authentication, credential verification,
show/hide password toggle, and academic demo credentials guide.
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
    """Modern clinical authentication view enforcing credential entry and verification."""

    def __init__(self, master, on_login_success: Callable[[dict], None], **kwargs):
        super().__init__(master, fg_color=("#F8FAFC", "#0A0F1D"), **kwargs)
        self.on_login_success = on_login_success
        self._password_visible = False

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct centered login card, credentials input, and evaluator reference guide."""
        # Outer centered container
        center_frame = ctk.CTkFrame(
            self,
            width=500,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=12,
        )
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        pad = ctk.CTkFrame(center_frame, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=32, pady=26)

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
        meta_lbl.pack(pady=(0, 14))

        # Separator line
        ctk.CTkFrame(pad, height=1, fg_color=("#E2E8F0", "#1E2D4A")).pack(fill="x", pady=(0, 14))

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

        pwd_row = ctk.CTkFrame(pad, fg_color="transparent")
        pwd_row.pack(fill="x", pady=(0, 10))

        self.password_entry = ctk.CTkEntry(
            pwd_row,
            placeholder_text="Enter password",
            show="•",
            height=36,
            corner_radius=6,
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_pwd_btn = ctk.CTkButton(
            pwd_row,
            text="👁 Show",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            height=36,
            corner_radius=6,
            fg_color=("#E2E8F0", "#1E293B"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#334155"),
            border_width=1,
            border_color=("#CBD5E1", "#334155"),
            command=self._toggle_password_visibility,
        )
        self.toggle_pwd_btn.pack(side="right")

        # Enter key triggers login
        self.username_entry.bind("<Return>", lambda e: self._attempt_login())
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        # Error Banner
        self.error_lbl = ctk.CTkLabel(
            pad,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#EF4444",
            wraplength=420,
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
        self.login_btn.pack(fill="x", pady=(0, 14))

        # 3. Informational Evaluator Reference Guide (Static credentials info — no bypass shortcuts)
        guide_box = ctk.CTkFrame(
            pad,
            fg_color=("#F8FAFC", "#0C152B"),
            border_width=1,
            border_color=("#E2E8F0", "#1E2D4A"),
            corner_radius=8,
        )
        guide_box.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(
            guide_box,
            text="ℹ️  Academic Review Credentials Guide (BBAT104):",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(6, 4))

        accounts_table = [
            ("👑 Administrator:", "admin", "Admin@123"),
            ("👩‍💼 Reception Staff:", "staff_reception", "Staff@123"),
            ("👨‍⚕️ Physician:", "dr_arun", "Doctor@123"),
            ("👤 Patient:", "patient_aarav", "Patient@123"),
        ]

        table_frame = ctk.CTkFrame(guide_box, fg_color="transparent")
        table_frame.pack(fill="x", padx=10, pady=(0, 6))
        table_frame.grid_columnconfigure(0, weight=2)
        table_frame.grid_columnconfigure(1, weight=2)
        table_frame.grid_columnconfigure(2, weight=2)

        for r_idx, (role_lbl, un, pw) in enumerate(accounts_table):
            ctk.CTkLabel(
                table_frame,
                text=role_lbl,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                anchor="w",
            ).grid(row=r_idx, column=0, sticky="w", pady=1)

            ctk.CTkLabel(
                table_frame,
                text=f"User: {un}",
                font=ctk.CTkFont(size=10),
                text_color=("#0F172A", "#F8FAFC"),
                anchor="w",
            ).grid(row=r_idx, column=1, sticky="w", pady=1, padx=4)

            ctk.CTkLabel(
                table_frame,
                text=f"Pass: {pw}",
                font=ctk.CTkFont(size=10),
                text_color=("#64748B", "#94A3B8"),
                anchor="w",
            ).grid(row=r_idx, column=2, sticky="w", pady=1)

        # Focus username entry on launch
        self.after(100, lambda: self.username_entry.focus_force())

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
        """Helper method to populate credentials and submit login for testing."""
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
            self.error_lbl.configure(text=msg or "Invalid username or password. Please try again.")
            self.login_btn.configure(state="normal", text="🔐  Sign In")
