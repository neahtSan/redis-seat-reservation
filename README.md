# 🎫 Redis Seat Reservation System

<div align="center">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/NestJS-E0234E?style=for-the-badge&logo=nestjs&logoColor=white" alt="NestJS"/>
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Locust-00C851?style=for-the-badge&logo=locust&logoColor=white" alt="Locust"/>
</div>

<br/>

A high-performance seat reservation system built with **Redis bitmaps** and **NestJS**, designed to handle thousands of concurrent seat bookings with atomic operations and real-time occupancy tracking.

## 🏗️ System Architecture

- **65,000 Seats**: 50 zones × 20 rows × 65 seats per row
- **Redis Bitmaps**: Ultra-efficient storage (1 bit per seat)
- **Atomic Operations**: Lua scripts for contiguous seat reservations
- **Connection Pooling**: Optimized Redis connection management
- **Clean Error Handling**: Only SUCCESS (200/201) and CONFLICT (409) responses

## 🚀 Features

### Core Functionality
- **Contiguous Seat Reservations**: Atomic Lua scripts ensure seats are booked together
- **Real-time Occupancy Tracking**: Check seat availability by zone and row
- **Global Availability Status**: Monitor system-wide seat occupancy
- **Concurrent Safe Operations**: Redis bitmap operations handle thousands of simultaneous requests
- **Memory Efficient**: Each seat uses only 1 bit of storage

### API Endpoints

#### Seat Reservation
```http
POST /reserve
Content-Type: application/json

{
  "zone": 1,
  "row": 1,
  "count": 2
}
```

#### Occupancy Checking
```http
GET /occupancy/:zone/:row
GET /availability/check-all
```

#### System Management
```http
POST /initialize     # Initialize all seat tables
GET /stats          # Redis memory and key statistics
POST /clear         # Clear all seat data (testing)
```

## 🛠️ Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Redis 7+ (included in Docker setup)

### Run with Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/neahtSan/redis-lab.git
cd redis-lab

# Start the complete system
docker-compose up

# Access the application
curl http://localhost:3000/stats
```

### Local Development Setup
```bash
# Install dependencies
cd backend
pnpm install

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Run in development mode
pnpm run start:dev
```

## 📊 Load Testing

This system includes comprehensive load testing tools to evaluate performance at scale.

### Available Test Configurations

#### 1. Configurable Load Testing (300-500 RPS)
```bash
# Edit loadtest/locustfile.py and change TARGET_RPS
TARGET_RPS = 300  # or 400, 500

# Run with Locust UI
cd loadtest
locust -f locustfile.py --host=http://localhost:3000
```

#### 2. High-Load Testing (10,000 RPS)
```bash
# Extreme load testing
cd loadtest
locust -f locust-10kUsers.py --headless -u 10000 -r 1000 --host=http://localhost:3000
```

#### 3. System Diagnostics
```bash
# Monitor system bottlenecks during load testing
cd loadtest
python diagnose_bottlenecks.py
```

### Load Testing Features
- **Realistic Data**: Uses generated test data with varied seat requests
- **Error Handling**: Detects and categorizes connection timeouts and failures
- **Performance Metrics**: Measures response times, throughput, and error rates
- **Sustained Load**: Continuous testing capability for endurance analysis

## 🏛️ System Architecture

### Redis Data Structure
```
Key Pattern: seats:{eventId}:{zone}:{row}
Data Type: Bitmap (1 bit per seat)
Example: seats:1:25:10 = "0110111000..." (65 bits)
```

### Atomic Operations
```lua
-- Lua script for contiguous seat reservation
for i = 0, (seats_per_row - seats_needed) do
  local bitsVal = redis.call('BITFIELD', key, 'GET', 'u'..seats_needed, i)[1]
  if bitsVal == 0 then
    -- Reserve seats atomically
    for j = 0, (seats_needed - 1) do
      redis.call('SETBIT', key, i + j, 1)
    end
    return i
  end
