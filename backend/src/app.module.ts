import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { SeatController } from './seat/seat.controller';
import { SeatService } from './seat/seat.service';

@Module({
  imports: [],
  controllers: [AppController, SeatController],
  providers: [AppService, SeatService],
})
export class AppModule {}
