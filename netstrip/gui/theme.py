"""
Cripple GUI Theme — Design system constants for a premium dark interface.
All colors, fonts, spacing, and styling tokens are defined here.
Optimized for 4K, soft rounded vibe, professional polish.
"""


# ──────────────────────────────────────────────
#  Color Palette — 4K HDR-ready, soft rounded vibe
# ──────────────────────────────────────────────

class Colors:
    """Central color palette for the entire application."""

    # Backgrounds (layered depth) — softer, warmer darks for 4K comfort
    BG_DARKEST = "#040408"       # Window background / deepest layer — near-black with blue tint
    BG_DARK = "#09090f"          # Main content area
    BG_PANEL = "#0f0f17"         # Panels, cards, sidebar — elevated surface
    BG_ELEVATED = "#15151e"      # Elevated elements (hover states, modals)
    BG_INPUT = "#1b1b27"         # Input fields, text areas
    BG_CARD = "#11111a"          # Card backgrounds — distinct from panels
    BG_SURFACE = "#14141d"       # Generic surface background

    # Accent — Purple to Cyan gradient, refined for 4K vibrancy
    ACCENT_PRIMARY = "#8b5cf6"   # Primary purple — brighter, more vibrant
    ACCENT_SECONDARY = "#7c3aed" # Deeper purple (pressed states)
    ACCENT_TERTIARY = "#a855f7"  # Tertiary purple
    ACCENT_LIGHT = "#c084fc"     # Light purple (hover, highlights, glow)
    ACCENT_CYAN = "#22d3ee"      # Cyan accent for contrast — more vivid
    ACCENT_CYAN_DARK = "#06b6d4" # Darker cyan
    ACCENT_CYAN_LIGHT = "#67e8f9" # Light cyan

    # Gradient stops for bloom effects
    GRADIENT_START = "#8b5cf6"
    GRADIENT_MID = "#a855f7"
    GRADIENT_END = "#22d3ee"

    # Semantic colors — softer, more readable
    SUCCESS = "#34d399"          # Allowed, active, good — emerald
    SUCCESS_DIM = "#064e3b"      # Success background
    SUCCESS_GLOW = "#10b981"     # Success glow
    WARNING = "#fbbf24"          # Caution, pending — amber
    WARNING_DIM = "#78350f"      # Warning background
    WARNING_GLOW = "#f59e0b"     # Warning glow
    DANGER = "#f87171"           # Blocked, error, critical — soft red
    DANGER_DIM = "#7f1d1d"       # Danger background
    DANGER_GLOW = "#ef4444"      # Danger glow
    INFO = "#60a5fa"             # Informational — soft blue
    INFO_GLOW = "#3b82f6"        # Info glow

    # Text — high contrast for 4K readability
    TEXT_PRIMARY = "#f1f5f9"     # Main text — near-white
    TEXT_SECONDARY = "#94a3b8"   # Muted text, labels
    TEXT_TERTIARY = "#64748b"    # Disabled, placeholder
    TEXT_INVERSE = "#0f172a"     # Text on light backgrounds
    TEXT_ACCENT = "#c084fc"      # Accent text

    # Borders — subtle, glassmorphism-ready
    BORDER_SUBTLE = "#1e1e2e"    # Subtle panel borders
    BORDER_DEFAULT = "#27273a"   # Default borders
    BORDER_HOVER = "#3a3a55"     # Hover state borders
    BORDER_GLOW = "#8b5cf6"      # Glow border for focus/active
    BORDER_CARD = "#1f1f2e"      # Card borders

    # Mode colors
    MODE_GHOST = "#f87171"       # Red — maximum protection
    MODE_PARANOID = "#f87171"    # Alias
    MODE_NORMAL = "#fbbf24"      # Yellow — balanced
    MODE_LOOSE = "#34d399"       # Green — permissive

    # Mode glow colors (for animated effects)
    MODE_GHOST_GLOW = "#ef4444"
    MODE_PARANOID_GLOW = "#ef4444"
    MODE_NORMAL_GLOW = "#f59e0b"
    MODE_LOOSE_GLOW = "#10b981"

    # Category colors (for connection types) — vibrant but harmonious
    CAT_AD = "#fb923c"           # Orange — advertisements
    CAT_TRACKER = "#f87171"      # Red — trackers
    CAT_TELEMETRY = "#c084fc"    # Purple — telemetry
    CAT_MALWARE = "#ef4444"      # Dark red — malware
    CAT_ESSENTIAL = "#34d399"    # Green — essential
    CAT_USER_ALLOWED = "#60a5fa" # Blue — user-allowed
    CAT_UNKNOWN = "#64748b"      # Gray — unknown
    CAT_LAN = "#22d3ee"          # Cyan — LAN
    CAT_USER_BLOCKED = "#f472b6" # Rose — user blocked (visually distinct)
    CAT_UPDATE = "#38bdf8"       # Sky blue — app/OS update connections
    CAT_SECURITY = "#a855f7"     # Violet — security/background noise
    CAT_SYSTEM = "#9ca3af"       # Slate — OS system processes

    # Shield indicator
    SHIELD_ACTIVE = "#34d399"
    SHIELD_WARNING = "#fbbf24"
    SHIELD_DANGER = "#f87171"
    SHIELD_INACTIVE = "#64748b"

    # Glassmorphism / frosted glass
    GLASS_WHITE = "rgba(255, 255, 255, 0.04)"
    GLASS_BORDER = "rgba(255, 255, 255, 0.08)"
    GLASS_HOVER = "rgba(139, 92, 246, 0.12)"


