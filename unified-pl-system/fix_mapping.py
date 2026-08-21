import re

with open('backend/routers/pl_router.py', 'r', encoding='utf-8') as f:
    txt = f.read()

# Replace schema_mapping block
pattern = r'"schema_mapping": \{\s*"overall_confidence": 100 if analysis\["confidence_ok"\] else 50,\s*"mappings": analysis\["suggested_mapping"\],\s*"detected_columns": analysis\["headers"\],\s*\},'
replacement = """            "schema_mapping": {
                "overall_confidence": 100 if analysis["confidence_ok"] else 50,
                # Flip mapping to {canonical: {mapped_to: original, confidence: X}} for frontend
                "mappings": {
                    val["mapped_to"]: {"mapped_to": orig, "confidence": val.get("confidence", 0)}
                    for orig, val in analysis["suggested_mapping"].items()
                    if val.get("mapped_to")
                },
                "detected_columns": analysis["headers"],
            },"""
txt = re.sub(pattern, replacement, txt)

with open('backend/routers/pl_router.py', 'w', encoding='utf-8') as f:
    f.write(txt)
print("Done")
