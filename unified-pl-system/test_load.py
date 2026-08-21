import sys
import os

sys.path.append('c:\\Users\\HP\\.gemini\\antigravity-ide\\scratch\\P&L system\\unified-pl-system\\backend')
from services.pl_service import load_file_to_dataframe

with open('c:\\Users\\HP\\.gemini\\antigravity-ide\\scratch\\P&L system\\unified-pl-system\\backend\\demo_dataset.csv', 'rb') as f:
    content = f.read()

df = load_file_to_dataframe(content, "demo_dataset.csv")
print(df.head())
print(df.columns.tolist())
