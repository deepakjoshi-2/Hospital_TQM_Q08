"""User Accounts Management View for Hospital Administrator.
Enables creating new staff/doctor/patient accounts, toggling account active status,
and resetting passwords with PBKDF2 hashing.
"""
from typing import Dict, List, Optional
import customtkinter as ctk

from config.constants import ROLE_ADMIN, USER_ROLES
from services.appointment_service import get_doctor_dropdown_options, get_patient_dropdown_options
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

        if not self.current_user or self.current_user.get("role") != ROLE_ADMIN:
            self._build_unauthorized_view()
            return

        self._build_header()
        self._build_table_container()
        self.load_users()

    def _build_unauthorized_view(self) -> None:
        """Access denied banner displayed for non-administrative roles."""
        card = ctk.CTkFrame(
            self,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#FCA5A5", "#7F1D1D"),
            corner_radius=12,
        )
        card.place(relx=0.5, rely=0.45, anchor="center")

        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(padx=36, pady=32)

        ctk.CTkLabel(
            pad,
            text="🔒 Access Restricted — Administrator Only",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#DC2626", "#F87171"),
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            pad,
            text="System user account administration and credential provisioning are restricted\nstrictly to authorized Hospital Administrators.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
            justify="center",
        ).pack(pady=(0, 16))

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
    """Modal for registering a new user account with role selection and linked entity mapping."""

    def __init__(self, master, on_success=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_success = on_success
        self._password_visible = False

        self.doctor_options = get_doctor_dropdown_options()
        self.patient_options = get_patient_dropdown_options()
        self.doc_id_map = {lbl: did for did, lbl in self.doctor_options}
        self.pat_id_map = {lbl: pid for pid, lbl in self.patient_options}

        self.title("Create New User Account")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_geometry()
        self._build_ui()

        self.bind("<Escape>", lambda e: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_geometry(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling() if hasattr(self, "_get_window_scaling") else 1.0
        target_w = min(520, int((sw - 40) / scaling))
        target_h = min(540, int((sh - 80) / scaling))
        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        x = max(0, (sw - phys_w) // 2)
        y = max(10, (sh - phys_h) // 2 - 20)
        self.geometry(f"{target_w}x{target_h}+{x}+{y}")

    def _build_ui(self) -> None:
        # 1. FIXED HEADER
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(side="top", fill="x", padx=24, pady=(16, 4))

        ctk.CTkLabel(
            header,
            text="➕ Create New System User",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            header,
            text="Provision credentials, clinical access role, and entity mappings.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(1, 4))

        # Error / Status Banner
        self.err_lbl = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#EF4444",
            wraplength=460,
            anchor="w",
        )

        # 2. FIXED FOOTER (Packed BOTTOM FIRST so it is never pushed off screen at 150% scaling)
        footer = ctk.CTkFrame(
            self,
            fg_color=("#F1F5F9", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
            corner_radius=8,
            height=52,
        )
        footer.pack(side="bottom", fill="x", padx=16, pady=(4, 12))
        footer.pack_propagate(False)

        tip_lbl = ctk.CTkLabel(
            footer,
            text="* Required fields  |  Esc to Cancel",
            font=ctk.CTkFont(size=10),
            text_color=("#64748B", "#94A3B8"),
        )
        tip_lbl.pack(side="left", padx=14)

        close_btn = ctk.CTkButton(
            footer,
            text="Cancel",
            width=80,
            height=32,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=self.destroy,
        )
        close_btn.pack(side="right", padx=(8, 12), pady=10)

        self.save_btn = ctk.CTkButton(
            footer,
            text="✓ Create Account",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            command=self._save,
        )
        self.save_btn.pack(side="right", pady=10)

        # 3. SCROLLABLE FORM BODY (Packed in center)
        self.form_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=("white", "#181A26"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
            corner_radius=8,
        )
        self.form_scroll.pack(side="top", fill="both", expand=True, padx=16, pady=(2, 4))

        # Inputs
        ctk.CTkLabel(self.form_scroll, text="Username *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", padx=12, pady=(8, 1))
        self.uname_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. nurse_rekha", height=32)
        self.uname_entry.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkLabel(self.form_scroll, text="Full Name *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", padx=12, pady=(4, 1))
        self.fname_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Rekha Sharma", height=32)
        self.fname_entry.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkLabel(self.form_scroll, text="Email Address *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", padx=12, pady=(4, 1))
        self.email_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. rekha.sharma@hospital.demo", height=32)
        self.email_entry.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkLabel(self.form_scroll, text="Role Assignment *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", padx=12, pady=(4, 1))
        self.role_menu = ctk.CTkOptionMenu(self.form_scroll, values=USER_ROLES, height=32, command=self._on_role_change)
        self.role_menu.set("Staff")
        self.role_menu.pack(fill="x", padx=12, pady=(0, 6))

        # Dynamic Linked Doctor Frame
        self.doc_link_frame = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        ctk.CTkLabel(self.doc_link_frame, text="Link to Doctor Profile *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(2, 1))
        doc_labels = list(self.doc_id_map.keys()) if self.doc_id_map else ["No Doctors Available"]
        self.doc_menu = ctk.CTkOptionMenu(self.doc_link_frame, values=doc_labels, height=32)
        if doc_labels:
            self.doc_menu.set(doc_labels[0])
        self.doc_menu.pack(fill="x", pady=(0, 6))

        # Dynamic Linked Patient Frame
        self.pat_link_frame = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        ctk.CTkLabel(self.pat_link_frame, text="Link to Patient Record *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(2, 1))
        pat_labels = list(self.pat_id_map.keys()) if self.pat_id_map else ["No Patients Available"]
        self.pat_menu = ctk.CTkOptionMenu(self.pat_link_frame, values=pat_labels, height=32)
        if pat_labels:
            self.pat_menu.set(pat_labels[0])
        self.pat_menu.pack(fill="x", pady=(0, 6))

        # Password Row with Show/Hide toggle
        ctk.CTkLabel(self.form_scroll, text="Initial Password *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", padx=12, pady=(4, 1))

        pwd_row = ctk.CTkFrame(self.form_scroll, fg_color="transparent")
        pwd_row.pack(fill="x", padx=12, pady=(0, 10))

        self.pwd_entry = ctk.CTkEntry(pwd_row, placeholder_text="At least 6 characters", show="•", height=32)
        self.pwd_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.toggle_pwd_btn = ctk.CTkButton(
            pwd_row,
            text="👁 Show",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=70,
            height=32,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=self._toggle_password_visibility,
        )
        self.toggle_pwd_btn.pack(side="right")

    def _toggle_password_visibility(self) -> None:
        """Toggle password masking."""
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.pwd_entry.configure(show="")
            self.toggle_pwd_btn.configure(text="🔒 Hide")
        else:
            self.pwd_entry.configure(show="•")
            self.toggle_pwd_btn.configure(text="👁 Show")

    def _on_role_change(self, selected_role: str) -> None:
        """Dynamically display linked Doctor or Patient selector when required."""
        if selected_role == "Doctor":
            self.pat_link_frame.pack_forget()
            self.doc_link_frame.pack(fill="x", padx=12, pady=(0, 6), before=self.form_scroll.winfo_children()[-2])
        elif selected_role == "Patient":
            self.doc_link_frame.pack_forget()
            self.pat_link_frame.pack(fill="x", padx=12, pady=(0, 6), before=self.form_scroll.winfo_children()[-2])
        else:
            self.doc_link_frame.pack_forget()
            self.pat_link_frame.pack_forget()

    def _show_error(self, message: str) -> None:
        """Show error banner in header."""
        self.err_lbl.configure(text=f"  ⚠️  {message}")
        if not self.err_lbl.winfo_ismapped():
            self.err_lbl.pack(fill="x", pady=(4, 0))

    def _clear_error(self) -> None:
        """Dismiss error banner."""
        if self.err_lbl.winfo_ismapped():
            self.err_lbl.pack_forget()

    def _save(self) -> None:
        self._clear_error()
        selected_role = self.role_menu.get().strip()

        linked_doc_id = None
        linked_pat_id = None

        if selected_role == "Doctor":
            doc_choice = self.doc_menu.get()
            linked_doc_id = self.doc_id_map.get(doc_choice)
            if not linked_doc_id:
                self._show_error("Please select a valid Doctor to associate with this login account.")
                return
        elif selected_role == "Patient":
            pat_choice = self.pat_menu.get()
            linked_pat_id = self.pat_id_map.get(pat_choice)
            if not linked_pat_id:
                self._show_error("Please select a valid Patient record to associate with this login account.")
                return

        data = {
            "username": self.uname_entry.get().strip(),
            "full_name": self.fname_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "role": selected_role,
            "password": self.pwd_entry.get().strip(),
            "linked_doctor_id": linked_doc_id,
            "linked_patient_id": linked_pat_id,
        }

        self.save_btn.configure(state="disabled", text="Creating Account...")
        self.update_idletasks()

        ok, msg, new_id = create_user(data)
        if ok:
            self.destroy()
            if self.on_success:
                self.on_success()
        else:
            self._show_error(msg)
            self.save_btn.configure(state="normal", text="✓ Create Account")
