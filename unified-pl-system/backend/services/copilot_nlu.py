"""
copilot_nlu.py - Natural Language Understanding for Financial Copilot
=====================================================================
Accurate multi-intent decomposition, metric detection, ordinal rank extraction,
direction detection, multi-item limits, entity extraction, time context,
and compound financial query parsing.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


ORDINAL_MAP = {
    "1st": 1, "first": 1, "#1": 1, "one": 1,
    "2nd": 2, "second": 2, "#2": 2, "two": 2,
    "3rd": 3, "third": 3, "#3": 3, "three": 3,
    "4th": 4, "fourth": 4, "#4": 4, "four": 4,
    "5th": 5, "fifth": 5, "#5": 5, "five": 5,
    "6th": 6, "sixth": 6, "#6": 6, "six": 6,
    "7th": 7, "seventh": 7, "#7": 7, "seven": 7,
    "8th": 8, "eighth": 8, "#8": 8, "eight": 8,
    "9th": 9, "ninth": 9, "#9": 9, "nine": 9,
    "10th": 10, "tenth": 10, "#10": 10, "ten": 10,
    "11th": 11, "eleventh": 11, "#11": 11,
    "12th": 12, "twelfth": 12, "#12": 12,
}

WORD_NUMBER_MAP = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "all": 999,
}


def detect_rank_and_limit(q_lower: str) -> Tuple[int, Optional[int]]:
    """
    Extract requested rank (1-indexed ordinal) and multi-item limit (e.g. top 3).
    Returns (rank, limit):
      - rank: 1 for lowest/highest, 2 for 2nd lowest/2nd highest, etc.
      - limit: None for single rank request, or N for multi-item requests (e.g. top 3 -> (1, 3)).
    """
    # 1. Multi-item limit expressions: "top 3", "top three", "bottom 5", "first 3", "last 3"
    top_n_match = re.search(r"\b(?:top|best|highest|leading)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|all)\b", q_lower)
    if top_n_match:
        val_str = top_n_match.group(1)
        lim = int(val_str) if val_str.isdigit() else WORD_NUMBER_MAP.get(val_str, 3)
        return (1, lim)

    bot_n_match = re.search(r"\b(?:bottom|worst|lowest|least)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|all)\b", q_lower)
    if bot_n_match:
        val_str = bot_n_match.group(1)
        lim = int(val_str) if val_str.isdigit() else WORD_NUMBER_MAP.get(val_str, 3)
        return (1, lim)

    # 2. "ranks #2", "rank #2", "rank 2", "position 2", "#2"
    rank_hash_match = re.search(r"\b(?:ranks?|positions?|#)\s*#?(\d+)\b", q_lower)
    if rank_hash_match:
        return (max(1, int(rank_hash_match.group(1))), None)

    # 3. Explicit ordinals: "2nd least", "second-lowest", "second lowest", "3rd highest", "second best", "2nd worst"
    for ord_word, rank_num in ORDINAL_MAP.items():
        pat = r"\b" + re.escape(ord_word) + r"[-\s]+(?:most|least|highest|lowest|best|worst|top|bottom|profitable|revenue|expense|margin|cost|spending|anomal|department|division)\b"
        if re.search(pat, q_lower):
            return (rank_num, None)
        from_pat = r"\b" + re.escape(ord_word) + r"[-\s]+(?:from\s+(?:the\s+)?)?(?:bottom|top)\b"
        if re.search(from_pat, q_lower):
            return (rank_num, None)

    # 4. Regex for generic \d+(?:st|nd|rd|th)
    gen_ord = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", q_lower)
    if gen_ord:
        return (max(1, int(gen_ord.group(1))), None)

    # 5. Full ranking list request
    if any(w in q_lower for w in ["rank departments", "ranking of departments", "rank all", "department ranking", "ranked list", "rankings"]):
        return (1, 999)

    return (1, None)


def detect_direction(q_lower: str) -> str:
    """
    Detect whether the user wants the MINIMUM or MAXIMUM value.
    Returns 'min' for worst/least/lowest/bottom/declining queries,
            'max' for best/highest/most/top/fastest queries (default).
    """
    if "from the bottom" in q_lower or "from bottom" in q_lower:
        return "min"
    if "from the top" in q_lower or "from top" in q_lower:
        return "max"

    min_phrases = [
        "least profitable", "least profit", "lowest profit", "minimum profit", "worst profit", "smallest profit", "bottom profit",
        "least revenue", "lowest revenue", "minimum revenue", "smallest revenue", "bottom revenue",
        "least expense", "lowest expense", "minimum expense", "smallest expense", "lowest cost", "least cost", "least spend", "lowest spend", "lowest spending",
        "lowest margin", "least margin", "minimum margin", "worst margin", "smallest margin", "bottom margin",
        "lowest growth", "least growth", "minimum growth", "slowest growing", "slowest growth", "decline most", "fall most", "drop most", "largest decrease", "largest decline", "shrink most", "expected to decline", "will decline", "deteriorated most", "worst performing", "lowest performing",
        "fewest anomalies", "least anomalies", "lowest anomalies", "minimum anomalies", "fewest outlier", "least outlier",
        "fewest", "smallest", "bottom", "worst", "lowest", "least", "minimum", "decline", "declining", "underperforming", "underperformer"
    ]
    for phrase in min_phrases:
        if phrase in q_lower:
            return "min"

    min_tokens = ["least ", "lowest ", "minimum ", "worst ", "smallest ", "fewest ", "decline "]
    for tok in min_tokens:
        if tok in q_lower:
            return "min"

    return "max"


def detect_time_context(q_lower: str) -> str:
    """Detect whether query pertains to FUTURE/FORECAST or CURRENT/HISTORICAL data."""
    future_indicators = [
        "will be", "in future", "future", "projected", "forecast", "forecasted",
        "next year", "next quarter", "next month", "after 1 month", "after 2 months",
        "after 3 months", "after 6 months", "after 12 months", "in 1 month", "in 2 months",
        "in 3 months", "in 6 months", "upcoming", "likely to", "growing to", "expected to",
        "will grow", "will decline", "will have", "project", "will happen", "forward"
    ]
    if any(w in q_lower for w in future_indicators):
        return "future"
    if re.search(r"(?:after|in|next)\s+\d+\s+months?", q_lower):
        return "future"
    return "historical"


def detect_primary_metric(q_lower: str) -> str:
    """Detect primary financial metric: profit, revenue, expense, margin, growth, budget, anomalies, cash_flow, health, schema_info."""
    if any(w in q_lower for w in ["financial health", "health score", "score"]):
        return "health"
    if any(w in q_lower for w in ["grow the most", "highest growth", "fastest growing", "maximum growth",
                                  "grow most", "growth rate", "will grow", "growth", "decline most",
                                  "slowest growing", "expected to decline", "largest decrease", "fall most", "drop most"]):
        return "growth"
    if any(w in q_lower for w in ["margin", "operating margin", "profit margin", "percentage margin"]):
        return "margin"
    if any(w in q_lower for w in ["over budget", "under budget", "budget variance", "largest budget variance", "budget", "allocated target", "overspending"]):
        return "budget"
    if any(w in q_lower for w in ["anomal", "outlier", "risk", "fraud", "irregular"]):
        return "anomalies"
    if any(w in q_lower for w in ["cash flow", "cashflow", "inflow", "outflow", "liquidity", "working capital"]):
        return "cash_flow"
    if any(w in q_lower for w in ["columns", "fields", "schema", "contain", "available columns", "what columns", "available in the dataset"]):
        return "schema_info"
    if any(w in q_lower for w in ["revenue", "sales", "income", "topline", "top line", "turnover"]):
        return "revenue"
    if any(w in q_lower for w in ["expense", "expenses", "cost", "costs", "spending", "spend", "opex", "expenditure"]):
        return "expense"
    return "profit"


def detect_forecast_horizon(q_lower: str) -> int:
    """Detect forecast horizon in months."""
    m = re.search(r"(?:after|in|next)\s+(\d+)\s+month", q_lower)
    if m:
        return max(1, int(m.group(1)))
    m = re.search(r"(\d+)\s+month", q_lower)
    if m:
        return max(1, int(m.group(1)))
    if any(w in q_lower for w in ["next month", "in 1 month", "after 1 month", "1 month"]):
        return 1
    if any(w in q_lower for w in ["next quarter", "quarter", "3 month", "in 3", "after 3"]):
        return 3
    if any(w in q_lower for w in ["6 month", "next 6", "half year", "half-year"]):
        return 6
    if any(w in q_lower for w in ["next year", "12 month", "next 12", "annual", "yearly", "next 1 year"]):
        return 12
    return 12


def decompose_intents(question: str) -> List[Dict[str, Any]]:
    """
    Deconstructs natural language financial questions into one or more structured analytical intents.
    Guarantees that compound questions (e.g. ranking + what-if, multi-ranking, ranking + margin)
    are fully planned and deterministically evaluated.
    """
    q = question.strip()
    q_lower = q.lower()

    # 1. Non-financial Out of Scope
    unsupported = [
        "customer satisfaction", "csat", "nps", "headcount", "turnover rate", "employee attrition",
        "stock price", "share price", "crypto", "bitcoin", "weather", "temperature",
        "server uptime", "latencies", "bugs", "github commit", "who is the president", "who is the ceo", "who is ceo",
        "apple stock", "tesla stock", "google stock", "who won"
    ]
    if any(t in q_lower for t in unsupported):
        return [{"type": "out_of_scope", "query": q}]

    # 2. Conversational Follow-Ups
    if q_lower in ["why?", "why", "why is that?", "explain why", "why so?", "how come?"]:
        return [{"type": "follow_up_why"}]
    if q_lower in ["show me the numbers", "show numbers", "show table", "show details", "numbers please", "give me the data", "breakdown"]:
        return [{"type": "follow_up_numbers"}]
    if q_lower.startswith("what about ") or q_lower.startswith("how about ") or q_lower.startswith("and "):
        # Check if follow-up specifies an entity
        return [{"type": "follow_up_entity", "raw": q}]

    # 3. Twisted & Specific Compound Queries

    # 3.1 "Which department has the highest revenue but not the highest profit?"
    if any(w in q_lower for w in ["highest revenue but not the highest profit", "highest revenue but not highest profit", "top revenue but not top profit", "max revenue but not max profit"]):
        return [{"type": "highest_rev_not_highest_profit"}]

    # 3.2 "Which department has the lowest margin but is not the lowest-profit department?"
    if any(w in q_lower for w in ["lowest margin but not the lowest-profit", "lowest margin but not lowest profit", "worst margin but not lowest profit", "lowest margin but not the lowest profit"]):
        return [{"type": "lowest_margin_not_lowest_profit"}]

    # 3.3 "Which department has the highest expenses but is still profitable?"
    if any(w in q_lower for w in ["highest expenses but is still profitable", "highest expense but still profitable", "most expensive but profitable", "highest cost but still profitable"]):
        return [{"type": "highest_expense_still_profitable"}]

    # 3.4 "Why is the company profitable despite high expenses?"
    if any(w in q_lower for w in ["profitable despite high expenses", "profitable despite high expense", "profitable despite expenses", "profitable even though expenses"]):
        return [{"type": "profitable_despite_high_expenses"}]

    # 3.5 "Which department is responsible for the largest expense increase?"
    if any(w in q_lower for w in ["largest expense increase", "biggest expense increase", "highest expense increase", "expense grew most", "expenses increased the most"]):
        return [{"type": "largest_expense_increase_dept"}]

    # 3.6 "What happens if the largest cost center reduces expenses by 10%?"
    if any(w in q_lower for w in ["largest cost center", "top cost center", "highest spending department", "highest expense department"]) and any(w in q_lower for w in ["reduce", "reduction", "cut", "fall", "decrease", "what happens if", "simulate"]):
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", q_lower)
        pct = float(pct_match.group(1)) if pct_match else 10.0
        return [{"type": "what_if_top_cost_center", "exp_reduction_pct": pct}]

    # 3.7 "What recommendation was previously rejected?"
    if any(w in q_lower for w in ["previously rejected", "was rejected", "rejected recommendation", "prior rejection", "rejected decision", "past rejection"]):
        return [{"type": "rejected_recommendations"}]

    # 3.8 "Compare the most profitable and least profitable departments"
    if any(w in q_lower for w in ["compare the most profitable and least profitable", "compare most and least profitable", "compare highest and lowest profit", "compare best and worst"]):
        return [{"type": "compare_extremes", "metric": "profit"}]

    # 3.9 "Compare Sales and Marketing and tell me why their margins differ"
    dept_comp_match = re.search(r"compare\s+([a-zA-Z\s&]+?)\s+(?:and|vs|versus)\s+([a-zA-Z\s&]+?)(?:\s+and\s+tell\s+me\s+why\s+their\s+margins?\s+differ|\s+and\s+why|\s+and\s+which\s+has\s+better\s+margin|\.|$)", q_lower)
    if dept_comp_match:
        d1 = dept_comp_match.group(1).strip()
        d2 = dept_comp_match.group(2).strip()
        focus = "margin_diff" if "margin" in q_lower else "general"
        return [{"type": "comparison", "entities": [d1, d2], "focus": focus}]

    # 3.10 "Why did profit change and which department contributed most?"
    if any(w in q_lower for w in ["why did profit change", "why did profitability change", "what caused profit to change", "why has profit changed"]) and any(w in q_lower for w in ["which department contributed most", "which department drove", "top contributor", "main contributor"]):
        return [{"type": "period_variance_causal_with_top_dept"}]

    # 3.11 Causal Variance: "Why did profit change?" / "Why has profit decreased?" / "What caused the profit decline?"
    if (any(w in q_lower for w in ["why did profit change", "why did profitability change", "why did profit drop", "why did profit decrease", "why did profit fall", "why has profit decreased", "what caused the profit decline", "what caused profit decline", "why did profit fall", "what changed between"]) or 
        (any(w in q_lower for w in ["why did", "why has", "what caused"]) and any(w in q_lower for w in ["profit", "profitability", "margin"]) and any(w in q_lower for w in ["change", "fall", "drop", "decrease", "decline"]))):
        return [{"type": "period_variance_causal"}]

    # 3.12 "Where are we overspending?" / "Which department spends the most?"
    if any(w in q_lower for w in ["where are we overspending", "are we overspending", "overspending areas", "overspend", "spends the most", "spend the most", "largest spending", "highest spending department"]):
        return [{"type": "overspending_investigation"}]

    # 3.13 "Show departments with declining margins"
    if any(w in q_lower for w in ["declining margins", "declining margin", "falling margins", "dropping margins", "margins declining", "margins falling"]):
        return [{"type": "ranking_list", "metric": "margin", "direction": "min", "limit": 999}]

    # 3.14 Evidence / Context: "Show me the evidence" / "Why are you saying this?"
    if any(w in q_lower for w in ["show me the evidence", "show evidence", "what is the evidence", "why are you saying this", "why do you say this", "where does this come from"]):
        return [{"type": "follow_up_why"}]

    # 3.15 "Are there anomalies affecting profit?"
    if any(w in q_lower for w in ["anomalies affecting profit", "anomaly affecting profit", "anomalies impacting profit", "are there anomalies", "is there any anomaly", "any anomalies"]):
        return [{"type": "anomalies_affecting_profit"}]

    # 3.16 Multi-Intent: "Top 3 by profit and bottom 3 by profit"
    top_bot_match = re.search(r"(?:top|best|highest)\s+(\d+)\s+.*?\s+and\s+(?:bottom|worst|lowest|least)\s+(\d+)", q_lower)
    if top_bot_match:
        lim1 = int(top_bot_match.group(1))
        lim2 = int(top_bot_match.group(2))
        met = detect_primary_metric(q_lower)
        return [
            {"type": "ranking_list", "metric": met, "direction": "max", "limit": lim1},
            {"type": "ranking_list", "metric": met, "direction": "min", "limit": lim2},
        ]

    # 3.15 Multi-Intent: "Which department is most profitable and which is 2nd least profitable?"
    # or "Which department is most profitable, which is least profitable, and what happens if expenses fall 5%?"
    sub_clauses = [s.strip() for s in re.split(r",|\band\b|\bas well as\b|\bwhile\b", q_lower) if s.strip()]
    decomposed: List[Dict[str, Any]] = []

    for clause in sub_clauses:
        # Check if clause is a What-If scenario
        if any(w in clause for w in ["what if", "what happens if", "expenses fall", "expenses decrease", "expenses drop", "expenses increase", "revenue increases", "revenue grows"]):
            pct_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", clause)
            is_exp = any(w in clause for w in ["expense", "expenses", "cost", "spending"])
            is_rev = any(w in clause for w in ["revenue", "sales", "topline"])
            is_fall = any(w in clause for w in ["fall", "decrease", "drop", "reduce", "cut"])
            
            exp_pct = 0.0
            rev_pct = 0.0
            
            if is_rev and is_exp and len(pct_matches) >= 2:
                # Compound what-if: revenue increases 10% while expenses increase 5%
                rev_pct = float(pct_matches[0])
                exp_pct = float(pct_matches[1])
            elif is_exp and pct_matches:
                p = float(pct_matches[0])
                exp_pct = -p if is_fall else p
            elif is_rev and pct_matches:
                p = float(pct_matches[0])
                rev_pct = -p if is_fall else p
            elif pct_matches:
                p = float(pct_matches[0])
                exp_pct = -p if is_fall else p

            decomposed.append({"type": "what_if", "rev_growth_pct": rev_pct, "exp_growth_pct": exp_pct})
            continue

        # Check if clause is a Ranking query
        if any(w in clause for w in ["profitable", "profit", "revenue", "expense", "margin", "cost", "least", "lowest", "highest", "most", "2nd", "second", "3rd", "third", "rank"]):
            r_num, r_lim = detect_rank_and_limit(clause)
            direction = detect_direction(clause)
            met = detect_primary_metric(clause)

            if "margin" in clause and r_num > 0 and not any(w in clause for w in ["lowest margin", "highest margin", "least margin", "most margin"]):
                # e.g. "what is the second most profitable department and what is its margin?"
                decomposed.append({
                    "type": "ranking_with_metric",
                    "metric": met,
                    "direction": direction,
                    "rank": r_num,
                    "secondary_metric": "margin"
                })
            elif r_lim is not None:
                decomposed.append({
                    "type": "ranking_list",
                    "metric": met,
                    "direction": direction,
                    "limit": r_lim
                })
            else:
                decomposed.append({
                    "type": "ranking",
                    "metric": met,
                    "direction": direction,
                    "rank": r_num
                })
            continue

    if len(decomposed) >= 2:
        return decomposed

    # 4. Single-Intent Classifications
    # 4.1 Compound What-If: "What happens if revenue increases 10% while expenses increase 5%?"
    if any(w in q_lower for w in ["what if", "simulate", "what happens if", "what would happen if"]):
        pcts = re.findall(r"(\d+(?:\.\d+)?)\s*%", q_lower)
        rev_pct = 0.0
        exp_pct = 0.0
        if "revenue" in q_lower and "expense" in q_lower and len(pcts) >= 2:
            rev_pct = float(pcts[0]) if "decrease" not in q_lower[:q_lower.find("while")] else -float(pcts[0])
            exp_pct = float(pcts[1]) if "decrease" not in q_lower[q_lower.find("while"):] else -float(pcts[1])
        elif any(w in q_lower for w in ["expense", "cost", "spending"]):
            p = float(pcts[0]) if pcts else 5.0
            exp_pct = -p if any(w in q_lower for w in ["fall", "decrease", "drop", "reduce", "cut"]) else p
        elif any(w in q_lower for w in ["revenue", "sales"]):
            p = float(pcts[0]) if pcts else 10.0
            rev_pct = -p if any(w in q_lower for w in ["fall", "decrease", "drop", "reduce"]) else p
        else:
            p = float(pcts[0]) if pcts else 5.0
            exp_pct = -p

        return [{"type": "what_if", "rev_growth_pct": rev_pct, "exp_growth_pct": exp_pct}]

    # 4.2 Single Ranking with Secondary Metric (e.g., "What is the second most profitable department and what is its margin?")
    if any(w in q_lower for w in ["second most profitable department and what is its margin", "2nd most profitable department and what is its margin", "most profitable department and what is its margin"]):
        r_num, _ = detect_rank_and_limit(q_lower)
        return [{"type": "ranking_with_metric", "metric": "profit", "direction": "max", "rank": r_num, "secondary_metric": "margin"}]

    # 4.3 Ranking (Ordinal or Superlative)
    r_num, r_lim = detect_rank_and_limit(q_lower)
    dir_val = detect_direction(q_lower)
    met_val = detect_primary_metric(q_lower)

    if (r_num > 1 or r_lim is not None or any(w in q_lower for w in [
        "least profitable", "lowest profit", "most profitable", "highest profit", "lowest revenue", "highest revenue",
        "lowest expense", "highest expense", "best margin", "worst margin", "lowest margin", "highest margin",
        "rank departments", "ranking of departments", "top departments", "bottom departments", "department ranking", "ranked by",
        "second least", "second lowest", "second highest", "third lowest", "third highest", "2nd least", "2nd lowest", "2nd highest",
        "from the bottom", "from bottom", "from the top", "from top", "who is the most profitable"
    ])):
        if r_lim is not None:
            return [{"type": "ranking_list", "metric": met_val, "direction": dir_val, "limit": r_lim}]
        return [{"type": "ranking", "metric": met_val, "direction": dir_val, "rank": r_num}]

    # 4.4 Period Variance & All Metrics Comparison
    if any(w in q_lower for w in ["what changed between the latest two periods", "what changed in revenue, expenses, profit and margin", "what changed between periods", "what changed compared"]):
        return [{"type": "period_variance_all_metrics"}]

    # 4.5 Schema & Quality Inspection
    if any(w in q_lower for w in ["what is missing", "what's missing", "missing from my dataset", "missing data", "missing fields", "available columns", "what columns"]):
        return [{"type": "schema_inspection"}]

    # 4.6 Recommendations
    if any(w in q_lower for w in ["what recommendations should management consider", "recommend", "action plan", "suggest", "what should we do", "what should management do"]):
        return [{"type": "recommendations"}]

    # 4.7 Cash Flow
    if any(w in q_lower for w in ["cash flow", "cashflow", "inflow", "outflow", "liquidity"]):
        return [{"type": "cash_flow"}]

    # 4.8 Forecast
    if detect_time_context(q_lower) == "future":
        horizon = detect_forecast_horizon(q_lower)
        return [{"type": "forecast", "metric": met_val, "horizon": horizon}]

    # 4.9 Generic Financial Totals / Department Lookup
    return [{"type": "general_financial", "metric": met_val, "raw": q}]


def classify_copilot_intent(question: str) -> str:
    """Legacy mapper returning top-level intent string for backwards compatibility."""
    decomposed = decompose_intents(question)
    if not decomposed:
        return "GENERAL_FINANCIAL"
    first = decomposed[0]
    t = first.get("type", "general_financial")
    type_map = {
        "out_of_scope": "OUT_OF_SCOPE",
        "follow_up_why": "FOLLOW_UP_WHY",
        "follow_up_numbers": "FOLLOW_UP_NUMBERS",
        "follow_up_entity": "FOLLOW_UP_ENTITY",
        "what_if": "WHAT_IF",
        "what_if_top_cost_center": "WHAT_IF",
        "ranking": "DEPARTMENT_RANKING",
        "ranking_list": "DEPARTMENT_RANKING",
        "ranking_with_metric": "DEPARTMENT_RANKING",
        "highest_rev_not_highest_profit": "DEPARTMENT_RANKING",
        "lowest_margin_not_lowest_profit": "DEPARTMENT_RANKING",
        "highest_expense_still_profitable": "DEPARTMENT_RANKING",
        "compare_extremes": "DEPARTMENT_COMPARISON",
        "comparison": "DEPARTMENT_COMPARISON",
        "comparison_with_margin_analysis": "DEPARTMENT_COMPARISON",
        "period_variance_causal": "VARIANCE_DRIVERS",
        "period_variance_causal_with_top_dept": "VARIANCE_DRIVERS",
        "period_variance_all_metrics": "PERIOD_ANALYSIS",
        "overspending_investigation": "BUDGET",
        "anomalies_affecting_profit": "ANOMALY",
        "profitable_despite_high_expenses": "VARIANCE_DRIVERS",
        "largest_expense_increase_dept": "VARIANCE_DRIVERS",
        "schema_inspection": "SCHEMA_INSPECTION",
        "recommendations": "RECOMMENDATION",
        "rejected_recommendations": "RECOMMENDATION",
        "cash_flow": "CASH_FLOW",
        "forecast": "FORECAST",
    }
    if len(decomposed) > 1:
        return "MULTI_OBJECTIVE"
    return type_map.get(t, "GENERAL_FINANCIAL")


def parse_question(question: str) -> Dict[str, Any]:
    """Parse a user question into structured analytical components."""
    lower = question.lower()
    rank_num, limit_num = detect_rank_and_limit(lower)
    intents = decompose_intents(question)
    return {
        "intent": classify_copilot_intent(question),
        "intents": intents,
        "primary_metric": detect_primary_metric(lower),
        "direction": detect_direction(lower),
        "rank": rank_num,
        "limit": limit_num,
        "time_context": detect_time_context(lower),
        "forecast_horizon": detect_forecast_horizon(lower),
    }
