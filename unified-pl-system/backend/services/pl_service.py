import uuid
import re
import logging
from io import StringIO, BytesIO
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from repositories import pl_repository
from services.data_quality_agent import check_data_quality
from services.schema_mapping_agent import infer_schema, save_mapping_feedback
from models.pl_record import PLRecord
from models.uploaded_file import UploadedFile
from models.recommendation import Setting

MONTH_TRANSLATION = {
    "jan": 1,
    "januar": 1,
    "janvier": 1,
    "enero": 1,
    "feb": 2,
    "februar": 2,
    "février": 2,
    "febrero": 2,
    "mar": 3,
    "märz": 3,
    "mars": 3,
    "marzo": 3,
    "apr": 4,
    "april": 4,
    "avril": 4,
    "abril": 4,
    "may": 5,
    "mai": 5,
    "mayo": 5,
    "jun": 6,
    "juni": 6,
    "juin": 6,
    "junio": 6,
    "jul": 7,
    "juli": 7,
    "juillet": 7,
    "julio": 7,
    "aug": 8,
    "august": 8,
    "août": 8,
    "agosto": 8,
    "sep": 9,
    "september": 9,
    "septembre": 9,
    "septiembre": 9,
    "oct": 10,
    "oktober": 10,
    "octobre": 10,
    "octubre": 10,
    "nov": 11,
    "november": 11,
    "novembre": 11,
    "noviembre": 11,
    "dec": 12,
    "dezember": 12,
    "décembre": 12,
    "diciembre": 12,
}


def parse_amount(val) -> float:
    """Smart parser for financial amounts, supporting currency symbols, commas, dots, spaces, parenthesized negatives, and mixed formats."""
    if pd.isnull(val):
        return 0.0
    s = str(val).strip()
    if not s:
        return 0.0

    # Handle parenthesized negatives: (1,234.56) -> -1,234.56
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()

    # Strip standard currency symbols and spaces
    s = re.sub(r"[^\d,\.\-\+]", "", s)
    if not s:
        return 0.0

    # Auto-detect thousands/decimal separator system
    if "," in s and "." in s:
        comma_idx = s.rfind(",")
        dot_idx = s.rfind(".")
        if comma_idx > dot_idx:
            # European style -> remove dots, treat comma as dot
            s = s.replace(".", "").replace(",", ".")
        else:
            # US style -> remove commas
            s = s.replace(",", "")
    elif "," in s:
        # Check if single comma is a decimal separator or thousands separator
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) != 3:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        val = float(s)
        return -val if is_negative else val
    except ValueError:
        return 0.0


def parse_date(val) -> str:
    """Smart date normalizer, supporting Quarters, foreign month names, and standard date formats."""
    if pd.isnull(val):
        return "1970-01-01"
    s = str(val).strip()
    if not s:
        return "1970-01-01"

    # Quarter pattern: e.g. 2026-Q1, 2026 Q2
    q_match = re.search(r"(\d{4})[\s\-]*[qQ](\d)", s)
    if q_match:
        year = q_match.group(1)
        qtr = int(q_match.group(2))
        month = (qtr - 1) * 3 + 1
        return f"{year}-{month:02d}-01"

    # Word character search for multilingual month names
    words = re.findall(r"[a-zA-Záéíóúüäöß]+", s)
    if words:
        for w in words:
            wl = w.lower()
            if wl in MONTH_TRANSLATION:
                month_num = MONTH_TRANSLATION[wl]
                nums = re.findall(r"\d+", s)
                if len(nums) >= 2:
                    year = [n for n in nums if len(n) == 4]
                    day = [n for n in nums if len(n) < 4]
                    yr = year[0] if year else "2026"
                    dy = day[0] if day else "01"
                    return f"{yr}-{month_num:02d}-{int(dy):02d}"
                elif len(nums) == 1:
                    yr = nums[0] if len(nums[0]) == 4 else "2026"
                    return f"{yr}-{month_num:02d}-01"

    # Explicit format checks to avoid ambiguity
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return pd.to_datetime(s, format=fmt).strftime("%Y-%m-%d")
        except:
            continue

    # Standard pandas parsing fallback
    try:
        dt = pd.to_datetime(s, errors="raise")
        return dt.strftime("%Y-%m-%d")
    except:
        return s


