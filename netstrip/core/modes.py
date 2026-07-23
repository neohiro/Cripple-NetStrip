"""
NetStrip Protection Modes — Defines the three filtering modes
and their associated rules and behaviors.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List


class ProtectionLevel(Enum):
    """The core protection modes."""
    PARANOID = auto()
    STRICT = auto()     # Alias for PARANOID (CLI compatibility)
    NORMAL = auto()
    STANDARD = auto()   # Alias for NORMAL (CLI compatibility)
    LOOSE = auto()


class ConnectionCategory(Enum):
    """Classification categories for network connections."""
    AD = "ad"
    TRACKER = "tracker"
    TELEMETRY = "telemetry"
    MALWARE = "malware"
    ESSENTIAL = "essential"
    USER_ALLOWED = "user_allowed"
    USER_BLOCKED = "user_blocked"
    UNKNOWN = "unknown"
    LAN = "lan"
    UPDATE = "update"
    SECURITY = "security"
    DNS = "dns"
    SYSTEM = "system"


class ConnectionAction(Enum):
    """What to do with a connection."""
    ALLOW = "allow"
    BLOCK = "block"
    ASK = "ask"           # Prompt the user
    SINKHOLE = "sinkhole" # DNS sinkhole (return 0.0.0.0)


class ConnectionProtocol(Enum):
    """Network protocol type."""
    TCP = "tcp"
    UDP = "udp"
    DNS = "dns"


@dataclass
class ModeConfig:
    """Configuration for a protection mode."""
    level: ProtectionLevel
    name: str
    description: str
    icon: str
    color: str

    # What to do with each category
    block_ads: bool = True
    block_trackers: bool = True
    block_telemetry: bool = True
    block_malware: bool = True
    block_unknown: bool = False
    block_lan: bool = True
    block_updates: bool = False
    block_security: bool = False
    ask_on_unknown: bool = False

    # LAN behavior
    lan_full_isolation: bool = False
    lan_allow_gateway: bool = True
    lan_allow_dhcp: bool = True
    lan_allow_dns: bool = True

    # Categories that are always blocked regardless of mode
    always_blocked: List[ConnectionCategory] = field(default_factory=lambda: [
        ConnectionCategory.MALWARE,
        ConnectionCategory.TRACKER,
    ])

    def get_action_for_category(self, category: ConnectionCategory, db=None) -> ConnectionAction:
        """Determine what action to take for a given connection category."""
        if self.level == ProtectionLevel.PARANOID:
            if category == ConnectionCategory.USER_ALLOWED:
                return ConnectionAction.ALLOW
            if category == ConnectionCategory.DNS:
                return ConnectionAction.ALLOW
            return ConnectionAction.BLOCK
            
        if category in self.always_blocked:
            return ConnectionAction.BLOCK

        if category == ConnectionCategory.USER_ALLOWED:
            return ConnectionAction.ALLOW
        if category == ConnectionCategory.USER_BLOCKED:
            return ConnectionAction.BLOCK
            
        if category in (ConnectionCategory.SECURITY, ConnectionCategory.SYSTEM):
            if self.level == ProtectionLevel.PARANOID and category == ConnectionCategory.SYSTEM:
                return ConnectionAction.BLOCK
            if hasattr(db, 'get_setting'):
                sys_val = db.get_setting("block_system_connections", "false")
            elif isinstance(db, dict):
                sys_val = db.get("block_system_connections", "false")
            else:
                sys_val = "false"
            if str(sys_val).lower() == "true":
                return ConnectionAction.BLOCK

        rules = {
            ConnectionCategory.AD: self.block_ads,
            ConnectionCategory.TELEMETRY: self.block_telemetry,
            ConnectionCategory.MALWARE: True,  # Always block
            ConnectionCategory.TRACKER: True,  # Always block
            ConnectionCategory.ESSENTIAL: False,  # Never block
            ConnectionCategory.DNS: False,  # Never block (we ARE the DNS)
            ConnectionCategory.UPDATE: self.block_updates,
            ConnectionCategory.SECURITY: self.block_security,
            ConnectionCategory.LAN: self.block_lan,
            ConnectionCategory.UNKNOWN: self.block_unknown,
        }

        should_block = rules.get(category, False)

        if should_block:
            return ConnectionAction.BLOCK
        elif category == ConnectionCategory.UNKNOWN and self.ask_on_unknown:
            return ConnectionAction.ASK
        else:
            return ConnectionAction.ALLOW


# ──────────────────────────────────────────────
#  Pre-configured modes
# ──────────────────────────────────────────────

PARANOID_MODE = ModeConfig(
    level=ProtectionLevel.PARANOID,
    name="Paranoid",
    description="Maximum protection. Blocks ALL connections not explicitly "
                "whitelisted. OS updates paused. Every unknown connection "
                "requires manual approval. Full LAN isolation.",
    icon="🔒",
    color="#ef4444",
    block_ads=True,
    block_trackers=True,
    block_telemetry=True,
    block_malware=True,
    block_unknown=True,     # Block unknown by default
    block_lan=True,
    block_updates=True,     # Even app/OS updates blocked
    block_security=True,    # Block OS security background noise
    ask_on_unknown=True,    # But prompt user for unknowns
    lan_full_isolation=True,
    lan_allow_gateway=True, # Still need internet
    lan_allow_dhcp=True,
    lan_allow_dns=True,
)

NORMAL_MODE = ModeConfig(
    level=ProtectionLevel.NORMAL,
    name="Normal",
    description="Balanced protection. Blocks known ads, trackers, and "
                "telemetry. Allows essential connections. Prompts for "
                "unrecognized connections. LAN isolated except essentials.",
    icon="🔰",
    color="#eab308",
    block_ads=True,
    block_trackers=True,
    block_telemetry=True,
    block_malware=True,
    block_unknown=False,    # Allow unknown by default
    block_lan=True,
    block_updates=False,    # Allow app/OS updates
    block_security=False,   # Allow OS security telemetry
    ask_on_unknown=False,   # Allow unknowns quietly so UI colors them green
    lan_full_isolation=False,
    lan_allow_gateway=True,
    lan_allow_dhcp=True,
    lan_allow_dns=True,
)

LOOSE_MODE = ModeConfig(
    level=ProtectionLevel.LOOSE,
    name="Loose",
    description="Minimal protection. Only blocks confirmed ad/tracker "
                "domains and malware. Allows most connections without "
                "prompting. LAN partially open. For maximum compatibility.",
    icon="🔓",
    color="#22c55e",
    block_ads=True,
    block_trackers=True,
    block_telemetry=False,  # Allow telemetry
    block_malware=True,
    block_unknown=False,
    block_lan=False,        # LAN open
    block_updates=False,
    block_security=False,
    ask_on_unknown=False,   # No prompts
    lan_full_isolation=False,
    lan_allow_gateway=True,
    lan_allow_dhcp=True,
    lan_allow_dns=True,
)

# Mode lookup
MODES = {
    ProtectionLevel.PARANOID: PARANOID_MODE,
    ProtectionLevel.STRICT: PARANOID_MODE,    # STRICT is an alias for PARANOID
    ProtectionLevel.NORMAL: NORMAL_MODE,
    ProtectionLevel.STANDARD: NORMAL_MODE,    # STANDARD is an alias for NORMAL
    ProtectionLevel.LOOSE: LOOSE_MODE,
}


def get_mode(level: ProtectionLevel) -> ModeConfig:
    """Get the mode configuration for a given protection level."""
    return MODES[level]
