// src/utils/helpers.ts
import { TimeRange } from '../types';

// Отримуємо поточні хвилини (наприклад, 10:30 -> 630)
export const getCurrentMinutes = (): number => {
  const now = new Date();
  return now.getHours() * 60 + now.getMinutes();
};

// Перевіряємо, чи ми зараз в "червоній зоні"
export const isLightOff = (ranges: TimeRange[] | undefined): boolean => {
  if (!ranges || ranges.length === 0) return false;

  const current = getCurrentMinutes();
  // Перевіряємо кожен проміжок
  return ranges.some(range => current >= range.start && current < range.end);
};

// Форматуємо хвилини назад у час (630 -> "10:30")
export const formatTime = (minutes: number): string => {
  const h = Math.floor(minutes / 60).toString().padStart(2, '0');
  const m = (minutes % 60).toString().padStart(2, '0');
  return `${h}:${m}`;
};