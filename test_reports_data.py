import sys, io
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'unified-pl-system/backend')

from database import SessionLocal
from routers.reports import get_report_data

db = SessionLocal()
for r in ['executive', 'department', 'variance', 'anomaly', 'forecast']:
    data = get_report_data(report_type=r, dept='all', period='monthly', db=db)
    print(f"Report [{r}]: {data['title']}")
    print(f"  KPIs: {data['kpis']}")
    print(f"  Depts: {len(data['departments'])} records")
    print(f"  Summary: {data['narrative_summary'][:80]}...")
    print()

db.close()
