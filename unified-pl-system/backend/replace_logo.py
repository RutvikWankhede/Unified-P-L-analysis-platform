import glob
import os

frontend_dir = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2"
html_files = glob.glob(os.path.join(frontend_dir, "*.html"))

target_old = (
    '<span class="material-symbols-outlined" style="font-size: 28px;">analytics</span>'
)
new_logo = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="28" height="28" style="color: var(--color-accent-teal); fill: none; flex-shrink: 0;"><circle cx="50" cy="50" r="40" style="fill: currentColor; opacity: 0.15;" /><path d="M 25 35 L 25 65 A 25 25 0 0 0 75 65 L 75 45 M 55 45 L 75 45 L 75 35 L 55 35 Z" style="stroke: currentColor; stroke-width: 8; stroke-linecap: round; stroke-linejoin: round;" /></svg>'

for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if target_old in content:
        updated = content.replace(target_old, new_logo)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"Updated logo in: {os.path.basename(file_path)}")
