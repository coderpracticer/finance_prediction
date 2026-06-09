import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class WebDashboardTests(unittest.TestCase):
    def test_dashboard_is_served_from_backend(self) -> None:
        client = TestClient(app)

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Investment Opportunity Dashboard", response.text)


if __name__ == "__main__":
    unittest.main()

