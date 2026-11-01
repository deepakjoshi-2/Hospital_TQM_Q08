"""Live Token Queue Tracker Modal and Component for MedCare HMS (Q08).

Provides real-time visibility into OPD consultation queues:
- Sequential token number tracking (TK-01, TK-02, etc.).
- Real-time queue status: Waiting, Now Serving, Completed, Cancelled, No-Show.
- Active doctor queue overview with queue position and estimated wait times.
- Real-time doctor controls: '▶ Start Consultation' and '✓ Complete Consultation'.
- Safe 10-second auto-refresh polling with memory-leak-safe timer cleanup.
"""
from datetime import date, datetime
import tkinter as tk
from typing import Callable, Optional
import customtkinter as ctk

from database.connection import get_db_connection
from services.auth_service import get_current_user
from services.token_service import (
    format_doctor_name,
    get_doctor_live_queue,
    get_patient_active_tokens,
    start_consultation,
    complete_consultation,
)


class LiveQueueTrackerModal(ctk.CTkToplevel):
    """Real-time OPD Token Queue Tracker Modal with auto-refresh."""

    def __init__(
        self,
        master,
        doctor_id: Optional[int] = None,
        appointment_id: Optional[int] = None,
        appointment_date: Optional[str] = None,
        on_update: Optional[Callable] = None,
    ):
        super().__init__(master)
        self.on_update = on_update
        self.selected_doctor_id: Optional[int] = doctor_id
        self.selected_date: Optional[str] = appointment_date
        self.highlight_appointment_id: Optional[int] = appointment_id
        self._refresh_timer: Optional[str] = None
        self._is_destroyed = False
        self.doc_options_map: dict = {}

        self.title("Live Outpatient Token Queue Tracker — MedCare HMS")
        self.geometry("780x620")
        self.minsize(720, 560)
        self.transient(master)
        self.grab_set()

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        self.bg_color = "#070D1E" if is_dark else "#F0F6FC"
        self.card_color = "#0F1E3D" if is_dark else "#FFFFFF"
        self.border_color = "#1E3258" if is_dark else "#CBD5E1"
        self.text_primary = "#FFFFFF" if is_dark else "#0A192F"
        self.text_muted = "#94A3B8" if is_dark else "#627D98"

        self.configure(fg_color=self.bg_color)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Resolve appointment context if appointment_id was provided
        if appointment_id:
            try:
                with get_db_connection() as conn:
                    row = conn.execute(
                        "SELECT doctor_id, appointment_date FROM appointments WHERE id = ?;",
                        (appointment_id,),
                    ).fetchone()
                    if row:
                        if not self.selected_doctor_id:
                            self.selected_doctor_id = row["doctor_id"]
                        if not self.selected_date:
                            self.selected_date = row["appointment_date"]
            except Exception as e:
                print(f"Notice: Failed to resolve appointment context: {e}")

        # Pre-select doctor if logged in as Doctor or passed as argument
        user = get_current_user() or {}
        if self.selected_doctor_id is None and user.get("role") == "Doctor" and user.get("linked_doctor_id"):
            self.selected_doctor_id = user["linked_doctor_id"]

        self._build_ui()
        self._load_queue_data()
        self._schedule_auto_refresh()

    def _build_ui(self) -> None:
        """Construct tracker modal layout."""
        # Top Header Bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 10))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="🎫 Live Outpatient Queue & Token Tracker",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Real-time OPD queue progression, estimated consultation wait times & live token updates.",
            font=ctk.CTkFont(size=11),
            text_color=self.text_muted,
        ).pack(anchor="w", pady=(2, 0))

        # Doctor selector, Date selector & refresh trigger on right
        controls_box = ctk.CTkFrame(header, fg_color="transparent")
        controls_box.pack(side="right")

        self.doctors_list = self._fetch_doctors_list()
        self.doc_options_map = {}
        doc_options = []
        for d in self.doctors_list:
            label = f"{d['name']} ({d['specialization']})"
            self.doc_options_map[label] = d["id"]
            doc_options.append(label)

        if not doc_options:
            doc_options = ["No doctors available"]

        self.doc_selector = ctk.CTkOptionMenu(
            controls_box,
            values=doc_options,
            command=self._on_doctor_selected,
            width=210,
            height=32,
            corner_radius=6,
        )
        self.doc_selector.pack(side="left", padx=(0, 6))

        # Date selector dropdown
        self.date_selector = ctk.CTkOptionMenu(
            controls_box,
            values=[date.today().isoformat()],
            command=self._on_date_selected,
            width=125,
            height=32,
            corner_radius=6,
        )
        self.date_selector.pack(side="left", padx=(0, 6))

        # Set initial doctor selection
        selected_label = None
        if self.selected_doctor_id:
            for opt, did in self.doc_options_map.items():
                if did == self.selected_doctor_id:
                    selected_label = opt
                    break
        elif self.doctors_list:
            self.selected_doctor_id = self.doctors_list[0]["id"]
            selected_label = doc_options[0]

        if selected_label:
            self.doc_selector.set(selected_label)

        self._update_date_options()

        refresh_btn = ctk.CTkButton(
            controls_box,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=75,
            height=32,
            corner_radius=6,
            command=self._load_queue_data,
        )
        refresh_btn.pack(side="left")

        # Live Status Summary Strip
        self.summary_frame = ctk.CTkFrame(
            self,
            fg_color=self.card_color,
            border_width=1,
            border_color=self.border_color,
            corner_radius=10,
        )
        self.summary_frame.pack(fill="x", padx=20, pady=(0, 12))
        self.summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._build_summary_cards()

        # Queue Table Container
        self.table_card = ctk.CTkFrame(
            self,
            fg_color=self.card_color,
            border_width=1,
            border_color=self.border_color,
            corner_radius=10,
        )
        self.table_card.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Table Column Header
        col_hdr = ctk.CTkFrame(self.table_card, fg_color=("#F1F5F9", "#0B152B"), height=34, corner_radius=6)
        col_hdr.pack(fill="x", padx=12, pady=(10, 6))

        cols = [
            ("Token #", 80),
            ("Code", 85),
            ("Patient Name", 150),
            ("Slot", 80),
            ("Queue Status", 110),
            ("Est. Wait", 85),
            ("Actions", 110),
        ]
        for name, width in cols:
            ctk.CTkLabel(
                col_hdr,
                text=name,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=self.text_muted,
                width=width,
                anchor="w",
            ).pack(side="left", padx=5)

        # Scrollable rows frame
        self.rows_frame = ctk.CTkScrollableFrame(self.table_card, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _build_summary_cards(self) -> None:
        """Create 4 KPI metric indicators in the summary frame."""
        for child in self.summary_frame.winfo_children():
            child.destroy()

        cards = [
            ("NOW SERVING", "—", "#10B981"),
            ("PATIENTS WAITING", "0", "#06B6D4"),
            ("COMPLETED TODAY", "0", "#3B82F6"),
            ("AVG WAIT TIME", "—", "#F59E0B"),
        ]
        self.kpi_labels = {}
        for col, (title, val, accent) in enumerate(cards):
            card_box = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
            card_box.grid(row=0, column=col, padx=8, pady=10, sticky="nsew")

            ctk.CTkLabel(
                card_box,
                text=title,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=self.text_muted,
                anchor="center",
            ).pack()

            v_lbl = ctk.CTkLabel(
                card_box,
                text=val,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=accent,
                anchor="center",
            )
            v_lbl.pack(pady=(2, 0))
            self.kpi_labels[title] = v_lbl

    def _fetch_doctors_list(self) -> list:
        """Fetch list of active doctors for selector with standardized naming."""
        docs = []
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    "SELECT id, first_name, last_name, specialization FROM doctors ORDER BY id ASC;"
                )
                for r in cursor.fetchall():
                    docs.append({
                        "id": r["id"],
                        "name": format_doctor_name(r["first_name"], r["last_name"]),
                        "specialization": r["specialization"],
                    })
        except Exception as e:
            print(f"Error fetching doctors: {e}")
        return docs

    def _fetch_doctor_dates(self, doctor_id: int) -> list:
        """Fetch distinct appointment dates for selected doctor."""
        dates = []
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT appointment_date FROM appointments
                    WHERE doctor_id = ? AND status != 'Cancelled'
                    ORDER BY appointment_date ASC;
                    """,
                    (doctor_id,),
                )
                dates = [r["appointment_date"] for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching doctor dates: {e}")

        today_str = date.today().isoformat()
        if today_str not in dates:
            dates.append(today_str)
        dates.sort()
        return dates

    def _doctor_has_appointments_on_date(self, doctor_id: int, target_date: str) -> bool:
        """Check if doctor has any active non-cancelled appointments on target date."""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled' LIMIT 1;",
                    (doctor_id, target_date),
                ).fetchone()
                return bool(row)
        except Exception:
            return False

    def _update_date_options(self) -> None:
        """Update available dates for current doctor selection."""
        if not self.selected_doctor_id or not hasattr(self, "date_selector"):
            return
        dates = self._fetch_doctor_dates(self.selected_doctor_id)
        if not dates:
            dates = [date.today().isoformat()]
        self.date_selector.configure(values=dates)

        today_str = date.today().isoformat()

        # If currently selected date has appointments for this doctor, keep it
        if self.selected_date and self._doctor_has_appointments_on_date(self.selected_doctor_id, self.selected_date):
            self.date_selector.set(self.selected_date)
        # If doctor has appointments today, select today
        elif self._doctor_has_appointments_on_date(self.selected_doctor_id, today_str):
            self.selected_date = today_str
            self.date_selector.set(today_str)
        else:
            # Pick next upcoming date with active appointments >= today
            upcoming_with_appts = [
                d for d in dates if d >= today_str and self._doctor_has_appointments_on_date(self.selected_doctor_id, d)
            ]
            if upcoming_with_appts:
                best_date = upcoming_with_appts[0]
            else:
                any_with_appts = [d for d in dates if self._doctor_has_appointments_on_date(self.selected_doctor_id, d)]
                best_date = any_with_appts[-1] if any_with_appts else today_str
            self.selected_date = best_date
            self.date_selector.set(best_date)

    def _on_doctor_selected(self, selection: str) -> None:
        """Handle doctor dropdown selection with direct ID mapping."""
        doc_id = self.doc_options_map.get(selection)
        if doc_id:
            self.selected_doctor_id = doc_id
            self._update_date_options()
            self._load_queue_data()

    def _on_date_selected(self, new_date: str) -> None:
        """Handle user changing appointment date in dropdown."""
        self.selected_date = new_date.strip()
        self._load_queue_data()

    def _load_queue_data(self) -> None:
        """Query and display live queue for the selected doctor and date."""
        if self._is_destroyed or not self.winfo_exists():
            return

        if not self.selected_doctor_id:
            return

        queue_data = get_doctor_live_queue(self.selected_doctor_id, self.selected_date)
        self.selected_date = queue_data.get("appointment_date") or self.selected_date
        now_serving = queue_data.get("now_serving")
        queue_list = queue_data.get("queue") or (queue_data.get("waiting_queue", []) + queue_data.get("completed_queue", []))
        waiting_count = queue_data.get("waiting_count", 0)
        completed_count = queue_data.get("completed_count", 0)
        is_future = queue_data.get("is_future_date", False)

        # Update KPI numbers
        if "NOW SERVING" in self.kpi_labels:
            if now_serving:
                self.kpi_labels["NOW SERVING"].configure(text=f"{now_serving.get('token_number', 'TK-01')} (Active)")
            elif is_future:
                self.kpi_labels["NOW SERVING"].configure(text="None (Ready)")
            else:
                self.kpi_labels["NOW SERVING"].configure(text="None (Ready)")

        if "PATIENTS WAITING" in self.kpi_labels:
            self.kpi_labels["PATIENTS WAITING"].configure(text=str(waiting_count))

        if "COMPLETED TODAY" in self.kpi_labels:
            self.kpi_labels["COMPLETED TODAY"].configure(text=str(completed_count))

        if "AVG WAIT TIME" in self.kpi_labels:
            if is_future:
                self.kpi_labels["AVG WAIT TIME"].configure(text="Scheduled")
            else:
                est_wait = waiting_count * 15
                self.kpi_labels["AVG WAIT TIME"].configure(text=f"~{est_wait} mins" if est_wait > 0 else "0 mins")

        # Render rows
        for w in self.rows_frame.winfo_children():
            w.destroy()

        if not queue_list:
            no_data = ctk.CTkLabel(
                self.rows_frame,
                text="No appointments scheduled for this doctor on the active date.",
                font=ctk.CTkFont(size=13),
                text_color=self.text_muted,
            )
            no_data.pack(pady=30)
            return

        user = get_current_user() or {}
        user_role = user.get("role")
        is_my_queue = (user_role == "Doctor" and user.get("linked_doctor_id") == self.selected_doctor_id) or user_role in ("Administrator", "Hospital Administrator", "Staff", "Reception Staff")

        for item in queue_list:
            appt_id = item["id"]
            is_highlighted = (self.highlight_appointment_id == appt_id)

            row = ctk.CTkFrame(
                self.rows_frame,
                fg_color=("#E0F2FE", "#132D52") if is_highlighted else "transparent",
                border_width=1 if is_highlighted else 0,
                border_color="#0284C7" if is_highlighted else None,
                height=38,
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            # 1. Token Number
            tok = item.get("token_number") or "—"
            tok_lbl = ctk.CTkLabel(
                row,
                text=tok,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                width=80,
                anchor="w",
            )
            tok_lbl.pack(side="left", padx=5)

            # 2. Appointment Code
            code = item.get("appointment_code", "")
            ctk.CTkLabel(
                row,
                text=code,
                font=ctk.CTkFont(size=11),
                text_color=self.text_primary,
                width=85,
                anchor="w",
            ).pack(side="left", padx=5)

            # 3. Patient Name
            pat_name = item.get("patient_name", "")
            disp_name = pat_name[:18] + "…" if len(pat_name) > 18 else pat_name
            ctk.CTkLabel(
                row,
                text=disp_name,
                font=ctk.CTkFont(size=11),
                text_color=self.text_primary,
                width=150,
                anchor="w",
            ).pack(side="left", padx=5)

            # 4. Slot
            ctk.CTkLabel(
                row,
                text=item.get("time_slot", ""),
                font=ctk.CTkFont(size=11),
                text_color=self.text_muted,
                width=80,
                anchor="w",
            ).pack(side="left", padx=5)

            # 5. Queue Status Chip
            q_st = item.get("queue_status") or "Waiting"
            if q_st == "Now Serving":
                c_bg = ("#DCFCE7", "#064E3B")
                c_fg = ("#15803D", "#34D399")
            elif q_st == "Waiting":
                c_bg = ("#E0F2FE", "#082F49")
                c_fg = ("#0284C7", "#38BDF8")
            elif q_st == "Completed":
                c_bg = ("#F1F5F9", "#1E293B")
                c_fg = ("#64748B", "#94A3B8")
            elif q_st == "Cancelled":
                c_bg = ("#FEE2E2", "#7F1D1D")
                c_fg = ("#DC2626", "#FCA5A5")
            else:  # No-Show
                c_bg = ("#FEF3C7", "#451A03")
                c_fg = ("#B45309", "#FCD34D")

            ctk.CTkLabel(
                row,
                text=q_st,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=c_bg,
                text_color=c_fg,
                corner_radius=4,
                width=110,
                height=22,
            ).pack(side="left", padx=5)

            # 6. Est. Wait Time
            if q_st == "Now Serving":
                wait_text = "In Chamber"
            elif is_future:
                wait_text = f"Scheduled ({item.get('time_slot', '')})"
            elif q_st == "Waiting":
                wait_text = f"~{item.get('estimated_wait_minutes', 0)} mins"
            else:
                wait_text = "—"

            ctk.CTkLabel(
                row,
                text=wait_text,
                font=ctk.CTkFont(size=10),
                text_color=self.text_muted,
                width=85,
                anchor="w",
            ).pack(side="left", padx=5)

            # 7. Doctor Actions
            act_box = ctk.CTkFrame(row, fg_color="transparent", width=110)
            act_box.pack(side="left", padx=5)

            if is_my_queue:
                if q_st == "Waiting":
                    start_btn = ctk.CTkButton(
                        act_box,
                        text="▶ Start",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color="#0284C7",
                        hover_color="#0369A1",
                        width=60,
                        height=24,
                        corner_radius=4,
                        command=lambda aid=appt_id: self._on_start_consultation(aid),
                    )
                    start_btn.pack(side="left")
                elif q_st == "Now Serving":
                    comp_btn = ctk.CTkButton(
                        act_box,
                        text="✓ Finish",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color="#10B981",
                        hover_color="#059669",
                        width=60,
                        height=24,
                        corner_radius=4,
                        command=lambda aid=appt_id: self._on_complete_consultation(aid),
                    )
                    comp_btn.pack(side="left")

    def _on_start_consultation(self, appointment_id: int) -> None:
        """Mark appointment as Now Serving."""
        res = start_consultation(appointment_id)
        is_ok = res[0] if isinstance(res, (tuple, list)) else bool(res.get("success"))
        if is_ok:
            self._load_queue_data()
            if self.on_update:
                self.on_update()

    def _on_complete_consultation(self, appointment_id: int) -> None:
        """Mark consultation as Completed."""
        res = complete_consultation(appointment_id)
        is_ok = res[0] if isinstance(res, (tuple, list)) else bool(res.get("success"))
        if is_ok:
            self._load_queue_data()
            if self.on_update:
                self.on_update()

    def _schedule_auto_refresh(self) -> None:
        """Schedule next 10-second queue refresh safely."""
        if self._is_destroyed:
            return
        self._refresh_timer = self.after(10000, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        """Periodic auto-refresh callback."""
        if self._is_destroyed or not self.winfo_exists():
            return
        self._load_queue_data()
        self._schedule_auto_refresh()

    def _on_close(self) -> None:
        """Clean up timers and destroy window."""
        self._is_destroyed = True
        if self._refresh_timer is not None:
            try:
                self.after_cancel(self._refresh_timer)
            except Exception:
                pass
            self._refresh_timer = None
        self.destroy()

    def _schedule_auto_refresh(self) -> None:
        """Schedule next 10-second queue refresh safely."""
        if self._is_destroyed:
            return
        self._refresh_timer = self.after(10000, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        """Periodic auto-refresh callback."""
        if self._is_destroyed or not self.winfo_exists():
            return
        self._load_queue_data()
        self._schedule_auto_refresh()

    def _on_close(self) -> None:
        """Clean up timers and destroy window."""
        self._is_destroyed = True
        if self._refresh_timer is not None:
            try:
                self.after_cancel(self._refresh_timer)
            except Exception:
                pass
            self._refresh_timer = None
        self.destroy()
