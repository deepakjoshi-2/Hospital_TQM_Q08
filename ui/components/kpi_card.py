"""Reusable KPI summary card widget for dashboard metrics."""
import customtkinter as ctk


class KPICard(ctk.CTkFrame):
    """Modern metric summary card with icon, value, title, and trend indicator."""

    def __init__(
        self,
        master,
        title: str,
        value: str,
        subtitle: str = "",
        icon: str = "📊",
        accent_color: str = "#38BDF8",
        **kwargs,
    ):
        super().__init__(master, corner_radius=12, **kwargs)
        self.configure(fg_color=("white", "#1E202E"), border_width=1, border_color=("#E2E8F0", "#334155"))

        # Main layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Top row: Title and Icon badge
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=18, pady=(16, 4))

        self.title_label = ctk.CTkLabel(
            top_frame,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        self.title_label.pack(side="left")

        self.icon_badge = ctk.CTkLabel(
            top_frame,
            text=icon,
            font=ctk.CTkFont(size=18),
            width=36,
            height=36,
            corner_radius=8,
            fg_color=("#F1F5F9", "#26293B"),
        )
        self.icon_badge.pack(side="right")

        # Metric Value
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            anchor="w",
        )
        self.value_label.pack(fill="x", padx=18, pady=(2, 4))

        # Bottom Subtitle / trend indicator
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self,
                text=subtitle,
                font=ctk.CTkFont(size=11),
                text_color=accent_color,
                anchor="w",
            )
            self.subtitle_label.pack(fill="x", padx=18, pady=(0, 14))
        else:
            self.pack_configure(pady=(0, 14))

    def update_value(self, new_value: str, new_subtitle: str = None) -> None:
        """Dynamically update card metric value and subtitle."""
        self.value_label.configure(text=new_value)
        if new_subtitle and hasattr(self, "subtitle_label"):
            self.subtitle_label.configure(text=new_subtitle)
