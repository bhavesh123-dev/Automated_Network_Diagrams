"""
layout_engine.py — Graphviz dot layout for N2G diagrams
=========================================================
Hybrid layout: 
- Y axis: STRICT tier-based positioning (ISP tier 0 at top → AP tier 6 at bottom)
- X axis: Graphviz dot handles horizontal spacing to avoid overlap

Install:
    pip install graphviz
    sudo apt install graphviz -y       # Ubuntu — installs dot binary

Usage:
    from layout_engine import build_positioned_diagram
    diagram = build_positioned_diagram(topology)
    diagram.dump_file(filename="out.drawio", folder="output_diagrams/")
"""

import sys
import json

try:
    import graphviz
except ImportError:
    raise ImportError("Graphviz not installed. Install with: pip install graphviz && sudo apt install graphviz -y")

try:
    from N2G.plugins.diagrams.N2G_DrawIO import drawio_diagram as DrawIoDiagram
except ImportError:
    print("Install n2g:  pip install n2g")
    sys.exit(1)

from config import (
    DEVICE_SHAPES, classify_device, get_device_shape, get_tier, NODE_WIDTH, NODE_HEIGHT,
    PAGE_WIDTH, PAGE_HEIGHT, GRID_MARGIN
)

# ── Scale factor: Graphviz uses inches, Draw.io uses pixels ──────────────────
# dot default DPI is 72. Multiply graphviz coords by this to get pixel coords.
DOT_DPI    = 72
PX_SCALE   = 1.8        # extra spread factor — increase for more breathing room
LINK_STYLE = "endArrow=none;"

# ── Tier-based Y positioning (strict hierarchical Y axis) ──────────────────────
TIER_VERTICAL_SPACING = {
    (0, 1): 250,  # ISP to WAN Switch
    (1, 2): 220,  # WAN Switch to SDWAN  
    (2, 3): 240,  # SDWAN to Firewall
    (3, 4): 250,  # Firewall to Distribution
    (4, 5): 200,  # Distribution to Access
    (5, 6): 180,  # Access to AP
}

DEFAULT_TIER_SPACING = 220
BASE_Y_POSITION = 70


def calculate_tier_y_positions(devices: list) -> dict:
    """
    Pre-calculate Y positions based strictly on device tier.
    Returns {hostname: y_position}.
    
    Y positions are FIXED by tier and never changed by layout engine.
    """
    y_positions = {}
    
    # Group devices by tier
    from collections import defaultdict
    tiers = defaultdict(list)
    for device in devices:
        tier = get_tier(device)
        tiers[tier].append(device)
    
    # Calculate Y position for each tier
    tier_y_positions = {}
    current_y = BASE_Y_POSITION
    existing_tiers = sorted(tiers.keys())
    
    for i, tier_level in enumerate(existing_tiers):
        tier_y_positions[tier_level] = current_y
        
        # Add spacing to next tier if it exists
        if i + 1 < len(existing_tiers):
            next_tier = existing_tiers[i + 1]
            spacing_key = (tier_level, next_tier)
            spacing = TIER_VERTICAL_SPACING.get(spacing_key, DEFAULT_TIER_SPACING)
            current_y += spacing
    
    # Assign Y position to each device based on its tier
    for device in devices:
        tier = get_tier(device)
        y_positions[device["hostname"]] = tier_y_positions[tier]
    
    return y_positions



def format_vlan_info(vlans: list) -> str:
    """Format VLAN information for display.

    Ignore VLANs whose name contains "default" (factory/default VLANs).
    """
    if not vlans:
        return "No VLANs"

    # Filter out default VLANs and show only active ones
    active_vlans = [
        v for v in vlans
        if v.get('status', '').lower() == 'active'
        and 'default' not in v.get('name', '').lower()
    ]
    if not active_vlans:
        return "No VLANs"

    vlan_list = [f"VLAN{v['id']}" for v in active_vlans[:5]]
    return f"VLANS: {', '.join(vlan_list)}"


def format_ip_info(ip_interfaces: list) -> str:
    """Format IP interface information for display."""
    if not ip_interfaces:
        return "No IPs"

    # Prefer VLAN interface IPs (layer 3) and show mapping by interface
    vlan_ifaces = [
        i for i in ip_interfaces
        if i.get('interface', '').lower().startswith('vlan')
    ]
    if vlan_ifaces:
        lines = [f"{iface['interface']}: {iface['ip']}" for iface in vlan_ifaces[:3]]
        return "IP:\n" + "\n".join(lines)

    # Fallback: show first 3 IPs
    ips = [f"{iface['ip']}" for iface in ip_interfaces[:3]]
    return f"IPs: {', '.join(ips)}"


