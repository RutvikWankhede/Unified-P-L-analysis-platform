"""
Clean stale SQLite lock files and show status.
"""
import os, glob

backend_dir = r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\backend'

print("=== Backend directory files ===")
for f in os.listdir(backend_dir):
    if any(f.endswith(ext) for ext in ['.log', '.db-wal', '.db-shm', '.db']):
        path = os.path.join(backend_dir, f)
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)
        import datetime
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {f:<35} {size:>10} bytes  {mtime_str}")

print()
print("=== Cleaning stale WAL/SHM lock files ===")
cleaned = []
for pattern in ['*.db-wal', '*.db-shm']:
    for f in glob.glob(os.path.join(backend_dir, pattern)):
        try:
            os.remove(f)
            cleaned.append(f)
            print(f"  DELETED: {os.path.basename(f)}")
        except Exception as e:
            print(f"  FAILED to delete {os.path.basename(f)}: {e}")

if not cleaned:
    print("  No WAL/SHM files found.")

print("\nDone. Ready to start backend.")
