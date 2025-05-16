# 📦 Retro Game Package Manager   

🚀 A **fast and lightweight** package manager for downloading and managing retro game ROMs from public archives. Featuring **smart search, filtering by system, resumable downloads, and automatic extraction** for compressed files. Perfect for quickly downloading ROMs for retro gaming consoles with minimal effort!

---

## 🔥 Why Use This?  
⚡ **Ultra-fast fetching** – Instantly fetch **thousands** of games.  
🎯 **Easy Filtering** – Find exactly what you want, **instantly**.  
📂 **Auto-Extract Archives** – **No manual extraction needed**.  
🔄 **Auto-compress** – Convert ISO/CUE/GDI files to CHD format.  
🧹 **Smart Cleanup** – Intelligently remove duplicate ROMs.  
🚀 **Minimal Dependencies** – Runs smoothly on **any system**.  
🛠 **Minimalist UI** – Inspired by **Pacman package manager** style.  

---

## **🎮 Supported Consoles**  
This tool can fetch ROMs for multiple **retro and modern gaming systems**, including:  

- **Nintendo**: GB, GBC, GBA, NES, SNES, N64, NDS, 3DS, GameCube, Wii, Wii U  
- **Sony**: PSX, PS2, PSP, PS3, PS Vita  
- **Microsoft**: Xbox, Xbox 360  
- **Sega**: Genesis, Dreamcast, Saturn  
- **Others**: Atari 2600, Neo Geo, TurboGrafx-16, PC-98, FM-Towns, 3DO  

---

## **🛠 Installation**  
### **1️⃣ Install dependencies**  
Make sure you have Python **3.7+** installed, then run:  
```bash
pip install requests tqdm bs4 py7zr rarfile
```
For Linux users, install `unrar` if not available:  
```bash
sudo apt install unrar
```

For CHD compression/extraction, install `chdman`:
```bash
# Ubuntu/Debian
sudo apt install mame-tools

# macOS
brew install mame-tools
```

### **2️⃣ Clone this repository**  
```bash
git clone https://github.com/xrce/retro.git
cd retro
```

---

## **⚡ Usage**  
### **1️⃣ Launch the application**  
```bash
python retro.py
```

You'll see the main menu:
```
▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▖  ▗▄▖ 
▐▌ ▐▌▐▌     █  ▐▌ ▐▌▐▌ ▐▌  ✓ 0/1234 games
▐▛▀▚▖▐▛▀▀▘  █  ▐▛▀▚▖▐▌ ▐▌  ✓ 0/23 systems
▐▌ ▐▌▐▙▄▄▖  █  ▐▌ ▐▌▝▚▄▞▘  ✓ 0.00B/1.23TB total
--------------------------------------------------
[1] Update packages
[2] Install packages
[3] Uninstall packages
[4] List Installed
[5] Compress packages
[6] Clean duplicates
[0] Exit
--------------------------------------------------
```

### **2️⃣ Update package listings**  
Select option `1` to fetch available ROM packages.

### **3️⃣ Search and install packages**  
Select option `2` to search and install ROMs.

#### 🔍 Search syntax:  
```
Keywords: silent hill psx
```

- Search by name: `silent hill`
- Search within a specific console: `gbc silent hill`
- Exclude words from search: `silent hill -demo`
- Install all ROMs for a system: `all gbc`

### **4️⃣ Uninstall packages**  
Select option `3` to remove installed ROMs.
Uses the same search syntax as installation.

### **5️⃣ List installed packages**  
Select option `4` to view all currently installed ROMs.

### **6️⃣ Compress packages**  
Select option `5` to convert ISO/CUE/GDI files to CHD format.
This helps save disk space while preserving full compatibility.

### **7️⃣ Clean duplicates**  
Select option `6` to scan for and remove duplicate ROMs.
The system prioritizes ROMs in this order: World (W), Europe (E), USA (U), Japan (J).

---

## **📂 Where Are ROMs Saved?**  
- ROMs are stored in folders matching their **system codes** (e.g., `psx`, `gbc`, `nds`).  
- Archives are **automatically extracted** into their respective folders.  

Example directory structure:  
```
📂 roms/
 ┣ 📂 gbc/
 ┃ ┗ 📂 Silent Hill GBC/
 ┣ 📂 ps2/
 ┃ ┗ 📂 Silent Hill 2/
 ┣ 📂 psp/
 ┃ ┗ 📂 Silent Hill Origins/
```

---

## **🎯 Example Output**  
```
Keywords: silent hill psx

Listing packages...
✗ 697.62MB Silent Hill (USA) (psx)
✗ 573.47MB Silent Hill (Europe) (psx)
✗ 565.12MB Silent Hill (Japan) (psx)

3 packages to install (1.80GB)
Install? [Y/n]: y

Installing: 33% [1/3]
Silent Hill (USA): 100% [697.62MB/697.62MB]
Silent Hill (Europe): 100% [573.47MB/573.47MB]
Silent Hill (Japan): 100% [565.12MB/565.12MB]

Installation complete.
```

---

## 🔧 Configuration  
Edit `systems.json` to add or remove supported systems. Example:

```json
{
    "psx": {
        "name": "Sony PlayStation",
        "format": ["bin", "cue", "chd"],
        "url": [
            "https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation/"
        ]
    }
}
```

---

## 📌 Notes  

- **Some ROMs are large!** Ensure you have enough storage space.  
- **Roms are fetched from external archives.** No ROMs are included in this repository.  
- **Use this responsibly!** Only download games you legally own.

🎮 **Happy gaming!** 🕹
