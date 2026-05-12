# Utility: classify switches as access or non-access
def classify_switch(device: dict, vlan_counts: dict = None, port_security_count: int = None) -> str:
    """
    Classify switch as 'access', 'wan', 'server', 'mini', or 'other'.
    - NX-OS platform: server switch
    - Port count < 20: mini switch
    - VLAN or port-security count > 10: access switch
    - Otherwise: non-access (wan/server/other)
    """
    platform = (device.get("platform") or "").upper()
    ports = device.get("port_count", 0)
    if "NX-OS" in platform:
        return "server"
    if ports and ports < 20:
        return "mini"
    if vlan_counts:
        for vlan, count in vlan_counts.items():
            if vlan != 1 and count > 10:
                return "access"
    if port_security_count and port_security_count > 10:
        return "access"
    # Fallback: use device type or platform hints
    dev_type = device.get("type")
    if dev_type == "wan_switch":
        return "wan"
    if dev_type == "access":
        return "access"
    return "other"
"""
config.py — Central Configuration
====================================
All project settings in one place.
Import this in every script instead of hardcoding values.

Usage:
    from config import OUTPUT_DIR, DEVICE_SHAPES, CREDENTIALS
"""

import os
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR  = os.path.join(BASE_DIR, "output_diagrams")
INPUT_JSON  = os.path.join(BASE_DIR, "topology_data/Test/Test/Test/Test_topology_data_latest.json")
SCHEMA_FILE = os.path.join(BASE_DIR, "schemas", "topology_schema.json")

# ── Diagram settings ──────────────────────────────────────────────────────────
DIAGRAM_TITLE   = "Network Topology"
NODE_WIDTH      = 130
NODE_HEIGHT     = 80
TIER_SPACING_X  = 200          # horizontal gap between devices in same tier
TIER_SPACING_Y  = 180          # vertical gap between tiers
LINK_STYLE      = "endArrow=none;"
# ── Page/grid settings (A4-like fixed grid)
PAGE_WIDTH      = 1000         # approximate Draw.io units for A4 layout
PAGE_HEIGHT     = 1400
GRID_MARGIN     = 60           # margin around the grid
GRID_COLS       = 3            # fixed columns (3 A4 pages across)
GRID_ROWS       = 2            # fixed rows (2 A4 pages down)
# Vertical Y position for each device tier
TIER_Y = {
    "isp":         50,   # ISP Links at top
    "wan_switch": 150,  # WAN Switch for ISP connections
    "sdwan":      250,  # Velocloud SDWAN
    "firewall":   350,  # Firewall
    "router":     450,  # Core routers
    "dist":       550,  # Distribution switches
    "switch":     550,  # treat switches as distribution by default
    "access":     650,  # Access switches
    "server":     750,  # Servers at bottom
}

# ── Draw.io shape library ───────────────────────────────────────────────
# Use Draw.io's built-in Cisco shapes with complete style strings.
# These require the full Draw.io style format to render correctly.

# Base style template for Cisco shapes
_CISCO_BASE_STYLE = "sketch=0;html=1;pointerEvents=1;dashed=0;fillColor=#036897;strokeColor=#ffffff;strokeWidth=2;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;"

# Map device types to complete Draw.io style strings for Cisco shapes
DEVICE_SHAPES = {
    "router":       f"shape=mxgraph.cisco.routers.router;{_CISCO_BASE_STYLE}",
    "core_router":  f"shape=mxgraph.cisco.routers.router;{_CISCO_BASE_STYLE}",
    "edge_router":  f"shape=mxgraph.cisco.routers.router;{_CISCO_BASE_STYLE}",
    "switch":       f"shape=mxgraph.cisco.switches.workgroup_switch;{_CISCO_BASE_STYLE}",
    "dist":         f"shape=mxgraph.cisco.switches.switch;{_CISCO_BASE_STYLE}",
    "access":       f"shape=mxgraph.cisco.switches.workgroup_switch;{_CISCO_BASE_STYLE}",
    "wan_switch":   f"shape=mxgraph.cisco.switches.multilayer_switch;{_CISCO_BASE_STYLE}",
    "firewall":     f"shape=rectangle;{_CISCO_BASE_STYLE}fillColor=#FF6B6B;",  # Red square for firewall
    "asa":          f"shape=mxgraph.cisco.security.asa_5500;{_CISCO_BASE_STYLE}",
    "sdwan":        f"shape=mxgraph.cisco.routers.router;{_CISCO_BASE_STYLE}fillColor=#4CAF50;",  # Green for SDWAN
    "server":       f"shape=mxgraph.cisco.servers.server;{_CISCO_BASE_STYLE}",
    "ap":           f"shape=mxgraph.cisco.wireless.wireless_access_point;{_CISCO_BASE_STYLE}fontSize=9;width=180;height=120;",
    "wlc":          f"shape=mxgraph.cisco.wireless.wireless_lan_controller;{_CISCO_BASE_STYLE}",
    "loadbalancer": f"shape=mxgraph.cisco.load_balancers.load_balancer;{_CISCO_BASE_STYLE}",
    "cloud":        f"shape=mxgraph.cisco.misc.cloud;{_CISCO_BASE_STYLE}",
    "pc":           f"shape=mxgraph.cisco.endpoints.pc;{_CISCO_BASE_STYLE}",
    "ip_phone":     f"shape=mxgraph.cisco.endpoints.ip_phone;{_CISCO_BASE_STYLE}",
    "isp":          f"shape=rectangle;{_CISCO_BASE_STYLE}fillColor=#E3F2FD;",  # Light blue square for ISP
    "default":      f"shape=rectangle;{_CISCO_BASE_STYLE}",
}

