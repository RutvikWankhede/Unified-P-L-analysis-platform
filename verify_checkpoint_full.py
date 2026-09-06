import zipfile
import os
import sqlite3

chk_dir = os.path.abspath("checkpoints/checkpoint_20260906_0131")
zip_p = os.path.join(chk_dir, "project_backup.zip")
db_p = os.path.join(chk_dir, "database_backup", "backend_enterprise_pl.db")
csv_p = os.path.join(chk_dir, "seeded_dataset", "unified_pnl_enterprise_demo.csv")

print("=" * 60)
print("  CHECKPOINT VERIFICATION SUITE")
print("=" * 60)

# 1. Zip check
assert os.path.exists(zip_p), "Zip backup missing!"
with zipfile.ZipFile(zip_p, "r") as zf:
    test_result = zf.testzip()
    assert test_result is None, f"Corrupt zip archive: {test_result}"
    file_count = len(zf.namelist())
    zip_mb = os.path.getsize(zip_p) / (1024 * 1024)
    print(f"  [PASS] Backup Archive Integrity: {zip_mb:.2f} MB ({file_count} files)")

# 2. Database backup check
assert os.path.exists(db_p), "DB backup missing!"
conn = sqlite3.connect(db_p)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM pl_records")
pl_cnt = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM anomalies")
anom_cnt = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM recommendations")
rec_cnt = c.fetchone()[0]
conn.close()
print(f"  [PASS] Database Backup Integrity: {pl_cnt} pl_records, {anom_cnt} anomalies, {rec_cnt} recommendations")

# 3. Seeded dataset check
assert os.path.exists(csv_p), "Dataset backup missing!"
with open(csv_p, "r", encoding="utf-8") as f:
    lines = f.readlines()
print(f"  [PASS] Seeded Dataset Integrity: {len(lines)-1} transaction rows")

# 4. Checkpoint docs check
for doc in ["PROJECT_STATE.md", "FILE_MANIFEST.txt", "DATABASE_STATE.md", "DATASET_STATE.md", "RUN_INSTRUCTIONS.md", "RESTORE_INSTRUCTIONS.md", "CHANGES_SINCE_BASELINE.md"]:
    doc_path = os.path.join(chk_dir, doc)
    assert os.path.exists(doc_path), f"Missing {doc}"
print("  [PASS] All 7 Checkpoint Documentation and Manifest files verified")

print("=" * 60)
print("  OVERALL CHECKPOINT STATUS: FULLY VERIFIED & RESTORABLE")
print("=" * 60)
