"""Reusable KPI summary card widget for dashboard metrics.
Enhanced with distinctive Clinical Analytics styling, hover states, and full-card click interactivity.
"""
from typing import Callable, Optional
import customtkinter as ctk


class KPICard(ctk.CTkFrame):
    """Modern metric summary card with icon, value, title, trend indicator, and full-card click navigation."""

    def __init__(
        self,
        master,
        title: str,
        value: str,
        subtitle: str = "",
        icon: str = "📊",
        accent_color: str = "#06B6D4",
        command: Optional[Callable[[], None]] = None,
        action_hint: Optional[str] = None,
        badge_tint: Optional[tuple] = None,
        **kwargs,
    ):
        super().__init__(master, corner_radius=12, **kwargs)
        self.accent_color = accent_color
        self.command = command
        self.action_hint = action_hint

        # Theme-aware card colors (Clinical Analytics: Deep Navy in dark, Clean Crisp White in light)
        self.normal_bg = ("#FFFFFF", "#131E36")
        self.hover_bg = ("#F8FAFC", "#1A2847")
        self.press_bg = ("#F1F5F9", "#1E3163")
        self.normal_border = ("#E2E8F0", "#223456")
        self.hover_border = accent_color

        self.configure(
            fg_color=self.normal_bg,
            border_width=1,
            border_color=self.normal_border,
        )

        # Main layout
        self.grid_columnconfigure(0, weight=1)

        # Top row: Title and Icon badge
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=16, pady=(14, 4))

        self.title_label = ctk.CTkLabel(
            top_frame,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        tint_bg = badge_tint if badge_tint else ("#E0F2FE", "#0C2340")
        self.icon_badge = ctk.CTkLabel(
            top_frame,
            text=icon,
            font=ctk.CTkFont(size=18),
            width=36,
            height=36,
            corner_radius=8,
            fg_color=tint_bg,
            text_color=accent_color,
        )
        self.icon_badge.pack(side="right")

        # Metric Value
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=("#0A192F", "#F8FAFC"),
            anchor="w",
        )
        self.value_label.pack(fill="x", padx=16, pady=(2, 2))

        # Bottom Subtitle / trend indicator & Navigation Hint
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.subtitle_label = ctk.CTkLabel(
            bottom_frame,
            text=subtitle if subtitle else "—",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
            justify="left",
            wraplength=170,
        )
        self.subtitle_label.pack(fill="x", anchor="w", pady=(0, 4))

        # Interactive navigation affordance chip on a dedicated separate line
        self.hint_label = None
        if command:
            hint_text = action_hint if action_hint else "Open →"
            self.hint_label = ctk.CTkLabel(
                bottom_frame,
                text=hint_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=accent_color,
                anchor="w",
            )
            self.hint_label.pack(fill="x", anchor="w")

        # Responsive card resize listener for dynamic wrapping
        self.bind("<Configure>", self._on_card_resize, add="+")

        # Attach interactive mouse & keyboard handlers if command is provided
        if command:
            self._setup_interactivity()

    def _on_card_resize(self, event=None) -> None:
        """Dynamically adapt text wrapping so descriptions and hints never overlap or clip."""
        try:
            scaling = self._get_widget_scaling() if hasattr(self, "_get_widget_scaling") else 1.0
            card_w = self.winfo_width() / scaling
            if card_w > 50:
                usable = max(110, int(card_w - 32))
                if hasattr(self, "subtitle_label") and self.subtitle_label.winfo_exists():
                    curr = self.subtitle_label.cget("wraplength")
                    if abs(usable - curr) > 8:
                        self.subtitle_label.configure(wraplength=usable)
        except Exception:
            pass

    def _setup_interactivity(self) -> None:
        """Bind recursive hover, pointer cursor, and click triggers to whole card."""
        widgets = self._get_all_descendants(self)
        for w in widgets:
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")
            w.bind("<ButtonPress-1>", self._on_press, add="+")
            w.bind("<ButtonRelease-1>", self._on_release, add="+")

        # Keyboard accessibility when card has focus
        self.bind("<Return>", lambda e: self._invoke_command())
        self.bind("<space>", lambda e: self._invoke_command())
        self.bind("<FocusIn>", lambda e: self._on_focus_in())
        self.bind("<FocusOut>", lambda e: self._on_focus_out())

    def _get_all_descendants(self, parent) -> list:
        """Return list of parent and all nested child widgets."""
        result = [parent]
        for child in parent.winfo_children():
            result.extend(self._get_all_descendants(child))
        return result

    def _on_enter(self, event=None) -> None:
        """Subtle hover feedback: brighten background and highlight border with accent color."""
        self.configure(fg_color=self.hover_bg, border_color=self.hover_border)

    def _on_leave(self, event=None) -> None:
        """Revert styling when pointer exits card."""
        self.configure(fg_color=self.normal_bg, border_color=self.normal_border)

    def _on_press(self, event=None) -> None:
        """Click down press feedback."""
        self.configure(fg_color=self.press_bg)

    def _on_release(self, event=None) -> None:
        """Trigger navigation on mouse release and restore hover state."""
        self.configure(fg_color=self.hover_bg)
        self._invoke_command()

    def _on_focus_in(self) -> None:
        """Keyboard focus border highlight."""
        self.configure(border_color=self.hover_border)

    def _on_focus_out(self) -> None:
        """Revert border when keyboard focus leaves."""
        self.configure(border_color=self.normal_border)

    def _invoke_command(self) -> None:
        """Execute bound navigation action safely."""
        if self.command and callable(self.command):
            try:
                self.command()
            except Exception as e:
                print(f"Error in KPI Card navigation: {e}")

    def update_value(self, new_value: str, new_subtitle: str = None) -> None:
        """Dynamically update card metric value and subtitle."""
        self.value_label.configure(text=new_value)
        if new_subtitle and hasattr(self, "subtitle_label"):
            self.subtitle_label.configure(text=new_subtitle)

