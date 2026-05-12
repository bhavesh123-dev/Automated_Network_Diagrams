# Prompt: Pull Live Data from Network Devices
> Attach `.github/INSTRUCTIONS.md` to Copilot Chat before using this prompt.

---

## Use this prompt when:
You want to pull real CDP neighbour data from Cisco devices via SSH
and save it as topology_data.json for diagram generation.

---

## Prompt (copy → paste into Copilot Chat)

```
Using INSTRUCTIONS.md rules and config.py settings, write a Python
script called live_puller.py that:

1. Reads SEED_DEVICES and CREDENTIALS from config.py (never hardcode)

2. For each seed device, SSH in using Netmiko ConnectHandler:
   - device_type from config or per-device override
   - timeout from CREDENTIALS["timeout"]

3. Run these commands and capture output:
   - "show cdp neighbors detail"   → parse neighbour hostnames + ports
   - "show version | include IOS"  → extract platform string
   - "show run | include hostname"  → confirm hostname

4. Parse CDP output to extract for each neighbour:
   - hostname (strip domain suffix after first dot)
   - local_port (Interface field)
   - remote_port (Port ID outgoing port field)
   - ip (IP address field if present)

5. Auto-discover: queue unvisited neighbour IPs for SSH crawl
   (stop crawl if neighbour IP is unreachable after timeout)

6. Build topology dict matching topology_schema.json structure

7. Save to topology_data.json with metadata.generated_at timestamp

8. Print progress: "Connecting to X...", "OK: HOSTNAME — N neighbours"

Handle NetmikoTimeoutException and NetmikoAuthenticationException
gracefully — log the failure and continue crawling other devices.
```

---

## Quick test (no real devices)

To test the parser logic without real devices, use this mock:
```python
# In live_puller.py, replace SSH call with:
cdp_output = open("tests/mock_cdp_output.txt").read()
```
See `tests/mock_cdp_output.txt` for sample CDP output format.

---

## Variations

**Juniper / LLDP support:**
```
Update live_puller.py to also support Juniper devices
(device_type="juniper_junos"). Use "show lldp neighbors detail"
instead of CDP, and map the LLDP fields to the same JSON schema.
```

**Parallel SSH (faster for large networks):**
```
Update live_puller.py to use concurrent.futures.ThreadPoolExecutor
to SSH into multiple devices in parallel (max 10 workers).
Keep the deduplication and crawl logic thread-safe.
```
