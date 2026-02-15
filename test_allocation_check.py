from utils.timetable_generator import generate_timetable
from datetime import date, timedelta

print("Testing with exclusion dates (May 2, May 4)")

rows = [
    {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Science'},
    {'department_code': 'D1', 'subject_code': 'S3', 'subject_name': 'English'},
    {'department_code': 'D2', 'subject_code': 'T1', 'subject_name': 'Math'},
    {'department_code': 'D2', 'subject_code': 'T2', 'subject_name': 'Science'},
]

start = date(2024, 5, 1)
excluded = ['02/05/2024', '04/05/2024']
schedule, _ = generate_timetable(rows, start.strftime('%d/%m/%Y'), excluded)

print(f"\nExcluded dates: {excluded}")
print(f"Available dates: May 1, 3, 5, 6, 7, ...\n")

excluded_set = {date(2024, 5, 2), date(2024, 5, 4)}

for dept in ['D1', 'D2']:
    print(f"\n{dept} Schedule:")
    dates = []
    for d, d2, subj, name in sorted(schedule):
        if d2 == dept:
            print(f"  {d}: {name}")
            dates.append(d)
    
    # Check: are the allocated dates the FIRST N available dates?
    available_dates = []
    check_date = start
    while len(available_dates) < len(dates):
        if check_date not in excluded_set:
            available_dates.append(check_date)
        check_date += timedelta(days=1)
    
    dates_unique = sorted(set(dates))
    print(f"  Allocated dates: {dates_unique}")
    print(f"  Should be: {available_dates}")
    print(f"  Match? {dates_unique == available_dates}")
