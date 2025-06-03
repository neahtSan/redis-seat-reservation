"""
Easy Load Test Configuration - Change TARGET_RPS to switch between load levels

🎯 CHANGE THIS VALUE TO SET YOUR TARGET:
- TARGET_RPS = 300  →  300 requests/second
- TARGET_RPS = 400  →  400 requests/second  
- TARGET_RPS = 500  →  500 requests/second

Then use these Locust UI settings:
- Users: Same as TARGET_RPS (300, 400, or 500)
- Ramp up: 10 users/second
- Host: http://localhost:3000

The wait_time will automatically adjust based on TARGET_RPS!
"""
from locust import HttpUser, task, between, events
from locust.exception import StopUser
import json
import threading
import itertools

# 🎯 EASY CONFIGURATION - Just change this number!
TARGET_RPS = 500  # Change to 300, 400, or 500 for different load levels

# Auto-calculate wait time (1 user = 1 req/sec when wait_time = 1.0)
WAIT_TIME = 1.0

# Configuration summary will be printed at startup
print(f"🎯 TARGET: {TARGET_RPS} requests/second")
print(f"👥 RECOMMENDED USERS: {TARGET_RPS}")
print(f"⏱️  WAIT TIME: {WAIT_TIME} seconds between requests")
print("📝 Locust UI Settings:")
print(f"   - Users: {TARGET_RPS}")
print(f"   - Ramp up: 10")
print(f"   - Host: http://localhost:3000")

test_cases_list = []
test_case_lock = threading.Lock()

def load_test_cases():
    """Load all test cases into memory and cycle through them"""
    global test_cases_list
    if not test_cases_list:
        with open("testdata.jsonl", "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        test_cases_list.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return itertools.cycle(test_cases_list)

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"🚀 Starting sustained load test for {TARGET_RPS} req/sec...")
    print(f"📊 Loaded {len(test_cases_list)} test cases (will cycle infinitely)")
    print(f"⚙️  Configuration: {environment.parsed_options.num_users} users × {1/WAIT_TIME:.1f} req/sec each")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("✅ Test complete.")

class SeatBookingUser(HttpUser):
    # Auto-calculated wait time based on TARGET_RPS
    # For TARGET_RPS users making 1 req/sec each = TARGET_RPS req/sec total
    wait_time = between(WAIT_TIME, WAIT_TIME)
    
    def on_start(self):
        """Initialize user with cycling test data"""
        self.test_case_iter = load_test_cases()
        print(f"👤 User {id(self)} started - ready for sustained load")

    @task
    def book_seat(self):
        """Make a seat reservation request - cycles through test data infinitely"""
        # Get next test case (cycles infinitely)
        data = next(self.test_case_iter)
        
        payload = {
            "zone": data.get("zone"),
            "row": data.get("row"),
            "count": data.get("count")
        }

        try:
            with self.client.post("/reserve", json=payload, catch_response=True, timeout=30) as response:
                user_id = data.get("user_id")
                
                # Handle connection issues that might cause status code 0
                if response.status_code == 0:
                    print(f"🔌 CONNECTION ERROR: User {user_id} — Network/timeout issue")
                    response.failure("Connection error - status code 0")
                elif response.status_code == 409:
                    print(f"🔒 CONFLICT: User {user_id} — Zone {payload['zone']}, Row {payload['row']}, Count {payload['count']}")
                    response.success()
                elif response.status_code in (200, 201):
                    print(f"✅ SUCCESS: User {user_id} — Zone {payload['zone']}, Row {payload['row']}, Count {payload['count']}")
                    response.success()
                else:
                    print(f"❌ UNEXPECTED: User {user_id} — {response.status_code} {response.text}")
                    response.failure(f"Unexpected status code: {response.status_code}")
        except Exception as e:
            print(f"🚨 EXCEPTION: User {data.get('user_id')} — {str(e)}")
            # Mark as failure but don't crash the user
            self.client.post("/reserve", json=payload, catch_response=True).failure(f"Exception: {str(e)}")

        # No StopUser() - user continues making requests indefinitely
