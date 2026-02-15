from utils.timetable_generator import generate_timetable
from datetime import date

def print_schedule(schedule):
    for d, dept, subj, name in sorted(schedule):
        print(f"  {d}: {dept} - {name}")

print("\nTEST 1: Insufficient Date Range")
rows = [
    {'department_code': 'CSE', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'CSE', 'subject_code': 'S2', 'subject_name': 'Physics'},
    {'department_code': 'CSE', 'subject_code': 'S3', 'subject_name': 'Chemistry'},
    {'department_code': 'CSE', 'subject_code': 'S4', 'subject_name': 'Biology'},
    {'department_code': 'CSE', 'subject_code': 'S5', 'subject_name': 'English'},
    {'department_code': 'CSE', 'subject_code': 'S6', 'subject_name': 'CS'},
]
start = date(2024, 5, 1)
end = date(2024, 5, 5)  # Only 5 days, but 6 subjects
schedule, _, warning = generate_timetable(rows, start.strftime('%d/%m/%Y'), [], {'__end_date__': end.strftime('%d/%m/%Y')})
print("Warning:", warning)

print("\nTEST 2: Exclusion Dates")
rows2 = [
    {'department_code': 'IT', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'IT', 'subject_code': 'S2', 'subject_name': 'Physics'},
    {'department_code': 'IT', 'subject_code': 'S3', 'subject_name': 'Chemistry'},
]
start2 = date(2024, 5, 1)
end2 = date(2024, 5, 5)
exclusions = ['02/05/2024', '04/05/2024']
schedule2, _, warning2 = generate_timetable(rows2, start2.strftime('%d/%m/%Y'), exclusions, {'__end_date__': end2.strftime('%d/%m/%Y')})
print_schedule(schedule2)
print("Warning:", warning2)

print("\nTEST 3: Multiple Departments, Gap-Filling & Order Independence")
rows3 = [
    {'department_code': 'ECE', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'ECE', 'subject_code': 'S2', 'subject_name': 'Physics'},
    {'department_code': 'IT', 'subject_code': 'S3', 'subject_name': 'Math'},
    {'department_code': 'IT', 'subject_code': 'S4', 'subject_name': 'Biology'},
    {'department_code': 'CSE', 'subject_code': 'S5', 'subject_name': 'Math'},
    {'department_code': 'CSE', 'subject_code': 'S6', 'subject_name': 'English'},
]
start3 = date(2024, 5, 1)
end3 = date(2024, 5, 6)
schedule3, _, warning3 = generate_timetable(rows3, start3.strftime('%d/%m/%Y'), [], {'__end_date__': end3.strftime('%d/%m/%Y')})
print_schedule(schedule3)
print("Warning:", warning3)

print("\nTEST 4: Smart Shuffling (Subject Swap)")
rows4 = [
    {'department_code': 'CSE', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'CSE', 'subject_code': 'S2', 'subject_name': 'Physics'},
    {'department_code': 'IT', 'subject_code': 'S3', 'subject_name': 'Math'},
    {'department_code': 'IT', 'subject_code': 'S4', 'subject_name': 'Physics'},
]
start4 = date(2024, 5, 1)
end4 = date(2024, 5, 3)
schedule4, _, warning4 = generate_timetable(rows4, start4.strftime('%d/%m/%Y'), [], {'__end_date__': end4.strftime('%d/%m/%Y')})
print_schedule(schedule4)
print("Warning:", warning4)
