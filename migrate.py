import os
import re

ref_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\stitch_reference"
out_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2"

def remove_first_aside(html):
    start_idx = html.find("<aside")
    if start_idx == -1:
        return html
    
    # Find matching </aside>
    end_tag = "</aside>"
    # This is a naive search but works if there are no nested asides
    end_idx = html.find(end_tag, start_idx)
    if end_idx != -1:
        return html[:start_idx] + html[end_idx + len(end_tag):]
    return html

for filename in os.listdir(ref_dir):
    if not filename.endswith(".html"):
        continue
    
    # Exclude login
    if filename == "login.html":
        continue
        
    with open(os.path.join(ref_dir, filename), 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 1. Remove first aside
    html = remove_first_aside(html)
    
    # 2. Insert sidebar-container
    body_match = re.search(r"<body[^>]*>", html)
    if body_match:
        insert_pos = body_match.end()
        html = html[:insert_pos] + '\n<div id="sidebar-container"></div>\n' + html[insert_pos:]
    else:
        # fallback
        html = html.replace("</head>", '</head>\n<body>\n<div id="sidebar-container"></div>')
        html = html + "\n</body>"
        
    # 3. Update main margin
    html = re.sub(r'ml-\[260px\]', 'ml-[240px]', html)
    html = re.sub(r'ml-\[280px\]', 'ml-[240px]', html)
    html = re.sub(r'width:\s*260px', 'width: 240px', html)
    html = re.sub(r'width:\s*280px', 'width: 240px', html)
    html = re.sub(r'margin-left:\s*260px', 'margin-left: 240px', html)
    html = re.sub(r'margin-left:\s*280px', 'margin-left: 240px', html)
    
    # 4. Inject wiring scripts before </body>
    wiring_script = filename.replace(".html", "_wiring.js")
    
    # If the file already has some script tags at the end, that's fine.
    scripts = f"""
<script type="module" src="js/shell.js"></script>
<script src="js/{wiring_script}"></script>
</body>
"""
    html = html.replace("</body>", scripts)
    
    # Write to frontend_v2
    with open(os.path.join(out_dir, filename), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Migrated {filename}")
