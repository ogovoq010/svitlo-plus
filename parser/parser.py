import requests
import json
import re
from datetime import datetime
import pytz

# Налаштування
CHANNEL_URL = 'https://t.me/s/Cherkasyenergy'
OUTPUT_FILE = 'schedule.json'
KYIV_TZ = pytz.timezone('Europe/Kiev')

# Словник місяців українською
MONTHS_UK = {
    'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4, 'травня': 5, 'червня': 6,
    'липня': 7, 'серпня': 8, 'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
}


def parse_time(t_str):
    """Парсить час у хвилини від початку дня"""
    t_str = t_str.strip()
    if t_str == '24:00':
        return 1440
    try:
        h, m = map(int, t_str.split(':'))
        if not (0 <= h <= 24 and 0 <= m <= 59):
            raise ValueError(f"Invalid time: {t_str}")
        return h * 60 + m
    except ValueError as e:
        print(f"Warning: parse_time error: {e}")
        return 0


def extract_date_from_text(text):
    """Витягує дату з тексту типу '18 лютого' або 'на 18 лютого'"""
    # Шукаємо патерн: число + місяць
    pattern = r'(?:на\s+)?(\d{1,2})\s+(' + '|'.join(MONTHS_UK.keys()) + r')'
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()
        month = MONTHS_UK.get(month_name)

        if month:
            # Визначаємо рік (поточний або наступний)
            current_date = datetime.now(KYIV_TZ)
            year = current_date.year

            # Якщо дата в минулому, беремо наступний рік
            try:
                schedule_date = datetime(year, month, day)
                if schedule_date.replace(tzinfo=KYIV_TZ) < current_date:
                    year += 1
                    schedule_date = datetime(year, month, day)

                return schedule_date.strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Якщо не знайшли, повертаємо поточну дату
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d")


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
        resp = requests.get(CHANNEL_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        html = resp.text

        # Шукаємо блоки повідомлень
        msgs = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)

        found = False
        for raw_msg in reversed(msgs):
            # Перетворюємо <br> в ентери, видаляємо теги
            text = re.sub(r'<br\s*/>', '\n', raw_msg)
            text = re.sub(r'<[^>]+>', '', text)

            # Шукаємо "черга" і ":" - це маркер графіку
            if "черга" in text.lower() and ":" in text:
                print("Found schedule message!")

                # Витягуємо дату з тексту
                schedule_date = extract_date_from_text(text)
                print(f"Extracted date: {schedule_date}")

                # Визначаємо чи це оновлений графік
                is_updated = "оновлений" in text.lower()
                is_emergency = "аварійні" in text.lower()

                temp_queues = {}
                lines = text.split('\n')

                for line in lines:
                    # Шукаємо формат "1.1:" або "1.2:"
                    q_match = re.search(r'(\d\.\d)\s*:', line)
                    if q_match:
                        q_id = q_match.group(1)

                        # Шукаємо всі часові діапазони на цьому рядку
                        # Підтримуємо різні види тире: -, –, —
                        times = re.findall(r'(\d{1,2}:\d{2})\s*[–\-—]\s*(\d{1,2}:\d{2})', line)

                        ranges = []
                        for t_start, t_end in times:
                            start_min = parse_time(t_start)
                            end_min = parse_time(t_end)

                            # Валідація: час має бути логічним
                            if start_min is not None and end_min is not None:
                                ranges.append({
                                    "start": start_min,
                                    "end": end_min
                                })

                        if ranges:
                            temp_queues[q_id] = ranges
                            print(f"  Queue {q_id}: {len(ranges)} ranges")

                if temp_queues:
                    final_data["queues"] = temp_queues
                    final_data["scheduleDate"] = schedule_date
                    final_data["isEmergency"] = is_emergency
                    final_data["isUpdated"] = is_updated
                    final_data["debugMessage"] = f"Успішно знайдено {'оновлений ' if is_updated else ''}графік на {schedule_date}"
                    found = True
                    break

        if not found:
            print("Warning: Schedule pattern not found in recent messages")
            final_data["debugMessage"] = "Графік не знайдено в останніх повідомленнях"

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        final_data["debugMessage"] = f"Помилка мережі: {str(e)}"
    except Exception as e:
        print(f"Error: {e}")
        final_data["debugMessage"] = f"Помилка: {str(e)}"

    # ГОЛОВНЕ: Записуємо файл у будь-якому випадку!
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        print(f"✓ {OUTPUT_FILE} saved successfully")
        print(f"  Queues found: {len(final_data['queues'])}")
        print(f"  Is updated: {final_data['isUpdated']}")
        print(f"  Date: {final_data['scheduleDate']}")
    except Exception as e:
        print(f"Error writing file: {e}")


if __name__ == "__main__":
    run()
