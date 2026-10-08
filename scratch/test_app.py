import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, startup

class NCPAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls.client = app.test_client()

    def test_pages(self):
        pages = [
            "/dashboard",
            "/devices",
            "/metrics",
            "/forecasting",
            "/capacity",
            "/alerts",
            "/performance",
            "/reports",
            "/settings",
        ]
        for page in pages:
            res = self.client.get(page)
            print(f"Page {page:15s} -> Status {res.status_code}")
            self.assertEqual(res.status_code, 200, f"Page {page} failed")

    def test_apis(self):
        apis = [
            "/api/devices",
            "/api/devices/1",
            "/api/metrics",
            "/api/metrics/1",
            "/api/metrics/chart/1",
            "/api/dashboard/charts",
            "/api/dashboard/device_utilization",
            "/api/forecast/1?resource=cpu&days=7",
            "/api/forecast/1?resource=memory&days=7",
            "/api/forecast/1?resource=bandwidth&days=7",
            "/api/capacity",
            "/api/capacity/1",
            "/api/alerts",
            "/api/model/performance",
            "/api/reports/summary",
            "/api/reports/capacity_summary",
        ]
        for endpoint in apis:
            res = self.client.get(endpoint)
            print(f"API {endpoint:45s} -> Status {res.status_code}")
            self.assertEqual(res.status_code, 200, f"API {endpoint} failed")
            data = json.loads(res.data)
            self.assertEqual(data.get("status"), "ok")

if __name__ == "__main__":
    unittest.main()
