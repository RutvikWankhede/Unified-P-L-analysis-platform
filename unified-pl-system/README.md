# Unified P&L AI Financial Intelligence Platform (v2.0)

An enterprise-grade SaaS platform for financial analytics, real-time anomaly detection, forecasting, and AI-driven explanations. Designed with modern light/dark themes, glassmorphism, responsive desktop/tablet interfaces, and advanced RAG-based copilot assistance.

## Technology Stack
- **Backend**: FastAPI (Python 3.13), SQLAlchemy, PostgreSQL, Alembic migrations.
- **AI/ML Engine**: Scikit-Learn (Isolation Forest), google-genai SDK (`gemini-2.5-flash`).
- **Frontend**: Vanilla HTML5, CSS3, JavaScript, Chart.js.
- **Infrastructure**: Docker, docker-compose, optimized configs for Render & Vercel.

---

## Features

### 1. High-Fidelity UI/UX SaaS Redesign
- **Clerk-like Authentication**: Glassmorphic login cards, floating canvas-based ambient particles, show/hide password toggles, real-time password strength meters, and keyboard shortcuts.
- **Linear-like Sidebar**: Collapsible navigation with automatic title tooltips, a system theme toggle (automatic/manual dark/light persistence), a persistent notification badge, and a profile info section.
- **Stripe-like Dashboard**: Responsive KPI cards with custom inline SVG sparklines, metrics, interactive multi-axis Chart.js line charts, and recent activity logs.
- **Perplexity-like Copilot Chat**: Streaming layout with typing indicators, suggested prompt chips, conversation thread list, markdown parser for code blocks, and a one-click copy utility.

### 2. Custom Business Intelligence Sections
- **Document Ingestion**: Drag-and-drop CSV validation, quality scoring, and neural schema mapping suggestions.
- **Real-Time Anomaly Explorer**: Timeline graph, dynamic scatter plot mapping amount vs. anomaly score with adaptive axis scaling, severity badge filters, and a slide-drawer investigation panel.
- **Forecast & What-If Scenarios**: Confidence bounds visualizer, algorithms (Holt-Winters/ARIMA) toggling, and interactive sliders for real-time scenario simulation.
- **Workflow & BPMN Orchestration**: BPMN workflow stage visualizations with pulsing active status indicators, retry control hooks, and logs.

---

## Quickstart

### Local Setup

1. **Clone & Setup Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

2. **Install Backend Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Database Configuration**:
   Create a `.env` file in the `backend/` directory:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/unified_pl
   GEMINI_API_KEY=your_gemini_api_key_here
   SECRET_KEY=your_jwt_secret_key_here
   ```

4. **Migrations & Seed Data**:
   ```bash
   cd backend
   alembic upgrade head
   python seed.py
   ```

5. **Start Dev Server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

6. **Serve Frontend**:
   Simply open `frontend_v2/index.html` in your browser, or serve it using any local static web server (e.g. `npx serve frontend_v2` or Live Server).

---

## Verification & Testing

The backend includes a comprehensive suite of unit and integration tests:

```bash
# Run backend tests
python -m pytest

# Run style quality checks
ruff check .
black --check .
flake8 . --exclude=venv,migration
```

---

## Release Documentation
Detailed release assets and deployment instructions are stored in the following project files:
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deploying backend to Render and frontend to Vercel.
- [CHANGELOG.md](CHANGELOG.md) - History of changes, bug fixes, and visual upgrades.
- [FINAL_QA_REPORT.md](FINAL_QA_REPORT.md) - Complete functionality checklist.
- [PRODUCTION_READINESS_REPORT.md](PRODUCTION_READINESS_REPORT.md) - Scaling details, security audits, and index optimization.
- [RELEASE_v2.md](RELEASE_v2.md) - Final release notes for stakeholders.
