import pandas as pd
import json

df = pd.read_csv("unified_pnl_enterprise_demo.csv")

depts = sorted(df['Department'].unique().tolist())
min_d = str(df['Date'].min())
max_d = str(df['Date'].max())
total_rev = float(df['Revenue'].sum())
total_exp = float(df['Expense'].sum())
total_profit = float(df['Profit'].sum())
total_budget = float(df['Budget'].sum())
avg_margin = float(df['Profit_Margin_Pct'].mean())

dept_summary = {}
for d, g in df.groupby('Department'):
    dept_summary[d] = {
        "records": len(g),
        "revenue": float(g['Revenue'].sum()),
        "expense": float(g['Expense'].sum()),
        "profit": float(g['Profit'].sum()),
        "budget": float(g['Budget'].sum()),
        "margin_pct": round(float(g['Profit'].sum() / g['Revenue'].sum() * 100), 2)
    }

output = {
    "filename": "unified_pnl_enterprise_demo.csv",
    "total_rows": len(df),
    "columns": list(df.columns),
    "date_range": {"min": min_d, "max": max_d},
    "departments": depts,
    "totals": {
        "revenue": total_rev,
        "expense": total_exp,
        "profit": total_profit,
        "budget": total_budget,
        "net_margin_pct": round(total_profit / total_rev * 100, 2)
    },
    "dept_breakdown": dept_summary
}

with open("dataset_details.json", "w") as f:
    json.dump(output, f, indent=2)

print("Dataset details saved. Summary:")
print(f"Total Rows: {len(df)}")
print(f"Date Range: {min_d} to {max_d}")
print(f"Departments ({len(depts)}): {', '.join(depts)}")
print(f"Total Revenue: {total_rev:,.2f}")
print(f"Total Expense: {total_exp:,.2f}")
print(f"Total Profit: {total_profit:,.2f}")