# Platform keyword -> device type mapping
PLATFORM_TYPE_HINTS = [
    # High-capacity routers
    ("ASR", "core_router"),
    ("NEXUS", "core_router"),
    ("C7600", "core_router"),

    # Edge / branch routers
    ("ISR", "edge_router"),
    ("C1111", "edge_router"),
    ("C1100", "edge_router"),

    # SDWAN devices
    ("VELOCLOUD", "sdwan"),
    ("VCE", "sdwan"),
    ("EDGE", "sdwan"),

    # Distribution / layer-3 switching
    ("C9500", "dist"),
    ("C9400", "dist"),
    ("C9300", "switch"),
    ("C9600", "switch"),
    ("C3850", "switch"),
    ("C3650", "switch"),

    # Access switches / workgroup
    ("CAT", "AC"),

    # Firewalls
    ("ASA", "asa"),
    ("FIREPOWER", "firewall"),
    ("FW", "firewall"),

    # Wireless
    ("WLC", "wlc"),
    ("AIRONET", "ap"),

    # Generic
    ("IOS", "switch"),

    # Other
    ("Cloud", "cloud"),
]


def get_device_shape(device: dict) -> str:
    """Return the best Draw.io style string for a device.

    Preferences:
    1) Device type (from classification) if it maps to a shape.
    2) Platform keyword hints if available.
    3) Default fallback shape.
    """
    # 1) Prefer explicit type mapping
    dev_type = device.get("type")
    if dev_type in DEVICE_SHAPES:
        style = DEVICE_SHAPES[dev_type]
        if _shape_image_exists(style):
            return style

    # 2) Apply platform hints
    platform = (device.get("platform") or "").upper()
    for keyword, shape_key in PLATFORM_TYPE_HINTS:
        if keyword in platform and shape_key in DEVICE_SHAPES:
            style = DEVICE_SHAPES[shape_key]
            if _shape_image_exists(style):
                return style

    # 3) Fallback
    return DEVICE_SHAPES["default"]


def _shape_image_exists(style: str) -> bool:
    """Check whether the shape is valid. For built-in shapes, always true."""
    return True
    candidate = os.path.join(BASE_DIR, "icons", icon_filename)
    return os.path.exists(candidate)

# ── Hostname → tier classification rules ──────────────────────────────────────
TIER_KEYWORDS = {
    "firewall":   ["FIRE", "FW", "ASA", "PIX", "NGFW", "PALO"],
    "sdwan":      ["SDWAN", "VCE", "VELO", "EDGE"],
    "wan_switch": ["WAN"],
    "router":     ["CORE", "RTR", "ROUTER", "GW", "GATEWAY", "EDGE", "PE", "CE"],
    "dist":       ["DIST", "DSW", "DISTRIBUTION", "AGG", "AGGR"],
    "server":     ["SRV", "SERVER", "ESX", "ESXI", "VCENTER"],
    "ap":         ["AP-", "WAP", "WLAN","JAP"],
}

# ── Scheduling ────────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_MINUTES = 60    # change to 30, 15, etc.
SCHEDULE_TIMEZONE         = "UTC" # e.g. "Asia/Kolkata", "America/New_York"

