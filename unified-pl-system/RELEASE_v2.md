# Release Notes - v2.0.0

We are proud to announce the release of **Unified P&L AI (v2.0)**. This release updates the platform frontend into an enterprise SaaS application, optimizes the AI Gemini models to the modern SDK, and resolves all outstanding integration lints and warnings.

---

## What's New in v2.0

### Clerk-Style Authentication
- Designed an interactive glassmorphic card for login and forgot-password pages.
- Embedded slow-moving canvas particle animations and float blur circles in the background.
- Included toggles to show/hide passwords, a real-time strength meter, and keyboard shortcuts.

### Collapsible Sidebar
- Collapsible sidebar matching Linear, utilizing CSS hover tooltips for icon-only navigation states.
- System light/dark theme switch that automatically persists preferences across sessions.
- Injected user profile summaries and live system notification counters.

### Stripe-Like Dashboard Widgets
- KPIs show trend metrics and dynamic inline SVG sparklines.
- Chart.js line charts utilize color variables from the active CSS design system theme.
- Dynamic table lists for recent anomalies and data uploads.

### Anomaly investigation & AI Copilot
- Scatter plot amount-mapping scales dynamically based on maximum amount, preventing overlapping dots.
- Panel investigations slide out as side-drawer overlays.
- Copilot chat responses support full markdown formatting, bold text, lists, and copy action buttons.

### Camunda Workflow stage
- Stages update status dynamically (completed, active, running) using pulsing active state CSS indicators.

### Under the Hood upgrades
- Upgraded deprecated `google-generativeai` to the new standard `google-genai==1.3.0` client SDK.
- Converted FastAPI startup hooks to the lifespan manager.
- Formatted all models, schemas, and routers to Pydantic V2 styles, resolving all deprecation warnings.
- 100% test coverage with automated Quality Assurance tests (Ruff, Black, Flake8).
