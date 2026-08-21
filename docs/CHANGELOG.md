# Changelog

## [2.0.0] - Enterprise Production Release

### Added
- **Global Search:** `Ctrl+K` support with Natural Language query understanding.
- **Executive Dashboard:** Top-level metrics and Board-ready reporting views.
- **AI Copilot V2:** Added markdown parsing, citation tracking, and inline action buttons (copy, export).
- **Audit Center:** Converted basic tables to detailed event timeline with JSON Before/After Diff viewer.
- **Workflow Heatmap:** Live timeline tracing for BPMN executions with incident management (retry/cancel).
- **Enterprise Reporting:** Report builder upgraded to support branding, watermarking, scheduling, and distribution lists.
- **Enterprise KPIs:** Added sparklines, AI insights, and target progression bars to the main dashboard.

### Changed
- Refactored entire frontend to eliminate duplicated `sidebar.html` logic.
- Unified `api.js` across all modules.
- Migrated legacy `copilot.html` to `ai-copilot.html`.
- Upgraded forecast visuals with Confidence Bands and RMSE scoring.

### Removed
- **ALL mock data, hardcoded arrays, demo charts, and fake datasets.**
- Deprecated legacy UI elements that didn't align with enterprise visual language.
