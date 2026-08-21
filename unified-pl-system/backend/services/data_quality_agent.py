import pandas as pd
import numpy as np
import re
from datetime import datetime


class DataQualityReport:
    def __init__(
        self,
        score: int,
        metrics: dict,
        warnings: list,
        suggestions: list,
        is_valid: bool,
    ):
        self.score = score
        self.metrics = metrics
        self.warnings = warnings
        self.suggestions = suggestions
        self.is_valid = is_valid

    @property
    def grade(self) -> str:
        if self.score >= 95:
            return "A+"
        elif self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"
        elif self.score >= 70:
            return "C"
        elif self.score >= 50:
            return "D"
        return "F"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "grade": self.grade,
            "metrics": self.metrics,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "is_valid": self.is_valid,
        }


def check_data_quality(df: pd.DataFrame, mapping: dict = None) -> DataQualityReport:
    """
    Evaluates dataset quality against enterprise SaaS standards.
    Detects duplicates, missing dates, negative revenue, expense > revenue, future dates,
    invalid departments, invalid currencies, null columns, wrong datatypes, and empty rows.
    """
    warnings = []
    suggestions = []
    score = 100
    is_valid = True

    total_rows = len(df)
    if total_rows == 0:
        return DataQualityReport(
            score=0,
            metrics={
                "total_rows": 0,
                "missing_percent": 100.0,
                "duplicate_percent": 0.0,
                "anomaly_percent": 0.0,
                "outliers_count": 0,
                "date_consistency": False,
                "currency_consistency": True,
            },
            warnings=["Uploaded file is empty."],
            suggestions=["Please load a valid file containing financial entries."],
            is_valid=False,
        )

    # 1. Null Columns Detection
    null_cols = [col for col in df.columns if df[col].isnull().all()]
    if null_cols:
        score -= len(null_cols) * 5
        warnings.append(f"Completely null columns detected: {', '.join(null_cols)}.")
        suggestions.append("Remove completely empty columns to reduce overhead.")

    # 2. Empty Rows Detection
    # If the dataframe has rows where all fields are null (pandas dropna drops them, but check if we found them)
    # We check the original shape or if any index was skipped, but a general check is:
    null_rows = df.isnull().all(axis=1).sum()
    if null_rows > 0:
        score -= min(10, int((null_rows / total_rows) * 100.0))
        warnings.append(f"Detected {null_rows} completely blank rows.")
        suggestions.append("Clean blank spacer lines from your source spreadsheet.")

    # 3. Missing Values
    total_cells = df.size
    missing_cells = df.isnull().sum().sum()
    missing_percent = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
    if missing_percent > 0:
        score -= int(missing_percent * 2.5)
        if missing_percent > 5.0:
            warnings.append(
                f"High missing cell rate: {missing_percent:.1f}% of data values are empty."
            )
            suggestions.append(
                "Check mandatory fields; high missingness could break downstream ML algorithms."
            )
        else:
            warnings.append(
                f"Minor missing cell rate: {missing_percent:.1f}% of values are empty."
            )

    # 4. Duplicate Records
    duplicate_rows = df.duplicated().sum()
    duplicate_percent = (duplicate_rows / total_rows * 100.0) if total_rows > 0 else 0.0
    if duplicate_rows > 0:
        score -= int(duplicate_percent * 1.5)
        warnings.append(
            f"Duplicate records found: {duplicate_rows} rows ({duplicate_percent:.1f}%) are duplicates."
        )
        suggestions.append(
            "Filter duplicates out to prevent double-counting of transactions."
        )

    # Get mapped columns
    date_col = None
    dept_col = None
    currency_col = None
    amount_cols = []
    revenue_cols = []
    expense_cols = []

    if mapping:
        for orig, tgt_info in mapping.items():
            val = tgt_info.get("mapped_to") if isinstance(tgt_info, dict) else tgt_info
            if val == "date":
                date_col = orig
            elif val == "department":
                dept_col = orig
            elif val == "currency":
                currency_col = orig
            elif val == "amount":
                amount_cols.append(orig)
            elif val == "Revenue":
                revenue_cols.append(orig)
            elif val == "Expense":
                expense_cols.append(orig)

    # 5. Check Dates (Missing, Invalid Datatypes, and Future Dates)
    date_consistency = True
    if date_col and date_col in df.columns:
        parsed_dates = pd.to_datetime(df[date_col], errors="coerce")
        missing_dates = df[date_col].isnull().sum()
        if missing_dates > 0:
            score -= int((missing_dates / total_rows) * 10.0)
            warnings.append(
                f"Missing date values: {missing_dates} records have no transaction dates."
            )
            suggestions.append(
                "Fill in transaction dates; system cannot assign periods to undated rows."
            )

        invalid_dates = parsed_dates.isnull().sum() - missing_dates
        if invalid_dates > 0:
            score -= int((invalid_dates / total_rows) * 15.0) + 5
            date_consistency = False
            warnings.append(
                f"Wrong date format/unparseable values: {invalid_dates} rows have invalid dates."
            )
            suggestions.append(
                "Ensure date columns are in standard ISO, YYYY-MM-DD, or DD/MM/YYYY formats."
            )

        # Future dates check
        future_dates = (parsed_dates > datetime.now()).sum()
        if future_dates > 0:
            score -= min(15, int((future_dates / total_rows) * 20.0))
            warnings.append(
                f"Future transaction dates detected: {future_dates} rows have dates in the future."
            )
            suggestions.append(
                "Check if posting dates or forecasts were merged into historical tables."
            )

    # 6. Check Departments (Empty or Invalid Values)
    if dept_col and dept_col in df.columns:
        invalid_depts = (
            df[dept_col]
            .dropna()
            .apply(lambda x: not isinstance(x, str) or len(str(x).strip()) == 0)
            .sum()
        )
        if invalid_depts > 0:
            score -= 5
            warnings.append(
                f"Invalid departments: found {invalid_depts} records with blank/non-string department fields."
            )
            suggestions.append("Standardize department codes to standard text values.")

    # 7. Check Currencies (Invalid formats)
    currency_consistency = True
    if currency_col and currency_col in df.columns:
        unique_currencies = df[currency_col].dropna().unique()
        if len(unique_currencies) > 1:
            score -= 10
            currency_consistency = False
            warnings.append(
                f"Mixed currencies: file contains {len(unique_currencies)} currencies ({', '.join(map(str, unique_currencies))})."
            )
            suggestions.append(
                "Normalize multi-currency ledgers using currency exchange helper rates."
            )

        # Validate standard 3-letter currency format (e.g. USD, EUR)
        invalid_cur_formats = (
            df[currency_col]
            .dropna()
            .apply(
                lambda x: not isinstance(x, str)
                or not re.match(r"^[A-Z]{3}$", str(x).strip().upper())
            )
            .sum()
        )
        if invalid_cur_formats > 0:
            score -= 5
            warnings.append(
                f"Invalid currency format: found {invalid_cur_formats} records with invalid currency labels."
            )
            suggestions.append(
                "Ensure currency labels conform to 3-letter ISO-4217 standard (e.g. USD, EUR, INR)."
            )

    # 8. Numeric Formatting & Values Check (Negative Revenue, Expense > Revenue, Outliers)
    from services.pl_service import parse_amount

    # Resolve amount values
    total_rev_sum = 0.0
    total_exp_sum = 0.0
    outliers_count = 0
    wrong_amount_datatypes = 0

    all_numeric_cols = amount_cols + revenue_cols + expense_cols
    if not all_numeric_cols:
        all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in all_numeric_cols:
        if col in df.columns:
            # Check if there are unparseable amounts
            for val in df[col].dropna():
                try:
                    parse_amount(val)
                except Exception:
                    wrong_amount_datatypes += 1

            col_data = df[col].dropna().apply(lambda x: float(parse_amount(x)))

            # Sum up Revenue/Expense for structural validation
            if col in revenue_cols:
                total_rev_sum += col_data.sum()
                # Negative Revenue check
                neg_rev_count = (col_data < 0).sum()
                if neg_rev_count > 0:
                    score -= min(15, int((neg_rev_count / len(col_data)) * 100))
                    warnings.append(
                        f"Negative revenue detected: {neg_rev_count} rows in revenue contain negative amounts."
                    )
                    suggestions.append(
                        "Move credit balances or refunds to offsets rather than negative sales."
                    )
            elif col in expense_cols:
                total_exp_sum += col_data.sum()

            # Extreme outliers check (IQR check)
            if len(col_data) > 4:
                q25, q75 = np.percentile(col_data, [25, 75])
                iqr = q75 - q25
                lower_bound = q25 - (3.0 * iqr)
                upper_bound = q75 + (3.0 * iqr)
                outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
                outliers_count += len(outliers)

    if wrong_amount_datatypes > 0:
        score -= min(20, int((wrong_amount_datatypes / total_rows) * 100.0) + 5)
        warnings.append(
            f"Wrong numeric datatypes: found {wrong_amount_datatypes} rows with non-numeric amount characters."
        )
        suggestions.append(
            "Check if commas, currency symbols, or footnotes are in raw amount cells."
        )

    anomaly_percent = (outliers_count / total_rows * 100.0) if total_rows > 0 else 0.0
    if outliers_count > 0:
        score -= min(15, int(anomaly_percent * 2.0))
        warnings.append(
            f"Statistical anomalies: found {outliers_count} extreme outlier values ({anomaly_percent:.1f}%)."
        )
        suggestions.append(
            "Inspect transaction outliers; confirm they do not represent ledger input typos."
        )

    # Expense > Revenue Batch validation
    if total_rev_sum > 0 and total_exp_sum > total_rev_sum:
        score -= 10
        warnings.append(
            f"Structural variance warning: Total Expenses (${total_exp_sum:,.2f}) exceed Total Revenue (${total_rev_sum:,.2f})."
        )
        suggestions.append(
            "Verify if this is an operational net-loss batch or if columns were transposed."
        )

    # 9. Target Schema Completeness
    if mapping:
        required_targets = {"date", "department"}
        mapped_targets = set()
        for orig, tgt_info in mapping.items():
            val = tgt_info.get("mapped_to") if isinstance(tgt_info, dict) else tgt_info
            if val:
                mapped_targets.add(val)

        has_long = "line_item" in mapped_targets and "amount" in mapped_targets
        has_wide = "Revenue" in mapped_targets or "Expense" in mapped_targets

        missing_reqs = required_targets - mapped_targets
        if missing_reqs or not (has_long or has_wide):
            is_valid = False
            score = 0
            missing_labels = list(missing_reqs)
            if not has_long and not has_wide:
                missing_labels.append("amount/Revenue/Expense mapping")
            warnings.append(
                f"Critical column targets are unmapped: {', '.join(missing_labels)}."
            )
            suggestions.append(
                "Manually align your columns using the header selectors to validate upload."
            )

    score = max(5, min(100, score))
    metrics = {
        "total_rows": total_rows,
        "missing_percent": round(missing_percent, 1),
        "duplicate_percent": round(duplicate_percent, 1),
        "anomaly_percent": round(anomaly_percent, 1),
        "outliers_count": outliers_count,
        "date_consistency": date_consistency,
        "currency_consistency": currency_consistency,
    }

    return DataQualityReport(
        score=score,
        metrics=metrics,
        warnings=warnings,
        suggestions=suggestions,
        is_valid=is_valid,
    )
