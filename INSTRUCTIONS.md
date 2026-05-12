# Network Automation — AI Code Generation Instructions
> This file guides GitHub Copilot Chat and other AI tools to generate
> correct, consistent code for this project. Attach this file whenever
> asking Copilot to write or fix code.

---

## Project Overview

This project automatically generates professional **Cisco network topology diagrams**
from live device data or JSON files. The output is Draw.io XML (`.drawio`),
PNG, SVG, and PDF — stored in GitHub and scheduled via APScheduler.

### Architecture (Updated for SDWAN Network)

```
Network Devices (Cisco IOS/NX-OS/Juniper)
        │  SSH via Jump Server
        ▼
Jump Server (192.168.1.10)
        │  SSH Tunnel
        ▼
  live_puller.py  ──► topology_data.json
        │
        ▼
  generate_diagram.py  (N2G + Graphviz/Grid layout engines)
        │  ┌──────────────────────────────┐
        ├──► Draw.io XML (.drawio)        │
        ├──► PNG / SVG / PDF             │  output_diagrams/
        └──► Visio VSDX (via converter)  │
             └──────────────────────────┘
                      │
                      ▼
              GitHub Repository
                      │
              scheduler.py (APScheduler / cron)
```

**Network Hierarchy (Top to Bottom):**
1. ISP Links
2. L2 Switch (WAN switch for ISP connections)
3. Velocloud SDWAN (at all sites)
4. WAN Switch (for SDWAN/campus connections)
5. Firewall (at select locations)
6. Distribution Switch (at some locations)
7. Access Switch (for user connections)

**Layout Engines**: Graphviz dot (hierarchical, zero overlap) or Grid math (fallback, one node per cell)

---

## Login Method for Network Devices

All network device connections must use a jump server for security and access control.

### Jump Server Configuration
- **Jump Server IP**: 192.168.1.10
- **Authentication**: Username/password from `CREDENTIALS` in `config.py`
- **Purpose**: Acts as a proxy for SSH connections to internal network devices

### Connection Flow
1. **Connect to Jump Server**:
   - Use paramiko SSHClient to establish connection
   - Set `set_missing_host_key_policy(paramiko.AutoAddPolicy())` to auto-accept host keys
   - Add `time.sleep(2)` after connection (jump server may be slow to respond)

2. **Establish SSH Tunnel**:
   - Open a direct-tcpip channel from jump server to target device
   - Add `time.sleep(1)` before attempting device login

3. **Connect to Device via Tunnel**:
   - Use Netmiko ConnectHandler with `sock=jump_channel` parameter
   - Supports legacy ciphers and KEX algorithms (diffie-hellman-group1-sha1, etc.)
   - Disabled modern algorithms that may not be supported by older devices

4. **Execute Commands**:
   - Run required `show` commands to gather topology data
   - Handle timeouts and authentication failures gracefully

### Error Handling
- Catch `NetmikoTimeoutException`, `NetmikoAuthenticationException`, `paramiko.SSHException`
- Log failures and continue processing other devices
- Always close jump server connection in `finally` block

### Code Implementation
Use this pattern in `live_puller.py`:

```python
import paramiko
import time

jump_client = paramiko.SSHClient()
jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
jump_client.connect('192.168.1.10', username=..., password=...)
time.sleep(2)  # Jump server response delay

jump_transport = jump_client.get_transport()
dest_addr = (device_ip, 22)
local_addr = ('localhost', 0)
jump_channel = jump_transport.open_channel("direct-tcpip", dest_addr, local_addr)
time.sleep(1)  # Before device login

device = {
    "device_type": device_type,
    "host": device_ip,
    "sock": jump_channel,  # Use tunnel
    # ... other params
}

with ConnectHandler(**device) as conn:
    # Execute show commands
```

---

