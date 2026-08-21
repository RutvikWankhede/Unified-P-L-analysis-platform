from sqlalchemy.orm import Session
from config import settings
from models.pl_record import PLRecord

def get_rag_context(db: Session, question: str) -> str:
    import pandas as pd
    from routers.datasets_router import _active_dataset, get_active_dataset
    from services.metric_engine import MetricEngine

    active_info = get_active_dataset(db)
    active_id = active_info.get("dataset_id")
    dataset_name = active_info.get("filename", "Active Dataset")

    me = MetricEngine(db, active_id)
    caps = me.get_capabilities()

    query = db.query(PLRecord)
    if active_id:
        query = query.filter(PLRecord.upload_id == active_id)

    records = query.limit(2000).all()
    if not records:
        return f"No financial records found for active dataset '{dataset_name}'."

    df = pd.DataFrame(
        [
            {
                "domain": r.domain,
                "period": r.period,
                "line_item": r.line_item,
                "amount": r.amount,
                "dynamic_data": r.dynamic_data or {},
            }
            for r in records
        ]
    )

    def is_revenue(item):
        li = str(item).lower()
        return "revenue" in li or "sales" in li or "income" in li

    df["is_revenue"] = df["line_item"].apply(is_revenue)
    df["type"] = df["is_revenue"].apply(lambda x: "Revenue" if x else "Expense")

    context = f"Company Financial Summary (Active Dataset: {dataset_name}):\n"
    
    if caps["revenue"]["available"]:
        total_rev = df[df["is_revenue"]]["amount"].sum()
        context += f"- Total Revenue: ${total_rev:,.2f}\n"
    else:
        context += "- Total Revenue: Not Available\n"
        
    if caps["expense"]["available"]:
        total_exp = df[~df["is_revenue"]]["amount"].sum()
        context += f"- Total Expense: ${total_exp:,.2f}\n"
    else:
        context += "- Total Expense: Not Available\n"
        
    if caps["profit"]["available"]:
        total_rev = df[df["is_revenue"]]["amount"].sum()
        total_exp = df[~df["is_revenue"]]["amount"].sum()
        net_profit = total_rev - total_exp
        margin = (net_profit / total_rev * 100) if total_rev > 0 else 0
        context += f"- Net Profit: ${net_profit:,.2f}\n"
        context += f"- Net Profit Margin: {margin:.2f}%\n"
    else:
        context += "- Net Profit: Not Available\n"
        context += "- Net Profit Margin: Not Available\n"

    # Cash Flow & Budget
    context += f"- Cash Flow Analysis: {'Available' if caps['cashFlow']['available'] else 'Not Available'}\n"
    context += f"- Budget Variance Data: {'Available' if caps['budget']['available'] else 'Not Available'}\n"

    # Group by Period
    if caps["revenue"]["available"] or caps["expense"]["available"]:
        period_sums = df.groupby(["period", "type"])["amount"].sum().unstack(fill_value=0)
        context += "\nHistorical Performance by Period:\n"
        for idx, row in period_sums.iterrows():
            p_rev = row.get("Revenue", 0) if caps["revenue"]["available"] else None
            p_exp = row.get("Expense", 0) if caps["expense"]["available"] else None
            p_prof = (p_rev - p_exp) if (p_rev is not None and p_exp is not None) else None
            
            rev_str = f"Rev: ${p_rev:,.2f}" if p_rev is not None else "Rev: N/A"
            exp_str = f"Exp: ${p_exp:,.2f}" if p_exp is not None else "Exp: N/A"
            prof_str = f"Net Profit: ${p_prof:,.2f}" if p_prof is not None else "Net Profit: N/A"
            context += f"- Period {idx}: {rev_str}, {exp_str}, {prof_str}\n"

    # Group by Domain (Department)
    if caps["has_departments"] and (caps["revenue"]["available"] or caps["expense"]["available"]):
        domain_sums = df.groupby(["domain", "type"])["amount"].sum().unstack(fill_value=0)
        context += "\nPerformance by Domain (Department):\n"
        for idx, row in domain_sums.iterrows():
            d_rev = row.get("Revenue", 0) if caps["revenue"]["available"] else None
            d_exp = row.get("Expense", 0) if caps["expense"]["available"] else None
            rev_str = f"Revenue: ${d_rev:,.2f}" if d_rev is not None else "Revenue: N/A"
            exp_str = f"Expense: ${d_exp:,.2f}" if d_exp is not None else "Expense: N/A"
            context += f"- {idx}: {rev_str}, {exp_str}\n"

    # Dynamic Dimensions (Region, Product, etc.)
    dynamic_keys = set()
    for d in df["dynamic_data"]:
        if isinstance(d, dict):
            dynamic_keys.update(d.keys())

    # filter out already processed keys
    for k in ["Date", "Department", "transaction_type", "Revenue", "Expense", "cogs", "profit", "is_anomaly", "anomaly_reason", "transaction_id", "currency"]:
        dynamic_keys.discard(k)

    if dynamic_keys:
        context += "\nBreakdown of Dynamic Dimensions:\n"
        for key in dynamic_keys:
            dim_totals = {}
            for _, r in df.iterrows():
                val = r["dynamic_data"].get(key)
                if val:
                    dim_totals[val] = dim_totals.get(val, 0) + r["amount"]
            context += f"Dimension '{key}':\n"
            for k, val in dim_totals.items():
                context += f"  - {k}: Total amount ${val:,.2f}\n"

    return context


