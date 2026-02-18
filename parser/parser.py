import requests
import json
import re
from datetime import datetime
import pytz  # GitHub сервери в UTC, нам треба Київ

# Налаштування
CHANNEL_URL = 'https://t.me/s/Cherkasyenergy'
OUTPUT_FILE = 'schedule.json'
KYIV_TZ = pytz.timezone('Europe/Kiev')


def parse_time(t_str):
    # Конвертує "10:30" -> 630 хвилин. "24:00" -> 1440.
    if '24:00' in t_str: return 1440
    try:
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
    except:
        return 0


def run():
    print(f"Checking {CHANNEL_URL}...")
    try:
        # Емулюємо браузер, щоб телеграм не блокував
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(CHANNEL_URL, headers=headers)
        html = resp.text
    except Exception as e:
        print(f"Error: {e}")
        return

    # Шукаємо блоки повідомлень
    msgs = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)

    final_data = None

    # Читаємо з кінця (найсвіжіші)
    for raw_msg in reversed(msgs):
        # Чистимо HTML теги (<br>, <b> і т.д.)
        text = re.sub(r'<br\s*/>', '\n', raw_msg)
        text = re.sub(r'<[^>]+>', '', text)

        # Шукаємо ключові слова
        if "черга" in text.lower() and ":" in text:
            print("Found potential schedule message...")

            # Структура JSON
            current_data = {
                "updatedAt": datetime.now(KYIV_TZ).isoformat(),
                "scheduleDate": datetime.now(KYIV_TZ).strftime("%Y-%m-%d"),
                "isEmergency": "аварійні" in text.lower(),
                "isUpdated": "оновлений" in text.lower(),
                "queues": {}
            }

            # Парсимо рядки типу "1.1: 07:00 – 10:30"
            # Regex шукає: початок рядка або нову лінію, потім Цифра.Цифра, потім двокрапку
            lines = text.split('\n')
            for line in lines:
                # Шукаємо чергу (1.1, 2.1...)
                q_match = re.search(r'(\d\.\d)[:.]', line)
                if q_match:
                    q_id = q_match.group(1)

                    # Шукаємо всі часові пари 00:00 - 00:00
                    # Тире може бути різним (–, -, —)
                    times = re.findall(r'(\d{1,2}:\d{2})\s*[–\-\—]\s*(\d{1,2}:\d{2})', line)

                    ranges = []
                    for t_start, t_end in times:
                        ranges.append({
                            "start": parse_time(t_start),
                            "end": parse_time(t_end)
                        })

                    if ranges:
                        current_data["queues"][q_id] = ranges

            # Якщо ми знайшли хоча б одну чергу з даними - це воно!
            if current_data["queues"]:
                final_data = current_data
                break

    if final_data:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        print("SUCCESS: schedule.json created!")
    else:
        print("FAIL: No schedule found in recent messages.")


if __name__ == "__main__":
    run()