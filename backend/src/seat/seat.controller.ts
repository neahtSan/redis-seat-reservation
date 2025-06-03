/* eslint-disable prettier/prettier */
import { Controller, Post, Body, Res, HttpStatus, Get, Param } from '@nestjs/common';
import { Response } from 'express';
import { SeatService } from './seat.service';

@Controller()
export class SeatController {
  constructor(private readonly seatService: SeatService) {}

  @Post('reserve')
  async reserveSeats(
    @Body('zone') zone: number,
    @Body('row') row: number,
    @Body('count') count: number,
    @Res() res: Response
  ) {
    // Validate input - updated for new configuration: 50 zones, 20 rows per zone, 65 seats per row
    if (!count || count < 1 || count > 5 || !zone || zone < 1 || zone > 50 || !row || row < 1 || row > 20) {
      // Return CONFLICT for invalid input to ensure only SUCCESS/CONFLICT outcomes
      return res.status(HttpStatus.CONFLICT).json({ 
        error: 'Invalid input: zone (1-50), row (1-20), count (1-5) required.',
        zone,
        row,
        count
      });
    }
    
    try {
      const startIndex = await this.seatService.reserveContiguousSeats(zone, row, count);
      if (startIndex >= 0) {
        // Success: seats allocated
        return res.status(HttpStatus.OK).json({
          zone,
          row,
          startIndex,
          seatsCount: count
        });
      } else {
        // Failure: no suitable block found
        return res.status(HttpStatus.CONFLICT).json({ 
          error: 'No suitable block of seats available.',
          zone,
          row,
          count
        });
      }
    } catch (err) {
      // Any error (including Redis connection issues) returns CONFLICT
      const errorMessage = err instanceof Error ? err.message : 'Service unavailable';
      return res.status(HttpStatus.CONFLICT).json({ 
        error: errorMessage,
        zone,
        row,
        count
      });
    }
  }

  @Post('initialize')
  async initializeSeats(@Res() res: Response) {
    try {
      await this.seatService.initializeAllSeatTables();
      return res.status(HttpStatus.OK).json({ 
        message: 'All seat tables initialized successfully',
        totalKeys: 50 * 20, // 1,000 Redis keys
        totalSeats: 50 * 20 * 65 // 65,000 seats
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Initialization failed';
      return res.status(HttpStatus.CONFLICT).json({ error: errorMessage });
    }
  }

  @Get('stats')
  async getRedisStats(@Res() res: Response) {
    try {
      const stats = await this.seatService.getRedisStats();
      return res.status(HttpStatus.OK).json(stats);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get stats';
      return res.status(HttpStatus.CONFLICT).json({ error: errorMessage });
    }
  }

  @Post('clear')
  async clearSeatData(@Res() res: Response) {
    try {
      await this.seatService.clearAllSeatData();
      return res.status(HttpStatus.OK).json({ message: 'All seat data cleared successfully' });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to clear data';
      return res.status(HttpStatus.CONFLICT).json({ error: errorMessage });
    }
  }

  @Get('occupancy/:zone/:row')
  async getSeatOccupancy(
    @Param('zone') zone: string,
    @Param('row') row: string,
    @Res() res: Response
  ) {
    const zoneNum = parseInt(zone, 10);
    const rowNum = parseInt(row, 10);
    
    // Validate input
    if (isNaN(zoneNum) || isNaN(rowNum) || zoneNum < 1 || zoneNum > 50 || rowNum < 1 || rowNum > 20) {
      return res.status(HttpStatus.CONFLICT).json({ 
        error: 'Invalid zone or row',
        zone: zoneNum,
        row: rowNum,
        occupied: 0,
        total: 65
      });
    }

    try {
      const occupancy = await this.seatService.getSeatOccupancy(zoneNum, rowNum);
      return res.status(HttpStatus.OK).json({
        zone: zoneNum,
        row: rowNum,
        occupied: occupancy.occupied,
        total: occupancy.total,
        available: occupancy.available
      });
    } catch {
      return res.status(HttpStatus.CONFLICT).json({ 
        error: 'Failed to get occupancy',
        zone: zoneNum,
        row: rowNum,
        occupied: 0,
        total: 65
      });
    }
  }

  @Get('availability/check-all')
  async checkAllSeatsAvailability(@Res() res: Response) {
    try {
      const availability = await this.seatService.checkAllSeatsUnavailable();
      return res.status(HttpStatus.OK).json({
        allUnavailable: availability.allUnavailable,
        totalSeats: availability.totalSeats,
        occupiedSeats: availability.occupiedSeats,
        availableSeats: availability.availableSeats,
        zonesChecked: availability.zonesChecked,
        rowsChecked: availability.rowsChecked,
        occupancyPercentage: ((availability.occupiedSeats / availability.totalSeats) * 100).toFixed(2)
      });
    } catch {
      return res.status(HttpStatus.CONFLICT).json({ 
        error: 'Failed to check seat availability',
        allUnavailable: false,
        totalSeats: 50 * 20 * 65, // 65,000 seats
        occupiedSeats: 0,
        availableSeats: 50 * 20 * 65,
        zonesChecked: 50,
        rowsChecked: 50 * 20
      });
    }
  }
}
