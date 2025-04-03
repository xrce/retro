# 📦 Retro Game Package Manager   

🚀 A **fast and lightweight** package manager for downloading and managing retro game ROMs from public archives. Featuring **smart search, filtering by system, resumable downloads, and automatic extraction** for compressed files. Perfect for quickly downloading ROMs for retro gaming consoles with minimal effort!

---

## 🔥 Why Use This?  
⚡ **Ultra-fast fetching** – Instantly fetch **thousands** of games.  
🎯 **Easy Filtering** – Find exactly what you want, **instantly**.  
📂 **Auto-Extract Archives** – **No manual extraction needed**.  
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

### **2️⃣ Clone this repository**  
```bash
git clone https://github.com/xrce/retro.git
cd retro
```

---

## **⚡ Usage**  
### **1️⃣ Fetch available ROM packages**  
```bash
python retro.py
```

### **2️⃣ Search for a game**  
#### 🔍 Search by name  
```bash
silent hill
```
#### 🎮 Search within a specific console  
```bash
gbc silent hill
```
or  
```bash
silent hill gbc
```
*(Only searches for "silent hill" in Game Boy Color ROMs)*  

#### 🚫 Exclude words from search  
```bash
silent hill -demo
```
*(Excludes files containing "demo")*  

### **3️⃣ Install selected ROMs**  
If prompted, type `Y` to install selected packages:  
```bash
:: Silent Hill 2 (PS2) [3.6GB] (ps2)
:: Silent Hill Origins (PSP) [1.2GB] (psp)
2 packages selected (4.8GB)

Install? [Y/n]:
```

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
Fetching package lists... 
:: Get: https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Game%20Boy%20Color/ gbc (11253) [960.98MB]
:: Get: https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%202/ ps2 (2890) [15.95TB]
:: Get: https://myrient.erista.me/files/Redump/Sony%20-%20PlayStation%20Portable/ psp (1350) [1.71TB]

Listing packages...
:: Silent Hill 2 (PS2) [3.6GB] (ps2)
:: Silent Hill Origins (PSP) [1.2GB] (psp)
2 packages selected (4.8GB)

Install? [Y/n]: y

:: 1/2  [##########          ]  1.2GB  Silent Hill Origins (psp)
:: 2/2  [####################]  3.6GB  Silent Hill 2 (ps2)

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
