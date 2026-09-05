import glob

font_links = """
<!-- Preconnect for fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Material Symbols Outlined -->
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block" />
<style>
  .material-symbols-outlined {
    font-family: 'Material Symbols Outlined', sans-serif !important;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20;
  }
</style>
"""

for f in glob.glob('*.html'):
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if 'Material+Symbols+Outlined' not in content:
            new_content = content.replace('</head>', font_links + '\n</head>')
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f"Added fonts to {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")
