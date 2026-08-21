import os
import re
from pathlib import Path

# Path to the frontend directory
frontend_dir = Path(r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2")

# Read dashboard.html as the master reference
with open(frontend_dir / "dashboard.html", "r", encoding="utf-8") as f:
    dashboard_html = f.read()

# Extract parts from dashboard.html
head_match = re.search(r'<head>(.*?)</head>', dashboard_html, re.DOTALL)
sidebar_match = re.search(r'<!-- BEGIN: Sidebar -->(.*?)<!-- END: Sidebar -->', dashboard_html, re.DOTALL)
topbar_match = re.search(r'<!-- BEGIN: Top Bar -->(.*?)<!-- END: Top Bar -->', dashboard_html, re.DOTALL)
body_match = re.search(r'<body class="(.*?)">', dashboard_html)
main_match = re.search(r'<main class="(.*?)">', dashboard_html)

if not (head_match and sidebar_match and topbar_match and body_match and main_match):
    print("Could not extract all master layout components from dashboard.html")
    exit(1)

head_content = head_match.group(1).strip()
sidebar_content = sidebar_match.group(1).strip()
topbar_content = topbar_match.group(1).strip()
body_classes = body_match.group(1).strip()
main_classes = main_match.group(1).strip()

def process_file(filepath):
    print(f"Processing {filepath.name}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if already processed (has the exact sidebar class)
    if "bg-surface-container-lowest" in content and "<!-- BEGIN: Sidebar -->" in content:
        print(f"Skipping {filepath.name} (already has sidebar)")
        return

    # Extract title to preserve it
    title = "Unified P&L System"
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    if title_match:
        title = title_match.group(1)

    # Reconstruct the file
    # Try to find main content
    # If the file has a <main> tag, we extract its inside. Otherwise we just wrap body content.
    main_content = ""
    inner_main = re.search(r'<main[^>]*>(.*?)</main>', content, re.DOTALL | re.IGNORECASE)
    
    if inner_main:
        main_content = inner_main.group(1).strip()
        # Clean up existing topbars inside main if any
        main_content = re.sub(r'<div class="px-8 pt-8 pb-4.*?</div>', '', main_content, flags=re.DOTALL, count=1)
        main_content = re.sub(r'<header.*?</header>', '', main_content, flags=re.DOTALL | re.IGNORECASE)
    else:
        # If no main, try to extract body content excluding scripts
        body_content_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
        if body_content_match:
            main_content = body_content_match.group(1).strip()
            # Remove any top-level sidebars or headers to avoid duplication if we can
            main_content = re.sub(r'<div id=[\'"]sidebar-container[\'"].*?</div>', '', main_content, flags=re.IGNORECASE)
            main_content = re.sub(r'<aside.*?</aside>', '', main_content, flags=re.DOTALL | re.IGNORECASE)
            main_content = re.sub(r'<nav.*?</nav>', '', main_content, flags=re.DOTALL | re.IGNORECASE)
            main_content = re.sub(r'<header.*?</header>', '', main_content, flags=re.DOTALL | re.IGNORECASE)
        else:
            main_content = "<div>Content missing</div>"

    # Create the new HTML
    new_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
{head_content}
</head>
<body class="{body_classes}">

  <!-- BEGIN: Sidebar -->
  {sidebar_content}
  <!-- END: Sidebar -->

  <!-- BEGIN: Main Content Area -->
  <main class="{main_classes}">
    <!-- BEGIN: Top Bar -->
    {topbar_content}
    <!-- END: Top Bar -->

    <div class="px-8 space-y-8 mt-8">
      {main_content}
    </div>
  </main>
  <!-- END: Main Content Area -->

  <script type="module" src="js/{filepath.stem}.js"></script>
</body>
</html>"""

    # Replace title back
    new_html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', new_html, flags=re.IGNORECASE)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_html)

for file in frontend_dir.glob("*.html"):
    if file.name == "dashboard.html":
        continue
    process_file(file)

print("Done unifying frontend layout.")
