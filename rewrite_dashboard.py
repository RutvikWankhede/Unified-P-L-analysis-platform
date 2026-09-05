import re

file_path = r"c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\frontend_v2\pl_dashboard.html"

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

new_main_content = """<main class="ml-[240px] min-h-screen pb-12 bg-[#FAFBFF]">
  <!-- Top Bar -->
  <header class="h-14 glass-effect border-b border-outline-variant/20 flex items-center justify-between px-6 sticky top-0 z-40">
    <div class="flex items-center gap-2">
      <span class="font-bold text-[15px] text-slate-800 tracking-tight">Executive Dashboard</span>
      <span class="bg-primary/10 text-primary text-[9px] font-bold px-1.5 py-0.5 rounded tracking-wide ml-2 uppercase">Auto-Sync Active</span>
    </div>
    <div class="flex items-center gap-4">
      <div class="bg-white border border-outline-variant/30 rounded px-2.5 py-1.5 flex items-center gap-2 text-xs font-semibold shadow-sm text-slate-600">
        <span class="material-symbols-outlined text-sm">calendar_today</span>
        <span id="dashboard-date-range">May 13 - May 19, 2025</span>
        <span class="material-symbols-outlined text-sm">keyboard_arrow_down</span>
      </div>
      <button class="relative p-1.5 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
        <span class="material-symbols-outlined text-[20px]">notifications</span>
        <span class="absolute top-1 right-1 w-2 h-2 bg-danger rounded-full border-2 border-white"></span>
      </button>
      <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-[10px] font-bold">RW</div>
    </div>
  </header>

  <div class="px-6 py-4 space-y-4">
    
    <!-- Row 1: KPI Cards -->
    <section class="grid grid-cols-6 gap-4">
      <!-- 1. Health Score -->
      <div class="col-span-1 bg-white rounded-[12px] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-5 h-5 bg-primary/10 text-primary rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-[13px]">favorite</span>
          </div>
          <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Health Score</p>
        </div>
        <p class="text-xl font-bold text-slate-800" id="kpi-health-score">96</p>
        <div class="flex items-center gap-1 text-success text-[10px] font-bold mt-1">
          <span class="material-symbols-outlined text-[12px]">arrow_upward</span>
          <span>8 pts vs last month</span>
        </div>
      </div>
      <!-- 2. Total Revenue -->
      <div class="col-span-1 bg-white rounded-[12px] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-5 h-5 bg-blue-100 text-blue-600 rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-[13px]">payments</span>
          </div>
          <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Total Revenue</p>
        </div>
        <p class="text-xl font-bold text-slate-800" id="kpi-total-revenue">₹0.00</p>
        <div class="flex items-center gap-1 text-success text-[10px] font-bold mt-1">
          <span class="material-symbols-outlined text-[12px]">arrow_upward</span>
          <span>12.8% vs last month</span>
        </div>
      </div>
      <!-- 3. Total Expense -->
      <div class="col-span-1 bg-white rounded-[12px] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-5 h-5 bg-danger/10 text-danger rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-[13px]">shopping_cart</span>
          </div>
          <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Total Expense</p>
        </div>
        <p class="text-xl font-bold text-slate-800" id="kpi-total-expense">₹0.00</p>
        <div class="flex items-center gap-1 text-danger text-[10px] font-bold mt-1">
          <span class="material-symbols-outlined text-[12px]">arrow_downward</span>
          <span>8.3% vs last month</span>
        </div>
      </div>
      <!-- 4. Net Profit -->
      <div class="col-span-1 bg-white rounded-[12px] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-5 h-5 bg-success/10 text-success rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-[13px]">trending_up</span>
          </div>
          <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Net Profit</p>
        </div>
        <p class="text-xl font-bold text-slate-800" id="kpi-net-profit">₹0.00</p>
        <div class="flex items-center gap-1 text-success text-[10px] font-bold mt-1">
          <span class="material-symbols-outlined text-[12px]">arrow_upward</span>
          <span>16.7% vs last month</span>
        </div>
      </div>
      <!-- 5. Forecast Rev -->
      <div class="col-span-1 bg-white rounded-[12px] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-5 h-5 bg-indigo-100 text-indigo-600 rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-[13px]">auto_graph</span>
          </div>
          <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Forecast Rev</p>
        </div>
        <p class="text-xl font-bold text-slate-800" id="kpi-forecasted-profit">₹0.00</p>
        <div class="flex items-center gap-1 text-success text-[10px] font-bold mt-1">
          <span class="material-symbols-outlined text-[12px]">arrow_upward</span>
          <span>Model expected case</span>
        </div>
      </div>
      <!-- 6. Cash Flow -->
      <div class="col-span-1 bg-white rounded-[12px] shadow-sm border border-outline-variant/20 p-4 flex flex-col justify-between">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-5 h-5 bg-teal-100 text-teal-600 rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-[13px]">account_balance_wallet</span>
          </div>
          <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider">Est. Cash Flow</p>
        </div>
        <p class="text-xl font-bold text-slate-800" id="kpi-cash-flow">₹0.00</p>
        <p class="text-[9px] text-slate-400 mt-1 leading-tight font-medium">Derived from Rev - Exp</p>
      </div>
    </section>

    <!-- Row 2: Main Chart + Insights -->
    <section class="grid grid-cols-12 gap-4">
      <!-- Left: Revenue vs Expense vs Profit -->
      <div class="col-span-9 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-[13px] text-slate-800">Revenue vs Expense vs Profit</h3>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-3 mr-2">
              <div class="flex items-center gap-1.5"><div class="w-2.5 h-2.5 rounded-full bg-primary"></div><span class="text-[10px] font-semibold text-slate-500">Revenue</span></div>
              <div class="flex items-center gap-1.5"><div class="w-2.5 h-2.5 rounded-full bg-danger"></div><span class="text-[10px] font-semibold text-slate-500">Expense</span></div>
              <div class="flex items-center gap-1.5"><div class="w-2.5 h-2.5 rounded-full bg-success"></div><span class="text-[10px] font-semibold text-slate-500">Profit</span></div>
            </div>
            <div class="border border-slate-200 px-2.5 py-1 rounded text-[10px] font-semibold text-slate-600 flex items-center gap-1 cursor-pointer hover:bg-slate-50">
              This Week <span class="material-symbols-outlined text-[14px]">keyboard_arrow_down</span>
            </div>
            <span class="material-symbols-outlined text-[16px] text-slate-400 cursor-pointer">more_vert</span>
          </div>
        </div>
        <div class="flex-1 min-h-[240px] relative">
          <canvas data-purpose="revenue-expense-chart" id="chart-revenue-expense" class="absolute inset-0 w-full h-full"></canvas>
        </div>
      </div>
      <!-- Right: Data Quality / Insights -->
      <div class="col-span-3 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col">
        <div class="flex items-start justify-between border-b border-slate-100 pb-3 mb-3">
          <div class="w-full">
            <h3 class="font-bold text-[13px] text-slate-800 mb-2">Data Quality Score</h3>
            <div class="flex justify-center w-full">
              <div class="relative w-24 h-24 my-2">
                <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="#f1f5f9" stroke-width="4"></circle>
                  <circle cx="18" cy="18" r="15.915" fill="none" stroke="#eab308" stroke-width="4" stroke-dasharray="98, 100" class="progress-ring-circle transition-all duration-1000"></circle>
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <span class="text-2xl font-bold text-slate-800">98</span>
                  <span class="text-[9px] font-semibold text-slate-400">/100</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-1.5 mb-3">
          <span class="material-symbols-outlined text-primary text-[14px]">auto_awesome</span>
          <h3 class="font-bold text-[13px] text-slate-800">Insights</h3>
        </div>
        <div class="space-y-2 flex-1 overflow-y-auto custom-scrollbar pr-1" id="ai-insights-container">
          <div data-row-template="true" class="p-2.5 bg-slate-50 rounded-lg flex gap-2.5 border border-slate-100">
            <div class="w-6 h-6 rounded bg-success/10 text-success flex-shrink-0 flex items-center justify-center">
              <span class="material-symbols-outlined text-[14px]">check_circle</span>
            </div>
            <div class="flex-1">
              <p class="text-[11px] font-bold text-slate-800 leading-tight mb-0.5">Dynamics Feature Processed</p>
              <p class="text-[10px] text-slate-500 leading-tight">Over 3 sources integrated into dynamic model optimization.</p>
            </div>
          </div>
          <div class="p-2.5 bg-slate-50 rounded-lg flex gap-2.5 border border-slate-100">
            <div class="w-6 h-6 rounded bg-danger/10 text-danger flex-shrink-0 flex items-center justify-center">
              <span class="material-symbols-outlined text-[14px]">trending_up</span>
            </div>
            <div class="flex-1">
              <p class="text-[11px] font-bold text-slate-800 leading-tight mb-0.5">Expenses Spike Identified</p>
              <p class="text-[10px] text-slate-500 leading-tight">Operating expenses show an unexpected week-over-week increase.</p>
            </div>
          </div>
          <div class="p-2.5 bg-slate-50 rounded-lg flex gap-2.5 border border-slate-100">
            <div class="w-6 h-6 rounded bg-primary/10 text-primary flex-shrink-0 flex items-center justify-center">
              <span class="material-symbols-outlined text-[14px]">insights</span>
            </div>
            <div class="flex-1">
              <p class="text-[11px] font-bold text-slate-800 leading-tight mb-0.5">HR Positive Trend Alert</p>
              <p class="text-[10px] text-slate-500 leading-tight">High retention rate correlates with lower hiring costs.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Row 3: Bar / Pie / Stacked Bar -->
    <section class="grid grid-cols-12 gap-4">
      <!-- Left: Department Performance (Bar Chart sim) -->
      <div class="col-span-5 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col h-[260px]">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-[13px] text-slate-800">Department Performance</h3>
          <div class="flex items-center border border-slate-200 rounded text-[10px] font-medium overflow-hidden">
            <button class="px-2.5 py-1 bg-slate-100 text-slate-800 border-r border-slate-200">Profit</button>
            <button class="px-2.5 py-1 text-slate-500 hover:bg-slate-50">Rev</button>
          </div>
        </div>
        <div class="flex-1 flex flex-col justify-around py-2">
          <div>
            <div class="flex justify-between text-[11px] font-medium mb-1.5"><span class="text-slate-600">Finance</span><span class="text-slate-900 font-bold">₹1.52 Cr</span></div>
            <div class="w-full bg-slate-100 rounded-full h-2"><div class="bg-primary h-2 rounded-full" style="width: 75%"></div></div>
          </div>
          <div>
            <div class="flex justify-between text-[11px] font-medium mb-1.5"><span class="text-slate-600">Sales</span><span class="text-slate-900 font-bold">₹1.28 Cr</span></div>
            <div class="w-full bg-slate-100 rounded-full h-2"><div class="bg-danger h-2 rounded-full" style="width: 65%"></div></div>
          </div>
          <div>
            <div class="flex justify-between text-[11px] font-medium mb-1.5"><span class="text-slate-600">IT</span><span class="text-slate-900 font-bold">₹0.96 Cr</span></div>
            <div class="w-full bg-slate-100 rounded-full h-2"><div class="bg-warning h-2 rounded-full" style="width: 50%"></div></div>
          </div>
          <div>
            <div class="flex justify-between text-[11px] font-medium mb-1.5"><span class="text-slate-600">Marketing</span><span class="text-slate-900 font-bold">₹1.75 Cr</span></div>
            <div class="w-full bg-slate-100 rounded-full h-2"><div class="bg-success h-2 rounded-full" style="width: 85%"></div></div>
          </div>
          <div>
            <div class="flex justify-between text-[11px] font-medium mb-1.5"><span class="text-slate-600">HR</span><span class="text-slate-900 font-bold">₹0.28 Cr</span></div>
            <div class="w-full bg-slate-100 rounded-full h-2"><div class="bg-sky-400 h-2 rounded-full" style="width: 30%"></div></div>
          </div>
        </div>
      </div>
      <!-- Center: Expense Distribution -->
      <div class="col-span-3 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col items-center justify-center h-[260px]">
        <div class="w-full flex justify-between items-center mb-2">
            <h3 class="font-bold text-[13px] text-slate-800">Expense Distribution</h3>
            <span class="material-symbols-outlined text-[16px] text-slate-400 cursor-pointer">more_vert</span>
        </div>
        <div class="flex-1 w-full flex items-center justify-center relative">
            <svg viewBox="0 0 36 36" class="w-40 h-40 transform -rotate-90">
              <circle cx="18" cy="18" r="12" fill="none" stroke="#ef4444" stroke-width="8" stroke-dasharray="30 70" stroke-dashoffset="0"></circle>
              <circle cx="18" cy="18" r="12" fill="none" stroke="#10b981" stroke-width="8" stroke-dasharray="25 75" stroke-dashoffset="-30"></circle>
              <circle cx="18" cy="18" r="12" fill="none" stroke="#5b5ceb" stroke-width="8" stroke-dasharray="20 80" stroke-dashoffset="-55"></circle>
              <circle cx="18" cy="18" r="12" fill="none" stroke="#f59e0b" stroke-width="8" stroke-dasharray="15 85" stroke-dashoffset="-75"></circle>
              <circle cx="18" cy="18" r="12" fill="none" stroke="#38bdf8" stroke-width="8" stroke-dasharray="10 90" stroke-dashoffset="-90"></circle>
            </svg>
        </div>
      </div>
      <!-- Right: Cash Flow Trend -->
      <div class="col-span-4 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col h-[260px]">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-bold text-[13px] text-slate-800">Cash Flow Trend</h3>
          <select id="ctrl-cf-agg" class="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-[10px] font-semibold text-slate-700">
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <div class="flex-1 w-full relative" id="chart-cash-flow-container">
          <div id="chart-cash-flow" class="absolute inset-0"></div>
        </div>
      </div>
    </section>

    <!-- Row 4: Budget & Recommendations -->
    <section class="grid grid-cols-12 gap-4">
      <!-- Left: Budget vs Actual -->
      <div class="col-span-6 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col h-[260px]">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-bold text-[13px] text-slate-800">Budget vs Actual</h3>
          <select id="ctrl-bdg-agg" class="bg-slate-50 border border-slate-200 rounded px-2 py-1 text-[10px] font-semibold text-slate-700">
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <div class="flex-1 w-full relative" id="chart-budget-container">
          <div id="chart-budget-actual" class="absolute inset-0"></div>
        </div>
      </div>
      <!-- Right: Recommendation Engine -->
      <div class="col-span-6 bg-white rounded-[12px] p-4 shadow-sm border border-outline-variant/20 flex flex-col h-[260px]">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3 mb-2">
          <div class="flex items-center gap-1.5">
            <span class="material-symbols-outlined text-primary text-[15px]">auto_awesome</span>
            <h3 class="font-bold text-[13px] text-slate-800">Recommendation Engine</h3>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto custom-scrollbar space-y-1 pr-2">
          <!-- Rec 1 -->
          <div class="flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors">
            <div class="w-7 h-7 rounded bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-[14px]">trending_down</span>
            </div>
            <div class="flex-1">
              <h4 class="text-[11px] font-bold text-slate-800 mb-0.5">Automated Budget Reallocated</h4>
              <p class="text-[10px] text-slate-500 leading-snug">Reallocated funds from low-ROI channels to high-yield optimization.</p>
            </div>
            <div class="text-right">
                <span class="text-[11px] font-bold text-success">-₹2.12M</span><br>
                <span class="text-[9px] font-medium text-slate-400">Impact</span>
            </div>
          </div>
          <!-- Rec 2 -->
          <div class="flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors">
            <div class="w-7 h-7 rounded bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-[14px]">monetization_on</span>
            </div>
            <div class="flex-1">
              <h4 class="text-[11px] font-bold text-slate-800 mb-0.5">Expense Spike Identified</h4>
              <p class="text-[10px] text-slate-500 leading-snug">Operating expenses are up due to unrecognized headcount overhead balances.</p>
            </div>
            <div class="text-right">
                <span class="text-[11px] font-bold text-danger">+₹480.5k</span><br>
                <span class="text-[9px] font-medium text-slate-400">Impact</span>
            </div>
          </div>
          <!-- Rec 3 -->
          <div class="flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors">
            <div class="w-7 h-7 rounded bg-success/10 text-success flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-[14px]">trending_up</span>
            </div>
            <div class="flex-1">
              <h4 class="text-[11px] font-bold text-slate-800 mb-0.5">HR Positive Trend Alert</h4>
              <p class="text-[10px] text-slate-500 leading-snug">Audit into departments for cost reduction.</p>
            </div>
            <div class="text-right">
                <span class="text-[11px] font-bold text-success">-1.4%</span><br>
                <span class="text-[9px] font-medium text-slate-400">Costs</span>
            </div>
          </div>
        </div>
      </div>
    </section>

  </div>
  
  <!-- Add dummy hidden tables to prevent wiring JS errors -->
  <table class="hidden"><tbody id="dept-table-body"></tbody></table>
  <div id="recent-uploads-container" class="hidden"></div>
  <div id="workflow-status-container" class="hidden"></div>

  <!-- Footer Status Bar -->
  <footer class="fixed bottom-0 right-0 left-[240px] h-10 bg-white/95 backdrop-blur-md border-t border-outline-variant/30 px-6 flex items-center justify-between text-[10px] font-medium text-slate-500 z-40">
    <div class="flex items-center gap-6">
      <div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[13px]">bar_chart</span><span>Data Quality Score: <span class="text-success font-bold">98%</span></span></div>
      <div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[13px]">schedule</span><span>Last Updated: <span class="text-slate-800 font-bold">2 mins ago</span></span></div>
      <div class="flex items-center gap-1.5"><span class="material-symbols-outlined text-[13px]">group</span><span>Active Users: <span class="text-slate-800 font-bold">12</span></span></div>
    </div>
    <div class="flex items-center gap-1.5">
      <div class="w-2 h-2 bg-success rounded-full shadow-[0_0_4px_#10b981]"></div>
      <span class="font-bold text-slate-700">All Systems Operational</span>
    </div>
  </footer>
</main>"""

# Find the main tag
main_pattern = re.compile(r'<main.*?</main>', re.DOTALL)
html = main_pattern.sub(new_main_content, html)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Dashboard rewritten successfully!")