| Layer | Library | Version |
|---|---|---|
| Diagram engine | `n2g` | ≥ 0.3.2 |
| Layout engine | `graphviz` | ≥ 0.21 |
| SSH / device pull | `netmiko` | ≥ 4.3.0 |
| Scheduling | `apscheduler` | ≥ 3.10.0 |
| GitHub upload | `PyGithub` | ≥ 2.1.0 |
| Image export | `pillow` | ≥ 10.0.0 |
| PDF export | `reportlab` | ≥ 4.0.0 |
| DOT → Draw.io | `graphviz2drawio` | latest |
| Python version | `python3` | ≥ 3.10 |

---

## JSON Topology Schema

All scripts read from / write to this exact schema.
**Never change field names without updating all scripts.**

```json
{
  "devices": [
    {
      "hostname": "CORE-RTR-01",
      "ip": "10.0.0.1",
      "type": "router",
      "platform": "Cisco IOS-XE",
      "neighbors": [
        {
          "hostname": "DIST-SW-01",
          "local_port": "GigabitEthernet0/0",
          "remote_port": "GigabitEthernet1/0/1"
        }
      ]
    }
  ]
}
```

### Valid `type` values
`router` | `switch` | `wan_switch` | `sdwan` | `firewall` | `server` | `ap` | `wlc` | `loadbalancer`

### Notes on layout & tiers
- **Layout Engines**: Choose Graphviz (recommended) or Grid layout to prevent node overlaps
- **Graphviz**: Uses `dot` algorithm for hierarchical positioning - best for complex networks
- **Grid**: Mathematical positioning with one node per cell - deterministic and reliable
- Diagram layout is driven by the device's `type` (and hostname patterns when `type` is missing).
- The script maps `type` → tier (Y position) based on network hierarchy:
  - `isp` → top (ISP links)
  - `wan_switch` → WAN layer (L2 switches for ISP)
  - `sdwan` → SDWAN layer (Velocloud devices)
  - `firewall` → security layer
  - `router` → core routing
  - `dist` → distribution
  - `access` → access layer
  - `server` → bottom
  - `dist` / `switch` → distribution
  - `access` → access
  - `server` → bottom
- For best layout, ensure your topology JSON uses meaningful `type` values (e.g., `dist`, `access`) and/or hostnames that follow the naming convention above.
- When multiple devices are in the same tier, the layout engines automatically spread them without overlaps.
- **Complex diagrams**: Always use layout engines - N2G alone cannot prevent overlaps!
### Hostname naming convention
| Prefix | Device tier |
|---|---|
| `ISP-*` | ISP connections |
| `WAN-*` | WAN switches (contains "wan" in hostname) |
| `SDWAN-*` or `VCE-*` or `EDGE-*` | Velocloud SDWAN devices |
| `FIRE-*` or `FW-*` or `ASA-*` | Security / firewall |
| `CORE-*` or `RTR-*` | Core routers |
| `DIST-*` or `DSW-*` | Distribution layer |
| `ACCESS-*` or `ASW-*` | Access layer |
| `AP-*` | Wireless access points |
| `SRV-*` | Server |

### Special Placement Rules

1. **SDWAN Placement**: SDWAN devices are placed in the middle of page 2 (top-middle grid cell). SDWAN devices are identified by:
   - Hostname containing: `SDWAN`, `VCE`, `VELO`, `EDGE`
   - Platform containing: `VELOCLOUD`, `VCE`, `EDGE`

2. **WAN Switch Detection**: WAN switches are identified by hostname containing "wan" string. They are placed below SDWAN devices in page 2.

3. **Connected Node Grouping**: When WAN switches are detected, the system logs into the switch and runs `show interface description | include up` to identify all connected nodes (ISP, Firewall, SDWAN). These connected nodes are grouped in a square container box.

4. **Access Point Detection**: Access points (Cisco and Juniper) are detected using:
   - `show cdp neighbors` (Cisco)
   - `show lldp neighbors` (Juniper/Cisco)
   - Hostname patterns: `AP-`, `WAP`, `WLAN`

5. **Legend**: All used device icons are displayed in a legend box in page 3 (top-right) for easy copy-paste if icons don't display.
| `AP-*` | Wireless access point |

---

## Layout Engines

