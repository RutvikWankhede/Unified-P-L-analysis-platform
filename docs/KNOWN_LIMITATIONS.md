# Known Limitations

1. **Workflow Animation Complexity:** Due to constraints with rendering complex SVG animations over `bpmn.js` canvases, the workflow node pulsing relies on standard CSS classes appended manually to the shadow DOM. Some very complex BPMN diagrams might slightly misalign highlighting.
2. **Global Search Scale:** The current Ctrl+K search is extremely fast but relies on client-side mapping for static pages. Deep entity searches (like specific invoice numbers) are federated to the backend.
3. **AI Copilot Streaming Limit:** Long markdown streaming from the backend may slightly lag if the connection is slow. Typing animations are synchronized but rely on stable WebSocket chunks.
