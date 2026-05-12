# Network Automation & Topology Visualization

A comprehensive Python-based tool for automated network topology discovery, inventory collection, and professional diagram generation. Discovers Cisco network devices via SSH, parses CDP neighbor data, and creates editable Draw.io diagrams with zero-overlap positioning using advanced layout engines.

## ✨ Key Features

### 🔍 **Network Discovery & Data Collection**
- **SSH-based Discovery**: Securely connects to Cisco devices via SSH with support for legacy algorithms
- **CDP Neighbor Parsing**: Automatically discovers network topology through Cisco Discovery Protocol
- **Device Classification**: Intelligent device type detection (routers, switches, firewalls, etc.)
- **Deduplication**: Handles duplicate hostnames and merges neighbor data

### 📊 **Professional Diagram Generation**
- **Zero-Overlap Layouts**: Two layout engines prevent node stacking in complex networks
- **Graphviz Integration**: Hierarchical positioning using industry-standard graph layout algorithms
- **Grid Fallback**: Mathematical grid positioning for reliable, deterministic layouts
- **Cisco Shape Library**: Authentic Cisco device icons and styling

### 🔧 **Automation & Integration**
- **Scheduled Generation**: APScheduler for automated periodic diagram updates
- **GitHub Integration**: Auto-push diagrams to repositories for team collaboration
- **Multiple Export Formats**: Draw.io, PNG, SVG, PDF support
- **JSON Schema Validation**: Structured data validation for reliability

### 🛡️ **Enterprise-Ready**
- **Secure Credentials**: Environment variable-based credential management
- **Error Handling**: Comprehensive error handling and logging
- **Modular Architecture**: Clean separation of concerns for maintainability

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Cisco Devices  │────│  live_puller.py  │────│ topology_data.  │
│  (SSH Access)   │    │  (SSH + CDP)     │    │ json            │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌──────────────────┐           ▼
│  Layout Engine  │────│ generate_diagram │    ┌─────────────────┐
│  (Graphviz/Grid)│    │ .py (N2G)        │────│ .drawio files   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌──────────────────┐           ▼
│  Export Tools   │────│ scheduler.py     │    ┌─────────────────┐
│  (PNG/SVG/PDF)  │    │ (APScheduler)    │────│ GitHub Repo     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

- **Python**: 3.10 or higher
- **System Packages**:
  - `graphviz` (Ubuntu/Debian: `sudo apt install graphviz`)
  - `openssh-client` (for SSH access)
- **Network Access**: SSH access to Cisco devices (IOS/IOS-XE/NX-OS)
- **VS Code**: With Draw.io extension for diagram editing (optional)

