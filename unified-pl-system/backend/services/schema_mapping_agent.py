import pandas as pd
from fuzzywuzzy import process
from sqlalchemy.orm import Session

from models.schema_mapping import SchemaMappingHistory

# Pre-defined known columns
STANDARD_COLUMNS = {
    "revenue": ["revenue", "income", "sales", "net sales"],
    "expense": ["expense", "cost", "operating cost", "cogs", "opex"],
    "period": ["date", "transaction date", "invoice date", "period"],
    "domain": ["domain", "business unit"],
    "cost_center": ["department", "cost center", "cost_center", "business unit"],
    "amount": ["amount", "value", "total"],
}


def map_columns(df: pd.DataFrame, db: Session, user_id: int) -> pd.DataFrame:
    mapped_df = df.copy()

    # 1. Learn from history first
    history = (
        db.query(SchemaMappingHistory)
        .filter(SchemaMappingHistory.confidence > 80)
        .all()
    )
    history_map = {h.original_column: h.mapped_column for h in history}

    new_cols = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()

        # Exact match in history
        if col_lower in history_map:
            new_cols[col] = history_map[col_lower]
            continue

        # Check standard definitions
        matched = False
        for std_col, aliases in STANDARD_COLUMNS.items():
            if col_lower in aliases:
                new_cols[col] = std_col
                # Store in history
                db.add(
                    SchemaMappingHistory(
                        user_id=user_id,
                        original_column=col_lower,
                        mapped_column=std_col,
                        confidence=100,
                    )
                )
                matched = True
                break

        if not matched:
            # Fuzzy match as fallback
            all_aliases = [
                alias for aliases in STANDARD_COLUMNS.values() for alias in aliases
            ]
            best_match, score = (
                process.extractOne(col_lower, all_aliases) if all_aliases else (None, 0)
            )
            if score > 85:  # High threshold
                # find the standard column for this alias
                for std_col, aliases in STANDARD_COLUMNS.items():
                    if best_match in aliases:
                        new_cols[col] = std_col
                        db.add(
                            SchemaMappingHistory(
                                user_id=user_id,
                                original_column=col_lower,
                                mapped_column=std_col,
                                confidence=score,
                            )
                        )
                        matched = True
                        break

        if not matched:
            new_cols[col] = col  # Keep original if no match

    db.commit()
    return mapped_df.rename(columns=new_cols)
