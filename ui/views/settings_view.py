"""User Profile Settings & Preferences View for Hospital Management System — Q08.
Provides live SQLite persistence for administrator profile details, role,
application appearance, scaling, default view, and safety utilities.
"""
from typing import Callable, Optional
import customtkinter as ctk

from config.constants import APP_SUBTITLE, STUDENT_NAME, STUDENT_SECTION
from database.connection import get_db_connection
from database.seed_data import seed_database
from services.profile_service import (
    ALLOWED_ROLES,
    ALLOWED_SCALING,
    ALLOWED_THEMES,
    ALLOWED_VIEWS,
    get_user_profile,
    update_user_profile,
)


class SettingsView(ctk.CTkFrame):
    """User Profile Settings view with full validation, SQLite persistence, and theme integration."""

    def __init__(
        self,
        master,
        on_theme_change: Optional[Callable[[str], None]] = None,
        on_profile_updated: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._notice_timer_id: Optional[str] = None
        self.on_theme_change = on_theme_change
        self.on_profile_updated = on_profile_updated
        self.profile_data = get_user_profile() or {}

        # Build UI layout
        self._build_header()
        self._build_notification_banner()
        self._build_scrollable_container()

    def _build_header(self) -> None:
        """Header with settings title and contextual description."""
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=24, pady=(20, 10))

        title = ctk.CTkLabel(
            self.header,
            text="User Profile & System Preferences",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            self.header,
            text="Manage administrator profile, application appearance, and database configuration.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_notification_banner(self) -> None:
        """Feedback toast/banner for immediate success and error reporting."""
        self.notice_banner = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#DCFCE7", "#14532D"),
            text_color=("#15803D", "#4ADE80"),
            corner_radius=8,
            height=32,
        )

    def _show_notice(self, message: str, is_error: bool = False) -> None:
        """Show temporary feedback banner with timer cancellation."""
        if is_error:
            self.notice_banner.configure(
                text=f"  ⚠️  {message}",
                fg_color=("#FEE2E2", "#7F1D1D"),
                text_color=("#DC2626", "#FCA5A5"),
            )
        else:
            self.notice_banner.configure(
                text=f"  ✓  {message}",
                fg_color=("#DCFCE7", "#14532D"),
                text_color=("#15803D", "#4ADE80"),
            )
        self.notice_banner.pack(fill="x", padx=24, pady=(0, 10), after=self.header)
        if self._notice_timer_id is not None:
            self.after_cancel(self._notice_timer_id)
        self._notice_timer_id = self.after(4000, self._hide_notice)

    def _hide_notice(self) -> None:
        """Dismiss notice banner safely checking widget existence."""
        self._notice_timer_id = None
        if self.winfo_exists() and hasattr(self, "notice_banner") and self.notice_banner.winfo_exists():
            self.notice_banner.pack_forget()

    def destroy(self) -> None:
        """Cancel pending notification timers on view destruction."""
        if hasattr(self, "_notice_timer_id") and self._notice_timer_id is not None:
            self.after_cancel(self._notice_timer_id)
            self._notice_timer_id = None
        super().destroy()

    def _build_scrollable_container(self) -> None:
        """Scrollable container ensuring high-DPI scaling adaptability."""
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.scroll_container.grid_columnconfigure((0, 1), weight=1)

        # Left Column: User Profile Card
        self._build_profile_card(self.scroll_container)

        # Right Column: System Preferences Card
        self._build_preferences_card(self.scroll_container)

        # Full Width: System Integrity & Maintenance Card
        self._build_maintenance_card(self.scroll_container)

    def _build_profile_card(self, parent: ctk.CTkFrame) -> None:
        """Card for viewing and editing Administrator Profile details."""
        p_card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        p_card.grid(row=0, column=0, padx=(0, 8), pady=(0, 16), sticky="nsew")

        # Card Title
        ctk.CTkLabel(
            p_card,
            text="Administrator Profile Details",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=20, pady=(18, 4))

        ctk.CTkLabel(
            p_card,
            text="Update personal contact information and operational role in SQLite.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        # 1. Username (Read-only badge)
        u_row = ctk.CTkFrame(p_card, fg_color="transparent")
        u_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(
            u_row,
            text="Username:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=110,
            anchor="w",
        ).pack(side="left")
        u_chip = ctk.CTkLabel(
            u_row,
            text=f"@{self.profile_data.get('username', 'deepak_admin')}",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E2E8F0", "#26293B"),
            text_color=("#0284C7", "#38BDF8"),
            corner_radius=6,
            padx=10,
            height=26,
        )
        u_chip.pack(side="left")

        # 2. Full Name
        fn_row = ctk.CTkFrame(p_card, fg_color="transparent")
        fn_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            fn_row,
            text="Full Name *:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=110,
            anchor="w",
        ).pack(side="left")
        self.fullname_entry = ctk.CTkEntry(
            fn_row,
            height=32,
            corner_radius=6,
        )
        self.fullname_entry.insert(0, self.profile_data.get("full_name", STUDENT_NAME))
        self.fullname_entry.pack(side="left", fill="x", expand=True)

        # 3. Role
        role_row = ctk.CTkFrame(p_card, fg_color="transparent")
        role_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            role_row,
            text="Role / Title *:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=110,
            anchor="w",
        ).pack(side="left")
        self.role_menu = ctk.CTkOptionMenu(
            role_row,
            values=ALLOWED_ROLES,
            height=32,
            corner_radius=6,
        )
        current_role = self.profile_data.get("role", "Hospital Administrator")
        if current_role in ALLOWED_ROLES:
            self.role_menu.set(current_role)
        else:
            self.role_menu.set("Hospital Administrator")
        self.role_menu.pack(side="left", fill="x", expand=True)

        # 4. Email Address
        em_row = ctk.CTkFrame(p_card, fg_color="transparent")
        em_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            em_row,
            text="Email Address *:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=110,
            anchor="w",
        ).pack(side="left")
        self.email_entry = ctk.CTkEntry(
            em_row,
            height=32,
            corner_radius=6,
        )
        self.email_entry.insert(0, self.profile_data.get("email", "deepak.joshi.tqm@hospital.demo"))
        self.email_entry.pack(side="left", fill="x", expand=True)

        # 5. Phone Number
        ph_row = ctk.CTkFrame(p_card, fg_color="transparent")
        ph_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            ph_row,
            text="Phone Number *:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=110,
            anchor="w",
        ).pack(side="left")
        self.phone_entry = ctk.CTkEntry(
            ph_row,
            height=32,
            corner_radius=6,
        )
        self.phone_entry.insert(0, self.profile_data.get("phone", "+91 98765 43210"))
        self.phone_entry.pack(side="left", fill="x", expand=True)

        # Academic Metadata Badge
        acad_row = ctk.CTkFrame(p_card, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
        acad_row.pack(fill="x", padx=20, pady=(10, 14))
        ctk.CTkLabel(
            acad_row,
            text=f"🎓 {APP_SUBTITLE} • {STUDENT_SECTION}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            padx=10,
            pady=6,
        ).pack(anchor="w")


        # Action Buttons
        btn_row = ctk.CTkFrame(p_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(4, 18))

        save_p_btn = ctk.CTkButton(
            btn_row,
            text="💾 Save Profile Details",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=34,
            corner_radius=6,
            command=self._save_profile_details,
        )
        save_p_btn.pack(side="left", padx=(0, 8))

        reset_p_btn = ctk.CTkButton(
            btn_row,
            text="↺ Reset to Saved",
            font=ctk.CTkFont(size=12),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            height=34,
            corner_radius=6,
            command=self._reset_profile_fields,
        )
        reset_p_btn.pack(side="left")

    def _build_preferences_card(self, parent: ctk.CTkFrame) -> None:
        """Card for configuring Application Appearance, Scaling, and Preferences."""
        s_card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        s_card.grid(row=0, column=1, padx=(8, 0), pady=(0, 16), sticky="nsew")

        ctk.CTkLabel(
            s_card,
            text="Interface & Usability Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=20, pady=(18, 4))

        ctk.CTkLabel(
            s_card,
            text="Customize theme mode, UI scaling factor, default startup view, and alerts.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=20, pady=(0, 14))

        # 1. Appearance Mode
        th_row = ctk.CTkFrame(s_card, fg_color="transparent")
        th_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            th_row,
            text="Appearance Mode:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=140,
            anchor="w",
        ).pack(side="left")
        self.theme_menu = ctk.CTkOptionMenu(
            th_row,
            values=ALLOWED_THEMES,
            command=self._on_theme_selection,
            height=32,
            corner_radius=6,
        )
        current_theme = self.profile_data.get("theme_preference", ctk.get_appearance_mode().capitalize())
        self.theme_menu.set(current_theme if current_theme in ALLOWED_THEMES else "Dark")
        self.theme_menu.pack(side="left", fill="x", expand=True)

        # 2. UI Scaling Factor
        sc_row = ctk.CTkFrame(s_card, fg_color="transparent")
        sc_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            sc_row,
            text="UI Scaling Factor:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=140,
            anchor="w",
        ).pack(side="left")
        self.scaling_menu = ctk.CTkOptionMenu(
            sc_row,
            values=ALLOWED_SCALING,
            command=self._on_scaling_selection,
            height=32,
            corner_radius=6,
        )
        current_scaling = self.profile_data.get("scaling_factor", "100%")
        self.scaling_menu.set(current_scaling if current_scaling in ALLOWED_SCALING else "100%")
        self.scaling_menu.pack(side="left", fill="x", expand=True)

        # 3. Default Startup View
        vw_row = ctk.CTkFrame(s_card, fg_color="transparent")
        vw_row.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            vw_row,
            text="Default Startup View:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=140,
            anchor="w",
        ).pack(side="left")
        self.view_menu = ctk.CTkOptionMenu(
            vw_row,
            values=ALLOWED_VIEWS,
            height=32,
            corner_radius=6,
        )
        current_view = self.profile_data.get("default_view", "Dashboard")
        self.view_menu.set(current_view if current_view in ALLOWED_VIEWS else "Dashboard")
        self.view_menu.pack(side="left", fill="x", expand=True)

        # 4. System Notifications Switch
        nt_row = ctk.CTkFrame(s_card, fg_color="transparent")
        nt_row.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(
            nt_row,
            text="Desktop Alerts:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            width=140,
            anchor="w",
        ).pack(side="left")
        self.notifications_switch = ctk.CTkSwitch(
            nt_row,
            text="Enable toast notifications for CRUD actions",
            font=ctk.CTkFont(size=12),
        )
        notif_state = self.profile_data.get("notifications_enabled", 1)
        if notif_state:
            self.notifications_switch.select()
        else:
            self.notifications_switch.deselect()
        self.notifications_switch.pack(side="left")

        # Action Button
        btn_row2 = ctk.CTkFrame(s_card, fg_color="transparent")
        btn_row2.pack(fill="x", padx=20, pady=(16, 18))

        save_pref_btn = ctk.CTkButton(
            btn_row2,
            text="💾 Save Preferences",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=34,
            corner_radius=6,
            command=self._save_preferences,
        )
        save_pref_btn.pack(side="left")

    def _build_maintenance_card(self, parent: ctk.CTkFrame) -> None:
        """Card summarizing Database Integrity and Keyboard Shortcuts reference."""
        m_card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        m_card.grid(row=1, column=0, columnspan=2, pady=(0, 20), sticky="nsew")

        # Header
        ctk.CTkLabel(
            m_card,
            text="System Integrity & Database Utilities",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=20, pady=(16, 4))

        # Status text with live counts
        counts_text = self._get_db_status_text()
        self.db_status_lbl = ctk.CTkLabel(
            m_card,
            text=counts_text,
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
            justify="left",
            anchor="w",
        )
        self.db_status_lbl.pack(anchor="w", padx=20, pady=(0, 12))

        # Safety info box
        info_box = ctk.CTkFrame(m_card, fg_color=("#F8FAFC", "#26293B"), corner_radius=8)
        info_box.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            info_box,
            text="🛡️ Data Protection Safeguard: All Patient, Physician, and Appointment records are saved permanently to 'hospital_tqm.db'. Foreign-key constraints and slot collision protection are actively enforced.",
            font=ctk.CTkFont(size=11),
            text_color=("#15803D", "#4ADE80"),
            justify="left",
            wraplength=680,
            padx=14,
            pady=10,
        ).pack(anchor="w")

    def _get_db_status_text(self) -> str:
        """Fetch live database statistics for the status card."""
        try:
            with get_db_connection() as conn:
                p_c = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
                d_c = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
                a_c = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]
                t_c = conn.execute("SELECT COUNT(*) FROM tqm_defect_logs;").fetchone()[0]
                return f"Active SQLite Database: 'hospital_tqm.db'  •  Persisted Records: {p_c} Patients, {d_c} Doctors, {a_c} Appointments, {t_c} TQM Quality Defects."
        except Exception:
            return "Active SQLite Database: 'hospital_tqm.db'"

    # =========================================================================
    # ACTION HANDLERS
    # =========================================================================
    def _save_profile_details(self) -> None:
        """Validate and commit user profile changes to SQLite."""
        username = self.profile_data.get("username", "deepak_admin")
        updated_data = {
            "full_name": self.fullname_entry.get().strip(),
            "role": self.role_menu.get().strip(),
            "email": self.email_entry.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "theme_preference": self.theme_menu.get().strip(),
            "scaling_factor": self.scaling_menu.get().strip(),
            "default_view": self.view_menu.get().strip(),
            "notifications_enabled": 1 if self.notifications_switch.get() else 0,
        }

        success, msg = update_user_profile(username, updated_data)
        if success:
            self.profile_data = get_user_profile(username) or updated_data
            if self.on_profile_updated:
                self.on_profile_updated(self.profile_data)
            self._show_notice(f"Profile updated successfully! Welcome, {updated_data['full_name']}.")
        else:
            self._show_notice(msg, is_error=True)

    def _save_preferences(self) -> None:
        """Validate and commit appearance and system preferences to SQLite."""
        username = self.profile_data.get("username", "deepak_admin")
        theme_val = self.theme_menu.get().strip()
        scaling_val = self.scaling_menu.get().strip()
        view_val = self.view_menu.get().strip()
        notif_val = 1 if self.notifications_switch.get() else 0

        # Preserve existing profile contact fields
        updated_data = {
            "full_name": self.fullname_entry.get().strip(),
            "role": self.role_menu.get().strip(),
            "email": self.email_entry.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "theme_preference": theme_val,
            "scaling_factor": scaling_val,
            "default_view": view_val,
            "notifications_enabled": notif_val,
        }

        success, msg = update_user_profile(username, updated_data)
        if success:
            self.profile_data = get_user_profile(username) or updated_data
            # Apply theme instantly
            self._on_theme_selection(theme_val)
            # Apply scaling instantly
            self._on_scaling_selection(scaling_val)
            if self.on_profile_updated:
                self.on_profile_updated(self.profile_data)
            self._show_notice("Preferences saved and applied successfully!")
        else:
            self._show_notice(msg, is_error=True)

    def _reset_profile_fields(self) -> None:
        """Reset form entry values back to current SQLite database state."""
        self.profile_data = get_user_profile() or {}
        self.fullname_entry.delete(0, "end")
        self.fullname_entry.insert(0, self.profile_data.get("full_name", STUDENT_NAME))

        current_role = self.profile_data.get("role", "Hospital Administrator")
        if current_role in ALLOWED_ROLES:
            self.role_menu.set(current_role)

        self.email_entry.delete(0, "end")
        self.email_entry.insert(0, self.profile_data.get("email", "deepak.joshi.tqm@hospital.demo"))

        self.phone_entry.delete(0, "end")
        self.phone_entry.insert(0, self.profile_data.get("phone", "+91 98765 43210"))

        self._show_notice("Profile fields reset to last saved values.")

    def _on_theme_selection(self, mode: str) -> None:
        """Handle theme dropdown selection."""
        ctk.set_appearance_mode(mode)
        if self.on_theme_change:
            self.on_theme_change(mode)

    def _on_scaling_selection(self, scaling_str: str) -> None:
        """Handle UI scaling factor selection."""
        try:
            scale_val = int(scaling_str.replace("%", "")) / 100.0
            ctk.set_widget_scaling(scale_val)
        except Exception as e:
            print(f"Error applying scaling: {e}")
