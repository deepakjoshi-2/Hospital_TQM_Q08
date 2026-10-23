"""User Accounts Management View for Hospital Administrator.
Enables creating new staff/doctor/patient accounts, toggling account active status,
and resetting passwords with PBKDF2 hashing.
"""
from typing import Dict, List, Optional
import customtkinter as ctk

from config.constants import ROLE_ADMIN, USER_ROLES
from services.auth_service import (
    create_user,
    get_all_users,
    get_current_user,
    reset_user_password,
    toggle_user_status,
)


class UserManagementView(ctk.CTkFrame):
    """Administrator View for managing system user accounts and roles."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = get_current_user()

        self._build_header()
        self._build_table_container()
        self.load_users()

    def _build_header(self) -> None:
        """Header with title, description, and user creation button."""
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 12))

        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="👥 System User Accounts & Roles",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            title_box,
            text="Role-based access control management. Configure Administrator, Staff, Doctor, and Patient logins.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        ).pack(fill="x")

        # Right actions
        r_box = ctk.CTkFrame(hdr, fg_color="transparent")
        r_box.pack(side="right")

        new_user_btn = ctk.CTkButton(
            r_box,
            text="➕ New User Account",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=34,
            command=self._open_new_user_modal,
        )
        new_user_btn.pack(side="right", padx=(8, 0))

        refresh_btn = ctk.CTkButton(
            r_box,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#E2E8F0", "#2B3E63"),
            border_width=1,
            border_color=("#CBD5E1", "#33456B"),
            height=34,
            command=self.load_users,
        )
        refresh_btn.pack(side="right")

    def _build_table_container(self) -> None:
        """Scrollable table frame holding user account records."""
        table_shell = ctk.CTkFrame(
            self,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        table_shell.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # Table Column Headers
        hdr_row = ctk.CTkFrame(table_shell, height=36, fg_color=("#F1F5F9", "#16233E"), corner_radius=0)
        hdr_row.pack(fill="x")
        hdr_row.pack_propagate(False)

        headers = [
            ("ID", 45),
            ("Username", 130),
            ("Full Name", 160),
            ("Role", 140),
            ("Email", 170),
            ("Linked Entity", 130),
            ("Status", 90),
            ("Actions", 150),
        ]

        for title, w in headers:
            ctk.CTkLabel(
                hdr_row,
                text=title,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                width=w,
                anchor="w" if title != "Actions" else "center",
                padx=8,
            ).pack(side="left")

        # Scrollable rows area
        self.rows_scroll = ctk.CTkScrollableFrame(table_shell, fg_color="transparent")
        self.rows_scroll.pack(fill="both", expand=True)

    def load_users(self) -> None:
        """Load and display all registered users."""
        for child in self.rows_scroll.winfo_children():
            child.destroy()

        users = get_all_users()

        role_colors = {
            "Hospital Administrator": (("#FEE2E2", "#450A0A"), ("#B91C1C", "#F87171")),
            "Staff": (("#E0F2FE", "#0C2E4E"), ("#0284C7", "#38BDF8")),
            "Doctor": (("#DCFCE7", "#064E3B"), ("#15803D", "#34D399")),
            "Patient": (("#FEF3C7", "#451A03"), ("#B45309", "#FBBF24")),
        }

        for i, u in enumerate(users):
            row_bg = ("#F8FAFC", "#0C152B") if i % 2 == 0 else ("#FFFFFF", "#0F172A")
            row = ctk.CTkFrame(self.rows_scroll, height=42, fg_color=row_bg, corner_radius=0)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # ID
            ctk.CTkLabel(row, text=str(u["id"]), font=ctk.CTkFont(size=11), text_color=("#64748B", "#94A3B8"), width=45, anchor="w", padx=8).pack(side="left")

            # Username
            ctk.CTkLabel(row, text=u["username"], font=ctk.CTkFont(size=11, weight="bold"), text_color=("#0F172A", "#F8FAFC"), width=130, anchor="w", padx=8).pack(side="left")

            # Full Name
            ctk.CTkLabel(row, text=u["full_name"], font=ctk.CTkFont(size=11), text_color=("#0F172A", "#F8FAFC"), width=160, anchor="w", padx=8).pack(side="left")

            # Role Badge
            bg_c, txt_c = role_colors.get(u["role"], (("#F1F5F9", "#1E293B"), ("#64748B", "#94A3B8")))
            r_frame = ctk.CTkFrame(row, width=140, fg_color="transparent")
            r_frame.pack(side="left")
            ctk.CTkLabel(
                r_frame,
                text=u["role"],
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=bg_c,
                text_color=txt_c,
                corner_radius=6,
                padx=8,
                pady=2,
            ).pack(side="left", padx=4)

            # Email
            ctk.CTkLabel(row, text=u["email"], font=ctk.CTkFont(size=10), text_color=("#64748B", "#94A3B8"), width=170, anchor="w", padx=8).pack(side="left")

            # Linked Entity
            linked_txt = "—"
            if u.get("linked_patient_id"):
                linked_txt = f"Patient #{u['linked_patient_id']}"
            elif u.get("linked_doctor_id"):
                linked_txt = f"Doctor #{u['linked_doctor_id']}"
            ctk.CTkLabel(row, text=linked_txt, font=ctk.CTkFont(size=10), text_color=("#64748B", "#94A3B8"), width=130, anchor="w", padx=8).pack(side="left")

            # Status Badge
            is_active = u.get("is_active") == 1
            s_bg = ("#DCFCE7", "#064E3B") if is_active else ("#F1F5F9", "#1E293B")
            s_fg = ("#15803D", "#34D399") if is_active else ("#64748B", "#94A3B8")
            s_frame = ctk.CTkFrame(row, width=90, fg_color="transparent")
            s_frame.pack(side="left")
            ctk.CTkLabel(
                s_frame,
                text="Active" if is_active else "Disabled",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=s_bg,
                text_color=s_fg,
                corner_radius=6,
                padx=8,
                pady=2,
            ).pack(side="left", padx=4)

            # Actions
            act_box = ctk.CTkFrame(row, width=150, fg_color="transparent")
            act_box.pack(side="left")

            # Toggle status button
            btn_txt = "Disable" if is_active else "Enable"
            tog_btn = ctk.CTkButton(
                act_box,
                text=btn_txt,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=("#F1F5F9", "#1E2D4A"),
                text_color=("#DC2626", "#F87171") if is_active else ("#16A34A", "#4ADE80"),
                hover_color=("#E2E8F0", "#2B3E63"),
                border_width=1,
                border_color=("#CBD5E1", "#33456B"),
                height=24,
                width=55,
                command=lambda uid=u["id"]: self._toggle_status(uid),
            )
            tog_btn.pack(side="left", padx=2)

            # Reset Password button
            reset_btn = ctk.CTkButton(
                act_box,
                text="🔑 Pwd",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=("#F1F5F9", "#1E2D4A"),
                text_color=("#0F172A", "#F8FAFC"),
                hover_color=("#E2E8F0", "#2B3E63"),
                border_width=1,
                border_color=("#CBD5E1", "#33456B"),
                height=24,
                width=50,
                command=lambda uid=u["id"], un=u["username"]: self._reset_password(uid, un),
            )
            reset_btn.pack(side="left", padx=2)

    def _toggle_status(self, user_id: int) -> None:
        """Toggle user active status."""
        ok, msg = toggle_user_status(user_id)
        self.load_users()

    def _reset_password(self, user_id: int, username: str) -> None:
        """Prompt to reset user password."""
        dialog = ctk.CTkInputDialog(text=f"Enter new password for '{username}':", title="Reset Password")
        new_pwd = dialog.get_input()
        if new_pwd:
            ok, msg = reset_user_password(user_id, new_pwd)
            self.load_users()

    def _open_new_user_modal(self) -> None:
        """Open modal to register a new user account."""
        NewUserModal(self.winfo_toplevel(), on_success=lambda: self.load_users())


class NewUserModal(ctk.CTkToplevel):
    """Modal for registering a new user account with role selection."""

    def __init__(self, master, on_success=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_success = on_success

        self.title("Create New User Account")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_geometry()
        self._build_ui()

        self.lift()
        self.focus_force()

    def _apply_geometry(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 480, 430
        x = max(0, (sw - w) // 2)
        y = max(10, (sh - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(pad, text="➕ Create New System User", font=ctk.CTkFont(size=16, weight="bold"), text_color=("#0284C7", "#06B6D4"), anchor="w").pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(pad, text="Register credentials and assign clinical access role.", font=ctk.CTkFont(size=11), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 14))

        # Inputs
        ctk.CTkLabel(pad, text="Username *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 1))
        self.uname_entry = ctk.CTkEntry(pad, placeholder_text="e.g. nurse_rekha", height=32)
        self.uname_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(pad, text="Full Name *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 1))
        self.fname_entry = ctk.CTkEntry(pad, placeholder_text="e.g. Rekha Sharma", height=32)
        self.fname_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(pad, text="Email Address *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 1))
        self.email_entry = ctk.CTkEntry(pad, placeholder_text="e.g. rekha.sharma@hospital.demo", height=32)
        self.email_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(pad, text="Role Assignment *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 1))
        self.role_menu = ctk.CTkOptionMenu(pad, values=USER_ROLES, height=32)
        self.role_menu.set("Staff")
        self.role_menu.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(pad, text="Initial Password *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 1))
        self.pwd_entry = ctk.CTkEntry(pad, placeholder_text="At least 6 characters", show="•", height=32)
        self.pwd_entry.pack(fill="x", pady=(0, 8))

        self.err_lbl = ctk.CTkLabel(pad, text="", font=ctk.CTkFont(size=11), text_color="#EF4444", anchor="w")
        self.err_lbl.pack(fill="x", pady=(0, 10))

        # Footer
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        close_btn = ctk.CTkButton(footer, text="Cancel", width=80, height=34, fg_color=("#E2E8F0", "#334155"), text_color=("#0F172A", "#F8FAFC"), command=self.destroy)
        close_btn.pack(side="right", padx=(8, 0))

        save_btn = ctk.CTkButton(footer, text="Create Account", height=34, fg_color=("#0284C7", "#0284C7"), hover_color=("#0369A1", "#0369A1"), command=self._save)
        save_btn.pack(side="right")

    def _save(self) -> None:
        self.err_lbl.configure(text="")
        data = {
            "username": self.uname_entry.get().strip(),
            "full_name": self.fname_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "role": self.role_menu.get().strip(),
            "password": self.pwd_entry.get().strip(),
        }
        ok, msg, new_id = create_user(data)
        if ok:
            self.destroy()
            if self.on_success:
                self.on_success()
        else:
            self.err_lbl.configure(text=msg)
