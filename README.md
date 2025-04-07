# 📦 Retro Game Package Manager   

🚀 A **fast and lightweight** package manager for downloading and managing retro game ROMs from public archives. Featuring **smart search, filtering by system, resumable downloads, and automatic extraction** for compressed files. Perfect for quickly downloading ROMs for retro gaming consoles with minimal effort!

---

## 🔥 Why Use This?  
- **Ultra-fast Fetching** – Instantly retrieve thousands of games.
- **Smart Filtering & Search** – Easily filter by system and search by keywords (with exclusion support).
- **Resumable Downloads** – Download large files without starting over.
- **Auto-Extract Archives** – No need for manual extraction; archives are unpacked automatically.
- **File Conversion** – Convert between formats (e.g., CHD to ISO, ISO to CHD, etc.) with a built-in converter.
- **Duplicate & Prototype Cleaning** – Remove duplicate region packages and prototype/beta files effortlessly.
- **Minimal Dependencies** – Runs smoothly on any system.
- **Clean & Minimalist UI** – Inspired by the classic Pacman package manager style.

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
### 1. Install dependencies  
Make sure you have Python **3.7+** installed, then run:  
```bash
pip install requests tqdm beautifulSoup4 py7zr rarfile
```
For Linux users, install `unrar` if not available:  
```bash
sudo apt install unrar
```

### 2. Clone this repository  
```bash
git clone https://github.com/xrce/retro.git
cd retro
```

---

## ⚡ Usage

### 1. Launching the Application

Start the Retro Game Package Manager by running the following command:

```bash
python retro.py
```

### 2. Main Menu Options

Upon launching, you will see a menu with several options:

- **Install Packages:**  
  Fetch available ROM packages, perform searches, and install selected ROMs.

- **Clean Packages:**  
  Remove unwanted files by cleaning duplicate region packages and prototype/beta versions.

- **Convert Files:**  
  Convert file formats (e.g., CHD to ISO, ISO to CHD, etc.). Hidden folders are automatically excluded during folder selection.

- **Exit:**  
  Quit the application.

### 3. Searching and Installing ROMs

When you select **Install Packages**, you will be prompted to enter search terms. You can refine your search using the following methods:

- **Search by Name:**  
  Simply type a keyword (e.g., `silent hill`) to search for games.

- **Filter by System:**  
  Include a system code to restrict the search to a specific console (e.g., `gbc silent hill` or `silent hill gbc`).

- **Exclude Keywords:**  
  Prefix a word with a hyphen to exclude files containing that term (e.g., `silent hill -demo`).

- **Install All Packages by System:**  
  Simply type `all` followed by system (e.g., `all gbc`) to install all packages from specific console.

After the search, matching packages are listed with details such as game name, size, and system code. If packages are found, you will be prompted to confirm the installation:

```
Listing packages...
:: Silent Hill 2 (PS2) [3.6GB] (ps2)
:: Silent Hill Origins (PSP) [1.2GB] (psp)

2 packages selected (4.8GB)
Install? [Y/n]: 
```

Type `Y` (or simply press Enter) to start the installation. The application will then display a progress bar for each package as it downloads and extracts the ROM files.

### 4. Converting Files

If you choose **Convert Files** from the main menu, you will enter the conversion menu where you can:

1. **Select a Conversion Mode:**  
   Choose the desired mode (e.g., CHD to ISO, ISO to CHD, etc.).

2. **Select a Folder:**  
   Pick the folder containing the files to convert (hidden folders are automatically excluded).

3. **View Conversion Progress:**  
   The conversion process is shown with a progress bar for each file.

### 5. Cleaning Packages

The **Clean Packages** option combines cleaning for duplicate region packages and prototype/beta files to help you manage your ROM collection:

- **Purpose:**  
  This option scans for:
  - **Duplicate Region Packages:** Keeps the highest priority version (e.g., Europe over USA or Japan) and deletes the redundant copies.
  - **Prototype/Beta Versions:** Removes files labeled as prototype, beta, or unlabeled, which are often incomplete or test versions.

- **Usage:**  
  Select **Clean Packages** from the main menu. The tool will scan your directories (excluding hidden folders), list all files targeted for cleaning along with their sizes, and prompt you to confirm deletion. Once confirmed, the selected files are removed with a progress display.

---

## 📂 ROM Storage Structure

- ROMs are stored in folders named after their **system codes** (e.g., `psx`, `gbc`, `nds`).
- Archives are **automatically extracted** into their respective folders.

Example directory structure:

```
roms/
 ┣ ps2/
 ┃ ┗ Silent Hill 2/
 ┣ psp/
 ┃ ┗ Silent Hill Origins/
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