def detect_currency_from_string(s: str) -> str:
    s = str(s).strip()
    if "€" in s or "EUR" in s.upper():
        return "EUR"
    if "£" in s or "GBP" in s.upper():
        return "GBP"
    if "¥" in s or "JPY" in s.upper():
        return "JPY"
    if "C$" in s or "CAD" in s.upper():
        return "CAD"
    if "A$" in s or "AUD" in s.upper():
        return "AUD"
    if "$" in s or "USD" in s.upper():
        return "USD"
    return None


def auto_detect_currency(df: pd.DataFrame, mapping: dict) -> str:
    # Look for currency symbols in columns mapped to amount, Revenue, or Expense
    target_cols = []
    for orig, target_val in mapping.items():
        val = (
            target_val.get("mapped_to") if isinstance(target_val, dict) else target_val
        )
        if val in ["amount", "Revenue", "Expense"]:
            target_cols.append(orig)

    for col in target_cols:
        if col in df.columns:
            sample_vals = df[col].dropna().head(20).astype(str).tolist()
            for val in sample_vals:
                curr = detect_currency_from_string(val)
                if curr:
                    return curr
    return "USD"


def clean_and_deduplicate_headers(headers: list) -> list:
    clean_headers = []
    seen = {}
    last_h = "Column"

    for i, h in enumerate(headers):
        if pd.isnull(h) or str(h).strip() == "":
            h_str = f"{last_h}_unnamed_{i}"
        else:
            h_str = str(h).strip()
            last_h = h_str

        if h_str in seen:
            seen[h_str] += 1
            h_str = f"{h_str}_{seen[h_str]}"
        else:
            seen[h_str] = 0

        clean_headers.append(h_str)
    return clean_headers


def load_file_to_dataframe(file_content: bytes, filename: str) -> pd.DataFrame:
    """Load and clean messy spreadsheets, auto-detecting formats, handling blank rows, and finding headers."""
    if filename.lower().endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(BytesIO(file_content))
        sheet_name = "Financial_Data" if "Financial_Data" in xls.sheet_names else 0
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    else:
        try:
            content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = file_content.decode("latin-1")
            except UnicodeDecodeError:
                content = file_content.decode("utf-16")

        # Delimiter check (find first non-empty line)
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        first_line = lines[0] if lines else ""
        delimiters = [",", ";", "\t", "|"]
        best_delim = ","
        max_count = 0
        for d in delimiters:
            c = first_line.count(d)
            if c > max_count:
                max_count = c
                best_delim = d

        try:
            df = pd.read_csv(BytesIO(file_content), sep=best_delim, header=None, skip_blank_lines=True)
        except Exception:
            try:
                df = pd.read_csv(BytesIO(file_content), header=None, skip_blank_lines=True)
            except Exception:
                df = pd.read_csv(BytesIO(file_content), header=None, skip_blank_lines=True, on_bad_lines="skip")

    # Forward fill to resolve merged cell headers or categories in the rows
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Locate headers row (first row with multiple non-null fields)
    header_idx = 0
    for idx, row in df.iterrows():
        if row.notnull().sum() >= 2:
            header_idx = idx
            break

    headers = df.iloc[header_idx].tolist()
    clean_headers = clean_and_deduplicate_headers(headers)

    data_df = df.iloc[header_idx + 1 :].copy()
    data_df.columns = clean_headers
    
    # 1. Drop entirely empty rows and columns
    data_df.dropna(how="all", inplace=True)
    data_df.dropna(axis=1, how="all", inplace=True)
    
    # 2. Strip whitespace from all string columns
    for col in data_df.select_dtypes(include=['object']).columns:
        data_df[col] = data_df[col].apply(lambda x: str(x).strip() if pd.notnull(x) else x)
        
    # 3. Deduplicate exact duplicate rows
    data_df.drop_duplicates(inplace=True)

    # 4. Fill empty values in standard fields using forward fill (e.g. for merged department names)
    data_df.ffill(axis=0, inplace=True)
    data_df.reset_index(drop=True, inplace=True)
    return data_df


