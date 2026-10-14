"""Doctors View for Hospital Management System — Q08.
Complete CRUD operations with SQLite persistence, search/specialty filter, and safety modals.
"""
import customtkinter as ctk
from typing import Optional

from config.constants import SPECIALIZATIONS
from database.connection import get_db_connection
from ui.components.doctor_modals import ConfirmDoctorActionModal, DoctorFormModal


class DoctorsView(ctk.CTkFrame):
    """Doctor management view with full Create, Read, Update, Delete, and Search operations."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._notice_timer_id: Optional[str] = None
        self.current_search_query = ""
        self.current_specialty_filter = "All Specialties"
        self.doctors = self._load_doctors()

        # Build UI layout
        self._build_header()
        self._build_notification_banner()
        self._build_table()

    def _load_doctors(self, query: str = "", specialty: str = "All Specialties") -> list:
        """Fetch doctors from SQLite database with optional search and specialty filtering."""
        results = []
        try:
            with get_db_connection() as conn:
                sql = """
                    SELECT id, doctor_code, first_name, last_name, specialization,
                           phone, email, consultation_fee, room_number, status
                    FROM doctors
                    WHERE 1=1
                """
                params = []

                if query.strip():
                    sql += " AND (doctor_code LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ? OR room_number LIKE ?)"
                    term = f"%{query.strip()}%"
                    params.extend([term, term, term, term, term, term])

                if specialty and specialty != "All Specialties":
                    sql += " AND specialization = ?"
                    params.append(specialty)

                sql += " ORDER BY id DESC;"
                cursor = conn.execute(sql, tuple(params))
                results = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error loading doctors from SQLite: {e}")
        return results

    def _build_header(self) -> None:
        """Header with search bar, specialty filter, clear button, and '+ Add Doctor' button."""
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=24, pady=(20, 10))

        info_box = ctk.CTkFrame(self.header, fg_color="transparent")
        info_box.pack(side="left")

        title = ctk.CTkLabel(
            info_box,
            text="Medical Specialists & Staff Roster",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        self.subtitle_lbl = ctk.CTkLabel(
            info_box,
            text=f"Total: {len(self.doctors)} registered physicians persisted in SQLite database.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        self.subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Controls on the right: Search + Filter + Add Doctor
        ctrl_box = ctk.CTkFrame(self.header, fg_color="transparent")
        ctrl_box.pack(side="right")

        # Search Entry
        self.search_entry = ctk.CTkEntry(
            ctrl_box,
            placeholder_text="Search name, code, email, room...",
            width=200,
            height=36,
            corner_radius=8,
        )
        self.search_entry.pack(side="left", padx=(0, 6))
        self.search_entry.bind("<Return>", lambda event: self._on_search())

        # Specialty Filter Dropdown
        specialty_options = ["All Specialties"] + SPECIALIZATIONS
        self.spec_dropdown = ctk.CTkOptionMenu(
            ctrl_box,
            values=specialty_options,
            command=self._on_specialty_filter,
            width=150,
            height=36,
            corner_radius=8,
        )
        self.spec_dropdown.set("All Specialties")
        self.spec_dropdown.pack(side="left", padx=(0, 6))

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

        # + Add Doctor Button (Prominent Action)
        add_btn = ctk.CTkButton(
            ctrl_box,
            text="＋ Add Doctor",
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
            self.notice_banner.pack_forget()

    def destroy(self) -> None:
        """Cancel pending notification timers on view destruction."""
        if hasattr(self, "_notice_timer_id") and self._notice_timer_id is not None:
            self.after_cancel(self._notice_timer_id)
            self._notice_timer_id = None
        super().destroy()

    def _build_table(self) -> None:
        """Card container displaying doctors roster with Action buttons."""
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
            ("Doctor Name", 160),
            ("Specialization", 130),
            ("Room", 90),
            ("Fee (INR)", 80),
            ("Status", 105),
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
        """Populate scrollable frame with doctor rows and action buttons."""
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        if not self.doctors:
            no_data = ctk.CTkLabel(
                self.rows_frame,
                text="No matching physicians found in SQLite database.",
                font=ctk.CTkFont(size=14),
                text_color=("#64748B", "#94A3B8"),
            )
            no_data.pack(pady=40)
            return

        for d in self.doctors:
            row = ctk.CTkFrame(self.rows_frame, fg_color="transparent", height=40)
            row.pack(fill="x", pady=2)

            # 1. Code
            ctk.CTkLabel(
                row,
                text=d["doctor_code"],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                width=75,
                anchor="w",
            ).pack(side="left", padx=6)

            # 2. Name
            full_name = f"{d['first_name']} {d['last_name']}"
            display_name = full_name[:22] + "..." if len(full_name) > 22 else full_name
            ctk.CTkLabel(
                row,
                text=display_name,
                font=ctk.CTkFont(size=12),
                text_color=("#0F172A", "#F8FAFC"),
                width=160,
                anchor="w",
            ).pack(side="left", padx=6)

            # 3. Specialization
            spec = d["specialization"]
            display_spec = spec[:18] + ".." if len(spec) > 18 else spec
            ctk.CTkLabel(
                row,
                text=display_spec,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                width=130,
                anchor="w",
            ).pack(side="left", padx=6)

            # 4. Room
            ctk.CTkLabel(
                row,
                text=d["room_number"],
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                width=90,
                anchor="w",
            ).pack(side="left", padx=6)

            # 5. Fee
            ctk.CTkLabel(
                row,
                text=f"₹{int(d['consultation_fee'])}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#0F172A", "#F8FAFC"),
                width=80,
                anchor="w",
            ).pack(side="left", padx=6)

            # 6. Status Chip
            status = d["status"]
            if status == "Available":
                c_bg = ("#DCFCE7", "#14532D")
                c_fg = ("#15803D", "#4ADE80")
            elif status == "In Consultation":
                c_bg = ("#FEF3C7", "#78350F")
                c_fg = ("#B45309", "#FCD34D")
            else:  # On Leave
                c_bg = ("#FEE2E2", "#7F1D1D")
                c_fg = ("#B91C1C", "#F87171")

            chip = ctk.CTkLabel(
                row,
                text=status,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=c_bg,
                text_color=c_fg,
                corner_radius=6,
                width=100,
                height=22,
            )
            chip.pack(side="left", padx=6)

            # 7. Actions Frame (Edit + Delete)
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
                command=lambda d_row=d: self._open_edit_modal(d_row),
            )
            edit_btn.pack(side="left", padx=(0, 6))

            # Delete Button
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
                command=lambda d_row=d: self._open_delete_modal(d_row),
            )
            del_btn.pack(side="left")

    def _open_add_modal(self) -> None:
        """Open modal form to register a new physician."""
        DoctorFormModal(
            self.winfo_toplevel(),
            doctor_data=None,
            on_success=self._on_action_success,
        )

    def _open_edit_modal(self, doctor_row: dict) -> None:
        """Open modal form pre-filled to edit an existing doctor."""
        DoctorFormModal(
            self.winfo_toplevel(),
            doctor_data=doctor_row,
            on_success=self._on_action_success,
        )

    def _open_delete_modal(self, doctor_row: dict) -> None:
        """Open confirmation dialog before archiving or deleting a physician."""
        ConfirmDoctorActionModal(
            self.winfo_toplevel(),
            doctor_row=doctor_row,
            on_success=self._on_action_success,
        )

    def _on_action_success(self, message: str) -> None:
        """Handle successful CRUD operation callback."""
        is_error = message.startswith("Error") or "failed" in message.lower() or "cannot" in message.lower()
        self.refresh_data()
        self._show_notice(message, is_error=is_error)

    def refresh_data(self) -> None:
        """Re-query SQLite database and update table rows and counter."""
        self.doctors = self._load_doctors(self.current_search_query, self.current_specialty_filter)
        self.subtitle_lbl.configure(
            text=f"Total: {len(self.doctors)} registered physicians persisted in SQLite database."
        )
        self._render_rows()

    def _on_search(self) -> None:
        """Handle search filtering query."""
        self.current_search_query = self.search_entry.get().strip()
        self.refresh_data()

    def _on_specialty_filter(self, choice: str) -> None:
        """Handle specialty dropdown selection."""
        self.current_specialty_filter = choice
        self.refresh_data()

    def _on_clear_filters(self) -> None:
        """Clear search input and specialty filter, reloading full roster."""
        self.search_entry.delete(0, "end")
        self.spec_dropdown.set("All Specialties")
        self.current_search_query = ""
        self.current_specialty_filter = "All Specialties"
        self.refresh_data()
