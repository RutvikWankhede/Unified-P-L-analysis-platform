import re
from pathlib import Path

def test_frontend_integrity():
    dash_html_path = Path("frontend_v2/dashboard.html")
    wiring_js_path = Path("frontend_v2/js/dashboard_wiring.js")
    
    assert dash_html_path.exists(), "dashboard.html does not exist"
    assert wiring_js_path.exists(), "dashboard_wiring.js does not exist"
    
    html = dash_html_path.read_text(encoding="utf-8")
    js = wiring_js_path.read_text(encoding="utf-8")
    
    # 1. Expense Distribution Metric Selector
    assert 'id="ctrl-exp-dist-metric"' in html, "ctrl-exp-dist-metric missing in dashboard.html"
    assert 'id="ctrl-exp-dist-dept"' in html, "ctrl-exp-dist-dept missing in dashboard.html"
    assert 'id="title-dist-card"' in html, "title-dist-card missing in dashboard.html"
    assert 'value="expense"' in html, "expense option missing"
    assert 'value="revenue"' in html, "revenue option missing"
    assert 'value="profit"' in html, "profit option missing"
    assert 'value="margin_pct"' in html, "margin_pct option missing"
    
    # 2. JS Wiring for Distribution
    assert 'loadExpenseDistribution(metric = \'expense\', dept = \'all\')' in js or 'loadExpenseDistribution(' in js
    assert 'ctrlExpDistMetric' in js, "ctrlExpDistMetric missing in JS"
    assert 'ctrlExpDistDept' in js, "ctrlExpDistDept missing in JS"
    assert 'ctrlExpDistMetric.addEventListener(\'change\', triggerExpDist)' in js, "metric change listener missing"
    assert 'ctrlExpDistDept.addEventListener(\'change\', triggerExpDist)' in js, "dept change listener missing"
    
    # 3. Tooltip styling (White background, subtle shadow, dark text)
    white_tooltip_count = js.count("backgroundColor: '#ffffff'")
    print(f"[OK] Found {white_tooltip_count} white tooltip configurations in dashboard_wiring.js")
    assert white_tooltip_count >= 5, "Not all chart tooltips updated to white background"
    
    # 4. Modals - Enlarged Typography
    assert 'id="modal-insights"' in html, "modal-insights missing"
    assert 'id="modal-recommendations"' in html, "modal-recommendations missing"
    assert 'font-bold text-sm text-slate-900' in js, "Enlarged modal title typography missing in JS"
    assert 'text-xs text-slate-700 leading-relaxed' in js, "Enlarged modal body typography missing in JS"
    assert 'btn-view-all-insights' in html, "btn-view-all-insights missing"
    assert 'btn-view-all-recommendations' in html, "btn-view-all-recommendations missing"
    
    # 5. Department Performance & Time Aggregations
    assert 'ctrlDeptMetric' in js, "ctrlDeptMetric missing"
    assert 'ctrlDeptRange' in js, "ctrlDeptRange missing"
    assert 'triggerDeptPerf' in js, "triggerDeptPerf missing"
    
    print("[SUCCESS] All frontend HTML and JS integrity checks PASSED 100%!")

if __name__ == "__main__":
    test_frontend_integrity()
