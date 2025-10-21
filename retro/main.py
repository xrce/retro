import os, re, json, shutil, subprocess, requests, zipfile, tarfile, py7zr, rarfile
from glob import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_config_dir():  # Get configuration directory path
    config_dir = os.path.expanduser("~/.config/retro")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def load_settings():  # Load settings from config file
    config_dir = get_config_dir()
    settings_file = os.path.join(config_dir, "settings.json")
    default_settings = {
        "roms_dir": os.path.expanduser("~/roms"),
        "fetch_workers": 10,
        "install_workers": 20,
        "convert_workers": 4,
        "compress_workers": 4
    }
    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        return {**default_settings, **settings}
    except:
        with open(settings_file, 'w') as f:
            json.dump(default_settings, f, indent=2)
        return default_settings

def parse_size(s):  # Convert size string to bytes
    s = s.replace("i", "").strip()
    if len(s) >= 2 and s[-1].upper() == 'B' and s[-2].upper() in 'KMG': s = s[:-1]
    if not s: return 0
    try: n = float(s[:-1])
    except: return 0
    return int(n*1024**{'K':1,'M':2,'G':3,'T':4}.get(s[-1].upper(),0)) if s[-1].upper() in "KMGT" else int(n)

def format_size(n):  # Convert bytes to human readable format
    for u in ('B','KB','MB','GB','TB'):
        if n < 1024: return f"{n:.2f}{u}"
        n /= 1024
    return f"{n:.2f}PB"

def download_file(url, path):  # Download file with resume support
    path = os.path.normpath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pos = os.path.getsize(path) if os.path.exists(path) else 0
    total = int(requests.head(url).headers.get('content-length', 0))
    headers = {'Range': f'bytes={pos}-'} if pos < total else {}
    with requests.get(url, headers=headers, stream=True) as r, open(path, 'ab' if pos else 'wb') as f:
        for c in r.iter_content(8192):
            if c: f.write(c)
    if os.path.getsize(path) < total: raise Exception(f"Incomplete download: {path}")

def extract_archive(fp, dst, ext):  # Extract various archive formats
    fp, dst = os.path.normpath(fp), os.path.normpath(dst)
    os.makedirs(dst, exist_ok=True)
    extractors = {"zip": lambda: zipfile.ZipFile(fp).extractall(dst), "tar.xz": lambda: tarfile.open(fp, "r:xz").extractall(dst), "7z": lambda: py7zr.SevenZipFile(fp, mode="r").extractall(dst), "rar": lambda: rarfile.RarFile(fp).extractall(dst)}
    if ext not in extractors: raise Exception(f"Unsupported archive: {ext}")
    extractors[ext]()

def get_directory_listing(url):  # Parse directory listing from web page
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    t = soup.find(lambda tag: tag.name == "table" and ("directory-listing-table" in tag.get("class", []) or tag.get("id") == "list"))
    if not t: return []
    h = [th.text.strip().lower() for th in t.find_all("th")]
    name_idx, size_idx = h.index("name") if "name" in h else 0, h.index("size") if "size" in h else None
    out, tbody = [], t.find("tbody")
    if not tbody: return out
    for tr in tbody.find_all("tr"):
        td = tr.find_all("td")
        if not td: continue
        a = td[name_idx].find("a")
        if not a: continue
        if "parent directory" in a.text.lower(): continue
        name, link = a.text.strip(), a["href"]
        sz = td[size_idx].text.strip() if size_idx is not None and size_idx < len(td) else ((tr.find("td", class_="size") or (td[2] if len(td)>2 else None)))
        sz = sz.text.strip() if hasattr(sz, "text") else (sz or "")
        out.append({"name":name, "link":link, "size_str":sz, "size_bytes":parse_size(sz), "base":url})
    return out

