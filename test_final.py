from utils.timetable_generator import generate_timetable
from datetime import date, timedelta

print("="*80)
print("FINAL TEST: Continuous Dates Per Department")
print("="*80)

# Test Case: 3 departments with different subject counts and shared subject names
rows = [
    # D1: 4 subjects
    {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
    {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Science'},
    {'department_code': 'D1', 'subject_code': 'S3', 'subject_name': 'English'},
    {'department_code': 'D1', 'subject_code': 'S4', 'subject_name': 'History'},
    # D2: 3 subjects (shares Math and Science with D1)
    {'department_code': 'D2', 'subject_code': 'T1', 'subject_name': 'Math'},
    {'department_code': 'D2', 'subject_code': 'T2', 'subject_name': 'Science'},
    {'department_code': 'D2', 'subject_code': 'T3', 'subject_name': 'Hindi'},
    # D3: 2 subjects (shares Math and Art - Art is unique)
    {'department_code': 'D3', 'subject_code': 'U1', 'subject_name': 'Math'},
    {'department_code': 'D3', 'subject_code': 'U2', 'subject_name': 'Art'},
]

start = date(2024, 5, 1)
excluded = ['02/05/2024', '04/05/2024']  # May 2, 4 excluded
schedule, _ = generate_timetable(rows, start.strftime('%d/%m/%Y'), excluded)

excluded_set = {date(2024, 5, 2), date(2024, 5, 4)}

# Generate available dates for verification
available_dates = []
check_date = start
while len(available_dates) < 20:
    if check_date not in excluded_set:
        available_dates.append(check_date)
    check_date += timedelta(days=1)

# Print schedule
print(f"\nExcluded dates: May 2, May 4")
print(f"Available dates: {[d.strftime('%b %d') for d in available_dates[:9]]}")
print(f"\nSchedule (sorted by date):")
for d, dept, subj, name in sorted(schedule):
    print(f"  {d.strftime('%b %d')}: {dept} - {name}")

# Validation
print("\n" + "="*80)
print("CONSTRAINT VERIFICATION")
print("="*80)

all_violations = []

# Constraint 1: No exam on excluded dates
print("\n✓ Constraint 1: No exams on excluded dates")
for d, dept, subj, name in schedule:
    if d in excluded_set:
        all_violations.append(f"  ERROR: {d} ({dept} {name}) is on excluded date")
print(f"  Status: {'PASS' if not any('ERROR' in str(v) for v in all_violations) else 'FAIL'}")

# Constraint 2: No department appears twice on same date
print("\n✓ Constraint 2: No department appears twice on same date")
dept_per_date = {}
for d, dept, subj, name in schedule:
    if d not in dept_per_date:
        dept_per_date[d] = []
    dept_per_date[d].append(dept)

for d, depts in dept_per_date.items():
    if len(depts) != len(set(depts)):
        all_violations.append(f"  ERROR: {d} has duplicate dept")

print(f"  Status: {'PASS' if not any('duplicate' in str(v) for v in all_violations) else 'FAIL'}")

# Constraint 3: Max 2 departments per subject_name per date
print("\n✓ Constraint 3: Max 2 departments per subject_name per date")
subj_per_date = {}
for d, dept, subj, name in schedule:
    key = (d, name)
    if key not in subj_per_date:
        subj_per_date[key] = []
    subj_per_date[key].append(dept)

max_2_violation = False
for (d, name), depts in subj_per_date.items():
    if len(depts) > 2:
        all_violations.append(f"  ERROR: {d} {name} has {len(depts)} depts")
        max_2_violation = True

print(f"  Status: {'PASS' if not max_2_violation else 'FAIL'}")

# Constraint 4: Each department gets continuous dates
print("\n✓ Constraint 4: Each department gets continuous dates")
continuous_violation = False
for dept in ['D1', 'D2', 'D3']:
    dept_dates = sorted(set(d for d, d2, _, _ in schedule if d2 == dept))
    if not dept_dates:
        continue
    
    # Expected dates for this dept
    num_subjects = len([r for r in rows if r['department_code'] == dept])
    expected_dates = available_dates[:sum(len([r for r in rows if r['department_code'] == d]) 
                                          for d in ['D1', 'D2', 'D3'] 
                                          if d <= dept)]
    expected_dates = expected_dates[-num_subjects:]
    
    # Check if actual matches expected
    if dept_dates == expected_dates:
        print(f"  {dept}: {num_subjects} subjects ✓ {[d.strftime('%b %d') for d in dept_dates]}")
    else:
        print(f"  {dept}: Expected {[d.strftime('%b %d') for d in expected_dates]}")
        print(f"        Got      {[d.strftime('%b %d') for d in dept_dates  ]}")
        continuous_violation = True
        all_violations.append(f"  {dept}: continuous allocation mismatch")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"  Total subjects scheduled: {len(schedule)} / {len(rows)}")
print(f"  Constraint violations: {len(all_violations)}")
if all_violations:
    for v in all_violations:
        print(v)
    print(f"\nRESULT: CONSTRAINT VIOLATIONS FOUND")
else:
    print(f"\nRESULT: ALL CONSTRAINTS SATISFIED ✓")
print("="*80)
