# Network Automation Project - File Manifest
## Complete File Inventory and Explanations

**Project**: Network Automation & Topology Visualization  
**Date**: March 15, 2026  
**Purpose**: Automated Cisco network discovery, topology mapping, and professional diagram generation

---

## 📁 Project Structure Overview

```
Automation-of-Network/
├── 📋 Documentation & Configuration
├── 🔧 Core Python Scripts
├── 🎨 Layout Engines
├── 🤖 Automation & Integration
├── 📊 Data Files
├── ⚙️ Development & Build Files
└── 📁 Parent Directory (Examples)
```

---

## 📋 Documentation & Configuration Files

### 📖 README.md
**Purpose**: Main project documentation and user guide  
**Contents**: Comprehensive installation, usage, and configuration instructions  
**Audience**: End users, developers, and system administrators  
**Key Sections**:
- Project overview and features
- Architecture diagram
- Installation steps (Python + system dependencies)
- Usage examples for all scripts
- Layout engine explanations
- Troubleshooting guide

### 📚 INSTRUCTIONS.md
**Purpose**: AI code generation guide for GitHub Copilot and other AI tools  
**Contents**: Technical specifications, coding standards, and development rules  
**Audience**: AI assistants and developers generating code  
**Key Sections**:
- Technology stack requirements
- JSON schema definitions
- N2G usage patterns
- Layout engine specifications
- Code structure templates
- Copilot prompt templates

### ⚙️ config.py
**Purpose**: Central configuration file for all project settings  
**Contents**: Device shapes, credentials, paths, layout parameters, and constants  
**Key Components**:
- `DEVICE_SHAPES`: Cisco Draw.io shape mappings
- `CREDENTIALS`: SSH connection settings with legacy algorithm support
- `SEED_DEVICES`: Initial network devices for discovery
- `TIER_Y`: Vertical positioning for device tiers
- `PAGE_WIDTH/HEIGHT`: Diagram canvas dimensions
- `classify_device()`: Automatic device type detection

### 🔧 .gitignore
**Purpose**: Git ignore rules to protect sensitive data and exclude generated files  
**Contents**: Patterns for credentials, virtual environments, cache files, and outputs  
**Key Rules**:
- `credentials.txt` (sensitive SSH credentials)
- `__pycache__/` (Python bytecode)
- `output_diagrams/` (generated diagram files)
- `.env` (environment variables)

### 🛠️ settings.json
**Purpose**: VS Code workspace configuration  
**Contents**: Python interpreter, formatting, and Draw.io settings  
**Key Settings**:
- Python virtual environment configuration
- Code formatting (autopep8, 88 char line length)
- Draw.io file associations
- Editor preferences (tabs, rulers)

### 📝 copilot-instructions.md
**Purpose**: VS Code GitHub Copilot workspace instructions  
**Contents**: Auto-loaded rules for AI-assisted coding in this project  
**Key Rules**:
- Always use N2G library for diagrams
- Follow INSTRUCTIONS.md patterns
- Use config.py for all settings
- Proper file structure and naming

---

## 🔧 Core Python Scripts

### 🌐 live_puller.py
**Purpose**: Network device discovery and topology data collection  
**Functionality**:
- SSH connection to Cisco devices using Netmiko
- CDP neighbor discovery and parsing
- Device information collection (hostname, IP, platform, type)
- Topology relationship mapping
- Deduplication of duplicate hostnames
- JSON output generation (`topology_data.json`)

**Key Features**:
- Legacy SSH algorithm support for older devices
- Jump server/bastion host support
- Error handling and retry logic
- Configurable seed devices

### 🎨 generate_diagram.py
**Purpose**: Professional network topology diagram generation  
**Functionality**:
- JSON topology data parsing and validation
- Automatic layout engine selection (Graphviz preferred, Grid fallback)
- Draw.io XML diagram creation using N2G library
- Cisco device shape rendering
- Link deduplication and labeling
- Timestamped output file generation

**Key Features**:
- Zero-overlap positioning guarantee
- Hierarchical device tiering
- Multiple export format support
- Command-line options (`--grid` for fallback layout)

### 📊 scheduler.py
**Purpose**: Automated periodic diagram generation and maintenance  
**Functionality**:
- APScheduler integration for cron-like job scheduling
- Configurable execution intervals
- Automatic diagram regeneration
- Optional GitHub integration for uploads
- Logging and error reporting

