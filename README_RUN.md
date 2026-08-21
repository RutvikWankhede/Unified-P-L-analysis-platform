# Unified Enterprise P&L AI Platform - Startup Guide

## How to Run

To launch the entire application, you only need one command:

```bash
python run.py
```

Alternatively, you can use the provided wrappers:
- **Windows:** Double-click `start.bat` or run `.\start.ps1`
- **Any OS:** `python start.py`

### What happens automatically?
1. The script detects your OS and virtual environment.
2. Missing Python dependencies are installed.
3. The database is checked, migrations run, and demo data is seeded (including the `admin` / `admin123` account).
4. Any zombie processes on ports `8000` or `3000` are safely terminated.
5. The FastAPI backend starts on `http://127.0.0.1:8000`.
6. The Frontend server starts on `http://127.0.0.1:3000`.
7. Health checks verify that all critical APIs are functioning.
8. Your default browser opens automatically to the login page.

### Stopping the Application
Press `CTRL+C` in the terminal where you ran the command. This will cleanly shut down both the frontend and backend servers.

### Troubleshooting
If the application fails to start or gets stuck, you can manually force kill the background servers by running:
```bash
python stop.py
```
