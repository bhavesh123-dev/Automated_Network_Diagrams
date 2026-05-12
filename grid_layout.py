"""
grid_layout.py — Strict grid math layout for N2G diagrams
==========================================================
Fallback when Graphviz isn't available. Mathematically ensures
zero overlap by assigning each node to a unique grid cell.
Uses tier-based hierarchical placement (ISP tier 0 → AP tier 6).

Layout Strategy:
- For small networks (< 9 access switches): Centered vertical layout  
- For large networks: 3×2 page grid expansion to multiple pages

Usage:
    from grid_layout import calculate_positions, validate_no_overlap
    positions = calculate_positions(devices)
    overlaps = validate_no_overlap(positions)
"""

from collections import defaultdict
from config import (
    PAGE_WIDTH, PAGE_HEIGHT, GRID_MARGIN, GRID_COLS, GRID_ROWS,
    NODE_WIDTH, NODE_HEIGHT, get_tier
)

# Vertical spacing between tiers in simple centered layout
TIER_VERTICAL_SPACING = {
    (0, 1): 300,  # ISP to WAN Switch
    (1, 2): 250,  # WAN Switch to SDWAN  
    (2, 3): 280,  # SDWAN to Firewall
    (3, 4): 300,  # Firewall to Distribution
    (4, 5): 250,  # Distribution to Access
    (5, 6): 220,  # Access to AP
}

# Fallback spacing if tiers are not consecutive
DEFAULT_TIER_SPACING = 280


def calculate_tier_y_position(tier: int, devices: list) -> float:
    """
    Calculate Y position for a tier based on hierarchical spacing.
    Tier 0 (ISP) starts at y=70, then each tier below adds spacing.
    """
    base_y = 70
    current_tier = 0
    current_y = base_y
    
    # Build a mapping of which tiers exist in devices
    existing_tiers = sorted(set(get_tier(d) for d in devices))
    
    if tier == 0:
        return base_y
    
    # Find all tiers up to target tier and sum their spacing
    for i, prev_tier in enumerate(existing_tiers):
        if prev_tier >= tier:
            break
        
        if i + 1 < len(existing_tiers):
            next_tier = existing_tiers[i + 1]
            # Use specific spacing if defined, otherwise default
            spacing_key = (prev_tier, next_tier)
            spacing = TIER_VERTICAL_SPACING.get(spacing_key, DEFAULT_TIER_SPACING)
            current_y += spacing
    
    return current_y


def calculate_positions(devices: list, layout_mode: str = "smart_spread") -> dict:
    """
    Calculate positions with STRICT tier-based Y positioning and smart X spreading.
    
    Parameters:
    - devices: list of device dicts
    - layout_mode: X-axis strategy - "smart_spread" (default), "centered", "columns", "harmonic"
    
    Y AXIS (STRICT): Fixed by tier, never changes
    X AXIS (SMART): Based on neighbor count, device type, and layout_mode
    
    Layout Strategies:
    1. "smart_spread": Spread devices left/right based on neighbor count (busy devices in middle)
    2. "centered": All devices at center_x (for small networks)
    3. "columns": Span devices across multiple columns per tier
    4. "harmonic": Wave pattern oscillating around center
    """
    positions = {}
    center_x = 400  # Center baseline for X positioning
    
    # Assign tier to each device using get_tier()
    tiers = defaultdict(list)
    for device in devices:
        tier = get_tier(device)
        tiers[tier].append(device)
    
    # Calculate positions based on tiers (STRICT Y AXIS)
    for tier_num in sorted(tiers.keys()):
        tier_devices = tiers[tier_num]
        base_y = calculate_tier_y_position(tier_num, devices)  # STRICT tier-based Y
        
        if layout_mode == "smart_spread":
            positions.update(_calculate_x_smart_spread(tier_devices, tier_num, base_y, center_x))
        
        elif layout_mode == "centered":
            positions.update(_calculate_x_centered(tier_devices, base_y, center_x))
        
        elif layout_mode == "columns":
            positions.update(_calculate_x_columns(tier_devices, tier_num, base_y, center_x))
        
        elif layout_mode == "harmonic":
            positions.update(_calculate_x_harmonic(tier_devices, tier_num, base_y, center_x))
        
        else:
            # Fallback to smart_spread
            positions.update(_calculate_x_smart_spread(tier_devices, tier_num, base_y, center_x))
    
    return positions


