"""Interactive modal dialogs for Appointment Booking, Edit, and Cancellation workflows.
Engineered with fixed footers, conflict prevention, and responsive scrollable forms.
"""
import customtkinter as ctk
from datetime import datetime
from typing import Callable, Dict, Optional

from config.constants import (
    APPOINTMENT_PRIORITIES,
    APPOINTMENT_STATUSES,
    ROLE_PATIENT,
    STATUS_PENDING,
    TIME_SLOTS,
)
from services.auth_service import get_current_user
from services.appointment_service import (
    cancel_appointment,
    create_appointment,
    delete_appointment,
    get_appointment_by_code,
    get_appointment_by_id,
    get_appointment_confirmation_details,
    get_doctor_dropdown_options,
    get_next_appointment_code,
    get_patient_dropdown_options,
    submit_visit_feedback,
    update_appointment,
)


class AppointmentFormModal(ctk.CTkToplevel):
    """Modal dialog for booking or updating an appointment with slot collision prevention."""

    def __init__(
        self,
        master,
        appointment_data: Optional[Dict] = None,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_success = on_success
        self._record_not_found = False
        self._not_found_message = ""

        # Normalize and resolve appointment input (supports dict, int ID, or string appointment code)
        raw_data = appointment_data
        resolved_id = None
        resolved_code = None

        if isinstance(raw_data, int):
            resolved_id = raw_data
            raw_data = {}
        elif isinstance(raw_data, str):
            resolved_code = raw_data.strip()
            raw_data = {}
        elif isinstance(raw_data, dict):
            resolved_id = raw_data.get("id") or raw_data.get("appointment_id")
            resolved_code = raw_data.get("appointment_code")

        # An edit intent is present if an appointment primary key or existing appointment code was provided.
        # If raw_data only carries default fields (e.g. {'patient_id': 1}) without an appointment key/code,
        # it is a new booking form, not an edit!
        has_edit_intent = bool(resolved_id is not None or resolved_code)

        fetched_record = None
        if resolved_id is not None:
            fetched_record = get_appointment_by_id(resolved_id)
            if not fetched_record and resolved_code:
                fetched_record = get_appointment_by_code(resolved_code)
        elif resolved_code:
            fetched_record = get_appointment_by_code(resolved_code)

        if fetched_record:
            self.is_edit = True
            self.appointment_id = fetched_record["id"]
            merged = dict(fetched_record)
            if isinstance(raw_data, dict):
                merged.update({k: v for k, v in raw_data.items() if v is not None})
            self.appointment_data = merged
        elif has_edit_intent:
            self.is_edit = True
            self.appointment_id = resolved_id
            self.appointment_data = raw_data if isinstance(raw_data, dict) else {}
            self._record_not_found = True
            missing_identifier = f"ID {resolved_id}" if resolved_id is not None else f"Code '{resolved_code}'"
            self._not_found_message = f"Appointment {missing_identifier} not found."
        else:
            self.is_edit = False
            self.appointment_id = None
            self.appointment_data = raw_data if isinstance(raw_data, dict) else {}

        # Check active authenticated user session for role-specific presentation
        self.current_user = get_current_user() or {}
        self.user_role = self.current_user.get("role")
        self.is_patient_user = (self.user_role == ROLE_PATIENT)

        # Pre-fill patient_id for patient user booking
        if self.is_patient_user and not self.is_edit:
            linked_pid = self.current_user.get("linked_patient_id")
            if linked_pid:
                self.appointment_data["patient_id"] = int(linked_pid)

        # Fetch dynamic patient & doctor options from database
        self.patient_options = get_patient_dropdown_options()
        self.doctor_options = get_doctor_dropdown_options()

        self.patient_id_map = {label: pid for pid, label in self.patient_options}
        self.patient_label_map = {pid: label for pid, label in self.patient_options}

        self.doctor_id_map = {label: did for did, label in self.doctor_options}
        self.doctor_label_map = {did: label for did, label in self.doctor_options}

        # Window title & properties
        appt_code_str = ""
        if isinstance(self.appointment_data, dict):
            appt_code_str = self.appointment_data.get("appointment_code") or ""
        if not appt_code_str and resolved_code:
            appt_code_str = resolved_code

        title_text = f"Edit Appointment: {appt_code_str}" if self.is_edit else "Book Clinical Appointment"
        self.title(title_text)
        self.transient(master)
        self.grab_set()

        # Responsive geometry tailored to 720p / 1080p and high-DPI scaling
        self._apply_responsive_geometry(master)

        # 1. FIXED HEADER (Packed TOP)
        self._build_header()

        # 2. FIXED FOOTER (Packed BOTTOM FIRST so it is permanently visible)
        self._build_fixed_footer()

        # 3. SCROLLABLE FORM BODY (Packed in the remaining middle area)
        self._build_scrollable_form()

        # If appointment record could not be found, display notice and disable save
        if self._record_not_found:
            self._show_error(self._not_found_message)
            if hasattr(self, "save_btn") and self.save_btn:
                self.save_btn.configure(state="disabled")

        # Bind mouse wheel and keyboard shortcuts
        self._setup_event_bindings()

        # Lift and focus
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Calculate dimensions so the modal fits safely inside screen height with taskbar margins."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        max_unscaled_h = int((sh - 90) / scaling)
        target_h = min(440, max_unscaled_h)
        target_w = min(580, int((sw - 40) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.minsize(min(460, sw - 40), min(340, sh - 60))

    def _build_header(self) -> None:
        """Header with title, subtitle, and error banner."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(12, 4))

        title = "✏️ Edit Appointment" if self.is_edit else "📅 Book Outpatient Appointment"
        sub = "Update appointment status, doctor, date, or clinical feedback." if self.is_edit else "Select patient, physician, date, and slot to schedule a consultation."

        t_lbl = ctk.CTkLabel(
            self.header_frame,
            text=title,
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="w",
        )
        t_lbl.pack(fill="x")

        s_lbl = ctk.CTkLabel(
            self.header_frame,
            text=sub,
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        s_lbl.pack(fill="x", pady=(1, 2))

        # Error notification banner (hidden by default)
        self.error_banner = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#FEE2E2", "#7F1D1D"),
            text_color=("#DC2626", "#FCA5A5"),
            corner_radius=6,
            height=26,
            wraplength=520,
        )

    def _show_error(self, message: str) -> None:
        """Display error banner in fixed header area."""
        self.error_banner.configure(text=f"  ⚠️  {message}")
        if not self.error_banner.winfo_ismapped():
            self.error_banner.pack(fill="x", pady=(4, 0))

    def _clear_error(self) -> None:
        """Dismiss error banner."""
        if self.error_banner.winfo_ismapped():
            self.error_banner.pack_forget()

    def _build_fixed_footer(self) -> None:
        """Fixed footer bar permanently anchored at the bottom of the dialog."""
        self.footer_frame = ctk.CTkFrame(
            self,
            fg_color=("#F1F5F9", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
            corner_radius=8,
            height=52,
        )
        self.footer_frame.pack(side="bottom", fill="x", padx=16, pady=(4, 12))
        self.footer_frame.pack_propagate(False)

        # Helper tip on left
        tip_lbl = ctk.CTkLabel(
            self.footer_frame,
            text="* Required fields  |  Esc to Cancel",
            font=ctk.CTkFont(size=10),
            text_color=("#64748B", "#94A3B8"),
        )
        tip_lbl.pack(side="left", padx=14)

        # Buttons on right
        cancel_btn = ctk.CTkButton(
            self.footer_frame,
            text="Cancel",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=85,
            height=32,
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(8, 12), pady=10)

        self.save_btn = ctk.CTkButton(
            self.footer_frame,
            text="✓ Save Appointment" if self.is_edit else "✓ Confirm Booking",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=32,
            command=self._on_save,
        )
        self.save_btn.pack(side="right", pady=10)

    def _build_scrollable_form(self) -> None:
        """Scrollable form container occupying the center between header and footer."""
        self.form_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=("white", "#181A26"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
            corner_radius=8,
        )
        self.form_scroll.pack(side="top", fill="both", expand=True, padx=16, pady=(2, 4))
        self.form_scroll.grid_columnconfigure((0, 1), weight=1, uniform="appt_col")

        d = self.appointment_data or {}

        # Row 0: Appointment Code & Priority
        ctk.CTkLabel(self.form_scroll, text="Appointment Code *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Priority Level *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=1, padx=8, pady=(4, 1), sticky="w")

        default_code = d.get("appointment_code") or get_next_appointment_code()
        self.code_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. APT-3043", height=32)
        self.code_entry.insert(0, default_code)
        self.code_entry.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.priority_menu = ctk.CTkOptionMenu(self.form_scroll, values=APPOINTMENT_PRIORITIES, height=32)
        self.priority_menu.set(d.get("priority") or "Normal")
        self.priority_menu.grid(row=1, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 2: Patient Selection (Locked to Authenticated Patient for Patient Role)
        if self.is_patient_user and not self.is_edit:
            ctk.CTkLabel(
                self.form_scroll,
                text="Patient Profile (Authenticated Account) *",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                anchor="w",
            ).grid(row=2, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")

            linked_pid = self.current_user.get("linked_patient_id")
            pat_name = self.current_user.get("full_name") or ""
            if not pat_name:
                p_first = self.current_user.get("pat_first_name") or ""
                p_last = self.current_user.get("pat_last_name") or ""
                pat_name = f"{p_first} {p_last}".strip()
            if not pat_name and linked_pid in self.patient_label_map:
                pat_name = self.patient_label_map[linked_pid]
            if not pat_name:
                pat_name = f"Patient #{linked_pid}" if linked_pid else "Unlinked Profile"

            p_code = self.current_user.get("patient_code") or (f"PAT-{linked_pid}" if linked_pid else "NO-ID")

            pat_card = ctk.CTkFrame(
                self.form_scroll,
                fg_color=("#F1F5F9", "#1E293B"),
                corner_radius=6,
                border_width=1,
                border_color=("#CBD5E1", "#334155"),
                height=36,
            )
            pat_card.grid(row=3, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="ew")

            ctk.CTkLabel(
                pat_card,
                text=f"👤 {pat_name} ({p_code})  —  [Authenticated: Self-Booking Only]",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                anchor="w",
                padx=12,
                pady=6,
            ).pack(fill="x")
            self.patient_menu = None
        else:
            ctk.CTkLabel(self.form_scroll, text="Select Patient *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")

            patient_labels = list(self.patient_id_map.keys()) if self.patient_id_map else ["No Patients in DB"]
            self.patient_menu = ctk.CTkOptionMenu(self.form_scroll, values=patient_labels, height=32)
            if d.get("patient_id") and d["patient_id"] in self.patient_label_map:
                self.patient_menu.set(self.patient_label_map[d["patient_id"]])
            elif patient_labels:
                self.patient_menu.set(patient_labels[0])
            self.patient_menu.grid(row=3, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="ew")

        # Row 4: Doctor Selection (Dropdown dynamically loaded from SQLite)
        ctk.CTkLabel(self.form_scroll, text="Select Doctor *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=4, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")

        doctor_labels = list(self.doctor_id_map.keys()) if self.doctor_id_map else ["No Doctors in DB"]
        self.doctor_menu = ctk.CTkOptionMenu(self.form_scroll, values=doctor_labels, height=32)
        if d.get("doctor_id") and d["doctor_id"] in self.doctor_label_map:
            self.doctor_menu.set(self.doctor_label_map[d["doctor_id"]])
        elif doctor_labels:
            self.doctor_menu.set(doctor_labels[0])
        self.doctor_menu.grid(row=5, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="ew")

        # Row 6: Appointment Date & Time Slot
        ctk.CTkLabel(self.form_scroll, text="Appointment Date (YYYY-MM-DD) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=6, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Time Slot *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=6, column=1, padx=8, pady=(4, 1), sticky="w")

        default_date = d.get("appointment_date") or datetime.now().strftime("%Y-%m-%d")
        self.date_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="YYYY-MM-DD", height=32)
        self.date_entry.insert(0, default_date)
        self.date_entry.grid(row=7, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.slot_menu = ctk.CTkOptionMenu(self.form_scroll, values=TIME_SLOTS, height=32)
        self.slot_menu.set(d.get("time_slot") or "10:00 AM")
        self.slot_menu.grid(row=7, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 8: Status & Info (Non-editable for patient bookings; CSAT post-visit only)
        if self.is_patient_user and not self.is_edit:
            ctk.CTkLabel(
                self.form_scroll,
                text="Consultation Status",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                anchor="w",
            ).grid(row=8, column=0, padx=8, pady=(4, 1), sticky="w")

            status_card = ctk.CTkFrame(
                self.form_scroll,
                fg_color=("#FEF3C7", "#3D2A00"),
                corner_radius=6,
                border_width=1,
                border_color=("#F59E0B", "#B45309"),
                height=32,
            )
            status_card.grid(row=9, column=0, padx=8, pady=(0, 6), sticky="ew")

            ctk.CTkLabel(
                status_card,
                text="⏳ Pending Staff Review (Default)",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#92400E", "#FCD34D"),
                anchor="w",
                padx=10,
                pady=6,
            ).pack(fill="x")
            self.status_menu = None
        else:
            ctk.CTkLabel(self.form_scroll, text="Consultation Status *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=8, column=0, padx=8, pady=(4, 1), sticky="w")
            
            self.status_menu = ctk.CTkOptionMenu(self.form_scroll, values=APPOINTMENT_STATUSES, height=32)
            self.status_menu.set(d.get("status") or ("Confirmed" if not self.is_edit else "Scheduled"))
            self.status_menu.grid(row=9, column=0, padx=8, pady=(0, 6), sticky="ew")

        if self.is_edit and d.get("status") == "Completed":
            ctk.CTkLabel(self.form_scroll, text="Recorded CSAT Rating", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=8, column=1, padx=8, pady=(4, 1), sticky="w")
            rating_options = ["None", "5 ★ (Excellent)", "4 ★ (Good)", "3 ★ (Average)", "2 ★ (Poor)", "1 ★ (Very Poor)"]
            self.rating_menu = ctk.CTkOptionMenu(self.form_scroll, values=rating_options, height=32)
            existing_rating = d.get("satisfaction_rating")
            if existing_rating:
                matched = [opt for opt in rating_options if opt.startswith(str(existing_rating))]
                self.rating_menu.set(matched[0] if matched else "None")
            else:
                self.rating_menu.set("None")
            self.rating_menu.grid(row=9, column=1, padx=8, pady=(0, 6), sticky="ew")
        else:
            self.rating_menu = None
            ctk.CTkLabel(self.form_scroll, text="Satisfaction Policy", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=8, column=1, padx=8, pady=(4, 1), sticky="w")
            policy_lbl = ctk.CTkLabel(
                self.form_scroll,
                text="⭐ CSAT feedback is collected post-visit after completion.",
                font=ctk.CTkFont(size=10),
                text_color=("#0284C7", "#38BDF8"),
                fg_color=("#E0F2FE", "#0C2E4E"),
                corner_radius=6,
                height=32,
            )
            policy_lbl.grid(row=9, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 10: Reason for Visit
        ctk.CTkLabel(self.form_scroll, text="Reason for Visit *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=10, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")
        self.reason_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Annual cardiac assessment, Migraine, Fever", height=32)
        if d.get("reason"):
            self.reason_entry.insert(0, d["reason"])
        self.reason_entry.grid(row=11, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="ew")

        # Row 12: Clinical Notes
        ctk.CTkLabel(self.form_scroll, text="Clinical Notes / Instructions (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=12, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")
        self.notes_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Pre-consultation reports verified, fasting advised", height=32)
        if d.get("notes"):
            self.notes_entry.insert(0, d["notes"])
        self.notes_entry.grid(row=13, column=0, columnspan=2, padx=8, pady=(0, 12), sticky="ew")

    def _setup_event_bindings(self) -> None:
        """Bind mouse wheel scrolling and keyboard shortcuts."""
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Control-s>", lambda event: self._on_save())
        self._bind_mousewheel_recursive(self.form_scroll)

    def _bind_mousewheel_recursive(self, widget) -> None:
        """Recursively attach mouse wheel scrolling handler."""
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")
        except (NotImplementedError, AttributeError, Exception):
            pass
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling on the form with responsive desktop increments."""
        try:
            if hasattr(self, "form_scroll") and self.form_scroll._parent_canvas:
                delta = getattr(event, "delta", 0)
                num = getattr(event, "num", 0)
                step = int(abs(delta) / 120.0 * 40) if delta else 40
                if num == 5 or delta < 0:
                    self.form_scroll._parent_canvas.yview("scroll", max(1, step), "units")
                elif num == 4 or delta > 0:
                    self.form_scroll._parent_canvas.yview("scroll", -max(1, step), "units")
        except Exception:
            pass

    def _on_save(self) -> None:
        """Gather inputs, run validation and conflict checks, and save to SQLite with double-click safeguard."""
        self._clear_error()

        # Double-click safeguard: disable save button while processing
        self.save_btn.configure(state="disabled", text="Processing...")
        self.update_idletasks()

        if self.is_patient_user and not self.is_edit:
            patient_id = self.current_user.get("linked_patient_id")
            if not patient_id:
                self._show_error("Booking error: No patient profile is linked to your account.")
                self.save_btn.configure(state="normal", text="✓ Confirm & Book Appointment")
                return
            status = STATUS_PENDING
        else:
            patient_choice = self.patient_menu.get().strip() if self.patient_menu else ""
            patient_id = self.patient_id_map.get(patient_choice)
            if not patient_id:
                self._show_error("Please select a valid patient from the dropdown.")
                self.save_btn.configure(state="normal", text="✓ Save Changes" if self.is_edit else "✓ Confirm & Book Appointment")
                return
            status = self.status_menu.get().strip() if self.status_menu else "Confirmed"

        doctor_choice = self.doctor_menu.get().strip() if hasattr(self, "doctor_menu") and self.doctor_menu else ""
        doctor_id = self.doctor_id_map.get(doctor_choice)

        if not doctor_id:
            self._show_error("Please select a valid doctor from the dropdown.")
            self.save_btn.configure(state="normal", text="✓ Save Changes" if self.is_edit else "✓ Confirm & Book Appointment")
            return

        rating_val = None
        if self.is_edit and self.rating_menu is not None:
            rating_choice = self.rating_menu.get()
            if rating_choice and rating_choice != "None":
                try:
                    rating_val = int(rating_choice[0])
                except (ValueError, IndexError):
                    rating_val = None

        data = {
            "appointment_code": self.code_entry.get().strip(),
            "patient_id": int(patient_id),
            "doctor_id": int(doctor_id),
            "appointment_date": self.date_entry.get().strip(),
            "time_slot": self.slot_menu.get().strip(),
            "reason": self.reason_entry.get().strip(),
            "priority": self.priority_menu.get().strip(),
            "status": status,
            "satisfaction_rating": rating_val,
            "notes": self.notes_entry.get().strip(),
        }

        new_appointment_id = None
        if self.is_edit:
            # Retain or resolve internal primary key throughout the edit workflow
            if self.appointment_id is None:
                code_to_try = self.code_entry.get().strip()
                if code_to_try:
                    rec = get_appointment_by_code(code_to_try)
                    if rec:
                        self.appointment_id = rec["id"]

            if self.appointment_id is None:
                self._show_error("Appointment ID None not found.")
                self.save_btn.configure(state="normal", text="✓ Save Changes" if self.is_edit else "✓ Confirm & Book Appointment")
                return

            success, message = update_appointment(self.appointment_id, data, user=self.current_user)
        else:
            success, message, new_appointment_id = create_appointment(data, user=self.current_user)

        if success:
            master_window = self.master
            on_succ = self.on_success
            self.destroy()
            if on_succ:
                on_succ(message)
            # Show appointment confirmation dialog for newly booked appointments
            if not self.is_edit and new_appointment_id:
                try:
                    top_win = master_window.winfo_toplevel() if hasattr(master_window, "winfo_toplevel") else master_window
                    AppointmentConfirmationModal(top_win, appointment_id=new_appointment_id)
                except Exception as ex:
                    print(f"Error opening confirmation modal: {ex}")
        else:
            self._show_error(message)
            self.save_btn.configure(state="normal", text="✓ Save Changes" if self.is_edit else "✓ Confirm & Book Appointment")


class ConfirmAppointmentActionModal(ctk.CTkToplevel):
    """Confirmation modal dialog for cancelling or deleting an appointment."""

    def __init__(
        self,
        master,
        appointment_row: Dict,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.appointment_row = appointment_row
        self.appointment_id = appointment_row["id"]
        self.appointment_code = appointment_row["appointment_code"]
        self.on_success = on_success

        self.title("Confirm Appointment Action")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Responsive geometry
        self._apply_responsive_geometry(master)

        self._build_ui()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda event: self.destroy())

        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal adaptively on screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(500, int((sw - 40) / scaling))
        target_h = min(290, int((sh - 90) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct dialog layout with action choices."""
        pad_frame = ctk.CTkFrame(self, fg_color="transparent")
        pad_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Warning Header
        hdr = ctk.CTkLabel(
            pad_frame,
            text=f"⚠️ Cancel or Delete Appointment?",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#F59E0B",
            anchor="w",
        )
        hdr.pack(fill="x", pady=(0, 4))

        # Details
        pat_name = self.appointment_row.get("patient_name", "")
        doc_name = self.appointment_row.get("doctor_name", "")
        slot = f"{self.appointment_row.get('appointment_date', '')} at {self.appointment_row.get('time_slot', '')}"

        info = ctk.CTkLabel(
            pad_frame,
            text=f"Appointment: {self.appointment_code}  |  {slot}\nPatient: {pat_name}  |  Doctor: {doc_name}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            justify="left",
            anchor="w",
        )
        info.pack(fill="x", pady=(0, 6))

        # Explanation
        tip_text = (
            "💡 TQM Clinical Recommendation:\n"
            "• 'Cancel Appointment': Marks the consultation Cancelled and immediately frees the doctor's slot for other patients.\n"
            "• 'Delete Permanently': Removes the appointment record entirely from the database."
        )
        tip_lbl = ctk.CTkLabel(
            pad_frame,
            text=tip_text,
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            justify="left",
            wraplength=440,
        )
        tip_lbl.pack(fill="x", pady=(2, 12))

        # Action Buttons in footer
        btn_box = ctk.CTkFrame(pad_frame, fg_color="transparent")
        btn_box.pack(fill="x", side="bottom")

        cancel_btn = ctk.CTkButton(
            btn_box,
            text="Dismiss",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=85,
            height=32,
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        cancel_appt_btn = ctk.CTkButton(
            btn_box,
            text="📁 Cancel Appointment",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D97706",
            hover_color="#B45309",
            height=32,
            command=self._do_cancel,
        )
        cancel_appt_btn.pack(side="right", padx=(8, 0))

        delete_btn = ctk.CTkButton(
            btn_box,
            text="🗑️ Delete Permanently",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=32,
            command=self._do_delete,
        )
        delete_btn.pack(side="right")

    def _do_cancel(self) -> None:
        """Cancel appointment and free slot."""
        success, message = cancel_appointment(self.appointment_id)
        self.destroy()
        if self.on_success:
            self.on_success(message if success else f"Error: {message}")

    def _do_delete(self) -> None:
        """Permanently delete appointment."""
        success, message = delete_appointment(self.appointment_id)
        self.destroy()
        if self.on_success:
            self.on_success(message if success else f"Error: {message}")


class AppointmentConfirmationModal(ctk.CTkToplevel):
    """Post-booking confirmation card displaying appointment reference, consultation fee, and patient instructions."""

    def __init__(self, master, appointment_id: int, on_close: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.appointment_id = appointment_id
        self.on_close = on_close
        self.details = get_appointment_confirmation_details(appointment_id) or {}

        code = self.details.get("appointment_code", "APT-XXXX")
        self.title(f"Appointment Confirmed — {code}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_ui()

        self.bind("<Escape>", lambda event: self._close())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Position confirmation dialog adaptively on screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(560, int((sw - 40) / scaling))
        target_h = min(480, int((sh - 80) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct presentation-ready confirmation receipt card."""
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Header Banner
        header = ctk.CTkFrame(pad, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        app_status = str(self.details.get("status", "Confirmed")).strip()
        is_pending = (app_status == "Pending")
        header_title = "⏳ Appointment Request Submitted" if is_pending else "✅ Appointment Confirmed & Registered"
        header_sub = "Your consultation request has been submitted and is pending staff review." if is_pending else "Official outpatient consultation slip generated with clinical quality tracking."
        title_color = ("#D97706", "#FBBF24") if is_pending else ("#16A34A", "#22C55E")

        title_lbl = ctk.CTkLabel(
            header,
            text=header_title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=title_color,
            anchor="w",
        )
        title_lbl.pack(fill="x")

        sub_lbl = ctk.CTkLabel(
            header,
            text=header_sub,
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        sub_lbl.pack(fill="x")

        # 2. Key Summary Card
        card = ctk.CTkFrame(
            pad,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#0284C7", "#06B6D4"),
            corner_radius=10,
        )
        card.pack(fill="x", pady=(0, 12), ipady=8)

        # Reference & Status Pills Header
        pill_row = ctk.CTkFrame(card, fg_color="transparent")
        pill_row.pack(fill="x", padx=16, pady=(8, 10))

        code_pill = ctk.CTkLabel(
            pill_row,
            text=f"Ref: {self.details.get('appointment_code', '')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E0F2FE", "#0C2E4E"),
            text_color=("#0284C7", "#38BDF8"),
            corner_radius=6,
            padx=10,
            pady=4,
        )
        code_pill.pack(side="left")

        status_pill = ctk.CTkLabel(
            pill_row,
            text=f"● {app_status}",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#FEF3C7", "#451A03") if is_pending else ("#DCFCE7", "#064E3B"),
            text_color=("#B45309", "#FBBF24") if is_pending else ("#15803D", "#34D399"),
            corner_radius=6,
            padx=10,
            pady=4,
        )
        status_pill.pack(side="left", padx=8)

        fee = float(self.details.get("consultation_fee", 500.0))
        fee_pill = ctk.CTkLabel(
            pill_row,
            text=f"Fee: Rs. {fee:.2f}",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#FEF3C7", "#451A03"),
            text_color=("#B45309", "#FBBF24"),
            corner_radius=6,
            padx=10,
            pady=4,
        )
        fee_pill.pack(side="right")

        # Detail Rows
        details_grid = ctk.CTkFrame(card, fg_color="transparent")
        details_grid.pack(fill="x", padx=16, pady=(0, 6))
        details_grid.grid_columnconfigure((0, 1), weight=1)

        # Patient Info
        p_name = self.details.get("patient_name", "")
        p_code = self.details.get("patient_code", "")
        p_phone = self.details.get("patient_phone", "")
        p_box = ctk.CTkFrame(details_grid, fg_color=("#F8FAFC", "#131D33"), corner_radius=6)
        p_box.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="nsew")
        ctk.CTkLabel(p_box, text="👤 PATIENT", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=10, pady=(6, 1))
        ctk.CTkLabel(p_box, text=f"{p_name} ({p_code})", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#0F172A", "#F8FAFC"), anchor="w").pack(fill="x", padx=10)
        ctk.CTkLabel(p_box, text=f"Phone: {p_phone}", font=ctk.CTkFont(size=10), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=10, pady=(1, 6))

        # Doctor Info
        d_name = self.details.get("doctor_name", "")
        d_spec = self.details.get("specialization", "")
        d_room = self.details.get("room_number", "")
        d_box = ctk.CTkFrame(details_grid, fg_color=("#F8FAFC", "#131D33"), corner_radius=6)
        d_box.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="nsew")
        ctk.CTkLabel(d_box, text="👨‍⚕️ PHYSICIAN", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=10, pady=(6, 1))
        ctk.CTkLabel(d_box, text=f"{d_name}", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#0F172A", "#F8FAFC"), anchor="w").pack(fill="x", padx=10)
        ctk.CTkLabel(d_box, text=f"{d_spec} • OPD Room: {d_room}", font=ctk.CTkFont(size=10), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=10, pady=(1, 6))

        # Date & Slot Bar
        time_bar = ctk.CTkFrame(card, fg_color=("#F1F5F9", "#16233E"), corner_radius=6)
        time_bar.pack(fill="x", padx=16, pady=(4, 8))
        appt_date = self.details.get("appointment_date", "")
        time_slot = self.details.get("time_slot", "")
        reason = self.details.get("reason", "Consultation")
        ctk.CTkLabel(
            time_bar,
            text=f"🗓 Scheduled: {appt_date} at {time_slot}   |   Reason: {reason}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            padx=10,
            pady=6,
            anchor="w",
        ).pack(fill="x")

        # 3. Patient Guidelines Panel
        inst_card = ctk.CTkFrame(
            pad,
            fg_color=("#F8FAFC", "#0C1527"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        inst_card.pack(fill="x", pady=(0, 14), padx=2)

        ctk.CTkLabel(
            inst_card,
            text="📋 Patient Guidelines & Reporting Instructions:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 4))

        instructions = self.details.get("instructions", [])
        for i, text in enumerate(instructions, 1):
            ctk.CTkLabel(
                inst_card,
                text=f" {i}. {text}",
                font=ctk.CTkFont(size=10),
                text_color=("#475569", "#94A3B8"),
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=12, pady=1)
        ctk.CTkLabel(inst_card, text="", height=4).pack()

        # 4. Footer Actions
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        close_btn = ctk.CTkButton(
            footer,
            text="✓ Done / Close",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=34,
            width=120,
            command=self._close,
        )
        close_btn.pack(side="right")

    def _close(self) -> None:
        """Close dialog and trigger callback."""
        self.destroy()
        if self.on_close:
            self.on_close()


class PostVisitFeedbackModal(ctk.CTkToplevel):
    """Post-visit patient satisfaction (CSAT) rating and feedback submission dialog.
    
    Adheres to TQM Q08 requirements: feedback is only collected after consultation is Completed.
    """

    def __init__(
        self,
        master,
        appointment_row: Dict,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.appointment_row = appointment_row
        self.appointment_id = appointment_row["id"]
        self.on_success = on_success

        code = appointment_row.get("appointment_code", "APT-XXXX")
        self.title(f"Post-Visit Quality Feedback — {code}")
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
        w, h = 480, 420
        x = max(0, (sw - w) // 2)
        y = max(10, (sh - h) // 2 - 20)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=22, pady=18)

        # Header
        t_lbl = ctk.CTkLabel(
            pad,
            text="⭐ Patient Consultation Feedback (CSAT)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
            anchor="w",
        )
        t_lbl.pack(fill="x")

        a = self.appointment_row
        meta_txt = f"Consultation Ref: {a.get('appointment_code', '')}  |  Date: {a.get('appointment_date', '')} {a.get('time_slot', '')}"
        m_lbl = ctk.CTkLabel(pad, text=meta_txt, font=ctk.CTkFont(size=11), text_color=("#64748B", "#94A3B8"), anchor="w")
        m_lbl.pack(fill="x", pady=(2, 10))

        doc_txt = f"Physician: {a.get('doctor_name', 'Physician')} ({a.get('specialization', '')})"
        ctk.CTkLabel(pad, text=doc_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#0F172A", "#F8FAFC"), anchor="w").pack(fill="x", pady=(0, 10))

        # Rating selection
        ctk.CTkLabel(pad, text="Overall Consultation Satisfaction Rating *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 4))

        self.rating_options = [
            "5 ★ — Excellent (Highly Satisfied)",
            "4 ★ — Good (Satisfied)",
            "3 ★ — Average (Neutral Experience)",
            "2 ★ — Poor (Dissatisfied with Care)",
            "1 ★ — Very Poor (Service Defect / Complaint)",
        ]
        self.rating_menu = ctk.CTkOptionMenu(pad, values=self.rating_options, height=34)
        self.rating_menu.set(self.rating_options[0])
        self.rating_menu.pack(fill="x", pady=(0, 12))

        # Feedback Comments / Notes
        ctk.CTkLabel(pad, text="Feedback Comments / Suggestions (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").pack(fill="x", pady=(0, 4))

        self.comments_entry = ctk.CTkEntry(
            pad,
            placeholder_text="e.g. Prompt diagnosis, courteous staff, minimal waiting time",
            height=34,
        )
        self.comments_entry.pack(fill="x", pady=(0, 12))

        # Error / Status message banner
        self.err_lbl = ctk.CTkLabel(pad, text="", font=ctk.CTkFont(size=11), text_color="#EF4444", anchor="w")
        self.err_lbl.pack(fill="x", pady=(0, 8))

        # Fixed Footer Buttons
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        close_btn = ctk.CTkButton(
            footer,
            text="Cancel",
            width=80,
            height=34,
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            command=self.destroy,
        )
        close_btn.pack(side="right", padx=(8, 0))

        self.submit_btn = ctk.CTkButton(
            footer,
            text="⭐ Submit Quality Feedback",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=34,
            command=self._do_submit,
        )
        self.submit_btn.pack(side="right")

    def _do_submit(self) -> None:
        self.err_lbl.configure(text="")
        choice = self.rating_menu.get()
        try:
            rating_val = int(choice[0])
        except (ValueError, IndexError):
            self.err_lbl.configure(text="Please select a valid rating.")
            return

        comments = self.comments_entry.get().strip()
        self.submit_btn.configure(state="disabled", text="Submitting...")
        self.update_idletasks()

        ok, msg = submit_visit_feedback(self.appointment_id, rating_val, comments)
        if ok:
            self.destroy()
            if self.on_success:
                self.on_success(msg)
        else:
            self.err_lbl.configure(text=msg)
            self.submit_btn.configure(state="normal", text="⭐ Submit Quality Feedback")