def analyze_upload(
    file_content: bytes, filename: str, db: Session, user_id: int
) -> dict:
    """Analyze and generate suggested mapping, capabilities, and quality scores for the uploaded file."""
    df = load_file_to_dataframe(file_content, filename)
    cols = df.columns.tolist()

    # AI column inference mapping
    mapping = infer_schema(cols, db, user_id)

    # Assess Data Quality
    dq = check_data_quality(df, mapping)

    def _get_target(col_info):
        return col_info.get("mapped_to") if isinstance(col_info, dict) else col_info

    def _get_conf(col_info):
        return col_info.get("confidence", 0.0) if isinstance(col_info, dict) else 80.0

    # Identify mapped targets
    detected_targets = {}
    for col, info in mapping.items():
        t = _get_target(info)
        c = _get_conf(info)
        if t:
            col_l = col.lower()
            tl = str(t).lower()
            existing = detected_targets.get(t) or detected_targets.get(tl)
            if existing:
                existing_src = existing["source"].lower()
                if existing_src == tl or (tl == "department" and existing_src in ["department", "dept"]):
                    continue
                if col_l == tl or (tl == "department" and col_l in ["department", "dept"]):
                    detected_targets[t] = {"source": col, "confidence": c}
                    detected_targets[tl] = {"source": col, "confidence": c}
                    continue
                if c > existing.get("confidence", 0):
                    detected_targets[t] = {"source": col, "confidence": c}
                    detected_targets[tl] = {"source": col, "confidence": c}
            else:
                detected_targets[t] = {"source": col, "confidence": c}
                detected_targets[tl] = {"source": col, "confidence": c}

    has_date = "date" in detected_targets
    has_dept = "department" in detected_targets or "dept" in detected_targets or "division" in detected_targets or "business_unit" in detected_targets
    has_amount = "amount" in detected_targets
    has_rev = "revenue" in detected_targets or "Revenue" in detected_targets or "sales" in detected_targets
    has_exp = "expense" in detected_targets or "Expense" in detected_targets or "cost" in detected_targets
    has_profit = "profit" in detected_targets or "Profit" in detected_targets
    has_budget = "budget" in detected_targets or "Budget" in detected_targets
    has_item = "line_item" in detected_targets

    # Check for transactional revenue/expense capability
    sample_categories = []
    if has_item:
        cat_src = detected_targets["line_item"]["source"]
        if cat_src in df.columns:
            sample_categories = [str(x).lower().strip() for x in df[cat_src].dropna().head(50).tolist()]

    rev_keywords = {"revenue", "sales", "income", "credit", "receivable", "billing", "subscription", "consulting", "services"}
    exp_keywords = {"expense", "expenses", "cost", "costs", "operating_cost", "spend", "debit", "cogs", "payable", "salary", "payroll", "rent", "marketing", "vendor", "supplies", "travel", "utilities", "maintenance", "software", "infrastructure"}
    
    can_derive_from_type = any(any(k in cat for k in rev_keywords) for cat in sample_categories) or any(any(k in cat for k in exp_keywords) for cat in sample_categories)
    revenue_expense_derivable = (has_rev and has_exp) or (has_amount and can_derive_from_type) or (has_rev or has_exp)

    confidence_ok = has_date and (has_rev or has_exp or has_amount or has_item)

    num_records = len(df)
    dept_src = detected_targets.get("department", {}).get("source")
    num_depts = df[dept_src].dropna().nunique() if (dept_src and dept_src in df.columns) else 1

    cat_src = detected_targets.get("line_item", {}).get("source")
    num_cats = df[cat_src].dropna().nunique() if (cat_src and cat_src in df.columns) else 1

    detected_currencies = auto_detect_currency(df, {k: _get_target(v) for k, v in mapping.items()})
    if not detected_currencies:
        detected_currencies = "USD"

    years_str = "2024-2026"
    date_src = detected_targets.get("date", {}).get("source")
    if date_src and date_src in df.columns:
        try:
            parsed_dates = pd.to_datetime(df[date_src].dropna(), errors="coerce")
            unique_years = sorted(parsed_dates.dt.year.dropna().unique().astype(int).tolist())
            if unique_years:
                years_str = f"{unique_years[0]}-{unique_years[-1]}" if len(unique_years) > 1 else str(unique_years[0])
        except Exception:
            years_str = "2024-2026"

    # Identify financial fields detected
    financial_fields = []
    if has_rev: financial_fields.append("Revenue")
    if has_exp: financial_fields.append("Expense")
    if has_profit: financial_fields.append("Profit")
    if has_budget: financial_fields.append("Budget")
    if has_amount: financial_fields.append("Amount")

    # Unmapped columns
    mapped_sources = {detected_targets[t]["source"] for t in detected_targets}
    unmapped_columns = [c for c in cols if c not in mapped_sources]

    # Build canonical mappings dictionary for the UI
    canonical_mappings = {}
    system_fields = ["date", "department", "amount", "Revenue", "Expense", "Profit", "Budget", "line_item", "currency", "cost_center"]
    for sf in system_fields:
        if sf in detected_targets:
            canonical_mappings[sf] = {
                "mapped_to": detected_targets[sf]["source"],
                "confidence": detected_targets[sf]["confidence"]
            }
        else:
            canonical_mappings[sf] = {
                "mapped_to": "",
                "confidence": 0.0
            }

    schema_mapping_obj = {
        "detected_columns": cols,
        "mappings": canonical_mappings,
        "suggested_mapping": mapping,
        "unmapped_columns": unmapped_columns,
        "financial_fields_detected": financial_fields,
        "capabilities": {
            "revenue_expense_derivable": revenue_expense_derivable,
            "forecast_available": has_date and num_records >= 10,
            "anomaly_detection_available": has_amount or has_rev or has_exp,
            "departments_available": has_dept,
            "budget_available": has_budget
        }
    }

    preview_rows = df.head(5).replace({np.nan: None}).to_dict(orient="records")

    return {
        "headers": cols,
        "suggested_mapping": mapping,
        "schema_mapping": schema_mapping_obj,
        "quality_report": dq.to_dict(),
        "preview_rows": preview_rows,
        "confidence_ok": confidence_ok,
        "records_count": num_records,
        "departments_count": num_depts,
        "categories_count": num_cats,
        "currencies_list": detected_currencies,
        "years_range": years_str,
        "financial_fields": financial_fields,
        "unmapped_columns": unmapped_columns,
        "revenue_expense_derivable": revenue_expense_derivable,
    }


