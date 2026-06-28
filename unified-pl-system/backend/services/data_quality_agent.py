import pandas as pd


class DataQualityResult:
    def __init__(self):
        self.score = 100
        self.warnings = []
        self.suggestions = []
        self.is_valid = True


def check_data_quality(df: pd.DataFrame) -> DataQualityResult:
    result = DataQualityResult()

    # 1. Missing Values
    missing_count = df.isnull().sum().sum()
    if missing_count > 0:
        result.score -= 10
        result.warnings.append(f"Found {missing_count} missing values.")
        result.suggestions.append(
            "Consider imputing missing values or dropping incomplete rows."
        )

    # 2. Duplicate Records
    duplicate_count = df.duplicated().sum()
    if duplicate_count > 0:
        result.score -= 15
        result.warnings.append(f"Found {duplicate_count} duplicate records.")
        result.suggestions.append("Deduplicate dataset before anomaly detection.")

    # 3. Negative Revenue / Expenses
    if "line_item" in df.columns and "amount" in df.columns:
        # Check negative revenue
        revenue_mask = (
            df["line_item"].str.lower().str.contains("revenue|income|sales", na=False)
        )
        neg_rev = df[revenue_mask & (df["amount"] < 0)]
        if not neg_rev.empty:
            result.score -= 20
            result.warnings.append(
                f"Found {len(neg_rev)} records with negative revenue."
            )

        # Check negative expenses
        expense_mask = (
            df["line_item"].str.lower().str.contains("expense|cost|cogs|opex", na=False)
        )
        neg_exp = df[expense_mask & (df["amount"] < 0)]
        if not neg_exp.empty:
            result.score -= 10
            result.warnings.append(
                f"Found {len(neg_exp)} records with negative expenses. This might represent credits."
            )

    # 4. Incomplete critical columns
    required = ["domain", "period", "line_item", "amount"]
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        result.is_valid = False
        result.score = 0
        result.warnings.append(f"Missing critical columns: {', '.join(missing_cols)}")

    result.score = max(0, result.score)
    return result
