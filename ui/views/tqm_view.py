"""TQM Quality Toolkit View for Hospital Management System — Q08.
Comprehensive quality engineering framework for BBAT104 Fundamentals of Total Quality Management.
Includes FMEA matrix with RPN calculation, SIPOC process mapping, CTQ tree,
Defect checksheet logging, Pareto distribution chart, Fishbone root-cause analysis,
and PDCA continuous-improvement workflow.
"""
from datetime import datetime
from typing import Dict, List, Optional
import customtkinter as ctk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from services.tqm_service import (
    DEFECT_CATEGORIES,
    DEFECT_SEVERITIES,
    DEFECT_STATUSES,
    export_defects_to_csv,
    get_ctq_tree_data,
    get_defect_logs,
    get_defect_pareto_data,
    get_fishbone_data,
    get_fmea_records,
    get_pdca_cycles_data,
    get_sipoc_data,
    update_defect_status,
)
from ui.components.tqm_modals import AddFMEAModal, LogDefectModal


class TQMView(ctk.CTkFrame):
    """Total Quality Management (TQM) Quality Toolkit view."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.active_figures: List[Figure] = []
        self.active_canvases: List[FigureCanvasTkAgg] = []
        self._notice_timer_id: Optional[str] = None

        self._build_header()
        self._build_notification_banner()
        self._build_tabview()

    def _build_header(self) -> None:
        """Header with TQM title, coursework metadata, and refresh button."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=24, pady=(20, 10))

        info_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        info_box.pack(side="left")

        title = ctk.CTkLabel(
            info_box,
            text="Total Quality Management (TQM) Quality Toolkit",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            info_box,
            text="Course: BBAT104 Fundamentals of TQM | Project Track: Q08 User Satisfaction Optimization.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # Academic Transparency Label
        badge_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        badge_box.pack(side="right")

        course_chip = ctk.CTkLabel(
            badge_box,
            text="🏷️ Academic Coursework Tools (BBAT104)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E2E8F0", "#26293B"),
            text_color=("#0284C7", "#38BDF8"),
            corner_radius=6,
            padx=10,
            height=30,
        )
        course_chip.pack(side="left", padx=(0, 8))

        refresh_btn = ctk.CTkButton(
            badge_box,
            text="🔄 Refresh Toolkit",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=30,
            width=120,
            corner_radius=6,
            command=self.refresh_all,
        )
        refresh_btn.pack(side="left")

    def _build_notification_banner(self) -> None:
        """Feedback toast/banner for immediate user notifications."""
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
        """Show temporary notification banner with cancellation of prior timers."""
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
        self.notice_banner.pack(fill="x", padx=24, pady=(0, 10), before=self.tabview)
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
        """Safely clean up active timers and matplotlib figures upon view destruction."""
        if hasattr(self, "_notice_timer_id") and self._notice_timer_id is not None:
            self.after_cancel(self._notice_timer_id)
            self._notice_timer_id = None
        self._close_active_figures()
        super().destroy()

    def _build_tabview(self) -> None:
        """Construct multi-tab container for all 6 TQM tools."""
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # 6 Core Quality Engineering Tabs
        self.tab_fmea = self.tabview.add("1. FMEA Risk Matrix (RPN)")
        self.tab_sipoc = self.tabview.add("2. SIPOC Process Map")
        self.tab_ctq = self.tabview.add("3. CTQ Quality Tree")
        self.tab_checksheet = self.tabview.add("4. Defect Checksheet Log")
        self.tab_pareto = self.tabview.add("5. Pareto & Root Cause (Fishbone)")
        self.tab_pdca = self.tabview.add("6. PDCA Improvement Cycles")

        self._render_fmea_tab()
        self._render_sipoc_tab()
        self._render_ctq_tab()
        self._render_checksheet_tab()
        self._render_pareto_tab()
        self._render_pdca_tab()

    def _get_theme_colors(self) -> Dict[str, str]:
        """Compute theme-adaptive colors for Matplotlib figures."""
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        return {
            "is_dark": is_dark,
            "bg": "#1E202E" if is_dark else "#FFFFFF",
            "text": "#F8FAFC" if is_dark else "#0F172A",
            "muted": "#94A3B8" if is_dark else "#64748B",
            "grid": "#334155" if is_dark else "#E2E8F0",
            "spine": "#334155" if is_dark else "#CBD5E1",
        }

    def _close_active_figures(self) -> None:
        """Close this view's active matplotlib figures and canvases to prevent memory leaks and dangling callbacks."""
        if hasattr(self, "active_canvases"):
            for canvas in self.active_canvases:
                try:
                    tk_widget = canvas.get_tk_widget()
                    if tk_widget.winfo_exists():
                        tk_widget.destroy()
                except Exception:
                    pass
            self.active_canvases.clear()

        for fig in list(self.active_figures):
            try:
                plt.close(fig)
            except Exception:
                pass
        self.active_figures.clear()

    # =========================================================================
    # TAB 1: FMEA RISK PRIORITY (RPN = S x O x D)
    # =========================================================================
    def _render_fmea_tab(self) -> None:
        """Render FMEA Matrix comparing pre-mitigation and target RPN."""
        for w in self.tab_fmea.winfo_children():
            w.destroy()

        top_bar = ctk.CTkFrame(self.tab_fmea, fg_color="transparent")
        top_bar.pack(fill="x", padx=12, pady=(10, 6))

        # Title & formula explanation
        left_info = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_info.pack(side="left")

        ctk.CTkLabel(
            left_info,
            text="Failure Mode and Effects Analysis (FMEA) Matrix",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w")

        formula_text = "Formula: RPN = Severity (S) × Occurrence (O) × Detection (D). Ratings: 1 (Lowest) to 10 (Highest Risk)."
        ctk.CTkLabel(
            left_info,
            text=formula_text,
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(1, 0))

        # Add FMEA Action button
        add_fmea_btn = ctk.CTkButton(
            top_bar,
            text="＋ Add Failure Mode",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=32,
            corner_radius=6,
            command=self._open_add_fmea_modal,
        )
        add_fmea_btn.pack(side="right")

        # Table Column Headers
        col_frame = ctk.CTkFrame(self.tab_fmea, fg_color=("#F8FAFC", "#26293B"), height=36, corner_radius=6)
        col_frame.pack(fill="x", padx=12, pady=(6, 4))

        headers = [
            ("Process Step", 120),
            ("Failure Mode & Effect", 220),
            ("S × O × D", 80),
            ("Initial RPN", 75),
            ("Q08 Mitigation Implemented", 220),
            ("Target RPN", 75),
            ("Risk Reduction", 85),
        ]
        for h, w in headers:
            ctk.CTkLabel(
                col_frame,
                text=h,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#64748B", "#94A3B8"),
                width=w,
                anchor="w",
            ).pack(side="left", padx=4, pady=4)

        # Scrollable rows frame
        rows_scroll = ctk.CTkScrollableFrame(self.tab_fmea, fg_color="transparent")
        rows_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        fmea_records = get_fmea_records()

        if not fmea_records:
            ctk.CTkLabel(
                rows_scroll,
                text="No FMEA records found in database.",
                font=ctk.CTkFont(size=13),
                text_color=("#64748B", "#94A3B8"),
            ).pack(pady=30)
            return

        for r in fmea_records:
            row = ctk.CTkFrame(rows_scroll, fg_color="transparent", height=42)
            row.pack(fill="x", pady=2)

            # Process Step
            ctk.CTkLabel(
                row,
                text=r["process_step"],
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                width=120,
                anchor="w",
            ).pack(side="left", padx=4)

            # Failure Mode & Effect
            mode_text = f"{r['failure_mode']} ({r.get('failure_effect', '')})"
            display_mode = mode_text[:38] + ".." if len(mode_text) > 38 else mode_text
            ctk.CTkLabel(
                row,
                text=display_mode,
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                width=220,
                anchor="w",
            ).pack(side="left", padx=4)

            # S x O x D breakdown
            sod_str = f"{r['severity_s']}×{r['occurrence_o']}×{r['detection_d']}"
            ctk.CTkLabel(
                row,
                text=sod_str,
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                width=80,
                anchor="w",
            ).pack(side="left", padx=4)

            # Initial RPN Badge
            rpn_val = r["rpn"]
            rpn_color = "#DC2626" if rpn_val >= 250 else ("#D97706" if rpn_val >= 150 else "#2563EB")
            rpn_badge = ctk.CTkLabel(
                row,
                text=str(rpn_val),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=rpn_color,
                width=75,
                anchor="w",
            )
            rpn_badge.pack(side="left", padx=4)

            # Mitigation Action
            act_text = r["mitigation_action"]
            display_act = act_text[:38] + ".." if len(act_text) > 38 else act_text
            ctk.CTkLabel(
                row,
                text=display_act,
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                width=220,
                anchor="w",
            ).pack(side="left", padx=4)

            # Target RPN Badge
            tr_val = r["target_rpn"]
            ctk.CTkLabel(
                row,
                text=str(tr_val),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#15803D",
                width=75,
                anchor="w",
            ).pack(side="left", padx=4)

            # Reduction %
            red_pct = r.get("reduction_pct", 0)
            red_chip = ctk.CTkLabel(
                row,
                text=f"-{int(red_pct)}%",
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=("#DCFCE7", "#14532D"),
                text_color=("#15803D", "#4ADE80"),
                corner_radius=4,
                width=65,
                height=22,
            )
            red_chip.pack(side="left", padx=4)

    # =========================================================================
    # TAB 2: SIPOC PROCESS MAP
    # =========================================================================
    def _render_sipoc_tab(self) -> None:
        """Render 5-column SIPOC matrix for Outpatient Appointment Scheduling."""
        for w in self.tab_sipoc.winfo_children():
            w.destroy()

        top_info = ctk.CTkFrame(self.tab_sipoc, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(12, 10))

        ctk.CTkLabel(
            top_info,
            text="SIPOC High-Level Process Map: Hospital Outpatient Appointment Scheduling",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            top_info,
            text="Defines Suppliers, Inputs, 5-Stage Clinical Process, Outputs, and Customers for scope boundary control.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(2, 0))

        scroll = ctk.CTkScrollableFrame(self.tab_sipoc, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        scroll.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        sipoc_data = get_sipoc_data()
        columns_meta = [
            ("S — Suppliers", sipoc_data["Suppliers"], "#0284C7", 0),
            ("I — Inputs", sipoc_data["Inputs"], "#8B5CF6", 1),
            ("P — Process", sipoc_data["Process"], "#10B981", 2),
            ("O — Outputs", sipoc_data["Outputs"], "#F59E0B", 3),
            ("C — Customers", sipoc_data["Customers"], "#EC4899", 4),
        ]

        for col_title, items, color, col_idx in columns_meta:
            card = ctk.CTkFrame(
                scroll,
                corner_radius=10,
                fg_color=("white", "#1E202E"),
                border_width=1,
                border_color=("#E2E8F0", "#334155"),
            )
            card.grid(row=0, column=col_idx, padx=5, pady=4, sticky="nsew")

            # Column Header Chip
            hdr = ctk.CTkLabel(
                card,
                text=col_title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#FFFFFF",
                fg_color=color,
                corner_radius=6,
                height=30,
            )
            hdr.pack(fill="x", padx=8, pady=(8, 10))

            # Items
            for item in items:
                box = ctk.CTkFrame(card, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
                box.pack(fill="x", padx=8, pady=4)
                ctk.CTkLabel(
                    box,
                    text=f"• {item}",
                    font=ctk.CTkFont(size=11),
                    text_color=("#0F172A", "#F8FAFC"),
                    justify="left",
                    wraplength=170,
                    padx=6,
                    pady=6,
                ).pack(anchor="w")

    # =========================================================================
    # TAB 3: CRITICAL TO QUALITY (CTQ) TREE
    # =========================================================================
    def _render_ctq_tab(self) -> None:
        """Render CTQ Tree translating Voice of Customer needs into measurable specs."""
        for w in self.tab_ctq.winfo_children():
            w.destroy()

        top_info = ctk.CTkFrame(self.tab_ctq, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(12, 10))

        ctk.CTkLabel(
            top_info,
            text="Critical to Quality (CTQ) Tree: Voice of Customer (VoC) to Measurable Specifications",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            top_info,
            text="Translates patient/operator qualitative needs into quantifiable engineering specifications and verified project outcomes.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(2, 0))

        scroll = ctk.CTkScrollableFrame(self.tab_ctq, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        ctq_items = get_ctq_tree_data()
        for i, ctq in enumerate(ctq_items, 1):
            card = ctk.CTkFrame(
                scroll,
                corner_radius=10,
                fg_color=("white", "#1E202E"),
                border_width=1,
                border_color=("#E2E8F0", "#334155"),
            )
            card.pack(fill="x", pady=6)

            grid_f = ctk.CTkFrame(card, fg_color="transparent")
            grid_f.pack(fill="x", padx=16, pady=12)
            grid_f.grid_columnconfigure(0, weight=1)
            grid_f.grid_columnconfigure(1, weight=1)
            grid_f.grid_columnconfigure(2, weight=1)

            # Node 1: Voice of Customer (Need)
            c1 = ctk.CTkFrame(grid_f, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
            c1.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
            ctk.CTkLabel(c1, text=f"Patient Need #{i}", font=ctk.CTkFont(size=10, weight="bold"), text_color="#0284C7").pack(anchor="w", padx=10, pady=(6, 2))
            ctk.CTkLabel(c1, text=f'"{ctq["need"]}"', font=ctk.CTkFont(size=11, weight="bold"), wraplength=220, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

            # Node 2: Quality Driver
            c2 = ctk.CTkFrame(grid_f, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
            c2.grid(row=0, column=1, padx=6, sticky="nsew")
            ctk.CTkLabel(c2, text="Quality Driver", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8B5CF6").pack(anchor="w", padx=10, pady=(6, 2))
            ctk.CTkLabel(c2, text=ctq["driver"], font=ctk.CTkFont(size=11, weight="bold"), wraplength=220, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

            # Node 3: Measurable CTQ & Status
            c3 = ctk.CTkFrame(grid_f, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
            c3.grid(row=0, column=2, padx=(6, 0), sticky="nsew")
            ctk.CTkLabel(c3, text=f"Target: {ctq['target']}", font=ctk.CTkFont(size=10, weight="bold"), text_color="#10B981").pack(anchor="w", padx=10, pady=(6, 2))
            ctk.CTkLabel(c3, text=ctq["ctq"], font=ctk.CTkFont(size=11), wraplength=240, justify="left").pack(anchor="w", padx=10, pady=(0, 4))
            ctk.CTkLabel(c3, text=f"✓ {ctq['status']}", font=ctk.CTkFont(size=10, weight="bold"), text_color="#15803D", wraplength=240, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    # =========================================================================
    # TAB 4: DEFECT CHECKSHEET & INCIDENT LOGGING
    # =========================================================================
    def _render_checksheet_tab(self) -> None:
        """Render interactive Defect Checksheet Log with logging modal integration."""
        for w in self.tab_checksheet.winfo_children():
            w.destroy()

        top_ctrl = ctk.CTkFrame(self.tab_checksheet, fg_color="transparent")
        top_ctrl.pack(fill="x", padx=12, pady=(10, 6))

        # Title on left
        left_box = ctk.CTkFrame(top_ctrl, fg_color="transparent")
        left_box.pack(side="left")

        ctk.CTkLabel(
            left_box,
            text="Operational Defect & Friction Checksheet Log",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            left_box,
            text="Real-time incident tally for Pareto root-cause analysis. Persisted directly in SQLite.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(1, 0))

        # Controls on right
        right_box = ctk.CTkFrame(top_ctrl, fg_color="transparent")
        right_box.pack(side="right")

        # Category Filter
        self.def_cat_filter = ctk.CTkOptionMenu(
            right_box,
            values=["All Categories"] + DEFECT_CATEGORIES,
            width=160,
            height=32,
            corner_radius=6,
            command=lambda _: self._render_checksheet_rows(),
        )
        self.def_cat_filter.set("All Categories")
        self.def_cat_filter.pack(side="left", padx=(0, 6))

        # Severity Filter
        self.def_sev_filter = ctk.CTkOptionMenu(
            right_box,
            values=["All Severities"] + DEFECT_SEVERITIES,
            width=120,
            height=32,
            corner_radius=6,
            command=lambda _: self._render_checksheet_rows(),
        )
        self.def_sev_filter.set("All Severities")
        self.def_sev_filter.pack(side="left", padx=(0, 6))

        # Status Filter
        self.def_status_filter = ctk.CTkOptionMenu(
            right_box,
            values=["All Statuses"] + DEFECT_STATUSES,
            width=120,
            height=32,
            corner_radius=6,
            command=lambda _: self._render_checksheet_rows(),
        )
        self.def_status_filter.set("All Statuses")
        self.def_status_filter.pack(side="left", padx=(0, 6))

        # Export CSV Button
        self.def_export_btn = ctk.CTkButton(
            right_box,
            text="📥 Export CSV",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#10B981", "#059669"),
            hover_color=("#059669", "#047857"),
            height=32,
            corner_radius=6,
            command=self._on_export_defects_csv,
        )
        self.def_export_btn.pack(side="left", padx=(0, 6))

        # + Log Defect Button
        log_btn = ctk.CTkButton(
            right_box,
            text="＋ Log Quality Defect",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=32,
            corner_radius=6,
            command=self._open_log_defect_modal,
        )
        log_btn.pack(side="left")

        # Table Column Headers
        col_frame = ctk.CTkFrame(self.tab_checksheet, fg_color=("#F8FAFC", "#26293B"), height=36, corner_radius=6)
        col_frame.pack(fill="x", padx=12, pady=(6, 4))

        headers = [
            ("Code", 85),
            ("Category", 180),
            ("Severity", 80),
            ("Description", 260),
            ("Reported By", 130),
            ("Status", 95),
            ("Action", 80),
        ]
        for h, w in headers:
            ctk.CTkLabel(
                col_frame,
                text=h,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#64748B", "#94A3B8"),
                width=w,
                anchor="w",
            ).pack(side="left", padx=4, pady=4)

        # Scrollable container for defect rows
        self.checksheet_rows_frame = ctk.CTkScrollableFrame(self.tab_checksheet, fg_color="transparent")
        self.checksheet_rows_frame.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self._render_checksheet_rows()

    def _render_checksheet_rows(self) -> None:
        """Render filtered defect log rows."""
        for w in self.checksheet_rows_frame.winfo_children():
            w.destroy()

        cat = self.def_cat_filter.get()
        sev = self.def_sev_filter.get()
        stat = self.def_status_filter.get() if hasattr(self, "def_status_filter") else None
        defects = get_defect_logs(category=cat, severity=sev, status=stat)

        if not defects:
            ctk.CTkLabel(
                self.checksheet_rows_frame,
                text="No logged defects match the selected filter.",
                font=ctk.CTkFont(size=13),
                text_color=("#64748B", "#94A3B8"),
            ).pack(pady=30)
            return

        for d in defects:
            row = ctk.CTkFrame(self.checksheet_rows_frame, fg_color="transparent", height=40)
            row.pack(fill="x", pady=2)

            # Code
            ctk.CTkLabel(
                row,
                text=d["defect_code"],
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#0284C7", "#38BDF8"),
                width=85,
                anchor="w",
            ).pack(side="left", padx=4)

            # Category
            c_text = d["category"]
            disp_cat = c_text[:24] + ".." if len(c_text) > 24 else c_text
            ctk.CTkLabel(
                row,
                text=disp_cat,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#0F172A", "#F8FAFC"),
                width=180,
                anchor="w",
            ).pack(side="left", padx=4)

            # Severity Chip
            s = d["severity"]
            s_bg = ("#FEE2E2", "#7F1D1D") if s == "Critical" else (("#FEF3C7", "#78350F") if s == "Major" else ("#E2E8F0", "#334155"))
            s_fg = "#DC2626" if s == "Critical" else ("#D97706" if s == "Major" else "#0284C7")
            ctk.CTkLabel(
                row,
                text=s,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=s_bg,
                text_color=s_fg,
                corner_radius=4,
                width=75,
                height=22,
            ).pack(side="left", padx=4)

            # Description
            desc = d["description"]
            disp_desc = desc[:40] + ".." if len(desc) > 40 else desc
            ctk.CTkLabel(
                row,
                text=disp_desc,
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                width=260,
                anchor="w",
            ).pack(side="left", padx=4)

            # Reported By
            ctk.CTkLabel(
                row,
                text=d.get("reported_by", "Staff"),
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                width=130,
                anchor="w",
            ).pack(side="left", padx=4)

            # Status Chip
            st = d["resolution_status"]
            st_bg = ("#DCFCE7", "#14532D") if st == "Resolved" else (("#FEF3C7", "#78350F") if st == "In Analysis" else ("#F1F5F9", "#26293B"))
            st_fg = "#15803D" if st == "Resolved" else ("#B45309" if st == "In Analysis" else "#64748B")
            ctk.CTkLabel(
                row,
                text=st,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=st_bg,
                text_color=st_fg,
                corner_radius=4,
                width=85,
                height=22,
            ).pack(side="left", padx=4)

            # Quick Action
            if st != "Resolved":
                res_btn = ctk.CTkButton(
                    row,
                    text="Resolve",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=("#10B981", "#059669"),
                    width=70,
                    height=24,
                    corner_radius=4,
                    command=lambda def_id=d["id"]: self._on_resolve_defect(def_id),
                )
                res_btn.pack(side="left", padx=4)
            else:
                ctk.CTkLabel(
                    row,
                    text="✓ Done",
                    font=ctk.CTkFont(size=10),
                    text_color="#10B981",
                    width=70,
                    anchor="w",
                ).pack(side="left", padx=4)

    # =========================================================================
    # TAB 5: PARETO CHART & FISHBONE ROOT CAUSE
    # =========================================================================
    def _render_pareto_tab(self) -> None:
        """Render embedded Pareto 80/20 chart and Ishikawa Fishbone Analysis."""
        for w in self.tab_pareto.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(self.tab_pareto, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(8, 10))
        scroll.grid_columnconfigure((0, 1), weight=1)

        # -------------------------------------------------------------
        # Left Card: Pareto Chart (80/20 Rule Analysis)
        # -------------------------------------------------------------
        pareto_card = ctk.CTkFrame(
            scroll,
            corner_radius=10,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        pareto_card.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="nsew")

        ctk.CTkLabel(
            pareto_card,
            text="Pareto Analysis (80/20 Rule) of Logged Defects",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=16, pady=(12, 2))

        pareto_data = get_defect_pareto_data()
        total_d = pareto_data["total_defects"]

        ctk.CTkLabel(
            pareto_card,
            text=f"Total: {total_d} incidents  •  Vital Few: {', '.join(pareto_data['vital_few'][:2])}",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        if total_d > 0:
            self._embed_pareto_chart(pareto_card, pareto_data)
        else:
            ctk.CTkLabel(
                pareto_card,
                text="No defect records available for Pareto analysis.",
                font=ctk.CTkFont(size=12),
                text_color=("#64748B", "#94A3B8"),
            ).pack(pady=40)

        # -------------------------------------------------------------
        # Right Card: Fishbone / Ishikawa Root Cause Analysis
        # -------------------------------------------------------------
        fish_card = ctk.CTkFrame(
            scroll,
            corner_radius=10,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        fish_card.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="nsew")

        ctk.CTkLabel(
            fish_card,
            text="Ishikawa Cause-and-Effect (Fishbone) Analysis",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=16, pady=(12, 2))

        ctk.CTkLabel(
            fish_card,
            text="Systematic root-cause categorization across People, Process, Technology, and Measurement.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        fish_data = get_fishbone_data()

        # Problem Statement Chip
        prob_box = ctk.CTkFrame(fish_card, fg_color=("#FEE2E2", "#7F1D1D"), corner_radius=6)
        prob_box.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(
            prob_box,
            text=f"🎯 Effect: {fish_data['problem']}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#DC2626", "#FCA5A5"),
            padx=10,
            pady=6,
        ).pack(anchor="w")

        # Branches
        for branch_name, causes in fish_data["branches"].items():
            b_frame = ctk.CTkFrame(fish_card, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
            b_frame.pack(fill="x", padx=14, pady=3)

            ctk.CTkLabel(
                b_frame,
                text=branch_name,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#0284C7",
                padx=8,
                pady=4,
            ).pack(anchor="w")

            for c in causes:
                ctk.CTkLabel(
                    b_frame,
                    text=f"  • {c}",
                    font=ctk.CTkFont(size=10),
                    text_color=("#0F172A", "#F8FAFC"),
                    justify="left",
                    wraplength=340,
                ).pack(anchor="w", padx=8, pady=1)

        # Root cause conclusion
        res_box = ctk.CTkFrame(fish_card, fg_color=("#DCFCE7", "#14532D"), corner_radius=6)
        res_box.pack(fill="x", padx=14, pady=(8, 12))
        ctk.CTkLabel(
            res_box,
            text=f"💡 {fish_data['root_cause_summary']}",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#15803D", "#4ADE80"),
            justify="left",
            wraplength=340,
            padx=10,
            pady=8,
        ).pack(anchor="w")

    def _embed_pareto_chart(self, parent: ctk.CTkFrame, data: Dict[str, Any]) -> None:
        """Embed Matplotlib Pareto 80/20 chart with dual Y-axes."""
        theme = self._get_theme_colors()
        fig = Figure(figsize=(5.2, 4.0), dpi=100)
        self.active_figures.append(fig)
        fig.patch.set_facecolor(theme["bg"])

        ax1 = fig.add_subplot(111)
        ax1.set_facecolor(theme["bg"])
        ax2 = ax1.twinx()

        # Abbreviate categories for X-axis labels
        def shorten_label(lbl: str) -> str:
            replacements = {
                "Appointment Booking Error": "Booking Err",
                "Confusing Form Layout": "Form Layout",
                "UI Lag / Latency": "UI Lag",
                "Missing Feedback Toast": "No Toast",
                "Doctor Schedule Overlap": "Doc Overlap",
                "Search Filter Inaccuracy": "Search Err",
                "Theme / Visual Fatigue": "Theme/Glare",
            }
            return replacements.get(lbl, lbl[:10])

        x_labels = [shorten_label(c) for c in data["categories"]]
        counts = data["counts"]
        cum_pct = data["cumulative_pct"]

        # Primary Axis: Bars
        bars = ax1.bar(x_labels, counts, color="#0284C7", width=0.55, edgecolor="none")
        ax1.set_ylabel("Defect Frequency", color=theme["muted"], fontsize=9)
        ax1.tick_params(colors=theme["text"], labelsize=8)
        ax1.tick_params(axis="x", rotation=35)
        ax1.grid(axis="y", linestyle="--", alpha=0.3, color=theme["grid"])

        for bar in bars:
            h = bar.get_height()
            ax1.annotate(
                f"{h}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=theme["text"],
                fontsize=8,
                fontweight="bold",
            )

        # Secondary Axis: Cumulative percentage line
        ax2.plot(x_labels, cum_pct, color="#EF4444", marker="o", linewidth=2.0, markersize=4)
        ax2.set_ylabel("Cumulative %", color="#EF4444", fontsize=9)
        ax2.set_ylim(0, 105)
        ax2.tick_params(colors=theme["text"], labelsize=8)

        # 80% Cutoff line
        ax2.axhline(80, color="#F59E0B", linestyle="--", linewidth=1.2, alpha=0.8)
        ax2.annotate(
            "80% Cutoff",
            xy=(0.02, 82),
            xycoords=("axes fraction", "data"),
            color="#F59E0B",
            fontsize=8,
            fontweight="bold",
        )

        for spine in list(ax1.spines.values()) + list(ax2.spines.values()):
            spine.set_color(theme["spine"])

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        self.active_canvases.append(canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # =========================================================================
    # TAB 6: PDCA CONTINUOUS IMPROVEMENT CYCLES
    # =========================================================================
    def _render_pdca_tab(self) -> None:
        """Render PDCA Continuous Improvement Cycle framework."""
        for w in self.tab_pdca.winfo_children():
            w.destroy()

        top_info = ctk.CTkFrame(self.tab_pdca, fg_color="transparent")
        top_info.pack(fill="x", padx=16, pady=(12, 10))

        ctk.CTkLabel(
            top_info,
            text="Deming Wheel / PDCA Continuous Improvement Cycle (BBAT104 Framework)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            top_info,
            text="Systematic Shewhart-Deming cycle (Plan-Do-Check-Act) applied to Outpatient Registration & User Satisfaction.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", pady=(2, 0))

        scroll = ctk.CTkScrollableFrame(self.tab_pdca, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        stages = get_pdca_cycles_data()
        colors = {
            "PLAN": ("#0284C7", ("#E0F2FE", "#0C4A6E")),
            "DO": ("#8B5CF6", ("#EDE9FE", "#4C1D95")),
            "CHECK": ("#10B981", ("#DCFCE7", "#14532D")),
            "ACT": ("#F59E0B", ("#FEF3C7", "#78350F")),
        }

        for item in stages:
            st_name = item["stage"]
            accent, badge_bg = colors.get(st_name, ("#0284C7", ("#E2E8F0", "#334155")))

            card = ctk.CTkFrame(
                scroll,
                corner_radius=10,
                fg_color=("white", "#1E202E"),
                border_width=1,
                border_color=("#E2E8F0", "#334155"),
            )
            card.pack(fill="x", pady=6)

            card_top = ctk.CTkFrame(card, fg_color="transparent")
            card_top.pack(fill="x", padx=16, pady=(12, 6))

            badge = ctk.CTkLabel(
                card_top,
                text=f"Phase: {st_name}",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=badge_bg,
                text_color=accent,
                corner_radius=6,
                padx=12,
                height=26,
            )
            badge.pack(side="left")

            ctk.CTkLabel(
                card_top,
                text=f" — {item['phase']}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("#0F172A", "#F8FAFC"),
            ).pack(side="left", padx=8)

            st_chip = ctk.CTkLabel(
                card_top,
                text=f"Status: {item['status']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#10B981",
            )
            st_chip.pack(side="right")

            # Description
            ctk.CTkLabel(
                card,
                text=item["description"],
                font=ctk.CTkFont(size=11),
                text_color=("#0F172A", "#F8FAFC"),
                justify="left",
                wraplength=760,
            ).pack(anchor="w", padx=16, pady=(0, 6))

            # Deliverables Box
            del_box = ctk.CTkFrame(card, fg_color=("#F8FAFC", "#26293B"), corner_radius=6)
            del_box.pack(fill="x", padx=16, pady=(0, 12))
            ctk.CTkLabel(
                del_box,
                text=f"📦 Deliverables: {item['deliverables']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#64748B", "#94A3B8"),
                padx=10,
                pady=6,
            ).pack(anchor="w")

    # =========================================================================
    # MODAL OPENERS & REFRESH HANDLERS
    # =========================================================================
    def _open_add_fmea_modal(self) -> None:
        """Open modal to record a new FMEA failure mode."""
        AddFMEAModal(
            self.winfo_toplevel(),
            on_success=self._on_fmea_success,
        )

    def _on_fmea_success(self, msg: str) -> None:
        """Handle FMEA creation callback."""
        self._render_fmea_tab()
        self._show_notice(msg)

    def _open_log_defect_modal(self) -> None:
        """Open modal to record a quality defect / incident."""
        LogDefectModal(
            self.winfo_toplevel(),
            on_success=self._on_defect_success,
        )

    def _on_defect_success(self, msg: str) -> None:
        """Handle defect creation callback."""
        self._render_checksheet_rows()
        self._render_pareto_tab()
        self._show_notice(msg)

    def _on_export_defects_csv(self) -> None:
        """Export currently filtered or all defect logs to a CSV file."""
        from tkinter import filedialog

        try:
            filepath = filedialog.asksaveasfilename(
                title="Export Defect Checksheet Logs to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                initialfile="TQM_Quality_Defect_Checksheet.csv",
            )
            if not filepath:
                return

            cat = self.def_cat_filter.get() if hasattr(self, "def_cat_filter") else None
            sev = self.def_sev_filter.get() if hasattr(self, "def_sev_filter") else None
            stat = self.def_status_filter.get() if hasattr(self, "def_status_filter") else None

            success, msg, count = export_defects_to_csv(
                filepath,
                category=cat,
                severity=sev,
                status=stat,
            )
            if success:
                self._show_notice(f"✓ {msg}")
            else:
                self._show_notice(f"Export failed: {msg}", is_error=True)
        except Exception as e:
            self._show_notice(f"Export error: {e}", is_error=True)

    def _on_resolve_defect(self, defect_id: int) -> None:
        """Mark defect status as Resolved."""
        success, msg = update_defect_status(defect_id, "Resolved")
        if success:
            self._render_checksheet_rows()
            self._show_notice(msg)
        else:
            self._show_notice(msg, is_error=True)

    def refresh_all(self) -> None:
        """Refresh all 6 quality tabs."""
        self._close_active_figures()
        self._render_fmea_tab()
        self._render_sipoc_tab()
        self._render_ctq_tab()
        self._render_checksheet_tab()
        self._render_pareto_tab()
        self._render_pdca_tab()
        self._show_notice("TQM Quality Toolkit successfully refreshed.")
