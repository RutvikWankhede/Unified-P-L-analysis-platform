html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta content="width=device-width, initial-scale=1.0" name="viewport">
<title>Unified P&amp;L - Dashboard</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
<script>
tailwind.config = {
theme: {
extend: {
colors: {
primary: '#5b5ceb', 'primary-container': '#e5e6ff', 'on-primary-container': '#1a1a4b',
surface: '#f8f9fd', 'surface-container-lowest': '#ffffff', 'surface-container-low': '#f2f3f7',
'on-surface': '#1a1c1e', 'on-surface-variant': '#44474e', 'outline-variant': '#c4c6d0',
success: '#10b981', danger: '#ef4444', warning: '#f59e0b',
},
fontFamily: { sans: ['Inter', 'sans-serif'] },
borderRadius: { 'card': '20px' }
}
}
}
</script>
<style>
body { background-color: #FAFBFF; font-family: 'Inter', sans-serif; }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
.glass-effect { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); }
.progress-ring-circle { transition: stroke-dashoffset 0.35s; transform: rotate(-90deg); transform-origin: 50% 50%; }
</style>
</head>
<body class="text-on-surface">
<div id="sidebar-container"></div>
<main class="ml-[280px] min-h-screen pb-16">

<header class="h-16 glass-effect border-b border-outline-variant/20 flex items-center justify-between px-8 sticky top-0 z-40">
<div class="flex items-center gap-2">
<span class="font-semibold text-sm">Dashboard</span>
<span class="text-xs text-on-surface-variant ml-4" id="header-health-score">Health: --</span>
</div>
<div class="flex items-center gap-4">
  <input type="date" id="filter-date" class="bg-white border border-outline-variant/30 rounded px-3 py-1 text-sm">
  <select id="filter-dept" class="bg-white border border-outline-variant/30 rounded px-3 py-1 text-sm">
    <option value="">All Departments</option>
    <option value="Sales">Sales</option>
    <option value="Marketing">Marketing</option>
    <option value="Engineering">Engineering</option>
    <option value="HR">HR</option>
    <option value="Finance">Finance</option>
  </select>
  <select id="filter-currency" class="bg-white border border-outline-variant/30 rounded px-3 py-1 text-sm">
    <option value="INR" selected>INR (₹)</option>
    <option value="USD">USD ($)</option>
    <option value="EUR">EUR (€)</option>
  </select>
  <select id="filter-agg" class="bg-white border border-outline-variant/30 rounded px-3 py-1 text-sm">
    <option value="daily">Daily</option>
    <option value="weekly">Weekly</option>
    <option value="monthly">Monthly</option>
    <option value="quarterly">Quarterly</option>
    <option value="yearly" selected>Yearly</option>
  </select>
</div>
</header>

