"""
generate_diagram.py — Network Diagram Generator (with layout engine)
======================================================================
JSON → Draw.io XML using N2G + hybrid layout engines (no node overlap).

Usage:
    python3 generate_diagram.py                           # Graphviz (recommended)
    python3 generate_diagram.py --grid                    # Grid fallback (smart_spread mode)
    python3 generate_diagram.py --grid --mode=centered    # Grid with centered layout
    python3 generate_diagram.py --grid --mode=columns     # Grid with column layout
    python3 generate_diagram.py --grid --mode=harmonic    # Grid with wave pattern

Available grid layout modes:
    - smart_spread (default): Intelligent spreading based on neighbor count
    - centered: All devices in tier centered at same X
    - columns: Devices spread across multiple columns
    - harmonic: Wave pattern oscillating around center
"""

import glob
import json
import os
import sys
from datetime import datetime
import math

try:
    from N2G.plugins.diagrams.N2G_DrawIO import drawio_diagram as DrawIoDiagram
except ImportError:
    print("ERROR: n2g not installed. Run:  pip install n2g")
    sys.exit(1)

from config import (
    BASE_DIR, INPUT_JSON, OUTPUT_DIR,
    NODE_WIDTH, NODE_HEIGHT, LINK_STYLE,
    PAGE_WIDTH, PAGE_HEIGHT, GRID_MARGIN,
    classify_device, get_device_shape, timestamp,
)

# ── Parse command-line arguments ──────────────────────────────────────────────
GRID_LAYOUT_MODE = "smart_spread"  # Default
if "--mode=" in " ".join(sys.argv):
    for arg in sys.argv:
        if arg.startswith("--mode="):
            GRID_LAYOUT_MODE = arg.split("=")[1]
            print(f"Grid mode: {GRID_LAYOUT_MODE}")

# ── Pick layout engine ────────────────────────────────────────────────────────
USE_GRAPHVIZ = False
if "--grid" not in sys.argv:
    try:
        from layout_engine import build_positioned_diagram
        USE_GRAPHVIZ = True
        print("Layout engine: Graphviz dot (hierarchical, no overlap)")
    except Exception:
        print("Graphviz unavailable — using grid layout fallback.")
        print("To install:  pip install graphviz && sudo apt install graphviz -y")

if not USE_GRAPHVIZ:
    print(f"Layout engine: strict grid math ({GRID_LAYOUT_MODE} mode)")
    from grid_layout import calculate_positions, validate_no_overlap


def load_topology(filepath: str) -> dict:
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found.")
        sys.exit(1)
    with open(filepath) as f:
        data = json.load(f)
    
    # Assign tier to each device for hierarchical placement
    from config import get_tier
    for device in data.get("devices", []):
        device["tier"] = get_tier(device)
    
    print(f"Loaded {len(data['devices'])} devices from {filepath}")
    return data


