from utils.timetable_generator import generate_timetable
from datetime import date, timedelta

rows = [
    {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Science'},
    {'department_code': 'D1', 'subject_code': 'S3', 'subject_name': 'English'},
    {'department_code': 'D1', 'subject_code': 'S4', 'subject_name': 'History'},
]

start = date(2024, 5, 1)
schedule, _ = generate_timetable(rows, start.strftime('%d/%m/%Y'), [])

print('D1 has 4 subjects:')
dates = []
for d, dept, subj, name in sorted(schedule):
    if dept == 'D1':
        print(f'  {d}: {name}')
        dates.append(d)

print(f'\nDates: {dates}')
is_continuous = dates == sorted(dates) and (dates[-1] - dates[0]).days == len(dates) - 1
print(f'Continuous? {is_continuous}')
