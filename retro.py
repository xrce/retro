import os, re, json, shutil, subprocess, requests, zipfile, tarfile, py7zr, rarfile
from glob import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt}'

class Manager:
    @staticmethod
    def _ps(s):
        s = s.replace("i", "").strip()
        if len(s) >= 2 and s[-1].upper()=='B' and s[-2].upper() in 'KMG': s = s[:-1]
        if not s: return 0
        try: n = float(s[:-1])
        except: return 0
        return int(n*1024**{'K':1,'M':2,'G':3,'T':4}.get(s[-1].upper(),0)) if s[-1].upper() in "KMG T" else int(n)

    @staticmethod
    def _fs(n):
        for u in ('B','KB','MB','GB','TB'):
            if n<1024: return f"{n:.2f}{u}"
            n /= 1024
        return f"{n:.2f}PB"

    @staticmethod
    def _download(url, path):
        pos = os.path.getsize(path) if os.path.exists(path) else 0
        total = int(requests.head(url).headers.get('content-length',0))
        hdr = {'Range':f'bytes={pos}-'} if pos<total else {}
        with requests.get(url, headers=hdr, stream=True) as r, open(path, 'ab' if pos else 'wb') as f, tqdm(total=total, initial=pos, unit='B', unit_scale=True, desc=f"{path}", leave=False, bar_format=bar_format, ncols=50) as p:
            for c in r.iter_content(8192):
                if c: f.write(c); p.update(len(c))
        if os.path.getsize(path)<total: raise Exception(f"Incomplete download: {path}")

    @staticmethod
    def _extract(fp, dst, ext):
        os.makedirs(dst, exist_ok=True)
        if ext=="zip": zipfile.ZipFile(fp).extractall(dst)
        elif ext=="tar.xz": tarfile.open(fp,"r:xz").extractall(dst)
        elif ext=="7z": py7zr.SevenZipFile(fp,mode="r").extractall(dst)
        elif ext=="rar": rarfile.RarFile(fp).extractall(dst)
        else: raise Exception("Unsupported archive:"+ext)

    @staticmethod
    def _get_files(url):
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
        t = BeautifulSoup(r.text, "html.parser").find(lambda tag: tag.name=="table" and (tag.get("class")=="directory-listing-table" or tag.get("id")=="list"))
        out = []
        if t and (tbody:=t.find("tbody")):
            for tr in tbody.find_all("tr"):
                a = tr.find("a")
                if not a or "parent directory" in a.text.lower(): continue
                td = tr.find_all("td")[2] if t.get("class") else tr.find("td", class_="size")
                sz = td.text.strip() if td else ""
                out.append({"name":a.text.strip(),"link":a["href"],"size_str":sz,"size_bytes":Manager._ps(sz),"base":url})
        return out

    def __init__(self, cfg="systems.json"): self.cfg, self.systems, self.files = cfg, {}, []
    def load(self):
        try: self.systems = json.load(open(self.cfg))
        except Exception as e: print("Failed to read systems.json\nError:", e); return False
        return True

    def fetch_system(self, sys_name):
        out = []
        fmt = [e.lower() for e in self.systems[sys_name].get("format",[])]
        for url in self.systems[sys_name].get("url",[]):
            lst = [f for f in Manager._get_files(url) if any(f["name"].lower().endswith("."+e) for e in fmt) or f["name"].lower().endswith((".zip",".7z",".tar.xz",".rar"))]
            for f in lst: f["system"] = sys_name
            out += lst
        return out

    def fetch(self):
        files = []
        with ThreadPoolExecutor(max_workers=4) as exe:
            futures = {exe.submit(self.fetch_system, s): s for s in self.systems}
            for fut in tqdm(as_completed(futures), total=len(futures), desc="Fetching", unit="sys", bar_format=bar_format, ncols=50): files += fut.result()
        self.files = files
        print("\nListing systems...")
        for sc, data in self.systems.items():
            games = [f for f in self.files if f["system"]==sc]
            total = sum(f["size_bytes"] for f in games)
            folder = os.path.join("roms", sc)
            installed = len(os.listdir(folder)) if os.path.isdir(folder) else 0
            status = "(complete)" if games and installed==len(games) else (f"({installed} installed)" if installed>0 else "")
            print(f":: {data.get('name',sc)} ({sc.lower()}) ({len(games)}) [{Manager._fs(total)}] {status}")
        print()

    def update(self):
        if not self.load(): return
        self.fetch()
        with open("packages.json", "w") as f: json.dump(self.files, f, indent=4)

    def search(self):
        terms = input("Keywords: ").split()
        keys = {s.lower() for s in self.systems}
        inc = {t.lower() for t in terms if t.lower() in keys}
        kw  = [t for t in terms if t.lower() not in keys and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]
        if len(terms)==2 and terms[0].lower()=="all" and terms[1].lower() in keys: sn = terms[1].lower(); out = [f for f in self.files if f["system"].lower()==sn]
        else: out = [f for f in self.files if (not inc or f["system"].lower() in inc) and (not kw or all(k.lower() in f["name"].lower() for k in kw)) and (not exc or not any(e.lower() in f["name"].lower() for e in exc))]
        if not out:  print("\nNo packages to install."); return []
        if terms[0].lower()!="all": print("\nListing packages...")
        if terms[0].lower()!="all":
            for f in out: print(f":: {f['name']} [{f['size_str']}] ({f['system']})")
        print(f"\n{len(out)} packages selected ({Manager._fs(sum(f['size_bytes'] for f in out))})")
        return out

    def install(self, pkgs):
        if input("Install? [Y/n]: ").lower() not in ("y","yes",""): return print("\nInstallation cancelled.")
        tmp = os.path.join("roms","tmp"); os.makedirs(tmp, exist_ok=True)
        total = len(pkgs); pbar = tqdm(total=total, desc="Installing", unit="pkg", bar_format=bar_format, ncols=50)
        def worker(f):
            dest = os.path.join("roms", f["system"]); os.makedirs(dest, exist_ok=True)
            bn = os.path.splitext(f["name"])[0]
            if any(os.path.splitext(x)[0]==bn for x in os.listdir(dest) if os.path.isfile(os.path.join(dest,x))): return ("skipped", f)
            tmp_path = os.path.join(tmp, f["name"])
            url = f["base"].rstrip("/") + "/" + f["link"]
            try:
                Manager._download(url, tmp_path)
                ext = "tar.xz" if f["name"].endswith(".tar.xz") else os.path.splitext(f["name"])[1].lstrip(".").lower()
                if ext in [e.lower() for e in self.systems[f["system"]].get("format",[])]: shutil.move(tmp_path, os.path.join(dest, f["name"]))
                else: Manager._extract(tmp_path, dest, ext); os.remove(tmp_path)
                return ("done", f)
            except Exception as e: return ("error", f, str(e))
        results = []
        with ThreadPoolExecutor(max_workers=20) as exe:
            futures = {exe.submit(worker, pkg): pkg for pkg in pkgs}
            for fut in as_completed(futures): results.append(fut.result()); pbar.update(1)
        pbar.close()
        print("\nInstallation complete.")

    def install_from_file(self):
        try:
            self.systems = json.load(open(self.cfg))
            self.files = json.load(open("packages.json"))
        except Exception as e: print("Load error:",e); return
        sel = self.search()
        if sel: self.install(sel)

    def list(self):
        try: systems = json.load(open(self.cfg))
        except Exception as e: print("Error loading systems.json:",e); return
        for sc, data in systems.items():
            folder = os.path.join("roms", sc)
            if os.path.isdir(folder):
                files = sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
                if not files: continue
                sizes = [os.path.getsize(os.path.join(folder, f)) for f in files]
                total = sum(sizes)
                print(f"{data.get('name',sc)} [{Manager._fs(total)}] ({len(files)} packages)")
                for f, sz in zip(files, sizes): print(f":: {f} [{Manager._fs(sz)}]")
                print()

    def uninstall(self):
        try: systems = json.load(open(self.cfg))
        except Exception as e: print("Error loading systems.json:",e); return
        inst = []
        for sc in systems:
            folder = os.path.join("roms", sc)
            if os.path.isdir(folder):
                for f in os.listdir(folder):
                    p = os.path.join(folder, f)
                    if os.path.isfile(p): inst.append({"system":sc,"name":f,"path":p})
        if not inst: return print("No installed packages.")
        terms = input("Keywords: ").split()
        keys = {s.lower() for s in systems}
        inc = {t.lower() for t in terms if t.lower() in keys}
        kw = [t for t in terms if t.lower() not in keys and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]
        if len(terms)==2 and terms[0].lower()=="all" and terms[1].lower() in keys: sn = terms[1].lower(); out = [p for p in inst if p["system"]==sn]
        else: out = [p for p in inst if (not inc or p["system"].lower() in inc) and (not kw or all(k.lower() in p["name"].lower() for k in kw)) and (not exc or not any(e.lower() in p["name"].lower() for e in exc))]
        if not out: return print("\nNo packages to uninstall.")
        for p in out: p["size_str"]=Manager._fs(os.path.getsize(p["path"]))
        if terms[0].lower()!="all": print("\nListing packages...")
        if terms[0].lower()!="all":
            for p in out: print(f":: {p['name']} [{p['size_str']}] ({p['system']})")
        tot = sum(os.path.getsize(p["path"]) for p in out)
        print(f"\n{len(out)} packages selected ({Manager._fs(tot)})")
        if input("Delete? [y/N]: ").lower()!="y": return print("\nCancelled.")
        pbar = tqdm(total=len(out), desc="Deleting", unit="pkg", bar_format=bar_format, ncols=50)
        for p in out: pbar.update(1); os.remove(p["path"])
        pbar.close()
        print("\nUninstallation complete.")