<div class="px-8 py-6 space-y-6">
  
  <!-- Row 1: KPIs (7 items) -->
  <section class="grid grid-cols-7 gap-4">
    <!-- Health Score -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-health-score">
      <div class="text-xs text-on-surface-variant font-medium mb-1">Financial Health Score</div>
      <div class="text-3xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> -- vs prior</div>
    </div>
    <!-- Revenue -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-revenue">
      <div class="text-xs text-on-surface-variant font-medium mb-1 flex items-center gap-2">
        <span class="w-5 h-5 rounded bg-blue-100 text-blue-600 flex items-center justify-center"><span class="material-symbols-outlined text-[12px]">payments</span></span> Total Revenue
      </div>
      <div class="text-xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> -- vs prior</div>
    </div>
    <!-- Expense -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-expense">
      <div class="text-xs text-on-surface-variant font-medium mb-1 flex items-center gap-2">
        <span class="w-5 h-5 rounded bg-red-100 text-red-600 flex items-center justify-center"><span class="material-symbols-outlined text-[12px]">shopping_cart</span></span> Total Expense
      </div>
      <div class="text-xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_downward</span> -- vs prior</div>
    </div>
    <!-- Net Profit -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-profit">
      <div class="text-xs text-on-surface-variant font-medium mb-1 flex items-center gap-2">
        <span class="w-5 h-5 rounded bg-green-100 text-green-600 flex items-center justify-center"><span class="material-symbols-outlined text-[12px]">account_balance</span></span> Net Profit
      </div>
      <div class="text-xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> -- vs prior</div>
    </div>
    <!-- Profit Margin -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-margin">
      <div class="text-xs text-on-surface-variant font-medium mb-1 flex items-center gap-2">
        <span class="w-5 h-5 rounded bg-emerald-100 text-emerald-600 flex items-center justify-center"><span class="material-symbols-outlined text-[12px]">percent</span></span> Profit Margin
      </div>
      <div class="text-xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> -- vs prior</div>
    </div>
    <!-- Cash Flow -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-cash-flow">
      <div class="text-xs text-on-surface-variant font-medium mb-1 flex items-center gap-2">
        <span class="w-5 h-5 rounded bg-cyan-100 text-cyan-600 flex items-center justify-center"><span class="material-symbols-outlined text-[12px]">water_drop</span></span> Cash Flow
      </div>
      <div class="text-xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> -- vs prior</div>
    </div>
    <!-- Forecast Revenue -->
    <div class="bg-white rounded-card p-4 border border-outline-variant/20 shadow-sm flex flex-col justify-between" id="kpi-forecast">
      <div class="text-xs text-on-surface-variant font-medium mb-1 flex items-center gap-2">
        <span class="w-5 h-5 rounded bg-purple-100 text-purple-600 flex items-center justify-center"><span class="material-symbols-outlined text-[12px]">trending_up</span></span> Forecast Rev
      </div>
      <div class="text-xl font-bold">--</div>
      <div class="text-[10px] text-success flex items-center mt-2 font-medium"><span class="material-symbols-outlined text-[14px]">arrow_upward</span> -- vs prior</div>
    </div>
  </section>

  <!-- Row 2: Core Financial (70/30) -->
  <section class="grid grid-cols-12 gap-6">
    <div class="col-span-8 bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-bold text-base">Revenue vs Expense vs Net Profit Trend</h3>
        <div id="trend-agg-buttons" class="flex bg-slate-100 p-1 rounded-lg text-[10px]">
          <button data-agg="daily" class="px-3 py-1 rounded-md text-slate-500 hover:bg-slate-200">Daily</button>
          <button data-agg="weekly" class="px-3 py-1 rounded-md text-slate-500 hover:bg-slate-200">Weekly</button>
          <button data-agg="monthly" class="px-3 py-1 rounded-md text-slate-500 hover:bg-slate-200">Monthly</button>
          <button data-agg="quarterly" class="px-3 py-1 rounded-md text-slate-500 hover:bg-slate-200">Quarterly</button>
          <button data-agg="yearly" class="px-3 py-1 rounded-md bg-white text-primary shadow-sm font-bold">Yearly</button>
        </div>
      </div>
      <div id="chart-rev-exp-profit" class="w-full flex-1 min-h-[300px]"></div>
    </div>
    <div class="col-span-4 flex flex-col gap-6">
      <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex-1 flex flex-col relative group">
        <h3 class="font-bold text-base mb-2">Anomaly Overview</h3>
        <a href="anomalies.html" class="absolute top-6 right-6 text-[10px] text-primary hover:underline font-bold flex items-center">View All <span class="material-symbols-outlined text-[12px]">arrow_forward</span></a>
        <div id="chart-anomaly-overview" class="w-full flex-1 min-h-[150px]"></div>
        <div id="anomaly-overview-legend" class="text-xs mt-2"></div>
      </div>
      <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex-1 flex flex-col relative">
        <h3 class="font-bold text-base mb-2">Anomaly Trend</h3>
        <div id="chart-anomaly-trend" class="w-full flex-1 min-h-[120px]"></div>
      </div>
    </div>
  </section>

  <!-- Row 3: Operational Analysis (3 cols) -->
  <section class="grid grid-cols-3 gap-6">
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col">
      <h3 class="font-bold text-base mb-4">Department Performance</h3>
      <div id="chart-dept-performance" class="w-full flex-1 min-h-[250px]"></div>
    </div>
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col">
      <h3 class="font-bold text-base mb-4">Expense Distribution</h3>
      <div id="chart-expense-dist" class="w-full flex-1 min-h-[250px]"></div>
    </div>
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-bold text-base">AI Financial Insights</h3>
        <button onclick="showModal('recommendations-modal')" class="text-primary text-xs hover:underline font-bold flex items-center">View All <span class="material-symbols-outlined text-[12px]">arrow_forward</span></button>
      </div>
      <div id="ai-insights-list" class="flex-1 space-y-3 overflow-y-auto custom-scrollbar"></div>
    </div>
  </section>

  <!-- Row 4: Forward Looking (50/50) -->
  <section class="grid grid-cols-2 gap-6">
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col">
      <h3 class="font-bold text-base mb-4">Forecast vs Actual</h3>
      <div id="chart-forecast-actual" class="w-full flex-1 min-h-[250px]"></div>
    </div>
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col relative">
      <h3 class="font-bold text-base mb-4">Cash Flow Trend</h3>
      <div id="cash-flow-empty" class="hidden absolute inset-0 flex items-center justify-center bg-white/90 z-10 text-sm text-slate-500 font-medium">Data not available</div>
      <div id="chart-cash-flow" class="w-full flex-1 min-h-[250px]"></div>
    </div>
  </section>

  <!-- Row 5: Financial Breakdown (50/50) -->
  <section class="grid grid-cols-2 gap-6">
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col relative">
      <h3 class="font-bold text-base mb-4">Profit Waterfall</h3>
      <div id="waterfall-empty" class="hidden absolute inset-0 flex items-center justify-center bg-white/90 z-10 text-sm text-slate-500 font-medium">Data not available</div>
      <div id="chart-waterfall" class="w-full flex-1 min-h-[250px]"></div>
    </div>
    <div class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm flex flex-col relative">
      <div class="flex justify-between items-center mb-4">
        <h3 class="font-bold text-base">Budget vs Actual</h3>
        <button id="btn-set-budget" class="text-primary text-[10px] font-bold flex items-center hover:underline bg-primary/10 px-2 py-1 rounded"><span class="material-symbols-outlined text-[14px] mr-1">edit</span> Set Budget</button>
      </div>
      <div id="budget-empty" class="hidden absolute inset-0 flex flex-col items-center justify-center bg-white/95 z-10 text-sm text-slate-500 font-medium pt-10">
        <span class="material-symbols-outlined text-4xl mb-2 text-slate-300">account_balance_wallet</span>
        No budget set for current active filters
      </div>
      <div id="chart-budget-actual" class="w-full flex-1 min-h-[250px]"></div>
    </div>
  </section>

  <!-- Row 6: AI Recommendations System (Full Width) -->
  <section class="bg-white rounded-card p-6 border border-outline-variant/20 shadow-sm">
    <div class="flex items-center justify-between mb-6">
      <h3 class="font-bold text-lg flex items-center gap-2"><span class="material-symbols-outlined text-brand">robot_2</span> AI Recommendations System</h3>
      <button onclick="showModal('recommendations-modal')" class="text-primary text-sm font-bold hover:underline flex items-center">View All <span class="material-symbols-outlined text-[16px]">arrow_forward</span></button>
    </div>
    <div id="ai-decision-center" class="grid grid-cols-3 gap-6"></div>
  </section>

