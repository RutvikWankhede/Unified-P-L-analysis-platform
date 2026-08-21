import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

def generate_synthetic_dataset(num_rows=1200):
    np.random.seed(42)
    random.seed(42)
    
    departments = ["Sales", "Finance", "R&D", "Marketing", "IT", "Operations", "HR", "Legal"]
    business_units = ["Enterprise", "Retail", "Cloud Solutions", "Consulting Services"]
    regions = ["North", "South", "East", "West"]
    products = ["Software Subscription", "Hardware Purchase", "Consulting Hours", "Premium Support"]
    categories = {
        "Revenue": ["Software Subscription", "Hardware Purchase", "Consulting Hours", "Premium Support"],
        "Expense": ["Salaries", "Cloud Infrastructure", "Marketing Spend", "Office Rent", "Travel", "Software Licenses", "Consulting Fees", "Legal Fees"]
    }
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 6, 30)
    delta_days = (end_date - start_date).days
    
    rows = []
    
    for i in range(num_rows):
        days_offset = random.randint(0, delta_days)
        current_date = start_date + timedelta(days=days_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        
        dept = random.choice(departments)
        bu = random.choice(business_units)
        region = random.choice(regions)
        prod = random.choice(products)
        
        txn_type = "Revenue" if random.random() > 0.45 else "Expense"
        cat = random.choice(categories[txn_type])
        
        quantity = random.randint(1, 150)
        if prod == "Software Subscription":
            price = random.uniform(500, 2000)
        elif prod == "Hardware Purchase":
            price = random.uniform(1000, 5000)
        elif prod == "Consulting Hours":
            price = random.uniform(150, 300)
        else:
            price = random.uniform(200, 800)
            
        base_amt = quantity * price
        
        month = current_date.month
        seasonality_factor = 1.0
        if month == 12:
            seasonality_factor = 1.35 if txn_type == "Revenue" else 1.10
        elif month in [1, 2]:
            seasonality_factor = 0.85 if txn_type == "Revenue" else 1.25
            
        amount = base_amt * seasonality_factor
        
        years_elapsed = (current_date - start_date).days / 365.0
        growth_factor = 1.0 + (0.08 * years_elapsed)
        amount *= growth_factor
        
        is_anomaly = False
        anomaly_reason = ""
        if dept == "IT" and txn_type == "Expense" and current_date.year == 2025 and month == 3 and random.random() < 0.15:
            amount *= 4.5
            is_anomaly = True
            anomaly_reason = "Cloud Infrastructure billing anomaly (4.5x spike)"
        elif dept == "Sales" and txn_type == "Revenue" and current_date.year == 2025 and month == 12 and random.random() < 0.10:
            amount *= 3.0
            is_anomaly = True
            anomaly_reason = "End of year enterprise software subscription deal"
            
        amount = round(amount, 2)
        
        if txn_type == "Revenue":
            rev_amt = amount
            exp_amt = 0.0
            cogs = round(amount * random.uniform(0.15, 0.35), 2)
            profit = round(rev_amt - cogs, 2)
            
            cash_in = amount
            cash_out = cogs
            
            budget_rev = round(rev_amt * random.uniform(0.90, 1.15), 2)
            budget_exp = round(cogs * random.uniform(0.95, 1.10), 2)
        else:
            rev_amt = 0.0
            exp_amt = amount
            cogs = 0.0
            profit = -amount
            
            cash_in = 0.0
            cash_out = amount
            
            budget_rev = 0.0
            budget_exp = round(exp_amt * random.uniform(0.85, 1.15), 2)
            
        rows.append({
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "date": date_str,
            "department": dept,
            "business_unit": bu,
            "region": region,
            "product": prod,
            "category": cat,
            "transaction_type": txn_type,
            "revenue": rev_amt,
            "cogs": cogs,
            "expense": exp_amt,
            "profit": profit,
            "budget_revenue": budget_rev,
            "budget_expense": budget_exp,
            "cash_inflow": cash_in,
            "cash_outflow": cash_out,
            "quantity": quantity,
            "price": round(price, 2),
            "currency": "USD" if random.random() > 0.15 else random.choice(["EUR", "GBP"]),
            "is_anomaly": is_anomaly,
            "anomaly_reason": anomaly_reason
        })
        
    df = pd.DataFrame(rows)
    df.sort_values(by="date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

if __name__ == "__main__":
    df = generate_synthetic_dataset()
    df.to_csv("synthetic_dataset.csv", index=False)
    print("Generated 1200 rows of synthetic dataset successfully.")