class Converter:
    def __init__(self, mode="chd_to_iso"): self.mode = mode
    def convert_all(self, folder="."):
        ext = {"chd_to_iso":"*.chd", "chd_to_cue":"*.chd", "chd_to_gdi":"*.chd", "iso_to_chd":"*.iso", "cue_to_chd":"*.cue", "gdi_to_chd":"*.gdi"}.get(self.mode, "*.chd")
        files = sorted(glob(os.path.join(folder, ext)))
        if not files: return print("No matching files found.")
        for i, f in enumerate(files,1): self._convert(f,i,len(files))

    def _convert(self, f, i, t):
        b = os.path.splitext(f)[0]
        out = b + (".chd" if "to_chd" in self.mode else {"chd_to_iso":".iso","chd_to_cue":".cue","chd_to_gdi":".gdi"}[self.mode])
        args = ["chdman", "createcd" if "to_chd" in self.mode else "extractcd", "-i", f, "-o", out, "-f"]
        bef = os.path.getsize(f)
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        aft = os.path.getsize(out) if os.path.exists(out) else 0
        if aft: os.remove(f)
        print(f":: {i}/{t}  {Manager._fs(bef)}->{Manager._fs(aft)}  {os.path.basename(out)}")

    def _fs(self,n):
        for u in ['B','KB','MB','GB','TB']:
            if n<1024: return f"{n:.2f}{u}"
            n /=1024
        return f"{n:.2f}PB"

