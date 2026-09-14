import sys
from database import SessionLocal
from services.metric_engine import MetricEngine
from services.analytics_engine import AnalyticsEngine
from routers.datasets_router import runtime_dataset_context

db = SessionLocal()
active_id = runtime_dataset_context.get_active_id()
me = MetricEngine(db, active_id)
ae = AnalyticsEngine(me)
fcst = ae.get_forecast(dept=None, metric="profit", n_forecast=12, agg="monthly")
print("FCST has_enough_data:", fcst.get("has_enough_data"))
print("FCST expected_case:", fcst.get("expected_case"))
print("FCST model_used:", fcst.get("model_used"))
print("FCST confidence_score:", fcst.get("confidence_score"))
print("FCST historical count:", len(fcst.get("historical", [])))
print("FCST forecast count:", len(fcst.get("forecast", [])))
db.close()