# ── SSH credentials (real devices) ────────────────────────────────────────────
# IMPORTANT: For production, load from environment variables or a vault:
#   export NET_USERNAME=admin
#   export NET_PASSWORD=secret
CREDENTIALS = {
    "username": os.getenv("NET_USERNAME", "root"),
    "password": os.getenv("NET_PASSWORD", "#Dhcp6768"),
    "timeout":  10,
    "device_type": "cisco_ios",        # default; override per device if needed
}
# ── Jump server credentials ────────────────────────────────────────────
# Separate credentials for jump server (may differ from device credentials)
JUMP_CREDENTIALS = {
    "username": os.getenv("JUMP_USERNAME", "bhavesh"),  # Update with real jump server username
    "password": os.getenv("JUMP_PASSWORD", "#Dhcp6768"),  # Update with real jump server password
    "timeout":  10,
}
# List of jump server IPs to try in order. If one fails, fallback to the next.
# Default reflects the current primary plus additional backups.
JUMP_SERVERS = [
    "192.168.1.21",
    "192.168.1.11",
    "192.168.1.12",
    "192.168.1.13",
]
# Can be overridden by env var, comma-separated list:
# export JUMP_SERVERS="192.168.1.21,192.168.1.11,192.168.1.12,192.168.1.13"
JUMP_SERVERS = [h.strip() for h in os.getenv("JUMP_SERVERS", ",".join(JUMP_SERVERS)).split(",") if h.strip()]

# Seed devices for CDP crawl (add your core/edge devices here)
SEED_DEVICES = [
    {"host": "192.168.1.100", "device_type": "cisco_ios"},
    {"host": "192.168.1.101", "device_type": "cisco_ios"},
    {"host": "192.168.1.102", "device_type": "cisco_ios"},
]

# ── GitHub settings (optional — for auto-push) ────────────────────────────────
GITHUB_TOKEN      = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO       = os.getenv("GITHUB_REPO",  "your-org/network-diagrams")
GITHUB_BRANCH     = "main"
GITHUB_UPLOAD_DIR = "diagrams"         # folder inside the repo

# ── Export formats ────────────────────────────────────────────────────────────
EXPORT_FORMATS = ["drawio", "png", "svg"]   # add "pdf" if reportlab installed

# ── Helpers ───────────────────────────────────────────────────────────────────
def timestamp() -> str:
    """Return current timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def classify_device(hostname: str) -> str:
    """Return tier name for a device based on its hostname."""
    h = hostname.upper()
    for tier, keywords in TIER_KEYWORDS.items():
        if any(kw in h for kw in keywords):
            return tier
    return "access"    # default tier for unknown devices


def get_tier(device: dict) -> int:
    """
    Assign numeric tier (0-6) to a device based on type/classification.
    
    ISP (tier 0) → WAN Switch (tier 1) → SDWAN (tier 2) → 
    Firewall (tier 3) → Distribution (tier 4) → Access (tier 5) → AP (tier 6)
    """
    # If tier already in device, return it
    if "tier" in device:
        return device.get("tier", 5)
    
    device_type = device.get("type", "").lower()
    hostname = device.get("hostname", "").upper()
    platform = device.get("platform", "").upper()
    
    # Check explicit device type first
    if device_type == "isp" or "ISP" in hostname:
        return 0
    elif device_type == "wan_switch" or "WAN" in hostname:
        return 1
    elif device_type == "sdwan" or any(kw in hostname for kw in ["SDWAN", "VCE", "VELO", "EDGE"]):
        return 2
    elif device_type == "firewall" or any(kw in hostname for kw in ["FIRE", "FW", "ASA", "PIX", "NGFW", "PALO"]):
        return 3
    elif device_type == "dist" or any(kw in hostname for kw in ["DIST", "DSW", "DISTRIBUTION", "AGG"]):
        return 4
    elif device_type == "access" or any(kw in hostname for kw in ["ACC", "ACCESS"]):
        return 5
    elif device_type == "ap" or any(kw in hostname for kw in ["AP-", "WAP", "WLAN", "AP"]):
        return 6
    
    # Check for synthetic/external devices
    if device.get("is_synthetic"):
        if "ISP" in hostname:
            return 0
        elif "WAN" in hostname:
            return 1
        elif "SDWAN" in hostname:
            return 2
        elif "FIREWALL" in hostname or "FIRE" in hostname:
            return 3
    
    # Fallback: assume access switch if not categorized
    return 5


def output_path(prefix: str = "diagram", ext: str = "drawio", region: str = "", country: str = "", city: str = "") -> str:
    """Build a timestamped output filepath with hierarchical folder structure."""
    # Create base output directory
    base_dir = OUTPUT_DIR

    # Add hierarchical structure: Region > Country > City
    if region and country and city:
        base_dir = os.path.join(OUTPUT_DIR, region, country, city)
    elif region and country:
        base_dir = os.path.join(OUTPUT_DIR, region, country)
    elif region:
        base_dir = os.path.join(OUTPUT_DIR, region)

    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, f"{prefix}_{timestamp()}.{ext}")
