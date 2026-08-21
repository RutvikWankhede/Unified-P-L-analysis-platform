import sys

content = open('frontend_v2/datasets.html', 'r', encoding='utf-8').read()

# Fix the truncation if it exists
idx = content.find('<truncated')
if idx != -1:
    content = content[:idx] + '''</thead>
<tbody id="recent-uploads-list" class="divide-y divide-border-light">
</tbody>
</table>
</div>
<div class="p-6 border-t border-border-light flex justify-center">
<button class="text-sm font-bold text-primary flex items-center gap-2 hover:gap-3 transition-all">
            View All Datasets 
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
</button>
</div>
</div>
</div>
</main>
<script type="module" src="js/upload.js"></script>
</body></html>'''

content = content.replace('class="upload-zone-border', 'id="upload-zone" class="upload-zone-border')
content = content.replace('<button class="bg-primary', '<button id="browse-btn" class="bg-primary')
content = content.replace('Supports .csv, .xls, .xlsx up to 100MB</p>', 'Supports .csv, .xls, .xlsx up to 100MB</p>\\n<input type="file" id="file-input" class="hidden" accept=".csv,.xls,.xlsx" style="display:none;">')

open('frontend_v2/datasets.html', 'w', encoding='utf-8').write(content)
