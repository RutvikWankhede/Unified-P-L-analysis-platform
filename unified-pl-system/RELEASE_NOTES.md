# Release Notes - v1.0.0

We are proud to announce the v1.0.0 release of the **Unified P&L Analytics Platform**, a production-ready, enterprise-grade application for financial data ingestion, anomaly detection, workflow orchestration, and generative AI explanations.

## Implemented Features
1. **P&L Data Ingestion**: Bulk parse, clean, and validate financial data from CSV files. Supported by a dynamic schema system allowing customizable key-value data metadata per record.
2. **AI Anomaly Detection**: Unsupervised anomaly detection powered by Scikit-Learn's `IsolationForest` module. Automatically rates anomaly severity (High, Medium, Low) and calculates percentile ranks.
3. **Conversational AI Copilot**: Fully-integrated chat panel utilizing the Google Gemini API (`gemini-pro`) to provide context-aware responses to financial queries.
4. **AI Explanations & Recommendations**: Generates automated root-cause analysis, business impact assessments, and actionable operational mitigation tasks.
5. **Modern Glassmorphism UI**: High-fidelity dashboard built using vanilla JS and CSS variables, featuring responsive grids, Recharts data visualization, skeleton loaders, and toaster messages.
6. **Task & Workflow Orchestration**: Process definition integration prepared for Camunda engine backend synchronization.
7. **Production DevSecOps**: central logging, rate limiting (Slowapi), secure JWT tokens, role-based access control, PostgreSQL schema migrations via Alembic, Docker container orchestration, and cloud configurations for Render and Vercel.

## Known Limitations & Sandbox Notes
- **Gemini API Configuration**: Requires a valid `GEMINI_API_KEY` set in the environment variables to run AI generation. If not provided, the system gracefully falls back to mock informational guides.
- **Camunda Connection**: If a local Camunda engine (default `localhost:8080`) is unreachable, the system relies on an integrated fallback mechanism generating mock workflow tracking IDs.
- **RAG Vector Search**: In-memory database lists are utilized as context for the AI Copilot. For massive scales (e.g. millions of rows), migrating to a vectorized search index (e.g. pgvector) is recommended.

## Quick Installation & Deployment
Refer to [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions.

### Local Command Execution
```bash
# Backend Setup
cd backend
python -m venv venv
source venv/Scripts/activate # or venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Frontend Setup
# Simply host /frontend_v2 using any static server or open index.html
```

### Docker Compose Execution
```bash
docker-compose up --build -d
```