class Manager:  # Main package manager class
    def __init__(self, cfg=None): 
        self.config_dir = get_config_dir()
        self.cfg = cfg or os.path.join(self.config_dir, "systems.json")
        self.settings = load_settings()
        self.systems, self.files = {}, []

    def load(self):  # Load systems configuration
        try: self.systems = json.load(open(self.cfg)); return True
        except: return False

    def fetch_system(self, sys_name):  # Fetch games for specific system
        out, fmt = [], [e.lower() for e in self.systems[sys_name].get("format", [])]
        for url in self.systems[sys_name].get("url", []):
            lst = [f for f in get_directory_listing(url) if any(f["name"].lower().endswith("." + e) for e in fmt) or f["name"].lower().endswith((".zip", ".7z", ".tar.xz", ".rar"))]
            for f in lst: f["system"] = sys_name
            out.extend(lst)
        return out

    def fetch(self):  # Fetch all systems with progress bar
        if not self.load(): return
        stats = {"pending": len(self.systems), "fetching": 0, "done": 0, "failed": 0}
        stats_lock = __import__('threading').Lock()
        
        def fetch_with_stats(sys_name):
            with stats_lock: stats["pending"] -= 1; stats["fetching"] += 1
            try: result = self.fetch_system(sys_name)
            except: result = []
            with stats_lock: stats["fetching"] -= 1; stats["done"] += 1 if result else 0; stats["failed"] += 1 if not result else 0
            return result
        
        with ThreadPoolExecutor(max_workers=self.settings["fetch_workers"]) as exe:
            futures = {exe.submit(fetch_with_stats, sys_name): sys_name for sys_name in self.systems}
            self.files = []
            with tqdm(total=100, desc="Fetching", bar_format='{desc}: {percentage:3.0f}%', ncols=60, leave=False) as pbar:
                for fut in as_completed(futures):
                    self.files.extend(fut.result())
                    desc = f"\033[90m⋯{stats['pending']}\033[0m \033[36m↓{stats['fetching']}\033[0m \033[92m✓{stats['done']}\033[0m \033[91m✗{stats['failed']}\033[0m"
                    pbar.set_description(desc)
                    progress = int(((stats['done'] + stats['failed']) / len(self.systems)) * 100)
                    pbar.n = progress; pbar.refresh()
        
        json.dump(self.files, open(os.path.join(self.config_dir, "packages.json"), "w"))

    def update(self):  # Update package lists and show systems
        self.fetch()
        print("\033[1mListing systems...\033[0m")
        for sys_name in sorted(self.systems.keys()):
            sys_files = [f for f in self.files if f["system"] == sys_name]
            total_size = sum(f.get("size_bytes", 0) for f in sys_files)
            count = len(sys_files)
            size_str = format_size(total_size)
            system_colored = f"\033[36m[{sys_name}]\033[0m"
            if count > 0:
                print(f"\033[92m✓ {size_str} {system_colored} ({count})\033[0m")
            else:
                print(f"\033[91m✗ {size_str} {system_colored} ({count})\033[0m")

    def search(self, query_terms):  # Search available games
        inc = [t.lower() for t in query_terms if t.lower() in [s.lower() for s in self.systems.keys()]]
        kw = [t for t in query_terms if t.lower() not in [s.lower() for s in self.systems.keys()] and not t.startswith('-')]
        exc = [t[1:] for t in query_terms if t.startswith('-')]
        
        if len(query_terms) == 2 and query_terms[0].lower() == "all" and query_terms[1].lower() in [s.lower() for s in self.systems.keys()]:
            results = [f for f in self.files if f["system"].lower() == query_terms[1].lower()]
        else: 
            results = [f for f in self.files if (not inc or f["system"].lower() in inc) and (not kw or all(k.lower() in f["name"].lower() for k in kw)) and (not exc or not any(e.lower() in f["name"].lower() for e in exc))]
        
        if not results: print("No packages found."); return
        
        by_system = {}
        for f in results:
            if f["system"] not in by_system: by_system[f["system"]] = []
            by_system[f["system"]].append(f)
        
        for sys_name in sorted(by_system.keys()):
            sys_files = by_system[sys_name]
            total_size = sum(f.get("size_bytes", 0) for f in sys_files)
            count = len(sys_files)
            installed = 0
            system_dir = os.path.join(self.settings["roms_dir"], sys_name)
            if os.path.exists(system_dir):
                for f in sys_files:
                    bn = os.path.splitext(f["name"])[0]
                    is_installed = any(os.path.splitext(x)[0] == bn for x in os.listdir(system_dir) if os.path.isfile(os.path.join(system_dir, x)))
                    if is_installed: installed += 1
            
            size_str = format_size(total_size)
            system_colored = f"\033[36m[{sys_name}]\033[0m"
            print(f"{system_colored} {size_str} ({count})" + (f" ({installed} installed)" if installed > 0 else ""))
            
            for f in sys_files:
                bn = os.path.splitext(f["name"])[0]
                is_installed = any(os.path.splitext(x)[0] == bn for x in os.listdir(system_dir) if os.path.exists(system_dir) and os.path.isfile(os.path.join(system_dir, x)))
                status = " \033[92m[installed]\033[0m" if is_installed else ""
                size_colored = f"\033[33m({format_size(f.get('size_bytes', 0))})\033[0m"
                print(f"  {size_colored} {f['name']}{status}")
            print()

    def search_for_install(self, terms=None):  # Search and prepare for installation
        if terms is None: terms = input("Keywords: ").split()
        inc = [t.lower() for t in terms if t.lower() in [s.lower() for s in self.systems.keys()]]
        kw = [t for t in terms if t.lower() not in [s.lower() for s in self.systems.keys()] and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]
        
        if len(terms) == 2 and terms[0].lower() == "all" and terms[1].lower() in [s.lower() for s in self.systems.keys()]:
            out = [p for p in self.files if p["system"].lower() == terms[1].lower()]
        else:
            out = []
            for p in self.files:
                system_match = not inc or p["system"].lower() in inc
                name_match = not kw or any(k.lower() in p["name"].lower() for k in kw)
                exclude_match = not exc or not any(e.lower() in p["name"].lower() for e in exc)
                if system_match and name_match and exclude_match: out.append(p)
        
        if not out: print("No packages found."); return None
        
        by_system = {}
        for f in out:
            if f["system"] not in by_system: by_system[f["system"]] = []
            by_system[f["system"]].append(f)
        
        for sys_name in sorted(by_system.keys()):
            sys_files = by_system[sys_name]
            total_size = sum(f.get("size_bytes", 0) for f in sys_files)
            count = len(sys_files)
            size_str = format_size(total_size)
            system_colored = f"\033[36m[{sys_name}]\033[0m"
            print(f"{system_colored} {size_str} ({count})")
            
            for f in sys_files:
                size_colored = f"\033[33m({format_size(f.get('size_bytes', 0))})\033[0m"
                print(f"  {size_colored} {f['name']}")
            print()
        
        total_size = sum(f.get("size_bytes", 0) for f in out)
        print(f"Total: {format_size(total_size)} ({len(out)} packages)")
        return out

    def install(self, pkgs):  # Install packages with progress bar
        from threading import Lock
        stats = {"pending": len(pkgs), "downloading": 0, "extracting": 0, "done": 0, "failed": 0}
        stats_lock = Lock()
        
        def worker(f):
            dest, tmp = os.path.join(self.settings["roms_dir"], f["system"]), os.path.join(self.settings["roms_dir"], f["system"], "tmp")
            os.makedirs(dest, exist_ok=True); os.makedirs(tmp, exist_ok=True)
            
            if os.path.exists(os.path.join(dest, f["name"])): 
                with stats_lock: stats["pending"] -= 1
                return ("skipped", f)
                
            bn = os.path.splitext(f["name"])[0]
            if any(os.path.splitext(x)[0] == bn for x in os.listdir(dest) if os.path.isfile(os.path.join(dest, x))): 
                with stats_lock: stats["pending"] -= 1
                return ("skipped", f)
            
            tmp_path = os.path.join(tmp, f["name"])
            url = f["base"].rstrip("/") + "/" + f["link"]
            try:
                with stats_lock: stats["pending"] -= 1; stats["downloading"] += 1
                download_file(url, tmp_path)
                with stats_lock: stats["downloading"] -= 1; stats["extracting"] += 1
                
                ext = "tar.xz" if f["name"].endswith(".tar.xz") else os.path.splitext(f["name"])[1].lstrip(".").lower()
                if ext in [e.lower() for e in self.systems[f["system"]].get("format", [])]:
                    shutil.move(tmp_path, os.path.join(dest, f["name"]))
                else: 
                    extract_archive(tmp_path, dest, ext); os.remove(tmp_path)
                
                with stats_lock: stats["extracting"] -= 1; stats["done"] += 1
                return ("done", f)
            except Exception as e: 
                with stats_lock: stats["downloading"] = max(0, stats["downloading"] - 1); stats["extracting"] = max(0, stats["extracting"] - 1); stats["failed"] += 1
                return ("error", f, str(e))
        
        with tqdm(total=100, desc="Installing", bar_format='{desc}: {percentage:3.0f}%', ncols=60, leave=False) as pbar:
            with ThreadPoolExecutor(max_workers=self.settings["install_workers"]) as exe:
                futures = {exe.submit(worker, pkg): pkg for pkg in pkgs}
                for fut in as_completed(futures): 
                    desc = f"\033[90m⋯{stats['pending']}\033[0m \033[33m↓{stats['downloading']}\033[0m \033[36m⚙{stats['extracting']}\033[0m \033[92m✓{stats['done']}\033[0m \033[91m✗{stats['failed']}\033[0m"
                    pbar.set_description(desc)
                    progress = int(((stats['done'] + stats['failed']) / len(pkgs)) * 100)
                    pbar.n = progress; pbar.refresh()
        
        for sys_name in set(pkg["system"] for pkg in pkgs):
            tmp_dir = os.path.join(self.settings["roms_dir"], sys_name, "tmp")
            if os.path.exists(tmp_dir) and not os.listdir(tmp_dir): shutil.rmtree(tmp_dir)
        
        print(f"\033[92m✓ {stats['done']}\033[0m installed, \033[91m✗ {stats['failed']}\033[0m failed")

    def list(self):  # List installed games by system
        try: self.systems = json.load(open(self.cfg))
        except Exception as e: print(f"E: Error loading systems.json: {e}"); return
        
        all_files = []
        for sys_name in self.systems:
            system_dir = os.path.join(self.settings["roms_dir"], sys_name)
            if not os.path.exists(system_dir): continue
            for file in os.listdir(system_dir):
                file_path = os.path.join(system_dir, file)
                if os.path.isfile(file_path) and not file.startswith('.'):
                    all_files.append({"name": file, "path": file_path, "system": sys_name})
        
        if not all_files: print("No games installed."); return
        
        by_system = {}
        for f in all_files:
            if f["system"] not in by_system: by_system[f["system"]] = []
            by_system[f["system"]].append(f)
        
        for sys_name in sorted(by_system.keys()):
            sys_files = by_system[sys_name]
            total_size = sum(os.path.getsize(f['path']) for f in sys_files)
            count = len(sys_files)
            size_str = format_size(total_size)
            system_colored = f"\033[36m[{sys_name}]\033[0m"
            print(f"{system_colored} {size_str} ({count})")
            
            for f in sys_files:
                size_colored = f"\033[33m({format_size(os.path.getsize(f['path']))})\033[0m"
                print(f"  {size_colored} {f['name']}")
            print()

    def uninstall(self, terms=None):  # Remove games with confirmation
        if terms is None: terms = input("Keywords: ").split()
        try: self.systems = json.load(open(self.cfg))
        except Exception as e: print(f"E: Error loading systems.json: {e}"); return
        
        all_files = []
        for sys_name in self.systems:
            system_dir = os.path.join(self.settings["roms_dir"], sys_name)
            if not os.path.exists(system_dir): continue
            for file in os.listdir(system_dir):
                file_path = os.path.join(system_dir, file)
                if os.path.isfile(file_path) and not file.startswith('.'):
                    all_files.append({"name": file, "path": file_path, "system": sys_name})
        
        if not all_files: print("No games installed."); return
        
        inc = [t.lower() for t in terms if t.lower() in [s.lower() for s in self.systems.keys()]]
        kw = [t for t in terms if t.lower() not in [s.lower() for s in self.systems.keys()] and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]
        
        if len(terms) == 2 and terms[0].lower() == "all" and terms[1].lower() in [s.lower() for s in self.systems.keys()]:
            out = [p for p in all_files if p["system"].lower() == terms[1].lower()]
        else:
            out = []
            for p in all_files:
                system_match = not inc or p["system"].lower() in inc
                name_match = not kw or any(k.lower() in p["name"].lower() for k in kw)
                exclude_match = not exc or not any(e.lower() in p["name"].lower() for e in exc)
                if system_match and name_match and exclude_match: out.append(p)
        
        if not out: print("No games found to remove."); return
        
        by_system = {}
        for f in out:
            if f["system"] not in by_system: by_system[f["system"]] = []
            by_system[f["system"]].append(f)
        
        for sys_name in sorted(by_system.keys()):
            sys_files = by_system[sys_name]
            total_size = sum(os.path.getsize(f['path']) for f in sys_files)
            count = len(sys_files)
            size_str = format_size(total_size)
            system_colored = f"\033[36m[{sys_name}]\033[0m"
            print(f"{system_colored} {size_str} ({count})")
            
            for f in sys_files:
                size_colored = f"\033[33m({format_size(os.path.getsize(f['path']))})\033[0m"
                print(f"  {size_colored} {f['name']}")
            print()
        
        total_size = sum(os.path.getsize(f['path']) for f in out)
        print(f"Total: {format_size(total_size)} ({len(out)} games)")
        
        confirm = input("Do you want to continue? [Y/n] ")
        if confirm.lower() in ["y", "yes", ""]:
            for f in out: os.remove(f['path'])
            print(f"\033[92m✓ {len(out)}\033[0m games removed")
        else: print("Abort.")

