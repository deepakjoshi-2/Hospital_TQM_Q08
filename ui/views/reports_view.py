"""Visual Reports View embedding Matplotlib analytics charts in CustomTkinter.
Displays live SQLite-driven analytics for appointment status, timeline trends,
physician workload, and patient satisfaction (CSAT) with dark/light theme support.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import customtkinter as ctk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt

from services.report_service import (
    get_appointments_by_status,
    get_appointments_over_time,
    get_doctor_workload,
    get_patient_satisfaction_data,
    get_reports_summary_stats,
)


class ReportsView(ctk.CTkFrame):
    """Visual Reports View featuring dynamic analytical charts and SQLite synchronization."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.active_figures: List[Figure] = []
        self.active_canvases: List[FigureCanvasTkAgg] = []
        self._refresh_timer_id: Optional[str] = None

        # Build UI layout
        self._build_header()
        self._build_scrollable_container()
        self.render_all_charts()

    def _build_header(self) -> None:
        """Header with report title, action buttons, and responsive summary KPI cards."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=24, pady=(20, 10))

        # Top row: title & subtitle on left, actions on right
        top_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_row.pack(fill="x")

        info_box = ctk.CTkFrame(top_row, fg_color="transparent")
        info_box.pack(side="left")

        title = ctk.CTkLabel(
            info_box,
            text="Visual Analytics & Clinical Reports",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        title.pack(anchor="w")

        self.subtitle_lbl = ctk.CTkLabel(
            info_box,
            text="Real-time SQLite analytics: operational status, timeline trends, workload, and CSAT.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
        )
        self.subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Right control panel: Export CSV + Refresh Reports
        self.ctrl_box = ctk.CTkFrame(top_row, fg_color="transparent")
        self.ctrl_box.pack(side="right")

        # Export CSV Button
        self.export_btn = ctk.CTkButton(
            self.ctrl_box,
            text="📥 Export CSV",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=120,
            height=36,
            corner_radius=8,
            command=self._on_export_csv,
        )
        self.export_btn.pack(side="left", padx=(0, 8))

        # Refresh Reports Button
        self.refresh_btn = ctk.CTkButton(
            self.ctrl_box,
            text="🔄 Refresh Data",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            width=130,
            height=36,
            corner_radius=8,
            command=self.refresh_reports,
        )
        self.refresh_btn.pack(side="left")

        # Bottom row: Summary KPI Badges Frame
        self.pills_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.pills_frame.pack(fill="x", pady=(10, 0))

    def _update_kpi_pills(self, stats: Dict[str, Any]) -> None:
        """Render quick summary badges in the header."""
        for w in self.pills_frame.winfo_children():
            w.destroy()

        # Pill 1: Total Consultations
        total_text = f"Total: {stats['total_appointments']}"
        p1 = ctk.CTkLabel(
            self.pills_frame,
            text=total_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E2E8F0", "#26293B"),
            text_color=("#0F172A", "#F8FAFC"),
            corner_radius=6,
            padx=10,
            height=30,
        )
        p1.pack(side="left", padx=(0, 6))

        # Pill 2: Completed / Completion Rate
        comp_text = f"Completed: {stats['completed_count']} ({stats['completion_rate_pct']}%)"
        p2 = ctk.CTkLabel(
            self.pills_frame,
            text=comp_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#DCFCE7", "#14532D"),
            text_color=("#15803D", "#4ADE80"),
            corner_radius=6,
            padx=10,
            height=30,
        )
        p2.pack(side="left", padx=(0, 6))

        # Pill 3: CSAT Rating (if available)
        if stats.get("has_feedback"):
            csat_text = f"CSAT: {stats['average_csat']} ★ ({stats['total_feedbacks']} ratings)"
            p3 = ctk.CTkLabel(
                self.pills_frame,
                text=csat_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=("#FEF3C7", "#78350F"),
                text_color=("#B45309", "#FCD34D"),
                corner_radius=6,
                padx=10,
                height=30,
            )
            p3.pack(side="left")

    def _build_scrollable_container(self) -> None:
        """Create vertically scrollable frame for high-DPI scaling and screen adaptability."""
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

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
            "card_bg": ("white", "#1E202E"),
            "border": ("#E2E8F0", "#334155"),
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

    def render_all_charts(self) -> None:
        """Fetch fresh SQLite data and render all 4 analytical cards in a 2x2 grid."""
        self._close_active_figures()

        for w in self.scroll_frame.winfo_children():
            w.destroy()

        # Update high-level summary KPIs
        summary_stats = get_reports_summary_stats()
        self._update_kpi_pills(summary_stats)

        # 2-column grid configuration
        self.scroll_frame.grid_columnconfigure((0, 1), weight=1)

        # -------------------------------------------------------------
        # Card 1: Appointments by Status (Donut Chart)
        # -------------------------------------------------------------
        c1 = self._create_card_frame(self.scroll_frame, row=0, col=0, padx=(0, 8), pady=(0, 16))
        self._build_status_chart(c1)

        # -------------------------------------------------------------
        # Card 2: Appointments Over Time (Trend / Timeline Chart)
        # -------------------------------------------------------------
        c2 = self._create_card_frame(self.scroll_frame, row=0, col=1, padx=(8, 0), pady=(0, 16))
        self._build_timeline_chart(c2)

        # -------------------------------------------------------------
        # Card 3: Doctor-wise Appointment Workload (Horizontal Bar Chart)
        # -------------------------------------------------------------
        c3 = self._create_card_frame(self.scroll_frame, row=1, col=0, padx=(0, 8), pady=(0, 16))
        self._build_doctor_workload_chart(c3)

        # -------------------------------------------------------------
        # Card 4: Patient Satisfaction / CSAT Feedback
        # -------------------------------------------------------------
        c4 = self._create_card_frame(self.scroll_frame, row=1, col=1, padx=(8, 0), pady=(0, 16))
        self._build_satisfaction_chart(c4)

    def _create_card_frame(self, parent, row: int, col: int, padx, pady) -> ctk.CTkFrame:
        """Create styled container card for a report chart."""
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=("white", "#1E202E"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
        )
        card.grid(row=row, column=col, padx=padx, pady=pady, sticky="nsew")
        return card

    def _render_empty_state(self, parent: ctk.CTkFrame, title: str, description: str, icon: str = "📊") -> None:
        """Display beginner-friendly placeholder when no database records exist."""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=20, pady=36)

        ctk.CTkLabel(
            box,
            text=f"{icon}  {title}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#D97706", "#FBBF24"),
        ).pack(pady=(10, 6))

        ctk.CTkLabel(
            box,
            text=description,
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#94A3B8"),
            justify="center",
        ).pack(pady=4)

    # =========================================================================
    # CHART 1: APPOINTMENTS BY STATUS
    # =========================================================================
    def _build_status_chart(self, parent: ctk.CTkFrame) -> None:
        """Render Appointments by Status as a clear, categorized Donut Chart."""
        # Card Header
        ctk.CTkLabel(
            parent,
            text="Appointments by Status",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=16, pady=(14, 2))

        status_data = get_appointments_by_status()
        total = status_data["total"]

        if status_data["is_empty"] or total == 0:
            self._render_empty_state(
                parent,
                title="No Appointment Records",
                description="No appointments found in the SQLite database.\nBook appointments to generate clinical status analytics.",
            )
            return

        counts = status_data["counts"]
        # Subtitle
        sub_text = f"Total: {total} consultations ({counts.get('Completed', 0)} completed, {counts.get('Scheduled', 0)} scheduled)"
        ctk.CTkLabel(
            parent,
            text=sub_text,
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Filter out categories with 0 count for clean pie display
        active_items = [(st, cnt) for st, cnt in counts.items() if cnt > 0]
        if not active_items:
            self._render_empty_state(parent, "No Status Data", "No appointments with active statuses found.")
            return

        theme = self._get_theme_colors()
        fig = Figure(figsize=(5.0, 3.4), dpi=100)
        self.active_figures.append(fig)
        fig.patch.set_facecolor(theme["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme["bg"])

        status_color_palette = {
            "Completed": "#10B981",  # Emerald
            "Scheduled": "#0284C7",  # Sky Blue
            "Cancelled": "#EF4444",  # Red
            "No-Show": "#F59E0B",    # Amber
        }

        labels = [st for st, _ in active_items]
        values = [cnt for _, cnt in active_items]
        slice_colors = [status_color_palette.get(st, "#8B5CF6") for st in labels]

        # Donut Chart with center hole
        wedges, texts, autotexts = ax.pie(
            values,
            labels=None,  # Labels in legend for clean look
            autopct="%1.0f%%",
            pctdistance=0.76,
            startangle=140,
            colors=slice_colors,
            wedgeprops={"width": 0.44, "edgecolor": theme["bg"], "linewidth": 2},
        )

        for at in autotexts:
            at.set_color("#FFFFFF")
            at.set_fontsize(9)
            at.set_weight("bold")

        # Center KPI text
        ax.text(
            0, 0,
            f"{total}\nTotal",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=theme["text"],
        )

        # Legend with exact counts
        legend_labels = [f"{st}: {cnt} ({int(cnt/total*100)}%)" for st, cnt in active_items]
        legend = ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
            fontsize=9,
        )
        for t in legend.get_texts():
            t.set_color(theme["text"])

        ax.axis("equal")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        self.active_canvases.append(canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # =========================================================================
    # CHART 2: APPOINTMENTS OVER TIME (TIMELINE TREND)
    # =========================================================================
    def _build_timeline_chart(self, parent: ctk.CTkFrame) -> None:
        """Render Appointments over Time as a chronological line/trend chart."""
        ctk.CTkLabel(
            parent,
            text="Appointments Over Time",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=16, pady=(14, 2))

        timeline_data = get_appointments_over_time()

        if not timeline_data:
            self._render_empty_state(
                parent,
                title="No Timeline Records",
                description="No historical or scheduled appointments found over time.\nCreate appointments with dates to plot timeline volume.",
            )
            return

        dates = [d["date"] for d in timeline_data]
        counts = [d["count"] for d in timeline_data]
        total_volume = sum(counts)
        date_span = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0]

        ctk.CTkLabel(
            parent,
            text=f"Span: {date_span}  •  {len(dates)} active clinic days",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=16, pady=(0, 6))

        theme = self._get_theme_colors()
        fig = Figure(figsize=(5.0, 3.4), dpi=100)
        self.active_figures.append(fig)
        fig.patch.set_facecolor(theme["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme["bg"])

        # Format dates for human readability (e.g., 'Oct 09')
        def format_date_str(d_str: str) -> str:
            try:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                return dt.strftime("%b %d")
            except Exception:
                return d_str

        formatted_dates = [format_date_str(d) for d in dates]

        # Line plot with markers and shaded area fill
        line_color = "#0284C7"
        ax.plot(
            formatted_dates,
            counts,
            marker="o",
            color=line_color,
            linewidth=2.4,
            markersize=5,
            markerfacecolor="#38BDF8",
            markeredgecolor=line_color,
            label="Daily Volume",
        )
        ax.fill_between(formatted_dates, counts, color=line_color, alpha=0.15)

        # Peak value annotations
        for x_idx, (x_lbl, y_val) in enumerate(zip(formatted_dates, counts)):
            if y_val > 0:
                ax.annotate(
                    f"{y_val}",
                    xy=(x_idx, y_val),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    color=theme["text"],
                    fontsize=8,
                    fontweight="bold",
                )

        ax.grid(axis="both", linestyle="--", alpha=0.35, color=theme["grid"])
        ax.tick_params(colors=theme["text"], labelsize=8)
        ax.tick_params(axis="x", rotation=35)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        for spine_name in ["top", "right"]:
            ax.spines[spine_name].set_visible(False)
        for spine_name in ["bottom", "left"]:
            ax.spines[spine_name].set_color(theme["spine"])

        ax.set_ylabel("Consultations", color=theme["muted"], fontsize=9)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        self.active_canvases.append(canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # =========================================================================
    # CHART 3: DOCTOR-WISE APPOINTMENT WORKLOAD
    # =========================================================================
    def _build_doctor_workload_chart(self, parent: ctk.CTkFrame) -> None:
        """Render Doctor-wise Appointment Workload as a readable horizontal bar chart."""
        ctk.CTkLabel(
            parent,
            text="Doctor-wise Workload Distribution",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=16, pady=(14, 2))

        workload_data = get_doctor_workload()

        if not workload_data:
            self._render_empty_state(
                parent,
                title="No Doctor Workload Records",
                description="No registered physicians found in SQLite.\nAdd doctors and assign appointments to view clinical load.",
            )
            return

        total_appts = sum(d["count"] for d in workload_data)
        ctk.CTkLabel(
            parent,
            text=f"Total: {len(workload_data)} physicians  •  {total_appts} total clinical assignments",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Show top 8 doctors (or all if <= 8) for optimal card sizing
        display_data = workload_data[:8]
        # Invert order for barh so top doctor appears at the top
        display_data = list(reversed(display_data))

        doc_labels = [f"{d['doctor_name']} ({d['specialization'][:10]})" for d in display_data]
        doc_counts = [d["count"] for d in display_data]

        theme = self._get_theme_colors()
        fig = Figure(figsize=(5.0, 3.4), dpi=100)
        self.active_figures.append(fig)
        fig.patch.set_facecolor(theme["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme["bg"])

        # Bar chart with accent gradient
        bars = ax.barh(doc_labels, doc_counts, color="#38BDF8", height=0.6, edgecolor="none")

        # Color the top doctor distinctly
        if bars:
            bars[-1].set_color("#0284C7")  # Highlight busiest doctor

        ax.grid(axis="x", linestyle="--", alpha=0.35, color=theme["grid"])
        ax.tick_params(colors=theme["text"], labelsize=8)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        for spine_name in ["top", "right"]:
            ax.spines[spine_name].set_visible(False)
        for spine_name in ["bottom", "left"]:
            ax.spines[spine_name].set_color(theme["spine"])

        # Value annotations at bar ends
        for bar in bars:
            width = bar.get_width()
            ax.annotate(
                f" {int(width)}",
                xy=(width, bar.get_y() + bar.get_height() / 2),
                xytext=(2, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                color=theme["text"],
                fontsize=8,
                fontweight="bold",
            )

        ax.set_xlabel("Appointments Handled", color=theme["muted"], fontsize=9)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        self.active_canvases.append(canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # =========================================================================
    # CHART 4: PATIENT SATISFACTION / CSAT FEEDBACK
    # =========================================================================
    def _build_satisfaction_chart(self, parent: ctk.CTkFrame) -> None:
        """Render Patient Satisfaction / CSAT ratings ONLY if actual feedback exists."""
        ctk.CTkLabel(
            parent,
            text="Patient Satisfaction & CSAT Ratings",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        ).pack(anchor="w", padx=16, pady=(14, 2))

        sat_data = get_patient_satisfaction_data()

        # Requirement 2 & 4: Only display chart if actual feedback data exists
        if not sat_data["has_feedback"] or sat_data["total_rated"] == 0:
            self._render_empty_state(
                parent,
                title="No Patient Feedback Recorded",
                description="Completed appointments have not received 1–5 star ratings yet.\nSubmit patient feedback ratings to unlock Voice of Customer analytics.",
                icon="⭐",
            )
            return

        # Subtitle with CSAT metrics
        avg_rating = sat_data["average_rating"]
        pos_pct = sat_data["positive_rate_pct"]
        total_r = sat_data["total_rated"]

        ctk.CTkLabel(
            parent,
            text=f"Average Score: {avg_rating} / 5.00 ⭐  •  {pos_pct}% Positive ({total_r} verified reviews)",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(anchor="w", padx=16, pady=(0, 6))

        breakdown = sat_data["breakdown"]
        star_labels = ["1 ★", "2 ★", "3 ★", "4 ★", "5 ★"]
        star_counts = [breakdown[1], breakdown[2], breakdown[3], breakdown[4], breakdown[5]]
        star_colors = ["#EF4444", "#FB923C", "#FBBF24", "#34D399", "#10B981"]

        theme = self._get_theme_colors()
        fig = Figure(figsize=(5.0, 3.4), dpi=100)
        self.active_figures.append(fig)
        fig.patch.set_facecolor(theme["bg"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme["bg"])

        # Horizontal rating distribution bars
        bars = ax.barh(star_labels, star_counts, color=star_colors, height=0.55, edgecolor="none")

        ax.grid(axis="x", linestyle="--", alpha=0.35, color=theme["grid"])
        ax.tick_params(colors=theme["text"], labelsize=8)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        for spine_name in ["top", "right"]:
            ax.spines[spine_name].set_visible(False)
        for spine_name in ["bottom", "left"]:
            ax.spines[spine_name].set_color(theme["spine"])

        # Annotation labels showing exact count and % of feedback
        for bar in bars:
            width = bar.get_width()
            pct_val = int(round((width / total_r) * 100)) if total_r > 0 else 0
            ax.annotate(
                f" {int(width)} ({pct_val}%)",
                xy=(width, bar.get_y() + bar.get_height() / 2),
                xytext=(2, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                color=theme["text"],
                fontsize=8,
                fontweight="bold",
            )

        ax.set_xlabel("Number of Patient Ratings", color=theme["muted"], fontsize=9)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=parent)
        self.active_canvases.append(canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # =========================================================================
    # EXPORT & REFRESH ACTIONS & LIFECYCLE CLEANUP
    # =========================================================================
    def _on_export_csv(self) -> None:
        """Export comprehensive clinical quality summary report to CSV."""
        from tkinter import filedialog
        from services.report_service import export_summary_report_to_csv

        try:
            filepath = filedialog.asksaveasfilename(
                title="Export Clinical Analytics Report to CSV",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                initialfile="Hospital_Q08_Analytics_Report.csv",
            )
            if not filepath:
                return

            success, msg = export_summary_report_to_csv(filepath)
            if success:
                self.export_btn.configure(text="✓ Exported!", fg_color="#10B981")
                self.after(2000, self._reset_export_btn)
            else:
                self.export_btn.configure(text="⚠️ Error", fg_color="#EF4444")
                self.after(2000, self._reset_export_btn)
        except Exception as e:
            print(f"Error exporting report to CSV: {e}")

    def _reset_export_btn(self) -> None:
        """Restore export button style."""
        if self.winfo_exists() and hasattr(self, "export_btn") and self.export_btn.winfo_exists():
            self.export_btn.configure(text="📥 Export CSV", fg_color=("#E2E8F0", "#334155"))

    def refresh_reports(self) -> None:
        """Refresh all data queries from SQLite and re-render charts."""
        self.refresh_btn.configure(text="⏳ Refreshing...", state="disabled")
        self.update_idletasks()

        try:
            self.render_all_charts()
            self.refresh_btn.configure(text="✓ Updated!", fg_color="#10B981")
            if self._refresh_timer_id is not None:
                self.after_cancel(self._refresh_timer_id)
            self._refresh_timer_id = self.after(1500, self._reset_refresh_btn)
        except Exception as e:
            print(f"Error refreshing reports: {e}")
            if self.winfo_exists() and hasattr(self, "refresh_btn") and self.refresh_btn.winfo_exists():
                self.refresh_btn.configure(text="🔄 Refresh Data", state="normal", fg_color="#0284C7")

    def _reset_refresh_btn(self) -> None:
        """Restore normal refresh button state."""
        self._refresh_timer_id = None
        if self.winfo_exists() and hasattr(self, "refresh_btn") and self.refresh_btn.winfo_exists():
            self.refresh_btn.configure(text="🔄 Refresh Data", state="normal", fg_color="#0284C7")

    def destroy(self) -> None:
        """Safely clean up active timers and matplotlib figures upon view destruction."""
        if hasattr(self, "_refresh_timer_id") and self._refresh_timer_id is not None:
            self.after_cancel(self._refresh_timer_id)
            self._refresh_timer_id = None
        self._close_active_figures()
        super().destroy()
