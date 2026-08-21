import os
import re

out_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2"

for root, dirs, files in os.walk(out_dir):
    for filename in files:
        if not filename.endswith('.html'):
            continue
        filepath = os.path.join(root, filename)
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        def fix_path_d(match):
            d_val = match.group(2)
            # Fix space after minus sign (e.g., "- 6" -> "-6", "7- 7" -> "7-7")
            d_val = re.sub(r'-\s+(\d+)', r'-\1', d_val)
            # Fix space after letter command if any (e.g., "v- 2" -> "v-2", "l- 6" -> "l-6")
            # The pattern above already handles "- 2" and "- 6"
            return f'<path{match.group(1)}d="{d_val}"'

        fixed_content = re.sub(r'<path([^>]*?)d="([^"]*?)"', fix_path_d, content)
        
        if fixed_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"Fixed SVG spaces in {filename}")
