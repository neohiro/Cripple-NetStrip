"""
Cripper GUI Theme — Design system constants for a premium dark interface.
All colors, fonts, spacing, and styling tokens are defined here.
"""


# ──────────────────────────────────────────────
#  Color Palette
# ──────────────────────────────────────────────

class Colors:
    """Central color palette for the entire application."""

    # Backgrounds (layered depth)
    BG_DARKEST = "#06060b"       # Window background / deepest layer
    BG_DARK = "#0a0a12"          # Main content area
    BG_PANEL = "#101019"         # Panels, cards, sidebar
    BG_ELEVATED = "#16161f"      # Elevated elements (hover states, modals)
    BG_INPUT = "#1a1a26"         # Input fields, text areas

    # Accent — Purple to Cyan gradient
    ACCENT_PRIMARY = "#7c3aed"   # Primary purple
    ACCENT_SECONDARY = "#6d28d9" # Deeper purple (pressed states)
    ACCENT_LIGHT = "#a78bfa"     # Light purple (hover, highlights)
    ACCENT_CYAN = "#06b6d4"      # Cyan accent for contrast
    ACCENT_CYAN_DARK = "#0891b2" # Darker cyan

    # Semantic colors
    SUCCESS = "#22c55e"          # Allowed, active, good
    SUCCESS_DIM = "#166534"      # Success background
    WARNING = "#eab308"          # Caution, pending
    WARNING_DIM = "#713f12"      # Warning background
    DANGER = "#ef4444"           # Blocked, error, critical
    DANGER_DIM = "#7f1d1d"       # Danger background
    INFO = "#3b82f6"             # Informational

    # Text
    TEXT_PRIMARY = "#e2e8f0"     # Main text
    TEXT_SECONDARY = "#94a3b8"   # Muted text, labels
    TEXT_TERTIARY = "#64748b"    # Disabled, placeholder
    TEXT_INVERSE = "#0f172a"     # Text on light backgrounds

    # Borders
    BORDER_SUBTLE = "#1e1e2e"    # Subtle panel borders
    BORDER_DEFAULT = "#2a2a3d"   # Default borders
    BORDER_HOVER = "#3a3a55"     # Hover state borders

    # Mode colors
    MODE_PARANOID = "#ef4444"    # Red — maximum protection
    MODE_NORMAL = "#eab308"      # Yellow — balanced
    MODE_LOOSE = "#22c55e"       # Green — permissive

    # Mode glow colors (for animated effects)
    MODE_PARANOID_GLOW = "#dc2626"
    MODE_NORMAL_GLOW = "#ca8a04"
    MODE_LOOSE_GLOW = "#16a34a"

    # Category colors (for connection types)
    CAT_AD = "#f97316"           # Orange — advertisements
    CAT_TRACKER = "#ef4444"      # Red — trackers
    CAT_TELEMETRY = "#a855f7"    # Purple — telemetry
    CAT_MALWARE = "#dc2626"      # Dark red — malware
    CAT_ESSENTIAL = "#22c55e"    # Green — essential
    CAT_USER_ALLOWED = "#3b82f6" # Blue — user-allowed
    CAT_UNKNOWN = "#64748b"      # Gray — unknown
    CAT_LAN = "#06b6d4"          # Cyan — LAN
    CAT_USER_BLOCKED = "#f43f5e"   # Rose — user blocked (visually distinct)
    CAT_UPDATE = "#0ea5e9"      # Sky blue — app/OS update connections
    CAT_SECURITY = "#8b5cf6"    # Violet — security/background noise
    CAT_SYSTEM = "#9ca3af"      # Slate — OS system processes

    # Shield indicator
    SHIELD_ACTIVE = "#22c55e"
    SHIELD_WARNING = "#eab308"
    SHIELD_DANGER = "#ef4444"
    SHIELD_INACTIVE = "#64748b"


# ──────────────────────────────────────────────
#  Typography
# ──────────────────────────────────────────────

