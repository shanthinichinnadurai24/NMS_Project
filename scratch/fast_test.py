import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

client = app.test_client()

routes = [
    "/dashboard",
    "/devices",
    "/metrics",
    "/forecasting",
    "/capacity",
    "/alerts",
    "/performance",
    "/reports",
    "/settings",
    "/api/devices",
    "/api/metrics/chart/1",
    "/api/dashboard/charts",
    "/api/dashboard/device_utilization",
    "/api/forecast/1?resource=cpu&days=7",
    "/api/alerts",
    "/api/model/performance",
]

print("--- Testing Core System Endpoints ---")
all_passed = True
for r in routes:
    res = client.get(r)
    status = "OK" if res.status_code == 200 else f"FAIL ({res.status_code})"
    print(f"[{status:8s}] {r}")
    if res.status_code != 200:
        all_passed = False

if all_passed:
    print("\n>>> ALL CORE ENDPOINTS PASSED SUCCESSFULLY! <<<")
else:
    print("\n>>> SOME ENDPOINTS FAILED! <<<")
