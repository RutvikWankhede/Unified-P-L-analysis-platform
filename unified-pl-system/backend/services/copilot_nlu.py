"""
copilot_nlu.py - Natural Language Understanding for Financial Copilot
=====================================================================
Accurate intent classification, metric detection, ordinal rank extraction,
direction detection, multi-item limits, entity extraction, and time context.
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

    # 3. Explicit ordinals: "2nd least", "second lowest", "3rd highest", "second best", "2nd worst"
    for ord_word, rank_num in ORDINAL_MAP.items():
        # Match ordinal followed by superlatives or nouns
        pat = r"\b" + re.escape(ord_word) + r"\s+(?:most|least|highest|lowest|best|worst|top|bottom|profitable|revenue|expense|margin|cost|spending|anomal|department|division)\b"
        if re.search(pat, q_lower):
            return (rank_num, None)
        # Match "2nd from the bottom", "second from bottom", "2nd from top"
        from_pat = r"\b" + re.escape(ord_word) + r"\s+(?:from\s+(?:the\s+)?)?(?:bottom|top)\b"
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
    """
    Detect whether the user's question pertains to FUTURE/FORECAST or CURRENT/HISTORICAL data.
    """
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
    """
    Detect the primary financial metric the user is asking about.
    Returns one of: 'profit', 'revenue', 'expense', 'margin', 'growth', 'budget', 'variance', 'anomalies', 'cash_flow', 'health', 'schema_info'
    """
    # Financial Health
    if any(w in q_lower for w in ["financial health", "health score", "score"]):
        return "health"

    # Growth & Trajectory
    if any(w in q_lower for w in ["grow the most", "highest growth", "fastest growing", "maximum growth",
                                  "grow most", "growth rate", "will grow", "growth", "decline most",
                                  "slowest growing", "expected to decline", "largest decrease", "fall most", "drop most"]):
        return "growth"
        
    # Margin
    if any(w in q_lower for w in ["margin", "operating margin", "profit margin", "percentage margin"]):
        return "margin"
        
    # Budget & Variance
    if any(w in q_lower for w in ["over budget", "under budget", "budget variance", "largest budget variance", "budget", "allocated target", "overspending"]):
        return "budget"
        
    # Anomalies & Risk
    if any(w in q_lower for w in ["anomal", "outlier", "risk", "fraud", "irregular"]):
        return "anomalies"
        
    # Cash Flow
    if any(w in q_lower for w in ["cash flow", "cashflow", "inflow", "outflow", "liquidity", "working capital"]):
        return "cash_flow"
        
    # Schema / Metadata
    if any(w in q_lower for w in ["columns", "fields", "schema", "contain", "available columns", "what columns", "available in the dataset"]):
        return "schema_info"
        
    # Revenue
    if any(w in q_lower for w in ["revenue", "sales", "income", "topline", "top line", "turnover"]):
        return "revenue"
        
    # Expense
    if any(w in q_lower for w in ["expense", "expenses", "cost", "costs", "spending", "spend", "opex", "expenditure"]):
        return "expense"
        
    # Default to Profit
    return "profit"


def detect_forecast_horizon(q_lower: str) -> int:
    """
    Detect the forecast horizon in months from the user's question.
    Returns integer number of months (e.g., 1, 2, 3, 6, 12). Default is 12.
    """
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


def classify_copilot_intent(question: str) -> str:
    """
    Classify incoming user query into an actionable enterprise intent category.
    """
    q = question.strip().lower()

    # 1. Non-Financial Out of Scope
    unsupported = [
        "customer satisfaction", "csat", "nps", "headcount", "turnover rate", "employee attrition",
        "stock price", "share price", "crypto", "bitcoin", "weather", "temperature",
        "server uptime", "latencies", "bugs", "github commit", "who is the president", "who is the ceo", "who is ceo",
        "apple stock", "tesla stock", "google stock", "who won"
    ]
    if any(t in q for t in unsupported):
        return "OUT_OF_SCOPE"

    # 2. Conversational Follow-Ups & Expansion
    if q in ["why?", "why", "why is that?", "explain why", "why so?", "how come?"]:
        return "FOLLOW_UP_WHY"
    if q in ["show me the numbers", "show numbers", "show table", "show details", "numbers please", "give me the data", "breakdown"]:
        return "FOLLOW_UP_NUMBERS"
    if q.startswith("what about ") or q.startswith("how about ") or q.startswith("and "):
        return "FOLLOW_UP_ENTITY"

    # 3. Schema & Data Quality Queries
    if any(w in q for w in ["what is missing", "what's missing", "missing from my dataset", "missing data",
                            "missing fields", "data quality", "dataset quality", "does the dataset contain",
                            "do we have", "is there budget", "is there cash flow", "which columns are available",
                            "what columns", "list columns", "available fields", "what data is available",
                            "dataset columns", "available in the dataset", "fields in dataset"]):
        return "SCHEMA_INSPECTION"

    # 4. Cash Flow Queries
    if any(w in q for w in ["cash flow", "cashflow", "cash inflow", "cash outflow", "inflow in", "outflow in", "liquidity", "working capital"]):
        return "CASH_FLOW"

    # 5. What-If Scenario Simulations
    if any(w in q for w in ["what if", "simulate", "increases by", "decreases by", "increase by", "decrease by",
                            "grows by", "falls by", "drops by", "scenario", "what happens if", "what would happen if"]):
        return "WHAT_IF"

    # 6. Multi-Objective Queries
    if ("," in q or " and " in q) and sum([
        1 if any(w in q for w in ["profit", "profitable"]) else 0,
        1 if any(w in q for w in ["margin", "operating margin"]) else 0,
        1 if any(w in q for w in ["anomal", "risk", "outlier"]) else 0,
        1 if any(w in q for w in ["revenue", "sales"]) else 0,
        1 if any(w in q for w in ["expense", "cost"]) else 0,
    ]) >= 2 and not any(w in q for w in ["compare", " vs ", " versus "]):
        return "MULTI_OBJECTIVE"

    # 7. Comparison Queries
    if any(w in q for w in ["compare", " vs ", " versus ", "difference between", "performing compared with",
                            "which is better", "which has higher", "which has lower", "which has more", "how much more",
                            "best and worst", "worst and best", "highest and lowest",
                            "lowest and highest", "most and least", "least and most", "top and bottom",
                            "which is best and which is worst"]):
        return "DEPARTMENT_COMPARISON"

    # 8. Strategic Recommendations & Management Actions
    if any(w in q for w in ["recommend", "action plan", "suggest", "advis", "how to improve", "best action",
                            "what should management focus on", "management focus", "what should we do", "what should management do",
                            "areas for improvement", "action item", "strategic action", "which department needs attention"]):
        return "RECOMMENDATION"

    # 9. Why / Root-Cause Diagnostics
    if any(w in q for w in ["why did profit", "why is profit", "profit fell", "profit drop", "profit decrease",
                            "profit down", "why are margins low", "why is margin low", "why loss", "driving expense",
                            "cost driver", "revenue driver", "what caused", "improved the most", "deteriorated the most",
                            "why are we losing", "root cause", "main driver", "what is driving revenue", "what is driving expense",
                            "why is profit declining"]):
        return "VARIANCE_DRIVERS"

    # 10. Budget & Variance Analysis
    if any(w in q for w in ["budget", "over budget", "under budget", "variance", "budget variance",
                            "allocated target", "overspending", "where are we overspending", "budget overrun"]):
        return "BUDGET"

    # 11. Anomaly & Risk Analysis
    if any(w in q for w in ["anomal", "outlier", "risk", "fraud", "irregular", "biggest anomaly",
                            "how many anomalies", "most anomalies", "severity", "audit risk", "biggest financial risk"]):
        return "ANOMALY"

    # 12. Future / Forecast Intents
    time_ctx = detect_time_context(q)
    metric = detect_primary_metric(q)
    if time_ctx == "future":
        if metric == "profit" and any(w in q for w in ["least profitable", "lowest profit", "most profitable", "highest profit", "profit in future", "profitable in future", "will be least profitable", "will be most profitable"]):
            return "FUTURE_PROFITABILITY"
        return "FORECAST"

    # 13. Top-N Ranking / Ordinal Ranking / Superlatives (MUST come before generic metric lookup)
    rank_num, lim = detect_rank_and_limit(q)
    is_ranking_query = (
        rank_num > 1 or lim is not None or any(w in q for w in [
            "least profitable", "lowest profit", "most profitable", "highest profit", "lowest revenue", "highest revenue",
            "lowest expense", "highest expense", "best margin", "worst margin", "lowest margin", "highest margin",
            "rank departments", "ranking of departments", "top departments", "bottom departments", "department ranking", "ranked by",
            "second least", "second lowest", "second highest", "third lowest", "third highest", "2nd least", "2nd lowest", "2nd highest", "3rd least", "3rd lowest", "3rd highest",
            "from the bottom", "from bottom", "from the top", "from top", "ranks #", "rank #"
        ]) or (
            any(w in q for w in ["which department", "what department", "who is the", "give me the department", "which division", "what division"]) and
            any(w in q for w in ["profit", "profitable", "revenue", "expense", "margin", "cost", "spending", "least", "lowest", "highest", "most", "best", "worst"])
        )
    )
    if is_ranking_query:
        return "DEPARTMENT_RANKING"

    # 14. Period / Date specific queries (e.g., "What happened in 2025-08?")
    if re.search(r"\b(20\d{2}[-/]\d{1,2}|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?\s+20\d{2})\b", q):
        return "PERIOD_ANALYSIS"

    # 15. Current Financial Totals & Department Lookup
    if any(w in q for w in ["total revenue", "total expense", "total expenses", "total profit", "net profit",
                            "operating margin", "what is revenue", "what is expense", "what is profit", "what is margin",
                            "how is sales", "how is operations", "how is marketing", "how is it", "how is finance",
                            "what is total revenue", "what is total expense", "what is total profit", "what is net profit"]):
        return "CURRENT_FINANCIAL"

    return "GENERAL_FINANCIAL"


def parse_question(question: str) -> Dict[str, Any]:
    """Parse a user question into structured analytical components."""
    lower = question.lower()
    rank_num, limit_num = detect_rank_and_limit(lower)
    return {
        "intent": classify_copilot_intent(question),
        "primary_metric": detect_primary_metric(lower),
        "direction": detect_direction(lower),
        "rank": rank_num,
        "limit": limit_num,
        "time_context": detect_time_context(lower),
        "forecast_horizon": detect_forecast_horizon(lower),
    }
