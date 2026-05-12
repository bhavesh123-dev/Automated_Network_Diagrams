"""
live_puller.py — Live Device Data Puller
=========================================
Connects to Cisco devices via SSH, runs CDP commands,
and builds topology_data.json for diagram generation.

Usage: python3 live_puller.py
"""

# ── Standard library ──────────────────────────────────────────
import json
import os
import re
import sys
import csv
from collections import defaultdict

# ── Third-party ───────────────────────────────────────────────
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
import paramiko
import time

# ── Local ─────────────────────────────────────────────────────
from config import CREDENTIALS, SEED_DEVICES, SCHEMA_FILE, classify_device, BASE_DIR, JUMP_CREDENTIALS, JUMP_SERVERS

# ── Constants ─────────────────────────────────────────────────
OUTPUT_JSON = os.path.join(BASE_DIR, "topology_data.json")
DEVICES_CSV = os.path.join(BASE_DIR, "devices.csv")

# ── Node Type Mapping ──────────────────────────────────────────
NODE_TYPE_MAPPING = {
    "Access": "access",
    "WAN": "wan_switch",
    "Distribution": "dist",
    "NX-OS": "server"
}

# ── Functions ─────────────────────────────────────────────────
def read_devices_csv(csv_path: str) -> list:
    """Read devices from CSV file and return list of device dictionaries.

    CSV columns: IP Address, System Name, Stack, Region, Country, City, Node_Type
    """
    devices = []
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        return devices

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map Node_Type to device type
            node_type = row.get('Node_Type', '').strip()
            device_type = NODE_TYPE_MAPPING.get(node_type, 'access')

            device = {
                'ip': row.get('IP Address', '').strip(),
                'hostname': row.get('System Name', '').strip(),
                'stack': row.get('Stack', '').strip().upper() == 'TRUE',
                'region': row.get('Region', '').strip(),
                'country': row.get('Country', '').strip(),
                'city': row.get('City', '').strip(),
                'node_type': device_type,
                'device_type': 'cisco_ios'  # Default device type for SSH
            }
            devices.append(device)

    print(f"Loaded {len(devices)} devices from {csv_path}")
    return devices


def normalize_hostname(hostname: str) -> str:
    """Normalize hostnames by stripping any domain component."""
    return hostname.split('.')[0].strip()


def parse_lldp_neighbors(output: str) -> list:
    """Parse 'show lldp neighbors' output into a list of neighbor dicts.

    Returns: [{"hostname": str, "local_port": str, "remote_port": str}]
    """
    neighbors = []
    lines = output.strip().split('\n')

    # Skip header lines
    data_started = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for table header
        if 'Device ID' in line and 'Local Intf' in line:
            data_started = True
            continue

        if data_started:
            # Parse LLDP lines: "SW1.example.com    Gi1/0/1     Gi1/0/1"
            parts = re.split(r'\s+', line, 3)
            if len(parts) >= 3:
                hostname = normalize_hostname(parts[0])
                local_port = parts[1]
                remote_port = parts[2] if len(parts) > 2 else ""

                neighbors.append({
                    "hostname": hostname,
                    "local_port": local_port,
                    "remote_port": remote_port
                })

    return neighbors


def parse_cdp_neighbors(output: str) -> list:
    """Parse 'show cdp neighbors detail' output into a list of neighbor dicts.

    Returns: [{"hostname": str, "local_port": str, "remote_port": str, "ip": str}]
    """
    neighbors = []
    # Split by device entries (each starts with "Device ID:")
    entries = re.split(r'\n(?=Device ID:)', output.strip())
    
    for entry in entries:
        if not entry.strip():
            continue
        
        lines = entry.split('\n')
        neighbor = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Device ID:'):
                raw_name = line.split('Device ID:')[1].strip().split('(')[0].strip()
                neighbor['hostname'] = normalize_hostname(raw_name)
            elif 'IP address:' in line:
                ip_match = re.search(r'IP address:\s*(\d+\.\d+\.\d+\.\d+)', line)
                if ip_match:
                    neighbor['ip'] = ip_match.group(1)
            elif line.startswith('Interface:'):
                ports = line.split('Interface:')[1].strip().split(',')
                if len(ports) >= 2:
                    neighbor['local_port'] = ports[0].strip()
                    neighbor['remote_port'] = ports[1].strip()
        
        if 'hostname' in neighbor:
            neighbors.append(neighbor)
    
    # Deduplicate neighbors by hostname + local/remote port
    seen = set()
    unique_neighbors = []
    for n in neighbors:
        key = (n.get('hostname'), n.get('local_port'), n.get('remote_port'))
        if key in seen:
            continue
        seen.add(key)
        unique_neighbors.append(n)

    return unique_neighbors


