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

    # Структура за замовчуванням (щоб файл завжди існував)
    final_data = {
        "updatedAt": datetime.now(KYIV_TZ).isoformat(),
        "scheduleDate": datetime.now(KYIV_TZ).strftime("%Y-%m-%d"),
        "isEmergency": False,
        "isUpdated": False,
        "queues": {},
        "debugMessage": "Графік не знайдено"
    }

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(CHANNEL_URL, headers=headers)
        html = resp.text

        # Чистимо текст від HTML тегів для простішого пошуку
        # Шукаємо блоки повідомлень
        msgs = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)

        found = False
        for raw_msg in reversed(msgs):
            # Перетворюємо <br> в ентери, видаляємо теги
            text = re.sub(r'<br\s*/>', '\n', raw_msg)
            text = re.sub(r'<[^>]+>', '', text)

            # Шукаємо "черга" і двокрапку - це маркер графіку
            if "черга" in text.lower() and ":" in text:
                print("Found schedule message!")

                temp_queues = {}
                lines = text.split('\n')

                for line in lines:
                    # Шукаємо "1.1" або "1 черга"
                    # Цей regex ловить "1.1", "1.2" і т.д.
                    q_match = re.search(r'(\d\.\d)', line)
                    if q_match:
                        q_id = q_match.group(1)

                        # Шукаємо час 00:00 - 00:00 (враховуємо різні тире)
                        times = re.findall(r'(\d{1,2}:\d{2})\s*[–\-\—]\s*(\d{1,2}:\d{2})', line)

                        ranges = []
                        for t_start, t_end in times:
                            ranges.append({
                                "start": parse_time(t_start),
                                "end": parse_time(t_end)
                            })

                        if ranges:
                            temp_queues[q_id] = ranges

                if temp_queues:
                    final_data["queues"] = temp_queues
                    final_data["isEmergency"] = "аварійні" in text.lower()
                    final_data["isUpdated"] = "оновлений" in text.lower()
                    final_data["debugMessage"] = "Успішно оновлено"
                    found = True
                    break

        if not found:
            print("Warning: Pattern not found in recent messages")

    except Exception as e:
        print(f"Error: {e}")
        final_data["debugMessage"] = f"Error: {str(e)}"

    # ГОЛОВНЕ: Записуємо файл у будь-якому випадку!
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("schedule.json created.")


if __name__ == "__main__":
    run()