class Cleaner:
    def __init__(self, regions="W,E,U,J", skip_ext=(".txt",".xml")):
        self.reg_prio = dict(zip(regions.split(","), range(1,4)))
        self.skip_ext = skip_ext

    def _clean_name(self, name):
        base = re.sub(r'[\[\(].*?[\]\)]', '', name).strip()
        return re.sub(r'\s+(\.[^.]+)$', r'\1', base)

    def _region_prio(self, name):
        toks = re.findall(r'[\[\(]([^)\]]+)[\]\)]', name)
        return min((self.reg_prio.get(t.strip().upper(), 99) for t in toks), default=99)

    def scan(self):
        groups = {}
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('.') or f.lower().endswith(self.skip_ext): continue
                full = os.path.join(root, f)
                base = self._clean_name(f)
                groups.setdefault(base, []).append(full)
        return {b:ps for b,ps in groups.items() if len(ps)>1}

    def report(self, dup):
        info = {}
        tot_dup = tot_size = 0
        for base, paths in sorted(dup.items()):
            best = max(paths, key=lambda p: ((-self._region_prio(os.path.basename(p))), os.path.getsize(p)))
            dups = [p for p in paths if p!=best]
            cnt, sz = len(dups), sum(os.path.getsize(p) for p in dups)
            tot_dup += cnt; tot_size += sz; info[base] = (dups, cnt, sz)
        print("\nListing duplicates...")
        for base, (dups, cnt, sz) in info.items(): print(f":: {base} ({cnt} duplicates) ({Manager._fs(sz)})")
        print(f"\n{tot_dup} duplicates from {len(info)} packages selected ({Manager._fs(tot_size)})")
        return info

    def clean(self):
        dup = self.scan()
        if not dup: print("No duplicates found."); return
        info = self.report(dup)
        if input("Delete? [y/N]: ").strip().lower()!="y": print("Cancelled."); return
        tot = sum(len(v[0]) for v in info.values())
        pbar = tqdm(total=tot, desc="Deleting", unit="file", bar_format=bar_format, ncols=50)
        for base, (paths, cnt, sz) in info.items():
            for p in paths:
                pbar.update(1)
                try: os.remove(p)
                except Exception as e: print(f"Error deleting {p}: {e}")
        pbar.close(); print("\nCleaning complete.")