def add_vlan_ip_labels(diagram: DrawIoDiagram, devices: list, positions: dict):
    """Add VLAN and IP information labels according to placement rules."""

    # Group devices by row (Y position)
    row_groups = {}
    for device in devices:
        hostname = device["hostname"]
        if hostname in positions:
            pos = positions[hostname]
            y_pos = pos["y"] if isinstance(pos, dict) else pos[1]
            if y_pos not in row_groups:
                row_groups[y_pos] = []
            row_groups[y_pos].append(device)

    for y_pos, row_devices in row_groups.items():
        # Sort by X position
        row_devices.sort(key=lambda d: positions[d["hostname"]]["x"] if isinstance(positions[d["hostname"]], dict) else positions[d["hostname"]][0])

        for idx, device in enumerate(row_devices):
            hostname = device["hostname"]
            pos = positions[hostname]
            x_pos = pos["x"] if isinstance(pos, dict) else pos[0]
            y_pos = pos["y"] if isinstance(pos, dict) else pos[1]

            pos = positions[hostname]
            if isinstance(pos, tuple):
                x_pos, y_pos = pos
            else:
                x_pos, y_pos = pos["x"], pos["y"]

            vlan_info = format_vlan_info(device.get("vlans", []))
            ip_info = format_ip_info(device.get("ip_interfaces", []))

            # Placement rules based on number of devices in row
            num_devices = len(row_devices)

            if num_devices == 1:
                # Single node: VLAN/IP info on left side
                vlan_x = x_pos - 200
                vlan_y = y_pos
                ip_x = x_pos - 200
                ip_y = y_pos + 30

            elif num_devices == 2:
                if idx == 0:  # Left node
                    vlan_x = x_pos - 150
                    vlan_y = y_pos
                    ip_x = x_pos - 150
                    ip_y = y_pos + 30
                else:  # Right node
                    vlan_x = x_pos + 150
                    vlan_y = y_pos
                    ip_x = x_pos + 150
                    ip_y = y_pos + 30

            else:  # 3 or more devices
                if idx == 0:  # Left node
                    vlan_x = x_pos - 150
                    vlan_y = y_pos
                    ip_x = x_pos - 150
                    ip_y = y_pos + 30
                elif idx == len(row_devices) - 1:  # Right node
                    vlan_x = x_pos + 150
                    vlan_y = y_pos
                    ip_x = x_pos + 150
                    ip_y = y_pos + 30
                else:  # Middle node(s)
                    vlan_x = x_pos
                    vlan_y = y_pos + 80  # Below the node
                    ip_x = x_pos
                    ip_y = y_pos + 110  # Below VLAN info

            # Add VLAN label
            diagram.add_node(
                id=f"{hostname}_vlan",
                label=vlan_info,
                style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=10;",
                width=120, height=20,
                x_pos=vlan_x, y_pos=vlan_y,
            )

            # Add IP label
            diagram.add_node(
                id=f"{hostname}_ip",
                label=ip_info,
                style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=10;",
                width=120, height=20,
                x_pos=ip_x, y_pos=ip_y,
            )


def add_legend(diagram: DrawIoDiagram, devices: list):
    """Add legend to top right of page 3 (top-right A4 grid cell)."""

    # Collect unique device types
    device_types = set()
    for device in devices:
        device_types.add(device.get("type", "unknown"))

    # Legend should live on page 3 (top-right) to avoid overlap with nodes.
    page3_origin_x = PAGE_WIDTH * 2
    page3_origin_y = 0
    legend_width = 150
    legend_height = 20 + (len(device_types) * 25)  # Dynamic height
    legend_x = page3_origin_x + PAGE_WIDTH - GRID_MARGIN - legend_width
    legend_y = page3_origin_y + GRID_MARGIN

    # Add legend background
    diagram.add_node(
        id="legend_bg",
        label="",
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f0f0f0;strokeColor=#cccccc;",
        width=legend_width, height=legend_height,
        x_pos=legend_x, y_pos=legend_y,
    )

    # Add legend title
    diagram.add_node(
        id="legend_title",
        label="Legend",
        style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=12;fontStyle=1;",
        width=legend_width, height=20,
        x_pos=legend_x, y_pos=legend_y + 5,
    )

    # Add device type entries
    y_offset = 30
    for device_type in sorted(device_types):
        # Use the same selection logic used for nodes (type/platform hints)
        shape = get_device_shape({"type": device_type, "platform": device_type})

        # Add small icon
        diagram.add_node(
            id=f"legend_icon_{device_type}",
            label="",
            style=shape,
            width=20, height=20,
            x_pos=legend_x + 10, y_pos=legend_y + y_offset,
        )

        # Add type label
        diagram.add_node(
            id=f"legend_label_{device_type}",
            label=device_type.capitalize(),
            style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=10;",
            width=100, height=20,
            x_pos=legend_x + 35, y_pos=legend_y + y_offset,
        )

        y_offset += 25