# ──────────────────────────────────────────────
#  Typography — 4K optimized scale
# ──────────────────────────────────────────────

class Fonts:
    """Font families and size scale."""

    # Font families (in preference order per platform)
    FAMILY_PRIMARY = ("Inter", "Segoe UI Variable", "Segoe UI", "SF Pro Display", "Ubuntu", "sans-serif")
    FAMILY_MONO = ("JetBrains Mono", "Cascadia Code", "SF Mono", "Ubuntu Mono", "monospace")

    # Size scale — slightly larger for 4K readability
    SIZE_XS = 11
    SIZE_SM = 12
    SIZE_BASE = 14
    SIZE_MD = 15
    SIZE_LG = 17
    SIZE_XL = 22
    SIZE_2XL = 28
    SIZE_3XL = 36
    SIZE_4XL = 44

    # Weight
    WEIGHT_NORMAL = "normal"
    WEIGHT_MEDIUM = "500"
    WEIGHT_BOLD = "bold"
    WEIGHT_EXTRABOLD = "800"


# ──────────────────────────────────────────────
#  Spacing & Layout — generous for 4K
# ──────────────────────────────────────────────

class Spacing:
    """Consistent spacing tokens (in pixels)."""

    XS = 6
    SM = 10
    MD = 14
    LG = 20
    XL = 28
    XXL = 36
    XXXL = 56

    # Specific layout dimensions
    SIDEBAR_WIDTH = 260
    SIDEBAR_COLLAPSED_WIDTH = 72
    STAT_CARD_HEIGHT = 120
    TABLE_ROW_HEIGHT = 44
    NOTIFICATION_WIDTH = 420
    NOTIFICATION_HEIGHT = 180

    # Border radius — softer, more rounded for premium feel
    RADIUS_SM = 8
    RADIUS_MD = 12
    RADIUS_LG = 16
    RADIUS_XL = 24
    RADIUS_2XL = 32
    RADIUS_FULL = 999  # Pill shape


# ──────────────────────────────────────────────
#  Animation Timing — smoother, more premium
# ──────────────────────────────────────────────

