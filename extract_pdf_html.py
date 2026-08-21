import json
import re
import os

transcript_path = r"C:\Users\HP\.gemini\antigravity-ide\brain\703335a6-deac-4bdc-8cca-f189d71e467e\.system_generated\logs\transcript_full.jsonl"
out_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\stitch_reference"

os.makedirs(out_dir, exist_ok=True)

with open(transcript_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

latest_user_message = ""
for line in reversed(lines):
    try:
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT' and '==Start of PDF==' in data.get('content', ''):
            latest_user_message = data['content']
            break
    except Exception as e:
        print("Error parsing line:", e)

print("Length of latest_user_message:", len(latest_user_message))

ocr_blocks = []
pattern = re.compile(r"==Start of OCR for page \d+==(.*?)==End of OCR for page \d+==", re.DOTALL)
for match in pattern.finditer(latest_user_message):
    ocr_blocks.append(match.group(1))

print("Found OCR blocks:", len(ocr_blocks))

full_text = "\n".join(ocr_blocks)

parts = full_text.split("<!DOCTYPE html>")
print("Found parts splitting by doctype:", len(parts))

files = {}
for i, part in enumerate(parts):
    if i == 0:
        continue
    content = "<!DOCTYPE html>" + part
    
    end_idx = content.find("</html>")
    if end_idx != -1:
        content = content[:end_idx + 7]
    
    header = content[:250].replace('\n', ' ')
    
    if "Dashboard" in header and "Unified P&amp;L" in header:
        files["dashboard.html"] = content
    elif "Upload / Datasets" in header:
        files["datasets.html"] = content
    elif "Audit Trail" in header:
        files["audit.html"] = content
    elif "Reports" in header:
        files["reports.html"] = content
    elif "AI Copilot" in header:
        files["copilot.html"] = content
    elif "Forecast" in header:
        files["forecast.html"] = content
    elif "Workflow" in header:
        files["workflow.html"] = content
    elif "Anomaly Detection Dashboard" in header:
        files["anomalies.html"] = content
    elif "Department Analysis" in header:
        files["departments.html"] = content
    elif "Login" in header:
        pass
        
for name, content in files.items():
    with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as f:
        f.write(content)
        
print(f"Extracted {len(files)} files to {out_dir}")
for k in files.keys():
    print(" - " + k)
