import requests
import json
import re
import os
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
    t_str = t_str.strip()
    if '24:00' in t_str: return 1440
    try:
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
    except:
        return 0


def extract_date_from_text(text):
    pattern = r'(?:на\s+)?(\d{1,2})\s+(' + '|'.join(MONTHS_UK.keys()) + r')'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month = MONTHS_UK.get(match.group(2).lower())
        if month:
            now = datetime.now(KYIV_TZ)
            year = now.year
            # Логіка зміни року
            if month == 1 and now.month == 12: year += 1
            return datetime(year, month, day).strftime("%Y-%m-%d")
    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d")


def run():
    print(f"Checking {CHANNEL_URL}...")

    # 1. Спробуємо завантажити старі дані, щоб не втратити їх
    old_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
        except:
            pass

    # Заготовка нових даних
    final_data = {
        "updatedAt": datetime.now(KYIV_TZ).isoformat(),
        "scheduleDate": datetime.now(KYIV_TZ).strftime("%Y-%m-%d"),
        "isEmergency": False,
        "isUpdated": False,
        "queues": {},
        "debugMessage": "Графік не знайдено (оновлено)"
    }

    # Якщо ми не знайдемо нічого нового, ми повернемо старі черги
    # (але дату оновлення змінимо, щоб знати, що бот працював)
    if old_data.get("queues"):
        final_data["queues"] = old_data["queues"]
        final_data["scheduleDate"] = old_data.get("scheduleDate", final_data["scheduleDate"])
        final_data["debugMessage"] = "Залишено старий графік (новий не знайдено)"

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(CHANNEL_URL, headers=headers, timeout=10)
        html = resp.text

        msgs = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)

        found = False
        scanned_snippets = []  # Для налагодження

        for raw_msg in reversed(msgs):
            text = re.sub(r'<br\s*/>', '\n', raw_msg)
            text = re.sub(r'<[^>]+>', '', text)

            # Зберігаємо початок кожного повідомлення для логу (перші 30 символів)
            scanned_snippets.append(text[:30].replace('\n', ' '))

            is_likely_schedule = any(kw in text.lower() for kw in ['графік', 'гпв', 'години', 'черга', 'вимкнень'])
            has_queue_pattern = re.search(r'\d\.\d\s*:', text)

            if is_likely_schedule and has_queue_pattern:
                schedule_date = extract_date_from_text(text)

                temp_queues = {}
                lines = text.split('\n')
                for line in lines:
                    q_match = re.search(r'(\d\.\d)\s*:', line)
                    if q_match:
                        q_id = q_match.group(1)
                        times = re.findall(r'(\d{1,2}:\d{2})\s*[–\-\—]\s*(\d{1,2}:\d{2})', line)
                        ranges = []
                        for t_start, t_end in times:
                            ranges.append({"start": parse_time(t_start), "end": parse_time(t_end)})
                        if ranges:
                            temp_queues[q_id] = ranges

                if temp_queues:
                    # Ура, знайшли новий графік! Перезаписуємо все.
                    final_data["queues"] = temp_queues
                    final_data["scheduleDate"] = schedule_date
                    final_data["isEmergency"] = "аварійні" in text.lower()
                    final_data["isUpdated"] = "оновлений" in text.lower()
                    final_data["debugMessage"] = f"OK. Found: {text[:20]}..."
                    found = True
                    break

        if not found:
            # Якщо не знайшли, додаємо лог, що саме ми бачили
            debug_info = " | ".join(scanned_snippets[-5:])  # Останні 5 повідомлень
            final_data["debugMessage"] = f"Not found. Scanned: {debug_info}"

    except Exception as e:
        final_data["debugMessage"] = f"Error: {str(e)}"

    # Запис
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("Done.")


if __name__ == "__main__":
    run()