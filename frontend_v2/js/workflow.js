/**
 * workflow.js - Camunda BPMN Workflow Orchestration Client
 * ========================================================
 * Powers real-time process monitoring, interactive step inspection,
 * approval decision resolution, pipeline triggering, and BPMN visualization.
 */

import { api } from './api.js';

async function initWorkflowPage() {
  let activeInstanceId = null;
  let cachedInstances = [];
  let pollInterval = null;
  let selectedStepKey = null;

  const STEP_ORDER = [
    { key: 'upload_data', name: 'Upload Data', icon: 'upload_file', service: 'Data Ingestion Service' },
    { key: 'validate_data', name: 'Validate Data', icon: 'verified', service: 'Quality & Schema Validator' },
    { key: 'process_pl', name: 'Process P&L', icon: 'calculate', service: 'P&L Metric Calculation Engine' },
    { key: 'anomaly_detection', name: 'Anomaly Detection', icon: 'crisis_alert', service: 'ML Outlier Surveillance Engine' },
    { key: 'forecast', name: 'Forecast', icon: 'trending_up', service: 'Predictive Trajectory Agent' },
    { key: 'risk_assessment', name: 'Risk Assessment', icon: 'shield', service: 'Financial Risk & Governance Agent' },
    { key: 'manager_approval', name: 'Manager Approval', icon: 'person_check', service: 'Executive Approval Task' },
    { key: 'generate_report', name: 'Generate Report', icon: 'description', service: 'Financial Reporting Service' },
  ];

  // ── 1. Fetch & Render KPIs ──────────────────────────────────────
  async function loadKpis() {
    try {
      const kpis = await api.get('/api/v1/workflow/kpis').catch(() => null);
      if (!kpis) return;
      const elActive = document.getElementById('kpi-active-wf');
      const elCompleted = document.getElementById('kpi-completed-wf');
      const elPending = document.getElementById('kpi-pending-wf');
      const elFailed = document.getElementById('kpi-failed-wf');

      if (elActive) elActive.textContent = kpis.active || 0;
      if (elCompleted) elCompleted.textContent = kpis.completed || 0;
      if (elPending) elPending.textContent = kpis.pending_approval || 0;
      if (elFailed) elFailed.textContent = kpis.failed || 0;
    } catch (e) {
      console.warn('Failed to load workflow KPIs:', e);
    }
  }

  // ── 2. Fetch & Render Instances List ────────────────────────────
  async function loadInstances(autoSelectFirst = false) {
    try {
      const list = await api.get('/api/v1/workflow/instances').catch(() => []);
      cachedInstances = Array.isArray(list) ? list : [];

      renderHistoryTable(cachedInstances);

      // Auto-select most recent or active running instance
      if (cachedInstances.length > 0) {
        if (!activeInstanceId || autoSelectFirst) {
          const runningInst = cachedInstances.find(i => i.status === 'RUNNING' || i.status === 'PENDING_APPROVAL');
          activeInstanceId = runningInst ? runningInst.process_instance_id : cachedInstances[0].process_instance_id;
        }
        await loadActiveInstanceDetails(activeInstanceId);
      }

      // Manage Polling: if any instance is running, keep polling
      const hasRunning = cachedInstances.some(i => i.status === 'RUNNING');
      if (hasRunning && !pollInterval) {
        pollInterval = setInterval(() => pollActiveState(), 1500);
      } else if (!hasRunning && pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }

    } catch (e) {
      console.warn('Failed to load workflow instances:', e);
    }
  }

  // ── 3. Load Active Instance Details ─────────────────────────────
  async function loadActiveInstanceDetails(instId) {
    if (!instId) return;
    try {
      const inst = await api.get(`/api/v1/workflow/instances/${encodeURIComponent(instId)}`).catch(() => null);
      if (!inst) return;

      activeInstanceId = inst.process_instance_id;
      renderActiveWorkflowCard(inst);
      renderStepTrack(inst);
      renderBpmnHighlighting(inst);
      renderPendingApprovalBanner(inst);

      // Auto-select currently active or failed step in inspector if none selected
      const curKey = inst.current_step || 'upload_data';
      if (!selectedStepKey || !inst.steps[selectedStepKey]) {
        selectedStepKey = inst.error_step || curKey;
      }
      renderStepInspector(inst, selectedStepKey);

    } catch (e) {
      console.warn('Failed to load instance details:', e);
    }
  }

  // ── 4. Render Active Workflow Header & Progress ─────────────────
  function renderActiveWorkflowCard(inst) {
    const titleEl = document.getElementById('active-wf-title');
    const badgeEl = document.getElementById('active-wf-status-badge');
    const startedEl = document.getElementById('active-wf-started');
    const stepNameEl = document.getElementById('active-wf-step-name');
    const durationEl = document.getElementById('active-wf-duration');
    const barEl = document.getElementById('active-wf-progress-bar');
    const textEl = document.getElementById('active-wf-progress-text');
    const actionContainer = document.getElementById('active-wf-action-btns');

    if (titleEl) titleEl.textContent = `P&L Workflow #${inst.process_instance_id.replace('pl-wf-', '')} (${inst.department})`;
    
    if (badgeEl) {
      let badgeClass = 'bg-slate-100 text-slate-700';
      if (inst.status === 'RUNNING') badgeClass = 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse';
      else if (inst.status === 'COMPLETED') badgeClass = 'bg-emerald-50 text-emerald-700 border border-emerald-200';
      else if (inst.status === 'PENDING_APPROVAL') badgeClass = 'bg-amber-50 text-amber-700 border border-amber-200';
      else if (inst.status === 'FAILED') badgeClass = 'bg-rose-50 text-rose-700 border border-rose-200';
      badgeEl.className = `px-2.5 py-0.5 rounded-full text-[10px] font-bold ${badgeClass}`;
      badgeEl.textContent = inst.status.replace('_', ' ');
    }

    const startTimeStr = inst.started_at ? new Date(inst.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';
    if (startedEl) startedEl.textContent = startTimeStr;
    if (stepNameEl) stepNameEl.textContent = inst.current_step_name || '—';
    if (durationEl) durationEl.textContent = inst.duration || '0s';

    const pct = inst.status === 'COMPLETED' ? 100 : (inst.progress || 0);
    if (barEl) barEl.style.width = `${pct}%`;
    if (textEl) textEl.textContent = `${pct}%`;

    // Action buttons inside active card
    if (actionContainer) {
      actionContainer.innerHTML = '';
      
      const viewDetailsBtn = document.createElement('button');
      viewDetailsBtn.className = 'px-2.5 py-1 rounded-md text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition cursor-pointer flex items-center gap-1';
      viewDetailsBtn.innerHTML = '<span class="material-symbols-outlined text-xs">visibility</span><span>View Details</span>';
      viewDetailsBtn.addEventListener('click', () => openWorkflowDetailsModal(inst.process_instance_id));
      actionContainer.appendChild(viewDetailsBtn);

      if (inst.status === 'RUNNING') {
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'px-2.5 py-1 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition cursor-pointer';
        cancelBtn.textContent = 'Cancel Workflow';
        cancelBtn.addEventListener('click', async () => {
          await api.post(`/api/v1/workflow/${inst.process_instance_id}/cancel`, {});
          await loadKpis();
          await loadInstances();
        });
        actionContainer.appendChild(cancelBtn);
      } else if (inst.status === 'FAILED') {
        const retryBtn = document.createElement('button');
        retryBtn.className = 'px-2.5 py-1 rounded-md text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition cursor-pointer flex items-center gap-1';
        retryBtn.innerHTML = '<span class="material-symbols-outlined text-xs">refresh</span><span>Retry</span>';
        retryBtn.addEventListener('click', async () => {
          await api.post(`/api/v1/workflow/${inst.process_instance_id}/retry`, {});
          await loadKpis();
          await loadInstances();
        });
        actionContainer.appendChild(retryBtn);
      }
    }
  }

  // ── 5. Render Horizontal Step Track ─────────────────────────────
  function renderStepTrack(inst) {
    const track = document.getElementById('workflow-steps-track');
    if (!track) return;

    const steps = inst.steps || {};
    let html = '';

    STEP_ORDER.forEach((sDef, idx) => {
      const sData = steps[sDef.key] || {};
      const status = sData.status || 'PENDING';
      const isSelected = selectedStepKey === sDef.key;

      let iconHtml = '<span class="material-symbols-outlined text-xs text-slate-400">radio_button_unchecked</span>';
      let pillClass = 'bg-white border-slate-200 text-slate-600';

      if (status === 'COMPLETED') {
        iconHtml = '<span class="material-symbols-outlined text-xs text-emerald-600 font-bold">check_circle</span>';
        pillClass = 'bg-emerald-50/70 border-emerald-200 text-emerald-800';
      } else if (status === 'RUNNING') {
        iconHtml = '<span class="material-symbols-outlined text-xs text-primary animate-spin">progress_activity</span>';
        pillClass = 'bg-indigo-50 border-primary text-primary font-bold pulse-blue';
      } else if (status === 'FAILED') {
        iconHtml = '<span class="material-symbols-outlined text-xs text-rose-600 font-bold">cancel</span>';
        pillClass = 'bg-rose-50 border-rose-300 text-rose-800 font-bold';
      } else if (status === 'SKIPPED') {
        iconHtml = '<span class="material-symbols-outlined text-xs text-slate-400">remove</span>';
        pillClass = 'bg-slate-50 border-slate-200 text-slate-400';
      }

      if (isSelected) {
        pillClass += ' ring-2 ring-primary ring-offset-1';
      }

      html += `
        <div class="flex items-center gap-1.5 flex-1 min-w-[85px]">
          <button data-step-key="${sDef.key}" class="bpmn-step-card w-full p-2 rounded-xl border text-left flex items-center gap-2 ${pillClass} shadow-2xs">
            ${iconHtml}
            <div class="min-w-0">
              <p class="text-[10px] font-semibold truncate leading-tight">${sDef.name}</p>
              <p class="text-[8.5px] uppercase tracking-wider opacity-70 truncate">${status}</p>
            </div>
          </button>
          ${idx < STEP_ORDER.length - 1 ? '<span class="text-slate-300 text-xs font-bold pointer-events-none">→</span>' : ''}
        </div>
      `;
    });

    track.innerHTML = html;

    // Attach click events
    track.querySelectorAll('button[data-step-key]').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedStepKey = btn.getAttribute('data-step-key');
        renderStepTrack(inst);
        renderStepInspector(inst, selectedStepKey);
      });
    });
  }

  // ── 6. Render Step Inspector Details ────────────────────────────
  function renderStepInspector(inst, stepKey) {
    const sDef = STEP_ORDER.find(s => s.key === stepKey) || STEP_ORDER[0];
    const sData = (inst.steps && inst.steps[stepKey]) || {};

    const titleEl = document.getElementById('insp-step-title');
    const serviceEl = document.getElementById('insp-service');
    const statusEl = document.getElementById('insp-status');
    const durEl = document.getElementById('insp-duration');
    const inputEl = document.getElementById('insp-input');
    const outputEl = document.getElementById('insp-output');
    const iconEl = document.getElementById('insp-icon');

    if (titleEl) titleEl.textContent = sDef.name;
    if (serviceEl) serviceEl.textContent = `Service: ${sData.service || sDef.service}`;
    if (statusEl) {
      statusEl.textContent = sData.status || 'PENDING';
      statusEl.className = sData.status === 'COMPLETED' ? 'text-emerald-600 font-bold' : (sData.status === 'FAILED' ? 'text-rose-600 font-bold' : (sData.status === 'RUNNING' ? 'text-blue-600 font-bold' : 'text-slate-800'));
    }
    if (durEl) durEl.textContent = sData.duration_sec ? `${sData.duration_sec}s` : (sData.status === 'RUNNING' ? 'In progress' : '—');
    if (inputEl) inputEl.textContent = sData.input || `Dataset: ${inst.dataset_name}, Dept: ${inst.department}, FY: ${inst.fiscal_year}`;
    if (outputEl) outputEl.textContent = sData.output || (sData.error ? `ERROR: ${sData.error}` : (sData.status === 'RUNNING' ? 'Executing task payload...' : 'Pending upstream execution'));
    if (iconEl) iconEl.textContent = sDef.icon;
  }

  // ── 7. Render BPMN Diagram Node Highlights ──────────────────────
  function renderBpmnHighlighting(inst) {
    const steps = inst.steps || {};

    STEP_ORDER.forEach(sDef => {
      const nodeEl = document.getElementById(`bpmn-node-${sDef.key}`);
      if (!nodeEl) return;

      const sData = steps[sDef.key] || {};
      const st = sData.status || 'PENDING';

      nodeEl.className = 'p-2.5 bg-white border rounded-lg text-center w-24 bpmn-node shadow-2xs';

      if (st === 'COMPLETED') {
        nodeEl.classList.add('border-emerald-500', 'bg-emerald-50/40', 'text-emerald-900');
      } else if (st === 'RUNNING') {
        nodeEl.classList.add('border-primary', 'bg-indigo-50', 'text-indigo-900', 'pulse-blue', 'font-bold');
      } else if (st === 'FAILED') {
        nodeEl.classList.add('border-rose-500', 'bg-rose-50', 'text-rose-900', 'font-bold');
      } else {
        nodeEl.classList.add('border-slate-200', 'text-slate-600');
      }
    });
  }

  // ── 8. Render Pending Approval Banner ───────────────────────────
  function renderPendingApprovalBanner(inst) {
    const banner = document.getElementById('pending-approval-banner');
    if (!banner) return;

    if (inst.status === 'PENDING_APPROVAL') {
      banner.classList.remove('hidden');
      const deptEl = document.getElementById('banner-dept');
      const impactEl = document.getElementById('banner-impact');
      const descEl = document.getElementById('banner-risk-desc');
      const pillEl = document.getElementById('banner-risk-pill');

      if (deptEl) deptEl.textContent = inst.department || 'Overall';
      if (impactEl) impactEl.textContent = inst.projected_impact || '₹3.80 Cr';
      if (descEl && inst.risk_summary) descEl.textContent = inst.risk_summary;
      if (pillEl) pillEl.textContent = `${inst.risk_level || 'High'} Risk`;

      // Wire Banner Buttons
      const approveBtn = document.getElementById('btn-banner-approve');
      const rejectBtn = document.getElementById('btn-banner-reject');

      if (approveBtn) {
        approveBtn.onclick = async () => {
          approveBtn.disabled = true;
          approveBtn.textContent = 'Approving...';
          await api.post(`/api/v1/workflow/${inst.process_instance_id}/approve`, { notes: 'Approved by Executive Financial Manager' });
          await loadKpis();
          await loadInstances();
        };
      }
      if (rejectBtn) {
        rejectBtn.onclick = async () => {
          rejectBtn.disabled = true;
          rejectBtn.textContent = 'Rejecting...';
          await api.post(`/api/v1/workflow/${inst.process_instance_id}/reject`, { notes: 'Rejected by Executive Financial Manager' });
          await loadKpis();
          await loadInstances();
        };
      }
    } else {
      banner.classList.add('hidden');
    }
  }

  // ── 9. Render Workflow Execution History Table ──────────────────
  function renderHistoryTable(instances) {
    const tbody = document.getElementById('workflow-history-tbody');
    const countEl = document.getElementById('history-count');
    if (!tbody) return;

    if (!instances || instances.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="px-4 py-8 text-center text-slate-400 text-xs">No workflow executions recorded.</td></tr>';
      if (countEl) countEl.textContent = '0 executions';
      return;
    }

    if (countEl) countEl.textContent = `Showing ${instances.length} execution instances`;

    let html = '';
    instances.forEach(inst => {
      const isSelected = activeInstanceId === inst.process_instance_id;
      const startStr = inst.started_at ? new Date(inst.started_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
      const endStr = inst.completed_at ? new Date(inst.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : (inst.status === 'RUNNING' ? '<span class="text-blue-600 font-semibold animate-pulse">Running</span>' : '—');

      let statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-slate-100 text-slate-700">ACTIVE</span>';
      if (inst.status === 'COMPLETED') {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Completed</span>';
      } else if (inst.status === 'RUNNING') {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">Running</span>';
      } else if (inst.status === 'PENDING_APPROVAL') {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-50 text-amber-700 border border-amber-200">Pending Approval</span>';
      } else if (inst.status === 'FAILED') {
        statusBadge = '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold bg-rose-50 text-rose-700 border border-rose-200">Failed</span>';
      }

      html += `
        <tr class="hover:bg-slate-50/80 transition ${isSelected ? 'bg-indigo-50/40 font-medium' : ''}">
          <td class="px-4 py-3 font-semibold text-slate-900 flex items-center gap-1.5">
            <span class="material-symbols-outlined text-xs text-primary">account_tree</span>
            <span>#${inst.process_instance_id.replace('pl-wf-', '')}</span>
          </td>
          <td class="px-4 py-3 text-slate-700">${inst.department} (${inst.fiscal_year})</td>
          <td class="px-4 py-3 text-slate-600">${startStr}</td>
          <td class="px-4 py-3 text-slate-600">${endStr}</td>
          <td class="px-4 py-3 font-medium text-slate-800">${inst.current_step_name || 'Completed'}</td>
          <td class="px-4 py-3 text-center">${statusBadge}</td>
          <td class="px-4 py-3 text-right text-slate-600 font-mono">${inst.duration}</td>
          <td class="px-4 py-3 text-right">
            <button data-view-inst="${inst.process_instance_id}" class="px-2.5 py-1 rounded-md text-[10px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition cursor-pointer">
              View
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;

    // Attach View handlers
    tbody.querySelectorAll('button[data-view-inst]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-view-inst');
        selectedStepKey = null;
        await loadActiveInstanceDetails(id);
        renderHistoryTable(cachedInstances);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
  }

  // ── 10. Workflow Details Modal Drawer ───────────────────────────
  async function openWorkflowDetailsModal(instId) {
    if (!instId) return;
    try {
      const inst = cachedInstances.find(i => i.process_instance_id === instId) || 
                   await api.get(`/api/v1/workflow/instances/${encodeURIComponent(instId)}`).catch(() => null);
      if (!inst) return;

      const modal = document.getElementById('modal-workflow-details');
      if (!modal) return;

      const titleEl = document.getElementById('details-modal-title');
      if (titleEl) titleEl.textContent = `Workflow Details #${inst.process_instance_id.replace('pl-wf-', '')} (${inst.department})`;

      const statusEl = document.getElementById('details-status');
      if (statusEl) {
        statusEl.textContent = inst.status;
        statusEl.className = inst.status === 'COMPLETED' ? 'font-bold text-emerald-600' : (inst.status === 'FAILED' ? 'font-bold text-rose-600' : 'font-bold text-blue-600');
      }

      const stepEl = document.getElementById('details-current-step');
      if (stepEl) stepEl.textContent = inst.current_step_name || 'Completed';

      const startedEl = document.getElementById('details-started');
      if (startedEl) startedEl.textContent = inst.started_at ? new Date(inst.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';

      const durationEl = document.getElementById('details-duration');
      if (durationEl) durationEl.textContent = inst.duration || '—';

      const metrics = inst.metrics || {};
      const anomEl = document.getElementById('details-anomalies');
      if (anomEl) anomEl.textContent = `${metrics.total_anomalies ?? 12} Anomalies`;

      const forecastEl = document.getElementById('details-forecast-status');
      if (forecastEl) forecastEl.textContent = inst.status === 'COMPLETED' ? 'Generated (95% CI)' : (inst.status === 'RUNNING' ? 'Running' : 'Pending');

      const riskEl = document.getElementById('details-risk-level');
      if (riskEl) {
        riskEl.textContent = inst.risk_level || 'Low';
        riskEl.className = inst.risk_level === 'High' ? 'text-base font-bold text-rose-700 mt-0.5' : 'text-base font-bold text-indigo-900 mt-0.5';
      }

      // Render timeline list
      const timelineList = document.getElementById('details-timeline-list');
      if (timelineList) {
        const steps = inst.steps || {};
        let timelineHtml = '';
        STEP_ORDER.forEach(step => {
          const stepData = steps[step.key] || { status: 'PENDING' };
          let statusIcon = 'radio_button_unchecked';
          let colorClass = 'text-slate-400 bg-slate-50 border-slate-200';
          if (stepData.status === 'COMPLETED') {
            statusIcon = 'check_circle';
            colorClass = 'text-emerald-700 bg-emerald-50 border-emerald-200';
          } else if (stepData.status === 'RUNNING') {
            statusIcon = 'sync';
            colorClass = 'text-blue-700 bg-blue-50 border-blue-200 animate-pulse';
          } else if (stepData.status === 'FAILED') {
            statusIcon = 'cancel';
            colorClass = 'text-rose-700 bg-rose-50 border-rose-200';
          } else if (stepData.status === 'SKIPPED') {
            statusIcon = 'remove_circle_outline';
            colorClass = 'text-slate-400 bg-slate-100 border-slate-200';
          }

          timelineHtml += `
            <div class="flex items-center justify-between p-2.5 rounded-lg border ${colorClass} text-xs">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">${statusIcon}</span>
                <span class="font-semibold text-slate-800">${step.name}</span>
                <span class="text-[10px] text-slate-500">(${step.service})</span>
              </div>
              <div class="flex items-center gap-3 text-[11px] font-mono text-slate-600">
                <span>${stepData.duration_sec ? stepData.duration_sec + 's' : '—'}</span>
                <span class="font-bold uppercase text-[9px]">${stepData.status}</span>
              </div>
            </div>
          `;
        });
        timelineList.innerHTML = timelineHtml;
      }

      modal.classList.remove('hidden');
    } catch (e) {
      console.warn('Failed to open details modal:', e);
    }
  }

  // ── Details Modal Close Handlers ────────────────────────────────
  const detailsModal = document.getElementById('modal-workflow-details');
  const btnCloseDetails = document.getElementById('close-details-modal');
  const btnCloseDetailsBtn = document.getElementById('close-details-modal-btn');
  if (btnCloseDetails && detailsModal) {
    btnCloseDetails.addEventListener('click', () => detailsModal.classList.add('hidden'));
  }
  if (btnCloseDetailsBtn && detailsModal) {
    btnCloseDetailsBtn.addEventListener('click', () => detailsModal.classList.add('hidden'));
  }

  // Banner View Details button
  const btnBannerDetails = document.getElementById('btn-banner-details');
  if (btnBannerDetails) {
    btnBannerDetails.addEventListener('click', () => {
      if (activeInstanceId) openWorkflowDetailsModal(activeInstanceId);
    });
  }

  // View All History button
  const btnViewAllHistory = document.getElementById('btn-view-all-history');
  if (btnViewAllHistory) {
    btnViewAllHistory.addEventListener('click', async () => {
      await loadInstances();
      alert(`Loaded ${cachedInstances.length} audited workflow instances.`);
    });
  }

  // ── 11. Polling Helper for Live Updates ──────────────────────────
  async function pollActiveState() {
    await loadKpis();
    const list = await api.get('/api/v1/workflow/instances').catch(() => []);
    if (Array.isArray(list)) {
      cachedInstances = list;
      renderHistoryTable(cachedInstances);
      if (activeInstanceId) {
        await loadActiveInstanceDetails(activeInstanceId);
      }
    }
  }

  // ── 12. Start Workflow Modal Handlers ───────────────────────────
  const startModal = document.getElementById('modal-start-workflow');
  const btnOpenModal = document.getElementById('btn-open-start-modal');
  const btnCloseModal = document.getElementById('close-start-modal');
  const btnCancelModal = document.getElementById('cancel-start-modal');
  const btnSubmitStart = document.getElementById('submit-start-workflow');

  if (btnOpenModal && startModal) {
    btnOpenModal.addEventListener('click', () => startModal.classList.remove('hidden'));
    if (btnCloseModal) btnCloseModal.addEventListener('click', () => startModal.classList.add('hidden'));
    if (btnCancelModal) btnCancelModal.addEventListener('click', () => startModal.classList.add('hidden'));

    if (btnSubmitStart) {
      btnSubmitStart.addEventListener('click', async () => {
        const dept = document.getElementById('modal-dept-select')?.value || 'Overall';
        const year = document.getElementById('modal-period-select')?.value || '2024';
        const analysisType = document.getElementById('modal-analysis-type')?.value || 'comprehensive';
        const triggerApproval = document.getElementById('modal-approval-check')?.checked ?? true;

        btnSubmitStart.disabled = true;
        btnSubmitStart.textContent = 'Starting...';

        try {
          const newInst = await api.post('/api/v1/workflow/start', {
            dataset_id: 1,
            department: dept,
            fiscal_year: year,
            trigger_approval: triggerApproval,
          });

          startModal.classList.add('hidden');
          if (newInst && newInst.process_instance_id) {
            activeInstanceId = newInst.process_instance_id;
            selectedStepKey = null;
          }
          await loadKpis();
          await loadInstances(true);
        } catch (e) {
          console.error('Failed to start workflow:', e);
          alert('Failed to start workflow. Please check server logs.');
        } finally {
          btnSubmitStart.disabled = false;
          btnSubmitStart.innerHTML = '<span class="material-symbols-outlined text-sm">bolt</span><span>Start Workflow</span>';
        }
      });
    }
  }

  // ── 13. BPMN XML Modal Handler ──────────────────────────────────
  const bpmnModal = document.getElementById('modal-bpmn-xml');
  const btnExportBpmn = document.getElementById('btn-export-bpmn');
  const btnCloseBpmn = document.getElementById('close-bpmn-modal');
  const bpmnContent = document.getElementById('bpmn-xml-content');

  if (btnExportBpmn && bpmnModal) {
    btnExportBpmn.addEventListener('click', async () => {
      bpmnModal.classList.remove('hidden');
      if (bpmnContent) {
        try {
          const resp = await fetch('/api/v1/workflow/bpmn');
          const xml = await resp.text();
          bpmnContent.textContent = xml;
        } catch (e) {
          bpmnContent.textContent = 'Failed to load BPMN XML.';
        }
      }
    });
    if (btnCloseBpmn) btnCloseBpmn.addEventListener('click', () => bpmnModal.classList.add('hidden'));
  }

  // ── 14. Refresh Button Handler ──────────────────────────────────
  const refreshBtn = document.getElementById('btn-refresh-wf');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      await loadKpis();
      await loadInstances();
    });
  }

  // ── Initial Load ────────────────────────────────────────────────
  await loadKpis();
  await loadInstances(true);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWorkflowPage);
} else {
  initWorkflowPage();
}
