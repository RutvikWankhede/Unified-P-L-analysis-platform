import os
import re

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend_v2"))

print(f"Scanning HTML files in {FRONTEND_DIR}...")

html_files = [f for f in os.listdir(FRONTEND_DIR) if f.endswith(".html")]

for filename in html_files:
    path = os.path.join(FRONTEND_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    modified = False

    # 1. Insert theme.js if not present
    if "theme.js" not in content and filename not in ["index.html"]:
        # Find head and insert
        head_match = re.search(r"<head>", content, re.IGNORECASE)
        if head_match:
            pos = head_match.end()
            content = content[:pos] + '\n  <script src="js/theme.js"></script>' + content[pos:]
            modified = True
            print(f"  Inserted theme.js into {filename}")

    # 2. Add darkMode: 'class' to tailwind.config
    if "tailwind.config" in content and "darkMode:" not in content:
        # Find tailwind.config = {
        config_match = re.search(r"tailwind\.config\s*=\s*\{", content)
        if config_match:
            pos = config_match.end()
            content = content[:pos] + "\n      darkMode: 'class'," + content[pos:]
            modified = True
            print(f"  Added darkMode: 'class' to tailwind.config in {filename}")

    if modified:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

print("HTML patching complete!")