def format_vlan_info(vlans: list) -> str:
    """Format VLAN information for display.

    Ignore VLANs whose name contains "default" (common factory/default VLANs).
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
            y_pos = positions[hostname]["y"]
            if y_pos not in row_groups:
                row_groups[y_pos] = []
            row_groups[y_pos].append(device)

    for y_pos, row_devices in row_groups.items():
        row_devices.sort(key=lambda d: positions[d["hostname"]]["x"])  # Sort by X position

        for idx, device in enumerate(row_devices):
            hostname = device["hostname"]
            pos = positions[hostname]

            vlan_info = format_vlan_info(device.get("vlans", []))
            ip_info = format_ip_info(device.get("ip_interfaces", []))

            # Placement rules based on number of devices in row
            num_devices = len(row_devices)

            if num_devices == 1:
                # Single node: VLAN/IP info on left side
                vlan_x = pos["x"] - 200
                vlan_y = pos["y"]
                ip_x = pos["x"] - 200
                ip_y = pos["y"] + 30

            elif num_devices == 2:
                if idx == 0:  # Left node
                    vlan_x = pos["x"] - 150
                    vlan_y = pos["y"]
                    ip_x = pos["x"] - 150
                    ip_y = pos["y"] + 30
                else:  # Right node
                    vlan_x = pos["x"] + 150
                    vlan_y = pos["y"]
                    ip_x = pos["x"] + 150
                    ip_y = pos["y"] + 30

            else:  # 3 or more devices
                if idx == 0:  # Left node
                    vlan_x = pos["x"] - 150
                    vlan_y = pos["y"]
                    ip_x = pos["x"] - 150
                    ip_y = pos["y"] + 30
                elif idx == len(row_devices) - 1:  # Right node
                    vlan_x = pos["x"] + 150
                    vlan_y = pos["y"]
                    ip_x = pos["x"] + 150
                    ip_y = pos["y"] + 30
                else:  # Middle node(s)
                    vlan_x = pos["x"]
                    vlan_y = pos["y"] + 80  # Below the node
                    ip_x = pos["x"]
                    ip_y = pos["y"] + 110  # Below VLAN info

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
    """Add legend to top right of page 3 (top-right A4 cell)."""

    # Collect unique device types
    device_types = set()
    for device in devices:
        device_types.add(device.get("type", "unknown"))

    # Place legend in page 3 (top-right) to avoid overlapping main nodes
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
        # Attempt to use the same selection logic as the nodes themselves
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


def add_external_wan_devices(diagram: DrawIoDiagram, devices: list) -> set:
    """Add external devices connected to WAN switches as square boxes with specific positioning."""
    external_devices = set()
    wan_devices = [d for d in devices if d.get("type") == "wan_switch"]

    for wan_device in wan_devices:
        if "wan_connections" in wan_device:
            for conn in wan_device["wan_connections"]:
                connected_device = conn.get("connected_device")
                if connected_device:
                    external_devices.add(connected_device)

    # Position external devices according to network hierarchy rules
    for ext_device in external_devices:
        if ext_device.lower() in ["isp", "internet", "provider"]:
            # ISP: Page 1 (top left) at top
            x = PAGE_WIDTH * 0 + (PAGE_WIDTH / 2)
            y = GRID_MARGIN + (NODE_HEIGHT / 2)
        elif ext_device.lower() in ["firewall", "fw", "palo", "asa"]:
            # Firewall: Page 2 (top middle) below SDWAN
            x = PAGE_WIDTH * 1 + (PAGE_WIDTH / 2)
            y = GRID_MARGIN + (NODE_HEIGHT / 2) + 200  # Below SDWAN
        else:
            # Other external devices: around WAN switch (Page 2 center)
            wan_switch_pos = {"x": PAGE_WIDTH * 1.5, "y": PAGE_HEIGHT * 0.5}
            # Position in a circle around WAN switch
            num_ext = len([d for d in external_devices if d.lower() not in ["isp", "internet", "provider", "firewall", "fw", "palo", "asa"]])
            if num_ext > 0:
                idx = list(external_devices).index(ext_device)
                angle = (idx * 2 * math.pi) / num_ext
                radius = 200
                x = wan_switch_pos["x"] + radius * math.cos(angle)
                y = wan_switch_pos["y"] + radius * math.sin(angle)
            else:
                x = wan_switch_pos["x"]
                y = wan_switch_pos["y"]

        # Use square box (default shape) for all external devices
        diagram.add_node(
            id=ext_device,
            label=ext_device,
            style=get_device_shape({"type": "default"}),
            width=NODE_WIDTH, height=NODE_HEIGHT,
            x_pos=x, y_pos=y,
            tooltip=f"External Device: {ext_device}",
        )

    return external_devices


def add_wan_external_links(diagram: DrawIoDiagram, devices: list):
    """Add links from WAN switches to external devices."""
    link_count = 0
    wan_devices = [d for d in devices if d.get("type") == "wan_switch"]

    for wan_device in wan_devices:
        wan_hostname = wan_device["hostname"]
        if "wan_connections" in wan_device:
            for conn in wan_device["wan_connections"]:
                connected_device = conn.get("connected_device")
                interface = conn.get("interface", "")
                description = conn.get("description", "")

                if connected_device:
                    diagram.add_link(
                        source=wan_hostname,
                        target=connected_device,
                        label=f"{interface}",
                        style=LINK_STYLE,
                        tooltip=f"{description}\nInterface: {interface}",
                    )
                    link_count += 1


def apply_special_placements(devices: list, positions: dict) -> dict:
    """Apply special placement rules for WAN switches and distribution switches."""
    for device in devices:
        hostname = device["hostname"]
        device_type = device.get("type", "")

        if device_type == "wan_switch":
            # WAN Switch: Page 2 center middle
            positions[hostname] = {
                "x": PAGE_WIDTH * 1.5,  # Page 2 center X
                "y": PAGE_HEIGHT * 0.5  # Middle Y
            }
        elif device_type == "dist":
            # Distribution Switch: Center bottom of page 2
            positions[hostname] = {
                "x": PAGE_WIDTH * 1.5,  # Page 2 center X
                "y": PAGE_HEIGHT - GRID_MARGIN  # Bottom with margin
            }

    return positions


def add_wan_switch_containers(diagram: DrawIoDiagram, devices: list, positions: dict):
    """Add square container boxes around nodes connected to WAN switches."""
    device_map = {d["hostname"]: d for d in devices}

    for device in devices:
        if device.get("type") == "wan_switch" and "wan_connections" in device:
            wan_hostname = device["hostname"]
            wan_pos = positions.get(wan_hostname)

            if not wan_pos:
                continue

            # Get connected devices (both internal and external)
            connected_devices = []
            for conn in device["wan_connections"]:
                connected_device = conn.get("connected_device")
                if connected_device:
                    connected_devices.append(connected_device)

            if not connected_devices:
                continue

            # Calculate container bounds
            all_positions = []
            for dev in connected_devices:
                pos = positions.get(dev)
                if pos:
                    all_positions.append(pos)

            if not all_positions:
                continue

            min_x = min(pos["x"] for pos in all_positions)
            max_x = max(pos["x"] for pos in all_positions)
            min_y = min(pos["y"] for pos in all_positions)
            max_y = max(pos["y"] for pos in all_positions)

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


def build_diagram_grid(topology: dict) -> DrawIoDiagram:
    """Build diagram with strict grid math — no overlap.
    
    Uses the selected layout mode from GRID_LAYOUT_MODE global variable.
    """
    devices    = topology["devices"]
    device_map = {d["hostname"]: d for d in devices}
    positions  = calculate_positions(devices, layout_mode=GRID_LAYOUT_MODE)

    # Apply special placement rules
    positions = apply_special_placements(devices, positions)

    overlaps = validate_no_overlap(positions)
    if overlaps:
        print(f"  WARNING: {len(overlaps)} overlap(s) — consider different layout mode")
    else:
        print(f"  Grid layout: {len(positions)} nodes, zero overlaps")


    diagram = DrawIoDiagram()
    diagram.add_diagram("Network Topology")

    # Add external devices connected to WAN switches
    external_devices = add_external_wan_devices(diagram, devices)

    # Add links from WAN switches to external devices
    add_wan_external_links(diagram, devices)

    for device in devices:
        hostname = device["hostname"]
        pos   = positions.get(hostname, {"x": 60, "y": 60})
        shape = get_device_shape(device)
        diagram.add_node(
            id=hostname,
            label=f"{hostname}\n{device['ip']}",
            style=shape,
            width=NODE_WIDTH, height=NODE_HEIGHT,
            x_pos=pos["x"], y_pos=pos["y"],
            tooltip=f"IP: {device['ip']}\nPlatform: {device['platform']}\nType: {device.get('type', 'unknown')}",
        )

    # Add WAN switch container boxes
    add_wan_switch_containers(diagram, devices, positions)

    # Add VLAN and IP information labels
    add_vlan_ip_labels(diagram, devices, positions)

    # Add legend
    add_legend(diagram, devices)

    seen = set()
    for device in devices:
        for n in device.get("neighbors", []):
            key = tuple(sorted([device["hostname"], n["hostname"]]))
            if key in seen or n["hostname"] not in device_map:
                continue
            seen.add(key)
            diagram.add_link(
                source=device["hostname"], target=n["hostname"],
                label=f"{n['local_port']}\n{n['remote_port']}",
                style=LINK_STYLE,
            )

    # Add links from WAN switches to external devices
    for device in devices:
        if device.get("type") == "wan_switch" and "wan_connections" in device:
            for conn in device["wan_connections"]:
                connected_device = conn.get("connected_device")
                if connected_device and connected_device in external_devices:
                    diagram.add_link(
                        source=device["hostname"], target=connected_device,
                        label=conn.get("interface", ""),
                        style=LINK_STYLE,
                    )

    print(f"  Added {len(seen)} internal links")
    return diagram


def save_diagram(diagram: DrawIoDiagram, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    diagram.dump_file(filename=os.path.basename(output_path),
                      folder=os.path.dirname(output_path))
    print(f"Saved → {output_path}")


def print_summary(topology: dict, output_path: str):
    counts = {}
    for d in topology["devices"]:
        counts[d["type"]] = counts.get(d["type"], 0) + 1
    print("\n" + "="*50)
    print("  NETWORK TOPOLOGY SUMMARY")
    print("="*50)
    for t, c in sorted(counts.items()):
        print(f"  {t.capitalize():14} : {c}")
    print(f"  {'Total':14} : {len(topology['devices'])}")
    print("="*50)
    print(f"  Output → {output_path}")
    print("="*50 + "\n")

if __name__ == "__main__":
    print("\n Network Diagram Generator")
    print("-" * 40)

    from config import output_path

    topology_files = sorted(glob.glob(os.path.join(BASE_DIR, "topology_data", "**", "*_topology_data_latest.json"), recursive=True))
    if not topology_files:
        print("ERROR: No topology files found in topology_data/**/**/**_topology_data_latest.json")
        sys.exit(1)

    total_files = len(topology_files)
    for index, topology_file in enumerate(topology_files, start=1):
        print(f"\nProcessing topology file {index}/{total_files}: {topology_file}")
        try:
            topology = load_topology(topology_file)
        except Exception as e:
            print(f"ERROR: Failed to load {topology_file}: {e}")
            continue

        # Region/Country/City are usually in the directory hierarchy under topology_data
        rel_path = os.path.relpath(topology_file, BASE_DIR)
        parts = rel_path.replace("\\", "/").split("/")
        region = parts[1] if len(parts) > 1 else ""
        country = parts[2] if len(parts) > 2 else ""
        city = parts[3] if len(parts) > 3 else ""

        if not city:
            city = os.path.basename(topology_file).replace("_topology_data_latest.json", "")

        output_file = output_path(
            prefix=f"Network Diagram of {city}" if city else "network_diagram",
            ext="drawio",
            region=region,
            country=country,
            city=city,
        )

        if USE_GRAPHVIZ:
            diagram = build_positioned_diagram(topology)
        else:
            diagram = build_diagram_grid(topology)

        save_diagram(diagram, output_file)
        print_summary(topology, output_file)
