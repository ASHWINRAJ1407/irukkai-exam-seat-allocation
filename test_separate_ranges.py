from utils.timetable_generator import generate_timetable
from datetime import date, timedelta

print("="*80)
print("TEST: Continuous Dates Per Department (Each Has Own Range)")
print("="*80)

# Test Case: 3 departments with different subject counts
rows = [
    # D1: 4 subjects
    {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Science'},
    {'department_code': 'D1', 'subject_code': 'S3', 'subject_name': 'English'},
    {'department_code': 'D1', 'subject_code': 'S4', 'subject_name': 'History'},
    # D2: 3 subjects
    {'department_code': 'D2', 'subject_code': 'T1', 'subject_name': 'Math'},
    {'department_code': 'D2', 'subject_code': 'T2', 'subject_name': 'Science'},
    {'department_code': 'D2', 'subject_code': 'T3', 'subject_name': 'Hindi'},
    # D3: 2 subjects
    {'department_code': 'D3', 'subject_code': 'U1', 'subject_name': 'Math'},
    {'department_code': 'D3', 'subject_code': 'U2', 'subject_name': 'Art'},
]

start = date(2024, 5, 1)
excluded = ['02/05/2024', '04/05/2024']  # May 2, 4 excluded
schedule, _ = generate_timetable(rows, start.strftime('%d/%m/%Y'), excluded)

excluded_set = {date(2024, 5, 2), date(2024, 5, 4)}

# Print schedule
print(f"\nExcluded dates: {excluded}")
print(f"\nSchedule (sorted by date):")
for d, dept, subj, name in sorted(schedule):
    print(f"  {d}: {dept} - {name}")

# Validation
print("\n" + "="*80)
print("CONSTRAINT VERIFICATION")
print("="*80)

# Constraint 1: No exam on excluded dates
print("\n1. No exams on excluded dates:")
violations_excluded = []
for d, dept, subj, name in schedule:
    if d in excluded_set:
        violations_excluded.append(f"  ERROR: {d} ({dept} {name}) is on excluded date")

if violations_excluded:
    for v in violations_excluded:
        print(v)
    print("  [FAIL]")
else:
    print("  [PASS] - All exams respect exclusion dates")

# Constraint 2: No department appears twice on same date
print("\n2. No department appears twice on same date:")
dept_dates = {}
violations_dept = []
for d, dept, subj, name in schedule:
    if d not in dept_dates:
        dept_dates[d] = []
    dept_dates[d].append(dept)

for d, depts in dept_dates.items():
    if len(depts) != len(set(depts)):
        duplicates = [dept for dept in set(depts) if depts.count(dept) > 1]
        violations_dept.append(f"  ERROR: {d} has duplicate departments: {duplicates}")

if violations_dept:
    for v in violations_dept:
        print(v)
    print("  [FAIL]")
else:
    print("  [PASS] - No department appears twice on same date")

# Constraint 3: Max 2 departments per subject_name per date
print("\n3. Max 2 departments per subject_name on any date:")
name_dates = {}
violations_name = []
for d, dept, subj, name in schedule:
    key = (d, name)
    if key not in name_dates:
        name_dates[key] = []
    name_dates[key].append(dept)

for (d, name), depts in name_dates.items():
    if len(depts) > 2:
        violations_name.append(f"  ERROR: {d} {name} has {len(depts)} depts: {depts}")

if violations_name:
    for v in violations_name:
        print(v)
    print("  [FAIL]")
else:
    print("  [PASS] - Max 2 departments per subject_name per date")

# Constraint 4: Each department gets continuous dates (own range)
print("\n4. Each department gets continuous dates (own isolated range):")

# Generate available dates
available_dates = []
check_date = start
while len(available_dates) < 20:
    if check_date not in excluded_set:
        available_dates.append(check_date)
    check_date += timedelta(days=1)

violations_continuous = []
for dept in ['D1', 'D2', 'D3']:
    dept_dates = sorted(set(d for d, d2, _, _ in schedule if d2 == dept))
    if not dept_dates:
        continue
    
    # Check if these dates are continuous (no gaps)
    # A gap would mean: next_date - current_date > 1 day
    is_continuous = True
    for i in range(len(dept_dates) - 1):
        if (dept_dates[i+1] - dept_dates[i]).days != 1:
            is_continuous = False
            break
    
    if is_continuous:
        print(f"  {dept}: {len(dept_dates)} subjects on {len(dept_dates)} continuous dates ✓ {dept_dates}")
    else:
        print(f"  {dept}: Dates are NOT continuous: {dept_dates} [FAIL]")
        violations_continuous.append(f"  {dept}: {dept_dates}")

# Summary
print("\n" + "="*80)
all_pass = (not violations_excluded and not violations_dept and 
            not violations_name and not violations_continuous)
print(f"RESULT: {'ALL CONSTRAINTS SATISFIED ✓' if all_pass else 'CONSTRAINT VIOLATIONS FOUND'}")
print("="*80)