**Key Features**:
- Configurable timezone and frequency
- Background execution
- Integration with other project components

### 📤 github_uploader.py
**Purpose**: Automated diagram publishing to GitHub repositories  
**Functionality**:
- GitHub API integration using PyGithub
- Authentication via personal access tokens
- File upload to specified repository and branch
- Directory structure preservation
- Error handling and status reporting

**Key Features**:
- Environment variable configuration
- Batch upload support
- Repository and branch flexibility

---

## 🎨 Layout Engine Scripts

### 🔄 layout_engine.py
**Purpose**: Graphviz-based hierarchical diagram layout (recommended)  
**Functionality**:
- Graphviz `dot` algorithm integration
- Automatic node positioning without overlaps
- Pixel-perfect coordinate calculation
- N2G diagram integration
- Device tier-based ranking

**Key Features**:
- Zero overlap guarantee
- Professional network diagram appearance
- Automatic scaling and centering
- Fallback handling when Graphviz unavailable

### 📐 grid_layout.py
**Purpose**: Mathematical grid-based layout (fallback when Graphviz unavailable)  
**Functionality**:
- Fixed grid positioning (5×5 cells)
- One node per cell guarantee
- Mathematical coordinate calculation
- Overlap validation and reporting
- Deterministic layout results

**Key Features**:
- No external dependencies
- Predictable positioning
- Validation of layout constraints
- Pure Python implementation

---

## 📊 Data Files

### 🗂️ topology_data.json
**Purpose**: Current network topology data (primary working file)  
**Contents**: JSON-formatted network device inventory and relationships  
**Structure**:
```json
{
  "devices": [
    {
      "hostname": "SWITCH01",
      "ip": "192.168.1.100",
      "type": "switch",
      "platform": "Cisco IOS",
      "neighbors": [...]
    }
  ]
}
```

### 🗂️ topology_data1.json
**Purpose**: Alternative/backup topology data file  
**Contents**: Secondary JSON topology dataset for testing or comparison  
**Usage**: Reference data or testing scenarios

### 📋 topology_schema.json
**Purpose**: JSON Schema validation for topology data files  
**Contents**: Formal schema definition for topology_data.json structure  
**Validation**: Ensures data integrity and required field presence

### 📄 mock_cdp_output.txt
**Purpose**: Sample CDP command output for testing and development  
**Contents**: Realistic Cisco `show cdp neighbors` command output  
**Usage**: Testing CDP parsing logic without live network access

### 📝 devices.txt
**Purpose**: Network device IP address inventory  
**Contents**: List of target device IP addresses (one per line)  
**Format**: Plain text, one IP address per line  
**Usage**: Input for network discovery scripts

### 🔐 credentials.txt
**Purpose**: SSH authentication credentials (runtime file)  
**Contents**: Username:password pairs for device access  
**Security**: Gitignored, contains sensitive authentication data  
**Format**: `username:password` (one per line)

---

## ⚙️ Development & Build Files

### 📦 requirements.txt
**Purpose**: Python package dependencies and versions  
**Contents**: All required Python packages with version constraints  
**Categories**:
- Core dependencies (n2g, netmiko, graphviz)
- Automation (APScheduler, PyGithub)
- Image processing (pillow, reportlab)
- Utilities (python-dotenv)

**Installation**: `pip install -r requirements.txt`

### 🔧 .env.example
**Purpose**: Environment variable template file  
**Contents**: Example configuration for sensitive settings  
**Variables**:
- `NET_USERNAME`: SSH username
- `NET_PASSWORD`: SSH password
- `GITHUB_TOKEN`: GitHub API token
- `GITHUB_REPO`: Target repository

### 📋 project structure
**Purpose**: Outdated project structure documentation  
**Contents**: Historical view of intended project organization  
**Status**: Reference only, superseded by actual structure

### 📄 Prompt
**Purpose**: Original project requirements and specifications  
**Contents**: Initial development brief and feature requirements  
**Status**: Historical reference document

---

## 📁 Parent Directory Files (Examples & References)

### 📋 generate_diagram-example.py
**Location**: `/home/bhavesh/Documents/Automation/`  
**Purpose**: Example implementation of diagram generation  
**Contents**: Alternative version with different layout approaches  
**Status**: Reference implementation, not part of main codebase

