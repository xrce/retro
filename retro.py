import os, json, re, shutil, subprocess, requests, zipfile, tarfile, py7zr, rarfile
from glob import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

class Cleaner:
    P = {"Europe": 3, "USA": 2, "Japan": 1}

    @staticmethod
    def _h(n):
        for u in ['B','KB','MB','GB']:
            if n < 1024: return f"{n:.2f}{u}"
            n /= 1024
        return f"{n:.2f}TB"

    @staticmethod
    def _delete(files):
        if not files: return print("No files to delete.")
        print("Listing packages...")
        for p in files: print(f":: {p}")
        total = sum(os.path.getsize(p) for p in files)
        print(f"\n{len(files)} packages selected ({Cleaner._h(total)})")
        if input("Delete? [y/N]: ").lower() != "y": return print("\nCancelled.")
        print(f"\nDeleting {len(files)} packages...")
        for i, p in enumerate(files,1):
            size = os.path.getsize(p)
            bar = "#"*int(i/len(files)*20)
            print(f":: {i}/{len(files)}  [{bar:20}]  {Cleaner._h(size)}  {os.path.basename(p)}")
            os.remove(p)
        print("\nDeletion complete.")

    @staticmethod
    def region(root="."):
        G, B, S = {}, {}, {}
        for d, dirs, fs in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith('.')]
            for f in fs:
                if not f.endswith(".zip"): continue
                m = re.findall(r"\(([^)]+)\)", f)
                if not m: continue
                r = next((x for x in m if x in Cleaner.P), None)
                if not r: continue
                b = re.split(r" *\([^)]*\)", f)[0].strip()
                k, p = (d, b), os.path.join(d,f)
                G.setdefault(k,[]).append(p)
                if Cleaner.P[r] > S.get(k,0): B[k], S[k] = p, Cleaner.P[r]
        D = [p for k in G for p in G[k] if p != B[k]]
        Cleaner._delete(D)

    @staticmethod
    def beta(root="."):
        D = []
        for d, dirs, fs in os.walk(root):
            dirs[:] = [x for x in dirs if not x.startswith('.')]
            for f in fs:
                if f.lower().endswith(".zip") and re.search(r"[\[(](proto|beta|unl)[\])]", f, re.I): D.append(os.path.join(d,f))
        Cleaner._delete(D)

class Converter:
    def __init__(self, mode="chd_to_iso"): self.mode = mode

    def convert_all(self, folder="."):
        ext = {
            "chd_to_iso":"*.chd","chd_to_cue":"*.chd","chd_to_gdi":"*.chd",
            "iso_to_chd":"*.iso","cue_to_chd":"*.cue","gdi_to_chd":"*.gdi"
        }.get(self.mode,"*.chd")
        files = sorted(glob(os.path.join(folder,ext)))
        if not files:
            print("No matching files found.")
            return
        for i,f in enumerate(files,1): self._convert(f,i,len(files))

    def _convert(self,f,i,t):
        b = os.path.splitext(f)[0]
        out = b + (".chd" if "to_chd" in self.mode else { "chd_to_iso":".iso","chd_to_cue":".cue","chd_to_gdi":".gdi" }[self.mode])
        args = ["chdman", "createcd" if "to_chd" in self.mode else "extractcd", "-i",f,"-o",out,"-f"]
        before = os.path.getsize(f)
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        after = os.path.getsize(out) if os.path.exists(out) else 0
        if after: os.remove(f)
        bar = "#"*int(i/t*20)+" "*(20-int(i/t*20))
        print(f":: {i}/{t}  [{bar}]  {self._fs(after)}/{self._fs(before)}  {os.path.basename(out)}")

    def _fs(self,n):
        for u in ['B','KB','MB','GB','TB']:
            if n < 1024: return f"{n:.2f}{u}"
            n /= 1024
        return f"{n:.2f}PB"