## 🚀 Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd Automation-of-Network
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install System Dependencies (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y graphviz
```

### 5. Configure Environment
```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your credentials and settings
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# SSH Credentials
NET_USERNAME=your_username
NET_PASSWORD=your_password

# GitHub Integration (optional)
GITHUB_TOKEN=your_github_token
GITHUB_REPO=your-org/network-diagrams

# Scheduling
SCHEDULE_TIMEZONE=UTC
```

### Device Configuration
- **SEED_DEVICES**: Configure initial devices in `config.py`
- **CREDENTIALS**: SSH connection settings with legacy algorithm support
- **DEVICE_SHAPES**: Cisco icon mappings for different device types

## 📖 Usage

### 1. Network Discovery (Live Data Collection)
```bash
python3 live_puller.py
```
- Connects to seed devices via SSH
- Discovers neighbors through CDP
- Generates `topology_data.json` with complete topology

### 2. Diagram Generation (Graphviz Layout - Recommended)
```bash
python3 generate_diagram.py
```
- Uses Graphviz for hierarchical, overlap-free positioning
- Generates timestamped `.drawio` files in `output_diagrams/`

### 3. Diagram Generation (Grid Layout - Fallback)
```bash
python3 generate_diagram.py --grid
```
- Uses mathematical grid positioning
- Reliable when Graphviz is unavailable

### 4. Scheduled Automation
```bash
python3 scheduler.py
```
- Runs diagram generation on a schedule (default: hourly)
- Automatically pushes to GitHub if configured

### 5. Manual GitHub Upload
```bash
python3 github_uploader.py
```
- Uploads generated diagrams to configured GitHub repository

## 🎨 Layout Engines Explained

### Graphviz Dot Layout (Recommended)
- **Algorithm**: Hierarchical top-down positioning using Graphviz `dot`
- **Best For**: Complex networks with many devices and connections
- **Features**:
  - Zero overlap guarantee
  - Automatic tier-based ranking
  - Professional network diagram appearance
- **Requirements**: Graphviz system package installed

### Grid Layout (Fallback)
- **Algorithm**: Mathematical cell-based positioning
- **Best For**: Simple networks or when Graphviz unavailable
- **Features**:
  - Fixed 5×5 grid with one node per cell
  - Deterministic positioning
  - No external dependencies
- **Reliability**: Always works, never overlaps

### Device Classification & Tiers
Devices are automatically classified into tiers:
- **Firewall** (top tier)
- **Router** (core tier)
- **Distribution** (dist tier)
- **Access** (access tier)
- **Server** (bottom tier)

## 📁 Project Structure

```
Automation-of-Network/
├── 📄 README.md                    # This file
├── 📄 INSTRUCTIONS.md              # AI code generation guide
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment template
├── 📄 .gitignore                   # Git ignore rules
├── 📁 output_diagrams/             # Generated diagram files
├── 📁 schemas/                     # JSON schema validation
│   └── 📄 topology_schema.json
├── 📁 Reference/                   # Documentation and examples
├── 📄 config.py                    # Central configuration
├── 📄 live_puller.py               # SSH network discovery
├── 📄 generate_diagram.py          # Diagram generation with layout engines
├── 📄 layout_engine.py             # Graphviz layout implementation
├── 📄 grid_layout.py               # Grid layout implementation
├── 📄 scheduler.py                 # Automated scheduling
├── 📄 github_uploader.py           # GitHub integration
├── 📄 topology_data.json           # Current topology data
├── 📄 credentials.txt              # SSH credentials (gitignored)
├── 📄 devices.txt                  # Device IP list
└── 📄 settings.json                # VS Code settings
```

## 🔧 Advanced Configuration

### Custom Device Types
Add new device types in `config.py`:
```python
DEVICE_SHAPES = {
    "custom_device": "mxgraph.cisco.routers.router",
    # ... existing types
}

TIER_KEYWORDS = {
    "custom": ["CUSTOM", "MYDEVICE"],
    # ... existing keywords
}
```

### Layout Customization
Modify layout parameters in `config.py`:
```python
# Grid layout settings
PAGE_WIDTH = 1000
PAGE_HEIGHT = 1400
GRID_COLS = 5
GRID_ROWS = 5

# Graphviz layout settings (in layout_engine.py)
DOT_DPI = 72
PX_SCALE = 1.8
```

### SSH Legacy Support
For older Cisco devices with legacy SSH algorithms:
```python
CREDENTIALS = {
    "device_type": "cisco_ios",
    "disabled_algorithms": {
        "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"],
        "kex": ["diffie-hellman-group-exchange-sha256"],
        "ciphers": ["aes128-cbc", "3des-cbc"]
    }
}
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Install development dependencies
4. Make your changes
5. Run tests and validation
6. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Add type hints for new functions
- Update `INSTRUCTIONS.md` for AI-generated code
- Test with both layout engines
- Document new features in README.md

### Testing
- Test with real Cisco devices when possible
- Validate JSON schema compliance
- Check diagram generation with both layout engines
- Verify GitHub integration functionality

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues
- **SSH Connection Failed**: Check credentials and network access
- **Graphviz Not Found**: Install system package `sudo apt install graphviz`
- **Layout Overlaps**: Use Graphviz layout or `--grid` fallback
- **Import Errors**: Ensure virtual environment is activated

### Support
- Check `INSTRUCTIONS.md` for detailed technical guidance
- Review existing issues and solutions
- Create new issues with detailed error logs

---

**Built with ❤️ for network engineers who value automation and visualization**