class Converter:  # CHD conversion utilities
    def __init__(self, mode="chd_to_iso"): 
        self.mode = mode
        self.settings = load_settings()

    def convert_all(self, folder="."):  # Convert all files in folder
        files = []
        for ext, mode in [("*.iso", "iso_to_chd"), ("*.cue", "cue_to_chd"), ("*.gdi", "gdi_to_chd")]:
            files.extend([(mode, f) for f in glob(os.path.join(folder, ext))])
        
        if not files: print("No files to convert."); return
        
        stats = {"pending": len(files), "converting": 0, "done": 0, "failed": 0}
        stats_lock = __import__('threading').Lock()
        
        def convert_worker(mode, file_path):
            with stats_lock: stats["pending"] -= 1; stats["converting"] += 1
            try:
                self.mode = mode
                if self._convert(file_path):
                    with stats_lock: stats["converting"] -= 1; stats["done"] += 1
                else:
                    with stats_lock: stats["converting"] -= 1; stats["failed"] += 1
            except:
                with stats_lock: stats["converting"] -= 1; stats["failed"] += 1
        
        with tqdm(total=100, desc="Converting", bar_format='{desc}: {percentage:3.0f}%', ncols=60, leave=False) as pbar:
            with ThreadPoolExecutor(max_workers=self.settings["convert_workers"]) as exe:
                futures = {exe.submit(convert_worker, mode, file_path): (mode, file_path) for mode, file_path in files}
                for fut in as_completed(futures):
                    desc = f"\033[90m⋯{stats['pending']}\033[0m \033[33m⚙{stats['converting']}\033[0m \033[92m✓{stats['done']}\033[0m \033[91m✗{stats['failed']}\033[0m"
                    pbar.set_description(desc)
                    progress = int(((stats['done'] + stats['failed']) / len(files)) * 100)
                    pbar.n = progress; pbar.refresh()
        
        print(f"\033[92m✓ {stats['done']}\033[0m converted, \033[91m✗ {stats['failed']}\033[0m failed")

    def _convert(self, f):  # Convert single file using chdman
        f = os.path.normpath(f)
        b = os.path.splitext(f)[0]
        ext_map = {"chd_to_iso": ".iso", "chd_to_cue": ".cue", "chd_to_gdi": ".gdi"}
        out = b + (".chd" if "to_chd" in self.mode else ext_map.get(self.mode, ""))
        
        if not os.path.exists(f): print(f"Error: Input file not found: {f}"); return False
        
        f_abs, out_abs = os.path.abspath(f), os.path.abspath(out)
        cmd = ["chdman", "createcd" if "to_chd" in self.mode else "extractcd", "-i", f_abs, "-o", out_abs, "-f"]
        
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, cwd=os.path.dirname(f_abs) or '.')
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='ignore').strip()
                if stderr: print(f"Error converting {os.path.basename(f)}: {stderr[:100]}")
                return False
            
            if os.path.exists(out_abs) and os.path.getsize(out_abs) > 0:
                os.remove(f_abs); return True
            return False
        except FileNotFoundError: print("Error: chdman not found. Please install MAME tools."); return False
        except Exception as e: print(f"Error: {e}"); return False

    def auto_compress_all(self):  # Compress ROMs to CHD with preview
        total_files = []
        for system_dir in glob(os.path.join(self.settings["roms_dir"], "*")):
            system = os.path.basename(system_dir)
            for ext, mode in [("*.iso", "iso_to_chd"), ("*.cue", "cue_to_chd"), ("*.gdi", "gdi_to_chd")]:
                total_files.extend([(mode, f, system) for f in glob(os.path.join(system_dir, ext))])
        
        if not total_files: print("No files to compress."); return
        
        print(f"The following files will be compressed:")
        for mode, file_path, system in total_files:
            system_colored = f"\033[36m[{system}]\033[0m"
            size_colored = f"\033[33m({format_size(os.path.getsize(file_path))})\033[0m"
            base_name = os.path.basename(file_path)
            chd_name = os.path.splitext(base_name)[0] + ".chd"
            
            print(f"  {system_colored} {size_colored} {base_name}")
            print(f"    \033[92m→ Create:\033[0m {chd_name}")
            print(f"    \033[91m→ Delete:\033[0m {base_name}")
            
            if mode == "cue_to_chd":
                dir_name = os.path.dirname(file_path)
                file_base = os.path.splitext(base_name)[0]
                bin_files = glob(os.path.join(dir_name, f"{file_base}.bin")) or glob(os.path.join(dir_name, f"{file_base}*.bin"))
                for bin_file in bin_files:
                    print(f"    \033[91m→ Delete:\033[0m {os.path.basename(bin_file)}")
        
        confirm = input("Do you want to continue? [Y/n] ")
        if confirm.lower() not in ["y", "yes", ""]: print("Abort."); return
        
        stats = {"pending": len(total_files), "compressing": 0, "done": 0, "failed": 0}
        stats_lock = __import__('threading').Lock()
        
        def compress_worker(mode, file_path, system):
            with stats_lock: stats["pending"] -= 1; stats["compressing"] += 1
            try:
                self.mode = mode
                if self._convert(file_path):
                    if mode == "cue_to_chd":
                        dir_name = os.path.dirname(file_path)
                        file_base = os.path.splitext(os.path.basename(file_path))[0]
                        bin_files = glob(os.path.join(dir_name, f"{file_base}.bin")) or glob(os.path.join(dir_name, f"{file_base}*.bin"))
                        for bin_file in bin_files: os.remove(bin_file)
                    with stats_lock: stats["compressing"] -= 1; stats["done"] += 1
                else:
                    with stats_lock: stats["compressing"] -= 1; stats["failed"] += 1
            except:
                with stats_lock: stats["compressing"] -= 1; stats["failed"] += 1
        
        with tqdm(total=100, desc="Compressing", bar_format='{desc}: {percentage:3.0f}%', ncols=60, leave=False) as pbar:
            with ThreadPoolExecutor(max_workers=self.settings["compress_workers"]) as exe:
                futures = {exe.submit(compress_worker, mode, file_path, system): (mode, file_path, system) for mode, file_path, system in total_files}
                for fut in as_completed(futures):
                    desc = f"\033[90m⋯{stats['pending']}\033[0m \033[33m⚙{stats['compressing']}\033[0m \033[92m✓{stats['done']}\033[0m \033[91m✗{stats['failed']}\033[0m"
                    pbar.set_description(desc)
                    progress = int(((stats['done'] + stats['failed']) / len(total_files)) * 100)
                    pbar.n = progress; pbar.refresh()
        
        print(f"\033[92m✓ {stats['done']}\033[0m compressed, \033[91m✗ {stats['failed']}\033[0m failed")

