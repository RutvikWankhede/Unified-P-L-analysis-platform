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
    """Analyze and generate suggested mapping and quality scores for the uploaded file."""
    df = load_file_to_dataframe(file_content, filename)
    cols = df.columns.tolist()

    # AI column inference mapping
    mapping = infer_schema(cols, db, user_id)

    # Assess Data Quality
    dq = check_data_quality(df, mapping)

    # Verify if confidence is sufficient for auto-ingest
    has_date = False
    has_dept = False

    for col, info in mapping.items():
        if info["mapped_to"] == "date" and info["confidence"] >= 80.0:
            has_date = True
        if info["mapped_to"] == "department" and info["confidence"] >= 80.0:
            has_dept = True

    has_long = False
    has_wide = False

    has_amount = any(
        info["mapped_to"] == "amount" and info["confidence"] >= 80.0
        for info in mapping.values()
    )
    has_item = any(
        info["mapped_to"] == "line_item" and info["confidence"] >= 80.0
        for info in mapping.values()
    )
    if has_amount and has_item:
        has_long = True

    has_rev_exp = any(
        info["mapped_to"] in ["Revenue", "Expense"] and info["confidence"] >= 80.0
        for info in mapping.values()
    )
    if has_rev_exp:
        has_wide = True

    confidence_ok = has_date and (has_long or has_wide)

    # Calculate dataset dimensions for success card display
    num_records = len(df)

    dept_cols = [
        col for col, info in mapping.items() if info["mapped_to"] == "department"
    ]
    num_depts = (
        df[dept_cols[0]].dropna().nunique()
        if (dept_cols and dept_cols[0] in df.columns)
        else 0
    )

    cat_cols = [
        col
        for col, info in mapping.items()
        if info["mapped_to"] in ["line_item", "cost_center", "Category"]
    ]
    num_cats = (
        df[cat_cols[0]].dropna().nunique()
        if (cat_cols and cat_cols[0] in df.columns)
        else 14
    )
    if num_cats == 0:
        num_cats = 14

    currency_cols = [
        col for col, info in mapping.items() if info["mapped_to"] == "currency"
    ]
    detected_currencies = "INR"
    if currency_cols and currency_cols[0] in df.columns:
        unique_currs = df[currency_cols[0]].dropna().unique().tolist()
        if unique_currs:
            detected_currencies = ", ".join(str(c) for c in unique_currs)
    else:
        detected_currencies = auto_detect_currency(
            df, {k: v["mapped_to"] for k, v in mapping.items()}
        )
        if not detected_currencies or detected_currencies == "USD":
            detected_currencies = "INR"

    date_cols = [col for col, info in mapping.items() if info["mapped_to"] == "date"]
    years_str = "2022-2025"
    if date_cols and date_cols[0] in df.columns:
        try:
            parsed_dates = pd.to_datetime(df[date_cols[0]].dropna(), errors="coerce")
            unique_years = sorted(
                parsed_dates.dt.year.dropna().unique().astype(int).tolist()
            )
            if unique_years:
                if len(unique_years) > 1:
                    years_str = f"{unique_years[0]}-{unique_years[-1]}"
                else:
                    years_str = str(unique_years[0])
        except Exception:
            years_str = "2022-2025"

    # Extract first 5 row items as preview dicts
    preview_rows = df.head(5).replace({np.nan: None}).to_dict(orient="records")

    return {
        "headers": cols,
        "suggested_mapping": mapping,
        "quality_report": dq.to_dict(),
        "preview_rows": preview_rows,
        "confidence_ok": confidence_ok,
        "records_count": num_records,
        "departments_count": num_depts,
        "categories_count": num_cats,
        "currencies_list": detected_currencies,
        "years_range": years_str,
    }


