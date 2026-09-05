import re
import json
import logging
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from models.schema_mapping import SchemaMappingHistory
from config import settings

logger = logging.getLogger(__name__)

# Define core target schema columns with synonyms
TARGET_SCHEMAS = {
    "date": [
        "date",
        "posting date",
        "invoice date",
        "created date",
        "transaction date",
        "transaction_date",
        "entry date",
        "period",
        "day",
        "month",
        "year",
        "time",
        "timestamp",
        "txn date",
        "val date",
    ],
    "department": [
        "department",
        "dept",
        "business unit",
        "division",
        "team",
        "function",
        "cost center",
        "segment",
        "bu",
        "cost_center",
        "domain",
    ],
    "line_item": [
        "line item",
        "line_item",
        "lineitem",
        "description",
        "details",
        "particulars",
        "category",
        "account",
        "account name",
        "account_name",
        "gl account",
        "ledger account",
        "account head",
        "transaction",
    ],
    "amount": [
        "amount",
        "value",
        "total",
        "net amount",
        "net_amount",
        "debit",
        "credit",
        "balance",
        "financial value",
        "price",
        "sum",
        "total amount",
        "charge",
    ],
    "Revenue": [
        "revenue",
        "sales",
        "sales amount",
        "sales revenue",
        "gross revenue",
        "revenue amount",
        "income",
        "total income",
        "total revenue",
        "net sales",
        "turnover",
        "operating revenue",
    ],
    "Expense": [
        "expense",
        "expenses",
        "cost",
        "costs",
        "total expense",
        "total expenses",
        "expenditure",
        "spending",
        "operating cost",
        "operating expenses",
        "cogs",
        "opex",
    ],
    "Profit": [
        "profit",
        "net profit",
        "net income",
        "earnings",
        "gain",
        "net gain",
        "operating profit",
        "ebit",
        "p&l",
        "pnl",
    ],
    "Cash_Inflow": [
        "cash inflow",
        "inflow",
        "cash received",
        "receipts",
        "collections",
        "cash_inflow",
        "operating cash inflow"
    ],
    "Cash_Outflow": [
        "cash outflow",
        "outflow",
        "cash paid",
        "payments",
        "cash_outflow",
        "operating cash outflow"
    ],
    "Budget": [
        "budget",
        "budget amount",
        "approved budget",
        "planned",
        "planned budget",
        "planned amount",
        "planned expense",
        "target",
        "budgeted amount",
    ],
    "Actual": [
        "actual",
        "actual amount",
        "realized",
        "actual revenue",
        "actual expense",
    ],
    "currency": ["currency", "currency code", "ccy", "curr", "fx", "symbol", "coin"],
    "cost_center": ["cost center", "cost_center", "cc"],
    "transaction_id": [
        "transaction_id",
        "transaction id",
        "transactionid",
        "invoice id",
        "invoice number",
        "transaction number",
        "txn id",
        "id",
    ],
    "channel": ["channel", "sales channel", "revenue channel", "source"],
}


def clean_column_name(name: str) -> str:
    """Standardize column names to improve matching."""
    if not name:
        return ""
    name = str(name).strip().lower()
    name = re.sub(r"[\s_\-]+", " ", name)
    name = re.sub(r"[^\w\s]", "", name)
    return name.strip()


def calculate_similarity(a: str, b: str) -> float:
    """Calculate token-based and RapidFuzz similarity score between 0 and 100."""
    a_clean = clean_column_name(a)
    b_clean = clean_column_name(b)
    if not a_clean or not b_clean:
        return 0.0

    if a_clean == b_clean:
        return 100.0

    # RapidFuzz similarity - prioritize full token matches over partial substrings
    ratio = fuzz.ratio(a_clean, b_clean)
    token_sort_ratio = fuzz.token_sort_ratio(a_clean, b_clean)
    token_set_ratio = fuzz.token_set_ratio(a_clean, b_clean)

    return float(max(ratio, token_sort_ratio, token_set_ratio * 0.9))


