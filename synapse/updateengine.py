import os
import sys
import json
import tempfile
import zipfile
import shutil
import urllib.request
from pathlib import Path

REPO_ZIP_URL = "https://github.com/yusifmuradliroot/synapse-openbeta/archive/refs/heads/main.zip"

def get_site_packages_dir():
    try:
        import synapse
        return Path(synapse.__file__).parent
    except ImportError:
        for p in sys.path:
            candidate = Path(p) / "synapse"
            if candidate.exists():
                return candidate
        return None

def download_repo(tmpdir):
    zip_path = os.path.join(tmpdir, "repo.zip")
    urllib.request.urlretrieve(REPO_ZIP_URL, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmpdir)
    for d in Path(tmpdir).iterdir():
        if d.is_dir() and (d / "synapse").exists():
            return d / "synapse"
    return None

def compare_and_update():
    print("\033[33m[*] UpdateEngine: Starting file-level sync...\033[0m")
    
    target_dir = get_site_packages_dir()
    if not target_dir:
        print("\033[31m[!] Could not find installed synapse package.\033[0m")
        return False
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            print("\033[33m[*] Downloading latest from GitHub...\033[0m")
            source_dir = download_repo(tmpdir)
            if not source_dir:
                print("\033[31m[!] Failed to extract package.\033[0m")
                return False
            
            changed = []
            added = []
            removed = []
            
            source_files = list(source_dir.rglob("*.py"))
            target_files = list(target_dir.rglob("*.py"))
            
            source_map = {str(f.relative_to(source_dir)): f for f in source_files}
            target_map = {str(f.relative_to(target_dir)): f for f in target_files}
            
            for rel_path, src_file in source_map.items():
                dst_file = target_dir / rel_path
                if not dst_file.exists():
                    added.append(rel_path)
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                else:
                    src_content = src_file.read_bytes()
                    dst_content = dst_file.read_bytes()
                    if src_content != dst_content:
                        changed.append(rel_path)
                        shutil.copy2(src_file, dst_file)
            
            for rel_path in target_map:
                if rel_path not in source_map:
                    removed.append(rel_path)
                    (target_dir / rel_path).unlink()
            
            if not changed and not added and not removed:
                print("\033[32m[✓] Already up to date. No changes.\033[0m")
                return True
            
            print(f"\033[1;36m\n  UpdateEngine: Sync Results\033[0m")
            if changed:
                print("  \033[1mChanged:\033[0m")
                for f in sorted(changed):
                    print(f"    \033[33m[~] {f}\033[0m")
            if added:
                print("  \033[1mAdded:\033[0m")
                for f in sorted(added):
                    print(f"    \033[32m[+] {f}\033[0m")
            if removed:
                print("  \033[1mRemoved:\033[0m")
                for f in sorted(removed):
                    print(f"    \033[31m[-] {f}\033[0m")
            
            # Clean Python cache
            for cache_dir in target_dir.rglob("__pycache__"):
                shutil.rmtree(cache_dir, ignore_errors=True)
            
            print(f"\n\033[32m[✓] Sync complete. Run 'synapse' to use updated version.\033[0m")
            return True
            
    except Exception as e:
        print(f"\033[31m[!] UpdateEngine error: {e}\033[0m")
        return False

def full_reinstall():
    print("\033[33m[*] UpdateEngine: Full reinstall mode...\033[0m")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = download_repo(tmpdir)
            if not source_dir:
                print("\033[31m[!] Download failed.\033[0m")
                return False
            
            target_dir = get_site_packages_dir()
            if target_dir and target_dir.exists():
                shutil.rmtree(target_dir)
                print(f"\033[33m[*] Removed old installation: {target_dir}\033[0m")
            
            target_dir = None
            for p in sys.path:
                if "site-packages" in p or "dist-packages" in p:
                    candidate = Path(p)
                    if candidate.exists():
                        target_dir = candidate / "synapse"
                        break
            
            if not target_dir:
                target_dir = Path.home() / ".local" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "synapse"
            
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, target_dir)
            print(f"\033[32m[✓] Installed to: {target_dir}\033[0m")
            
            # Create entry point script
            bin_dir = Path.home() / ".local" / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            entry_script = bin_dir / "synapse"
            entry_script.write_text(f"""#!/usr/bin/env python{sys.version_info.major}
import sys
from synapse.main import main
sys.exit(main())
""")
            entry_script.chmod(0o755)
            print(f"\033[32m[✓] Entry point created: {entry_script}\033[0m")
            print("\033[32m[✓] Full reinstall complete.\033[0m")
            return True
            
    except Exception as e:
        print(f"\033[31m[!] Reinstall error: {e}\033[0m")
        return False
