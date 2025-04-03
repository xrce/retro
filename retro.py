import os, json, requests, zipfile, shutil, tarfile, py7zr, rarfile
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

def parse_size(s):
    s = s.replace("i", "").strip()
    if s[-1].upper()=='B' and s[-2].upper() in 'KMG': s = s[:-1]
    try: num = float(s[:-1])
    except: return 0
    u = s[-1].upper()
    return int(num*1024) if u=='K' else int(num*1024**2) if u=='M' else int(num*1024**3) if u=='G' else int(num)

def format_size(n):
    for u in ['B','KB','MB','GB','TB']:
        if n < 1024: return f"{n:.2f}{u}"
        n /= 1024
    return f"{n:.2f}PB"

def download(url, file):
    pos = os.path.getsize(file) if os.path.exists(file) else 0
    total = int(requests.head(url).headers.get('content-length', 0))
    headers = {'Range': f'bytes={pos}-'} if pos < total else {}
    with requests.get(url, headers=headers, stream=True) as r, open(file, 'ab' if pos else 'wb') as f, tqdm(total=total, initial=pos, unit='B', unit_scale=True, desc="Downloading", leave=False) as pbar:
        for chunk in r.iter_content(8192):
            if chunk: f.write(chunk); pbar.update(len(chunk))
    if os.path.getsize(file) < total: raise Exception(f"Incomplete download: {file}")

def extract(fp, dest, ext):
    os.makedirs(dest, exist_ok=True)
    if ext=="zip": zipfile.ZipFile(fp).extractall(dest)
    elif ext=="tar.xz": tarfile.open(fp, "r:xz").extractall(dest)
    elif ext=="7z": py7zr.SevenZipFile(fp, mode="r").extractall(dest)
    elif ext=="rar": rarfile.RarFile(fp).extractall(dest)
    else: raise Exception("Unsupported archive: " + ext)

def get_files(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser"); files = []
    table = soup.find("table", class_="directory-listing-table") or soup.find("table", id="list")
    if table:
        for row in table.find("tbody").find_all("tr"):
            a = row.find("a")
            if not a or "parent directory" in a.get_text().lower(): continue
            size_td = row.find_all("td")[2] if table.get("class") else row.find("td", class_="size")
            size_str = size_td.get_text().strip() if size_td else ""
            files.append({"name": a.get_text().strip(), "link": a["href"], "size_str": size_str,
                          "size_bytes": parse_size(size_str), "base": url})
    return files

def fetch_system(system, sys_data):
    files, urls = [], sys_data.get("url", [])
    if not urls: return []
    valid_exts = [fmt.lower() for fmt in sys_data.get("format", [])]
    for url in urls:
        fs = [f for f in get_files(url) if any(f["name"].lower().endswith("."+fmt) for fmt in valid_exts) or f["name"].lower().endswith((".zip",".7z",".tar.xz",".rar"))]
        for f in fs: f["system"] = system
        print(f":: Get: {url} {system} ({len(fs)}) [{format_size(sum(f['size_bytes'] for f in fs))}]")
        files.extend(fs)
    return files

def main():
    print("Fetching package lists... ")
    try:
        with open("systems.json", "r") as f: systems = json.load(f)
    except Exception as e:
        print("Failed to read systems.json\nError:", e); return

    all_files = []
    with ThreadPoolExecutor() as executor:
        results = executor.map(lambda s: fetch_system(s, systems[s]), systems.keys())
    for res in results: all_files.extend(res)
    print(f"\n{len(all_files)} packages from {len(systems)} systems available ({format_size(sum(f['size_bytes'] for f in all_files))})")

    ui = input("Enter search terms (keywords or exclude with '-'): ").split()
    sys_keys = {s.lower() for s in systems.keys()}
    sys_filter = {t.lower() for t in ui if t.lower() in sys_keys}
    keywords = [t for t in ui if t.lower() not in sys_keys and not t.startswith('-')]
    excludes = [t[1:] for t in ui if t.startswith('-')]
    
    filtered = [f for f in all_files if
                (not sys_filter or f["system"].lower() in sys_filter) and
                (not keywords or all(kw.lower() in f["name"].lower() for kw in keywords)) and
                (not excludes or not any(ex.lower() in f["name"].lower() for ex in excludes))]
    if not filtered:
        print("\nNo packages to install."); return

    print("\nListing packages...")
    for f in filtered:
        print(f":: {f['name']} [{f['size_str']}] ({f['system']})")
    print(f"\n{len(filtered)} packages selected ({format_size(sum(f['size_bytes'] for f in filtered))})")
    if input("Install? [Y/n]: ").lower() not in ["y", "yes", ""]: 
        print("\nInstallation cancelled."); return

    print(f"\nInstalling {len(filtered)} packages...")
    for i, f in enumerate(filtered, 1):
        pb = "#" * int(i/len(filtered)*20) + " " * (20 - int(i/len(filtered)*20))
        print(f":: {i}/{len(filtered)}  [{pb}]  {f['size_str']}  {f['name']} ({f['system']})")
        file_url = f["base"].rstrip("/") + "/" + f["link"]
        local = f["name"].replace(" ", "_")
        try: download(file_url, local)
        except Exception as e: print("Err:", e); continue
        dest = os.path.join(f["system"], os.path.splitext(local)[0])
        os.makedirs(dest, exist_ok=True)
        ext = "tar.xz" if local.endswith(".tar.xz") else os.path.splitext(local)[1].lstrip(".").lower()
        if ext in [fmt.lower() for fmt in systems[f["system"]]["format"]]:
            shutil.move(local, os.path.join(dest, local))
        elif ext in ("zip", "7z", "tar.xz", "rar"):
            try: extract(local, dest, ext)
            except Exception as e: print("Err (extract):", e); continue
            os.remove(local)
    print("\nInstallation complete.")

if __name__=="__main__": main()