class RomCleaner:  # Duplicate ROM detection and removal
    def __init__(self, regions="W,E,U,J"): 
        self.regions = regions.split(",")
        self.settings = load_settings()

    def _build_rank_table(self, user_regions):  # Build region priority table
        rank_table = {}
        for i, region in enumerate(user_regions):
            rank_table[region] = i
        return rank_table

    def _clean_name(self, filename): return re.sub(r'[\[\(].*?[\]\)]', '', filename).strip()  # Remove brackets/parentheses

    def _extract_tags(self, filename): return re.findall(r'[\[\(]([^\]\)]+)[\]\)]', filename)  # Extract tags from filename

    def _get_region(self, tags):  # Determine region from tags
        for tag in tags:
            if tag.upper() in ['W', 'E', 'U', 'J', 'USA', 'EUR', 'JPN', 'PAL', 'NTSC']:
                return tag.upper()
        return 'U'

    def _region_rank(self, regions): return sum(self._build_rank_table(self.regions).get(r, 999) for r in regions)  # Calculate region priority

    def _get_disc_info(self, tags):  # Extract disc/version info from tags
        disc_info = {'disc': 1, 'version': 1, 'rev': 1}
        for tag in tags:
            if tag.lower().startswith('disc'): disc_info['disc'] = int(tag[4:]) if tag[4:].isdigit() else 1
            elif tag.lower().startswith('v'): disc_info['version'] = int(tag[1:]) if tag[1:].isdigit() else 1
            elif tag.lower().startswith('rev'): disc_info['rev'] = int(tag[3:]) if tag[3:].isdigit() else 1
        return disc_info

    def _build_rank(self, tags):  # Build ranking score for file selection
        region = self._get_region(tags)
        disc_info = self._get_disc_info(tags)
        region_rank = self._region_rank([region])
        purity_score = self._purity_score(tags, "")
        return (region_rank, disc_info['disc'], disc_info['version'], disc_info['rev'], -purity_score)

    def _purity_score(self, tags, filename):  # Calculate purity score for ROM quality
        score = 0
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ['w', 'e', 'u', 'j', 'usa', 'eur', 'jpn', 'pal', 'ntsc']: score += 10
            elif tag_lower in ['final', 'complete', 'full']: score += 5
            elif tag_lower in ['demo', 'beta', 'alpha', 'prototype']: score -= 20
            elif tag_lower in ['hack', 'mod', 'patch']: score -= 10
        return score

    def clean(self):  # Remove duplicate ROMs with preview
        all_files = []
        for system_dir in glob(os.path.join(self.settings["roms_dir"], "*")):
            system = os.path.basename(system_dir)
            for file in os.listdir(system_dir):
                file_path = os.path.join(system_dir, file)
                if os.path.isfile(file_path) and not file.startswith('.'):
                    all_files.append((file_path, system))
        
        if not all_files: print("No games found."); return
        
        by_title = {}
        for path, system in all_files:
            filename = os.path.basename(path)
            clean_title = self._clean_name(filename)
            if clean_title not in by_title: by_title[clean_title] = []
            by_title[clean_title].append((path, filename))
        
        duplicates = {title: files for title, files in by_title.items() if len(files) > 1}
        if not duplicates: print("No duplicate games found."); return
        
        to_keep, to_delete = [], []
        for title, files in duplicates.items():
            ranked_files = []
            for path, filename in files:
                tags = self._extract_tags(filename)
                rank = self._build_rank(tags)
                ranked_files.append((rank, path, filename))
            ranked_files.sort()
            to_keep.append((ranked_files[0][1], title))
            to_delete.extend([(path, title) for _, path, _ in ranked_files[1:]])
        
        if not to_delete: print("No duplicate games found."); return
        
        print(f"The following duplicate games will be processed:")
        
        current_title = None
        for path, title in sorted(to_keep + to_delete, key=lambda x: (x[1], x[0])):
            if title != current_title:
                if current_title is not None: print()
                print(f"\033[1m{title}:\033[0m")
                current_title = title
            
            system = os.path.basename(os.path.dirname(path))
            system_colored = f"\033[36m[{system}]\033[0m"
            size_colored = f"\033[33m({format_size(os.path.getsize(path))})\033[0m"
            filename = os.path.basename(path)
            
            is_keep = (path, title) in to_keep
            if is_keep:
                print(f"  {system_colored} {size_colored} {filename}")
                print(f"    \033[92m→ Keep:\033[0m Best version")
            else:
                print(f"  {system_colored} {size_colored} {filename}")
                print(f"    \033[91m→ Delete:\033[0m Duplicate")
        
        confirm = input("Do you want to continue? [Y/n] ")
        if confirm.lower() in ["y", "yes", ""]:
            for path, _ in to_delete: os.remove(path)
            print(f"\033[92m✓ {len(to_delete)}\033[0m duplicates removed")
        else: print("Abort.")

