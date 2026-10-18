"""Interactive modal dialogs for Patient Add, Edit, and Confirmation workflows.
Engineered with fixed footers and responsive scrollable forms for any screen size or DPI scaling.
"""
import customtkinter as ctk
from typing import Callable, Dict, Optional

from config.constants import BLOOD_GROUPS, PATIENT_STATUSES
from services.patient_service import (
    archive_patient,
    create_patient,
    delete_patient,
    get_next_patient_code,
    get_patient_appointment_count,
    update_patient,
)


class PatientFormModal(ctk.CTkToplevel):
    """Modal dialog for creating or updating a patient record with a fixed footer and scrollable form."""

    def __init__(
        self,
        master,
        patient_data: Optional[Dict] = None,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.patient_data = patient_data
        self.is_edit = patient_data is not None
        self.patient_id = patient_data.get("id") if self.is_edit else None
        self.on_success = on_success

        # Window title & properties
        title_text = f"Edit Patient: {patient_data.get('patient_code', '')}" if self.is_edit else "Register New Patient"
        self.title(title_text)
        self.transient(master)
        self.grab_set()

        # Responsive Geometry tailored to 720p / 1080p and high-DPI scaling
        self._apply_responsive_geometry(master)

        # 1. FIXED HEADER (Packed TOP)
        self._build_header()

        # 2. FIXED FOOTER (Packed BOTTOM FIRST so it is permanently visible)
        self._build_fixed_footer()

        # 3. SCROLLABLE FORM BODY (Packed in the remaining middle area)
        self._build_scrollable_form()

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

        # Calculate maximum safe dimensions taking 150% scaling into account
        # On 1280x720 with 1.5 scaling: 720 - 90 = 630 physical -> 630 / 1.5 = 420 unscaled
        max_unscaled_h = int((sh - 90) / scaling)
        target_h = min(440, max_unscaled_h)
        target_w = min(580, int((sw - 40) / scaling))

        # Centered physical coordinates
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

        title = "✏️ Edit Patient Record" if self.is_edit else "➕ Register New Patient"
        sub = "Update patient clinical and contact details." if self.is_edit else "Fill in patient demographics to save in the SQLite database."

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

        save_btn = ctk.CTkButton(
            self.footer_frame,
            text="✓ Save Patient Record" if self.is_edit else "✓ Register Patient",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=32,
            command=self._on_save,
        )
        save_btn.pack(side="right", pady=10)

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
        self.form_scroll.grid_columnconfigure((0, 1), weight=1, uniform="form_col")

        d = self.patient_data or {}

        # Row 0: Patient Code & Status
        ctk.CTkLabel(self.form_scroll, text="Patient Code *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Status *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=1, padx=8, pady=(4, 1), sticky="w")

        default_code = d.get("patient_code") or get_next_patient_code()
        self.code_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. PAT-1026", height=32)
        self.code_entry.insert(0, default_code)
        self.code_entry.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.status_menu = ctk.CTkOptionMenu(self.form_scroll, values=PATIENT_STATUSES, height=32)
        self.status_menu.set(d.get("status") or "Active")
        self.status_menu.grid(row=1, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 2: First Name & Last Name
        ctk.CTkLabel(self.form_scroll, text="First Name *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Last Name *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=1, padx=8, pady=(4, 1), sticky="w")

        self.fname_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Ramesh", height=32)
        if d.get("first_name"):
            self.fname_entry.insert(0, d["first_name"])
        self.fname_entry.grid(row=3, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.lname_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Kumar", height=32)
        if d.get("last_name"):
            self.lname_entry.insert(0, d["last_name"])
        self.lname_entry.grid(row=3, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 4: Date of Birth & Gender
        ctk.CTkLabel(self.form_scroll, text="Date of Birth (YYYY-MM-DD) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=4, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Gender *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=4, column=1, padx=8, pady=(4, 1), sticky="w")

        self.dob_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="YYYY-MM-DD (e.g. 1995-05-15)", height=32)
        if d.get("dob"):
            self.dob_entry.insert(0, d["dob"])
        self.dob_entry.grid(row=5, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.gender_menu = ctk.CTkOptionMenu(self.form_scroll, values=["Male", "Female", "Other"], height=32)
        self.gender_menu.set(d.get("gender") or "Male")
        self.gender_menu.grid(row=5, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 6: Phone & Email
        ctk.CTkLabel(self.form_scroll, text="Contact Phone *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=6, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Email Address (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=6, column=1, padx=8, pady=(4, 1), sticky="w")

        self.phone_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. +91 98765 43210", height=32)
        if d.get("phone"):
            self.phone_entry.insert(0, d["phone"])
        self.phone_entry.grid(row=7, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.email_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. user@example.com", height=32)
        if d.get("email"):
            self.email_entry.insert(0, d["email"])
        self.email_entry.grid(row=7, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 8: Blood Group & Emergency Contact
        ctk.CTkLabel(self.form_scroll, text="Blood Group", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=8, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Emergency Contact Phone", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=8, column=1, padx=8, pady=(4, 1), sticky="w")

        self.blood_menu = ctk.CTkOptionMenu(self.form_scroll, values=[""] + BLOOD_GROUPS, height=32)
        self.blood_menu.set(d.get("blood_group") or "B+")
        self.blood_menu.grid(row=9, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.emg_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. +91 98111 22334", height=32)
        if d.get("emergency_contact"):
            self.emg_entry.insert(0, d["emergency_contact"])
        self.emg_entry.grid(row=9, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 10: Address
        ctk.CTkLabel(self.form_scroll, text="Residential Address (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=10, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")
        self.addr_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="House/Flat No, Street, City, Pin Code", height=32)
        if d.get("address"):
            self.addr_entry.insert(0, d["address"])
        self.addr_entry.grid(row=11, column=0, columnspan=2, padx=8, pady=(0, 12), sticky="ew")

    def _setup_event_bindings(self) -> None:
        """Bind mouse wheel scrolling across all child widgets and keyboard shortcuts."""
        # Keyboard shortcuts
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Control-s>", lambda event: self._on_save())

        # Recursively bind MouseWheel to scrollable canvas so wheel works over any entry or label
        self._bind_mousewheel_recursive(self.form_scroll)

    def _bind_mousewheel_recursive(self, widget) -> None:
        """Recursively attach mouse wheel scrolling handler."""
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
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
        """Gather inputs, run validation and persistence, and trigger callback."""
        self._clear_error()

        data = {
            "patient_code": self.code_entry.get().strip(),
            "first_name": self.fname_entry.get().strip(),
            "last_name": self.lname_entry.get().strip(),
            "dob": self.dob_entry.get().strip(),
            "gender": self.gender_menu.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "blood_group": self.blood_menu.get().strip(),
            "emergency_contact": self.emg_entry.get().strip(),
            "address": self.addr_entry.get().strip(),
            "status": self.status_menu.get().strip(),
        }

        if self.is_edit:
            success, message = update_patient(self.patient_id, data)
        else:
            success, message, _ = create_patient(data)

        if success:
            self.destroy()
            if self.on_success:
                self.on_success(message)
        else:
            self._show_error(message)


class ConfirmPatientActionModal(ctk.CTkToplevel):
    """Confirmation modal dialog for deleting or archiving a patient with screen-adaptive positioning."""

    def __init__(
        self,
        master,
        patient_row: Dict,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.patient_row = patient_row
        self.patient_id = patient_row["id"]
        self.patient_code = patient_row["patient_code"]
        self.patient_name = f"{patient_row['first_name']} {patient_row['last_name']}"
        self.on_success = on_success

        # Check existing appointments linked to this patient
        self.appt_count = get_patient_appointment_count(self.patient_id)

        self.title("Confirm Patient Action")
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

        target_w = min(490, int((sw - 40) / scaling))
        target_h = min(290, int((sh - 90) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct dialog layout with warning icon and action options."""
        pad_frame = ctk.CTkFrame(self, fg_color="transparent")
        pad_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Warning Header
        hdr = ctk.CTkLabel(
            pad_frame,
            text=f"⚠️ Remove or Archive Patient?",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#F59E0B",
            anchor="w",
        )
        hdr.pack(fill="x", pady=(0, 4))

        # Patient Details
        info = ctk.CTkLabel(
            pad_frame,
            text=f"Target: {self.patient_name}  [{self.patient_code}]",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            anchor="w",
        )
        info.pack(fill="x", pady=(0, 4))

        # Appointment Warning if applicable
        if self.appt_count > 0:
            warning_text = (
                f"Notice: This patient has {self.appt_count} appointment(s) in the hospital database.\n"
                f"Deleting permanently will cascade-delete their appointment history."
            )
            warn_lbl = ctk.CTkLabel(
                pad_frame,
                text=warning_text,
                font=ctk.CTkFont(size=11),
                text_color=("#DC2626", "#F87171"),
                justify="left",
                wraplength=440,
            )
            warn_lbl.pack(fill="x", pady=(2, 6))

        # TQM Safety Recommendation
        tqm_tip = (
            "💡 TQM Recommendation: Choose 'Archive Patient' to preserve clinical history "
            "for quality audits while marking the patient inactive."
        )
        tip_lbl = ctk.CTkLabel(
            pad_frame,
            text=tqm_tip,
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
            text="Cancel",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=85,
            height=32,
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        archive_btn = ctk.CTkButton(
            btn_box,
            text="📁 Archive Patient",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D97706",
            hover_color="#B45309",
            height=32,
            command=self._do_archive,
        )
        archive_btn.pack(side="right", padx=(8, 0))

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

    def _do_archive(self) -> None:
        """Perform soft archive action."""
        success, message = archive_patient(self.patient_id)
        self.destroy()
        if self.on_success:
            self.on_success(message if success else f"Error: {message}")

    def _do_delete(self) -> None:
        """Perform permanent delete action."""
        success, message = delete_patient(self.patient_id)
        self.destroy()
        if self.on_success:
            self.on_success(message if success else f"Error: {message}")