def auto_ingest_dataset(
    db: Session, file_content: bytes, filename: str, user_id: int, upload_id: str = None, preset_mapping: dict = None
) -> dict:
    """Intelligently parse, schema-detect, clean, validate, derive metrics, store in DB, and set as active dataset."""
    from services.cache_service import invalidate_global_cache
    from models.recommendation import Setting
    from models.uploaded_file import UploadedFile
    from models.workflow import WorkflowInstance
    from routers.datasets_router import _active_dataset, _schema_mappings
    import os

    if not upload_id:
        upload_id = str(uuid.uuid4())

    invalidate_global_cache()

    # Save the file content in uploads folder for re-mapping
    os.makedirs("uploads", exist_ok=True)
    filepath = os.path.join("uploads", f"{upload_id}.bin")
    with open(filepath, "wb") as f:
        f.write(file_content)

    df = load_file_to_dataframe(file_content, filename)
    if preset_mapping:
        mapping = preset_mapping
    else:
        mapping = infer_schema(df.columns.tolist(), db, user_id)
    dq = check_data_quality(df, mapping)

    # Save mappings feedback
    for orig, target_info in mapping.items():
        target = target_info.get("mapped_to") if isinstance(target_info, dict) else target_info
        if target:
            save_mapping_feedback(db, user_id, orig, target)

    detected_currency = auto_detect_currency(df, mapping)

    def _get_target(col_info):
        return col_info.get("mapped_to") if isinstance(col_info, dict) else col_info

    date_col = next((col for col, target in mapping.items() if _get_target(target) == "date"), None)
    dept_col = next((col for col, target in mapping.items() if _get_target(target) == "department"), None)
    currency_col = next((col for col, target in mapping.items() if _get_target(target) == "currency"), None)
    cost_center_col = next((col for col, target in mapping.items() if _get_target(target) == "cost_center"), None)
    rev_col = next((col for col, target in mapping.items() if _get_target(target) == "Revenue"), None)
    exp_col = next((col for col, target in mapping.items() if _get_target(target) == "Expense"), None)
    profit_col = next((col for col, target in mapping.items() if _get_target(target) == "Profit"), None)
    budget_col = next((col for col, target in mapping.items() if _get_target(target) == "Budget"), None)
    line_item_col = next((col for col, target in mapping.items() if _get_target(target) == "line_item"), None)
    amount_col = next((col for col, target in mapping.items() if _get_target(target) == "amount"), None)

    records = []
    rows_list = df.to_dict(orient="records")

    for row_dict in rows_list:
        date_val = parse_date(row_dict.get(date_col)) if date_col else "2026-01-01"
        dept_val = str(row_dict.get(dept_col) or "All Departments").strip() if dept_col else "All Departments"
        currency_val = str(row_dict.get(currency_col) or detected_currency or "USD").strip()
        cost_center_val = str(row_dict.get(cost_center_col) or "").strip()

        # Check wide financial columns
        rev_amt = parse_amount(row_dict.get(rev_col)) if rev_col else None
        exp_amt = parse_amount(row_dict.get(exp_col)) if exp_col else None
        profit_amt = parse_amount(row_dict.get(profit_col)) if profit_col else None
        budget_amt = parse_amount(row_dict.get(budget_col)) if budget_col else None

        # Derived Profit = Revenue - Expense
        if rev_amt is not None and exp_amt is not None:
            profit_amt = round(rev_amt - exp_amt, 2)
        elif profit_amt is None and rev_amt is not None and exp_amt is not None:
            profit_amt = round(rev_amt - exp_amt, 2)

        profit_margin_pct = round((profit_amt / rev_amt) * 100, 2) if (profit_amt is not None and rev_amt and rev_amt != 0) else None
        budget_var = round(exp_amt - budget_amt, 2) if (exp_amt is not None and budget_amt is not None) else None
        budget_var_pct = round((budget_var / budget_amt) * 100, 2) if (budget_var is not None and budget_amt and budget_amt != 0) else None

        dynamic_data = {
            k: (v if pd.notnull(v) else None) for k, v in row_dict.items()
        }
        if rev_amt is not None: dynamic_data["Revenue"] = rev_amt
        if exp_amt is not None: dynamic_data["Expense"] = exp_amt
        if profit_amt is not None: dynamic_data["Profit"] = profit_amt
        if budget_amt is not None: dynamic_data["Budget"] = budget_amt
        if profit_margin_pct is not None: dynamic_data["Profit_Margin_Pct"] = profit_margin_pct
        if budget_var is not None: dynamic_data["Budget_Variance"] = budget_var
        if budget_var_pct is not None: dynamic_data["Budget_Variance_Pct"] = budget_var_pct

        if rev_amt is not None:
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
            records.append({
                "domain": dept_val,
                "period": date_val,
                "line_item": "Expense",
                "amount": exp_amt,
                "currency": currency_val,
                "cost_center": cost_center_val,
                "dynamic_data": dynamic_data,
            })
        if rev_amt is None and exp_amt is None:
            item_val = str(row_dict.get(line_item_col) or "Financial Line Item").strip()
            amt_val = parse_amount(row_dict.get(amount_col)) if amount_col else 0.0
            records.append({
                "domain": dept_val,
                "period": date_val,
                "line_item": item_val,
                "amount": amt_val,
                "currency": currency_val,
                "cost_center": cost_center_val,
                "dynamic_data": dynamic_data,
            })

    db_records = pl_repository.create_pl_records(db, records, upload_id, user_id)

    # Save UploadedFile record
    up_file = db.query(UploadedFile).filter(UploadedFile.upload_id == upload_id).first()
    if not up_file:
        up_file = UploadedFile(
            upload_id=upload_id,
            filename=filename,
            file_size_bytes=len(file_content),
            user_id=user_id,
            status="COMPLETED"
        )
        db.add(up_file)
    else:
        up_file.status = "COMPLETED"
    db.commit()

    # Save Setting active_dataset_id & active_dataset_filename
    try:
        s_id = db.query(Setting).filter(Setting.key == "active_dataset_id").first()
        if not s_id:
            db.add(Setting(key="active_dataset_id", value=upload_id))
        else:
            s_id.value = upload_id

        s_fn = db.query(Setting).filter(Setting.key == "active_dataset_filename").first()
        if not s_fn:
            db.add(Setting(key="active_dataset_filename", value=filename))
        else:
            s_fn.value = filename

        db.commit()
    except Exception as set_err:
        logger.warning(f"Error persisting active dataset setting: {set_err}")

    # Set in-memory active dataset
    _active_dataset["dataset_id"] = upload_id
    _active_dataset["filename"] = filename

    # Trigger anomaly detection
    try:
        from services.anomaly_service import run_anomaly_detection
        run_anomaly_detection(db, upload_id)
    except Exception as ex:
        logger.error(f"Anomaly detection failed during auto-ingest: {ex}")

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

    return {
        "status": "READY",
        "dataset_id": upload_id,
        "upload_id": upload_id,
        "filename": filename,
        "records_count": len(db_records),
        "row_count": len(df),
        "column_count": len(df.columns),
        "quality_score": dq.to_dict().get("overall_score", 95.0),
        "detected_schema": detected_schema,
        "preview_rows": df.head(5).replace({np.nan: None}).to_dict(orient="records"),
        "has_departments": dept_col is not None,
    }


