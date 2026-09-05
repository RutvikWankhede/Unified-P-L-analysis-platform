import sys

with open("backend.log", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
    print("--- LAST 50 LINES OF BACKEND.LOG ---")
    for l in lines[-50:]:
        safe_line = l.rstrip().encode("ascii", "replace").decode("ascii")
        print(safe_line)
