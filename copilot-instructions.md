# Copilot Workspace Instructions
# Auto-loaded by VS Code GitHub Copilot extension for this workspace.

This project generates Cisco network topology diagrams from JSON data using
the N2G library. Key rules:

- Always use `n2g.DrawIoDiagram` for diagram creation — never `drawpyo` or `diagrams`
- Read topology from `topology_data.json` using the schema in `.github/INSTRUCTIONS.md`
- Map device types to Cisco mxgraph shapes using `DEVICE_SHAPES` dict in `config.py`
- Save all outputs to `output_diagrams/` with timestamp in filename
- Deduplicate bidirectional links using `tuple(sorted([src, dst]))`
- Auto-layout: firewall y=50, router y=200, distribution y=380, access y=560
- SSH device connections use Netmiko — credentials always from `config.py`, never hardcoded
- Follow the file structure template in INSTRUCTIONS.md for every new script

For full schema, shape library, and code patterns see `.github/INSTRUCTIONS.md`.