class Installer:
    @staticmethod
    def _ps(s):
        s = s.replace("i","").strip()
        if len(s)>=2 and s[-1].upper()=='B' and s[-2].upper() in 'KMG': s = s[:-1]
        if not s: return 0
        u, num = s[-1].upper(), s[:-1]
        try: n = float(num)
        except: return 0
        return int(n * 1024**{'K':1,'M':2,'G':3,'T':4}.get(u,0)) if u in 'KMG T' else int(n)

    @staticmethod
    def _fs(n):
        for u in ('B','KB','MB','GB','TB'):
            if n < 1024: return f"{n:.2f}{u}"
            n /= 1024
        return f"{n:.2f}PB"

    @staticmethod
    def _download(url,path):
        pos = os.path.getsize(path) if os.path.exists(path) else 0
        total = int(requests.head(url).headers.get('content-length',0))
        hdr = {'Range':f'bytes={pos}-'} if pos<total else {}
        with requests.get(url, headers=hdr, stream=True) as r, open(path, 'ab' if pos else 'wb') as f, tqdm(total=total, initial=pos, unit='B', unit_scale=True, desc="Downloading", leave=False) as p:
            for c in r.iter_content(8192):
                if c: f.write(c); p.update(len(c))
        if os.path.getsize(path) < total: raise Exception(f"Incomplete download: {path}")

    @staticmethod
    def _extract(fp,dst,ext):
        os.makedirs(dst, exist_ok=True)
        if ext=="zip":        zipfile.ZipFile(fp).extractall(dst)
        elif ext=="tar.xz":   tarfile.open(fp,"r:xz").extractall(dst)
        elif ext=="7z":       py7zr.SevenZipFile(fp, mode="r").extractall(dst)
        elif ext=="rar":      rarfile.RarFile(fp).extractall(dst)
        else: raise Exception("Unsupported archive: "+ext)

    @staticmethod
    def _get_files(url):
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
        t = BeautifulSoup(r.text,"html.parser").find(lambda tag: tag.name=="table" and (tag.get("class")=="directory-listing-table" or tag.get("id")=="list"))
        out = []
        if t and (tbody := t.find("tbody")):
            for tr in tbody.find_all("tr"):
                a = tr.find("a")
                if not a or "parent directory" in a.text.lower(): continue
                td = tr.find_all("td")[2] if t.get("class") else tr.find("td", class_="size")
                sz = td.text.strip() if td else ""
                out.append({
                    "name": a.text.strip(),
                    "link": a["href"],
                    "size_str": sz,
                    "size_bytes": Installer._ps(sz),
                    "base": url
                })
        return out

    def __init__(self, cfg="systems.json"): self.cfg, self.systems, self.files = cfg, {}, []

    def load(self):
        print("Fetching package lists... ")
        try: self.systems = json.load(open(self.cfg))
        except Exception as e:
            print("Failed to read systems.json\nError:", e)
            return False
        return True

    def fetch(self):
        def fs(sys_name):
            out = []
            fmt = [e.lower() for e in self.systems[sys_name].get("format",[])]
            for url in self.systems[sys_name].get("url",[]):
                lst = [f for f in Installer._get_files(url) if any(f["name"].lower().endswith("."+e) for e in fmt) or f["name"].lower().endswith((".zip",".7z",".tar.xz",".rar"))]
                for f in lst: f["system"]=sys_name
                sz = sum(f["size_bytes"] for f in lst)
                print(f":: Get: {url} {sys_name} ({len(lst)}) [{Installer._fs(sz)}]")
                out+=lst
            return out

        with ThreadPoolExecutor() as exe:
            for lst in exe.map(fs, self.systems): self.files+=lst
        total = sum(f["size_bytes"] for f in self.files)
        print(f"\n{len(self.files)} packages from {len(self.systems)} systems available ({Installer._fs(total)})")

    def search(self):
        terms = input("Enter search terms (keywords or exclude with '-'): ").split()
        keys = {s.lower() for s in self.systems}
        inc = {t.lower() for t in terms if t.lower() in keys}
        kw  = [t for t in terms if t.lower() not in keys and not t.startswith('-')]
        exc = [t[1:] for t in terms if t.startswith('-')]

        if len(terms)==2 and terms[0].lower()=="all" and terms[1].lower() in keys:
            sn = terms[1].lower()
            out = [f for f in self.files if f["system"].lower()==sn]
            print(f"\nAll packages from system '{sn}' selected.")
        else:
            out = [f for f in self.files if (not inc or f["system"].lower() in inc) and (not kw  or all(k.lower() in f["name"].lower() for k in kw)) and (not exc or not any(e.lower() in f["name"].lower() for e in exc))]
        if not out:
            print("\nNo packages to install.")
            return []
        print("\nListing packages...")
        for f in out: print(f":: {f['name']} [{f['size_str']}] ({f['system']})")
        print(f"\n{len(out)} packages selected ({Installer._fs(sum(f['size_bytes'] for f in out))})")
        return out

    def install(self, pkgs):
        if input("Install? [Y/n]: ").lower() not in ("y","yes",""): return print("\nInstallation cancelled.")
        print(f"\nInstalling {len(pkgs)} packages...")
        for i,f in enumerate(pkgs,1):
            bar="#"*int(i/len(pkgs)*20)+" "*(20-int(i/len(pkgs)*20))
            print(f":: {i}/{len(pkgs)}  [{bar}]  {f['size_str']}  {f['name']} ({f['system']})")
            url = f["base"].rstrip("/") + "/" + f["link"]
            name = f["name"].replace(" ","_")
            try: Installer._download(url,name)
            except Exception as e:
                print("Err:",e)
                continue
            dst = f["system"]
            os.makedirs(dst, exist_ok=True)
            ext = "tar.xz" if name.endswith(".tar.xz") else os.path.splitext(name)[1].lstrip(".").lower()
            if ext in [e.lower() for e in self.systems[f["system"]]["format"]]: shutil.move(name, os.path.join(dst,name))
            else:
                try:
                    Installer._extract(name,dst,ext)
                    os.remove(name)
                except Exception as e: print("Err (extract):",e)
        print("\nInstallation complete.")

    def run(self):
        if not self.load(): return
        self.fetch()
        sel = self.search()
        if sel: self.install(sel)

