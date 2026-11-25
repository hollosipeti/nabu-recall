"""Calendar extensions for Nabu Recall 2.0.0; no HA dependency."""
from datetime import date, datetime, time, timedelta
import re
import unicodedata

MONTHS = ('január február március április május június július augusztus szeptember október november december').split()

def iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('ISO dátum szükséges (ÉÉÉÉ-HH-NN)')
    return date.fromisoformat(value)

def midnight(d, now):
    return datetime.combine(d, time.min, now.tzinfo)

def range_window(start_date, end_date, now):
    first, last = iso_day(start_date), iso_day(end_date)
    if last <= first:
        raise ValueError('A kizáró záródátumnak a kezdődátum után kell lennie')
    return midnight(first, now), midnight(last, now)

def hungarian_month_day(value, now):
    match = re.fullmatch(r'(?:(\d{4})\.\s*)?('+'|'.join(MONTHS)+r')\s+(\d{1,2})(?:\.|-?(?:án|én|jén|je))?', value.casefold().strip())
    if not match:
        return None
    year, month, day = match.groups()
    month, day = MONTHS.index(month)+1, int(day)
    if year:
        return date(int(year), month, day)
    for y in range(now.year, now.year+9):
        try:
            candidate = date(y, month, day)
        except ValueError:
            continue
        if candidate >= now.date():
            return candidate
    raise ValueError('Érvénytelen dátum')

def all_day_bounds(day, end_date, now, resolve_day):
    first = hungarian_month_day(day, now) or resolve_day(day, now)
    if first < now.date():
        raise ValueError('A múltba nem hozható létre esemény')
    last = iso_day(end_date) if end_date is not None else first + timedelta(days=1)
    if last <= first:
        raise ValueError('Érvénytelen záródátum')
    return first, last

def normalize_title(value):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c)).split())

def title_matches(event, title):
    target = normalize_title(title)
    summary = normalize_title(str(event.get('summary', '')))
    return bool(target) and target in summary
