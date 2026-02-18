// src/hooks/useSchedule.ts
import { useState, useEffect, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ScheduleData } from '../types';

// ТУТ БУДЕ ТВОЄ ПОСИЛАННЯ (поки що пусте)
const GITHUB_URL = 'https://raw.githubusercontent.com/USERNAME/REPO/main/schedule.json';

export const useSchedule = () => {
  const [data, setData] = useState<ScheduleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // 1. Спочатку пробуємо показати кеш (миттєво)
      const cached = await AsyncStorage.getItem('schedule_data');
      if (cached) {
        setData(JSON.parse(cached));
      }

      // 2. Пробуємо завантажити свіже
      // Додаємо ?t=... щоб обійти кешування GitHub
      const response = await fetch(`${GITHUB_URL}?t=${new Date().getTime()}`);
      if (response.ok) {
        const freshData: ScheduleData = await response.json();
        await AsyncStorage.setItem('schedule_data', JSON.stringify(freshData));
        setData(freshData);
        setLastUpdated(new Date().toLocaleTimeString());
      }
    } catch (error) {
      console.log('Offline mode or Fetch Error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Оновлювати кожну хвилину локально
    const interval = setInterval(loadData, 60000);
    return () => clearInterval(interval);
  }, [loadData]);

  return { data, loading, lastUpdated, refresh: loadData };
};