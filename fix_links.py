import os
import re

MAPPING = {
    'Dashboard': 'dashboard.html',
    'Departments': 'departments.html',
    'Upload / Datasets': 'datasets.html',
    'Forecast': 'forecast.html',
    'Anomaly Detection': 'anomalies.html',
    'AI Copilot': 'copilot.html',
    'Workflow': 'workflow.html',
    'Reports': 'reports.html',
    'Audit Trail': 'audit.html',
    'Settings': 'settings.html',
}

# Also map specific variations found in sidebars just in case
MAPPING['AI Co-pilot'] = 'copilot.html'
MAPPING['Audit'] = 'audit.html'

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    
    def replacer(match):
        a_tag = match.group(0)
        # Check from longest to shortest to avoid partial matches if any
        for key, link in sorted(MAPPING.items(), key=lambda x: -len(x[0])):
            # Basic text match inside the <a> tag
            # We strip html tags to just search the text
            text_only = re.sub(r'<[^>]+>', '', a_tag)
            if key in text_only:
                return a_tag.replace('href="#"', f'href="{link}"', 1).replace("href='#'", f"href='{link}'", 1)
        return a_tag

    # Match an anchor tag from <a to </a> non-greedy
    content = re.sub(r'<a\s+[^>]*?href=[\'"]#[\'"][^>]*>.*?</a>', replacer, content, flags=re.DOTALL | re.IGNORECASE)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    frontend_dir = 'frontend_v2'
    
    # 1. Delete redundant files
    redundant = ['department.html', 'upload.html', 'anomaly.html', 'ai-copilot.html']
    for r in redundant:
        p = os.path.join(frontend_dir, r)
        if os.path.exists(p):
            os.remove(p)
            print(f"Deleted {r}")
            
    # 2. Fix all files
    count = 0
    # Also fix partials
    partials_dir = os.path.join(frontend_dir, 'partials')
    all_files = [os.path.join(frontend_dir, f) for f in os.listdir(frontend_dir) if f.endswith('.html')]
    if os.path.exists(partials_dir):
        all_files += [os.path.join(partials_dir, f) for f in os.listdir(partials_dir) if f.endswith('.html')]
        
    for f in all_files:
        if fix_file(f):
            print(f"Fixed links in {os.path.basename(f)}")
            count += 1
                
    print(f"Fixed {count} files.")

if __name__ == '__main__':
    main()
