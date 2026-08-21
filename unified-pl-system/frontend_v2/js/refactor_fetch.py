import re
import glob

# Files with fetch
files = ['audit_wiring.js', 'copilot_wiring.js', 'dashboard_wiring.js', 'datasets_wiring.js', 'settings_wiring.js', 'workflow_wiring.js']

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            
        if 'fetch(' not in content:
            continue
            
        # Add import if missing
        if "import { api }" not in content:
            content = "import { api } from './api.js';\n" + content
            
        # Replace simple gets: fetch('/path').then(res => res.json()).then(data =>
        # It's safer to just replace fetch( URL ).then(r=>r.json()) with api.get( URL )
        
        content = re.sub(r'fetch\((.*?)\)\s*\.then\([^)]+\s*=>\s*[^)]+\.json\(\)\)', r'api.get(\1)', content)
        
        # Datasets specific fixes where it uses await fetch
        content = re.sub(r'await fetch\((.*?),\s*\{\s*method:\s*[\'"]POST[\'"](?:,\s*body:\s*(.*?))?\s*\}\)', r'await api.post(\1, \2)', content)
        
        # Replace any remaining fetch with api.get (assuming they are GETs if no method is specified)
        # But wait, some have fetch(URL, { method: ...})
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Refactored {f}")
    except Exception as e:
        print(f"Error on {f}: {e}")
