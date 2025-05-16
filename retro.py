import os, re, json, shutil, subprocess, requests, zipfile, tarfile, py7zr, rarfile
from glob import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import reduce

def parse_size(s):
    s = s.replace("i", "").strip()
    if len(s) >= 2 and s[-1].upper() == 'B' and s[-2].upper() in 'KMG': s = s[:-1]
    if not s: return 0
    try: n = float(s[:-1])
    except: return 0
    return int(n*1024**{'K':1,'M':2,'G':3,'T':4}.get(s[-1].upper(),0)) if s[-1].upper() in "KMGT" else int(n)

def format_size(n):
    for u in ('B','KB','MB','GB','TB'):
        if n < 1024: return f"{n:.2f}{u}"
        n /= 1024
    return f"{n:.2f}PB"

def download_file(url, path):
    pos = os.path.getsize(path) if os.path.exists(path) else 0
    total = int(requests.head(url).headers.get('content-length', 0))
    headers = {'Range': f'bytes={pos}-'} if pos < total else {}
    with requests.get(url, headers=headers, stream=True) as r, open(path, 'ab' if pos else 'wb') as f, \
         tqdm(total=total, initial=pos, unit='B', unit_scale=True, desc=os.path.basename(path), leave=False, 
             bar_format='{desc}: {percentage:3.0f}% [{n_fmt}/{total_fmt}]', ncols=80) as p:
        for c in r.iter_content(8192):
            if c: f.write(c); p.update(len(c))
    if os.path.getsize(path) < total: raise Exception(f"Incomplete download: {path}")

def extract_archive(fp, dst, ext):
    os.makedirs(dst, exist_ok=True)
    extractors = {
        "zip": lambda: zipfile.ZipFile(fp).extractall(dst),
        "tar.xz": lambda: tarfile.open(fp, "r:xz").extractall(dst),
        "7z": lambda: py7zr.SevenZipFile(fp, mode="r").extractall(dst),
        "rar": lambda: rarfile.RarFile(fp).extractall(dst)
    }
    if ext not in extractors: raise Exception(f"Unsupported archive: {ext}")
    extractors[ext]()

