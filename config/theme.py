"""Theme and styling definitions for CustomTkinter and Matplotlib."""

# Appearance Modes
APPEARANCE_MODES = ["Dark", "Light", "System"]
COLOR_THEMES = ["blue", "green", "dark-blue"]

# Palette Colors (Modern Healthcare Aesthetic)
THEME_COLORS = {
    "dark": {
        "bg_primary": "#12131C",
        "bg_secondary": "#1E202E",
        "bg_card": "#26293B",
        "bg_input": "#181A26",
        "text_primary": "#F1F5F9",
        "text_secondary": "#94A3B8",
        "text_muted": "#64748B",
        "accent": "#38BDF8",       # Sky Blue
        "accent_hover": "#0284C7",
        "success": "#22C55E",      # Green
        "warning": "#F59E0B",      # Amber
        "danger": "#EF4444",       # Rose Red
        "info": "#60A5FA",
        "border": "#334155",
        "chart_bg": "#1E202E",
        "chart_grid": "#334155",
    },
    "light": {
        "bg_primary": "#F8FAFC",
        "bg_secondary": "#FFFFFF",
        "bg_card": "#FFFFFF",
        "bg_input": "#F1F5F9",
        "text_primary": "#0F172A",
        "text_secondary": "#475569",
        "text_muted": "#94A3B8",
        "accent": "#0284C7",       # Ocean Blue
        "accent_hover": "#0369A1",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
        "info": "#2563EB",
        "border": "#E2E8F0",
        "chart_bg": "#FFFFFF",
        "chart_grid": "#E2E8F0",
    },
}

def get_matplotlib_style(mode: str = "dark") -> dict:
    """Return styling parameters for Matplotlib figures matching the current theme."""
    mode_key = "dark" if mode.lower() in ("dark", "system") else "light"
    palette = THEME_COLORS[mode_key]

    return {
        "figure.facecolor": palette["chart_bg"],
        "axes.facecolor": palette["chart_bg"],
        "axes.edgecolor": palette["border"],
        "axes.labelcolor": palette["text_primary"],
        "xtick.color": palette["text_secondary"],
        "ytick.color": palette["text_secondary"],
        "text.color": palette["text_primary"],
        "grid.color": palette["chart_grid"],
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
        "figure.autolayout": True,
    }
