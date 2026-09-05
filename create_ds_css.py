import os
import re

css_content = """
:root {
  /* Layout & Grid */
  --ds-container-max: 1600px;
  --ds-grid-gap: 24px;
  
  /* Cards */
  --ds-card-padding: 32px;
  --ds-card-border-radius: 12px;
  
  /* Typography */
  --ds-font-heading: 18px;
  --ds-font-stat-large: 48px;
  --ds-font-stat-medium: 32px;
  --ds-font-label: 14px;
  
  /* Charts */
  --ds-chart-height-tall: 400px;
  --ds-chart-height-std: 320px;
  --ds-line-thickness: 4px;
}

/* Component Classes */
.ds-card {
  padding: var(--ds-card-padding) !important;
  border-radius: var(--ds-card-border-radius) !important;
  background: white;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.ds-heading { font-size: var(--ds-font-heading) !important; font-weight: 700; color: #1e293b; margin-bottom: 16px;}
.ds-stat { font-size: var(--ds-font-stat-medium) !important; font-weight: 700; color: #0f172a;}
.ds-stat-lg { font-size: var(--ds-font-stat-large) !important; font-weight: 700; color: #0f172a;}
.ds-label { font-size: var(--ds-font-label) !important; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;}
"""

with open(r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2\css\design-system.css", "w") as f:
    f.write(css_content)

print("design-system.css written")