def parse_vlan_database(output: str) -> list:
    """Parse 'show vlan-Switch' or 'show vlan brief' output into VLAN list.

    Returns: [{"id": int, "name": str, "status": str}]
    """
    vlans = []
    lines = output.strip().split('\n')

    # Skip header lines
    data_started = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for VLAN table header or data
        if 'VLAN' in line and 'Name' in line and 'Status' in line:
            data_started = True
            continue

        if data_started:
            # Parse VLAN lines: "1    default                          active"
            parts = re.split(r'\s+', line, 2)
            if len(parts) >= 3:
                try:
                    vlan_id = int(parts[0])
                    vlan_name = parts[1]
                    vlan_status = parts[2] if len(parts) > 2 else "unknown"
                    vlans.append({
                        "id": vlan_id,
                        "name": vlan_name,
                        "status": vlan_status
                    })
                except ValueError:
                    continue

    return vlans


def parse_ip_interfaces(output: str) -> list:
    """Parse 'show ip interface brief | exclude unassigned' output.

    Returns: [{"interface": str, "ip": str, "status": str, "protocol": str}]
    """
    interfaces = []
    lines = output.strip().split('\n')

    # Skip header line
    data_started = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for interface table header
        if 'Interface' in line and 'IP-Address' in line:
            data_started = True
            continue

        if data_started:
            # Parse interface lines: "Vlan1                192.168.1.1     YES     manual up"
            parts = re.split(r'\s+', line, 3)
            if len(parts) >= 4:
                interface = parts[0]
                ip = parts[1]
                status = parts[2]
                protocol = parts[3] if len(parts) > 3 else "unknown"

                # Only include interfaces with IP addresses
                if ip != "unassigned" and re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                    interfaces.append({
                        "interface": interface,
                        "ip": ip,
                        "status": status,
                        "protocol": protocol
                    })

    return interfaces


def parse_interface_descriptions(output: str) -> list:
    """Parse 'show interface description' output to identify connected devices.

    Returns: [{"interface": str, "description": str, "status": str}]
    """
    interfaces = []
    lines = output.strip().split('\n')

    # Skip header lines
    for line in lines:
        line = line.strip()
        if not line or line.startswith('Interface') or line.startswith('-'):
            continue

        # Parse lines like: "Gi1/0/1     up             Connected to SDWAN-01"
        parts = line.split()
        if len(parts) >= 3:
            interface = parts[0]
            status = parts[1]
            description = ' '.join(parts[2:]) if len(parts) > 2 else ""

            interfaces.append({
                "interface": interface,
                "status": status,
                "description": description
            })

    return interfaces


def _build_netmiko_params(host: str, device_type: str, sock=None, use_legacy_algos: bool = False) -> dict:
    """Build Netmiko connection params.

    If use_legacy_algos is True, disable newer kex/ciphers/macs so that
    old Cisco devices (and old jump servers) can authenticate.
    """
    params = {
        "device_type": device_type,
        "host": host,
        "username": CREDENTIALS["username"],
        "password": CREDENTIALS["password"],
        "timeout": CREDENTIALS["timeout"],
        "use_keys": False,
        "allow_agent": False,
        "ssh_config_file": None,
    }

    if sock is not None:
        params["sock"] = sock

    if use_legacy_algos:
        # Enable legacy KEX/ciphers/MACs for older Cisco IOS (or old jump servers)
        params["disabled_algorithms"] = {
            "kex": [
                "diffie-hellman-group-exchange-sha256",
                "diffie-hellman-group14-sha256",
                "diffie-hellman-group16-sha512",
                "diffie-hellman-group18-sha512",
                "ecdh-sha2-nistp256",
                "ecdh-sha2-nistp384",
                "ecdh-sha2-nistp521",
                "curve25519-sha256",
                "curve25519-sha256@libssh.org",
            ],
            "ciphers": [
                "aes256-ctr",
                "aes192-ctr",
                "aes128-ctr",
                "aes256-gcm@openssh.com",
                "aes128-gcm@openssh.com",
                "chacha20-poly1305@openssh.com",
            ],
            "macs": [
                "hmac-sha2-256",
                "hmac-sha2-512",
                "hmac-sha1-etm@openssh.com",
                "hmac-sha2-256-etm@openssh.com",
                "hmac-sha2-512-etm@openssh.com",
            ],
        }

    return params


