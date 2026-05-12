# Prompt: Export Diagrams to PNG / SVG / PDF
> Attach `.github/INSTRUCTIONS.md` to Copilot Chat before using this prompt.

---

## Use this prompt when:
You want to convert the `.drawio` output file into PNG, SVG, or PDF
for sharing with the client without requiring Draw.io to be installed.

---

## Method 1 — Draw.io CLI (Best quality, recommended)

### Setup (Ubuntu)
```bash
# Install Draw.io desktop app (includes CLI)
sudo snap install drawio

# Test CLI export
drawio --export --format png --output output.png input.drawio
```

### Prompt for Copilot
```
Write a Python function called export_diagram(drawio_path, formats)
that uses subprocess to call the Draw.io CLI and export the diagram
to the specified formats.

formats is a list like ["png", "svg", "pdf"]

For each format:
- Build the output path by replacing .drawio extension with the format
- Call: drawio --export --format FORMAT --output OUTPUT INPUT
- Log success or failure for each format
- Return a dict of {format: output_path} for successful exports

Use config.EXPORT_FORMATS as the default format list.
```

---

## Method 2 — graphviz2drawio

### Setup
```bash
pip install graphviz2drawio graphviz
sudo apt install graphviz -y
```

### Prompt for Copilot
```
Write a Python function that:
1. Takes a NetworkX graph object of the topology
2. Converts it to a graphviz Digraph using networkx.drawing.nx_agraph
3. Renders PNG and SVG using graphviz source.render()
4. Also converts to Draw.io XML using graphviz2drawio.convert()
5. Saves all outputs to output_diagrams/ with the same timestamp base name

This is the secondary export path — primary is N2G DrawIoDiagram.
```

---

## Method 3 — Pillow (PNG from diagram data, no CLI)

### Prompt for Copilot
```
Write a Python function called render_topology_image(topology, output_path)
that uses matplotlib + networkx to render a quick PNG of the topology.
Use a hierarchical spring layout with nodes coloured by device type:
- router: blue (#1565C0)
- switch: teal (#00695C)  
- firewall: red (#B71C1C)
- server: gray (#424242)
- ap: green (#2E7D32)

This is for quick preview only — the real diagram is the .drawio file.
```

---

## Variation — Auto-export after every generation

```
Update generate_diagram.py to call export_diagram() automatically
after saving the .drawio file, using config.EXPORT_FORMATS.
Print the path of each exported file.
```
