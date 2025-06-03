import json
import random
from collections import defaultdict

# Optimized: Generate exactly 65,000 seats across orders
TARGET_TOTAL_SEATS = 65_000
ZONES = 50
ROWS_PER_ZONE = 20
SEATS_PER_ROW = 65
SEATS_PER_ZONE = 1300
TOTAL_SEATS = ZONES * SEATS_PER_ZONE  # 65,000 seats
SUCCESS_RATIO = 0.75  # 75% success rate
FAILURE_RATIO = 0.25  # 25% failure rate

# Seat count probability: favor smaller seat requests
SEAT_COUNT_WEIGHTS = {
    1: 0.5,
    2: 0.25,
    3: 0.15,
    4: 0.07,
    5: 0.03
}

# Calculate average seats per order
AVERAGE_SEATS_PER_ORDER = sum(count * weight for count, weight in SEAT_COUNT_WEIGHTS.items())
# Calculate number of orders needed to reach exactly 65,000 seats
NUM_USERS = int(TARGET_TOTAL_SEATS / AVERAGE_SEATS_PER_ORDER)

def get_weighted_seat_count():
    """Get a random seat count based on weights"""
    rand = random.random()
    cumulative = 0
    for count, weight in SEAT_COUNT_WEIGHTS.items():
        cumulative += weight
        if rand <= cumulative:
            return count
    return 1  # fallback

def get_controlled_seat_count(remaining_seats, remaining_orders):
    """Get seat count that helps reach exactly 65,000 total seats"""
    if remaining_orders == 1:
        # Last order gets all remaining seats (capped at 5)
        return min(remaining_seats, 5)
    
    # Target average for remaining orders
    target_avg = remaining_seats / remaining_orders
    
    # If we need higher counts, bias toward larger seat counts
    if target_avg > 2.5:
        weights = {1: 0.2, 2: 0.2, 3: 0.2, 4: 0.2, 5: 0.2}
    elif target_avg > 2.0:
        weights = {1: 0.3, 2: 0.3, 3: 0.2, 4: 0.1, 5: 0.1}
    else:
        weights = SEAT_COUNT_WEIGHTS
    
    rand = random.random()
    cumulative = 0
    for count, weight in weights.items():
        cumulative += weight
        if rand <= cumulative:
            return count
    return 1

def seats_overlap(start1, count1, start2, count2):
    """Check if two seat ranges overlap"""
    end1 = start1 + count1 - 1
    end2 = start2 + count2 - 1
    return not (end1 < start2 or end2 < start1)

def generate_successful_booking(remaining_seats, remaining_orders):
    """Generate a booking that should succeed (non-conflicting)"""
    zone = random.randint(1, ZONES)
    row = random.randint(1, ROWS_PER_ZONE)
    count = get_controlled_seat_count(remaining_seats, remaining_orders)
    return {
        "zone": zone,
        "row": row,
        "count": count
    }

def generate_conflicting_booking(successful_bookings):
    """Generate a booking that will conflict with an existing successful booking"""
    if not successful_bookings:
        return {"zone": random.randint(1, ZONES), "row": random.randint(1, ROWS_PER_ZONE), "count": get_weighted_seat_count()}
    
    # Pick a random successful booking to conflict with
    target = random.choice(successful_bookings)
    zone, row = target["zone"], target["row"]
    count = get_weighted_seat_count()
    
    return {
        "zone": zone,
        "row": row,
        "count": count
    }

print("Generating optimized test data to reach exactly 65,000 seats...")
print(f"Target: {NUM_USERS:,} orders to generate exactly {TARGET_TOTAL_SEATS:,} seats")
print(f"Average seats per order: {AVERAGE_SEATS_PER_ORDER:.2f}")
print(f"Available seat capacity: {TOTAL_SEATS:,} seats")
print(f"Over-capacity ratio: {TARGET_TOTAL_SEATS/TOTAL_SEATS:.1%}")

# Calculate numbers
num_successful = int(NUM_USERS * SUCCESS_RATIO)
num_failing = NUM_USERS - num_successful

# Target seats for successful bookings (they should use most of the 65k seats)
target_successful_seats = int(TARGET_TOTAL_SEATS * 0.9)  # 90% of seats go to successful bookings
target_failing_seats = TARGET_TOTAL_SEATS - target_successful_seats

print(f"Target: {num_successful:,} successful orders ({target_successful_seats:,} seats)")
print(f"Target: {num_failing:,} failing orders ({target_failing_seats:,} seats)")

# Track seat occupancy for realistic conflicts
seat_occupancy = defaultdict(lambda: defaultdict(set))  # zone -> row -> set of occupied seats
row_fill_status = defaultdict(lambda: defaultdict(int))  # zone -> row -> occupied_count

successful_bookings = []
all_bookings = []