def get_directory_listing(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    t = soup.find(lambda tag: tag.name == "table" and 
                ("directory-listing-table" in tag.get("class", []) or tag.get("id") == "list"))
    if not t: return []
    h = [th.text.strip().lower() for th in t.find_all("th")]
    name_idx, size_idx = h.index("name") if "name" in h else 0, h.index("size") if "size" in h else None
    out, tbody = [], t.find("tbody")
    if not tbody: return out
    
    for tr in tbody.find_all("tr"):
        td = tr.find_all("td")
        if not td or not td[name_idx].find("a"): continue
        a = td[name_idx].find("a")
        if "parent directory" in a.text.lower(): continue
        name, link = a.text.strip(), a["href"]
        sz = td[size_idx].text.strip() if size_idx is not None and size_idx < len(td) else (
            (tr.find("td", class_="size") or (td[2] if len(td)>2 else None)))
        sz = sz.text.strip() if hasattr(sz, "text") else (sz or "")
        out.append({"name":name, "link":link, "size_str":sz, "size_bytes":parse_size(sz), "base":url})
    return out

class Manager:
    def __init__(self, cfg="systems.json"): 
        self.cfg, self.systems, self.files = cfg, {}, []
        
    def load(self):
        try: self.systems = json.load(open(self.cfg)); return True
        except Exception as e: print(f"Failed to read systems.json\nError: {e}"); return False

    def fetch_system(self, sys_name):
        out, fmt = [], [e.lower() for e in self.systems[sys_name].get("format", [])]
        for url in self.systems[sys_name].get("url", []):
            lst = [f for f in get_directory_listing(url) if 
                  any(f["name"].lower().endswith("." + e) for e in fmt) or 
                  f["name"].lower().endswith((".zip", ".7z", ".tar.xz", ".rar"))]
            for f in lst: f["system"] = sys_name
            out.extend(lst)
        return out

    def fetch(self):
        with ThreadPoolExecutor(max_workers=4) as exe:
            futures = {exe.submit(self.fetch_system, s): s for s in self.systems}
            self.files = []
            for fut in tqdm(as_completed(futures), total=len(futures), desc="Fetching", 
                          bar_format='Fetching: {percentage:3.0f}% [{n_fmt}/{total_fmt}]', ncols=80): 
                self.files.extend(fut.result())
        
        print("\nListing systems...")
        for sc, data in self.systems.items():
            games = [f for f in self.files if f["system"] == sc]
            folder = os.path.join("roms", sc)
            
            installed = 0
            if os.path.isdir(folder):
                for f in games:
                    if os.path.exists(os.path.join(folder, f["name"])): 
                        installed += 1; continue
                    bn = os.path.splitext(f["name"])[0]
                    for x in os.listdir(folder):
                        if os.path.isfile(os.path.join(folder, x)) and os.path.splitext(x)[0] == bn:
                            installed += 1; break
            
            print(f"\033[92m✓\033[0m {format_size(sum(f.get('size_bytes',0) for f in games))} "
                 f"{data.get('name', sc)} ({sc.lower()}) ({len(games)}) "
                 f"({installed} installed)" if installed > 0 else "")

    def update(self):
        if not self.load(): return
        self.fetch()
        with open("packages.json", "w") as f: json.dump(self.files, f, indent=4)

    def search(self):
        terms = input("Keywords: ").split()
        keys = {s.lower() for s in self.systems}
        inc = {t.lower() for t in terms if t.lower() in keys}
        kw = [t for t in terms if t.lower() not in keys and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]
        
        if len(terms) == 2 and terms[0].lower() == "all" and terms[1].lower() in keys:
            initial_results = [f for f in self.files if f["system"].lower() == terms[1].lower()]
        else: 
            initial_results = [f for f in self.files if 
                  (not inc or f["system"].lower() in inc) and 
                  (not kw or all(k.lower() in f["name"].lower() for k in kw)) and 
                  (not exc or not any(e.lower() in f["name"].lower() for e in exc))]
        
        if not initial_results: print("\nNo packages to install."); return []
        
        out = []
        for f in initial_results:
            is_installed = False
            system_dir = os.path.join("roms", f["system"])
            if os.path.isdir(system_dir):
                if os.path.exists(os.path.join(system_dir, f["name"])):
                    is_installed = True
                else:
                    bn = os.path.splitext(f["name"])[0]
                    is_installed = any(os.path.splitext(x)[0] == bn for x in os.listdir(system_dir) 
                                      if os.path.isfile(os.path.join(system_dir, x)))
            if not is_installed: out.append(f)
        
        if not out: print("\nAll matching packages are already installed."); return []
        
        print("\nListing packages...")
        for f in initial_results:
            is_installed = False
            system_dir = os.path.join("roms", f["system"])
            if os.path.isdir(system_dir):
                if os.path.exists(os.path.join(system_dir, f["name"])):
                    is_installed = True
                else:
                    bn = os.path.splitext(f["name"])[0]
                    is_installed = any(os.path.splitext(x)[0] == bn for x in os.listdir(system_dir) 
                                      if os.path.isfile(os.path.join(system_dir, x)))
            
            print(f"{'\033[92m✓\033[0m' if is_installed else '\033[91m✗\033[0m'} "
                  f"{format_size(f.get('size_bytes', 0))} {f['name']} ({f['system']})")
            
        print(f"\n{len(out)} packages to install ({format_size(sum(f['size_bytes'] for f in out))})")
        return out

    def install(self, pkgs):
        if input("Install? [Y/n]: ").lower() not in ("y", "yes", ""): 
            print("\nInstallation cancelled."); return
        
        def worker(f):
            dest, tmp = os.path.join("roms", f["system"]), os.path.join("roms", f["system"], "tmp")
            os.makedirs(dest, exist_ok=True); os.makedirs(tmp, exist_ok=True)
            
            if os.path.exists(os.path.join(dest, f["name"])): return ("skipped", f)
                
            bn = os.path.splitext(f["name"])[0]
            if any(os.path.splitext(x)[0] == bn for x in os.listdir(dest) 
                 if os.path.isfile(os.path.join(dest, x))): return ("skipped", f)
            
            tmp_path = os.path.join(tmp, f["name"])
            url = f["base"].rstrip("/") + "/" + f["link"]
            try:
                download_file(url, tmp_path)
                ext = "tar.xz" if f["name"].endswith(".tar.xz") else os.path.splitext(f["name"])[1].lstrip(".").lower()
                if ext in [e.lower() for e in self.systems[f["system"]].get("format", [])]:
                    shutil.move(tmp_path, os.path.join(dest, f["name"]))
                else: 
                    extract_archive(tmp_path, dest, ext); os.remove(tmp_path)
                return ("done", f)
            except Exception as e: return ("error", f, str(e))
                
        with tqdm(total=len(pkgs), desc="Installing", 
                 bar_format='Installing: {percentage:3.0f}% [{n_fmt}/{total_fmt}]',
                 ncols=80) as pbar:
            with ThreadPoolExecutor(max_workers=20) as exe:
                futures = {exe.submit(worker, pkg): pkg for pkg in pkgs}
                for fut in as_completed(futures): pbar.update(1)
        
        for sys_name in set(pkg["system"] for pkg in pkgs):
            tmp_dir = os.path.join("roms", sys_name, "tmp")
            if os.path.exists(tmp_dir) and not os.listdir(tmp_dir): shutil.rmtree(tmp_dir)
            
        print("\nInstallation complete.")

    def install_from_file(self):
        try:
            if not self.load(): print("Failed to load systems.json"); return
            try: self.files = json.load(open("packages.json"))
            except Exception as e: print(f"Failed to load packages.json: {e}"); return
        except Exception as e: print(f"Load error: {e}"); return
        sel = self.search()
        if sel: self.install(sel)

    def list(self):
        try: self.systems = json.load(open(self.cfg))
        except Exception as e: print(f"Error loading systems.json: {e}"); return
        
        for sc, data in self.systems.items():
            folder = os.path.join("roms", sc)
            if not os.path.isdir(folder): continue
            
            files = [{"name": f, "path": os.path.join(folder, f), "size": os.path.getsize(os.path.join(folder, f))} 
                    for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            
            if not files: continue
            
            files = sorted(files, key=lambda x: x["name"])
            total_size = sum(f["size"] for f in files)
            
            print(f"{data.get('name', sc)} [{format_size(total_size)}] ({len(files)} packages)")
            
            for f in files:
                print(f"\033[92m✓\033[0m {format_size(f['size'])} {f['name']}")
            
            print()

    def uninstall(self):
        try: self.systems = json.load(open(self.cfg))
        except Exception as e: print(f"Error loading systems.json: {e}"); return
        
        inst = [{"system": sc, "name": f, "path": os.path.join("roms", sc, f)}
               for sc in self.systems 
               for f in (os.listdir(os.path.join("roms", sc)) 
                        if os.path.isdir(os.path.join("roms", sc)) else [])
               if os.path.isfile(os.path.join("roms", sc, f))]
        
        if not inst: print("No installed packages."); return
        
        terms = input("Keywords: ").split()
        keys = {s.lower() for s in self.systems}
        inc = {t.lower() for t in terms if t.lower() in keys}
        kw = [t for t in terms if t.lower() not in keys and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]
        
        if len(terms) == 2 and terms[0].lower() == "all" and terms[1].lower() in keys:
            out = [p for p in inst if p["system"].lower() == terms[1].lower()]
        else:
            out = [p for p in inst if 
                  (not inc or p["system"].lower() in inc) and 
                  (not kw or all(k.lower() in p["name"].lower() for k in kw)) and 
                  (not exc or not any(e.lower() in p["name"].lower() for e in exc))]
        
        if not out: print("\nNo packages to uninstall."); return
        
        for p in out: p["size_str"] = format_size(os.path.getsize(p["path"]))
        if terms[0].lower() != "all":
            print("\nListing packages...")
            for p in out: print(f"\033[91m✗\033[0m {p['size_str']} {p['name']} ({p['system']})")
        
        print(f"\n{len(out)} packages selected ({format_size(sum(os.path.getsize(p['path']) for p in out))})")
        if input("Delete? [y/N]: ").lower() != "y": print("\nCancelled."); return
        
        with tqdm(total=len(out), desc="Deleting", 
                  bar_format='Deleting: {percentage:3.0f}% [{n_fmt}/{total_fmt}]',
                  ncols=80) as pbar:
            for p in out: 
                try: os.remove(p["path"]); pbar.update(1)
                except Exception as e: print(f"Error deleting {p['path']}: {e}")
            
        print("\nUninstallation complete.")

class Converter:
    def __init__(self, mode="chd_to_iso"): self.mode = mode
    
    def convert_all(self, folder="."):
        ext_map = {"chd_to_iso": "*.chd", "chd_to_cue": "*.chd", "chd_to_gdi": "*.chd", 
                  "iso_to_chd": "*.iso", "cue_to_chd": "*.cue", "gdi_to_chd": "*.gdi"}
        files = sorted(glob(os.path.join(folder, ext_map.get(self.mode, "*.chd"))))
        if not files: print("No matching files found."); return
        
        with tqdm(total=len(files), desc="Converting", 
                 bar_format='Converting: {percentage:3.0f}% [{n_fmt}/{total_fmt}]',
                 ncols=80) as pbar:
            for f in files: self._convert(f); pbar.update(1)
        
        print("\nConversion complete.")

    def _convert(self, f):
        b = os.path.splitext(f)[0]
        ext_map = {"chd_to_iso": ".iso", "chd_to_cue": ".cue", "chd_to_gdi": ".gdi"}
        out = b + (".chd" if "to_chd" in self.mode else ext_map.get(self.mode, ""))
        cmd = ["chdman", "createcd" if "to_chd" in self.mode else "extractcd", "-i", f, "-o", out, "-f"]
        
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(out) and os.path.getsize(out) > 0:
                os.remove(f); return True
            return False
        except Exception as e: print(f"Error converting {f}: {e}"); return False

    def auto_compress_all(self):
        roms_dir = "roms"
        if not os.path.isdir(roms_dir): print("Folder 'roms/' not found."); return
            
        try: systems_data = json.load(open("systems.json"))
        except Exception as e: print(f"Error loading systems.json: {e}"); systems_data = {}
            
        systems = [d for d in os.listdir(roms_dir) if os.path.isdir(os.path.join(roms_dir, d))]
        if not systems: print("No systems in 'roms/'."); return
            
        print("\nScanning for files to compress...")
        
        total_files = []
        for system in systems:
            system_dir = os.path.join(roms_dir, system)
            for ext, mode in [("*.iso", "iso_to_chd"), ("*.cue", "cue_to_chd"), ("*.gdi", "gdi_to_chd")]:
                total_files.extend([(mode, f, system) for f in glob(os.path.join(system_dir, ext))])
        
        if not total_files: print("No files found to compress."); return
            
        by_system = {}
        for mode, path, system in total_files:
            if system not in by_system: by_system[system] = []
            by_system[system].append((mode, path))
            
        total_size = sum(os.path.getsize(f) for _, f, _ in total_files)
        print(f"\nFound {len(total_files)} files to compress [{format_size(total_size)}]:")
        
        all_files_to_delete = []
        
        for system, files in sorted(by_system.items()):
            system_name = systems_data.get(system, {}).get("name", system)
            print(f"\n{system_name} ({len(files)} files):")
            
            for mode, path in files:
                base_name = os.path.basename(path)
                dir_name = os.path.dirname(path)
                file_base = os.path.splitext(base_name)[0]
                
                print(f"\033[92m✓\033[0m {file_base}.chd")
                print(f"\033[91m✗\033[0m {format_size(os.path.getsize(path))} {base_name}")
                all_files_to_delete.append(path)
                
                if mode == "cue_to_chd":
                    bin_files = glob(os.path.join(dir_name, f"{file_base}.bin")) or glob(os.path.join(dir_name, f"{file_base}*.bin"))
                    for bin_file in bin_files:
                        bin_name = os.path.basename(bin_file)
                        print(f"\033[91m✗\033[0m {format_size(os.path.getsize(bin_file))} {bin_name}")
                        all_files_to_delete.append(bin_file)
        
        if input("\nCompress all files? [y/N]: ").lower() != "y": print("\nOperation cancelled."); return
            
        with tqdm(total=len(total_files), desc="Compressing", 
                 bar_format='Compressing: {percentage:3.0f}% [{n_fmt}/{total_fmt}]',
                 ncols=80) as pbar:
            for mode, file_path, _ in total_files:
                self.mode = mode
                self._convert(file_path)
                pbar.update(1)
                
                if mode == "cue_to_chd":
                    dir_name = os.path.dirname(file_path)
                    file_base = os.path.splitext(os.path.basename(file_path))[0]
                    bin_files = glob(os.path.join(dir_name, f"{file_base}.bin")) or glob(os.path.join(dir_name, f"{file_base}*.bin"))
                    for bin_file in bin_files:
                        if os.path.exists(bin_file):
                            try: os.remove(bin_file)
                            except Exception as e: print(f"Error deleting {bin_file}: {e}")
                
        print("\nCompression complete.")

class RomCleaner:
    def __init__(self, regions="W,E,U,J"):
        self.regions = regions
        self.country_codes = {
            'As':'Asia', 'A': 'Australia', 'B': 'Brazil', 'C': 'Canada', 'Ch':'China', 'D': 'Netherlands', 
            'E':'Europe', 'F':'France', 'Fn': 'Finland', 'G': 'Germany', 'Gr': 'Greece', 'Hk': 'Hong Kong', 
            'I': 'Italy','J':'Japan','K':'Korea','Nl':'Netherlands', 'No':'Norway', 'R': 'Russia', 'S': 'Spain', 
            'Sw': 'Sweden', 'U': 'USA', 'UK': 'United Kingdom', 'W': 'World', 'Unl': 'Unlicensed', 
            'PD': 'Public Domain', 'Unk': 'Unknown'
        }
        self.release_codes = ['!','rev','alternate','alt','v','o','beta','proto','alpha','promo','pirate','demo','sample','bootleg','b']
        self.special_collections = [
            'mega drive mini', 'sonic classic collection', 'sonic mega collection', 'sega channel', 
            'rev a', 'rev b', 'rev 1', 'rev 2', 'rev 3', 'virtual console'
        ]
        self.rank_table = self._build_rank_table([r.strip() for r in regions.split(',')])
        
    def _build_rank_table(self, user_regions):
        valid_regions = set(self.country_codes.keys()) | set(self.country_codes.values())
        for region in user_regions:
            if region not in valid_regions:
                print(f"Warning: Region code '{region}' is not recognized. Skipping.")
                user_regions.remove(region)
        alpha_rank = [(i, item) for i, item in enumerate(sorted(set(self.country_codes) - set(user_regions), reverse=True))]
        return alpha_rank + [(i, item) for i, item in enumerate(reversed(user_regions), start=len(alpha_rank))]

    def _clean_name(self, filename):
        return re.sub(r'[\[\(].*?[\]\)]', '', os.path.splitext(filename)[0]).strip()

    def _extract_tags(self, filename):
        tags = []
        for content in re.findall(r'\(([^()]+)\)', filename) + re.findall(r'\[([^\[\]]+)\]', filename):
            tags.extend([tag.strip() for tag in content.split(',')])
        return sorted(set(tags))
    
    def _get_region(self, tags):
        regions = [code for tag in tags for code, name in self.country_codes.items() 
                  if tag in (code, name)]
        return regions or ['Unk']
    
    def _region_rank(self, regions):
        scores = [rank for rank, code in self.rank_table if code in regions]
        return max(scores) if scores else 0
    
    def _get_disc_info(self, tags):
        for tag in tags:
            for prefix in ['disc', 'disk', 'side', 'volume']:
                if tag.lower().startswith(prefix + ' '):
                    try:
                        num = tag.lower().split(' ')[1]
                        return int(num) if num.isdigit() else ord(num[0])
                    except (IndexError, ValueError): pass
        return 0
    
    def _build_rank(self, tags):
        build_rank = len(self.release_codes) - 2
        version = float('inf')
        for tag in tags:
            tag_lower = tag.lower()
            for i, code in enumerate(self.release_codes):
                if tag_lower.startswith(code):
                    build_rank = len(self.release_codes) - i - 1
                    version_match = re.search(r'(\d+(\.\d+)?)', tag_lower)
                    if version_match:
                        try: version = float(version_match.group(1))
                        except ValueError: pass
                    break
        return (build_rank, version)
    
    def _purity_score(self, tags, filename):
        score = 100
        for tag in tags:
            tag_lower = tag.lower()
            for special in self.special_collections:
                if special in tag_lower: score -= 10; break
        if any(re.search(r'rev\s*[a-z0-9]', tag.lower()) for tag in tags): score -= 5
        if any(re.search(r'\d{4}-\d{2}', tag) for tag in tags): score -= 3
        if sum(1 for t in tags if any(r in t for r in self.country_codes)) == len(tags): score += 10
        if any(tag in ('W', 'World') for tag in tags): score += 5
        if "[BIOS]" in filename: score -= 50
        return score
    
    def clean(self):
        print("\nScanning for duplicates...")
        
        all_files = [os.path.join(root, filename) for root, _, files in os.walk("roms") 
                     for filename in files if not filename.startswith('.') and os.path.isfile(os.path.join(root, filename))]
        
        groups = {}
        for filepath in all_files:
            filename = os.path.basename(filepath)
            clean_name = self._clean_name(filename)
            if clean_name not in groups: groups[clean_name] = []
            groups[clean_name].append({
                'path': filepath, 'name': filename, 'size': os.path.getsize(filepath),
                'tags': self._extract_tags(filename), 'ext': os.path.splitext(filename)[1]
            })
        
        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        
        if not duplicate_groups:
            print("No duplicates found.")
            return
        
        print(f"Found {len(duplicate_groups)} titles with duplicates")
        
        total_files = 0
        total_size = 0
        to_delete = []
        
        for title, files in sorted(duplicate_groups.items()):
            ext = files[0]['ext']
            print(f"\n{title}{ext} ({len(files)-1} duplicates)")
            
            for f in files:
                f['regions'] = self._get_region(f['tags'])
                f['region_rank'] = self._region_rank(f['regions'])
                f['build_rank'] = self._build_rank(f['tags'])
                f['disc_num'] = self._get_disc_info(f['tags'])
                f['purity'] = self._purity_score(f['tags'], f['name'])
            
            sorted_files = sorted(files, 
                key=lambda x: (x['build_rank'][0], x['purity'], x['region_rank'], 
                               x['build_rank'][1], -x['size'], -x['disc_num']),
                reverse=True)
            
            keep_file = sorted_files[0]
            for i, f in enumerate(sorted_files):
                total_files += 1
                total_size += f['size'] / (1024**2)
                size_mb = f['size'] / (1024**2)
                
                if i == 0 or (f['disc_num'] > 0 and keep_file['disc_num'] > 0 and f['disc_num'] != keep_file['disc_num']):
                    mark = "\033[92m✓\033[0m"; to_keep = True
                else:
                    mark = "\033[91m✗\033[0m"; to_delete.append(f['path']); to_keep = False
                
                print(f"{mark} {size_mb:.2f}MB {f['name']}")
        
        delete_size = sum(os.path.getsize(f) for f in to_delete) / (1024**2)
        print(f"\nFound {len(to_delete)} duplicates that can be deleted ({delete_size:.2f}MB)")
        print(f"Total files: {total_files} ({total_size:.2f}MB)")
        
        if not to_delete: return
        
        if input("Delete duplicates? [y/N]: ").lower() == 'y':
            with tqdm(total=len(to_delete), desc="Deleting", 
                      bar_format='Deleting: {percentage:3.0f}% [{n_fmt}/{total_fmt}]',
                      ncols=80) as pbar:
                for path in to_delete:
                    try: os.remove(path); pbar.update(1)
                    except Exception as e: print(f"Error deleting {path}: {e}")
            print("\nDuplicate cleaning complete.")
        else: print("\nOperation cancelled.")

def clean_menu():
    RomCleaner("W,E,U,J").clean()

def compress_packages():
    Converter().auto_compress_all()

def main():
    menu = {
        "1": ("Update packages", lambda: Manager().update()),
        "2": ("Install packages", lambda: Manager().install_from_file()),
        "3": ("Uninstall packages", lambda: Manager().uninstall()),
        "4": ("List Installed", lambda: Manager().list()),
        "5": ("Compress packages", compress_packages),
        "6": ("Clean duplicates", clean_menu),
        "0": ("Exit", exit)
    }
    
    while True:
        try: avail = json.load(open("packages.json"))
        except: avail = []
        
        a_count = len(avail)
        a_size = sum(f.get("size_bytes",0) for f in avail)
        a_sys = len({f.get("system") for f in avail})
        
        roms_dir = "roms"
        systems = [d for d in os.listdir(roms_dir) if os.path.isdir(os.path.join(roms_dir,d))] if os.path.isdir(roms_dir) else []
        
        t_games = t_size = 0
        for folder in systems:
            p = os.path.join("roms", folder)
            files = [os.path.join(r, f) for r,_,fs in os.walk(p) for f in fs]
            t_games += len(files)
            t_size += sum(os.path.getsize(f) for f in files)
        
        mark = "\033[92m✓\033[0m"
        print(f"""
▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▖  ▗▄▖ 
▐▌ ▐▌▐▌     █  ▐▌ ▐▌▐▌ ▐▌  {mark} {t_games}/{a_count} games
▐▛▀▚▖▐▛▀▀▘  █  ▐▛▀▚▖▐▌ ▐▌  {mark} {len(systems)}/{a_sys} systems
▐▌ ▐▌▐▙▄▄▖  █  ▐▌ ▐▌▝▚▄▞▘  {mark} {format_size(t_size)}/{format_size(a_size)} total""")
        print("─"*50)
        for k,v in menu.items(): print(f"[{k}] {v[0]}")
        print("─"*50)
        
        act = menu.get(input("Select option: ").strip())
        print(" "*50, end="\r")
        if act: act[1]()
        else: print("Invalid option.")
        input("\nPress Enter to return to menu...")

if __name__=="__main__": main()