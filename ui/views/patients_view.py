"""Patients View for Hospital Management System — Q08.
Complete CRUD operations with SQLite persistence, search, and confirmation dialogs.
"""
import customtkinter as ctk
from typing import Optional

from database.connection import get_db_connection
from ui.components.patient_modals import ConfirmPatientActionModal, PatientFormModal


class PatientsView(ctk.CTkFrame):
    """Patient management view with full Create, Read, Update, Delete, and Search operations."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_search_query = ""
        self.patients = self._load_patients()

        # Build UI layout
        self._build_header()
        self._build_notification_banner()
        self._build_table()

    def _load_patients(self, query: str = "") -> list:
        """Fetch patients from SQLite database, optionally filtering by query."""
        results = []
        try:
            with get_db_connection() as conn:
                if query.strip():
                    term = f"%{query.strip()}%"
                    cursor = conn.execute(
                        """
                        SELECT id, patient_code, first_name, last_name, dob, gender, phone, email, blood_group, emergency_contact, address, status
                        FROM patients
                        WHERE patient_code LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?
                        ORDER BY id DESC;
                        """,
                        (term, term, term, term),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT id, patient_code, first_name, last_name, dob, gender, phone, email, blood_group, emergency_contact, address, status
                        FROM patients
                        ORDER BY id DESC;
                        """
                    )
                results = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error loading patients from SQLite: {e}")
        return results

    def _build_header(self) -> None:
        """Header with title, search input, clear button, and prominent '+ Add Patient' button."""
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=24, pady=(20, 10))

        info_box = ctk.CTkFrame(self.header, fg_color="transparent")
        info_box.pack(side="left")

        title = ctk.CTkLabel(
            info_box,
            text="Patient Registry & Records",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        self.subtitle_lbl = ctk.CTkLabel(
            info_box,
            text=f"Total: {len(self.patients)} patient records persisted in SQLite database.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        self.subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Controls on the right: Search + Add Patient
        ctrl_box = ctk.CTkFrame(self.header, fg_color="transparent")
        ctrl_box.pack(side="right")

        # Search Entry
        self.search_entry = ctk.CTkEntry(
            ctrl_box,
            placeholder_text="Search name, phone, code...",
            width=220,
            height=36,
            corner_radius=8,
        )
        self.search_entry.pack(side="left", padx=(0, 6))
        self.search_entry.bind("<Return>", lambda event: self._on_search())

        # Search Button
        search_btn = ctk.CTkButton(
            ctrl_box,
            text="🔍 Search",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=76,
            height=36,
            corner_radius=8,
            command=self._on_search,
        )
        search_btn.pack(side="left", padx=(0, 6))

        # Clear Search Button
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
            command=self._on_clear_search,
        )
        clear_btn.pack(side="left", padx=(0, 12))

        # + Add Patient Button (Prominent Action)
        add_btn = ctk.CTkButton(
            ctrl_box,
            text="＋ Add Patient",
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
        """Show temporary feedback banner."""
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
        # Auto-hide notice after 4 seconds
        self.after(4000, self._hide_notice)

    def _hide_notice(self) -> None:
        """Dismiss notice banner."""
        if self.notice_banner.winfo_ismapped():
            self.notice_banner.pack_forget()

    def _build_table(self) -> None:
        """Card container displaying patients list with Action column."""
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
            ("Code", 80),
            ("Patient Name", 150),
            ("DOB & Gender", 110),
            ("Contact Phone", 120),
            ("Blood", 70),
            ("Status", 80),
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
        """Populate scrollable frame with patient rows and action buttons."""
        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        if not self.patients:
            no_data = ctk.CTkLabel(
                self.rows_frame,
                text="No matching patient records found in SQLite database.",
                font=ctk.CTkFont(size=14),
                text_color=("#64748B", "#94A3B8"),
            )
            no_data.pack(pady=40)
            return

        for p in self.patients:
            row = ctk.CTkFrame(self.rows_frame, fg_color="transparent", height=40)
            row.pack(fill="x", pady=2)

            # 1. Code
            ctk.CTkLabel(
                row,
                text=p["patient_code"],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                width=80,
                anchor="w",
            ).pack(side="left", padx=6)

            # 2. Name
            full_name = f"{p['first_name']} {p['last_name']}"
            display_name = full_name[:20] + "..." if len(full_name) > 20 else full_name
            ctk.CTkLabel(
                row,
                text=display_name,
                font=ctk.CTkFont(size=12),
                text_color=("#0F172A", "#F8FAFC"),
                width=150,
                anchor="w",
            ).pack(side="left", padx=6)

            # 3. DOB & Gender
            g_initial = p["gender"][0] if p.get("gender") else "M"
            ctk.CTkLabel(
                row,
                text=f"{p['dob']} ({g_initial})",
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                width=110,
                anchor="w",
            ).pack(side="left", padx=6)

            # 4. Phone
            ctk.CTkLabel(
                row,
                text=p["phone"],
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                width=120,
                anchor="w",
            ).pack(side="left", padx=6)

            # 5. Blood Group
            ctk.CTkLabel(
                row,
                text=p.get("blood_group") or "—",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("#F1F5F9", "#26293B"),
                corner_radius=4,
                width=60,
                height=22,
            ).pack(side="left", padx=(6, 16))

            # 6. Status Chip
            st = p.get("status") or "Active"
            if st == "Active":
                chip_bg = ("#DCFCE7", "#14532D")
                chip_fg = ("#15803D", "#4ADE80")
            elif st == "Discharged":
                chip_bg = ("#FEF3C7", "#78350F")
                chip_fg = ("#B45309", "#FCD34D")
            else:  # Archived
                chip_bg = ("#F1F5F9", "#334155")
                chip_fg = ("#64748B", "#94A3B8")

            ctk.CTkLabel(
                row,
                text=st,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=chip_bg,
                text_color=chip_fg,
                corner_radius=6,
                width=75,
                height=22,
            ).pack(side="left", padx=6)

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
                command=lambda p_row=p: self._open_edit_modal(p_row),
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
                command=lambda p_row=p: self._open_delete_modal(p_row),
            )
            del_btn.pack(side="left")

    def _open_add_modal(self) -> None:
        """Open modal form to register a new patient."""
        PatientFormModal(
            self.winfo_toplevel(),
            patient_data=None,
            on_success=self._on_action_success,
        )

    def _open_edit_modal(self, patient_row: dict) -> None:
        """Open modal form pre-filled to edit an existing patient."""
        PatientFormModal(
            self.winfo_toplevel(),
            patient_data=patient_row,
            on_success=self._on_action_success,
        )

    def _open_delete_modal(self, patient_row: dict) -> None:
        """Open confirmation dialog before archiving or deleting a patient."""
        ConfirmPatientActionModal(
            self.winfo_toplevel(),
            patient_row=patient_row,
            on_success=self._on_action_success,
        )

    def _on_action_success(self, message: str) -> None:
        """Handle successful CRUD operation callback."""
        is_error = message.startswith("Error") or "failed" in message.lower()
        self.refresh_data()
        self._show_notice(message, is_error=is_error)

    def refresh_data(self) -> None:
        """Re-query SQLite database and update table rows and subtitle counter."""
        self.patients = self._load_patients(self.current_search_query)
        self.subtitle_lbl.configure(
            text=f"Total: {len(self.patients)} patient records persisted in SQLite database."
        )
        self._render_rows()

    def _on_search(self) -> None:
        """Handle search filtering query."""
        self.current_search_query = self.search_entry.get().strip()
        self.refresh_data()

    def _on_clear_search(self) -> None:
        """Clear search input and reload full patient directory."""
        self.search_entry.delete(0, "end")
        self.current_search_query = ""
        self.refresh_data()
