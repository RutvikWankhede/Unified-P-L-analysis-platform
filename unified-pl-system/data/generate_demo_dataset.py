import csv
import random
from datetime import datetime, timedelta

def generate_dataset(filename="unified_pnl_demo_dataset.csv", num_rows=1250):
    departments = ["Finance", "Sales", "Marketing", "IT", "HR", "Operations", "Procurement", "Logistics", "R&D", "Legal", "Administration", "Customer Support"]
    revenue_categories = ["Product Sales", "Service Revenue", "Subscription Revenue", "Consulting Revenue", "Other Revenue"]
    expense_categories = ["Salaries", "Marketing", "Software", "Cloud Infrastructure", "Office", "Travel", "Logistics", "Procurement", "Utilities", "Professional Services", "Training", "Maintenance"]
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    days_range = (end_date - start_date).days

    # Some messiness
    messy_dates = [True, False, False, False, False]
    messy_amounts = [True, False, False, False, False]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_id", "date", "department", "category", "description", "transaction_type", "amount", "currency", "status"])
        
        for i in range(num_rows):
            txn_id = f"TXN-{random.randint(100000, 999999)}"
            
            day_offset = random.randint(0, days_range)
            txn_date = start_date + timedelta(days=day_offset)
            
            # Seasonal boost in Q4
            if txn_date.month in [10, 11, 12] and random.random() < 0.3:
                is_q4_boost = True
            else:
                is_q4_boost = False

            dept = random.choice(departments)
            txn_type = random.choices(["Revenue", "Expense"], weights=[0.45, 0.55])[0]
            
            if txn_type == "Revenue":
                cat = random.choice(revenue_categories)
                amount = round(random.uniform(5000, 150000), 2)
                if is_q4_boost:
                    amount *= random.uniform(1.2, 2.0)
            else:
                cat = random.choice(expense_categories)
                amount = round(random.uniform(1000, 50000), 2)
                
            # Add some anomalies (spikes or drops)
            if random.random() < 0.02:
                amount *= random.uniform(5.0, 10.0)
                
            desc = f"{cat} related to {dept}"
            currency = random.choices(["USD", "EUR", "GBP"], weights=[0.8, 0.1, 0.1])[0]
            status = "Completed"
            
            # Formatting the date
            date_str = txn_date.strftime("%Y-%m-%d")
            if random.choice(messy_dates):
                date_str = txn_date.strftime("%d/%m/%Y")
                
            # Formatting the amount
            amount_str = f"{amount:.2f}"
            if random.choice(messy_amounts):
                amount_str = f"${amount:,.2f}" if currency == "USD" else amount_str
            
            # Sometimes duplicate rows
            writer.writerow([txn_id, date_str, dept, cat, desc, txn_type, amount_str, currency, status])
            if random.random() < 0.005:  # 0.5% chance of exact duplicate
                writer.writerow([txn_id, date_str, dept, cat, desc, txn_type, amount_str, currency, status])
                
        print(f"Generated {filename} successfully with {num_rows} base rows (plus some duplicates).")

if __name__ == "__main__":
    generate_dataset()