def convert_menu():
    opts = {"1":"chd_to_iso","2":"chd_to_cue","3":"chd_to_gdi","4":"iso_to_chd","5":"cue_to_chd","6":"gdi_to_chd"}
    for k,v in opts.items(): print(f"[{k}] {v}")
    print("─"*50)
    fmt = opts.get(input("Select format: ").strip())
    if not fmt: return print("Invalid format.")
    base_dir = "roms"
    if not os.path.isdir(base_dir): return print("Folder 'roms/' not found.")
    systems = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir,d))]
    if not systems: return print("No systems in 'roms/'.")
    for i, s in enumerate(systems,1): print(f"[{i}] {s}")
    print("─"*50)
    try: sys_choice = systems[int(input("Select system: ").strip())-1]
    except: return print("Invalid selection.")
    folder = os.path.join(base_dir, sys_choice)
    print(f"\nConverting packages in roms/{sys_choice}...")
    Converter(fmt).convert_all(folder)

def main():
    menu = {
        "1":("Update packages", lambda: Manager().update()),
        "2":("Install packages", lambda: Manager().install_from_file()),
        "3":("Uninstall packages", lambda: Manager().uninstall()),
        "4":("List Installed", lambda: Manager().list()),
        "5":("Convert files", convert_menu),
        "6":("Clean duplicate packages", lambda: Cleaner().clean()),
        "0":("Exit", exit)
    }
    while True:
        try: avail = json.load(open("packages.json"))
        except: avail = []
        a_count = len(avail)
        a_size = sum(f.get("size_bytes",0) for f in avail)
        a_sys = len({f.get("system") for f in avail})
        roms_dir = "roms"
        systems = [d for d in os.listdir(roms_dir) if os.path.isdir(os.path.join(roms_dir,d))] if os.path.isdir(roms_dir) else []
        t_games=t_size=0
        for folder in systems:
            p = os.path.join("roms", folder)
            files = [os.path.join(r, f) for r,_,fs in os.walk(p) for f in fs]
            t_games += len(files); t_size += sum(os.path.getsize(f) for f in files)
        banner = f"""
▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▖  ▗▄▖ 
▐▌ ▐▌▐▌     █  ▐▌ ▐▌▐▌ ▐▌  {t_games}/{a_count} games
▐▛▀▚▖▐▛▀▀▘  █  ▐▛▀▚▖▐▌ ▐▌  {len(systems)}/{a_sys} systems
▐▌ ▐▌▐▙▄▄▖  █  ▐▌ ▐▌▝▚▄▞▘  {Manager._fs(t_size)}/{Manager._fs(a_size)} total
        """
        print(banner); print("─"*50)
        for k,v in menu.items(): print(f"[{k}] {v[0]}")
        print("─"*50)
        act = menu.get(input("Select option: ").strip())
        print(" "*50, end="\r"); (act[1]() if act else print("Invalid option.")); input("\nPress Enter to return to menu...")

if __name__=="__main__":  main()