### 📋 layout-engine-example.py
**Location**: `/home/bhavesh/Documents/Automation/`  
**Purpose**: Example Graphviz layout engine implementation  
**Contents**: Standalone layout engine for reference  
**Status**: Development example, superseded by `layout_engine.py`

### 📋 grid_layout.py (Parent)
**Location**: `/home/bhavesh/Documents/Automation/`  
**Purpose**: Duplicate grid layout implementation  
**Contents**: Alternative grid positioning logic  
**Status**: Superseded by project version

### 📋 topology_data.json (Parent)
**Location**: `/home/bhavesh/Documents/Automation/`  
**Purpose**: Additional topology data example  
**Contents**: Sample network topology for testing  
**Status**: Reference data

### 📁 Reference/
**Location**: `/home/bhavesh/Documents/Automation/Reference/`  
**Purpose**: Archive directory for project references  
**Contents**: `__init__.py` (makes it a Python package)  
**Status**: Empty reference package

---

## 🤖 AI Prompt Files

### 📝 generate_from_json.md
**Purpose**: Copilot prompt for diagram generation from JSON  
**Contents**: Step-by-step instructions for AI to generate `generate_diagram.py`  
**Usage**: Copy-paste into GitHub Copilot for code generation

### 📝 live_device_pull.md
**Purpose**: Copilot prompt for live network device data collection  
**Contents**: Instructions for generating `live_puller.py`  
**Usage**: AI-assisted development of network discovery scripts

### 📝 export_formats.md
**Purpose**: Copilot prompt for diagram export functionality  
**Contents**: Instructions for PNG/SVG/PDF export features  
**Usage**: Adding export capabilities to the project

### 📝 github_upload.md
**Purpose**: Copilot prompt for GitHub integration  
**Contents**: Instructions for generating `github_uploader.py`  
**Usage**: AI-assisted GitHub automation development

---

## 📁 Generated Output Files

### 🎨 output_diagrams/
**Purpose**: Directory for generated diagram files  
**Contents**: Timestamped `.drawio` files and exported formats  
**Naming**: `network_diagram_YYYYMMDD_HHMMSS.drawio`  
**Git Status**: Excluded from version control

**Example File**: `network_diagram_20260315_191805.drawio`
- Generated Draw.io diagram file
- Contains XML representation of network topology
- Editable in VS Code Draw.io extension

---

## 🔄 File Dependencies & Relationships

### Core Workflow
```
live_puller.py → topology_data.json → generate_diagram.py → .drawio files
                              ↓
                       scheduler.py (automation)
                              ↓
                    github_uploader.py (publishing)
```

### Configuration Flow
```
config.py → All Python scripts
INSTRUCTIONS.md → AI code generation
requirements.txt → pip install
```

### Layout Engine Selection
```
generate_diagram.py → layout_engine.py (preferred)
                     ↓
                  grid_layout.py (fallback)
```

---

## 📊 File Statistics

- **Total Files**: 32 (including parent directory)
- **Python Scripts**: 7 core + 2 layout + 1 scheduler + 1 uploader = 11
- **Documentation**: 6 Markdown files
- **Configuration**: 4 files (.env, settings, gitignore, requirements)
- **Data Files**: 4 JSON + 2 text files
- **Generated Content**: 1 output directory

---

## 🚨 Security Considerations

### Sensitive Files (Never Commit)
- `credentials.txt` - SSH authentication credentials
- `.env` - Environment variables with tokens
- `output_diagrams/` - May contain sensitive network information

### Safe Files (Can Be Committed)
- All `.example` and template files
- Documentation and instructions
- Core Python scripts (no hardcoded credentials)
- Schema and configuration templates

---

## 🔄 Version Control Status

### Tracked Files
- Source code and documentation
- Configuration templates
- Schema definitions
- Build requirements

### Ignored Files
- Runtime credentials and secrets
- Generated diagram outputs
- Python cache files
- Virtual environment
- Local development artifacts

---

**This manifest provides complete visibility into the Network Automation project structure, ensuring developers, users, and AI assistants understand every component's role and relationship within the system.**</content>
<parameter name="filePath">/home/bhavesh/Documents/Automation/Automation-of-Network/FILE_MANIFEST.md