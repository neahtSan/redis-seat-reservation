/* eslint-disable prettier/prettier */
import { Injectable } from '@nestjs/common';
import Redis from 'ioredis';
import * as genericPool from 'generic-pool';

const ZONES = 50;
const ROWS_PER_ZONE = 20;
const SEATS_PER_ROW = 65;
const SEATS_PER_ZONE = 1300;
const EVENT_ID = 1;

@Injectable()
export class SeatService {
  private redisPool: ReturnType<typeof genericPool.createPool>;
  private readonly seatsPerZone = SEATS_PER_ZONE;
  private readonly seatsPerRow = SEATS_PER_ROW;

  // Lua script to find and reserve a contiguous block of seats in a row
  private readonly reserveScript: string = `
    local key = KEYS[1]
    local seats_needed = tonumber(ARGV[1])
    local seats_per_row = tonumber(ARGV[2])
    -- Loop through seat indices in the row
    for i = 0, (seats_per_row - seats_needed) do
      local bitsVal = redis.call('BITFIELD', key, 'GET', 'u'..seats_needed, i)[1]
      if bitsVal == 0 then
        for j = 0, (seats_needed - 1) do
          redis.call('SETBIT', key, i + j, 1)
        end
        return i
      end
    end
    return -1
  `;

  constructor() {
    // Create a Redis connection pool with better error handling
    this.redisPool = genericPool.createPool({
      create: () => {
        const client = new Redis({
          host: 'redis',
          port: 6379,
          enableReadyCheck: true,
          maxRetriesPerRequest: 3,
          lazyConnect: true,
          keepAlive: 30000,
          connectTimeout: 10000,
          commandTimeout: 5000
        });
        
        // Handle connection errors
        client.on('error', (err) => {
          console.error('Redis connection error:', err);
        });
        
        return Promise.resolve(client);
      },
      destroy: async (client: Redis) => { 
        try {
          await client.quit(); 
        } catch (err) {
          console.error('Error closing Redis connection:', err);
        }
      },
    }, {
      max: 20, // Tune this number based on your server's capacity
      min: 2,
      acquireTimeoutMillis: 10000,
      idleTimeoutMillis: 30000
    });
  }

  /**
   * Pre-initialize all seat tables in Redis for performance testing
   * Creates all possible zone:row combinations as bitmaps
   */
  async initializeAllSeatTables(): Promise<void> {
    console.log('🚀 Starting Redis seat table initialization...');
    const startTime = Date.now();
    
    const client = await this.redisPool.acquire() as Redis;
    try {
      const pipeline = client.pipeline();
      let totalKeys = 0;

      // Create all possible seat keys
      for (let zone = 1; zone <= ZONES; zone++) {
        for (let row = 1; row <= ROWS_PER_ZONE; row++) {
          const seatKey = `seats:${EVENT_ID}:${zone}:${row}`;
          // Initialize bitmap by setting the last bit (this creates the full bitmap)
          pipeline.setbit(seatKey, SEATS_PER_ROW - 1, 0);
          totalKeys++;
        }
      }

      // Execute all commands in batch
      await pipeline.exec();
      
      const duration = Date.now() - startTime;
      const totalSeats = ZONES * ROWS_PER_ZONE * SEATS_PER_ROW;
      console.log(`✅ Initialized ${totalKeys} seat tables in ${duration}ms`);
      console.log(`📊 Total rows: ${ZONES} zones × ${ROWS_PER_ZONE} rows = ${totalKeys} Redis keys`);
      console.log(`🎫 Seats per row: ${SEATS_PER_ROW}`);
      console.log(`🏟️ Total seat capacity: ${totalSeats.toLocaleString()} seats`);
    } finally {
      await this.redisPool.release(client);
    }
  }

  /**
   * Get Redis memory usage and key statistics
   */
  async getRedisStats(): Promise<{
    memoryUsed: string;
    totalKeys: number;
    seatKeys: number;
    estimatedSizePerKey: number;
  }> {
    const client = await this.redisPool.acquire() as Redis;
    try {
      // Get memory info using INFO command
      const memoryInfo = await client.info('memory');
      const memoryUsedMatch = memoryInfo.match(/used_memory:(\d+)/);
      const memoryUsedBytes = memoryUsedMatch ? parseInt(memoryUsedMatch[1], 10) : 0;
      
      const totalKeys = await client.dbsize();
      
      // Count seat-specific keys
      const seatKeyPattern = `seats:${EVENT_ID}:*`;
      const seatKeys = await client.keys(seatKeyPattern);
      const seatKeyCount = seatKeys.length;
      
      // Calculate estimated size per key (each bitmap = 65 bits = ~9 bytes + overhead)
      const estimatedSizePerKey = Math.ceil(SEATS_PER_ROW / 8) + 50; // bits to bytes + Redis overhead
      
      const memoryMB = (memoryUsedBytes / 1024 / 1024).toFixed(2);
      return {
        memoryUsed: `${memoryMB} MB`,
        totalKeys,
        seatKeys: seatKeyCount,
        estimatedSizePerKey
      };
    } finally {
      await this.redisPool.release(client);
    }
  }

  /**
   * Clear all seat data (useful for testing)
   */
  async clearAllSeatData(): Promise<void> {
    console.log('🧹 Clearing all seat data...');
    const client = await this.redisPool.acquire() as Redis;
    try {
      const seatKeyPattern = `seats:${EVENT_ID}:*`;
      const seatKeys = await client.keys(seatKeyPattern);
      
      if (seatKeys.length > 0) {
        await client.del(...seatKeys);
        console.log(`✅ Deleted ${seatKeys.length} seat keys`);
      } else {
        console.log('ℹ️ No seat keys found to delete');
      }
    } finally {
      await this.redisPool.release(client);
    }
  }