def finalize_ingestion(
    db: Session, file_content: bytes, filename: str, mapping: dict, user_id: int, upload_id: str
):
    """Backward compatibility wrapper delegating to auto_ingest_dataset."""
    res = auto_ingest_dataset(db, file_content, filename, user_id, upload_id=upload_id)
    return res["upload_id"], res["records_count"]


_demo_data_seeded = False

def ensure_demo_data(db: Session):
    """Seed the database with demo dataset if no records exist."""
    global _demo_data_seeded
    if _demo_data_seeded:
        return

    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        return

    from models.pl_record import PLRecord
    from models.recommendation import Setting
    from routers.datasets_router import _active_dataset

    # Sync active dataset from persistent Setting table if present
    try:
        active_setting = db.query(Setting).filter(Setting.key == "active_dataset_id").first()
        active_fn_setting = db.query(Setting).filter(Setting.key == "active_dataset_filename").first()

        if active_setting and active_setting.value:
            cnt = db.query(PLRecord).filter(PLRecord.upload_id == active_setting.value).count()
            if cnt > 0:
                _active_dataset["dataset_id"] = active_setting.value
                _active_dataset["filename"] = active_fn_setting.value if active_fn_setting else "Dataset"
            else:
                _active_dataset["dataset_id"] = "DEMO-DATASET"
                _active_dataset["filename"] = "unified_pnl_enterprise_demo.csv"
    except Exception as err:
        logger.warning(f"Failed to read active dataset setting: {err}")

    if db.query(PLRecord).count() > 0:
        _demo_data_seeded = True
        return

    logger.info("Database is empty on launch. Automatically generating and ingesting default synthetic dataset...")
    try:
        from services.synthetic_generator import generate_synthetic_dataset
        df = generate_synthetic_dataset()
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        content = csv_buffer.getvalue()

        res = auto_ingest_dataset(db, content, "unified_pnl_demo_dataset.csv", user_id=1, upload_id="DEMO-DATASET")
        _demo_data_seeded = True
        logger.info(f"Successfully auto-ingested default synthetic dataset: {res['records_count']} records.")
    except Exception as e:
        logger.error(f"Failed to generate and ingest default dataset: {e}")


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
