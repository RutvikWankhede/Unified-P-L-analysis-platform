# API Coverage Matrix

## Overview
All frontend modules have been audited and wired to backend endpoints using the unified `api.js` client.

## Endpoints Mapped

| Module | Features | Status | Endpoint |
|---|---|---|---|
| Dashboard | KPIs, Trends, Alerts | 100% | `/api/v1/dashboard/summary` |
| Departments | Financials, Peer Ranking | 100% | `/api/v1/departments/*` |
| Forecast | RMSE, Confidence Bands | 100% | `/api/v1/forecast/models` |
| Anomalies | Risk Scores, Workflows | 100% | `/api/v1/anomalies/` |
| Reports | Export PDF/Excel/PPT | 100% | `/api/v1/reports/generate` |
| Workflow | Live Timelines, BPMN | 100% | `/api/v1/workflow/status` |
| AI Copilot | Streaming, Markdown, Citation | 100% | `/api/v1/copilot/chat` |
| Notifications | Real-time WS, Grouping | 100% | `/api/v1/notifications/` |
| Audit Trail | JSON Diff, Immutable Logs | 100% | `/api/v1/audit/logs` |

## Exceptions
None. 0 mock datasets remain. All hardcoded arrays, demo charts, and random number generators have been completely purged from the frontend.
