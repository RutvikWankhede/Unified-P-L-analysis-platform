import uuid
from io import StringIO

import pandas as pd
from sqlalchemy.orm import Session

from repositories import pl_repository
from schemas.pl_schemas import PLRecordCreate
from services.data_quality_agent import check_data_quality
from services.schema_mapping_agent import map_columns


def process_csv_upload(db: Session, file_content: bytes, user_id: int):
    # Read CSV
    content = file_content.decode("utf-8")
    df = pd.read_csv(StringIO(content))

    # 1. Map Columns dynamically
    df = map_columns(df, db, user_id)

    # 2. Check Data Quality
    dq_result = check_data_quality(df)
    if not dq_result.is_valid:
        raise ValueError("Data Quality Check Failed: " + "; ".join(dq_result.warnings))

    # 3. Map to schema with dynamic data
    records = []
    required_cols = ["domain", "period", "line_item", "amount"]

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        dynamic_data = {
            k: v
            for k, v in row_dict.items()
            if k not in required_cols and k not in ["currency", "cost_center"]
        }

        records.append(
            PLRecordCreate(
                domain=row_dict["domain"],
                period=row_dict["period"],
                line_item=row_dict["line_item"],
                amount=float(row_dict["amount"]),
                currency=row_dict.get("currency", "USD"),
                cost_center=row_dict.get("cost_center"),
                dynamic_data=dynamic_data,
            )
        )

    upload_id = str(uuid.uuid4())
    db_records = pl_repository.create_pl_records(db, records, upload_id, user_id)

    # We could also save dq_result to a DataQualityReport table here

    return upload_id, len(db_records)
