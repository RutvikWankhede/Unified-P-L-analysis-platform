# CURRENT_STATE.md — Protected Stable Checkpoint

> [!IMPORTANT]
> **This project contains a protected stable checkpoint.**
> **Read this file before making modifications.**

---

## 1. Checkpoint Overview
- **Checkpoint Date/Time**: 2026-09-06 01:31 IST
- **Checkpoint Directory**: [`checkpoints/checkpoint_20260906_0131/`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/checkpoints/checkpoint_20260906_0131/)
- **Full Source Backup Archive**: [`checkpoints/checkpoint_20260906_0131/project_backup.zip`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/checkpoints/checkpoint_20260906_0131/project_backup.zip) (24.34 MB, verified integrity)
- **Database Backup Snapshot**: [`checkpoints/checkpoint_20260906_0131/database_backup/`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/checkpoints/checkpoint_20260906_0131/database_backup/)
- **Canonical Seeded Dataset**: [`checkpoints/checkpoint_20260906_0131/seeded_dataset/unified_pnl_enterprise_demo.csv`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/checkpoints/checkpoint_20260906_0131/seeded_dataset/unified_pnl_enterprise_demo.csv)

---

## 2. Active Architecture
- **Active Frontend**: `unified-pl-system/frontend_v2/` (Mirrored to `frontend_v2/` via `sync_frontends.py`)
- **Active Backend**: `unified-pl-system/backend/` (FastAPI / Uvicorn on `http://127.0.0.1:8000`)
- **Active Database**: SQLite at `unified-pl-system/backend/enterprise_pl.db` (1,872 `pl_records`, 95 `anomalies`, 5,136 `recommendations`)
- **Active Seeded Dataset**: `unified_pnl_enterprise_demo.csv` (12 departments, ₹27.8 Cr Revenue, ₹19.8 Cr Expense, ₹7.99 Cr Net Profit)

---

## 3. Approved Components — DO NOT BREAK / DO NOT REVERT
1. **Global Sidebar**: Unified across all 10 pages via `shell.js` and `sidebar.css`.
2. **Revenue vs Expense vs Net Profit**: Approved and locked.
3. **Anomaly Overview**: Donut chart with High/Med/Low severity breakdown, 95 anomalies detected. Approved and locked.
4. **Department Performance**: Crisp SVG labels, distinct department colors, dynamic metric (Profit/Expense/Revenue/Margin) and range (Top 5/Top 10/All) selectors.
5. **Expense Distribution**: Donut category breakdown with metric selectors.
6. **Cash Flow Trend**: Symmetrical green/red vertical bars around baseline 0 with blue Net Flow line and top legend.
7. **Insights & Recommendations**: Live widgets with in-place expandable modal views.
8. **Smart Dataset Ingestion**: Fuzzy column normalization for multi-format CSV/XLSX imports.

---

## 4. How to Restore if Code Breaks
See complete instructions in [`checkpoints/checkpoint_20260906_0131/RESTORE_INSTRUCTIONS.md`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/checkpoints/checkpoint_20260906_0131/RESTORE_INSTRUCTIONS.md).

```powershell
# Restore all code from checkpoint archive:
& ".\unified-pl-system\venv\Scripts\python.exe" -c "import zipfile; zipfile.ZipFile('checkpoints/checkpoint_20260906_0131/project_backup.zip').extractall('.')"

# Restore database:
Copy-Item "checkpoints\checkpoint_20260906_0131\database_backup\backend_enterprise_pl.db" "unified-pl-system\backend\enterprise_pl.db" -Force

# Run verification:
& ".\unified-pl-system\venv\Scripts\python.exe" verify_all.py
```