class Animation:
    """Animation duration and easing constants (milliseconds)."""

    FAST = 120
    NORMAL = 200
    SLOW = 350
    VERY_SLOW = 500
    BLOOM = 400  # Bloom hover effect duration

    # Update intervals
    CONNECTION_POLL_MS = 250     # Connection monitor poll rate — faster for snappy feel
    STATS_UPDATE_MS = 1500       # Dashboard stats refresh — faster
    ACTIVITY_FEED_MS = 400       # Activity feed scroll
    NOTIFICATION_DURATION = 12000 # Toast notification auto-dismiss
    SHIELD_PULSE_MS = 2500       # Shield pulse animation cycle


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
    SHIELD = "🛡"          # Shield (alias)
    SHIELD_ON = "🛡"       # Shield
    SHIELD_OFF = "⊗"      # Crossed circle
    BLOCKED = "✕"         # X mark
    ALLOWED = "✓"         # Checkmark
    PENDING = "◌"         # Dotted circle
    WARNING = "⚠"         # Warning triangle
    UPDATE = "↻"          # Update / Sync

    # Mode
    GHOST = "👻"          # Ghost
    PARANOID = "👻"       # Alias
    NORMAL = "🔰"          # Shield with check
    LOOSE = "🔓"           # Unlock

    # Categories
    AD = "📢"              # Advertisement
    TRACKER = "👁"         # Eye / tracking
    TELEMETRY = "📡"       # Satellite dish
    MALWARE = "☠"         # Skull
    ESSENTIAL = "✦"       # Star
    LAN = "🖧"             # Network
    SYSTEM = "💻"          # System / OS

    # Actions
    REFRESH = "↻"         # Refresh
    SEARCH = "🔍"          # Search
    EXPORT = "↗"          # Export
    TRASH = "🗑"           # Delete
    PAUSE = "⏸"           # Pause
    PLAY = "▶"            # Play


# ──────────────────────────────────────────────
#  customtkinter Theme Config — 4K ready, soft rounded
# ──────────────────────────────────────────────

# These are passed to CTk widget constructors for consistent styling
CTK_BUTTON_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 0,
    "fg_color": Colors.ACCENT_PRIMARY,
    "hover_color": Colors.ACCENT_LIGHT,
    "text_color": Colors.TEXT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
}

CTK_BUTTON_SECONDARY_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 1,
    "fg_color": "transparent",
    "hover_color": Colors.BG_ELEVATED,
    "border_color": Colors.BORDER_DEFAULT,
    "text_color": Colors.TEXT_SECONDARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
}

CTK_BUTTON_DANGER_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 0,
    "fg_color": Colors.DANGER,
    "hover_color": Colors.DANGER_GLOW,
    "text_color": Colors.TEXT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
}

CTK_BUTTON_SUCCESS_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 0,
    "fg_color": Colors.SUCCESS,
    "hover_color": Colors.SUCCESS_GLOW,
    "text_color": Colors.TEXT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
}

CTK_BUTTON_GHOST_STYLE = {
    "corner_radius": Spacing.RADIUS_MD,
    "border_width": 1,
    "fg_color": "transparent",
    "hover_color": Colors.GLASS_HOVER,
    "border_color": Colors.BORDER_GLOW,
    "text_color": Colors.ACCENT_PRIMARY,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
}

CTK_FRAME_STYLE = {
    "corner_radius": Spacing.RADIUS_LG,
    "fg_color": Colors.BG_PANEL,
    "border_width": 1,
    "border_color": Colors.BORDER_SUBTLE,
}

CTK_FRAME_CARD_STYLE = {
    "corner_radius": Spacing.RADIUS_XL,
    "fg_color": Colors.BG_CARD,
    "border_width": 1,
    "border_color": Colors.BORDER_CARD,
}

CTK_FRAME_GLASS_STYLE = {
    "corner_radius": Spacing.RADIUS_XL,
    "fg_color": Colors.GLASS_WHITE,
    "border_width": 1,
    "border_color": Colors.GLASS_BORDER,
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

CTK_LABEL_ACCENT_STYLE = {
    "text_color": Colors.TEXT_ACCENT,
    "font": (Fonts.FAMILY_PRIMARY[0], Fonts.SIZE_BASE, Fonts.WEIGHT_MEDIUM),
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
        'dns': Colors.INFO, 'system': Colors.CAT_SYSTEM, 'identity': '#8b5cf6',
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
        'system': 'System', 'identity': 'Identity',
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
        'dns': "🌐", 'system': Icons.SYSTEM, 'identity': '🪪',
    }
    return mapping.get(category, Icons.PENDING)
