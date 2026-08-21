import json

transcript_path = r"C:\Users\HP\.gemini\antigravity-ide\brain\703335a6-deac-4bdc-8cca-f189d71e467e\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        try:
            data = json.loads(line)
            if data.get('type') == 'USER_INPUT':
                content = data.get('content', '')
                print(f"Line {i}, Step {data.get('step_index')}, USER_INPUT length: {len(content)}")
                if '==Start of PDF==' in content:
                    print(f" -> FOUND '==Start of PDF==' in Step {data.get('step_index')}")
        except Exception as e:
            pass
