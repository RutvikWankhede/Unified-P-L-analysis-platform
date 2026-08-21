import os
import re

out_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2"

id_mapping = {
    '?5.32 Cr': 'kpi-total-revenue',
    '?3.11 Cr': 'kpi-total-expense',
    '?2.21 Cr': 'kpi-net-profit',
    '?2.46 Cr': 'kpi-forecasted-profit',
}

for filename in os.listdir(out_dir):
    if not filename.endswith('.html'): continue
    filepath = os.path.join(out_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # Inject KPIs based on known dummy values
    for val, ID in id_mapping.items():
        # Look for <p class="...">VAL</p> or <span class="...">VAL</span>
        # We can just replace the specific <...>{val}</...> with <... id="{ID}">{val}</...>
        html = re.sub(
            fr'(<(?:p|span|div|h\d)[^>]*)>(?:\s*){re.escape(val)}(?:\s*)</',
            fr'\1 id="{ID}">{val}</',
            html
        )
        
    # Inject Health Score
    html = re.sub(
        r'(<(?:p|span|div)[^>]*)>\s*92\s*(<span[^>]*>/100</span>)',
        r'\1 id="kpi-health-score">92 \2',
        html
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
        
print("Generic ID injection complete.")
