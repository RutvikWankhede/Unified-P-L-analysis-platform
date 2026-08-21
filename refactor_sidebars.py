import os
import re

FRONTEND_DIR = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2"
SIDEBAR_REGEX = re.compile(r"(\s*)<!-- Sidebar -->(?:\s*)<aside.*?<\/aside>", re.DOTALL)
SIDEBAR_REGEX_NO_COMMENT = re.compile(r"(\s*)<aside class=\"w-\[260px\].*?<\/aside>", re.DOTALL)

def refactor_sidebars():
    html_files = [f for f in os.listdir(FRONTEND_DIR) if f.endswith('.html')]
    
    # Replace sidebar in all files
    count = 0
    for filename in html_files:
        filepath = os.path.join(FRONTEND_DIR, filename)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        new_content, num_subs = SIDEBAR_REGEX.subn(r"\1<div id='sidebar-container'></div>", content)
        if num_subs == 0:
             new_content, num_subs = SIDEBAR_REGEX_NO_COMMENT.subn(r"\1<div id='sidebar-container'></div>", new_content)
             
        if num_subs > 0:
            with open(filepath, 'w', encoding='utf-8', errors='replace') as f:
                f.write(new_content)
            count += 1
            print(f"Refactored {filename}")
            
    print(f"Successfully replaced sidebar in {count} files.")

if __name__ == '__main__':
    refactor_sidebars()
