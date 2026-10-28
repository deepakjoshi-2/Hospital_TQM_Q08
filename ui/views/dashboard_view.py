"""Interactive Dashboard View for Hospital Management System — Q08."""
import datetime
from typing import Callable, Optional
import customtkinter as ctk

from database.connection import get_db_connection
from ui.components.kpi_card import KPICard


class DashboardView(ctk.CTkFrame):
    """Interactive KPI Dashboard with real-time statistics, today's schedule, and TQM highlights."""

    def __init__(self, master, on_navigate: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_navigate = on_navigate

        # Load live database metrics
        self.metrics = self._fetch_live_metrics()

        # Build UI layout
        self._build_header()
        self._build_kpi_row()
        self._build_main_sections()

    def _fetch_live_metrics(self) -> dict:
        """Query SQLite database for live dashboard statistics based on current system date."""
        today_str = datetime.date.today().isoformat()
        data = {
            "total_patients": "0",
            "active_doctors": "0",
            "today_appointments": "0",
            "csat_score": "5.0 / 5.0",
            "csat_percentage": "100%",
            "recent_appointments": [],
            "today_date": today_str,
        }
        try:
            with get_db_connection() as conn:
                # 1. Total Patients
                row = conn.execute("SELECT COUNT(*) as c FROM patients;").fetchone()
                if row:
                    data["total_patients"] = str(row["c"])

                # 2. Available / Active Doctors
                row = conn.execute("SELECT COUNT(*) as c FROM doctors WHERE status != 'On Leave';").fetchone()
                if row:
                    data["active_doctors"] = f"{row['c']} Available"

                # 3. Today's Appointments (using dynamic current system date)
                row = conn.execute(
                    "SELECT COUNT(*) as c FROM appointments WHERE appointment_date = ?;",
                    (today_str,),
                ).fetchone()
                if row:
                    data["today_appointments"] = str(row["c"])

                # 4. Average CSAT Rating
                row = conn.execute(
                    "SELECT AVG(satisfaction_rating) as avg_rating, COUNT(satisfaction_rating) as total_rated "
                    "FROM appointments WHERE satisfaction_rating IS NOT NULL;"
                ).fetchone()
                if row and row["avg_rating"]:
                    avg_val = round(row["avg_rating"], 2)
                    percentage = int((avg_val / 5.0) * 100)
                    data["csat_score"] = f"{avg_val} / 5.0"
                    data["csat_percentage"] = f"{percentage}% Satisfaction ({row['total_rated']} reviews)"

                # 5. Today's appointments list
                cursor = conn.execute(
                    """
                    SELECT a.id,
                           a.appointment_code, 
                           a.patient_id,
                           a.doctor_id,
                           p.first_name || ' ' || p.last_name AS patient_name,
                           d.first_name || ' ' || d.last_name AS doctor_name,
                           d.specialization,
                           a.time_slot,
                           a.priority,
                           a.status
                    FROM appointments a
                    JOIN patients p ON a.patient_id = p.id
                    JOIN doctors d ON a.doctor_id = d.id
                    WHERE a.appointment_date = ?
                    ORDER BY a.time_slot ASC
                    LIMIT 8;
                    """,
                    (today_str,),
                )
                data["recent_appointments"] = cursor.fetchall()
        except Exception as e:
            print(f"Notice: Dashboard query fallback ({e})")
        return data

    def _build_header(self) -> None:
        """Top section with greeting, quick info, and quick-action buttons."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(20, 14))

        left_info = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_info.pack(side="left")

        # Top line: Title + Status Pill
        title_row = ctk.CTkFrame(left_info, fg_color="transparent")
        title_row.pack(anchor="w")

        title = ctk.CTkLabel(
            title_row,
            text="Executive Clinical Dashboard",
            font=ctk.CTkFont(size=23, weight="bold"),
            text_color=("#0A192F", "#F8FAFC"),
        )
        title.pack(side="left")

        live_pill = ctk.CTkLabel(
            title_row,
            text="● Live System",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#DCFCE7", "#064E3B"),
            text_color=("#15803D", "#34D399"),
            corner_radius=10,
            padx=8,
            height=20,
        )
        live_pill.pack(side="left", padx=(10, 0))

        subtitle = ctk.CTkLabel(
            left_info,
            text="Real-time patient throughput, physician roster, and TQM satisfaction indicators.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        subtitle.pack(anchor="w", pady=(3, 0))

        # Quick Action buttons on right
        btn_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_box.pack(side="right")

        new_appt_btn = ctk.CTkButton(
            btn_box,
            text="+ Book Appointment",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=36,
            corner_radius=8,
            command=self._open_book_appointment_modal,
        )
        new_appt_btn.pack(side="right", padx=(8, 0))

        new_pat_btn = ctk.CTkButton(
            btn_box,
            text="+ Register Patient",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#E2E8F0", "#1E2D4A"),
            text_color=("#0A192F", "#F8FAFC"),
            hover_color=("#CBD5E1", "#2B3D66"),
            height=36,
            corner_radius=8,
            command=lambda: self._trigger_nav("Patients"),
        )
        new_pat_btn.pack(side="right")

    def _build_kpi_row(self) -> None:
        """Grid of 4 interactive, clickable KPI metric cards with hover feedback."""
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=24, pady=(0, 16))
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")
        kpi_frame.grid_rowconfigure(0, weight=1)

        # 1. Total Patients -> Opens Patients Section
        c1 = KPICard(
            kpi_frame,
            title="Total Registered Patients",
            value=self.metrics["total_patients"],
            subtitle="Active clinical records in database",
            icon="👥",
            accent_color="#06B6D4",
            command=lambda: self._trigger_nav("Patients"),
            action_hint="View Patients →",
            badge_tint=("#E0F2FE", "#082F49"),
        )
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        # 2. Available Doctors -> Opens Doctors Section
        c2 = KPICard(
            kpi_frame,
            title="Available Medical Staff",
            value=self.metrics["active_doctors"],
            subtitle="Specialists ready for consultation",
            icon="👨‍⚕️",
            accent_color="#10B981",
            command=lambda: self._trigger_nav("Doctors"),
            action_hint="View Doctors →",
            badge_tint=("#DCFCE7", "#064E3B"),
        )
        c2.grid(row=0, column=1, padx=8, sticky="nsew")

        # 3. Today's Appointments -> Opens Appointments Section (Full Roster)
        c3 = KPICard(
            kpi_frame,
            title="Today's Appointments",
            value=self.metrics["today_appointments"],
            subtitle=f"Date: {self.metrics.get('today_date', '')}",
            icon="📅",
            accent_color="#F59E0B",
            command=lambda: self._trigger_nav("Appointments"),
            action_hint="Manage Schedule →",
            badge_tint=("#FEF3C7", "#451A03"),
        )
        c3.grid(row=0, column=2, padx=8, sticky="nsew")

        # 4. CSAT Satisfaction -> Opens Visual Reports (CSAT Focused)
        c4 = KPICard(
            kpi_frame,
            title="User Satisfaction (CSAT)",
            value=self.metrics["csat_score"],
            subtitle=self.metrics["csat_percentage"],
            icon="⭐",
            accent_color="#8B5CF6",
            command=lambda: self._trigger_nav("Reports", target_report="csat"),
            action_hint="View CSAT Report →",
            badge_tint=("#F3E8FF", "#2E1065"),
        )
        c4.grid(row=0, column=3, padx=(8, 0), sticky="nsew")

    def _build_main_sections(self) -> None:
        """Bottom split section: Today's schedule table on left, TQM highlights on right."""
        split_frame = ctk.CTkFrame(self, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        split_frame.grid_columnconfigure(0, weight=3)
        split_frame.grid_columnconfigure(1, weight=2)
        split_frame.grid_rowconfigure(0, weight=1)

        # Left Card: Today's Schedule Table
        table_card = ctk.CTkFrame(
            split_frame,
            corner_radius=12,
            fg_color=("#FFFFFF", "#131E36"),
            border_width=1,
            border_color=("#CBD5E1", "#223456"),
        )
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tbl_header = ctk.CTkFrame(table_card, fg_color="transparent")
        tbl_header.pack(fill="x", padx=18, pady=(16, 10))

        today_label_date = self.metrics.get("today_date", "")
        tbl_title = ctk.CTkLabel(
            tbl_header,
            text=f"Today's Outpatient Schedule ({today_label_date})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0A192F", "#F8FAFC"),
        )
        tbl_title.pack(side="left")

        view_all_btn = ctk.CTkButton(
            tbl_header,
            text="View Full Roster →",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            text_color=("#0284C7", "#06B6D4"),
            hover_color=("#F1F5F9", "#1A2847"),
            width=130,
            height=28,
            command=lambda: self._trigger_nav("Appointments"),
        )
        view_all_btn.pack(side="right")

        # Table Column Headers
        col_frame = ctk.CTkFrame(table_card, fg_color=("#F1F5F9", "#0E172B"), height=34, corner_radius=6)
        col_frame.pack(fill="x", padx=16, pady=(0, 6))

        headers = [("Code", 80), ("Patient", 140), ("Doctor & Speciality", 180), ("Slot", 90), ("Status", 90)]
        for h_text, width in headers:
            lbl = ctk.CTkLabel(
                col_frame,
                text=h_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                width=width,
                anchor="w",
            )
            lbl.pack(side="left", padx=8, pady=4)

        # Scrollable rows list
        rows_container = ctk.CTkScrollableFrame(table_card, fg_color="transparent")
        rows_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        appts = self.metrics["recent_appointments"]
        if not appts:
            empty_card = ctk.CTkFrame(
                rows_container,
                corner_radius=10,
                fg_color=("#F8FAFC", "#0E172B"),
                border_width=1,
                border_color=("#E2E8F0", "#1E2D4A"),
            )
            empty_card.pack(fill="both", expand=True, padx=12, pady=20)

            # Calendar visual icon badge
            cal_icon = ctk.CTkLabel(
                empty_card,
                text="📅",
                font=ctk.CTkFont(size=36),
                text_color=("#0284C7", "#06B6D4"),
            )
            cal_icon.pack(pady=(22, 6))

            # Main Heading
            heading = ctk.CTkLabel(
                empty_card,
                text="No appointments scheduled for today",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=("#0A192F", "#F8FAFC"),
            )
            heading.pack(pady=(0, 4))

            # Helpful dynamic explanation
            sub_msg = ctk.CTkLabel(
                empty_card,
                text=(
                    f"There are currently no outpatient consultations booked for {today_label_date}.\n"
                    "When patient appointments are scheduled for today, they will automatically appear here."
                ),
                font=ctk.CTkFont(size=12),
                text_color=("#64748B", "#94A3B8"),
                justify="center",
            )
            sub_msg.pack(pady=(0, 16))

            # Action Buttons Row
            act_box = ctk.CTkFrame(empty_card, fg_color="transparent")
            act_box.pack(pady=(0, 22))

            book_btn = ctk.CTkButton(
                act_box,
                text="＋ Book Appointment",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#0284C7",
                hover_color="#0369A1",
                height=34,
                corner_radius=8,
                command=self._open_book_appointment_modal,
            )
            book_btn.pack(side="left", padx=6)

            roster_btn = ctk.CTkButton(
                act_box,
                text="View Full Roster →",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=("#E2E8F0", "#1E2D4A"),
                text_color=("#0A192F", "#F8FAFC"),
                hover_color=("#CBD5E1", "#2B3D66"),
                height=34,
                corner_radius=8,
                command=lambda: self._trigger_nav("Appointments"),
            )
            roster_btn.pack(side="left", padx=6)
        else:
            for item in appts:
                self._render_table_row(rows_container, item)

        # Right Card: TQM Methodology & Coursework Highlights
        self.tqm_card = ctk.CTkFrame(
            split_frame,
            corner_radius=12,
            fg_color=("#FFFFFF", "#131E36"),
            border_width=1,
            border_color=("#CBD5E1", "#223456"),
        )
        self.tqm_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tqm_header = ctk.CTkFrame(self.tqm_card, fg_color="transparent")
        tqm_header.pack(fill="x", padx=16, pady=(14, 10))

        tqm_title = ctk.CTkLabel(
            tqm_header,
            text="🛡️ TQM Quality Focus (Q08)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#0A192F", "#F8FAFC"),
        )
        tqm_title.pack(side="left")

        # Academic project metadata pill
        badge = ctk.CTkLabel(
            tqm_header,
            text="BBAT104",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E0F2FE", "#082F49"),
            text_color=("#0284C7", "#38BDF8"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        # Scrollable container for TQM highlights and student metadata
        self.tqm_scroll = ctk.CTkScrollableFrame(self.tqm_card, fg_color="transparent")
        self.tqm_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        # Highlights content with a stylized goal card
        goal_box = ctk.CTkFrame(
            self.tqm_scroll,
            fg_color=("#F0F9FF", "#0A2540"),
            border_width=1,
            border_color=("#BAE6FD", "#075985"),
            corner_radius=8,
        )
        goal_box.pack(fill="x", padx=4, pady=(0, 6))

        self.goal_title = ctk.CTkLabel(
            goal_box,
            text="🎯 Q08 Continuous Improvement Goal",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="w",
            wraplength=170,
            justify="left",
        )
        self.goal_title.pack(fill="x", padx=10, pady=(6, 2))

        self.goal_desc = ctk.CTkLabel(
            goal_box,
            text="Maximize User Satisfaction by eliminating registration bottlenecks, interface lag, and booking friction.",
            font=ctk.CTkFont(size=11),
            text_color=("#334E68", "#94A3B8"),
            wraplength=170,
            justify="left",
        )
        self.goal_desc.pack(fill="x", padx=10, pady=(0, 6))

        # TQM Checklist items
        highlights = [
            ("🛡️ Double-Booking Shield", "Database partial index prevents slot collision (0.0%)"),
            ("⚡ Fast Keyboard Shortcuts", "Instant access via Ctrl+1..7, Ctrl+T, F1"),
            ("🌓 Theme Fatigue Reduction", "Instant Light / Dark high-contrast switcher"),
            ("📊 Pareto 80/20 Defect Log", "Integrated Voice-of-Customer defect analysis"),
            ("⭐ CSAT Feedback Loop", "Ratings captured upon appointment completion"),
        ]

        self.tqm_title_labels = []
        self.tqm_desc_labels = []
        for title_text, detail in highlights:
            item_box = ctk.CTkFrame(
                self.tqm_scroll,
                fg_color=("#F8FAFC", "#0E172B"),
                border_width=1,
                border_color=("#E2E8F0", "#1C2B48"),
                corner_radius=8,
            )
            item_box.pack(fill="x", padx=4, pady=2)

            t_lbl = ctk.CTkLabel(
                item_box,
                text=title_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0A192F", "#F8FAFC"),
                anchor="w",
                wraplength=170,
                justify="left",
            )
            t_lbl.pack(fill="x", padx=10, pady=(5, 1))
            self.tqm_title_labels.append(t_lbl)

            d_lbl = ctk.CTkLabel(
                item_box,
                text=detail,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                anchor="w",
                wraplength=170,
                justify="left",
            )
            d_lbl.pack(fill="x", padx=10, pady=(0, 5))
            self.tqm_desc_labels.append(d_lbl)

        # Bottom Student Info
        student_frame = ctk.CTkFrame(self.tqm_scroll, fg_color="transparent")
        student_frame.pack(fill="x", padx=4, pady=(8, 4))

        self.st_lbl = ctk.CTkLabel(
            student_frame,
            text="Developer: Deepak Joshi | Roll: 2410302011 | Section B",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="center",
            wraplength=170,
            justify="center",
        )
        self.st_lbl.pack(fill="x")

        # Responsive card and canvas resize listeners for dynamic text wrapping
        self._tqm_after_ids = []
        self.tqm_card.bind("<Configure>", self._recalculate_tqm_wrapping, add="+")
        if hasattr(self.tqm_scroll, "_parent_canvas"):
            self.tqm_scroll._parent_canvas.bind("<Configure>", self._recalculate_tqm_wrapping, add="+")
        self._schedule_tqm_wrap(50)
        self._schedule_tqm_wrap(200)

    def _schedule_tqm_wrap(self, ms: int = 50) -> None:
        """Safely schedule a wrap recalculation with cancellation tracking."""
        try:
            if not self.winfo_exists():
                return
            if not hasattr(self, "_tqm_after_ids"):
                self._tqm_after_ids = []
            aid = self.after(ms, self._recalculate_tqm_wrapping)
            self._tqm_after_ids.append(aid)
        except Exception:
            pass

    def _recalculate_tqm_wrapping(self, event=None) -> None:
        """Dynamically compute exact text wraplength from the scrollable canvas width."""
        try:
            if not hasattr(self, "tqm_scroll") or not self.winfo_exists() or not self.tqm_scroll.winfo_exists():
                return
            canvas = self.tqm_scroll._parent_canvas
            canvas_w = canvas.winfo_width()
            scaling = self._get_widget_scaling() if hasattr(self, "_get_widget_scaling") else 1.0

            # If canvas not mapped yet, derive from tqm_card width or schedule check
            if canvas_w <= 10:
                card_w = self.tqm_card.winfo_width()
                if card_w > 50:
                    canvas_w = max(100, card_w - 44)
                else:
                    self._schedule_tqm_wrap(50)
                    return

            # Canvas width minus item_box padding (8px) minus label padding (20px) minus safety clearance (6px) = 34px
            usable_physical = max(120, canvas_w - 34)
            usable_logical = max(80, int(usable_physical / scaling))

            # Apply exact wraplength across all labels in the TQM panel
            if hasattr(self, "goal_desc") and self.goal_desc.winfo_exists():
                if abs(self.goal_desc.cget("wraplength") - usable_logical) > 3:
                    self.goal_desc.configure(wraplength=usable_logical)
            if hasattr(self, "goal_title") and self.goal_title.winfo_exists():
                if abs(self.goal_title.cget("wraplength") - usable_logical) > 3:
                    self.goal_title.configure(wraplength=usable_logical)
            if hasattr(self, "tqm_title_labels"):
                for lbl in self.tqm_title_labels:
                    if lbl.winfo_exists() and abs(lbl.cget("wraplength") - usable_logical) > 3:
                        lbl.configure(wraplength=usable_logical)
            if hasattr(self, "tqm_desc_labels"):
                for lbl in self.tqm_desc_labels:
                    if lbl.winfo_exists() and abs(lbl.cget("wraplength") - usable_logical) > 3:
                        lbl.configure(wraplength=usable_logical)
            if hasattr(self, "st_lbl") and self.st_lbl.winfo_exists():
                if abs(self.st_lbl.cget("wraplength") - usable_logical) > 3:
                    self.st_lbl.configure(wraplength=usable_logical)
        except Exception:
            pass

    def _render_table_row(self, container, item) -> None:
        """Render individual appointment table row with styled chips."""
        row_frame = ctk.CTkFrame(container, fg_color="transparent", height=38)
        row_frame.pack(fill="x", pady=2)

        # Appointment Code
        code_lbl = ctk.CTkLabel(
            row_frame,
            text=item["appointment_code"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            width=80,
            anchor="w",
        )
        code_lbl.pack(side="left", padx=8)

        # Patient Name
        pat_lbl = ctk.CTkLabel(
            row_frame,
            text=item["patient_name"],
            font=ctk.CTkFont(size=12),
            text_color=("#0F172A", "#F8FAFC"),
            width=140,
            anchor="w",
        )
        pat_lbl.pack(side="left", padx=8)

        # Doctor & Spec
        doc_text = f"{item['doctor_name']} ({item['specialization']})"
        doc_lbl = ctk.CTkLabel(
            row_frame,
            text=doc_text[:24] + "..." if len(doc_text) > 24 else doc_text,
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            width=180,
            anchor="w",
        )
        doc_lbl.pack(side="left", padx=8)

        # Time Slot
        time_lbl = ctk.CTkLabel(
            row_frame,
            text=item["time_slot"],
            font=ctk.CTkFont(size=11),
            text_color=("#0F172A", "#F8FAFC"),
            width=90,
            anchor="w",
        )
        time_lbl.pack(side="left", padx=8)

        # Status badge chip
        status = item["status"]
        if status == "Completed":
            chip_bg = ("#DCFCE7", "#14532D")
            chip_fg = ("#15803D", "#4ADE80")
        elif status == "Scheduled":
            chip_bg = ("#FEF3C7", "#78350F")
            chip_fg = ("#B45309", "#FCD34D")
        else:
            chip_bg = ("#FEE2E2", "#7F1D1D")
            chip_fg = ("#B91C1C", "#F87171")

        chip = ctk.CTkLabel(
            row_frame,
            text=status,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=chip_bg,
            text_color=chip_fg,
            corner_radius=6,
            width=80,
            height=22,
        )
        chip.pack(side="left", padx=8)

    def _trigger_nav(self, view_name: str, **kwargs) -> None:
        """Call navigation handler if supplied with optional target arguments."""
        if self.on_navigate and callable(self.on_navigate):
            try:
                self.on_navigate(view_name, **kwargs)
            except TypeError:
                self.on_navigate(view_name)

    def _open_book_appointment_modal(self) -> None:
        """Open the real appointment booking modal and refresh dashboard on success."""
        from ui.components.appointment_modals import AppointmentFormModal

        AppointmentFormModal(
            self.winfo_toplevel(),
            appointment_data=None,
            on_success=self._on_appointment_booked,
        )

    def _on_appointment_booked(self, msg: str = "") -> None:
        """Callback after appointment is booked: reload live database metrics and re-render."""
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        """Fetch fresh live metrics from SQLite and rebuild dashboard components."""
        self.metrics = self._fetch_live_metrics()
        for w in self.winfo_children():
            w.destroy()
        self._build_header()
        self._build_kpi_row()
        self._build_main_sections()

    def destroy(self) -> None:
        """Cancel any pending scheduled callbacks and unbind listeners cleanly."""
        if hasattr(self, "_tqm_after_ids"):
            for aid in self._tqm_after_ids:
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
            self._tqm_after_ids.clear()
        super().destroy()
