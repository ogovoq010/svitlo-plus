import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, RefreshControl, SafeAreaView, StatusBar } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSchedule } from './src/hooks/useSchedule';
import { isLightOff, formatTime } from './src/utils/helpers';

const QUEUES = ['1.1', '1.2', '2.1', '2.2', '3.1', '3.2', '4.1', '4.2', '5.1', '5.2', '6.1', '6.2'];

export default function App() {
  const { data, loading, refresh, lastUpdated } = useSchedule();
  const [myQueue, setMyQueue] = useState<string>('1.1');

  // Завантажуємо обрану чергу при старті
  useEffect(() => {
    AsyncStorage.getItem('my_queue').then(q => { if (q) setMyQueue(q); });
  }, []);

  // Зберігаємо чергу при зміні
  const selectQueue = async (q: string) => {
    setMyQueue(q);
    await AsyncStorage.setItem('my_queue', q);
  };

  const currentSchedule = data?.queues[myQueue];
  const isOff = isLightOff(currentSchedule);

  // Кольори
  const bgColor = isOff ? '#2d0a0a' : '#0a2d15'; // Темно-червоний або темно-зелений
  const circleColor = isOff ? '#ff4444' : '#00cc66';
  const statusText = isOff ? 'СВІТЛА НЕМАЄ' : 'СВІТЛО Є';

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: bgColor }]}>
      <StatusBar barStyle="light-content" />

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} tintColor="#fff" />}
      >
        <Text style={styles.headerDate}>
          {data?.scheduleDate || 'Дані відсутні'}
        </Text>

        {/* --- ГОЛОВНЕ КОЛО --- */}
        <View style={[styles.circle, { borderColor: circleColor }]}>
          <Text style={styles.statusTitle}>{statusText}</Text>
          {data?.isEmergency && <Text style={styles.emergencyText}>АВАРІЙНІ!</Text>}
          {data?.isUpdated && <Text style={styles.updatedText}>ОНОВЛЕНИЙ!</Text>}
        </View>

        {/* --- ВИБІР ЧЕРГИ --- */}
        <Text style={styles.sectionTitle}>Обери чергу:</Text>
        <View style={styles.queueGrid}>
          {QUEUES.map(q => (
            <TouchableOpacity
              key={q}
              style={[styles.qBtn, myQueue === q && styles.qBtnActive]}
              onPress={() => selectQueue(q)}
            >
              <Text style={[styles.qText, myQueue === q && styles.qTextActive]}>{q}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* --- ГРАФІК --- */}
        <View style={styles.scheduleCard}>
          <Text style={styles.cardTitle}>Графік відключень ({myQueue}):</Text>

          {currentSchedule && currentSchedule.length > 0 ? (
            currentSchedule.map((range, idx) => (
              <View key={idx} style={styles.timeRow}>
                <Text style={styles.timeText}>
                  {formatTime(range.start)} — {formatTime(range.end)}
                </Text>
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>Графік чистий (або не завантажився)</Text>
          )}
        </View>

        <Text style={styles.footer}>Оновлено: {lastUpdated || '-'}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { alignItems: 'center', paddingVertical: 20 },
  headerDate: { color: '#fff', fontSize: 18, opacity: 0.7, marginBottom: 30, marginTop: 20 },

  circle: {
    width: 260, height: 260, borderRadius: 130,
    borderWidth: 8, justifyContent: 'center', alignItems: 'center',
    marginBottom: 40, backgroundColor: 'rgba(0,0,0,0.2)'
  },
  statusTitle: { color: '#fff', fontSize: 36, fontWeight: '900', textAlign: 'center' },
  emergencyText: { color: '#ffcc00', fontSize: 20, fontWeight: 'bold', marginTop: 10 },
  updatedText: { color: '#00ccff', fontSize: 18, fontWeight: 'bold', marginTop: 5 },

  sectionTitle: { color: '#ccc', marginBottom: 10, alignSelf: 'flex-start', marginLeft: 20 },
  queueGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: 8, marginBottom: 30, paddingHorizontal: 10 },
  qBtn: { width: 50, height: 40, justifyContent: 'center', alignItems: 'center', borderRadius: 8, backgroundColor: 'rgba(255,255,255,0.1)' },
  qBtnActive: { backgroundColor: '#fff' },
  qText: { color: '#fff', fontWeight: 'bold' },
  qTextActive: { color: '#000' },

  scheduleCard: { width: '90%', backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 16, padding: 20 },
  cardTitle: { color: '#aaa', marginBottom: 15, textTransform: 'uppercase', fontSize: 12, fontWeight: 'bold' },
  timeRow: { borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.1)', paddingVertical: 12 },
  timeText: { color: '#fff', fontSize: 24, fontWeight: '600', letterSpacing: 1 },
  emptyText: { color: '#888', fontStyle: 'italic', marginTop: 10 },
  footer: { color: '#555', marginTop: 30, fontSize: 12 }
});