def _build_dot_graph(topology: dict, tier_y_positions: dict) -> graphviz.Digraph:
    """
    Build a Graphviz Digraph that ONLY computes X (horizontal) positions.
    Y positions are pre-computed and fixed by tier.
    
    This ensures:
    - Graphviz handles only horizontal spacing (prevents X overlap)
    - Tier-based Y axis is never overridden
    """
    dot = graphviz.Digraph(
        engine="neato",         # neato = spring model (good for X spacing without forcing hierarchy)
        graph_attr={
            "overlap":      "scale",   # Scale down overlaps proportionally
            "sep":          "0.5",     # Separation between nodes
            "start":        "rand",    # Random layout helps with X spacing
            "splines":      "ortho",   # Right-angle edges
        },
        node_attr={
            "shape":    "box",
            "width":    "1.0",
            "height":   "0.6",
            "fixedsize":"true",
        },
    )

    devices = topology["devices"]

    # Add all nodes with their FIXED Y position from tier calculation
    for device in devices:
        hostname = device["hostname"]
        y_pos_pixels = tier_y_positions.get(hostname, 100)
        # Convert pixel Y to inches for dot format (divide by DPI)
        y_pos_inches = y_pos_pixels / DOT_DPI
        
        # Add node with fixed Y position
        if device.get("type") == "ap":
            dot.node(hostname, label=hostname, pos=f"0,{y_pos_inches}!", width="1.8", height="1.2", fixedsize="true")
        else:
            dot.node(hostname, label=hostname, pos=f"0,{y_pos_inches}!", width="1.0", height="0.6", fixedsize="true")

    # Add edges for neato layout (helps with X spacing without Y influence)
    seen = set()
    for device in devices:
        src = device["hostname"]
        for neighbor in device.get("neighbors", []):
            dst = neighbor["hostname"]
            key = tuple(sorted([src, dst]))
            if key not in seen:
                seen.add(key)
                dot.edge(src, dst, len="2.0")  # Edge length helps with X spacing

    return dot



def _parse_dot_positions(dot: graphviz.Digraph, tier_y_positions: dict) -> dict:
    """
    Run graphviz layout and parse X positions from output.
    OVERRIDE Y positions with pre-calculated tier-based Y values.
    
    Returns {hostname: {"x": x_pixels, "y": y_pixels}}.
    """
    # Render to 'plain' format — simplest to parse
    plain = dot.pipe(format="plain").decode("utf-8")

    positions = {}
    for line in plain.splitlines():
        parts = line.split()
        if parts and parts[0] == "node":
            # plain format: node <name> <x> <y> <width> <height> ...
            name = parts[1]
            x_in = float(parts[2])
            # IGNORE graphviz Y position — use pre-calculated tier-based Y
            # Convert X inches → pixels and apply scale
            x_px = x_in * DOT_DPI * PX_SCALE
            y_px = tier_y_positions.get(name, 100)  # Use tier-based Y, not dot Y
            
            positions[name] = {
                "x": round(x_px),
                "y": round(y_px)
            }

    return positions


def _centre_layout(positions: dict) -> dict:
    """
    Translate X positions so the diagram starts at x=60.
    Y positions are already fixed by tier and should not be modified.
    
    Works with {hostname: {"x": x_px, "y": y_px}} format.
    """
    if not positions:
        return positions
    
    min_x = min(pos["x"] for pos in positions.values() if isinstance(pos, dict))
    
    # Center X axis at x=60, keep Y axis as-is (tier-based)
    return {
        name: {
            "x": pos["x"] - min_x + 60 if isinstance(pos, dict) else pos[0],
            "y": pos["y"] if isinstance(pos, dict) else pos[1]
        }
        for name, pos in positions.items()
    }


def add_wan_switch_containers(diagram: DrawIoDiagram, devices: list, positions: dict):
    """Add square container boxes around nodes connected to WAN switches."""
    device_map = {d["hostname"]: d for d in devices}

    for device in devices:
        if device.get("type") == "wan_switch" and "wan_connections" in device:
            wan_hostname = device["hostname"]
            wan_pos = positions.get(wan_hostname)

            if not wan_pos:
                continue

            # Get connected devices
            connected_devices = []
            for conn in device["wan_connections"]:
                connected_device = conn.get("connected_device")
                if connected_device and connected_device in device_map:
                    connected_devices.append(connected_device)

            if not connected_devices:
                continue

            # Calculate container bounds
            all_positions = [positions.get(dev) for dev in connected_devices if positions.get(dev)]
            if not all_positions:
                continue

            min_x = min(pos[0] if isinstance(pos, tuple) else pos["x"] for pos in all_positions)
            max_x = max(pos[0] if isinstance(pos, tuple) else pos["x"] for pos in all_positions)
            min_y = min(pos[1] if isinstance(pos, tuple) else pos["y"] for pos in all_positions)
            max_y = max(pos[1] if isinstance(pos, tuple) else pos["y"] for pos in all_positions)

            # Add padding
            padding = 40
            container_x = min_x - padding
            container_y = min_y - padding
            container_width = (max_x - min_x) + (NODE_WIDTH + 2 * padding)
            container_height = (max_y - min_y) + (NODE_HEIGHT + 2 * padding)

            # Add container box
            diagram.add_node(
                id=f"container_{wan_hostname}",
                label=f"WAN Switch: {wan_hostname} Connections",
                style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e6f3ff;strokeColor=#0066cc;dashed=1;",
                width=container_width, height=container_height,
                x_pos=container_x, y_pos=container_y,
            )


