import os
import sys

print("Testing database & metric engine...")
from database import SessionLocal
from services.metric_engine import MetricEngine
from routers.datasets_router import runtime_dataset_context

db = SessionLocal()
active_id = runtime_dataset_context.get_active_id()
print("Active ID:", active_id)
me = MetricEngine(db, active_id)
kpis = me.get_kpis()
print("KPIS:", kpis)
db.close()
print("Done!")
