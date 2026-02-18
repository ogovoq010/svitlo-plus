import requests
import json
import re
from datetime import datetime
import pytz

# Налаштування
CHANNEL_URL = 'https://t.me/s/Cherkasyenergy'
OUTPUT_FILE = 'schedule.json'
KYIV_TZ = pytz.timezone('Europe/Kiev')


def parse_time(t_str):
    if '24:00' in t_str: return 1440
    try:
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
    except:
        return 0


def run():
    print(f"Checking {CHANNEL_URL}...")

    # Структура за замовчуванням (якщо нічого не знайдемо)
    final_data = {
        "updatedAt": datetime.now(KYIV_TZ).isoformat(),
        "scheduleDate": datetime.now(KYIV_TZ).strftime("%Y-%m-%d"),
        "isEmergency": False,
        "isUpdated": False,
        "queues": {},  # Пустий об'єкт
        "debugMessage": "Графік не знайдено або помилка парсингу"
    }

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(CHANNEL_URL, headers=headers)
        html = resp.text

        # Шукаємо всі повідомлення
        msgs = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)
        print(f"Found {len(msgs)} messages.")

        for raw_msg in reversed(msgs):
            # Чистимо текст
            text = re.sub(r'<br\s*/>', '\n', raw_msg)
            text = re.sub(r'<[^>]+>', '', text)

            # Спрощений пошук: якщо є цифри "1.1" або "1 черга" і двокрапка
            if (re.search(r'\d\.\d', text) or "черга" in text.lower()) and ":" in text:
                print("Processing potential message...")

                temp_queues = {}
                lines = text.split('\n')

                for line in lines:
                    # Шукаємо "1.1" або "1.2" на початку
                    q_match = re.search(r'(\d\.\d)', line)
                    if q_match:
                        q_id = q_match.group(1)
                        # Шукаємо час 00:00 - 00:00
                        times = re.findall(r'(\d{1,2}:\d{2})\s*[–\-\—]\s*(\d{1,2}:\d{2})', line)

                        ranges = []
                        for t_start, t_end in times:
                            ranges.append({
                                "start": parse_time(t_start),
                                "end": parse_time(t_end)
                            })

                        if ranges:
                            temp_queues[q_id] = ranges

                # Якщо знайшли хоча б щось
                if temp_queues:
                    final_data["queues"] = temp_queues
                    final_data["isEmergency"] = "аварійні" in text.lower()
                    final_data["isUpdated"] = "оновлений" in text.lower()
                    final_data["debugMessage"] = "Успішно оновлено"
                    print("SUCCESS: Queue data found!")
                    break

    except Exception as e:
        print(f"Global Error: {e}")
        final_data["debugMessage"] = f"Error: {str(e)}"

    # ЗАВЖДИ зберігаємо файл, щоб GitHub Action не падав
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("schedule.json saved (even if empty).")


if __name__ == "__main__":
    run()