def main():  # Main CLI entry point
    import sys

    if len(sys.argv) < 2:
        print("retro - retro game package manager")
        print("Usage: retro <command> [options]\n")
        print("Commands:")
        print("  update      - Update game lists")
        print("  install     - Install games")
        print("  remove      - Remove games")
        print("  list        - List installed games")
        print("  search      - Search available games")
        print("  compress    - Compress ROMs to CHD")
        print("  autoremove  - Remove duplicates\n")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "update":
        Manager().update()

    elif cmd == "install":
        if len(sys.argv) < 3:
            print("E: No search term specified")
            sys.exit(1)

        mgr = Manager()
        if not mgr.load():
            print("E: Could not load systems.json")
            sys.exit(1)

        if not os.path.exists(os.path.join(mgr.config_dir, "packages.json")):
            print("E: No package data found. Run 'retro update' first.")
            sys.exit(1)

        try:
            mgr.files = json.load(open(os.path.join(mgr.config_dir, "packages.json")))
        except Exception as e:
            print(f"E: Could not load packages.json: {e}")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        original_input = input
        input_func = lambda prompt: query if "Keywords" in prompt else ""
        import builtins
        builtins.input = input_func
        
        sel = mgr.search_for_install()
        
        builtins.input = original_input
        
        if sel:
            confirm = input("Do you want to continue? [Y/n] ")
            if confirm.lower() in ["y", "yes", ""]:
                mgr.install(sel)
            else:
                print("Abort.")

    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("E: No search term specified")
            sys.exit(1)

        mgr = Manager()
        if not mgr.load():
            print("E: Could not load systems.json")
            sys.exit(1)

        query = " ".join(sys.argv[2:])
        original_input = input
        import builtins
        builtins.input = lambda prompt: query if "Keywords" in prompt else original_input(prompt)
        mgr.uninstall()
        builtins.input = original_input
    
    elif cmd == "list":
        mgr = Manager()
        if not mgr.load():
            print("E: Could not load systems.json")
            sys.exit(1)
        mgr.list()

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("E: No search term specified")
            sys.exit(1)

        mgr = Manager()
        if not mgr.load():
            print("E: Could not load systems.json")
            sys.exit(1)

        if not os.path.exists(os.path.join(mgr.config_dir, "packages.json")):
            print("E: No package data found. Run 'retro update' first.")
            sys.exit(1)

        try:
            mgr.files = json.load(open(os.path.join(mgr.config_dir, "packages.json")))
        except Exception as e:
            print(f"E: Could not load packages.json: {e}")
            sys.exit(1)

        query_terms = sys.argv[2:]
        mgr.search(query_terms)

    elif cmd == "compress":
        Converter().auto_compress_all()

    elif cmd == "autoremove":
        RomCleaner("W,E,U,J").clean()

    else:
        print(f"E: Invalid operation {cmd}")
        sys.exit(1)

if __name__=="__main__": main()