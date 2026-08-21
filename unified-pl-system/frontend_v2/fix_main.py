import glob, re

for f in glob.glob('*.html'):
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if '<main' in content:
            new_content = re.sub(
                r'<main[^>]*>', 
                '<main id="main-content" class="ml-[260px] flex-1 min-h-screen pb-16 transition-all duration-300 overflow-x-hidden">', 
                content
            )
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f"Fixed {f}")
    except Exception as e:
        print(f"Error processing {f}: {e}")