class Fonts:
    """Font families and size scale."""

    # Font families (in preference order per platform)
    FAMILY_PRIMARY = ("Inter", "Segoe UI", "SF Pro Display", "Ubuntu", "sans-serif")
    FAMILY_MONO = ("JetBrains Mono", "Cascadia Code", "SF Mono", "Ubuntu Mono", "monospace")

    # Size scale
    SIZE_XS = 10
    SIZE_SM = 11
    SIZE_BASE = 13
    SIZE_MD = 14
    SIZE_LG = 16
    SIZE_XL = 20
    SIZE_2XL = 24
    SIZE_3XL = 32
    SIZE_4XL = 40

    # Weight
    WEIGHT_NORMAL = "normal"
    WEIGHT_BOLD = "bold"


# ──────────────────────────────────────────────
#  Spacing & Layout
# ──────────────────────────────────────────────

class Spacing:
    """Consistent spacing tokens (in pixels)."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32
    XXXL = 48

    # Specific layout dimensions
    SIDEBAR_WIDTH = 220
    SIDEBAR_COLLAPSED_WIDTH = 64
    STAT_CARD_HEIGHT = 100
    TABLE_ROW_HEIGHT = 40
    NOTIFICATION_WIDTH = 380
    NOTIFICATION_HEIGHT = 160

    # Border radius
    RADIUS_SM = 6
    RADIUS_MD = 10
    RADIUS_LG = 14
    RADIUS_XL = 20
    RADIUS_FULL = 999  # Pill shape


# ──────────────────────────────────────────────
#  Animation Timing
# ──────────────────────────────────────────────

class Animation:
    """Animation duration and easing constants (milliseconds)."""

    FAST = 150
    NORMAL = 250
    SLOW = 400
    VERY_SLOW = 600

    # Update intervals
    CONNECTION_POLL_MS = 300     # Connection monitor poll rate
    STATS_UPDATE_MS = 2000       # Dashboard stats refresh
    ACTIVITY_FEED_MS = 500       # Activity feed scroll
    NOTIFICATION_DURATION = 15000 # Toast notification auto-dismiss
    SHIELD_PULSE_MS = 2000       # Shield pulse animation cycle


# ──────────────────────────────────────────────
#  Icons (Unicode symbols for lightweight icons)
# ──────────────────────────────────────────────

class Icons:
    """Unicode/emoji icons used throughout the UI."""

    # Navigation
    DASHBOARD = "⬡"      # Hexagon
    CONNECTIONS = "⇄"     # Bidirectional
    APPS = "◫"            # Grid
    BLOCKLIST = "⊘"       # Blocked
    LOGS = "☰"            # Menu/list
    SETTINGS = "⚙"        # Gear

    # Status
    SHIELD_ON = "🛡"       # Shield
    SHIELD_OFF = "⊗"      # Crossed circle
    BLOCKED = "✕"         # X mark
    ALLOWED = "✓"         # Checkmark
    PENDING = "◌"         # Dotted circle
    WARNING = "⚠"         # Warning triangle

    # Mode
    PARANOID = "🔒"        # Lock
    NORMAL = "🔰"          # Shield with check
    LOOSE = "🔓"           # Unlock

    # Categories
    AD = "📢"              # Advertisement
    TRACKER = "👁"         # Eye / tracking
    TELEMETRY = "📡"       # Satellite dish
    MALWARE = "☠"         # Skull
    ESSENTIAL = "✦"       # Star
    LAN = "🖧"             # Network

    # Actions
    REFRESH = "↻"         # Refresh
    SEARCH = "🔍"          # Search
    EXPORT = "↗"          # Export
    TRASH = "🗑"           # Delete
    PAUSE = "⏸"           # Pause
    PLAY = "▶"            # Play


# ──────────────────────────────────────────────
#  customtkinter Theme Config
# ──────────────────────────────────────────────

# These are passed to CTk widget constructors for consistent styling
CTK_BUTTON_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 0,
    "fg_color": Colors.ACCENT_PRIMARY,
    "hover_color": Colors.ACCENT_LIGHT,
    "text_color": Colors.TEXT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
}

CTK_BUTTON_SECONDARY_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 1,
    "fg_color": "transparent",
    "hover_color": Colors.BG_ELEVATED,
    "border_color": Colors.BORDER_DEFAULT,
    "text_color": Colors.TEXT_SECONDARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
}

CTK_BUTTON_DANGER_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 0,
    "fg_color": Colors.DANGER,
    "hover_color": "#dc2626",
    "text_color": Colors.TEXT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
}

CTK_FRAME_STYLE = {
    "corner_radius": Spacing.RADIUS_LG,
    "fg_color": Colors.BG_PANEL,
    "border_width": 1,
    "border_color": Colors.BORDER_SUBTLE,
}

CTK_ENTRY_STYLE = {
    "corner_radius": Spacing.RADIUS_SM,
    "fg_color": Colors.BG_INPUT,
    "border_width": 1,
    "border_color": Colors.BORDER_DEFAULT,
    "text_color": Colors.TEXT_PRIMARY,
    "placeholder_text_color": Colors.TEXT_TERTIARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
}

CTK_LABEL_STYLE = {
    "text_color": Colors.TEXT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
}

CTK_LABEL_MUTED_STYLE = {
    "text_color": Colors.TEXT_SECONDARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_SM),
}

CTK_SWITCH_STYLE = {
    "progress_color": Colors.ACCENT_PRIMARY,
    "button_color": Colors.TEXT_PRIMARY,
    "button_hover_color": Colors.ACCENT_LIGHT,
    "fg_color": Colors.BORDER_DEFAULT,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE),
    "text_color": Colors.TEXT_PRIMARY,
}


# ──────────────────────────────────────────────
#  Category Helpers
# ──────────────────────────────────────────────

def get_category_color(category) -> str:
    """Return the theme color for a connection category."""
    if hasattr(category, 'value'):
        category = category.value
    category = str(category).lower()
    mapping = {
        'ad': Colors.CAT_AD, 'tracker': Colors.CAT_TRACKER,
        'telemetry': Colors.CAT_TELEMETRY, 'malware': Colors.CAT_MALWARE,
        'essential': Colors.CAT_ESSENTIAL, 'user_allowed': Colors.CAT_USER_ALLOWED,
        'user_blocked': Colors.CAT_USER_BLOCKED, 'unknown': Colors.CAT_UNKNOWN,
        'lan': Colors.CAT_LAN, 'update': Colors.CAT_UPDATE, 'security': Colors.CAT_SECURITY,
        'dns': Colors.INFO, 'system': Colors.CAT_SYSTEM,
    }
    return mapping.get(category, Colors.CAT_UNKNOWN)


def get_category_label(category) -> str:
    """Return a human-readable label for a connection category."""
    if hasattr(category, 'value'):
        category = category.value
    category = str(category).lower()
    mapping = {
        'ad': 'Advertisement', 'tracker': 'Tracker', 'telemetry': 'Telemetry',
        'malware': 'Malware', 'essential': 'Essential', 'user_allowed': 'Allowed',
        'user_blocked': 'Blocked', 'unknown': 'Unknown', 'lan': 'LAN',
        'update': 'Update', 'security': 'Security', 'dns': 'DNS',
        'system': 'System',
    }
    return mapping.get(category, category.title() if category != 'unknown' else 'Unknown')


def get_category_icon(category) -> str:
    """Return a unicode icon for a connection category."""
    if hasattr(category, 'value'):
        category = category.value
    category = str(category).lower()
    mapping = {
        'ad': Icons.AD, 'tracker': Icons.TRACKER, 'telemetry': Icons.TELEMETRY,
        'malware': Icons.MALWARE, 'essential': Icons.ESSENTIAL,
        'user_allowed': Icons.ALLOWED, 'user_blocked': Icons.BLOCKED,
        'lan': Icons.LAN, 'update': Icons.REFRESH, 'security': "🛡",
        'dns': "🌐", 'system': "⚙",
    }
    return mapping.get(category, Icons.PENDING)