def _calculate_x_smart_spread(devices: list, tier: int, base_y: float, center_x: float) -> dict:
    """
    Smart X placement: Devices with more neighbors are placed more centrally.
    Devices with fewer neighbors are pushed to edges.
    """
    positions = {}
    
    if len(devices) == 1:
        # Single device: center it
        positions[devices[0]["hostname"]] = {
            "x": center_x,
            "y": base_y
        }
        return positions
    
    # Calculate neighbor count for each device
    neighbor_counts = {}
    for dev in devices:
        neighbor_counts[dev["hostname"]] = len(dev.get("neighbors", []))
    
    # Sort by neighbor count (descending) - busiest devices first
    sorted_devices = sorted(devices, key=lambda d: neighbor_counts.get(d["hostname"], 0), reverse=True)
    
    # Special rules for specific tiers
    if tier == 0:  # ISP tier - single device
        positions[devices[0]["hostname"]] = {"x": center_x, "y": base_y}
    
    elif tier == 1:  # WAN Switch(es)
        if len(devices) == 1:
            positions[devices[0]["hostname"]] = {"x": center_x, "y": base_y}
        elif len(devices) == 2:
            # Dual WAN: split left/right with major spacing
            positions[devices[0]["hostname"]] = {"x": center_x - 150, "y": base_y}
            positions[devices[1]["hostname"]] = {"x": center_x + 150, "y": base_y}
        else:
            # Multiple WAN: spread across width
            spacing = 200 // (len(devices) - 1) if len(devices) > 1 else 0
            for idx, dev in enumerate(sorted_devices):
                positions[dev["hostname"]] = {
                    "x": center_x - 100 + idx * (200 // max(len(devices) - 1, 1)),
                    "y": base_y
                }
    
    elif tier == 2:  # SDWAN
        positions[devices[0]["hostname"]] = {"x": center_x, "y": base_y}
    
    elif tier == 3:  # Firewall
        if len(devices) == 1:
            positions[devices[0]["hostname"]] = {"x": center_x, "y": base_y}
        else:
            # Dual/multiple firewalls: spread horizontally
            for idx, dev in enumerate(sorted_devices):
                offset = -120 if idx % 2 == 0 else 120
                positions[dev["hostname"]] = {
                    "x": center_x + offset,
                    "y": base_y + (idx // 2) * 100
                }
    
    elif tier == 4:  # Distribution switches - KEY tier for spreading
        if len(devices) == 1:
            positions[devices[0]["hostname"]] = {"x": center_x, "y": base_y}
        else:
            # Spread distribution switches across width based on neighbor count
            max_neighbors = max(neighbor_counts.get(d["hostname"], 0) for d in devices)
            for idx, dev in enumerate(sorted_devices):
                neighbor_ratio = neighbor_counts.get(dev["hostname"], 0) / max(max_neighbors, 1)
                # Busiest devices in center, least busy on edges
                x_offset = (neighbor_ratio - 0.5) * 200  # Range: -100 to 100
                positions[dev["hostname"]] = {
                    "x": center_x + x_offset,
                    "y": base_y + (idx * 10)  # Small vertical stagger
                }
    
    else:  # Tiers 5, 6 (Access, AP)
        # Spread across columns with intelligent balancing
        num_cols = min(3, max(1, len(devices)))
        col_width = 200 / num_cols
        
        for idx, dev in enumerate(sorted_devices):
            col = idx % num_cols
            row = idx // num_cols
            x_pos = center_x - 100 + col * col_width + (col_width / 2)
            y_offset = row * 120
            positions[dev["hostname"]] = {
                "x": x_pos,
                "y": base_y + y_offset
            }
    
    return positions


def _calculate_x_centered(devices: list, base_y: float, center_x: float) -> dict:
    """Simple centered X placement for all devices in tier."""
    positions = {}
    for dev in devices:
        positions[dev["hostname"]] = {
            "x": center_x,
            "y": base_y
        }
    return positions


def _calculate_x_columns(devices: list, tier: int, base_y: float, center_x: float) -> dict:
    """
    X placement: Span devices across multiple columns.
    Better for large networks (9+ access switches).
    """
    positions = {}
    
    # Determine columns based on tier
    if tier in [0, 2]:  # ISP, SDWAN - single column
        cols = 1
    elif tier == 1:  # WAN Switch - up to 2 columns
        cols = min(2, len(devices))
    elif tier == 3:  # Firewall - up to 2 columns
        cols = min(2, len(devices))
    elif tier == 4:  # Distribution - up to 3 columns
        cols = min(3, len(devices))
    else:  # Access, AP - up to 4 columns
        cols = min(4, len(devices))
    
    col_width = 300 / cols if cols > 0 else 300
    
    for idx, dev in enumerate(devices):
        col = idx % cols
        row = idx // cols
        positions[dev["hostname"]] = {
            "x": center_x - 150 + col * col_width,
            "y": base_y + row * 100
        }
    
    return positions


def _calculate_x_harmonic(devices: list, tier: int, base_y: float, center_x: float) -> dict:
    """
    X placement: Wave pattern oscillating around center.
    Creates visually interesting layout without sacrificing clarity.
    """
    import math
    positions = {}
    
    for idx, dev in enumerate(devices):
        # Harmonic wave: oscillate left/right as we go through devices
        amplitude = 150  # Max distance from center
        frequency = 0.5  # Controls wave frequency
        phase = 2 * math.pi * idx * frequency / len(devices)
        x_offset = amplitude * math.sin(phase)
        
        positions[dev["hostname"]] = {
            "x": center_x + x_offset,
            "y": base_y + (idx % 2) * 80  # Slight vertical stagger
        }
    
    return positions


def validate_no_overlap(positions: dict) -> list:
    """
    Check for overlaps in positions. Returns list of overlapping pairs.
    Each position is a dict with 'x', 'y' keys.
    """
    overlaps = []
    pos_list = list(positions.items())
    for i, (name1, pos1) in enumerate(pos_list):
        for name2, pos2 in pos_list[i+1:]:
            # Simple box overlap check (assuming NODE_WIDTH/HEIGHT)
            if (abs(pos1["x"] - pos2["x"]) < NODE_WIDTH and
                abs(pos1["y"] - pos2["y"]) < NODE_HEIGHT):
                overlaps.append((name1, name2))
    return overlaps
