import os
import glob

frontend_dir = 'c:/Users/HP/.gemini/antigravity-ide/scratch/P&L system/frontend_v2'

material_link = '<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">'

for html_file in glob.glob(os.path.join(frontend_dir, '*.html')):
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'Material+Symbols+Outlined' not in content and '<head>' in content:
        content = content.replace('<head>', '<head>\n' + material_link + '\n')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed {html_file}')

for new_file in ['dataset-quality.html', 'financial-health.html', 'analytics.html']:
    path = os.path.join(frontend_dir, new_file)
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'<!DOCTYPE html>\n<html lang="en">\n<head>\n{material_link}\n<title>{new_file}</title>\n</head>\n<body>\n<h1>{new_file}</h1>\n</body>\n</html>')
        print(f'Created {path}')