def _connect_via_jump(jump_client: paramiko.SSHClient, host: str, device_type: str, use_legacy: bool = False):
    """Open a tunnel via jump server and return a Netmiko connection."""
    jump_transport = jump_client.get_transport()
    dest_addr = (host, 22)
    local_addr = ("localhost", 0)
    jump_channel = jump_transport.open_channel("direct-tcpip", dest_addr, local_addr)

    params = _build_netmiko_params(host, device_type, sock=jump_channel, use_legacy_algos=use_legacy)
    return ConnectHandler(**params)


def _open_jump_connection() -> paramiko.SSHClient:
    """Try each configured jump server IP in order until one connects."""
    for jump_host in JUMP_SERVERS:
        jump_client = paramiko.SSHClient()
        jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            jump_client.connect(
                jump_host,
                username=JUMP_CREDENTIALS["username"],
                password=JUMP_CREDENTIALS["password"],
                timeout=JUMP_CREDENTIALS["timeout"],
                allow_agent=False,
                look_for_keys=False,
            )
            time.sleep(2)  # Sleep as jump server may be slow to respond
            return jump_client
        except Exception as e:
            print(f"WARNING: Failed to connect to jump server {jump_host}: {e}")
            jump_client.close()

    raise Exception(f"Unable to connect to any jump server: {JUMP_SERVERS}")


def get_wan_switch_connections(host: str, device_type: str = None) -> list:
    """Connect to a WAN switch and get interface descriptions for connected nodes.

    Returns: [{"hostname": str, "ip": str, "local_port": str, "remote_port": str, "link_type": str}]
    """
    if device_type is None:
        device_type = CREDENTIALS["device_type"]

    # First, connect to jump server (Rocky/Alpine compatible)
    try:
        jump_client = _open_jump_connection()

        # First attempt: modern ciphers (newer Cisco devices)
        try:
            conn = _connect_via_jump(jump_client, host, device_type, use_legacy=False)
        except Exception as e:
            # Fallback to legacy algorithms (old Cisco devices / old jump servers)
            if "no matching" in str(e).lower() or "kex" in str(e).lower() or "cipher" in str(e).lower():
                conn = _connect_via_jump(jump_client, host, device_type, use_legacy=True)
            else:
                raise

        with conn:
            # Get interface descriptions for up interfaces
            desc_output = conn.send_command("show interface description | include up")
            interfaces = parse_interface_descriptions(desc_output)

            neighbors = []
            for iface in interfaces:
                # Extract device name from description
                desc = iface["description"].lower()
                connected_hostname = None
                connected_device_type = None

                # Look for ISP indicators
                if any(keyword in desc for keyword in ["isp", "internet", "provider"]):
                    connected_hostname = "ISP"
                    connected_device_type = "isp"
                # Look for Firewall indicators
                elif any(keyword in desc for keyword in ["firewall", "fw", "asa", "palo"]):
                    connected_hostname = "Firewall"
                    connected_device_type = "firewall"
                # Look for SDWAN indicators
                elif any(keyword in desc for keyword in ["sdwan", "vce", "velo", "edge", "work", "wan"]):
                    # Try to extract hostname from description
                    # Common patterns: "Connected to SDWAN-01" or "SDWAN-01 port"
                    desc_parts = iface["description"].split()
                    for part in desc_parts:
                        if any(keyword in part.lower() for keyword in ["sdwan", "vce", "velo", "edge"]):
                            connected_hostname = part.strip('.,')
                            break

                    if not connected_hostname:
                        # Look for the word after common connectors
                        connectors = ["to", "from", "connected"]
                        for i, part in enumerate(desc_parts):
                            if part.lower() in connectors and i + 1 < len(desc_parts):
                                connected_hostname = desc_parts[i + 1].strip('.,')
                                break
                    
                    if not connected_hostname:
                        connected_hostname = "SDWAN"
                    connected_device_type = "sdwan"

                if connected_hostname:
                    # Extract remote port from description (try to find interface name)
                    remote_port = ""
                    for port_type in ["GE", "Gi", "Fa", "Eth", "Port", "port"]:
                        if port_type.lower() in desc.lower():
                            remote_port = port_type
                            break
                    
                    neighbors.append({
                        "hostname": connected_hostname,
                        "ip": "unknown",
                        "local_port": iface["interface"],
                        "remote_port": remote_port if remote_port else "unknown",
                        "link_type": "access"
                    })

            return neighbors

    except Exception as e:
        print(f"WARNING: Failed to get WAN switch connections from {host}: {e}")
        return []
    finally:
        if 'jump_client' in locals() and jump_client is not None:
            jump_client.close()


