import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "unified-pl-system" / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models.recommendation import Setting
from models.pl_record import PLRecord
from models.uploaded_file import UploadedFile
from services.cache_service import invalidate_global_cache
import seed

db = SessionLocal()
seed.seed()

# Set active dataset to seeded demo dataset if available
demo_rec = db.query(PLRecord.upload_id).filter(PLRecord.upload_id != None).first()
if demo_rec:
    s_id = db.query(Setting).filter(Setting.key == "active_dataset_id").first()
    if s_id:
        s_id.value = demo_rec.upload_id
    else:
        db.add(Setting(key="active_dataset_id", value=demo_rec.upload_id))
    db.commit()

invalidate_global_cache()
print("Seeded dataset restored and active.")