def auto_ingest_dataset(
    db: Session,
    file_content: bytes,
    filename: str,
    user_id: int,
    upload_id: str = None,
    preset_mapping: dict = None,
    set_active: bool = True,
) -> dict:
    """Intelligently parse, schema-detect, clean, validate, derive metrics, store in DB, and optionally set as active dataset."""
    from services.cache_service import invalidate_global_cache
    from models.recommendation import Setting
    from core.dataset_context import runtime_dataset_context, CANONICAL_SEED_ID, CANONICAL_SEED_FILENAME
    from routers.datasets_router import _schema_mappings
    import os
    import math

    if not upload_id:
        upload_id = str(uuid.uuid4())

    invalidate_global_cache()

    # Save the file content in uploads folder for re-mapping
    os.makedirs("uploads", exist_ok=True)
    filepath = os.path.join("uploads", f"{upload_id}.bin")
    with open(filepath, "wb") as f:
        f.write(file_content)

    df = load_file_to_dataframe(file_content, filename)
    cols = df.columns.tolist()

    # Normalize mapping
    mapping = {}
    if preset_mapping:
        # Check if preset_mapping is {canonical: source_col} or {source_col: canonical}
        for k, v in preset_mapping.items():
            if not v:
                continue
            val_target = v.get("mapped_to") if isinstance(v, dict) else v
            if not val_target:
                continue
            if val_target in cols:
                mapping[val_target] = {"mapped_to": k, "confidence": 100.0}
            elif k in cols:
                mapping[k] = {"mapped_to": val_target, "confidence": 100.0}
        # For columns in df not explicitly mapped in preset_mapping, run inference
        inferred = infer_schema([c for c in cols if c not in mapping], db, user_id)
        for c, inf in inferred.items():
            if c not in mapping:
                mapping[c] = inf
    else:
        mapping = infer_schema(cols, db, user_id)

    dq = check_data_quality(df, mapping)

    # Save mapping feedback
    for orig, target_info in mapping.items():
        target = target_info.get("mapped_to") if isinstance(target_info, dict) else target_info
        if target:
            save_mapping_feedback(db, user_id, orig, target)

    detected_currency = auto_detect_currency(df, mapping) or "USD"

    def _get_target(col_info):
        return col_info.get("mapped_to") if isinstance(col_info, dict) else col_info

    # Date column: direct canonical match > schema mapping > aliases
    date_col = next((c for c in df.columns if c.lower() in ["date", "transaction_date", "period"]), None)
    if not date_col:
        date_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["date", "period", "transaction_date"]), None)
    if not date_col:
        date_col = next((c for c in df.columns if c.lower() in ["posting_date", "invoice_date", "financial_date", "dt"]), None)

    # Department column: direct "department"/"dept" > schema mapping > "division"/"business_unit"
    dept_col = next((c for c in df.columns if c.lower() in ["department", "dept"]), None)
    if not dept_col:
        dept_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["department", "dept"]), None)
    if not dept_col:
        dept_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["division", "business_unit", "cost_center", "domain"]), None)
    if not dept_col:
        dept_col = next((c for c in df.columns if c.lower() in ["division", "business_unit", "cost_center", "domain", "region"]), None)

    currency_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["currency", "ccy"]), None)
    cost_center_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["cost_center", "cost center"]), None)

    # Revenue column
    rev_col = next((c for c in df.columns if c.lower() in ["revenue", "sales", "total_revenue", "sales_revenue", "income", "turnover"]), None)
    if not rev_col:
        rev_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["revenue", "sales", "income", "turnover"]), None)

    # Expense column
    exp_col = next((c for c in df.columns if c.lower() in ["expense", "expenses", "cost", "costs", "total_expense", "total_cost", "operating_cost", "operating_expense", "opex"]), None)
    if not exp_col:
        exp_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["expense", "expenses", "cost", "costs", "opex", "spend"]), None)

    # Profit column
    profit_col = next((c for c in df.columns if c.lower() in ["profit", "net_profit", "earnings", "net_income"]), None)
    if not profit_col:
        profit_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["profit", "net_profit", "earnings"]), None)

    # Budget column
    budget_col = next((c for c in df.columns if c.lower() in ["budget", "budget_amount", "allocated_budget", "planned_budget", "budget_target"]), None)
    if not budget_col:
        budget_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["budget", "budget_amount", "allocated_budget", "target"]), None)

    line_item_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["line_item", "line item", "category", "account", "item"]), None)
    amount_col = next((col for col, target in mapping.items() if str(_get_target(target) or "").lower() in ["amount", "value", "net_amount"]), None)

    rev_keywords = {"revenue", "sales", "income", "credit", "receivable", "billing", "subscription", "consulting", "services"}
    exp_keywords = {"expense", "expenses", "cost", "costs", "operating_cost", "spend", "debit", "cogs", "payable", "salary", "payroll", "rent", "marketing", "vendor", "supplies", "travel", "utilities", "maintenance", "software", "infrastructure"}

    records = []
    rows_list = df.to_dict(orient="records")
    total_rev = 0.0
    total_exp = 0.0
    has_rev_records = False
    has_exp_records = False

    for row_dict in rows_list:
        date_val = parse_date(row_dict.get(date_col)) if date_col else "2026-01-01"
        dept_val = str(row_dict.get(dept_col) or "All Departments").strip() if dept_col else "All Departments"
        currency_val = str(row_dict.get(currency_col) or detected_currency or "USD").strip()[:10]
        cost_center_val = str(row_dict.get(cost_center_col) or "").strip()[:50]

        # Check wide financial columns
        rev_amt = parse_amount(row_dict.get(rev_col)) if rev_col else None
        exp_amt = parse_amount(row_dict.get(exp_col)) if exp_col else None
        profit_amt = parse_amount(row_dict.get(profit_col)) if profit_col else None
        budget_amt = parse_amount(row_dict.get(budget_col)) if budget_col else None

        # Build dynamic_data dict safely
        dynamic_data = {}
        for k, v in row_dict.items():
            if pd.isnull(v):
                dynamic_data[str(k)] = None
            elif isinstance(v, (np.integer, int)):
                dynamic_data[str(k)] = int(v)
            elif isinstance(v, (np.floating, float)):
                dynamic_data[str(k)] = round(float(v), 4) if not (math.isnan(v) or math.isinf(v)) else None
            else:
                dynamic_data[str(k)] = str(v)

        # Case 1: Wide format with Revenue and/or Expense columns
        if rev_amt is not None or exp_amt is not None:
            if rev_amt is not None and exp_amt is not None:
                profit_amt = round(rev_amt - exp_amt, 2)
            profit_margin_pct = round((profit_amt / rev_amt) * 100, 2) if (profit_amt is not None and rev_amt and rev_amt != 0) else None
            budget_var = round(exp_amt - budget_amt, 2) if (exp_amt is not None and budget_amt is not None) else None
            budget_var_pct = round((budget_var / budget_amt) * 100, 2) if (budget_var is not None and budget_amt and budget_amt != 0) else None

            if rev_amt is not None:
                dynamic_data["Revenue"] = rev_amt
                total_rev += rev_amt
                has_rev_records = True
                records.append({
                    "domain": dept_val,
                    "period": date_val,
                    "line_item": "Revenue",
                    "amount": rev_amt,
                    "currency": currency_val,
                    "cost_center": cost_center_val,
                    "dynamic_data": dynamic_data,
                })

            if exp_amt is not None:
                dynamic_data["Expense"] = exp_amt
                total_exp += exp_amt
                has_exp_records = True
                records.append({
                    "domain": dept_val,
                    "period": date_val,
                    "line_item": "Expense",
                    "amount": exp_amt,
                    "currency": currency_val,
                    "cost_center": cost_center_val,
                    "dynamic_data": dynamic_data,
                })

        # Case 2: Transaction-style data with Amount and Category/Type
        else:
            item_val = str(row_dict.get(line_item_col) or "").strip()
            raw_amt_val = parse_amount(row_dict.get(amount_col)) if amount_col else None
            amt_val = raw_amt_val if raw_amt_val is not None else 0.0

            item_lower = item_val.lower()
            is_rev = any(k in item_lower for k in rev_keywords)
            is_exp = any(k in item_lower for k in exp_keywords)

            if is_rev and not is_exp:
                total_rev += abs(amt_val)
                has_rev_records = True
                dynamic_data["Revenue"] = abs(amt_val)
                records.append({
                    "domain": dept_val,
                    "period": date_val,
                    "line_item": item_val or "Revenue",
                    "amount": abs(amt_val),
                    "currency": currency_val,
                    "cost_center": cost_center_val,
                    "dynamic_data": dynamic_data,
                })
            elif is_exp and not is_rev:
                total_exp += abs(amt_val)
                has_exp_records = True
                dynamic_data["Expense"] = abs(amt_val)
                records.append({
                    "domain": dept_val,
                    "period": date_val,
                    "line_item": item_val or "Expense",
                    "amount": abs(amt_val),
                    "currency": currency_val,
                    "cost_center": cost_center_val,
                    "dynamic_data": dynamic_data,
                })
            else:
                # General structured row: ingest as actual line item without fabricating revenue/expense
                records.append({
                    "domain": dept_val,
                    "period": date_val,
                    "line_item": item_val or "Financial Line Item",
                    "amount": amt_val,
                    "currency": currency_val,
                    "cost_center": cost_center_val,
                    "dynamic_data": dynamic_data,
                })

    db_records = pl_repository.create_pl_records(db, records, upload_id, user_id)

    # Save UploadedFile record
    is_seed_dataset = (upload_id == CANONICAL_SEED_ID)
    up_file = db.query(UploadedFile).filter(UploadedFile.upload_id == upload_id).first()
    if not up_file:
        up_file = UploadedFile(
            upload_id=upload_id,
            filename=filename,
            file_size_bytes=len(file_content),
            user_id=user_id,
            status="COMPLETED",
            is_seeded=is_seed_dataset
        )
        db.add(up_file)
    else:
        up_file.status = "COMPLETED"
        up_file.is_seeded = is_seed_dataset
    db.commit()

    # Set in-memory runtime active dataset if set_active is True
    if set_active:
        runtime_dataset_context.set_active(
            dataset_id=upload_id,
            filename=filename,
            source="upload",
            reason="USER UPLOAD"
        )

    # Trigger anomaly detection safely
    try:
        from services.anomaly_service import run_anomaly_detection
        run_anomaly_detection(db, upload_id)
    except Exception as ex:
        logger.error(f"Anomaly detection skipped or failed during auto-ingest: {ex}")

    # Format mapping for frontend
    formatted_mapping = []
    for orig, info in mapping.items():
        mapped_to = info.get("mapped_to") if isinstance(info, dict) else info
        conf = info.get("confidence", 99.0) if isinstance(info, dict) else 99.0
        formatted_mapping.append({
            "canonical_field": mapped_to or "ignore",
            "proposed_source": orig,
            "confidence": "High" if conf >= 80 else ("Medium" if conf >= 50 else "Low"),
            "required": mapped_to in ["date", "amount"],
            "description": f"Mapped column {orig}"
        })
    _schema_mappings[upload_id] = {
        "source_headers": df.columns.tolist(),
        "mapping": formatted_mapping
    }

    # Build schema summary dict
    detected_schema = {}
    for col, info in mapping.items():
        mapped_to = info.get("mapped_to") if isinstance(info, dict) else info
        if mapped_to:
            detected_schema[col] = mapped_to

    derived_metrics = {
        "revenue": round(total_rev, 2) if has_rev_records else None,
        "expense": round(total_exp, 2) if has_exp_records else None,
        "profit": round(total_rev - total_exp, 2) if (has_rev_records and has_exp_records) else None
    }

    return {
        "status": "READY",
        "dataset_id": upload_id,
        "upload_id": upload_id,
        "filename": filename,
        "records_ingested": len(db_records),
        "records_count": len(db_records),
        "row_count": len(df),
        "column_count": len(df.columns),
        "quality_score": dq.to_dict().get("overall_score", 95.0),
        "detected_schema": detected_schema,
        "derived_metrics": derived_metrics,
        "preview_rows": df.head(5).replace({np.nan: None}).to_dict(orient="records"),
        "has_departments": dept_col is not None,
    }