  /**
   * Attempts to reserve a contiguous block of `count` seats in a given zone and row.
   * @param zone Zone number (1-based)
   * @param row Row number (1-based)
   * @param count Number of seats to reserve
   * @return the starting seat index if successful, or -1 if no suitable block found.
   */
  async reserveContiguousSeats(zone: number, row: number, count: number): Promise<number> {
    if (zone < 1 || zone > ZONES || row < 1 || row > ROWS_PER_ZONE) {
      throw new Error('Invalid zone or row');
    }
    const seatKey = `seats:${EVENT_ID}:${zone}:${row}`;
    const client = await this.redisPool.acquire() as Redis;
    try {
      // Ensure the bitmap key exists and has length = seatsPerRow (set last bit to define size)
      const curLenBytes = await client.strlen(seatKey);
      if (curLenBytes * 8 < this.seatsPerRow) {
        await client.setbit(seatKey, this.seatsPerRow - 1, 0);
      }
      // Execute the Lua script atomically on Redis
      const result = await client.eval(
        this.reserveScript, 1, seatKey, count, this.seatsPerRow
      );
      return typeof result === 'number' ? result : parseInt(result as string);
    } finally {
      await this.redisPool.release(client);
    }
  }

  /**
   * Attempts to reserve specific seats starting at a given position.
   * @param zone Zone number (1-based)
   * @param row Row number (1-based)
   * @param start Starting seat position (0-based)
   * @param count Number of seats to reserve
   * @return the starting seat index if successful, or -1 if seats are already taken.
   */
  async reserveSpecificSeats(zone: number, row: number, start: number, count: number): Promise<number> {
    if (zone < 1 || zone > ZONES || row < 1 || row > ROWS_PER_ZONE) {
      throw new Error('Invalid zone or row');
    }
    if (start < 0 || start + count > this.seatsPerRow) {
      throw new Error('Invalid seat range');
    }
    const seatKey = `seats:${EVENT_ID}:${zone}:${row}`;
    const client = await this.redisPool.acquire() as Redis;
    try {
      // Ensure the bitmap key exists and has length = seatsPerRow
      const curLenBytes = await client.strlen(seatKey);
      if (curLenBytes * 8 < this.seatsPerRow) {
        await client.setbit(seatKey, this.seatsPerRow - 1, 0);
      }
      // Check if the specific seats are available and reserve them atomically
      const reserveSpecificScript = `
        local key = KEYS[1]
        local start_pos = tonumber(ARGV[1])
        local count = tonumber(ARGV[2])
        -- Check if all seats in the range are free
        for i = 0, (count - 1) do
          local bit = redis.call('GETBIT', key, start_pos + i)
          if bit == 1 then
            return -1  -- seat already taken
          end
        end
        -- All seats are free, reserve them
        for i = 0, (count - 1) do
          redis.call('SETBIT', key, start_pos + i, 1)
        end
        return start_pos
      `;
      const result = await client.eval(
        reserveSpecificScript, 1, seatKey, start, count
      );
      return typeof result === 'number' ? result : parseInt(result as string);
    } finally {
      await this.redisPool.release(client);
    }
  }

  /**
   * Get seat occupancy for a specific zone and row
   */
  async getSeatOccupancy(zone: number, row: number): Promise<{
    occupied: number;
    total: number;
    available: number;
  }> {
    if (zone < 1 || zone > ZONES || row < 1 || row > ROWS_PER_ZONE) {
      throw new Error('Invalid zone or row');
    }
    
    const seatKey = `seats:${EVENT_ID}:${zone}:${row}`;
    const client = await this.redisPool.acquire() as Redis;
    try {
      // Get the bitmap and count set bits
      const occupiedCount = await client.bitcount(seatKey);
      return {
        occupied: occupiedCount,
        total: this.seatsPerRow,
        available: this.seatsPerRow - occupiedCount
      };
    } finally {
      await this.redisPool.release(client);
    }
  }

  /**
   * Check if all seats are unavailable across all zones and rows
   */
  async checkAllSeatsUnavailable(): Promise<{
    allUnavailable: boolean;
    totalSeats: number;
    occupiedSeats: number;
    availableSeats: number;
    zonesChecked: number;
    rowsChecked: number;
  }> {
    const client = await this.redisPool.acquire() as Redis;
    try {
      let totalOccupied = 0;
      const totalSeats = ZONES * ROWS_PER_ZONE * SEATS_PER_ROW;
      
      // Use pipeline for better performance when checking many keys
      const pipeline = client.pipeline();
      
      // Queue all bitcount operations
      for (let zone = 1; zone <= ZONES; zone++) {
        for (let row = 1; row <= ROWS_PER_ZONE; row++) {
          const seatKey = `seats:${EVENT_ID}:${zone}:${row}`;
          pipeline.bitcount(seatKey);
        }
      }
      
      // Execute all bitcount operations
      const results = await pipeline.exec();
      
      // Sum up all occupied seats
      if (results) {
        for (const result of results) {
          if (result && result[0] === null) { // No error
            totalOccupied += (result[1] as number) || 0;
          }
        }
      }
      
      const availableSeats = totalSeats - totalOccupied;
      
      return {
        allUnavailable: availableSeats === 0,
        totalSeats,
        occupiedSeats: totalOccupied,
        availableSeats,
        zonesChecked: ZONES,
        rowsChecked: ZONES * ROWS_PER_ZONE
      };
    } finally {
      await this.redisPool.release(client);
    }
  }
}
