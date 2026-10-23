"""Main application window for Hospital Management System — Q08."""
import tkinter as tk
from typing import Dict, Optional
import customtkinter as ctk

from config.constants import (
    APP_NAME,
    STUDENT_NAME,
    STUDENT_BRANCH,
    STUDENT_SECTION,
)
from database.seed_data import seed_database
from services.auth_service import (
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
    get_current_user,
    has_permission,
    login,
    logout,
    set_current_user,
)
from services.notification_service import get_unread_notification_count
from services.profile_service import get_user_profile
from ui.components.notification_modal import NotificationCenterModal
from ui.components.scroll_manager import ScrollManager
from ui.views import (
    AppointmentsView,
    BillingView,
    DashboardView,
    DoctorsView,
    LoginView,
    PatientsView,
    ReportsView,
    SettingsView,
    TQMView,
    UserManagementView,
)



class HospitalApp(ctk.CTk):
    """Main desktop application window with responsive sidebar and modular views."""

    def __init__(self, start_login: bool = False):
        super().__init__()

        # Install centralized mouse-wheel scrolling across all views and modals
        ScrollManager.install(self)

        # Initial Appearance & Theme configuration
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Window Metadata
        self.title(f"{APP_NAME} — [{STUDENT_NAME} | {STUDENT_BRANCH}]")

        # Center on screen adaptively to monitor dimensions
        self._center_window()

        # Layout Setup: 2-column grid (Sidebar + Main Area)
        self.grid_columnconfigure(0, weight=0, minsize=230)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Active view tracking
        self.active_view_name = "Dashboard"
        self.nav_buttons: Dict[str, ctk.CTkButton] = {}
        self.current_view_frame: Optional[ctk.CTkFrame] = None
        self.login_container: Optional[ctk.CTkFrame] = None
        self.login_view_frame: Optional[ctk.CTkFrame] = None

        # Build Main UI Shell frames
        self._build_sidebar()
        self._build_content_area()

        # Register Keyboard Shortcuts (Q08 Feature 4)
        self._register_shortcuts()

        # Startup flow: Dedicated full login screen on fresh launch (start_login=True),
        # or resume authenticated dashboard if user session is active / direct view mode.
        current_u = get_current_user()
        if start_login:
            self.show_login_screen()
        else:
            if current_u is None:
                login("admin", "Admin@123")
            self._rebuild_sidebar_menu()
            self.update_profile_display()
            self.show_view("Dashboard")

        # Guarantee window is visible and elevated above background terminal
        self.after(100, self._ensure_visible_on_screen)

    def _center_window(self) -> None:
        """Center application window dynamically based on monitor resolution."""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Compute safe dimensions tailored to screen with taskbar allowance
        w = min(1160, max(850, int(sw * 0.90)))
        h = min(650, max(500, int(sh * 0.86)))
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)

        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min(800, sw - 40), min(480, sh - 70))

    def _ensure_visible_on_screen(self) -> None:
        """Ensure window is deiconified, elevated above terminal, and focused."""
        try:
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(200, lambda: self.attributes("-topmost", False))
            self.focus_force()
        except Exception:
            pass

    def _build_sidebar(self) -> None:
        """Create modern navigation sidebar with hospital branding and theme controls."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color=("#F8FAFC", "#0C152B"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # 1. Hospital Brand Header
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(20, 10))

        logo_lbl = ctk.CTkLabel(
            brand_frame,
            text="🏥 Hospital TQM",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        )
        logo_lbl.pack(fill="x")

        sub_lbl = ctk.CTkLabel(
            brand_frame,
            text="Clinical Quality Analytics • Q08",
            font=ctk.CTkFont(size=11),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        )
        sub_lbl.pack(fill="x")

        # Student Badge
        badge = ctk.CTkLabel(
            brand_frame,
            text=f"{STUDENT_NAME} • {STUDENT_SECTION}",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#F1F5F9", "#131E36"),
            text_color=("#0A192F", "#F8FAFC"),
            corner_radius=6,
            height=24,
        )
        badge.pack(fill="x", pady=(8, 0))

        # Separator line
        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color=("#CBD5E1", "#1E2D4A"))
        sep.pack(fill="x", padx=16, pady=(12, 16))

        # 2. Navigation Menu Container (Dynamically rendered per role)
        self.nav_menu_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_menu_container.pack(fill="both", expand=True)
        self._rebuild_sidebar_menu()

        # 3. Bottom Controls Area (Theme Toggle, Scaling, DB Status)
        bottom_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_box.pack(fill="x", side="bottom", padx=16, pady=16)

        # Database connection indicator
        db_pill = ctk.CTkLabel(
            bottom_box,
            text="● SQLite Active (WAL Mode)",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#DCFCE7", "#064E3B"),
            text_color=("#15803D", "#34D399"),
            corner_radius=8,
            height=24,
            anchor="center",
        )
        db_pill.pack(fill="x", pady=(0, 10))

        # Theme Switcher (Q08 Feature 3)
        theme_lbl = ctk.CTkLabel(
            bottom_box,
            text="Appearance Theme:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        theme_lbl.pack(fill="x")

        self.theme_switch = ctk.CTkOptionMenu(
            bottom_box,
            values=["Dark", "Light", "System"],
            command=self.set_theme_mode,
            height=30,
            corner_radius=6,
        )
        self.theme_switch.set("Dark")
        self.theme_switch.pack(fill="x", pady=(4, 6))

        # Academic Version Tag
        v_tag = ctk.CTkLabel(
            bottom_box,
            text="Academic Prototype — v1.0",
            font=ctk.CTkFont(size=9),
            text_color=("#64748B", "#64748B"),
            anchor="center",
        )
        v_tag.pack(fill="x")

    def _rebuild_sidebar_menu(self) -> None:
        """Dynamically render navigation buttons based on logged-in user role permissions."""
        for child in self.nav_menu_container.winfo_children():
            child.destroy()
        self.nav_buttons.clear()

        user = get_current_user() or {}
        role = user.get("role", ROLE_ADMIN)

        if role == ROLE_ADMIN:
            menu_items = [
                ("Dashboard", "📊  Dashboard"),
                ("Patients", "👥  Patients Directory"),
                ("Doctors", "👨‍⚕️  Physicians Roster"),
                ("Appointments", "📅  Appointments"),
                ("Reports", "📈  Visual Reports"),
                ("Billing", "💳  Billing & Receipts"),
                ("TQM", "🛡️  TQM Quality Tools"),
                ("Users", "👥  User Accounts"),
                ("Settings", "⚙️  User Settings"),
            ]
        elif role == ROLE_STAFF:
            menu_items = [
                ("Dashboard", "📊  Dashboard"),
                ("Patients", "👥  Patients Directory"),
                ("Doctors", "👨‍⚕️  Physicians Roster"),
                ("Appointments", "📅  Appointments"),
                ("Billing", "💳  Billing & Receipts"),
                ("Settings", "⚙️  User Settings"),
            ]
        elif role == ROLE_DOCTOR:
            menu_items = [
                ("Appointments", "📅  My Appointments"),
                ("Patients", "👥  Patient Directory"),
                ("Reports", "📈  Clinical Reports"),
                ("Billing", "💳  Consultation Billings"),
                ("Settings", "⚙️  User Settings"),
            ]
        elif role == ROLE_PATIENT:
            menu_items = [
                ("Appointments", "📅  My Appointments"),
                ("Doctors", "👨‍⚕️  Physicians Roster"),
                ("Billing", "💳  My Invoices & Receipts"),
                ("Settings", "⚙️  My Profile"),
            ]
        else:
            menu_items = [
                ("Dashboard", "📊  Dashboard"),
                ("Patients", "👥  Patients Directory"),
                ("Doctors", "👨‍⚕️  Physicians Roster"),
                ("Appointments", "📅  Appointments"),
                ("Reports", "📈  Visual Reports"),
                ("TQM", "🛡️  TQM Quality Tools"),
                ("Settings", "⚙️  User Settings"),
            ]

        for key, label in menu_items:
            btn = ctk.CTkButton(
                self.nav_menu_container,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                height=38,
                corner_radius=8,
                fg_color="transparent",
                text_color=("#475569", "#94A3B8"),
                hover_color=("#E2E8F0", "#162544"),
                command=lambda k=key: self.show_view(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = btn

    def _build_content_area(self) -> None:
        """Create main dynamic content area and top header bar."""
        self.content_container = ctk.CTkFrame(self, corner_radius=0, fg_color=("#F1F5F9", "#0A0F1D"))
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.grid_rowconfigure(1, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Top Header Bar
        self.top_bar = ctk.CTkFrame(
            self.content_container,
            height=60,
            corner_radius=0,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
        )
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_propagate(False)

        # Title in top bar
        self.view_title_lbl = ctk.CTkLabel(
            self.top_bar,
            text="Interactive Dashboard",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#0A192F", "#F8FAFC"),
        )
        self.view_title_lbl.pack(side="left", padx=24)

        # Right actions in top bar
        right_actions = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        right_actions.pack(side="right", padx=20)

        # Shortcuts Help button (F1)
        help_btn = ctk.CTkButton(
            right_actions,
            text="⌨ Shortcuts [F1]",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#F1F5F9", "#17254A"),
            text_color=("#0A192F", "#F8FAFC"),
            hover_color=("#E2E8F0", "#223862"),
            border_width=1,
            border_color=("#CBD5E1", "#243666"),
            width=120,
            height=32,
            corner_radius=6,
            command=self.show_shortcuts_modal,
        )
        help_btn.pack(side="left", padx=(0, 10))

        # Quick Theme Toggle Button
        self.theme_quick_btn = ctk.CTkButton(
            right_actions,
            text="🌙 Theme",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=85,
            height=32,
            corner_radius=6,
            fg_color=("#F1F5F9", "#17254A"),
            text_color=("#0A192F", "#F8FAFC"),
            hover_color=("#E2E8F0", "#223862"),
            border_width=1,
            border_color=("#CBD5E1", "#243666"),
            command=self.toggle_theme,
        )
        self.theme_quick_btn.pack(side="left", padx=(0, 8))

        # In-App Notification Bell Button
        self.notif_btn = ctk.CTkButton(
            right_actions,
            text="🔔 0",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=78,
            height=32,
            corner_radius=6,
            fg_color=("#F1F5F9", "#17254A"),
            text_color=("#0A192F", "#F8FAFC"),
            hover_color=("#E2E8F0", "#223862"),
            border_width=1,
            border_color=("#CBD5E1", "#243666"),
            command=self._open_notifications,
        )
        self.notif_btn.pack(side="left", padx=(0, 8))

        # User Profile Pill (Clickable -> Settings)
        user_chip = ctk.CTkFrame(
            right_actions,
            fg_color=("#F1F5F9", "#17254A"),
            border_width=1,
            border_color=("#CBD5E1", "#243666"),
            corner_radius=16,
            cursor="hand2",
        )
        user_chip.pack(side="left")

        self.user_lbl = ctk.CTkLabel(
            user_chip,
            text=f"👤 {STUDENT_NAME} (Admin)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0A192F", "#F8FAFC"),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        self.user_lbl.pack()
        user_chip.bind("<Button-1>", lambda event: self.show_view("Settings"))
        self.user_lbl.bind("<Button-1>", lambda event: self.show_view("Settings"))

        # Sign Out / Switch User Button
        self.signout_btn = ctk.CTkButton(
            right_actions,
            text="🚪 Sign Out",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=85,
            height=32,
            corner_radius=6,
            fg_color=("#FEE2E2", "#3B1219"),
            text_color=("#DC2626", "#F87171"),
            hover_color=("#FECACA", "#4C1D24"),
            border_width=1,
            border_color=("#FCA5A5", "#5C2029"),
            command=self.logout_user,
        )
        self.signout_btn.pack(side="left", padx=(8, 0))

        # Initialize profile display from SQLite
        self.update_profile_display()

        # Dynamic View Frame holder
        self.current_view_frame: Optional[ctk.CTkFrame] = None

    def update_profile_display(self, profile: Optional[dict] = None) -> None:
        """Update top bar user badge with active session or profile."""
        current_u = get_current_user()
        if current_u:
            role_text = current_u.get("role", "Admin")
            name_text = current_u.get("full_name", STUDENT_NAME)
        else:
            role_text = "Guest"
            name_text = "Not Signed In"

        if hasattr(self, "user_lbl"):
            self.user_lbl.configure(text=f"👤 {name_text} ({role_text})")
        self.update_notification_badge()

    def update_notification_badge(self) -> None:
        """Refresh unread notifications count badge on top bar."""
        if not hasattr(self, "notif_btn"):
            return
        user = get_current_user() or {}
        uid = user.get("id")
        pid = user.get("linked_patient_id")
        unread = get_unread_notification_count(user_id=uid, patient_id=pid)
        if unread > 0:
            self.notif_btn.configure(
                text=f"🔔 {unread} New",
                fg_color=("#E0F2FE", "#0C2E4E"),
                text_color=("#0284C7", "#38BDF8"),
                border_color=("#0284C7", "#06B6D4"),
            )
        else:
            self.notif_btn.configure(
                text="🔔 0",
                fg_color=("#F1F5F9", "#17254A"),
                text_color=("#64748B", "#94A3B8"),
                border_color=("#CBD5E1", "#243666"),
            )

    def _open_notifications(self) -> None:
        """Open notification center modal."""
        user = get_current_user() or {}
        NotificationCenterModal(
            self,
            user_id=user.get("id"),
            patient_id=user.get("linked_patient_id"),
            on_update=self.update_notification_badge,
        )

    def logout_user(self) -> None:
        """Clear authenticated session and transition cleanly to fullscreen login view."""
        logout()
        self.show_login_screen()

    def show_login_screen(self) -> None:
        """Display dedicated fullscreen login view; hide sidebar and content container."""
        self.active_view_name = "Login"
        if hasattr(self, "sidebar") and self.sidebar.winfo_ismapped():
            self.sidebar.grid_remove()
        if hasattr(self, "content_container") and self.content_container.winfo_ismapped():
            self.content_container.grid_remove()

        if hasattr(self, "login_container") and self.login_container is not None:
            try:
                self.login_container.destroy()
            except Exception:
                pass

        self.login_container = ctk.CTkFrame(self, fg_color=("#F8FAFC", "#0A0F1D"))
        self.login_container.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.login_view_frame = LoginView(
            self.login_container,
            on_login_success=self.on_login_success,
        )
        self.login_view_frame.pack(fill="both", expand=True)

    def on_login_success(self, user: dict) -> None:
        """Callback when user successfully logs in from LoginView."""
        set_current_user(user)

        if hasattr(self, "login_container") and self.login_container is not None:
            try:
                self.login_container.destroy()
            except Exception:
                pass
            self.login_container = None
            self.login_view_frame = None

        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.content_container.grid(row=0, column=1, sticky="nsew")

        self._rebuild_sidebar_menu()
        self.update_profile_display()

        role = user.get("role", ROLE_ADMIN)
        if role in (ROLE_DOCTOR, ROLE_PATIENT):
            self.show_view("Appointments")
        else:
            self.show_view("Dashboard")

    def show_view(self, view_name: str, **kwargs) -> None:
        """Switch active view frame dynamically with highlight updating."""
        # Normalize common aliases
        if view_name in ("TQM Toolkit", "TQM Quality Tools"):
            view_name = "TQM"

        self.active_view_name = view_name

        # Update Navigation Button Styles with distinctive clinical accent indicator
        for name, btn in self.nav_buttons.items():
            if name == view_name:
                btn.configure(
                    fg_color=("#E0F2FE", "#0F2B48"),
                    text_color=("#0284C7", "#38BDF8"),
                    border_width=1,
                    border_color=("#0284C7", "#06B6D4"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("#475569", "#94A3B8"),
                    border_width=0,
                )

        # Remove existing view frame
        if self.current_view_frame is not None:
            self.current_view_frame.destroy()
            self.current_view_frame = None

        # Instantiate requested view
        if view_name == "Dashboard":
            self.view_title_lbl.configure(text="Executive Clinical Dashboard")
            self.current_view_frame = DashboardView(self.content_container, on_navigate=self.show_view)
        elif view_name == "Patients":
            self.view_title_lbl.configure(text="Patient Directory & Demographics")
            self.current_view_frame = PatientsView(self.content_container)
        elif view_name == "Doctors":
            self.view_title_lbl.configure(text="Physician Roster & Specializations")
            self.current_view_frame = DoctorsView(self.content_container)
        elif view_name == "Appointments":
            self.view_title_lbl.configure(text="Clinical Appointments Management")
            self.current_view_frame = AppointmentsView(self.content_container)
        elif view_name == "Reports":
            self.view_title_lbl.configure(text="Visual Reports & Quality Analytics")
            target_rep = kwargs.get("target_report")
            self.current_view_frame = ReportsView(self.content_container, target_report=target_rep)
        elif view_name == "Billing":
            self.view_title_lbl.configure(text="Consultation Billing & Receipts")
            self.current_view_frame = BillingView(self.content_container)
        elif view_name == "TQM":
            self.view_title_lbl.configure(text="TQM Quality Toolkit (BBAT104)")
            self.current_view_frame = TQMView(self.content_container)
        elif view_name == "Users":
            self.view_title_lbl.configure(text="System User Accounts & Roles")
            self.current_view_frame = UserManagementView(self.content_container)
        elif view_name == "Settings":
            self.view_title_lbl.configure(text="User Profile & Application Settings")
            self.current_view_frame = SettingsView(
                self.content_container,
                on_theme_change=self.set_theme_mode,
                on_profile_updated=self.update_profile_display,
            )
        elif view_name == "Login":
            self.show_login_screen()
            return

        if self.current_view_frame is not None:
            self.current_view_frame.grid(row=1, column=0, sticky="nsew")

    def set_theme_mode(self, mode: str) -> None:
        """Switch appearance mode in real time and refresh view."""
        ctk.set_appearance_mode(mode)
        self.theme_switch.set(mode.capitalize())
        if mode.lower() == "light":
            self.theme_quick_btn.configure(text="☀️ Theme")
        else:
            self.theme_quick_btn.configure(text="🌙 Theme")

        # Re-render current view to adapt custom child widgets (e.g., charts)
        self.show_view(self.active_view_name)

    def toggle_theme(self) -> None:
        """Toggle between Dark and Light mode instantly."""
        current = ctk.get_appearance_mode().lower()
        new_mode = "Light" if current == "dark" else "Dark"
        self.set_theme_mode(new_mode)

    def _is_text_widget_focused(self, event=None) -> bool:
        """Check if focused widget is an active text input (Entry or Text) to prevent shortcut conflicts."""
        widget = getattr(event, "widget", None) if event else self.focus_get()
        if widget is None:
            widget = self.focus_get()
        if widget is None:
            return False
        if isinstance(widget, (tk.Entry, tk.Text)):
            return True
        if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox)):
            return True
        try:
            w_class = widget.winfo_class()
            return w_class in ("Entry", "Text", "TEntry")
        except Exception:
            return False

    def _on_ctrl_a(self, event):
        """Navigate to Appointments on Ctrl+A, but allow native Select All inside text fields."""
        if self._is_text_widget_focused(event):
            return  # Let native Entry handle Select All
        self.show_view("Appointments")

    def _on_ctrl_d(self, event):
        """Navigate to Dashboard on Ctrl+D, but avoid navigating when user is typing."""
        if self._is_text_widget_focused(event):
            return
        self.show_view("Dashboard")

    def _on_ctrl_p(self, event):
        """Navigate to Patients on Ctrl+P, but avoid navigating when user is typing."""
        if self._is_text_widget_focused(event):
            return
        self.show_view("Patients")

    def _on_ctrl_t(self, event):
        """Toggle appearance theme on Ctrl+T."""
        self.toggle_theme()

    def _register_shortcuts(self) -> None:
        """Register global hotkeys for rapid workflow navigation (Q08 Feature 4)."""
        self.bind("<Control-Key-1>", lambda event: self.show_view("Dashboard"))
        self.bind("<Control-Key-2>", lambda event: self.show_view("Patients"))
        self.bind("<Control-Key-3>", lambda event: self.show_view("Doctors"))
        self.bind("<Control-Key-4>", lambda event: self.show_view("Appointments"))
        self.bind("<Control-Key-5>", lambda event: self.show_view("Reports"))
        self.bind("<Control-Key-6>", lambda event: self.show_view("TQM"))
        self.bind("<Control-Key-7>", lambda event: self.show_view("Settings"))
        self.bind("<Control-d>", self._on_ctrl_d)
        self.bind("<Control-p>", self._on_ctrl_p)
        self.bind("<Control-a>", self._on_ctrl_a)
        self.bind("<Control-t>", self._on_ctrl_t)
        self.bind("<F1>", lambda event: self.show_shortcuts_modal())

    def show_shortcuts_modal(self) -> None:
        """Display interactive cheat sheet for keyboard shortcuts with conflict guidance."""
        modal = ctk.CTkToplevel(self)
        modal.title("Keyboard Shortcuts Reference — Q08")
        modal.geometry("520x460")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        # Center modal over main window
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 460) // 2
        modal.geometry(f"+{max(0, x)}+{max(0, y)}")

        ctk.CTkLabel(
            modal,
            text="⚡ Keyboard Shortcuts Reference",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            modal,
            text="Rapid navigation hotkeys designed to minimize mouse travel during outpatient registration.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            wraplength=480,
        ).pack(pady=(0, 12))

        shortcuts_list = [
            ("Ctrl + 1  /  Ctrl + D", "Jump to Executive Clinical Dashboard"),
            ("Ctrl + 2  /  Ctrl + P", "Jump to Patient Directory & Demographics"),
            ("Ctrl + 3", "Jump to Physician Specialist Roster"),
            ("Ctrl + 4  /  Ctrl + A*", "Jump to Clinical Appointments Schedule"),
            ("Ctrl + 5", "Jump to Visual Analytics Reports"),
            ("Ctrl + 6", "Jump to TQM Quality Toolkit"),
            ("Ctrl + 7", "Jump to User Profile & System Preferences"),
            ("Ctrl + T", "Toggle Light / Dark Mode Instantly"),
            ("F1", "Open this Keyboard Shortcuts Guide"),
        ]

        list_frame = ctk.CTkFrame(modal, fg_color=("white", "#1E202E"), corner_radius=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        for keys, description in shortcuts_list:
            row = ctk.CTkFrame(list_frame, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=4)

            badge = ctk.CTkLabel(
                row,
                text=keys,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("#E2E8F0", "#334155"),
                text_color=("#0284C7", "#38BDF8"),
                corner_radius=6,
                width=165,
                height=24,
            )
            badge.pack(side="left")

            desc = ctk.CTkLabel(
                row,
                text=description,
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                anchor="w",
            )
            desc.pack(side="left", padx=10)

        # Footnote explaining text conflict protection
        ctk.CTkLabel(
            modal,
            text="* Note: When typing inside text fields, Ctrl+A performs native 'Select All' without navigating away.",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color=("#10B981", "#34D399"),
        ).pack(pady=(0, 8))

        ctk.CTkButton(
            modal,
            text="Close Guide (Esc)",
            width=120,
            command=modal.destroy,
        ).pack(pady=(0, 14))
        modal.bind("<Escape>", lambda event: modal.destroy())



def main():
    """Application entry point."""
    seed_database()  # Ensure SQLite database is present and seeded
    logout()  # Guarantee fresh launch starts in dedicated unauthenticated login view
    app = HospitalApp(start_login=True)
    app.deiconify()
    app.lift()
    app.focus_force()
    print(f"[Hospital TQM] GUI window launched successfully: {app.geometry()}")
    print("[Hospital TQM] Window is active on your screen. (Close the window or press Ctrl+C to exit)")
    app.mainloop()


if __name__ == "__main__":
    main()