def get_device_info(host: str, device_type: str = None) -> dict:
    """Connect to a device and get hostname, platform, CDP neighbors, VLANs, and IP interfaces."""
    if device_type is None:
        device_type = CREDENTIALS["device_type"]

    # First, connect to jump server (Rocky/Alpine compatible)
    try:
        jump_client = _open_jump_connection()

        # First attempt: modern algorithms (newer Cisco devices)
        try:
            conn = _connect_via_jump(jump_client, host, device_type, use_legacy=False)
        except Exception as e:
            # Fallback to legacy algorithms for old Cisco devices / older SSH implementations
            if "no matching" in str(e).lower() or "kex" in str(e).lower() or "cipher" in str(e).lower():
                conn = _connect_via_jump(jump_client, host, device_type, use_legacy=True)
            else:
                raise

        with conn:
            # Get hostname
            hostname_output = conn.send_command("show version | include uptime")
            hostname_match = re.search(r"(\S+)\s+uptime", hostname_output)
            hostname = hostname_match.group(1) if hostname_match else host

            # Get platform
            platform_output = conn.send_command("show version | include Cisco")
            platform = "Cisco IOS"  # Default
            if "IOS-XE" in platform_output:
                platform = "Cisco IOS-XE"
            elif "NX-OS" in platform_output:
                platform = "Cisco NX-OS"

            # Get CDP neighbors
            cdp_output = conn.send_command("show cdp neighbors detail")
            neighbors = parse_cdp_neighbors(cdp_output)

            # Get LLDP neighbors (for Juniper and additional Cisco devices)
            try:
                lldp_output = conn.send_command("show lldp neighbors")
                lldp_neighbors = parse_lldp_neighbors(lldp_output)
                # Merge LLDP neighbors with CDP neighbors
                neighbors.extend(lldp_neighbors)
            except Exception:
                # LLDP not supported or failed, continue with CDP only
                pass

            # Get VLAN information (test environment - will be changed to 'show vlan brief' for production)
            # TODO: Uncomment the production command below when ready for real devices
            # vlan_output = conn.send_command("show vlan brief")
            vlan_output = conn.send_command("show vlan-switch brief")  # Test environment only
            vlans = parse_vlan_database(vlan_output)

            # Get IP interface information
            ip_output = conn.send_command("show ip interface brief | exclude unassigned")
            ip_interfaces = parse_ip_interfaces(ip_output)

            return {
                "hostname": hostname,
                "ip": host,
                "platform": platform,
                "neighbors": neighbors,
                "vlans": vlans,
                "ip_interfaces": ip_interfaces
            }
    except (NetmikoTimeoutException, NetmikoAuthenticationException, paramiko.SSHException) as e:
        print(f"ERROR: Failed to connect to {host} via jump server: {e}")
        return None
    finally:
        if 'jump_client' in locals() and jump_client is not None:
            jump_client.close()


def is_ip(address: str) -> bool:
    """Return True if the address is an IPv4 address."""
    return bool(re.match(r"^\d+\.\d+\.\d+\.\d+$", address))