def build_positioned_diagram(topology: dict) -> DrawIoDiagram:
    """
    Main function: build a DrawIoDiagram with hybrid layout.
    
    Y AXIS: Strict tier-based positioning (pre-calculated, never changed)
    X AXIS: Graphviz handles horizontal spacing to avoid overlap
    """
    devices   = topology["devices"]
    device_map = {d["hostname"]: d for d in devices}

    # STEP 1: Pre-calculate Y positions strictly based on tier
    tier_y_positions = calculate_tier_y_positions(devices)
    print(f"  Tier-based Y positions calculated for {len(tier_y_positions)} devices")

    # STEP 2: Build Graphviz graph for X spacing (Y is fixed)
    dot = _build_dot_graph(topology, tier_y_positions)
    
    # STEP 3: Parse graphviz output - get X positions, use pre-calculated Y
    dot_positions = _parse_dot_positions(dot, tier_y_positions)
    positions = _centre_layout(dot_positions)
    print(f"  Graphviz layout computed X positions for {len(positions)} nodes")

    # STEP 4: Build N2G diagram using corrected positions
    diagram = DrawIoDiagram()
    diagram.add_diagram("Network Topology")

    for device in devices:
        hostname = device["hostname"]
        pos      = positions.get(hostname, {"x": 100, "y": 100})
        shape    = get_device_shape(device)
        tooltip  = f"IP: {device['ip']}\nPlatform: {device['platform']}\nType: {device['type'].upper()}"
        
        x_pos = pos["x"] if isinstance(pos, dict) else pos[0]
        y_pos = pos["y"] if isinstance(pos, dict) else pos[1]

        # Handle stacked switches - add two icons with offset
        if device.get("stack", False):
            # First switch
            diagram.add_node(
                id      = hostname,
                label   = f"{hostname}\n{device['ip']}",
                style   = shape,
                width   = NODE_WIDTH,
                height  = NODE_HEIGHT,
                x_pos   = x_pos,
                y_pos   = y_pos,
                tooltip = tooltip,
            )
            # Second switch with offset
            diagram.add_node(
                id      = f"{hostname}_stack2",
                label   = f"{hostname}\n{device['ip']}",
                style   = shape,
                width   = NODE_WIDTH,
                height  = NODE_HEIGHT,
                x_pos   = x_pos + 30,
                y_pos   = y_pos + 15,
                tooltip = tooltip,
            )
        else:
            # Single device
            diagram.add_node(
                id      = hostname,
                label   = f"{hostname}\n{device['ip']}",
                style   = shape,
                width   = NODE_WIDTH,
                height  = NODE_HEIGHT,
                x_pos   = x_pos,
                y_pos   = y_pos,
                tooltip = tooltip,
            )

    # Add VLAN and IP information labels
    add_vlan_ip_labels(diagram, devices, positions)

    # Add legend
    add_legend(diagram, devices)

    # Add links (deduplicated)
    seen_links = set()
    for device in devices:
        src = device["hostname"]
        for neighbor in device.get("neighbors", []):
            dst = neighbor["hostname"]
            key = tuple(sorted([src, dst]))
            if key in seen_links:
                continue
            seen_links.add(key)

            # Only add link if both ends are in the diagram
            if dst not in device_map:
                continue

            diagram.add_link(
                source = src,
                target = dst,
                label  = f"{neighbor.get('local_port', '')}\n{neighbor.get('remote_port', '')}",
                style  = LINK_STYLE,
            )

    print(f"  Added {len(seen_links)} links")
    return diagram


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from config import INPUT_JSON, OUTPUT_DIR, timestamp

    print("Layout Engine Test — Graphviz dot + N2G")
    print("-" * 40)

    try:
        with open(INPUT_JSON) as f:
            topology = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {INPUT_JSON} not found")
        sys.exit(1)

    diagram     = build_positioned_diagram(topology)
    output_file = f"layout_test_{timestamp()}.drawio"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    diagram.dump_file(filename=output_file, folder=OUTPUT_DIR)
    print(f"\nSaved → {OUTPUT_DIR}/{output_file}")
    print("Open in VS Code Draw.io extension to verify spacing.")