end
```

### Performance Characteristics
- **Memory Usage**: ~65,000 seats = 8.1 KB per row bitmap
- **Total Storage**: 1,000 Redis keys ≈ 8.1 MB for all seats
- **Lookup Speed**: O(1) for individual seat status
- **Reservation Speed**: O(n) where n = seats per row (65)

## 📈 Monitoring & Observability

The system includes comprehensive monitoring with:

### Prometheus Metrics
- Redis connection pool statistics
- Request latency and throughput
- Error rates and types
- Memory usage patterns

### Grafana Dashboards
```bash
# Access monitoring
http://localhost:4000  # Grafana
http://localhost:9090  # Prometheus
http://localhost:9121  # Redis Exporter
```

### Built-in Diagnostics
```bash
# System health check
curl http://localhost:3000/stats

# Check global occupancy
curl http://localhost:3000/availability/check-all

# Zone-specific occupancy
curl http://localhost:3000/occupancy/25/10
```

## 🔧 Configuration

### Redis Connection Pool
```typescript
// Optimized for high concurrency
{
  max: 20,           // Maximum connections
  min: 2,            // Minimum connections
  acquireTimeoutMillis: 10000,
  connectTimeout: 10000,
  commandTimeout: 5000
}
```

### System Limits
- **Zones**: 50 (configurable)
- **Rows per Zone**: 20 (configurable)
- **Seats per Row**: 65 (configurable)
- **Max Reservation**: 5 seats per request
- **Total Capacity**: 65,000 seats

## 🧪 Testing

### Unit Tests
```bash
cd backend
pnpm run test
```

### Integration Tests
```bash
# Test all endpoints
python test_endpoints.py

# Manual API testing
curl -X POST http://localhost:3000/initialize
curl -X POST http://localhost:3000/reserve \
  -H "Content-Type: application/json" \
  -d '{"zone": 1, "row": 1, "count": 2}'
```

### Performance Testing
```bash
# Quick performance test
python loadtest/precise_load_test.py

# Sustained load test
docker-compose up locust
```

## 📝 API Response Codes

This system uses a simplified error model for predictable behavior:

| Status Code | Meaning | Usage |
|-------------|---------|-------|
| **200 OK** | Success | Seats reserved, data retrieved |
| **201 Created** | Success | Resources initialized |
| **409 Conflict** | Any Error | Invalid input, no seats available, system errors |

*No other status codes are returned, ensuring clean error handling in load testing.*

## 🚀 Deployment

### Production Considerations
- **Connection Pooling**: Tune Redis pool size based on expected concurrent users
- **Memory Planning**: Allow ~10 MB for seat data + Redis overhead
- **CPU Scaling**: Each Lua script execution requires minimal CPU
- **Network**: High-frequency bitmap operations benefit from low latency to Redis

### Docker Production Setup
```bash
# Build optimized production image
docker build -t redis-seat-system .

# Deploy with resource limits
docker run -d \
  --memory=512m \
  --cpus=2 \
  -p 3000:3000 \
  redis-seat-system
```

## 📚 Technical Details

### Why Redis Bitmaps?
1. **Memory Efficiency**: 1 bit per seat vs 8+ bytes for traditional storage
2. **Atomic Operations**: Built-in concurrency safety
3. **High Performance**: Microsecond-level seat lookups
4. **Scalability**: Linear scaling with seat count

### Lua Script Benefits
- **Atomicity**: All-or-nothing seat reservations
- **Performance**: Reduces Redis round trips
- **Consistency**: Prevents race conditions
- **Flexibility**: Custom logic for contiguous seat finding

### Connection Pool Strategy
- **Prevents Exhaustion**: Limits concurrent Redis connections
- **Improves Latency**: Reuses existing connections
- **Error Recovery**: Handles connection failures gracefully
- **Monitoring**: Tracks pool usage for optimization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Workflow
```bash
# Setup development environment
git clone https://github.com/neahtSan/redis-lab.git
cd redis-lab
docker-compose up redis  # Start Redis only
cd backend
pnpm install
pnpm run start:dev

# Run tests
pnpm run test
python test_endpoints.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <img src="https://github.com/neahtSan.png" width="80" style="border-radius: 50%;" alt="neahtSan Logo"/>
  <br>
  <strong>Made with ❤️ by <a href="https://github.com/neahtSan">neahtSan</a></strong>
</div>
