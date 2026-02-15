from utils.timetable_generator import generate_timetable
from datetime import date

print('\nEDGE CASE TEST 1: start_date after end_date')
rows = [
    {'department_code': 'CS', 'subject_code': 'A1', 'subject_name': 'Math'},
]
start = date(2024,5,5)
end = date(2024,5,1)
try:
    schedule, _, warning = generate_timetable(rows, start.strftime('%d/%m/%Y'), [], {'__end_date__': end.strftime('%d/%m/%Y')})
    print('Schedule:', schedule)
    print('Warning:', warning)
except Exception as e:
    print('Exception:', e)

print('\nEDGE CASE TEST 2: too many exclusions (no available dates)')
rows2 = [
    {'department_code': 'CS', 'subject_code': 'A1', 'subject_name': 'Math'},
    {'department_code': 'IT', 'subject_code': 'B1', 'subject_name': 'Physics'},
]
start2 = date(2024,5,1)
end2 = date(2024,5,3)
exclusions = ['01/05/2024', '02/05/2024', '03/05/2024']
schedule2, _, warning2 = generate_timetable(rows2, start2.strftime('%d/%m/%Y'), exclusions, {'__end_date__': end2.strftime('%d/%m/%Y')})
print('Schedule:', schedule2)
print('Warning:', warning2)

print('\nEDGE CASE TEST 3: heavy shared subject names requiring shuffling')
rows3 = []
for d in ['D1','D2','D3','D4']:
    rows3.append({'department_code': d, 'subject_code': 'S1', 'subject_name': 'Math'})
    rows3.append({'department_code': d, 'subject_code': 'S2', 'subject_name': 'Physics'})
start3 = date(2024,5,1)
end3 = date(2024,5,6)
schedule3, _, warning3 = generate_timetable(rows3, start3.strftime('%d/%m/%Y'), [], {'__end_date__': end3.strftime('%d/%m/%Y')})
print('Warning:', warning3)
for s in sorted(schedule3):
    print(s)