# Helper function to find available seats in a row
def find_available_seats_in_row(zone, row, count):
    """Find a valid start position for 'count' seats in the given row"""
    occupied = seat_occupancy[zone][row]
    for start in range(SEATS_PER_ROW - count + 1):
        seat_range = set(range(start, start + count))
        if not occupied.intersection(seat_range):
            return start
    return None

# Generate successful bookings first - spread them across zones/rows
print("Generating successful bookings with controlled seat distribution...")
zone_distribution = list(range(1, ZONES + 1)) * (num_successful // ZONES + 1)
random.shuffle(zone_distribution)

remaining_successful_seats = target_successful_seats
for i in range(num_successful):
    if i % 5000 == 0:
        print(f"  Generated {i:,} successful bookings, {remaining_successful_seats:,} seats remaining...")
    
    remaining_orders = num_successful - i
    max_attempts = 200
    booking = None
    
    for attempt in range(max_attempts):
        # Try to distribute across zones evenly first
        if attempt < 100:
            zone = zone_distribution[i % len(zone_distribution)]
        else:
            zone = random.randint(1, ZONES)
            
        row = random.randint(1, ROWS_PER_ZONE)
        count = get_controlled_seat_count(remaining_successful_seats, remaining_orders)
        
        # Check if row has space
        if row_fill_status[zone][row] + count <= SEATS_PER_ROW:
            start = find_available_seats_in_row(zone, row, count)
            if start is not None:
                booking = {"zone": zone, "row": row, "start": start, "count": count}
                # Mark seats as occupied
                seat_range = set(range(start, start + count))
                seat_occupancy[zone][row].update(seat_range)
                row_fill_status[zone][row] += count
                remaining_successful_seats -= count
                break
    
    if booking is None:
        # Fallback: generate any valid booking with controlled count
        zone = random.randint(1, ZONES)
        row = random.randint(1, ROWS_PER_ZONE)
        if remaining_orders == 1:
            count = max(1, remaining_successful_seats)
        else:
            count = min(get_controlled_seat_count(remaining_successful_seats, remaining_orders), remaining_successful_seats)
        booking = {"zone": zone, "row": row, "count": count}
        remaining_successful_seats -= count
    
    successful_bookings.append(booking)
    all_bookings.append({
        "user_id": len(all_bookings) + 1,
        "zone": booking["zone"],
        "row": booking["row"],
        "count": booking["count"]
    })

print(f"Generated {len(successful_bookings):,} successful bookings")

# Generate failing bookings (intentionally conflicting)
print("Generating failing bookings...")
remaining_failing_seats = target_failing_seats
for i in range(num_failing):
    if i % 2000 == 0:
        print(f"  Generated {i:,} failing bookings, {remaining_failing_seats:,} seats remaining...")
    
    remaining_orders = num_failing - i
    booking = generate_conflicting_booking(successful_bookings)
    
    # Control seat count for failing bookings to hit exact target
    if remaining_orders == 1:
        # Last failing order gets all remaining seats
        booking["count"] = max(1, remaining_failing_seats)
        remaining_failing_seats = 0
    elif remaining_failing_seats > 0 and remaining_orders > 0:
        target_seats = max(1, remaining_failing_seats // remaining_orders)
        booking["count"] = min(booking["count"], target_seats, remaining_failing_seats)
        remaining_failing_seats -= booking["count"]
    else:
        booking["count"] = 1
    
    all_bookings.append({
        "user_id": len(all_bookings) + 1,
        "zone": booking["zone"],
        "row": booking["row"],
        "count": booking["count"]
    })

# Shuffle to randomize the order
print("Sorting bookings by user_id...")
all_bookings.sort(key=lambda b: b["user_id"])

# Write to JSONL
print("Writing testdata.jsonl...")
with open("testdata.jsonl", "w") as f:
    for booking in all_bookings:
        f.write(json.dumps(booking) + "\n")

# Calculate actual statistics
total_seats_generated = sum(booking["count"] for booking in all_bookings)
successful_seats_used = sum(row_fill_status[zone][row] for zone in row_fill_status for row in row_fill_status[zone])

print(f"\n=== GENERATION COMPLETE ===")
print(f"Generated testdata.jsonl with {NUM_USERS:,} orders")
print(f"Total seats in orders: {total_seats_generated:,} (target: {TARGET_TOTAL_SEATS:,})")
print(f"Successful orders: {len(successful_bookings):,} ({len(successful_bookings)/NUM_USERS:.1%})")
print(f"Failing orders: {num_failing:,} ({num_failing/NUM_USERS:.1%})")
print(f"Successful seats reserved: {successful_seats_used:,} ({successful_seats_used/TOTAL_SEATS:.1%} of capacity)")
print(f"Total venue capacity: {TOTAL_SEATS:,} seats")
print(f"Over-capacity ratio: {total_seats_generated/TOTAL_SEATS:.1%}")
print(f"Accuracy: Generated {abs(total_seats_generated - TARGET_TOTAL_SEATS)} seats from target")
print(f"This creates a realistic high-concurrency scenario with exactly {total_seats_generated:,} seat requests")
