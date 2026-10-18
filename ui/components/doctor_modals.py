"""Interactive modal dialogs for Doctor Registration, Edit, and Confirmation workflows.
Engineered with fixed footers and responsive scrollable forms for any screen size or DPI scaling.
"""
import customtkinter as ctk
from typing import Callable, Dict, Optional

from config.constants import DOCTOR_STATUSES, SPECIALIZATIONS
from services.doctor_service import (
    archive_doctor,
    create_doctor,
    delete_doctor,
    get_doctor_appointment_count,
    get_next_doctor_code,
    update_doctor,
)


class DoctorFormModal(ctk.CTkToplevel):
    """Modal dialog for creating or updating a doctor record with a fixed footer and scrollable form."""

    def __init__(
        self,
        master,
        doctor_data: Optional[Dict] = None,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.doctor_data = doctor_data
        self.is_edit = doctor_data is not None
        self.doctor_id = doctor_data.get("id") if self.is_edit else None
        self.on_success = on_success

        # Window title & properties
        title_text = f"Edit Doctor: {doctor_data.get('doctor_code', '')}" if self.is_edit else "Register New Physician"
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

        title = "✏️ Edit Physician Details" if self.is_edit else "➕ Register Medical Staff"
        sub = "Update physician credentials, department, and fees." if self.is_edit else "Register a new medical specialist into the hospital SQLite database."

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
            text="✓ Save Doctor Record" if self.is_edit else "✓ Register Doctor",
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

        d = self.doctor_data or {}

        # Row 0: Doctor Code & Availability Status
        ctk.CTkLabel(self.form_scroll, text="Doctor Code *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Availability Status *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=1, padx=8, pady=(4, 1), sticky="w")

        default_code = d.get("doctor_code") or get_next_doctor_code()
        self.code_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. DOC-2011", height=32)
        self.code_entry.insert(0, default_code)
        self.code_entry.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.status_menu = ctk.CTkOptionMenu(self.form_scroll, values=DOCTOR_STATUSES, height=32)
        self.status_menu.set(d.get("status") or "Available")
        self.status_menu.grid(row=1, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 2: First Name & Last Name
        ctk.CTkLabel(self.form_scroll, text="First Name (with prefix) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Last Name *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=1, padx=8, pady=(4, 1), sticky="w")

        self.fname_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Dr. Rajesh", height=32)
        if d.get("first_name"):
            self.fname_entry.insert(0, d["first_name"])
        self.fname_entry.grid(row=3, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.lname_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Kapoor", height=32)
        if d.get("last_name"):
            self.lname_entry.insert(0, d["last_name"])
        self.lname_entry.grid(row=3, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 4: Specialization & Consultation Fee
        ctk.CTkLabel(self.form_scroll, text="Clinical Specialization *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=4, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Consultation Fee (INR) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=4, column=1, padx=8, pady=(4, 1), sticky="w")

        self.spec_menu = ctk.CTkOptionMenu(self.form_scroll, values=SPECIALIZATIONS, height=32)
        self.spec_menu.set(d.get("specialization") or "Cardiology")
        self.spec_menu.grid(row=5, column=0, padx=8, pady=(0, 6), sticky="ew")

        default_fee = str(d.get("consultation_fee", "600.0"))
        self.fee_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. 600.0", height=32)
        self.fee_entry.insert(0, default_fee)
        self.fee_entry.grid(row=5, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 6: Phone & Email
        ctk.CTkLabel(self.form_scroll, text="Contact Phone *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=6, column=0, padx=8, pady=(4, 1), sticky="w")
        ctk.CTkLabel(self.form_scroll, text="Official Email Address *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=6, column=1, padx=8, pady=(4, 1), sticky="w")

        self.phone_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. +91 98111 22011", height=32)
        if d.get("phone"):
            self.phone_entry.insert(0, d["phone"])
        self.phone_entry.grid(row=7, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.email_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. rajesh.k@hospital.demo", height=32)
        if d.get("email"):
            self.email_entry.insert(0, d["email"])
        self.email_entry.grid(row=7, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Row 8: Room / OPD Number
        ctk.CTkLabel(self.form_scroll, text="Consultation Room / OPD Number *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=8, column=0, columnspan=2, padx=8, pady=(4, 1), sticky="w")
        self.room_entry = ctk.CTkEntry(self.form_scroll, placeholder_text="e.g. Cardio-205 or Room 102", height=32)
        if d.get("room_number"):
            self.room_entry.insert(0, d["room_number"])
        self.room_entry.grid(row=9, column=0, columnspan=2, padx=8, pady=(0, 12), sticky="ew")

    def _setup_event_bindings(self) -> None:
        """Bind mouse wheel scrolling and keyboard shortcuts."""
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Control-s>", lambda event: self._on_save())
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
            "doctor_code": self.code_entry.get().strip(),
            "first_name": self.fname_entry.get().strip(),
            "last_name": self.lname_entry.get().strip(),
            "specialization": self.spec_menu.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "consultation_fee": self.fee_entry.get().strip(),
            "room_number": self.room_entry.get().strip(),
            "status": self.status_menu.get().strip(),
        }

        if self.is_edit:
            success, message = update_doctor(self.doctor_id, data)
        else:
            success, message, _ = create_doctor(data)

        if success:
            self.destroy()
            if self.on_success:
                self.on_success(message)
        else:
            self._show_error(message)


class ConfirmDoctorActionModal(ctk.CTkToplevel):
    """Confirmation modal dialog for setting a doctor On Leave or deleting them permanently."""

    def __init__(
        self,
        master,
        doctor_row: Dict,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.doctor_row = doctor_row
        self.doctor_id = doctor_row["id"]
        self.doctor_code = doctor_row["doctor_code"]
        self.doctor_name = f"{doctor_row['first_name']} {doctor_row['last_name']}"
        self.on_success = on_success

        # Check existing appointments linked to this doctor
        self.appt_count = get_doctor_appointment_count(self.doctor_id)

        self.title("Confirm Doctor Action")
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
        target_h = min(300, int((sh - 90) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct dialog layout with clinical safeguard indicators."""
        pad_frame = ctk.CTkFrame(self, fg_color="transparent")
        pad_frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Warning Header
        hdr = ctk.CTkLabel(
            pad_frame,
            text=f"⚠️ Deactivate or Remove Doctor?",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#F59E0B",
            anchor="w",
        )
        hdr.pack(fill="x", pady=(0, 4))

        # Doctor Details
        info = ctk.CTkLabel(
            pad_frame,
            text=f"Physician: {self.doctor_name}  [{self.doctor_code}] — {self.doctor_row.get('specialization', '')}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            anchor="w",
        )
        info.pack(fill="x", pady=(0, 6))

        # Appointment Warning if applicable
        if self.appt_count > 0:
            warning_text = (
                f"🛡️ Clinical Integrity Rule: This doctor currently has {self.appt_count} active/scheduled appointment(s).\n"
                f"Database referential integrity (RESTRICT) prevents deleting doctors with existing patient bookings.\n"
                f"Please choose 'Mark On Leave' to make this physician unavailable."
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
        else:
            safe_text = "This doctor has 0 appointments scheduled. You can safely mark them 'On Leave' or delete them permanently."
            safe_lbl = ctk.CTkLabel(
                pad_frame,
                text=safe_text,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                justify="left",
                wraplength=440,
            )
            safe_lbl.pack(fill="x", pady=(2, 6))

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
            text="📁 Mark On Leave",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D97706",
            hover_color="#B45309",
            height=32,
            command=self._do_archive,
        )
        archive_btn.pack(side="right", padx=(8, 0))

        # Permanent Delete button
        del_btn_state = "normal" if self.appt_count == 0 else "disabled"
        del_fg = "#DC2626" if self.appt_count == 0 else ("#E2E8F0", "#334155")
        delete_btn = ctk.CTkButton(
            btn_box,
            text="🗑️ Delete Permanently",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=del_fg,
            hover_color="#B91C1C",
            state=del_btn_state,
            height=32,
            command=self._do_delete,
        )
        delete_btn.pack(side="right")

    def _do_archive(self) -> None:
        """Mark doctor On Leave."""
        success, message = archive_doctor(self.doctor_id)
        self.destroy()
        if self.on_success:
            self.on_success(message if success else f"Error: {message}")

    def _do_delete(self) -> None:
        """Permanently delete doctor."""
        success, message = delete_doctor(self.doctor_id)
        self.destroy()
        if self.on_success:
            self.on_success(message if success else f"Error: {message}")