def get_mapping_confidence(
    original_name: str, target: str, db: Session, user_id: int
) -> float:
    """Assess mapping confidence using rules, history, and token similarity."""
    cleaned = clean_column_name(original_name)
    if not cleaned:
        return 0.0

    # 1. Check exact matches in aliases (Highest Priority)
    aliases = TARGET_SCHEMAS.get(target, [])
    if cleaned in aliases:
        return 100.0

    # 2. Check history database (Learning Schema)
    try:
        history = (
            db.query(SchemaMappingHistory)
            .filter(
                SchemaMappingHistory.original_column == cleaned,
                SchemaMappingHistory.mapped_column == target,
            )
            .first()
        )
        if history:
            return float(history.confidence)
    except Exception as e:
        logger.warning(f"Error reading schema mapping history: {e}")

    # 3. Exact word boundary regex matches
    if target == "date":
        if re.search(r"\b(date|time|timestamp|period|posting|created)\b", cleaned):
            return 90.0
    elif target == "department":
        if re.search(r"\b(dept|department|bu|division|team|segment|unit)\b", cleaned):
            return 90.0
    elif target == "Revenue":
        if re.search(r"\b(revenue|sales|income|turnover)\b", cleaned):
            return 90.0
    elif target == "Expense":
        if re.search(r"\b(expense|expenses|cost|costs|opex|spend|spending|expenditure|cogs)\b", cleaned):
            return 90.0
    elif target == "Profit":
        if re.search(r"\b(profit|gain|earnings|ebit|margin)\b", cleaned):
            return 90.0
    elif target == "amount":
        if re.search(r"\b(amount|value|total|debit|credit|balance|sum)\b", cleaned):
            return 80.0

    # 4. Fuzzy string matching against aliases
    best_score = 0.0
    for alias in aliases:
        score = calculate_similarity(cleaned, alias)
        if score > best_score:
            best_score = score

    return round(best_score, 1)


def llm_infer_schema(columns: list) -> dict:
    """Call Gemini to run embedding / semantic schema mapping suggestion."""
    if not settings.GEMINI_API_KEY:
        return {}

    from google import genai

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = f"""
        You are an expert financial schema mapping tool.
        Map the list of incoming spreadsheet column headers to standard target categories:
        Target schema: {list(TARGET_SCHEMAS.keys())}
        
        Incoming headers: {columns}
        
        Return a valid JSON object where keys are the incoming headers exactly, and values are objects containing:
        - "mapped_to": (one of the Target schema keys, or null if it doesn't match any target)
        - "confidence": (a number between 0 and 100 representing your mapping confidence)
        
        Example JSON output:
        {{
           "TXN DATE": {{ "mapped_to": "date", "confidence": 95 }},
           "Cost Center": {{ "mapped_to": "cost_center", "confidence": 100 }}
        }}
        
        Return ONLY valid JSON.
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        # Parse output JSON
        text = response.text.strip()
        # Find JSON boundaries
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx : end_idx + 1]
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Gemini schema inference failed: {e}")
        return {}


def infer_schema(columns: list, db: Session, user_id: int) -> dict:
    """
    Infer target mapping for a list of input columns.
    Returns a dictionary mapping: original_column -> { column_name, confidence }
    """
    mappings = {}

    # First attempt LLM if configured
    llm_mappings = {}
    if settings.GEMINI_API_KEY:
        llm_mappings = llm_infer_schema(columns)

    for col in columns:
        col_clean = str(col).strip()

        # If LLM returned a highly confident result, let's respect it
        if (
            col_clean in llm_mappings
            and llm_mappings[col_clean].get("confidence", 0) >= 80
        ):
            mappings[col_clean] = {
                "mapped_to": llm_mappings[col_clean].get("mapped_to", llm_mappings[col_clean].get("column_name")),
                "confidence": llm_mappings[col_clean]["confidence"],
            }
            continue

        best_target = None
        best_confidence = 0.0

        for target in TARGET_SCHEMAS.keys():
            conf = get_mapping_confidence(col_clean, target, db, user_id)
            if conf >= 100.0:
                best_confidence = 100.0
                best_target = target
                break
            if conf > best_confidence:
                best_confidence = conf
                best_target = target

        if best_confidence < 40.0:
            mappings[col_clean] = {"mapped_to": None, "confidence": 0.0}
        else:
            mappings[col_clean] = {
                "mapped_to": best_target,
                "confidence": best_confidence,
            }

    overall_confidence = 0
    mapped_confidences = [info["confidence"] for info in mappings.values() if info.get("mapped_to") is not None]
    if mapped_confidences:
        overall_confidence = sum(mapped_confidences) / len(mapped_confidences)

    return mappings


def save_mapping_feedback(
    db: Session,
    user_id: int,
    original: str,
    mapped: str,
    sample_values: str = None,
    currency_context: str = None,
):
    """Save manual corrections to history so the engine learns over time."""
    orig_clean = clean_column_name(original)
    if not orig_clean or not mapped:
        return

    # Check if there's already a mapping
    existing = (
        db.query(SchemaMappingHistory)
        .filter(
            SchemaMappingHistory.original_column == orig_clean,
            SchemaMappingHistory.mapped_column == mapped,
        )
        .first()
    )

    if existing:
        existing.confidence = 99
        if sample_values:
            existing.sample_values = sample_values
        if currency_context:
            existing.currency_context = currency_context
    else:
        db.add(
            SchemaMappingHistory(
                user_id=user_id,
                original_column=orig_clean,
                mapped_column=mapped,
                confidence=99,
                sample_values=sample_values,
                currency_context=currency_context,
            )
        )
    db.commit()