def convert_menu():
    opts = {
        "1":"chd_to_iso","2":"chd_to_cue","3":"chd_to_gdi",
        "4":"iso_to_chd","5":"cue_to_chd","6":"gdi_to_chd"
    }
    for k,v in opts.items(): print(f"[{k}] {v}")
    print("─"*50)
    fmt = opts.get(input("Select format: ").strip())
    if not fmt: return print("Invalid format.")
    folders = [f for f in os.listdir() if os.path.isdir(f) and not f.startswith('.')]
    if not folders: return print("No folders found.")
    for i,f in enumerate(folders,1): print(f"[{i}] {f}")
    print("─"*50)
    try: folder = folders[int(input("Select folder: ").strip())-1]
    except: return print("Invalid folder.")
    print(f"\nConverting {folder} packages...")
    Converter(fmt).convert_all(folder)

def main():
    menu = {
        "1":("Install packages", lambda: Installer().run()),
        "2":("Clean duplicate regions", Cleaner.region),
        "3":("Clean prototypes", Cleaner.beta),
        "4":("Convert files", convert_menu),
        "0":("Exit", exit)
    }
    system_folders = [f for f in os.listdir(".") if os.path.isdir(f) and not f.startswith('.')]
    total_games = total_size = 0
    for folder in system_folders:
        files = [os.path.join(r,f) for r,dirs,fs in os.walk(folder) for f in fs]
        total_games += len(files)
        total_size  += sum(os.path.getsize(f) for f in files)
    banner = f"""
▗▄▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▖  ▗▄▖ 
▐▌ ▐▌▐▌     █  ▐▌ ▐▌▐▌ ▐▌  {total_games} games
▐▛▀▚▖▐▛▀▀▘  █  ▐▛▀▚▖▐▌ ▐▌  {len(system_folders)} systems
▐▌ ▐▌▐▙▄▄▖  █  ▐▌ ▐▌▝▚▄▞▘  {Cleaner._h(total_size)} installed
    """
    while True:
        print(banner)
        print("─"*50)
        for k,v in menu.items(): print(f"[{k}] {v[0]}")
        print("─"*50)
        act = menu.get(input("Select option: ").strip())
        print()
        (act[1]() if act else print("Invalid option."))
        input("\nPress Enter to return to menu...")

if __name__ == "__main__": main()
