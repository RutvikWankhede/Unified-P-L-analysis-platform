import os
import sys
import shutil
import zipfile
import sqlite3
import json
from datetime import datetime

TIMESTAMP = "20260906_0131"
CHECKPOINT_DIR = os.path.abspath(f"checkpoints/checkpoint_{TIMESTAMP}")
ROOT_DIR = os.path.abspath(".")

os.makedirs(CHECKPOINT_DIR, exist_ok=True)
db_backup_dir = os.path.join(CHECKPOINT_DIR, "database_backup")
os.makedirs(db_backup_dir, exist_ok=True)
dataset_backup_dir = os.path.join(CHECKPOINT_DIR, "seeded_dataset")
os.makedirs(dataset_backup_dir, exist_ok=True)

print(f"Creating checkpoint in: {CHECKPOINT_DIR}")

# 1. Copy Database files and dump SQL
db1 = os.path.join(ROOT_DIR, "enterprise_pl.db")
db2 = os.path.join(ROOT_DIR, "unified-pl-system", "backend", "enterprise_pl.db")
if os.path.exists(db1):
    shutil.copy2(db1, os.path.join(db_backup_dir, "root_enterprise_pl.db"))
if os.path.exists(db2):
    shutil.copy2(db2, os.path.join(db_backup_dir, "backend_enterprise_pl.db"))
    # Also dump SQL
    conn = sqlite3.connect(db2)
    with open(os.path.join(db_backup_dir, "backend_enterprise_pl_dump.sql"), "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    conn.close()
    print("Database dumped and copied.")

# 2. Copy Seeded Dataset files
for f_name in ["unified_pnl_enterprise_demo.csv", "unified_pnl_enterprise_demo.xlsx"]:
    src = os.path.join(ROOT_DIR, f_name)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(dataset_backup_dir, f_name))
print("Seeded datasets copied.")

# 3. Create project_backup.zip
zip_path = os.path.join(CHECKPOINT_DIR, "project_backup.zip")

EXCLUDE_DIRS = {
    ".git", "__pycache__", "venv", "node_modules", ".pytest_cache", ".ruff_cache",
    ".idea", ".vscode", "checkpoints", "FORENSIC_RESTORE_CANDIDATES", "PRE18_CANDIDATE_RESTORE_2026-08-21"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".log", ".tmp"}

print(f"Archiving working project to {zip_path}...")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(ROOT_DIR):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".tmp") and not d.startswith("venv")]
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in EXCLUDE_EXTS:
                continue
            if file == "postgres.zip" or file.endswith(".log"):
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, ROOT_DIR)
            if rel_path.startswith("checkpoints") or rel_path.startswith(".git"):
                continue
            zf.write(full_path, rel_path)

zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"Backup archive created: {zip_path} ({zip_size_mb:.2f} MB)")

# Verify ZIP
with zipfile.ZipFile(zip_path, 'r') as zf:
    test_res = zf.testzip()
    namelist = zf.namelist()
    print(f"ZIP Integrity Check: {'PASSED' if test_res is None else 'FAILED: ' + str(test_res)}")
    print(f"Total files in backup archive: {len(namelist)}")

print("Done checkpoint packaging.")
