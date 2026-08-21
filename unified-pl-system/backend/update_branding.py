import glob
import os

frontend_dir = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2"
html_files = glob.glob(os.path.join(frontend_dir, "*.html"))

old_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="28" height="28" style="color: var(--color-accent-teal); fill: none; flex-shrink: 0;"><circle cx="50" cy="50" r="40" style="fill: currentColor; opacity: 0.15;" /><path d="M 25 35 L 25 65 A 25 25 0 0 0 75 65 L 75 45 M 55 45 L 75 45 L 75 35 L 55 35 Z" style="stroke: currentColor; stroke-width: 8; stroke-linecap: round; stroke-linejoin: round;" /></svg>'
new_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" class="premium-logo" width="28" height="28" style="fill: none; stroke: currentColor; stroke-width: 8; stroke-linecap: round; stroke-linejoin: round; color: var(--color-accent-teal); flex-shrink: 0;"><path d="M 20 70 L 45 45 L 60 55 L 85 20 M 20 30 L 45 55 L 60 45 L 85 80" style="opacity: 0.85;"/><circle cx="85" cy="20" r="6" style="fill: currentColor;"/></svg>'

for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    updated = content
    # Replace the old SVG logo
    if old_svg in updated:
        updated = updated.replace(old_svg, new_svg)

    # Replace titles/headers like "P&L AI" or "Unified AI" with "Unified P&L"
    updated = updated.replace("P&L AI", "Unified P&L")
    updated = updated.replace("Unified AI", "Unified P&L")

    if updated != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"Updated branding in: {os.path.basename(file_path)}")
