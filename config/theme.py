"""Theme and styling definitions for CustomTkinter and Matplotlib.
Distinctive visual identity: Premium Clinical Analytics (Deep Navy + Cyan/Teal + Restrained Mint).
"""

# Appearance Modes
APPEARANCE_MODES = ["Dark", "Light", "System"]
COLOR_THEMES = ["blue", "green", "dark-blue"]

# Palette Colors (Premium Clinical Analytics Aesthetic)
THEME_COLORS = {
    "dark": {
        "bg_primary": "#0A0F1D",       # Deep clinical midnight navy
        "bg_secondary": "#0F172A",     # Deep navy slate
        "bg_card": "#131E36",          # Dark navy-cyan card background
        "bg_card_hover": "#1A2847",    # Luminous card hover state
        "bg_input": "#0B132B",         # Deep recessed input field
        "text_primary": "#F8FAFC",     # Pure crisp slate white
        "text_secondary": "#94A3B8",   # Neutral technical slate
        "text_muted": "#64748B",       # Subdued technical text
        "accent": "#0284C7",           # Clinical Ocean Blue / Cyan
        "accent_cyan": "#06B6D4",      # Electric Cyan
        "accent_mint": "#10B981",      # Restrained surgical mint
        "accent_hover": "#0369A1",     # Deep cyan hover
        "success": "#10B981",          # Surgical Mint / Green
        "warning": "#F59E0B",          # Clinical Amber
        "danger": "#EF4444",           # Rose Red
        "info": "#38BDF8",             # Sky Blue
        "border": "#223456",           # Crisp navy hairline border
        "border_focus": "#06B6D4",     # Accent cyan focus
        "chart_bg": "#131E36",         # Blends with card background
        "chart_grid": "#1E2D4A",       # Subtle chart gridline
    },
    "light": {
        "bg_primary": "#F1F5F9",       # Crisp ice-slate
        "bg_secondary": "#FFFFFF",     # Pure clinical white
        "bg_card": "#FFFFFF",          # Elevated white card
        "bg_card_hover": "#F8FAFC",    # Subtle light hover
        "bg_input": "#F8FAFC",         # Soft recessed input
        "text_primary": "#0A192F",     # Deep clinical navy text
        "text_secondary": "#334E68",   # Technical slate text
        "text_muted": "#627D98",       # Muted annotation text
        "accent": "#0284C7",           # Ocean Cyan / Teal
        "accent_cyan": "#0891B2",      # Deep Teal
        "accent_mint": "#059669",      # Crisp Mint
        "accent_hover": "#0369A1",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
        "info": "#0284C7",
        "border": "#CBD5E1",           # Crisp light border
        "border_focus": "#0284C7",
        "chart_bg": "#FFFFFF",
        "chart_grid": "#E2E8F0",
    },
}

# Semantic KPI Accent Tokens (Consistent across both themes)
KPI_PALETTE = {
    "patients": {
        "accent": "#06B6D4",           # Vibrant Cyan
        "dark_tint": "#082F49",
        "light_tint": "#E0F2FE",
        "label": "PATIENTS",
    },
    "doctors": {
        "accent": "#10B981",           # Restrained Surgical Mint
        "dark_tint": "#064E3B",
        "light_tint": "#DCFCE7",
        "label": "PHYSICIANS",
    },
    "appointments": {
        "accent": "#F59E0B",           # Clinical Amber
        "dark_tint": "#451A03",
        "light_tint": "#FEF3C7",
        "label": "APPOINTMENTS",
    },
    "csat": {
        "accent": "#8B5CF6",           # Clinical Purple / Quality Star
        "dark_tint": "#2E1065",
        "light_tint": "#F3E8FF",
        "label": "SATISFACTION",
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
