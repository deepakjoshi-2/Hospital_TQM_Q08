"""Theme and styling definitions for CustomTkinter and Matplotlib.
Distinctive visual identity: MedCare Premium Healthcare SaaS (Deep Midnight Navy + Electric Cyan + Ocean Blue).
Directly matches the visual language of MedCare Hospital Management Homepage reference.
"""
from typing import Dict, Any

# Appearance Modes
APPEARANCE_MODES = ["Dark", "Light", "System"]
COLOR_THEMES = ["blue", "green", "dark-blue"]

# Palette Colors (Premium Healthcare SaaS Aesthetic)
THEME_COLORS: Dict[str, Dict[str, str]] = {
    "dark": {
        "bg_primary": "#070D1E",       # Deep midnight navy canvas (matches reference header/cards)
        "bg_secondary": "#0B152B",     # Deep navy sidebar and navigation panels
        "bg_card": "#0F1E3D",          # Elevated dark navy card
        "bg_card_hover": "#16284F",    # Luminous card hover state
        "bg_card_glass": "#0D1B36",    # Semi-translucent glassmorphic card
        "bg_input": "#070E20",         # Deep recessed input field
        "text_primary": "#FFFFFF",     # Pure crisp white text
        "text_secondary": "#94A3B8",   # Slate text for secondary details
        "text_muted": "#64748B",       # Muted annotation text
        "accent": "#0284C7",           # Clinical Ocean Blue
        "accent_cyan": "#06B6D4",      # Electric Cyan highlight
        "accent_mint": "#10B981",      # Surgical Mint
        "accent_hover": "#0369A1",     # Deep ocean blue hover
        "success": "#10B981",          # Success green
        "warning": "#F59E0B",          # Clinical amber
        "danger": "#EF4444",           # Rose red
        "info": "#38BDF8",             # Sky blue
        "border": "#1E3258",           # Hairline navy card border
        "border_subtle": "#132240",    # Very subtle card separator
        "border_focus": "#06B6D4",     # Electric cyan focus glow
        "badge_bg": "#0B2744",         # Pill badge dark tint
        "badge_text": "#38BDF8",       # Pill badge cyan text
        "hero_badge_bg": "#08233C",    # Hero tagline capsule background
        "hero_badge_border": "#0E5280",# Hero tagline capsule border
        "stat_card_bg": "#0F1E3D",     # Stats bar card
        "chart_bg": "#0F1E3D",         # Blends with dark card background
        "chart_grid": "#1A2C4E",       # Subtle chart gridline
    },
    "light": {
        "bg_primary": "#F0F6FC",       # Crisp icy-slate canvas
        "bg_secondary": "#FFFFFF",     # Pure clinical white navigation
        "bg_card": "#FFFFFF",          # Elevated white card
        "bg_card_hover": "#F8FAFC",    # Subtle light card hover
        "bg_card_glass": "#FFFFFF",    # Crisp glassmorphic card
        "bg_input": "#F8FAFC",         # Soft recessed input field
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
        "border_subtle": "#E2E8F0",    # Subtle separator
        "border_focus": "#0284C7",
        "badge_bg": "#E0F2FE",         # Pill badge light tint
        "badge_text": "#0369A1",       # Pill badge deep blue text
        "hero_badge_bg": "#E0F2FE",    # Hero tagline capsule background
        "hero_badge_border": "#BAE6FD",# Hero tagline capsule border
        "stat_card_bg": "#FFFFFF",     # Stats bar card in light mode
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

def get_theme_color(token: str, mode: str = "dark") -> str:
    """Retrieve color hex value safely by token and appearance mode."""
    mode_key = "dark" if mode.lower() in ("dark", "system") else "light"
    return THEME_COLORS[mode_key].get(token, THEME_COLORS[mode_key]["accent"])

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
