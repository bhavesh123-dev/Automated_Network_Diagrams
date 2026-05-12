# Prompt: Generate Diagram from JSON
> Attach `.github/INSTRUCTIONS.md` to Copilot Chat before using this prompt.

---

## Use this prompt when:
You want Copilot to write or rewrite `generate_diagram.py` from scratch
or add a new feature to the diagram generation pipeline.

---

## Prompt (copy → paste into Copilot Chat)

```
Using the rules in INSTRUCTIONS.md and the topology JSON schema,
write a Python script called generate_diagram.py that:

1. Loads topology_data.json and validates required fields
   (hostname, ip, type, platform, neighbors)

2. Classifies each device into a tier using classify_device() from config.py
   Tiers: firewall → router → dist → access

3. Auto-calculates x/y positions:
   - Y position per tier from config.TIER_Y
   - X positions: centre devices evenly with TIER_SPACING_X gap

4. Creates a DrawIoDiagram using N2G:
   - add_node() for each device using DEVICE_SHAPES from config.py
   - Tooltip shows: IP, Platform, Type
   - add_link() for each unique neighbour pair (deduplicate bidirectional)
   - Link label shows local_port and remote_port

5. Saves the diagram to output_diagrams/ with a timestamp filename

6. Prints a summary: device count, link count, output path

Follow the file structure template and error handling rules in INSTRUCTIONS.md.
```

---

## Example output to expect

```
Network Diagram Generator — N2G
----------------------------------------
Loaded 8 devices from topology_data.json
Built diagram: 8 nodes, 7 links
Saved → output_diagrams/network_diagram_20260314_112400.drawio

==================================================
  NETWORK TOPOLOGY SUMMARY
==================================================
  Firewall     : 1
  Router       : 1
  Switch       : 6
  Total        : 8
==================================================
```

---

## Variations

**Add PNG export:**
```
Extend generate_diagram.py to also export a PNG image using
the diagrams library or subprocess call to Draw.io CLI.
Save as output_diagrams/network_diagram_TIMESTAMP.png
```

**Add multi-site support:**
```
Update generate_diagram.py to handle a topology_data.json
that contains a "site" field per device, and group devices
into labelled containers (dashed rect) per site in the diagram.
```
