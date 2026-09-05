import os
import zipfile

p = "checkpoints/checkpoint_20260906_0131/project_backup.zip"
if os.path.exists(p):
    size = os.path.getsize(p)
    print(f"Zip exists! Size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    try:
        with zipfile.ZipFile(p, 'r') as zf:
            corrupt = zf.testzip()
            files = zf.namelist()
            print(f"Testzip check: {'ALL OK (No corruption)' if corrupt is None else 'Error: ' + str(corrupt)}")
            print(f"Archived file count: {len(files)}")
            print("Sample files:", files[:10])
    except Exception as e:
        print("Zip read error (likely still being written):", e)
else:
    print("Zip file does not exist yet.")
