// src/types/index.ts

export interface TimeRange {
  start: number; // хвилини від початку доби (0..1440)
  end: number;
}

export interface ScheduleData {
  updatedAt: string;
  scheduleDate: string;
  isEmergency: boolean;
  isUpdated: boolean;
  queues: Record<string, TimeRange[]>; // "1.1": [{start: 600, end: 840}]
}