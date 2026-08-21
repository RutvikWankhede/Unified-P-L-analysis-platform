# Known Issues & Runbook

This document tracks known recurring failure modes in this project's backend to avoid rediscovering them from scratch. **Check this FIRST before debugging a "backend down" or "connection error" issue.**

## Pre-Debugging Checklist
1. Check if the process is running on port 8000: `netstat -ano | findstr ":8000"`
2. Check `backend.log` and look for the specific startup steps (Step 1/3, Step 2/3, Step 3/3).
3. If it hangs on cache warmup or DB creation, suspect a stale SQLite `.db-wal` lock.

## Known Failure Modes

### 1. `asyncio.wait_for` Orphaned Threads (Crash-Loop)
**Symptom**: Backend appears to start, but hangs indefinitely during cache warmup or database initialization, eventually throwing timeout errors or causing subsequent requests to fail with database lock errors.
**Root Cause**: Wrapping `asyncio.to_thread` database calls in `asyncio.wait_for`. If the timeout is reached, `wait_for` cancels the awaitable but the thread continues executing in the background, permanently holding onto the SQLite database lock.
**Fix Applied**: Removed all `asyncio.wait_for` wrappers around threaded DB calls in `main.py`'s startup routines. If they block, they should be allowed to finish or explicitly fail, but never orphaned.

### 2. SQLite WAL Lock Startup Hang
**Symptom**: `python run.py` takes a very long time to start or hangs completely before listening on the port.
**Root Cause**: Ungraceful shutdowns leave stale `.db-wal` and `.db-shm` lock files behind. Upon next startup, SQLite tries to reconcile these or gets stuck waiting for a lock that is held by a phantom process.
**Fix Applied**: Implemented cleanup scripts and ensured graceful exit handlers. When encountering this, check for stray Python processes and manually delete `.db-wal` files if the DB is closed.

### 3. Frontend Cascading Rendering Crashes
**Symptom**: Clicking a simple filter (like Quarterly) blanks the entire dashboard and hides all widgets.
**Root Cause**: Independent chart rendering routines (e.g. `updateKPIs`, `updateCharts`) were placed sequentially in a Promise chain without `try/catch` boundaries. If one failed (due to missing data or bad API response), it threw a synchronous TypeError that halted the rest of the widgets from rendering.
**Fix Applied**: Wrapped individual chart/widget updates in `try/catch` blocks within the `fetchDashboardData()` pipeline, isolating errors so one broken chart doesn't break the whole dashboard.
