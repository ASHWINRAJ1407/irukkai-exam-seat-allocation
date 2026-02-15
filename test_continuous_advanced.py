from utils.timetable_generator import generate_timetable
from datetime import date, timedelta

print("="*70)
print("TEST 1: Two departments with continuous dates")
print("="*70)

rows = [
    {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Science'},
    {'department_code': 'D1', 'subject_code': 'S3', 'subject_name': 'English'},
    {'department_code': 'D2', 'subject_code': 'T1', 'subject_name': 'Math'},
    {'department_code': 'D2', 'subject_code': 'T2', 'subject_name': 'Science'},
]

start = date(2024, 5, 1)
schedule, _ = generate_timetable(rows, start.strftime('%d/%m/%Y'), [])

for dept in ['D1', 'D2']:
    dates = []
    for d, d2, subj, name in sorted(schedule):
        if d2 == dept:
            dates.append(d)
    dates_unique = sorted(set(dates))
    is_continuous = dates_unique == sorted(dates_unique) and (dates_unique[-1] - dates_unique[0]).days == len(dates_unique) - 1
    print(f"\n{dept}: {len(dates)} subjects in {len(dates_unique)} dates")
    print(f"  Dates: {dates_unique}")
    print(f"  Continuous? {is_continuous}")

print("\n" + "="*70)
print("TEST 2: With exclusion dates (May 2, May 4)")
print("="*70)

excluded = ['02/05/2024', '04/05/2024']
schedule2, _ = generate_timetable(rows, start.strftime('%d/%m/%Y'), excluded)

excluded_set = {date(2024, 5, 2), date(2024, 5, 4)}

for dept in ['D1', 'D2']:
    dates = []
    for d, d2, subj, name in sorted(schedule2):
        if d2 == dept:
            dates.append(d)
            if d in excluded_set:
                print(f"  ERROR: {d} is excluded!")
    dates_unique = sorted(set(dates))
    
    # Check if continuous (excluding the excluded dates)
    print(f"\n{dept}: {len(dates)} subjects in {len(dates_unique)} dates")
    print(f"  Dates: {dates_unique}")
    
    # For continuous check, filter excluded dates
    dates_available = [d for d in dates_unique if d not in excluded_set]
    
    # Check if the non-excluded dates form a continuous range
    if dates_available:
        is_continuous = (dates_available[-1] - dates_available[0]).days == len(dates_available) - 1
        print(f"  Continuous (excluding excluded dates)? {is_continuous}")
