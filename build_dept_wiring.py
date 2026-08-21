import os
content = open(r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2\js\departments_wiring.js', 'r').read()
new_content = '''import { generatePalette, initEchart, safeSetOption } from './chart-engine.js';

document.addEventListener('DOMContentLoaded', () => {
    const formatCurrency = (val) => {
        if (!val && val !== 0) return '₹0';
        if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
        if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
        return `₹${val.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;
    };
    
    // Wire KPIs
    fetch('/api/v1/pl/departments')
        .then(r => r.json())
        .then(data => {
            let totRev = 0, totExp = 0;
            data.forEach(d => {
                totRev += (d.revenue || 0);
                totExp += (d.expense || 0);
            });
            const totProfit = totRev - totExp;
            
            const revEl = document.getElementById('kpi-total-revenue');
            if(revEl) revEl.innerText = formatCurrency(totRev);
            
            const expEl = document.getElementById('kpi-total-expense');
            if(expEl) expEl.innerText = formatCurrency(totExp);
            
            const profEl = document.getElementById('kpi-net-profit');
            if(profEl) profEl.innerText = formatCurrency(totProfit);
            
            const healthEl = document.getElementById('kpi-health-score');
            if(healthEl && totRev > 0) {
                healthEl.innerText = ((totProfit / totRev) * 100).toFixed(1) + "%";
            }

            // Populate Table
            const tbody = document.getElementById('dept-table-body');
            if(tbody) {
                const template = tbody.querySelector('[data-row-template="true"]');
                if(template) {
                    template.style.display = 'none';
                    const nodesToRemove = [];
                    Array.from(tbody.children).forEach(child => {
                        if (!child.hasAttribute('data-row-template')) {
                            nodesToRemove.push(child);
                        }
                    });
                    nodesToRemove.forEach(n => n.remove());

                    data.forEach(d => {
                        const clone = template.cloneNode(true);
                        clone.removeAttribute('data-row-template');
                        clone.style.display = '';
                        const nameEl = clone.querySelector('span.font-semibold');
                        if(nameEl) nameEl.innerText = d.domain || 'N/A';
                        const tds = clone.querySelectorAll('td');
                        if(tds.length >= 4) {
                            tds[1].innerText = formatCurrency(d.revenue);
                            tds[2].innerText = formatCurrency(d.expense);
                            tds[3].innerText = formatCurrency(d.profit);
                        }
                        tbody.appendChild(clone);
                    });
                }
            }
            
            // ECharts chart
            const canvasContainer = document.getElementById('chart-department-profit');
            if (canvasContainer) {
                const chart = initEchart(canvasContainer);
                const categories = data.map(d => d.domain || 'Unknown');
                const revenues = data.map(d => d.revenue || 0);
                const expenses = data.map(d => d.expense || 0);
                
                safeSetOption(chart, {
                    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
                    legend: { data: ['Revenue', 'Expense'], bottom: 0 },
                    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
                    xAxis: { type: 'value' },
                    yAxis: { type: 'category', data: categories },
                    series: [
                        { name: 'Revenue', type: 'bar', data: revenues, itemStyle: { color: '#5b5ceb' } },
                        { name: 'Expense', type: 'bar', data: expenses, itemStyle: { color: '#ef4444' } }
                    ]
                });
                window.addEventListener('resize', () => chart.resize());
            }
        }).catch(e => console.error("Error fetching departments", e));
});
'''
with open(r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2\js\departments_wiring.js', 'w', encoding='utf-8') as f:
    f.write(new_content)