The project supports two layout engines to prevent node overlap in complex diagrams:

### 1. Graphviz Dot Layout (Recommended)
- **Engine**: Graphviz `dot` algorithm (hierarchical top-down)
- **Usage**: `python3 generate_diagram.py` (default)
- **Features**: 
  - Zero overlap guarantee
  - Automatic tier-based ranking
  - Professional hierarchical layout
- **Requirements**: 
  - `pip install graphviz`
  - `sudo apt install graphviz` (system package)
- **Best for**: Complex networks with many devices

### 2. Grid Layout (Fallback)
- **Engine**: Mathematical grid positioning
- **Usage**: `python3 generate_diagram.py --grid`
- **Features**:
  - Fixed A4-like grid (5×5 cells)
  - One node per cell (no overlaps)
  - Deterministic positioning
- **Requirements**: None (pure Python)
- **Best for**: Simple networks or when Graphviz unavailable

### Layout Behavior
- **Tiers**: Devices grouped by type (firewall → router → dist → access → server)
- **Positioning**: Graphviz uses computed coordinates; Grid uses cell-based math
- **Links**: Always deduplicated bidirectional connections
- **Spacing**: Automatic gap calculation prevents overlaps

---

## Draw.io Shape Library (Cisco)

Always use these exact shape strings in N2G `add_node()` calls:

```python
DEVICE_SHAPES = {
    "router":       "mxgraph.cisco.routers.router",
    "switch":       "mxgraph.cisco.switches.workgroup_switch",
    "firewall":     "mxgraph.cisco.firewalls.firewall",
    "server":       "mxgraph.cisco.servers.standard_server",
    "ap":           "mxgraph.cisco.wireless.wireless_access_point",
    "wlc":          "mxgraph.cisco.wireless.wireless_lan_controller",
    "loadbalancer": "mxgraph.cisco.routers.content_engine",
    "default":      "mxgraph.cisco.routers.router",
}
```

---

## Code Rules for AI Generation

### 1. File structure
Every generated script must follow this layout:
```python
"""
Module docstring — one line description
============================
Longer description if needed.
Usage: python3 script_name.py
"""

# ── Standard library ──────────────────────────────────────────
import json, os, sys
from datetime import datetime

# ── Third-party ───────────────────────────────────────────────
from n2g import DrawIoDiagram

# ── Local ─────────────────────────────────────────────────────
from config import OUTPUT_DIR, DEVICE_SHAPES

# ── Constants ─────────────────────────────────────────────────
INPUT_JSON = "topology_data.json"

# ── Functions ─────────────────────────────────────────────────
def function_name(...):
    ...

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    ...
```

### 2. N2G usage pattern
Always use this exact pattern for building diagrams:
```python
from n2g import DrawIoDiagram

diagram = DrawIoDiagram()
diagram.add_diagram("Network Topology")  # Required for proper diagram creation

# Add node
diagram.add_node(
    id=hostname,
    label=f"{hostname}\n{ip}",
    style=DEVICE_SHAPES.get(device_type, DEVICE_SHAPES["default"]),
    width=78,
    height=78,
    x_pos=x_pos,  # Use x_pos/y_pos (not x/y) for N2G compatibility
    y_pos=y_pos,
    tooltip=f"IP: {ip}\nPlatform: {platform}",
)

# Add link
diagram.add_link(
    source=src_hostname,
    target=dst_hostname,
    label=f"{local_port}\n{remote_port}",
    style="endArrow=none;",
)

# Save
diagram.dump_file(filename="diagram.drawio", folder="output_diagrams/")
```

### 2.5. Layout engine selection
For complex diagrams, use layout engines to prevent overlaps:
```python
# Graphviz (recommended) - requires graphviz package
from layout_engine import build_positioned_diagram
diagram = build_positioned_diagram(topology)

# Grid fallback - pure Python, no external dependencies
from grid_layout import calculate_positions, validate_no_overlap
positions = calculate_positions(devices)
overlaps = validate_no_overlap(positions)  # Should return empty list
```

