# Retro Game Package Manager

A command-line tool designed specifically to download and manage ROMs from public archives, with features like smart searching, filtering, and automatic extraction of compressed files.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Advanced Usage](#advanced-usage)
- [Configuration](#configuration)
- [Supported Platforms](#supported-platforms)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## Overview

Retro Game Package Manager is a tool that simplifies the management of retro game collections. It features intelligent search algorithms, multi-threaded downloads, automatic archive extraction, and advanced duplicate management capabilities.

### Key Features

- **High-Performance Downloads**: Multi-threaded architecture with configurable worker pools
- **Intelligent Search**: Advanced filtering with system-specific queries and exclusion patterns
- **Archive Management**: Automatic extraction for ZIP, 7Z, TAR.XZ, and RAR formats
- **Space Optimization**: CHD compression support for significant storage savings
- **Duplicate Resolution**: Smart duplicate detection with region-based prioritization
- **Cross-Platform**: Native support for Windows, macOS, and Linux
- **Configuration Management**: Centralized settings with JSON-based configuration

## Installation

### Dependency Installation

Install core Python dependencies:

```bash
pip install requests tqdm beautifulsoup4 py7zr rarfile
```

### Optional Components

#### CHD Compression Support

For advanced compression capabilities, install MAME tools:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mame-tools
```

**macOS (Homebrew):**
```bash
brew install rom-tools
```

**Windows:**
Download MAME tools from the [official Recalbox website](https://wiki.recalbox.com/en/tutorials/utilities/rom-conversion/chdman)

#### Archive Extraction Tools

**Ubuntu/Debian:**
```bash
sudo apt install unrar-free p7zip-full
```

**macOS:**
```bash
brew install unrar p7zip
```

### Package Installation

```bash
pip install .
```

Verify installation:
```bash
retro --version
```

## Quick Start

### Initial Setup

1. **Initialize Configuration**
   ```bash
   retro update
   ```

2. **Search Available Games**
   ```bash
   retro search mario
   ```

3. **Install Games**
   ```bash
   retro install sonic genesis
   ```

4. **Manage Your Collection**
   ```bash
   retro list
   ```

## Command Reference

### Core Commands

#### `retro update`
Synchronizes the local game database with remote repositories.

**Usage:**
```bash
retro update
```

**Process:**
- Fetches system definitions from configured repositories
- Downloads and parses directory listings
- Updates local package cache
- Displays system statistics

**Output:**
```
Listing systems...
✓ 208.08GB [Panasonic 3DO] (666)
✓ 3.30GB [Commodore Amiga] (3169)
✓ 1.2TB [PlayStation] (8,234)
✗ 0.00B [Atari 2600] (0)
```

#### `retro install <terms>`
Installs games matching specified search criteria.

**Usage:**
```bash
retro install <search_terms>
```

**Search Patterns:**
- **Name-based**: `retro install mario`
- **System-specific**: `retro install mario nes`
- **Bulk installation**: `retro install all gbc`
- **Exclusion filtering**: `retro install mario -demo -beta`

**Interactive Process:**
```
[genesis] 145.75MB (71)
  (1.00MB) Sonic The Hedgehog (USA, Europe)
  (2.00MB) Sonic The Hedgehog 2 (World)
  (4.00MB) Sonic 3D Blast (USA, Europe, Korea) (En)

Total: 145.75MB (71 packages)
Do you want to continue? [Y/n]: y

Installing: ⋯18 ↓4 ⚙2 ✓27 ✗0: 75%
✓ 27 installed, ✗ 0 failed
```

#### `retro remove <terms>`
Removes installed games matching specified criteria.

**Usage:**
```bash
retro remove <search_terms>
```

**Examples:**
```bash
retro remove mario           # Remove all Mario games
retro remove all psx         # Remove all PlayStation games
retro remove sonic -beta     # Remove Sonic games, keep betas
```

#### `retro list`
Displays comprehensive information about installed games.

**Usage:**
```bash
retro list
```

**Output Format:**
```
[genesis] 70.00MB (33)
  (1.00MB) Aerobiz Supersonic (USA).md
  (2.00MB) Sonic & Knuckles (World).md
  (512.00KB) Sonic The Hedgehog (USA, Europe).md

[psx] 627.79MB (3)
  (266.21MB) Rampage - Through Time (Europe) (En,Fr,De).chd
  (136.74MB) Rampage - World Tour (Europe).chd

74 games from 2 systems, 773.54MB used.
```

#### `retro search <terms>`
Searches available games without installation.

**Usage:**
```bash
retro search <search_terms>
```

**Advanced Search:**
```bash
retro search zelda           # Basic name search
retro search zelda nes        # System-specific search
retro search all snes         # Complete system listing
retro search mario -demo      # Exclusion-based search
```

**Output with Installation Status:**
```
[genesis] 145.75MB (71) (5 installed)
  (1.00MB) Sonic The Hedgehog (USA, Europe)
  (2.00MB) Sonic The Hedgehog 2 (World) [installed]
  (4.00MB) Sonic 3D Blast (USA, Europe, Korea) (En)
```

### Utility Commands

#### `retro compress`
Converts ROM files to CHD format for space optimization.

**Usage:**
```bash
retro compress
```

**Compression Process:**
```
The following files will be compressed:
  [psx] (266.21MB) Rampage - Through Time (Europe) (En,Fr,De).iso
    → Create: Rampage - Through Time (Europe) (En,Fr,De).chd
    → Delete: Rampage - Time (Europe) (En,Fr,De).iso
    → Delete: Rampage - Time (Europe) (En,Fr,De).bin

Do you want to continue? [Y/n]: y

Compressing: ⋯0 ⚙1 ✓0 ✗0: 100%
✓ 1 compressed, ✗ 0 failed
```

#### `retro autoremove`
Intelligently removes duplicate ROMs based on quality metrics.

**Usage:**
```bash
retro autoremove
```

**Duplicate Resolution:**
```
The following duplicate games will be processed:
Sonic The Hedgehog:
  [genesis] (512.00KB) Sonic The Hedgehog (USA, Europe).md
    → Keep: Best version
  [genesis] (512.00KB) Sonic The Hedgehog (Japan).md
    → Delete: Duplicate

Do you want to continue? [Y/n]: y
✓ 1 duplicates removed
```

## Advanced Usage

### Search Syntax

#### Basic Patterns
- **Exact match**: `retro search "Super Mario Bros"`
- **Partial match**: `retro search mario`
- **System filter**: `retro search mario nes`
- **Complete system**: `retro search all snes`

#### Exclusion Patterns
- **Single exclusion**: `retro search mario -demo`
- **Multiple exclusions**: `retro search sonic -beta -prototype -hack`
- **Complex filtering**: `retro search zelda nes -demo -beta`

#### Region Preferences
The autoremove command prioritizes ROMs in this order:
1. **World (W)** - International releases
2. **Europe (E)** - European releases
3. **USA (U)** - North American releases
4. **Japan (J)** - Japanese releases

### Performance Tuning

#### Worker Configuration
Adjust worker counts in `~/.config/retro/settings.json`:

```json
{
  "fetch_workers": 15,      # Increase for faster updates
  "install_workers": 30,     # Increase for faster downloads
  "convert_workers": 8,      # Increase for faster CHD conversion
  "compress_workers": 8      # Increase for faster compression
}
```

#### Network Optimization
- Use wired connections for large downloads
- Configure proxy settings if needed
- Monitor bandwidth usage during bulk operations

## Configuration

### Settings Management

Configuration is stored in `~/.config/retro/settings.json`:

```json
{
  "roms_dir": "~/roms",
  "fetch_workers": 10,
  "install_workers": 20,
  "convert_workers": 4,
  "compress_workers": 4
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `roms_dir` | string | `~/roms` | Primary ROM storage directory |
| `fetch_workers` | integer | 10 | Concurrent threads for repository fetching |
| `install_workers` | integer | 20 | Concurrent threads for game downloads |
| `convert_workers` | integer | 4 | Concurrent threads for CHD conversion |
| `compress_workers` | integer | 4 | Concurrent threads for compression |
| `preferred_regions` | array | `["W","E","U","J"]` | Region priority for duplicate resolution |
| `auto_extract` | boolean | true | Automatically extract archives |
| `verify_downloads` | boolean | true | Verify download integrity |

### System Definitions

System configurations are stored in `~/.config/retro/systems.json`:

```json
{
  "genesis": {
    "name": "Sega Genesis",
    "format": ["md", "smd", "bin"],
    "url": [
      "https://archive.org/download/redump-sega-genesis-mega-drive/"
    ]
  },
  "psx": {
    "name": "Sony PlayStation",
    "format": ["bin", "cue", "chd"],
    "url": [
      "https://archive.org/download/redump-sony-playstation/"
    ]
  }
}
```

### Directory Structure

```
~/.config/retro/
├── systems.json      # System definitions and repository URLs
├── packages.json     # Cached game database
└── settings.json     # User preferences and configuration

~/roms/               # Primary ROM storage (configurable)
├── genesis/          # Sega Genesis games
├── psx/              # PlayStation games
├── nes/              # Nintendo Entertainment System games
├── snes/             # Super Nintendo games
└── ...               # Additional system directories
```

## Supported Platforms

### Nintendo Systems

| System | Code | Formats | Description |
|--------|------|---------|-------------|
| Game Boy | GB | .gb | Original Game Boy games |
| Game Boy Color | GBC | .gbc | Game Boy Color games |
| Game Boy Advance | GBA | .gba | Game Boy Advance games |
| Nintendo Entertainment System | NES | .nes | NES games |
| Super Nintendo | SNES | .smc, .sfc | SNES games |
| Nintendo 64 | N64 | .n64, .z64 | Nintendo 64 games |
| Nintendo DS | NDS | .nds | Nintendo DS games |
| Nintendo 3DS | 3DS | .3ds, .cia | Nintendo 3DS games |
| GameCube | GC | .gcm, .iso | GameCube games |
| Wii | WII | .wbfs, .iso | Wii games |
| Wii U | WIIU | .wud, .wux | Wii U games |

### Sony Systems

| System | Code | Formats | Description |
|--------|------|---------|-------------|
| PlayStation | PSX | .bin, .cue, .chd | Original PlayStation games |
| PlayStation 2 | PS2 | .iso, .chd | PlayStation 2 games |
| PlayStation Portable | PSP | .iso, .cso | PSP games |
| PlayStation 3 | PS3 | .pkg, .iso | PlayStation 3 games |
| PlayStation Vita | PSV | .vpk, .mai | PlayStation Vita games |

### Microsoft Systems

| System | Code | Formats | Description |
|--------|------|---------|-------------|
| Xbox | XB | .iso, .xbe | Original Xbox games |
| Xbox 360 | X360 | .iso, .xex | Xbox 360 games |

### Sega Systems

| System | Code | Formats | Description |
|--------|------|---------|-------------|
| Genesis | GEN | .md, .smd, .bin | Sega Genesis/Mega Drive games |
| Dreamcast | DC | .gdi, .cdi, .chd | Sega Dreamcast games |
| Saturn | SAT | .bin, .cue, .chd | Sega Saturn games |

### Other Systems

| System | Code | Formats | Description |
|--------|------|---------|-------------|
| Atari 2600 | A26 | .a26, .bin | Atari 2600 games |
| Neo Geo | NG | .ngp, .ngc | Neo Geo games |
| TurboGrafx-16 | TG16 | .pce, .cue | TurboGrafx-16 games |
| PC-98 | PC98 | .hdi, .fdi | PC-98 games |
| FM Towns | FMT | .hdi, .fdi | FM Towns games |
| 3DO | 3DO | .iso, .chd | 3DO games |

## Performance Optimization

### Download Optimization

**Network Settings:**
- Use wired connections for stability
- Configure appropriate worker counts based on bandwidth
- Monitor system resources during bulk operations

**Storage Optimization:**
- Use CHD compression for disc-based games
- Implement regular duplicate cleanup
- Consider SSD storage for frequently accessed games

### System Resource Management

**Memory Usage:**
- Monitor RAM usage during large downloads
- Adjust worker counts based on available memory
- Close unnecessary applications during bulk operations

**CPU Utilization:**
- Balance worker counts with CPU cores
- Use compression during off-peak hours
- Monitor system temperature during intensive operations

## Troubleshooting

### Common Issues

#### Installation Problems

**"No package data found" error:**
```bash
retro update
```

**Permission denied errors:**
```bash
# Ensure write permissions to ROMs directory
chmod 755 ~/roms
# Ensure write permissions to config directory
chmod 755 ~/.config/retro
```

**"chdman not found" error:**
Install MAME tools as described in the Installation section.

#### Download Issues

**Network timeouts:**
- Check internet connection stability
- Reduce worker counts in settings.json
- Verify repository accessibility

**Incomplete downloads:**
- Enable download verification in settings
- Check available disk space
- Verify write permissions

#### Performance Issues

**Slow downloads:**
- Increase `install_workers` in settings.json
- Check network bandwidth limitations
- Verify repository server performance

**High CPU usage:**
- Decrease worker counts in settings.json
- Close resource-intensive applications
- Monitor system temperature

**Disk space issues:**
- Use `retro compress` for space optimization
- Remove unwanted games with `retro remove`
- Consider external storage solutions

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `E: No package data found` | Missing packages.json | Run `retro update` |
| `E: Could not load systems.json` | Missing or invalid systems.json | Check file exists and is valid JSON |
| `E: No search term specified` | Missing search terms | Provide search terms after command |
| `Error: chdman not found` | MAME tools not installed | Install MAME tools |
| `Permission denied` | Insufficient file permissions | Fix directory permissions |
| `Network timeout` | Connection issues | Check internet connection |

## Legal Notice

This tool is designed to help manage ROMs for games you legally own. Please ensure you only download games that you have purchased or that are in the public domain. The developers of this tool do not condone piracy and are not responsible for any illegal use of this software.

**Important**: Always respect copyright laws and only download games you legally own. This tool is provided for educational and preservation purposes only.
