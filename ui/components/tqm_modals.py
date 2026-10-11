"""Interactive modals for TQM Defect Logging and FMEA Risk Assessment.
Engineered with fixed footers, real-time RPN calculation, and responsive sizing.
"""
from typing import Callable, Dict, Optional
import customtkinter as ctk

from services.tqm_service import (
    DEFECT_CATEGORIES,
    DEFECT_SEVERITIES,
    DEFECT_STATUSES,
    add_fmea_record,
    calculate_rpn,
    get_next_defect_code,
    log_defect,
)


class LogDefectModal(ctk.CTkToplevel):
    """Modal dialog for logging outpatient incidents and operational defects."""

    def __init__(
        self,
        master,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_success = on_success

        self.title("Log Quality Defect / Incident")
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_header()
        self._build_fixed_footer()
        self._build_scrollable_form()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal adaptively on screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        target_w = min(540, int(sw * 0.85))
        target_h = min(460, int(sh * 0.80))
        pos_x = max(0, (sw - target_w) // 2)
        pos_y = max(10, (sh - target_h) // 2 - 25)
        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_header(self) -> None:
        """Fixed top header with icon and description."""
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            hdr,
            text="⚠️ Log Quality Defect / Incident",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text="Record Voice-of-Customer operational friction into SQLite checksheet.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(2, 0))

    def _build_fixed_footer(self) -> None:
        """Fixed bottom footer permanently visible on scaled displays."""
        footer = ctk.CTkFrame(self, fg_color=("#F8FAFC", "#1E202E"), height=54, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        box = ctk.CTkFrame(footer, fg_color="transparent")
        box.pack(side="right", padx=16, pady=10)

        ctk.CTkButton(
            box,
            text="Cancel",
            font=ctk.CTkFont(size=12),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=90,
            height=32,
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            box,
            text="Save Defect Log",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            width=135,
            height=32,
            command=self._on_save,
        ).pack(side="left")

    def _build_scrollable_form(self) -> None:
        """Scrollable form body for defect details."""
        self.form_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        # Defect Code
        code_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        code_row.pack(fill="x", pady=4)
        ctk.CTkLabel(code_row, text="Defect Code:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.code_entry = ctk.CTkEntry(code_row, height=30)
        self.code_entry.insert(0, get_next_defect_code())
        self.code_entry.pack(side="left", fill="x", expand=True)

        # Category
        cat_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        cat_row.pack(fill="x", pady=4)
        ctk.CTkLabel(cat_row, text="Category *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.cat_menu = ctk.CTkOptionMenu(cat_row, values=DEFECT_CATEGORIES, height=30)
        self.cat_menu.set(DEFECT_CATEGORIES[0])
        self.cat_menu.pack(side="left", fill="x", expand=True)

        # Severity
        sev_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        sev_row.pack(fill="x", pady=4)
        ctk.CTkLabel(sev_row, text="Severity *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.sev_menu = ctk.CTkOptionMenu(sev_row, values=DEFECT_SEVERITIES, height=30)
        self.sev_menu.set("Major")
        self.sev_menu.pack(side="left", fill="x", expand=True)

        # Reported By
        rep_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        rep_row.pack(fill="x", pady=4)
        ctk.CTkLabel(rep_row, text="Reported By *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.rep_entry = ctk.CTkEntry(rep_row, placeholder_text="e.g. Front Desk Operator", height=30)
        self.rep_entry.insert(0, "Front Desk Operator")
        self.rep_entry.pack(side="left", fill="x", expand=True)

        # Status
        st_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        st_row.pack(fill="x", pady=4)
        ctk.CTkLabel(st_row, text="Status *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.st_menu = ctk.CTkOptionMenu(st_row, values=DEFECT_STATUSES, height=30)
        self.st_menu.set("Logged")
        self.st_menu.pack(side="left", fill="x", expand=True)

        # Description
        desc_lbl = ctk.CTkLabel(self.form_frame, text="Description of Defect / Friction *:", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        desc_lbl.pack(fill="x", pady=(6, 2))
        self.desc_box = ctk.CTkTextbox(self.form_frame, height=70)
        self.desc_box.pack(fill="x", pady=(0, 6))

        # Inline Error label
        self.err_lbl = ctk.CTkLabel(self.form_frame, text="", text_color="#EF4444", font=ctk.CTkFont(size=11), anchor="w")
        self.err_lbl.pack(fill="x")

    def _on_save(self) -> None:
        """Validate and commit defect log."""
        data = {
            "defect_code": self.code_entry.get().strip(),
            "category": self.cat_menu.get().strip(),
            "severity": self.sev_menu.get().strip(),
            "reported_by": self.rep_entry.get().strip(),
            "resolution_status": self.st_menu.get().strip(),
            "description": self.desc_box.get("1.0", "end").strip(),
        }

        success, msg, _ = log_defect(data)
        if success:
            if self.on_success:
                self.on_success(msg)
            self.destroy()
        else:
            self.err_lbl.configure(text=f"⚠️ {msg}")


class AddFMEAModal(ctk.CTkToplevel):
    """Modal dialog for logging FMEA failure modes with real-time RPN calculation."""

    def __init__(
        self,
        master,
        on_success: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_success = on_success

        self.title("Add FMEA Failure Mode & Mitigation")
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_header()
        self._build_fixed_footer()
        self._build_scrollable_form()

        # Keyboard shortcuts
        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal adaptively on screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        target_w = min(580, int(sw * 0.88))
        target_h = min(500, int(sh * 0.85))
        pos_x = max(0, (sw - target_w) // 2)
        pos_y = max(10, (sh - target_h) // 2 - 25)
        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_header(self) -> None:
        """Top header banner."""
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 6))

        ctk.CTkLabel(
            hdr,
            text="📋 Add FMEA Failure Mode Assessment",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#38BDF8"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text="RPN = Severity (S) × Occurrence (O) × Detection (D). Ratings scale from 1 to 10.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(2, 0))

    def _build_fixed_footer(self) -> None:
        """Fixed bottom footer."""
        footer = ctk.CTkFrame(self, fg_color=("#F8FAFC", "#1E202E"), height=54, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

        box = ctk.CTkFrame(footer, fg_color="transparent")
        box.pack(side="right", padx=16, pady=10)

        ctk.CTkButton(
            box,
            text="Cancel",
            font=ctk.CTkFont(size=12),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=90,
            height=32,
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            box,
            text="Save FMEA Record",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            width=145,
            height=32,
            command=self._on_save,
        ).pack(side="left")

    def _build_scrollable_form(self) -> None:
        """Scrollable form body with real-time RPN calculations."""
        self.form_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        # Process Step
        p_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        p_row.pack(fill="x", pady=4)
        ctk.CTkLabel(p_row, text="Process Step *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.step_entry = ctk.CTkEntry(p_row, placeholder_text="e.g. Slot Reservation", height=30)
        self.step_entry.pack(side="left", fill="x", expand=True)

        # Failure Mode
        f_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        f_row.pack(fill="x", pady=4)
        ctk.CTkLabel(f_row, text="Failure Mode *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.mode_entry = ctk.CTkEntry(f_row, placeholder_text="e.g. Double booking doctor slot", height=30)
        self.mode_entry.pack(side="left", fill="x", expand=True)

        # Potential Cause & Effect
        eff_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        eff_row.pack(fill="x", pady=4)
        ctk.CTkLabel(eff_row, text="Potential Effect:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.effect_entry = ctk.CTkEntry(eff_row, placeholder_text="e.g. Patient wait time exceeds 60m", height=30)
        self.effect_entry.pack(side="left", fill="x", expand=True)

        cause_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        cause_row.pack(fill="x", pady=4)
        ctk.CTkLabel(cause_row, text="Root Cause:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.cause_entry = ctk.CTkEntry(cause_row, placeholder_text="e.g. Unchecked concurrent bookings", height=30)
        self.cause_entry.pack(side="left", fill="x", expand=True)

        # Pre-Mitigation Ratings Box (S, O, D -> RPN)
        pre_box = ctk.CTkFrame(self.form_frame, fg_color=("#F8FAFC", "#26293B"), corner_radius=8)
        pre_box.pack(fill="x", pady=8, padx=2)

        ctk.CTkLabel(pre_box, text="Initial Assessment (Pre-Mitigation):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        ratings_row = ctk.CTkFrame(pre_box, fg_color="transparent")
        ratings_row.pack(fill="x", padx=12, pady=(0, 8))

        scale_vals = [str(i) for i in range(1, 11)]

        ctk.CTkLabel(ratings_row, text="S:").pack(side="left", padx=(0, 2))
        self.s_menu = ctk.CTkOptionMenu(ratings_row, values=scale_vals, width=54, height=28, command=lambda _: self._update_rpn_labels())
        self.s_menu.set("7")
        self.s_menu.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(ratings_row, text="O:").pack(side="left", padx=(0, 2))
        self.o_menu = ctk.CTkOptionMenu(ratings_row, values=scale_vals, width=54, height=28, command=lambda _: self._update_rpn_labels())
        self.o_menu.set("6")
        self.o_menu.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(ratings_row, text="D:").pack(side="left", padx=(0, 2))
        self.d_menu = ctk.CTkOptionMenu(ratings_row, values=scale_vals, width=54, height=28, command=lambda _: self._update_rpn_labels())
        self.d_menu.set("5")
        self.d_menu.pack(side="left", padx=(0, 12))

        self.rpn_badge = ctk.CTkLabel(
            ratings_row,
            text="Initial RPN: 210",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#FEE2E2", "#7F1D1D"),
            text_color=("#DC2626", "#FCA5A5"),
            corner_radius=6,
            padx=10,
            height=28,
        )
        self.rpn_badge.pack(side="left")

        # Mitigation Action
        act_row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        act_row.pack(fill="x", pady=4)
        ctk.CTkLabel(act_row, text="Mitigation Action *:", font=ctk.CTkFont(size=12, weight="bold"), width=120, anchor="w").pack(side="left")
        self.act_entry = ctk.CTkEntry(act_row, placeholder_text="e.g. SQLite partial unique index + validation lock", height=30)
        self.act_entry.pack(side="left", fill="x", expand=True)

        # Target Ratings Box (Target S, O, D -> Target RPN)
        target_box = ctk.CTkFrame(self.form_frame, fg_color=("#F8FAFC", "#26293B"), corner_radius=8)
        target_box.pack(fill="x", pady=8, padx=2)

        ctk.CTkLabel(target_box, text="Post-Mitigation Target:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        target_row = ctk.CTkFrame(target_box, fg_color="transparent")
        target_row.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(target_row, text="Target S:").pack(side="left", padx=(0, 2))
        self.ts_menu = ctk.CTkOptionMenu(target_row, values=scale_vals, width=54, height=28, command=lambda _: self._update_rpn_labels())
        self.ts_menu.set("7")
        self.ts_menu.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(target_row, text="Target O:").pack(side="left", padx=(0, 2))
        self.to_menu = ctk.CTkOptionMenu(target_row, values=scale_vals, width=54, height=28, command=lambda _: self._update_rpn_labels())
        self.to_menu.set("1")
        self.to_menu.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(target_row, text="Target D:").pack(side="left", padx=(0, 2))
        self.td_menu = ctk.CTkOptionMenu(target_row, values=scale_vals, width=54, height=28, command=lambda _: self._update_rpn_labels())
        self.td_menu.set("2")
        self.td_menu.pack(side="left", padx=(0, 12))

        self.target_rpn_badge = ctk.CTkLabel(
            target_row,
            text="Target RPN: 14",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#DCFCE7", "#14532D"),
            text_color=("#15803D", "#4ADE80"),
            corner_radius=6,
            padx=10,
            height=28,
        )
        self.target_rpn_badge.pack(side="left")

        # Error label
        self.err_lbl = ctk.CTkLabel(self.form_frame, text="", text_color="#EF4444", font=ctk.CTkFont(size=11), anchor="w")
        self.err_lbl.pack(fill="x")

        self._update_rpn_labels()

    def _update_rpn_labels(self) -> None:
        """Calculate and update RPN badges in real time."""
        try:
            s = int(self.s_menu.get())
            o = int(self.o_menu.get())
            d = int(self.d_menu.get())
            rpn = calculate_rpn(s, o, d)
            self.rpn_badge.configure(text=f"Initial RPN: {rpn}")

            ts = int(self.ts_menu.get())
            to = int(self.to_menu.get())
            td = int(self.td_menu.get())
            tr = calculate_rpn(ts, to, td)
            reduction = round(((rpn - tr) / rpn) * 100) if rpn > 0 else 0
            self.target_rpn_badge.configure(text=f"Target RPN: {tr} (-{reduction}%)")
        except Exception:
            pass

    def _on_save(self) -> None:
        """Validate and commit FMEA record."""
        data = {
            "process_step": self.step_entry.get().strip(),
            "failure_mode": self.mode_entry.get().strip(),
            "failure_effect": self.effect_entry.get().strip(),
            "potential_cause": self.cause_entry.get().strip(),
            "severity_s": self.s_menu.get(),
            "occurrence_o": self.o_menu.get(),
            "detection_d": self.d_menu.get(),
            "mitigation_action": self.act_entry.get().strip(),
            "target_severity": self.ts_menu.get(),
            "target_occurrence": self.to_menu.get(),
            "target_detection": self.td_menu.get(),
        }

        success, msg, _ = add_fmea_record(data)
        if success:
            if self.on_success:
                self.on_success(msg)
            self.destroy()
        else:
            self.err_lbl.configure(text=f"⚠️ {msg}")
