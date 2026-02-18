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
    if '24:00' in t_str:
        return 1440
    try:
        h, m = map(int, t_str.split(':'))
        if not (0 <= h <= 24 and 0 <= m <= 59):
            return 0  # Ігноруємо некоректний час
        return h * 60 + m
    except Exception:
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
            current_date = datetime.now(KYIV_TZ)
            year = current_date.year

            # Спробуємо створити дату
            try:
                schedule_date = datetime(year, month, day)
                # Якщо місяць січень, а зараз грудень - це наступний рік
                if month == 1 and current_date.month == 12:
                    year += 1
                # Якщо дата виглядає як минуле (наприклад, парсимо 18 лютого, а сьогодні 19 лютого),
                # то залишаємо як є (можливо це архів), або коригуємо логіку за потребою.
                # Тут беремо поточний рік за замовчуванням.

                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

    return datetime.now(KYIV_TZ).strftime("%Y-%m-%d")


def run():
    print(f"Checking {CHANNEL_URL}...")

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

        # Розбиваємо на повідомлення
        msgs = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', html, re.DOTALL)

        found = False
        # Проходимо з кінця (найсвіжіші повідомлення)
        for raw_msg in reversed(msgs):
            # Чистка HTML
            text = re.sub(r'<br\s*/>', '\n', raw_msg)
            text = re.sub(r'<[^>]+>', '', text)
            text_lower = text.lower()

            # --- ГОЛОВНА ЗМІНА: Критерії пошуку ---
            # Шукаємо або слово "графік", або "гпв", або "години", або "черга"
            is_likely_schedule = any(kw in text_lower for kw in ['графік', 'гпв', 'години', 'черга', 'вимкнень'])

            # Але найголовніше - чи є там рядки типу "1.1:"
            has_queue_pattern = re.search(r'\d\.\d\s*:', text)

            if is_likely_schedule and has_queue_pattern:
                print("Found potential schedule message...")

                # 1. Дата
                schedule_date = extract_date_from_text(text)

                # 2. Статусы
                is_updated = "оновлений" in text_lower
                is_emergency = "аварійні" in text_lower

                # 3. Парсинг черг
                temp_queues = {}
                lines = text.split('\n')

                for line in lines:
                    line = line.strip()
                    # Шукаємо початок рядка типу "1.1:" або "1.1."
                    q_match = re.search(r'(\d\.\d)\s*[:.]', line)
                    if q_match:
                        q_id = q_match.group(1)

                        # Шукаємо час. Підтримуємо різні тире: -, –, —
                        # Regex ловить пари: (01:30) (тире) (03:30)
                        times = re.findall(r'(\d{1,2}:\d{2})\s*[–\-\—]\s*(\d{1,2}:\d{2})', line)

                        ranges = []
                        for t_start, t_end in times:
                            start_min = parse_time(t_start)
                            end_min = parse_time(t_end)

                            ranges.append({
                                "start": start_min,
                                "end": end_min
                            })

                        if ranges:
                            temp_queues[q_id] = ranges

                # Якщо ми знайшли хоча б одну чергу з годинами - це точно графік
                if temp_queues:
                    final_data["queues"] = temp_queues
                    final_data["scheduleDate"] = schedule_date
                    final_data["isEmergency"] = is_emergency
                    final_data["isUpdated"] = is_updated
                    final_data["debugMessage"] = f"OK. Date: {schedule_date}. Updated: {is_updated}"
                    found = True
                    print(f"Successfully parsed schedule for {schedule_date}")
                    break  # Зупиняємося на першому (найсвіжішому) знайденому графіку

        if not found:
            print("Warning: No schedule format found in recent messages")

    except Exception as e:
        print(f"Error: {e}")
        final_data["debugMessage"] = f"Error: {str(e)}"

    # Збереження
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"✓ {OUTPUT_FILE} saved.")


if __name__ == "__main__":
    run()