"""
High-Load Test for Seat Reservation System

🚀 TARGET: 10,000 requests per second
👥 USERS: 10,000
⚙️ WAIT TIME: Near-zero to maintain target RPS

Run with:
  locust -f loadtest_10000.py --headless -u 10000 -r 1000 --host=http://localhost:3000
"""

from locust import HttpUser, task, between, events
from random import randint, choice

# Configurable constants
ZONES = 50
ROWS_PER_ZONE = 20
SEATS_PER_ROW = 65

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"\n🚀 Starting high-load test: 10,000 users @ ~10,000 RPS")
    print(f"🔁 Random data used for each request (no testdata.jsonl needed)")
    print("✅ Locust config recommendation:")
    print("    locust -f loadtest_10000.py --headless -u 10000 -r 1000 --host=http://localhost:3000\n")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("✅ Test completed.")

class SeatBookingUser(HttpUser):
    wait_time = between(0.001, 0.002)  # ~1ms wait for max throughput

    @task
    def book_random_seat(self):
        payload = {
            "zone": randint(1, ZONES),
            "row": randint(1, ROWS_PER_ZONE),
            "count": choice([1, 2, 3, 4])  # Simulate 1–4 ticket selections
        }

        try:
            with self.client.post("/reserve", json=payload, catch_response=True, timeout=10) as response:
                if response.status_code == 409:
                    response.success()
                elif response.status_code in (200, 201):
                    response.success()
                else:
                    response.failure(f"Unexpected status code: {response.status_code}")
        except Exception as e:
            response = self.client.post("/reserve", json=payload, catch_response=True)
            response.failure(f"Exception: {str(e)}")
