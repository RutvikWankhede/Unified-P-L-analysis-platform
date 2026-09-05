import os
import sys
import zipfile
import shutil

TIMESTAMP = "20260906_0131"
CHECKPOINT_DIR = os.path.abspath(f"checkpoints/checkpoint_{TIMESTAMP}")
ROOT_DIR = os.path.abspath(".")

zip_path = os.path.join(CHECKPOINT_DIR, "project_backup.zip")
if os.path.exists(zip_path):
    try:
        os.remove(zip_path)
    except Exception:
        pass

INCLUDE_DIRS = [
    "unified-pl-system",
    "frontend_v2",
    "unified-pl-system_reconstructed",
    "docs",
    "evidence"
]

EXCLUDE_DIRS = {
    "venv", ".git", "__pycache__", "node_modules", ".pytest_cache", ".ruff_cache",
    ".idea", ".vscode", "checkpoints", "FORENSIC_RESTORE_CANDIDATES", "PRE18_CANDIDATE_RESTORE_2026-08-21",
    "postgres", "postgres.zip", ".tempmediaStorage"
}

EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".log", ".tmp"}

print("Creating fast, complete project backup archive...")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    # 1. Add root files
    for item in os.listdir(ROOT_DIR):
        item_path = os.path.join(ROOT_DIR, item)
        if os.path.isfile(item_path):
            ext = os.path.splitext(item)[1]
            if ext not in EXCLUDE_EXTS and item != "postgres.zip" and not item.endswith(".log"):
                zf.write(item_path, item)
    
    # 2. Add included directories
    for inc in INCLUDE_DIRS:
        inc_dir = os.path.join(ROOT_DIR, inc)
        if os.path.exists(inc_dir):
            for root, dirs, files in os.walk(inc_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith("venv") and not d.startswith(".tmp")]
                for file in files:
                    ext = os.path.splitext(file)[1]
                    if ext in EXCLUDE_EXTS or file.endswith(".log"):
                        continue
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, ROOT_DIR)
                    zf.write(full_p, rel_p)

size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"Archive successfully generated: {zip_path} ({size_mb:.2f} MB)")

# Verify archive
with zipfile.ZipFile(zip_path, 'r') as zf:
    corrupt = zf.testzip()
    file_count = len(zf.namelist())
    print(f"Archive verification: {'PASSED (No corruption)' if corrupt is None else 'FAILED: ' + str(corrupt)}")
    print(f"Total files archived: {file_count}")

