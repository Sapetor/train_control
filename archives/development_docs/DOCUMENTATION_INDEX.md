# Documentation Index

## Main Documentation Files

### 📚 [`COMPLETE_DOCUMENTATION.md`](COMPLETE_DOCUMENTATION.md)
**Comprehensive Project Documentation** (Created: Oct 28, 2025)
- Complete system overview and architecture
- Quick start guide and installation
- All recent improvements and fixes
- ESP32 firmware documentation
- Experiment modes (PID & Step Response)
- Network configuration and MQTT protocol
- Testing procedures and troubleshooting
- Development guidelines

### 📖 [`README_platform.md`](README_platform.md) 
**Quick Start README**
- Basic project overview
- Installation instructions
- Quick start guide
- Basic troubleshooting

### 💻 [`CLAUDE.md`](CLAUDE.md)
**Coding Guidelines for Developers**
- Project-specific coding conventions
- Architecture guidelines
- Code style and formatting rules
- Testing requirements
- Git workflow recommendations

## Other Project Files

### Python Application
- `train_control_platform.py` - Main application (2700+ lines)
- `train_control_platform_backup.py` - Previous version backup
- `test_improvements.py` - Test suite for verification
- `requirements.txt` - Python dependencies

### ESP32 Firmware
- `tren_esp_unified/` - Unified firmware supporting both modes
  - `tren_esp_unified.ino` - Main firmware with race condition fixes
  - `actuadores.ino` - Motor control
  - `sensores.ino` - Sensor functions
  - `README_UNIFIED.md` - Firmware documentation
  - `FIXES_APPLIED.txt` - Fix history

### Configuration
- `network_config.json` - Saved network and language settings
- `.gitignore` - Git ignore rules

### Data Files
- `experiment_*.csv` - PID control experiment data
- `step_response_*.csv` - Step response experiment data

---

## Where to Start?

1. **New Users**: Start with [`README_platform.md`](README_platform.md)
2. **Full Documentation**: Read [`COMPLETE_DOCUMENTATION.md`](COMPLETE_DOCUMENTATION.md)
3. **Developers**: Review [`CLAUDE.md`](CLAUDE.md) for coding guidelines
4. **ESP32 Setup**: Check `tren_esp_unified/README_UNIFIED.md`

---

*Last updated: October 28, 2025*
