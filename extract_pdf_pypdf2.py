import os
import PyPDF2

pdf_path = r"C:\Users\HP\.gemini\antigravity-ide\brain\703335a6-deac-4bdc-8cca-f189d71e467e\media__1783960157696.pdf"
out_dir = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\stitch_reference"
os.makedirs(out_dir, exist_ok=True)

text = ""
with open(pdf_path, 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

parts = text.split("<!DOCTYPE html>")

files = {}
for i, part in enumerate(parts):
    if i == 0:
        continue
    content = "<!DOCTYPE html>" + part
    
    end_idx = content.find("</html>")
    if end_idx != -1:
        content = content[:end_idx + 7]
    
    header = content[:250].replace('\n', ' ')
    
    if "Upload / Datasets" in header:
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
    elif "Unified P&amp;L - AI Governance System" in header and "Upload" not in header and "Workflow" not in header:
        files["dashboard.html"] = content
    elif "Login" in header:
        pass

for name, content in files.items():
    with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Extracted {len(files)} files to {out_dir}")
for k in files.keys():
    print(" - " + k)