def crawl_topology(devices_csv: list) -> dict:
    """Process devices from CSV file, collecting device information.

    Returns: {"devices": [device_dicts]}
    """
    devices = []
    device_map = {}  # normalized hostname -> device dict

    def add_or_merge_device(device_info: dict):
        """Add device to list or merge if already present (avoid duplicates)."""
        hostname = normalize_hostname(device_info["hostname"])
        device_info["hostname"] = hostname

        # Task 7: Classify links as access, trunk, or L3
        for n in device_info.get("neighbors", []):
            # Example logic: trunk if interface contains 'trunk', L3 if 'routed', else access
            local_port = n.get("local_port", "").lower()
            remote_port = n.get("remote_port", "").lower()
            if "trunk" in local_port or "trunk" in remote_port:
                n["link_type"] = "trunk"
            elif "routed" in local_port or "routed" in remote_port:
                n["link_type"] = "l3"
            else:
                n["link_type"] = "access"

        existing = device_map.get(hostname)
        if existing:
            # Merge neighbors (avoid duplicates)
            existing_neighbors = {(n.get("hostname"), n.get("local_port"), n.get("remote_port"))
                                  for n in existing.get("neighbors", [])}
            for n in device_info.get("neighbors", []):
                key = (n.get("hostname"), n.get("local_port"), n.get("remote_port"))
                if key not in existing_neighbors:
                    existing["neighbors"].append(n)
                    existing_neighbors.add(key)
            return existing

        devices.append(device_info)
        device_map[hostname] = device_info
        return device_info

    # Process each device from CSV
    for csv_device in devices_csv:
        host = csv_device['ip']
        device_type = csv_device.get('device_type', 'cisco_ios')

        print(f"Processing device: {csv_device['hostname']} ({host})")

        # Get device information via SSH
        device_info = get_device_info(host, device_type)
        if not device_info:
            # If SSH fails, create basic device info from CSV
            device_info = {
                "hostname": csv_device['hostname'],
                "ip": host,
                "platform": "Unknown",
                "neighbors": [],
                "vlans": [],
                "ip_interfaces": []
            }

        # Add CSV metadata
        device_info.update({
            "region": csv_device.get('region', ''),
            "country": csv_device.get('country', ''),
            "city": csv_device.get('city', ''),
            "stack": csv_device.get('stack', False),
            "node_type": csv_device.get('node_type', 'access')
        })

        device_info["neighbors"] = [
            {**n, "hostname": normalize_hostname(n.get("hostname", ""))}
            for n in device_info.get("neighbors", [])
        ]

        add_or_merge_device(device_info)

    # Set device types from CSV node_type
    from config import TIER_KEYWORDS
    for device in devices:
        device["type"] = device.get("node_type", "access")

        # Additional access point detection based on neighbors
        if device["type"] == "access":  # Only check if not already classified as AP
            for neighbor in device.get("neighbors", []):
                neighbor_hostname = neighbor.get("hostname", "").upper()
                if any(ap_keyword in neighbor_hostname for ap_keyword in ["AP-", "WAP", "AIRONET", "WLC"]):
                    device["type"] = "ap"
                    break

        # Task 4: Identify and classify non-CDP/LLDP neighbours
        cdp_lldp_hostnames = {n.get("hostname") for n in device.get("neighbors", [])}
        # Parse trunk interfaces (simulate trunk parsing)
        trunk_interfaces = []  # TODO: parse from device info if available
        # Parse interface descriptions for non-CDP/LLDP neighbours
        desc_interfaces = []  # TODO: parse from device info if available
        # For each interface description, if not in CDP/LLDP, classify
        for iface in desc_interfaces:
            if iface["interface"] not in trunk_interfaces:
                desc = iface["description"].lower()
                # Infer device type from description using TIER_KEYWORDS
                device_type = "other"
                for tier, keywords in TIER_KEYWORDS.items():
                    if any(keyword.lower() in desc for keyword in keywords):
                        device_type = tier
                        break
                # Add as neighbour with rectangle icon and type as label
                device["neighbors"].append({
                    "hostname": iface["description"],
                    "local_port": iface["interface"],
                    "remote_port": "",
                    "device_type": device_type,
                    "icon": "rectangle",
                    "label": device_type.capitalize()
                })

    # Get WAN connections for WAN switches and merge into neighbors
    for device in devices:
        if device["type"] == "wan_switch":
            print(f"Checking WAN switch connections for {device['hostname']}...")
            wan_neighbors = get_wan_switch_connections(device["ip"])
            if wan_neighbors:
                # Merge WAN neighbors into the existing neighbors list
                existing_neighbors = {(n.get("hostname"), n.get("local_port"), n.get("remote_port"))
                                      for n in device.get("neighbors", [])}
                for wan_neighbor in wan_neighbors:
                    key = (wan_neighbor.get("hostname"), wan_neighbor.get("local_port"), wan_neighbor.get("remote_port"))
                    if key not in existing_neighbors:
                        device["neighbors"].append(wan_neighbor)
                        existing_neighbors.add(key)
                print(f"  Found {len(wan_neighbors)} WAN-connected devices")

    # Task 4: Add synthetic devices for neighbors that are not accessible via SSH
    # (ISP, SDWAN, Firewall, etc.)
    existing_hostnames = {d["hostname"] for d in devices}
    synthetic_devices = {}
    
    # Tier mapping for device types
    tier_map = {
        "isp": 0,
        "wan_switch": 1,
        "sdwan": 2,
        "firewall": 3,
        "dist": 4,
        "access": 5,
        "ap": 6
    }
    
    for device in devices:
        for neighbor in device.get("neighbors", []):
            neighbor_hostname = neighbor.get("hostname")
            
            # Check if this is a synthetic neighbor (not in existing device list and marked as external)
            # External devices typically have empty IP or are from WAN connections
            if (neighbor_hostname and 
                neighbor_hostname not in existing_hostnames and 
                neighbor_hostname not in synthetic_devices and
                neighbor.get("ip") == "unknown"):
                
                # Infer device type from neighbor hostname
                neighbor_hostname_lower = neighbor_hostname.lower()
                device_type = "other"
                for key, keywords in {"isp": ["isp"], "sdwan": ["sdwan", "vce", "velo", "edge"], 
                                     "firewall": ["firewall", "fw", "asa"]}.items():
                    if any(keyword in neighbor_hostname_lower for keyword in keywords):
                        device_type = key
                        break
                
                synthetic_device = {
                    "hostname": neighbor_hostname,
                    "ip": "",  # External devices don't have SSH-accessible IPs
                    "platform": "External",
                    "neighbors": [],
                    "vlans": [],
                    "ip_interfaces": [],
                    "region": device.get("region", ""),
                    "country": device.get("country", ""),
                    "city": device.get("city", ""),
                    "stack": False,
                    "node_type": device_type,
                    "type": device_type,
                    "is_synthetic": True,  # Mark as non-SSH device
                    "tier": tier_map.get(device_type, 999)  # Assign explicit tier level
                }
                synthetic_devices[neighbor_hostname] = synthetic_device
                existing_hostnames.add(neighbor_hostname)
    
    # Add synthetic devices to devices list
    devices.extend(synthetic_devices.values())

    return {"devices": devices}

