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
                    SELECT a.appointment_code, 
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

        title = ctk.CTkLabel(
            left_info,
            text="Executive Clinical Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            left_info,
            text="Real-time patient throughput, medical roster, and TQM satisfaction indicators.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        subtitle.pack(anchor="w", pady=(2, 0))

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
            command=lambda: self._trigger_nav("Appointments"),
        )
        new_appt_btn.pack(side="right", padx=(8, 0))

        new_pat_btn = ctk.CTkButton(
            btn_box,
            text="+ Register Patient",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            height=36,
            corner_radius=8,
            command=lambda: self._trigger_nav("Patients"),
        )
        new_pat_btn.pack(side="right")

    def _build_kpi_row(self) -> None:
        """Grid of 4 interactive KPI metric cards."""
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", padx=24, pady=(0, 16))
        kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        # 1. Total Patients
        c1 = KPICard(
            kpi_frame,
            title="Total Registered Patients",
            value=self.metrics["total_patients"],
            subtitle="Active clinical records in database",
            icon="👥",
            accent_color="#38BDF8",
        )
        c1.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        # 2. Available Doctors
        c2 = KPICard(
            kpi_frame,
            title="Available Medical Staff",
            value=self.metrics["active_doctors"],
            subtitle="Specialists ready for consultation",
            icon="👨‍⚕️",
            accent_color="#22C55E",
        )
        c2.grid(row=0, column=1, padx=8, sticky="ew")

        # 3. Today's Appointments
        c3 = KPICard(
            kpi_frame,
            title="Today's Appointments",
            value=self.metrics["today_appointments"],
            subtitle=f"Date: {self.metrics.get('today_date', '')}",
            icon="📅",
            accent_color="#F59E0B",
        )
        c3.grid(row=0, column=2, padx=8, sticky="ew")

        # 4. CSAT Satisfaction
        c4 = KPICard(
            kpi_frame,
            title="User Satisfaction (CSAT)",
            value=self.metrics["csat_score"],
            subtitle=self.metrics["csat_percentage"],
            icon="⭐",
            accent_color="#A855F7",
        )
        c4.grid(row=0, column=3, padx=(8, 0), sticky="ew")

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
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tbl_header = ctk.CTkFrame(table_card, fg_color="transparent")
        tbl_header.pack(fill="x", padx=18, pady=(16, 10))

        today_label_date = self.metrics.get("today_date", "")
        tbl_title = ctk.CTkLabel(
            tbl_header,
            text=f"Today's Outpatient Schedule ({today_label_date})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        tbl_title.pack(side="left")

        view_all_btn = ctk.CTkButton(
            tbl_header,
            text="View Full Roster →",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color="#38BDF8",
            hover_color=("#F1F5F9", "#26293B"),
            width=120,
            height=28,
            command=lambda: self._trigger_nav("Appointments"),
        )
        view_all_btn.pack(side="right")

        # Table Column Headers
        col_frame = ctk.CTkFrame(table_card, fg_color=("#F8FAFC", "#26293B"), height=34, corner_radius=6)
        col_frame.pack(fill="x", padx=16, pady=(0, 6))

        headers = [("Code", 80), ("Patient", 140), ("Doctor & Speciality", 180), ("Slot", 90), ("Status", 90)]
        for h_text, width in headers:
            lbl = ctk.CTkLabel(
                col_frame,
                text=h_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#64748B", "#94A3B8"),
                width=width,
                anchor="w",
            )
            lbl.pack(side="left", padx=8, pady=4)

        # Scrollable rows list
        rows_container = ctk.CTkScrollableFrame(table_card, fg_color="transparent")
        rows_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        appts = self.metrics["recent_appointments"]
        if not appts:
            empty_lbl = ctk.CTkLabel(
                rows_container,
                text=f"No outpatient appointments scheduled for today ({today_label_date}).",
                font=ctk.CTkFont(size=13),
                text_color=("#64748B", "#94A3B8"),
            )
            empty_lbl.pack(pady=30)
        else:
            for item in appts:
                self._render_table_row(rows_container, item)

        # Right Card: TQM Methodology & Coursework Highlights
        tqm_card = ctk.CTkFrame(
            split_frame,
            corner_radius=12,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        tqm_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tqm_header = ctk.CTkFrame(tqm_card, fg_color="transparent")
        tqm_header.pack(fill="x", padx=18, pady=(16, 12))

        tqm_title = ctk.CTkLabel(
            tqm_header,
            text="TQM Quality Focus (Q08)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        tqm_title.pack(side="left")

        # Academic project metadata pill
        badge = ctk.CTkLabel(
            tqm_header,
            text="BBAT104",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E0F2FE", "#0C4A6E"),
            text_color=("#0369A1", "#38BDF8"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        badge.pack(side="right")

        # Scrollable container for TQM highlights and student metadata
        self.tqm_scroll = ctk.CTkScrollableFrame(tqm_card, fg_color="transparent")
        self.tqm_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Highlights content
        desc = ctk.CTkLabel(
            self.tqm_scroll,
            text="Goal: Maximize User Satisfaction by eliminating registration bottlenecks, interface lag, and booking friction.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
            wraplength=320,
            justify="left",
        )
        desc.pack(fill="x", padx=6, pady=(0, 10))

        # TQM Checklist items
        highlights = [
            ("🛡️ Double-Booking Shield", "Database partial index prevents slot collision"),
            ("⚡ Fast Keyboard Shortcuts", "Instant access via Ctrl+1..6, Ctrl+N, F1"),
            ("🌓 Theme Fatigue Reduction", "Instant Light / Dark high-contrast switcher"),
            ("📊 Pareto 80/20 Defect Log", "Integrated Voice-of-Customer analysis"),
            ("⭐ CSAT Feedback Loop", "Ratings captured upon appointment completion"),
        ]

        for title, detail in highlights:
            item_box = ctk.CTkFrame(self.tqm_scroll, fg_color=("#F8FAFC", "#26293B"), corner_radius=8)
            item_box.pack(fill="x", padx=6, pady=4)

            t_lbl = ctk.CTkLabel(
                item_box,
                text=title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0F172A", "#F8FAFC"),
                anchor="w",
            )
            t_lbl.pack(fill="x", padx=10, pady=(6, 1))

            d_lbl = ctk.CTkLabel(
                item_box,
                text=detail,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                anchor="w",
            )
            d_lbl.pack(fill="x", padx=10, pady=(0, 6))

        # Bottom Student Info
        student_frame = ctk.CTkFrame(self.tqm_scroll, fg_color="transparent")
        student_frame.pack(fill="x", padx=6, pady=(12, 4))

        st_lbl = ctk.CTkLabel(
            student_frame,
            text="Developer: Deepak Joshi | CSE Section B",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="center",
        )
        st_lbl.pack(fill="x")

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

    def _trigger_nav(self, view_name: str) -> None:
        """Call navigation handler if supplied."""
        if self.on_navigate:
            self.on_navigate(view_name)