def finalize_ingestion(
    db: Session, file_content: bytes, filename: str, mapping: dict, user_id: int, upload_id: str
):
    """Finalize ingestion by parsing mapping and storing records in DB."""
    res = auto_ingest_dataset(db, file_content, filename, user_id, upload_id=upload_id, preset_mapping=mapping, set_active=True)
    return res["upload_id"], res["records_ingested"]


_demo_data_seeded = False

def ensure_demo_data(db: Session, force: bool = False):
    """Seed the database with the canonical demo dataset if missing, and ensure runtime active dataset is canonical seed on startup."""
    import os
    from pathlib import Path

    from core.dataset_context import runtime_dataset_context, CANONICAL_SEED_ID, CANONICAL_SEED_FILENAME
    from models.uploaded_file import UploadedFile

    canonical_upload_id = CANONICAL_SEED_ID
    canonical_filename = CANONICAL_SEED_FILENAME

    # 1. Check if canonical demo dataset records exist
    try:
        canonical_record_count = db.query(PLRecord).filter(PLRecord.upload_id == canonical_upload_id).count()
    except Exception:
        canonical_record_count = 0

    if canonical_record_count >= 1000 and not force:
        return

    if canonical_record_count < 1000:
        candidate_paths = [
            Path("demo_dataset.csv"),
            Path("unified_pnl_enterprise_demo.csv"),
            Path("data/default/unified_pnl_enterprise_demo.csv"),
            Path("../data/default/unified_pnl_enterprise_demo.csv"),
            Path("../unified_pnl_enterprise_demo.csv"),
            Path("../../data/default/unified_pnl_enterprise_demo.csv"),
            Path("../../unified_pnl_enterprise_demo.csv"),
            Path("unified-pl-system/backend/demo_dataset.csv"),
            Path("unified-pl-system/data/default/unified_pnl_enterprise_demo.csv"),
        ]
        csv_file_path = None
        for cp in candidate_paths:
            if cp.exists():
                csv_file_path = cp
                break

        if csv_file_path:
            with open(csv_file_path, "rb") as f:
                content = f.read()
            res = auto_ingest_dataset(
                db,
                content,
                csv_file_path.name,
                user_id=1,
                upload_id=canonical_upload_id,
                set_active=False
            )
            canonical_record_count = res.get('records_count', 0)
        else:
            logger.error("[DATASET] Canonical unified_pnl_enterprise_demo.csv could not be found.")

    # 2. Ensure UploadedFile record exists for canonical demo dataset
    try:
        uf = db.query(UploadedFile).filter(UploadedFile.upload_id == canonical_upload_id).first()
        if not uf:
            uf = UploadedFile(
                upload_id=canonical_upload_id,
                filename=canonical_filename,
                file_size_bytes=124362,
                user_id=1,
                status="COMPLETED",
                is_seeded=True
            )
            db.add(uf)
            db.commit()
        else:
            if not getattr(uf, "is_seeded", False):
                uf.is_seeded = True
                db.commit()
    except Exception as uf_err:
        logger.warning(f"[DATASET WARN] Error ensuring UploadedFile for demo dataset: {uf_err}")
        try:
            db.rollback()
        except Exception:
            pass

    # 3. Synchronize Runtime Active Dataset: ALWAYS canonical seed on fresh startup
    runtime_dataset_context.reset_to_seed()

    _demo_data_seeded = True
    try:
        print_dataset_startup_diagnostics(db)
    except Exception as diag_err:
        logger.warning(f"Error printing dataset startup diagnostics: {diag_err}")