### 3. Error handling
All file I/O and network operations must use try/except:
```python
try:
    with open(INPUT_JSON) as f:
        topology = json.load(f)
except FileNotFoundError:
    print(f"ERROR: {INPUT_JSON} not found. Run live_puller.py first.")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in {INPUT_JSON}: {e}")
    sys.exit(1)
```

### 4. Output file naming
Always timestamp output files:
```python
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"{OUTPUT_DIR}/network_diagram_{TIMESTAMP}.drawio"
```

### 5. Deduplication of links
Always deduplicate bidirectional links:
```python
seen_links = set()
link_key = tuple(sorted([src, dst]))
if link_key in seen_links:
    continue
seen_links.add(link_key)
```

### 6. Auto-layout tiers
Devices must be positioned by tier (Y-axis) and spread evenly (X-axis):
```python
TIER_Y = {"firewall": 50, "router": 200, "dist": 380, "access": 560}
# Spread devices evenly: start_x = centre - (count-1)*spacing/2
```

---

## Copilot Prompt Templates

Use these exact phrases when asking Copilot to generate code:

### Generate from scratch
```
Using INSTRUCTIONS.md rules and the topology JSON schema,
write a Python script that [task description].
Use N2G DrawIoDiagram, follow the file structure template,
and save output to output_diagrams/ with a timestamp filename.
```

### Fix / extend existing script
```
Referring to INSTRUCTIONS.md, update generate_diagram.py to
[change description]. Keep the same N2G pattern, JSON schema,
and output naming convention.
```

### Fix layout overlaps
```
Following INSTRUCTIONS.md layout engine rules, update generate_diagram.py
to use Graphviz or Grid layout for zero-overlap positioning.
Add layout_engine.py and grid_layout.py imports, and use build_positioned_diagram()
or calculate_positions() instead of manual positioning.
```

### Add a new device type
```
Following INSTRUCTIONS.md DEVICE_SHAPES rules, add support for
[device type] devices in generate_diagram.py.
Add the correct Cisco mxgraph shape string and update classify_device().
```

---

## File Map

```
network-automation/
├── .github/
│   ├── INSTRUCTIONS.md          ← THIS FILE — attach to every Copilot prompt
│   └── copilot-instructions.md  ← Auto-loaded by VS Code Copilot extension
├── .vscode/
│   └── settings.json            ← Python path, Draw.io, Copilot settings
├── prompts/
│   ├── generate_from_json.md    ← Prompt: JSON → diagram
│   ├── add_device_type.md       ← Prompt: extend device support
│   ├── export_formats.md        ← Prompt: PNG/SVG/PDF export
│   └── github_upload.md         ← Prompt: push diagrams to GitHub
├── schemas/
│   └── topology_schema.json     ← JSON Schema (validates topology_data.json)
├── config.py                    ← Central config (paths, credentials, shapes)
├── generate_diagram.py          ← Main: JSON → Draw.io diagram (with layout engines)
├── layout_engine.py             ← Graphviz dot layout (zero overlap)
├── grid_layout.py               ← Grid math layout (fallback)
├── live_puller.py               ← SSH pull from real Cisco devices
├── scheduler.py                 ← APScheduler auto-generation
├── topology_data.json           ← Sample / last-known topology
├── requirements.txt             ← All pip dependencies
└── README.md                    ← Setup and usage guide
```

---

## Do Not

- Do not change the JSON schema field names (`hostname`, `ip`, `type`, `neighbors`, `local_port`, `remote_port`)
- Do not hardcode device IPs or credentials in scripts — use `config.py`
- Do not use `drawpyo` or `diagrams` library — this project uses `n2g` exclusively
- Do not create output files outside the `output_diagrams/` folder
- Do not add arrows (`endArrow=block`) to topology links — use `endArrow=none`
- **Do not manually position nodes without layout engines** — always use Graphviz or Grid layout for complex diagrams to prevent overlaps
- Do not use `x`/`y` parameters in N2G — use `x_pos`/`y_pos` for compatibility