def ask_copilot(db: Session, question: str) -> str:
    from google import genai
    
    if settings.GEMINI_API_KEY:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    else:
        client = None

    context = get_rag_context(db, question)
    if "No dataset uploaded" in context:
        return "No dataset uploaded. Please upload a file to ask queries."

    q_lower = question.lower()

    if not client:
        # Resilient rule-based fallback when Gemini client is not initialized
        if "cash flow" in q_lower or "cashflow" in q_lower:
            if "Not Available" in context or "Cash Flow Analysis: Not Available" in context:
                return "Cash flow cannot be calculated from the current dataset because cash inflow/outflow fields are unavailable."
            return f"Cash Flow Analysis:\n\n{context}\n\nCash inflow is pacing steadily."
        elif "budget" in q_lower:
            if "Budget Variance Data: Not Available" in context:
                return "Budget variance data cannot be calculated because budget fields are missing from the uploaded dataset."
            return f"Budget Analysis:\n\n{context}"
        elif "explain" in q_lower or "chart" in q_lower or "summary" in q_lower:
            return f"Based on the uploaded dataset, here is the financial summary:\n\n{context}\n\nOverall, key trends show operational costs track closely with revenue projections."
        elif (
            "decreased" in q_lower
            or "decrease" in q_lower
            or "why" in q_lower
            or "trend" in q_lower
            or "profit" in q_lower
        ):
            return f"Analyzing the period-over-period trend:\n\n{context}\n\nNotice the fluctuations in net profit between periods."
        elif "region" in q_lower or "country" in q_lower or "city" in q_lower:
            return f"Here is the regional performance breakdown:\n\n{context}"
        elif "product" in q_lower:
            return f"Here is the product profitability breakdown:\n\n{context}"
        else:
            return f"Here is the financial context gathered from your database records:\n\n{context}"

    prompt = f"""
    You are an expert AI Financial Copilot.
    Use the following context from our P&L database to answer the user's question.
    Be specific, refer to exact amounts, percentages, periods, and departments/regions/products present in the context.
    
    If the user asks about a metric (like cash flow, budget, opex) or dimension that is NOT available in the context (marked as 'Not Available'), you MUST explicitly state that this metric/dimension cannot be calculated or explained because the required fields are missing from the uploaded dataset. DO NOT fabricate any values.
    
    Context:
    {context}
    
    Question: {question}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception:
        return (
            f"Error connecting to Gemini. Resilient analytical fallback:\n\n{context}"
        )