def print_dataset_startup_diagnostics(db: Session):
    """Outputs structured startup block on backend startup."""
    from core.dataset_context import CANONICAL_SEED_ID, CANONICAL_SEED_FILENAME
    from routers.datasets_router import get_active_dataset

    active_ds = get_active_dataset(db)
    seed_records = db.query(PLRecord).filter(PLRecord.upload_id == CANONICAL_SEED_ID).count()

    lines = [
        "",
        "==================================================",
        "DATASET STARTUP",
        "==================================================",
        "",
        "Seed dataset:",
        f"ID: {CANONICAL_SEED_ID}",
        f"Name: {CANONICAL_SEED_FILENAME}",
        f"Record count: {seed_records}",
        "",
        "Runtime active dataset:",
        f"ID: {active_ds.get('dataset_id')}",
        f"Name: {active_ds.get('filename')}",
        f"Record count: {active_ds.get('record_count')}",
        "",
        "Startup rule:",
        "SEEDED DATASET",
        "",
        "==================================================",
        "",
    ]

    diag_text = "\n".join(lines)
    print(diag_text, flush=True)
    logger.info(diag_text)


def process_csv_upload(db: Session, file_content: bytes, user_id: int):
    """Fallback standard handler for backward compatibility in unit testing."""
    analysis = analyze_upload(file_content, "upload.csv", db, user_id)

    # Build default mapping
    mapping = {}
    for orig, val in analysis["suggested_mapping"].items():
        mapping[orig] = val["mapped_to"]

    # Fill default required column mapping if not detected
    req_cols = {
        "date": "period",
        "department": "domain",
        "line_item": "line_item",
        "amount": "amount",
    }
    for req, target in req_cols.items():
        if req not in mapping.values():
            for orig in analysis["headers"]:
                if orig not in mapping:
                    mapping[orig] = req
                    break

    upload_id, count = finalize_ingestion(
        db, file_content, "upload.csv", mapping, user_id
    )
    return upload_id, count
