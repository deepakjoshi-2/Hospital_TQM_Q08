"""Appointments View for Hospital Management System — Q08.
Complete CRUD operations with SQLite persistence, slot conflict prevention,
search/status filter, and safety modals.
"""
import customtkinter as ctk
from typing import Optional

from config.constants import APPOINTMENT_STATUSES
from database.connection import get_db_connection
from ui.components.appointment_modals import (
    AppointmentFormModal,
    ConfirmAppointmentActionModal,
)


class AppointmentsView(ctk.CTkFrame):
    """Appointment scheduling view with full Create, Read, Update, Delete/Cancel, and Search operations."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._notice_timer_id: Optional[str] = None
        self.current_search_query = ""
        self.current_status_filter = "All Statuses"
        self.appointments = self._load_appointments()

        # Build UI layout
        self._build_header()
        self._build_notification_banner()
        self._build_table()

    def _load_appointments(self, query: str = "", status_filter: str = "All Statuses") -> list:
        """Fetch appointments from SQLite database with patient/doctor join, search, and status filter."""
        results = []
        try:
            with get_db_connection() as conn:
                sql = """
                    SELECT a.id, a.appointment_code, a.patient_id, a.doctor_id,
                           p.first_name || ' ' || p.last_name AS patient_name,
                           p.patient_code,
                           d.first_name || ' ' || d.last_name AS doctor_name,
                           d.doctor_code,
                           d.specialization,
                           a.appointment_date,
                           a.time_slot,
                           a.reason,
                           a.priority,
                           a.status,
                           a.satisfaction_rating
                    FROM appointments a
                    JOIN patients p ON a.patient_id = p.id
                    JOIN doctors d ON a.doctor_id = d.id
                    WHERE 1=1
                """
                params = []

                if query.strip():
                    term = f"%{query.strip()}%"
                    sql += """ AND (
                        a.appointment_code LIKE ? OR 
                        p.first_name LIKE ? OR 
                        p.last_name LIKE ? OR 
                        d.first_name LIKE ? OR 
                        d.last_name LIKE ? OR 
                        a.appointment_date LIKE ? OR
                        a.reason LIKE ?
                    )"""
                    params.extend([term, term, term, term, term, term, term])

                if status_filter and status_filter not in ("All", "All Statuses"):
                    sql += " AND a.status = ?"
                    params.append(status_filter)

                sql += " ORDER BY a.appointment_date DESC, a.time_slot ASC, a.id DESC;"
                cursor = conn.execute(sql, tuple(params))
                results = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error loading appointments from SQLite: {e}")
        return results

    def _build_header(self) -> None:
        """Header with search bar, status filter dropdown, clear button, and '+ Book Appointment' button."""
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=24, pady=(20, 10))

        info_box = ctk.CTkFrame(self.header, fg_color="transparent")
        info_box.pack(side="left")

        title = ctk.CTkLabel(
            info_box,
            text="Clinical Appointments Management",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        self.subtitle_lbl = ctk.CTkLabel(
            info_box,
            text=f"Total: {len(self.appointments)} scheduled, completed, and historical consultations in SQLite.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        self.subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Controls on the right: Search + Status Filter + Clear + Book Appointment
        ctrl_box = ctk.CTkFrame(self.header, fg_color="transparent")
        ctrl_box.pack(side="right")

        # Search Entry
        self.search_entry = ctk.CTkEntry(
            ctrl_box,
            placeholder_text="Search patient, doctor, code...",
            width=185,
            height=36,
            corner_radius=8,
        )
        self.search_entry.pack(side="left", padx=(0, 6))
        self.search_entry.bind("<Return>", lambda event: self._on_search())

        # Status Filter Dropdown
        status_options = ["All Statuses"] + APPOINTMENT_STATUSES
        self.status_dropdown = ctk.CTkOptionMenu(
            ctrl_box,
            values=status_options,
            command=self._on_status_filter,
            width=135,
            height=36,
            corner_radius=8,
        )
        self.status_dropdown.set("All Statuses")
        self.status_dropdown.pack(side="left", padx=(0, 6))

        # Clear Filter Button
        clear_btn = ctk.CTkButton(
            ctrl_box,
            text="✕ Clear",
            font=ctk.CTkFont(size=12),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=65,
            height=36,
            corner_radius=8,
            command=self._on_clear_filters,
        )
        clear_btn.pack(side="left", padx=(0, 10))

        # + Book Appointment Button (Prominent Action)
        add_btn = ctk.CTkButton(
            ctrl_box,
            text="＋ Book Appointment",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=36,
            corner_radius=8,
            command=self._open_add_modal,
        )
        add_btn.pack(side="left")

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
        self.notice_banner.pack(fill="x", padx=24, pady=(0, 10), before=self.card)
        if self._notice_timer_id is not None:
            self.after_cancel(self._notice_timer_id)
        self._notice_timer_id = self.after(4000, self._hide_notice)

    def _hide_notice(self) -> None:
        """Dismiss notice banner safely checking widget existence."""
        self._notice_timer_id = None
        if self.winfo_exists() and hasattr(self, "notice_banner") and self.notice_banner.winfo_exists():
            if self.notice_banner.winfo_ismapped():
                self.notice_banner.pack_forget()

    def destroy(self) -> None:
        """Cancel pending notification timers on view destruction."""
        if hasattr(self, "_notice_timer_id") and self._notice_timer_id is not None:
            self.after_cancel(self._notice_timer_id)
            self._notice_timer_id = None
        super().destroy()

    def _build_table(self) -> None:
        """Card container displaying appointments roster with Action buttons."""
        self.card = ctk.CTkFrame(
            self,
            corner_radius=12,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        self.card.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # Column Headers
        col_frame = ctk.CTkFrame(self.card, fg_color=("#F8FAFC", "#26293B"), height=36, corner_radius=6)
        col_frame.pack(fill="x", padx=14, pady=10)

        headers = [
            ("Code", 75),
            ("Date & Time", 125),
            ("Patient Name", 135),
            ("Physician", 140),
            ("Priority", 75),
            ("Status", 85),
            ("Rating", 55),
            ("Actions", 130),
        ]
        for h_text, width in headers:
            lbl = ctk.CTkLabel(
                col_frame,
                text=h_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#64748B", "#94A3B8"),
                width=width,
                anchor="w",
            )
            lbl.pack(side="left", padx=6, pady=4)

        # Scrollable rows container
        self.rows_frame = ctk.CTkScrollableFrame(self.card, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._render_rows()

    def _render_rows(self) -> None:
        """Populate scrollable frame with appointment rows and action buttons."""
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        if not self.appointments:
            no_data = ctk.CTkLabel(
                self.rows_frame,
                text="No matching appointments found in SQLite database.",
                font=ctk.CTkFont(size=14),
                text_color=("#64748B", "#94A3B8"),
            )
            no_data.pack(pady=40)
            return

        for a in self.appointments:
            row = ctk.CTkFrame(self.rows_frame, fg_color="transparent", height=40)
            row.pack(fill="x", pady=2)

            # 1. Code
            ctk.CTkLabel(
                row,
                text=a["appointment_code"],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                width=75,
                anchor="w",
            ).pack(side="left", padx=6)

            # 2. Date & Time
            ctk.CTkLabel(
                row,
                text=f"{a['appointment_date']} {a['time_slot']}",
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                width=125,
                anchor="w",
            ).pack(side="left", padx=6)

            # 3. Patient Name
            pat_name = a["patient_name"]
            display_pat = pat_name[:18] + ".." if len(pat_name) > 18 else pat_name
            ctk.CTkLabel(
                row,
                text=display_pat,
                font=ctk.CTkFont(size=12),
                text_color=("#0F172A", "#F8FAFC"),
                width=135,
                anchor="w",
            ).pack(side="left", padx=6)

            # 4. Doctor Name
            doc_name = a["doctor_name"]
            display_doc = doc_name[:18] + ".." if len(doc_name) > 18 else doc_name
            ctk.CTkLabel(
                row,
                text=display_doc,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                width=140,
                anchor="w",
            ).pack(side="left", padx=6)

            # 5. Priority
            p = a["priority"]
            p_fg = "#EF4444" if p == "Urgent" else ("#0F172A", "#F8FAFC")
            ctk.CTkLabel(
                row,
                text=p,
                font=ctk.CTkFont(size=11, weight="bold" if p == "Urgent" else "normal"),
                text_color=p_fg,
                width=75,
                anchor="w",
            ).pack(side="left", padx=6)

            # 6. Status Chip
            st = a["status"]
            if st == "Completed":
                c_bg = ("#DCFCE7", "#14532D")
                c_fg = ("#15803D", "#4ADE80")
            elif st == "Scheduled":
                c_bg = ("#FEF3C7", "#78350F")
                c_fg = ("#B45309", "#FCD34D")
            elif st == "Cancelled":
                c_bg = ("#FEE2E2", "#7F1D1D")
                c_fg = ("#B91C1C", "#F87171")
            else:  # No-Show
                c_bg = ("#F1F5F9", "#334155")
                c_fg = ("#64748B", "#94A3B8")

            chip = ctk.CTkLabel(
                row,
                text=st,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=c_bg,
                text_color=c_fg,
                corner_radius=6,
                width=85,
                height=22,
            )
            chip.pack(side="left", padx=6)

            # 7. Rating
            rating = a["satisfaction_rating"]
            rating_text = f"{rating} ★" if rating else "—"
            ctk.CTkLabel(
                row,
                text=rating_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#F59E0B" if rating else "#94A3B8"),
                width=55,
                anchor="w",
            ).pack(side="left", padx=6)

            # 8. Actions Frame (Edit + Del/Cancel)
            act_frame = ctk.CTkFrame(row, fg_color="transparent", width=130)
            act_frame.pack(side="left", padx=6)

            # Edit Button
            edit_btn = ctk.CTkButton(
                act_frame,
                text="✏️ Edit",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("#E2E8F0", "#334155"),
                text_color=("#0F172A", "#F8FAFC"),
                hover_color=("#CBD5E1", "#475569"),
                width=56,
                height=26,
                corner_radius=6,
                command=lambda a_row=a: self._open_edit_modal(a_row),
            )
            edit_btn.pack(side="left", padx=(0, 6))

            # Delete / Cancel Button
            del_btn = ctk.CTkButton(
                act_frame,
                text="🗑️ Del",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("#FEE2E2", "#7F1D1D"),
                text_color=("#DC2626", "#FCA5A5"),
                hover_color=("#FECACA", "#991B1B"),
                width=56,
                height=26,
                corner_radius=6,
                command=lambda a_row=a: self._open_confirm_modal(a_row),
            )
            del_btn.pack(side="left")

    def _open_add_modal(self) -> None:
        """Open modal form to book a new appointment."""
        AppointmentFormModal(
            self.winfo_toplevel(),
            appointment_data=None,
            on_success=self._on_action_success,
        )

    def _open_edit_modal(self, appointment_row: dict) -> None:
        """Open modal form pre-filled to update an existing appointment."""
        AppointmentFormModal(
            self.winfo_toplevel(),
            appointment_data=appointment_row,
            on_success=self._on_action_success,
        )

    def _open_confirm_modal(self, appointment_row: dict) -> None:
        """Open safety dialog offering Cancel Appointment or Permanent Delete."""
        ConfirmAppointmentActionModal(
            self.winfo_toplevel(),
            appointment_row=appointment_row,
            on_success=self._on_action_success,
        )

    def _on_action_success(self, message: str) -> None:
        """Handle appointment CRUD action completion callback."""
        is_error = message.startswith("Error") or "failed" in message.lower() or "cannot" in message.lower()
        self.refresh_data()
        self._show_notice(message, is_error=is_error)

    def refresh_data(self) -> None:
        """Re-query SQLite database and update appointments table rows and counter."""
        self.appointments = self._load_appointments(
            self.current_search_query,
            self.current_status_filter,
        )
        self.subtitle_lbl.configure(
            text=f"Total: {len(self.appointments)} scheduled, completed, and historical consultations in SQLite."
        )
        self._render_rows()

    def _on_search(self) -> None:
        """Handle search filtering query."""
        self.current_search_query = self.search_entry.get().strip()
        self.refresh_data()

    def _on_status_filter(self, choice: str) -> None:
        """Handle status dropdown selection."""
        self.current_status_filter = choice
        self.refresh_data()

    def _on_clear_filters(self) -> None:
        """Clear search input and status filter, reloading full roster."""
        self.search_entry.delete(0, "end")
        self.status_dropdown.set("All Statuses")
        self.current_search_query = ""
        self.current_status_filter = "All Statuses"
        self.refresh_data()
