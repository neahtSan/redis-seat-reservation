import redis

# Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
EVENT_ID = 1
ZONE = 4
ROW = 12
SEATS_PER_ROW = 65  # Adjust if needed

# Key format
key = f"seats:{EVENT_ID}:{ZONE}:{ROW}"

# Connect to Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Fetch and print seat bitmap
print(f"🎟️  Seat status for {key}:")
seat_bits = []
for i in range(SEATS_PER_ROW):
    bit = r.getbit(key, i)
    seat_bits.append(str(bit))

# Print nicely (e.g., 10 per row)
for i in range(0, len(seat_bits), 10):
    row_slice = seat_bits[i:i+10]
    print(f"Seat {i:02}-{i+len(row_slice)-1:02}: " + " ".join(row_slice))