</div>

<footer class="h-12 bg-white/90 backdrop-blur-md border-t border-outline-variant/30 px-8 flex items-center justify-between text-xs text-on-surface-variant z-40 fixed bottom-0 left-[280px] right-0">
  <div class="flex items-center gap-2">
    <div class="w-2 h-2 rounded-full bg-success"></div>
    <span class="font-medium">System Status: All Systems Operational</span>
  </div>
  <div class="text-[10px] text-slate-400">Data reflects currently active dataset</div>
</footer>

</main>

<!-- Modals -->
<div id="budget-modal" class="fixed inset-0 z-50 hidden items-center justify-center bg-slate-900/50 backdrop-blur-sm opacity-0 transition-opacity duration-300">
  <div id="budget-modal-content" class="bg-white rounded-2xl shadow-xl w-full max-w-md transform scale-95 transition-transform duration-300">
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
      <h3 class="font-bold text-lg">Set Department Budget</h3>
      <button id="btn-close-budget" class="text-slate-400 hover:text-slate-600"><span class="material-symbols-outlined">close</span></button>
    </div>
    <div class="p-6">
      <form id="budget-form" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Department</label>
          <select id="budget-dept" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none">
            <option value="Sales">Sales</option>
            <option value="Marketing">Marketing</option>
            <option value="Engineering">Engineering</option>
            <option value="HR">HR</option>
            <option value="Finance">Finance</option>
            <option value="Operations">Operations</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Budget Amount (₹)</label>
          <input type="number" id="budget-amount" required class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none" placeholder="e.g. 5000000">
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button type="button" id="btn-cancel-budget" class="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg transition-colors">Cancel</button>
          <button type="submit" class="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm">Save Budget</button>
        </div>
      </form>
    </div>
  </div>
</div>

<div id="recommendations-modal" class="fixed inset-0 z-50 hidden items-center justify-center bg-slate-900/50 backdrop-blur-sm opacity-0 transition-opacity duration-300">
  <div id="recommendations-modal-content" class="bg-white rounded-2xl shadow-xl w-full max-w-4xl transform scale-95 transition-transform duration-300 max-h-[85vh] flex flex-col">
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100 shrink-0">
      <h3 class="font-bold text-lg flex items-center gap-2"><span class="material-symbols-outlined text-brand">robot_2</span> AI Recommendations System</h3>
      <button onclick="hideModal('recommendations-modal')" class="text-slate-400 hover:text-slate-600 transition-colors">
        <span class="material-symbols-outlined">close</span>
      </button>
    </div>
    <div class="p-6 overflow-y-auto flex-1 bg-slate-50" id="modal-recommendations-list">
      <!-- dynamically populated -->
    </div>
    <div class="px-6 py-4 border-t border-slate-100 shrink-0 flex justify-end">
      <button onclick="hideModal('recommendations-modal')" class="px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-700">Close</button>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<script type="module" src="js/shell.js"></script>
<script type="module" src="js/dashboard_wiring.js"></script>
</body>
</html>
"""
with open(r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2\dashboard.html', 'w', encoding='utf-8') as f:
    f.write(html)