if __name__ == "__main__":
    # Read devices from CSV file
    devices_csv = read_devices_csv(DEVICES_CSV)
    if not devices_csv:
        print(f"ERROR: No devices found in {DEVICES_CSV}")
        sys.exit(1)

    print("Starting network topology processing...")
    topology = crawl_topology(devices_csv)

    # Task 5: Save topology_data.json in Region/Country/City/City_topology_data_latest.json
    import datetime
    region = topology["devices"][0].get("region", "Unknown")
    country = topology["devices"][0].get("country", "Unknown")
    city = topology["devices"][0].get("city", "Unknown")
    base_folder = os.path.join(BASE_DIR, "topology_data", region, country, city)
    os.makedirs(base_folder, exist_ok=True)
    latest_file = os.path.join(base_folder, f"{city}_topology_data_latest.json")
    history_folder = os.path.join(base_folder, "history")
    os.makedirs(history_folder, exist_ok=True)

    # Archive old file if exists
    if os.path.exists(latest_file):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = os.path.join(history_folder, f"{city}_topology_data_{timestamp}.json")
        os.rename(latest_file, archive_file)

    try:
        with open(latest_file, 'w') as f:
            json.dump(topology, f, indent=2)
        print(f"Topology data saved to {latest_file}")
    except Exception as e:
        print(f"ERROR: Failed to save {latest_file}: {e}")
        sys.exit(1)