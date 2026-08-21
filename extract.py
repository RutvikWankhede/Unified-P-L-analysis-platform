import json
import os
import re

transcript_path = r"C:\Users\HP\.gemini\antigravity-ide\brain\aadd4640-369e-4200-b28b-b217ba6bbd22\.system_generated\logs\transcript_full.jsonl"
stitch_dir = "stitch_reference"

if not os.path.exists(stitch_dir):
    os.makedirs(stitch_dir)

pdf_content = ""

# Parse the transcript to find the PDF content
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            entry = json.loads(line)
            if entry.get("type") == "USER_INPUT" and "==Start of PDF==" in entry.get("content", ""):
                content = entry["content"]
                start = content.find("==Start of PDF==")
                end = content.find("==End of PDF==")
                if start != -1 and end != -1:
                    pdf_content = content[start:end]
                    break
        except json.JSONDecodeError:
            pass

if not pdf_content:
    print("Could not find PDF content in transcript.")
    exit(1)

# Clean up OCR artifacts like "==Start of OCR for page X=="
clean_lines = []
for line in pdf_content.splitlines():
    if line.startswith("==Start of") or line.startswith("==End of") or line.startswith("==Screenshot"):
        continue
    clean_lines.append(line)

clean_html = "\n".join(clean_lines)

# Split by HTML structure
# Find every occurrence of <!DOCTYPE html>
splits = clean_html.split("<!DOCTYPE html>")
if len(splits) > 1:
    # First split is before the first doctype, usually just empty or leading comments
    header = splits[0]
    for i in range(1, len(splits)):
        part = "<!DOCTYPE html>" + splits[i]
        
        # Try to extract the page title
        title_match = re.search(r'<title>(.*?)</title>', part)
        title = title_match.group(1) if title_match else f"page_{i}"
        
        filename = "unknown.html"
        if "Dashboard" in title:
            filename = "dashboard.html"
        elif "Upload" in title or "Datasets" in title:
            filename = "upload.html" # Also could be datasets.html, we'll name it upload.html
        elif "Audit" in title:
            filename = "audit.html"
        elif "Reports" in title:
            filename = "reports.html"
        elif "Copilot" in title:
            filename = "ai-copilot.html"
        elif "Forecast" in title:
            filename = "forecast.html"
        elif "Workflow" in title:
            filename = "workflow.html"
        elif "Anomaly" in title:
            filename = "anomaly.html"
        elif "Department Analysis" in title:
            filename = "departments.html"
        elif "Login" in title:
            filename = "login.html"
        
        # Strip trailing newlines or extra text after </html>
        end_idx = part.rfind("</html>")
        if end_idx != -1:
            part = part[:end_idx+7]
            
        with open(os.path.join(stitch_dir, filename), "w", encoding="utf-8") as out_f:
            # Also prepend any leading comment if it belongs to this part.
            prev = splits[i-1].strip()
            if prev.rfind("<!--") != -1:
                comment = prev[prev.rfind("<!--"):]
                out_f.write(comment + "\n")
            out_f.write(part)
        print(f"Extracted {filename}")
else:
    print("No <!DOCTYPE html> found")
