# Changelog

All notable changes to the Unified P&L AI platform will be documented in this file.

## [2.0.0] - 2026-06-30

### Added
- **Dynamic Particles Canvas**: Added Clerk-style floating particle canvases to `index.html` and `forgot-password.html`.
- **Password Security Enhancements**: Integrated a password strength meter, show/hide password toggle, and escape shortcuts on recovery and authentication pages.
- **Dynamic Sparklines**: Custom SVG sparkline indicators added to all main dashboard KPI metric cards.
- **Adaptive Scatter Plot**: Configured automatic axis scaling in the Anomaly Explorer timeline based on max amount to prevent layout bunching.
- **Workflow State Animation**: Added CSS pulse animation keyframes to highlight the active steps in the BPMN workflow progress view.
- **Markdown Response Parsing**: Configured inline styling and multi-line markdown rendering support inside the Copilot chat container.

### Changed
- **google-genai SDK Migration**: Replaced deprecated `google-generativeai` imports with the modern `google-genai==1.3.0` API and initialized `Client` models.
- **Theme Color Bindings**: Redesigned all charts (Chart.js) to load colors dynamically from design system CSS variables instead of hardcoding.
- **Collapsible Tooltips**: Upgraded the sidebar to support auto-tooltips on collapsible states using native title elements and DOM dataset properties.

### Fixed
- **Query Selector Syntax Error**: Resolved `:contains()` syntax error in the jQuery-style query selectors in `ui.js`.
- **FastAPI Lifespan Manager**: Migrated backend start hooks to lifespan callbacks.
- **Pydantic V2 Config dict**: Updated configuration settings schemas to resolve deprecation warnings.
- **Alembic Imports Lint**: Added `# noqa: E402` to `env.py` to fix module-level import warnings.
