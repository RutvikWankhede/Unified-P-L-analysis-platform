import os
import shutil
import filecmp

src_dir = r"unified-pl-system\frontend_v2"
dst_dirs = [
    r"frontend_v2",
    r"unified-pl-system_reconstructed\frontend_v2"
]

for dst in dst_dirs:
    if os.path.exists(dst):
        for root, dirs, files in os.walk(src_dir):
            rel_dir = os.path.relpath(root, src_dir)
            target_dir = os.path.join(dst, rel_dir)
            os.makedirs(target_dir, exist_ok=True)
            for f in files:
                sf = os.path.join(root, f)
                tf = os.path.join(target_dir, f)
                shutil.copy2(sf, tf)
        print(f"Synchronized {src_dir} -> {dst}")
