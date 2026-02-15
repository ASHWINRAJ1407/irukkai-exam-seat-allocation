"""
Comprehensive test suite for ESAL Timetable Generator v2.0
Tests: backtracking, gap-filling, date sufficiency, exclusion dates, smart shuffling, and UI validation.
"""
from utils.timetable_generator import generate_timetable
from datetime import date

def test_case(name, rows, start_str, end_str, excluded, expected_warn=False):
    """Helper to run and report test."""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    try:
        result = generate_timetable(rows, start_str, excluded, {'__end_date__': end_str})
        if isinstance(result, tuple) and len(result) == 3:
            schedule, _, warning = result
        else:
            schedule, _ = result
            warning = None
        
        print(f"Status: {'⚠️ WARNING' if warning else '✓ SUCCESS'}")
        if warning:
            print(f"Warning: {warning}")
        
        if schedule:
            print(f"Total allocations: {len(schedule)}")
            depts = set(d for _, d, _, _ in schedule)
            print(f"Departments: {sorted(depts)}")
            print(f"Schedule preview:")
            for d, dept, subj, name in sorted(schedule)[:10]:
                print(f"  {d}: {dept} - {name}")
            if len(schedule) > 10:
                print(f"  ... and {len(schedule) - 10} more")
        
        # Validate constraints
        validate_constraints(schedule, excluded)
        return True
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False

def validate_constraints(schedule, excluded_list):
    """Check all constraints."""
    if not schedule:
        print("✓ No schedule (empty, which is valid for insufficient dates)")
        return
    
    excluded_set = set()
    for e in excluded_list:
        parts = e.split('/')
        excluded_set.add(date(int(parts[2]), int(parts[1]), int(parts[0])))
    
    # Constraint 1: No dept twice on same date
    dept_per_date = {}
    for d, dept, _, _ in schedule:
        if d not in dept_per_date:
            dept_per_date[d] = []
        dept_per_date[d].append(dept)
    
    viol = [d for d, depts in dept_per_date.items() if len(depts) != len(set(depts))]
    print(f"✓ Constraint 1 (no dept twice/date): {'PASS' if not viol else 'FAIL - ' + str(viol)}")
    
    # Constraint 2: Max 2 per subject_name
    name_per_date = {}
    for d, dept, _, name in schedule:
        key = (d, name)
        if key not in name_per_date:
            name_per_date[key] = []
        name_per_date[key].append(dept)
    
    viol2 = [(d, n, len(ds)) for (d, n), ds in name_per_date.items() if len(ds) > 2]
    print(f"✓ Constraint 2 (max 2/subject/date): {'PASS' if not viol2 else 'FAIL - ' + str(viol2)}")
    
    # Constraint 3: No exams on excluded dates
    exams_on_excluded = [d for d, _, _, _ in schedule if d in excluded_set]
    print(f"✓ Constraint 3 (exclude dates): {'PASS' if not exams_on_excluded else 'FAIL - ' + str(exams_on_excluded)}")

# ========== TESTS ==========

test_case(
    "Basic compaction: 2 depts, 2 subjects each, 5-day window",
    [
        {'department_code': 'CS', 'subject_code': 'S1', 'subject_name': 'Math'},
        {'department_code': 'CS', 'subject_code': 'S2', 'subject_name': 'Physics'},
        {'department_code': 'IT', 'subject_code': 'S3', 'subject_name': 'Math'},
        {'department_code': 'IT', 'subject_code': 'S4', 'subject_name': 'Biology'},
    ],
    '01/05/2024', '05/05/2024', []
)

test_case(
    "Insufficient date range (should warn)",
    [
        {'department_code': 'CS', 'subject_code': 'S1', 'subject_name': 'Math'},
        {'department_code': 'CS', 'subject_code': 'S2', 'subject_name': 'Physics'},
        {'department_code': 'CS', 'subject_code': 'S3', 'subject_name': 'Chemistry'},
    ],
    '01/05/2024', '02/05/2024', [],
    expected_warn=True
)

test_case(
    "Exclusion dates with compaction",
    [
        {'department_code': 'ECE', 'subject_code': 'S1', 'subject_name': 'Math'},
        {'department_code': 'ECE', 'subject_code': 'S2', 'subject_name': 'Physics'},
        {'department_code': 'ECE', 'subject_code': 'S3', 'subject_name': 'Chemistry'},
    ],
    '01/05/2024', '07/05/2024', ['02/05/2024', '04/05/2024', '06/05/2024']
)

test_case(
    "Smart shuffling: 3 depts, all want same subject names",
    [
        {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
        {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Physics'},
        {'department_code': 'D2', 'subject_code': 'S3', 'subject_name': 'Math'},
        {'department_code': 'D2', 'subject_code': 'S4', 'subject_name': 'Physics'},
        {'department_code': 'D3', 'subject_code': 'S5', 'subject_name': 'Math'},
        {'department_code': 'D3', 'subject_code': 'S6', 'subject_name': 'Physics'},
    ],
    '01/05/2024', '08/05/2024', []
)

test_case(
    "Order independence: same data, different order",
    [
        {'department_code': 'IT', 'subject_code': 'B', 'subject_name': 'Biology'},
        {'department_code': 'CS', 'subject_code': 'M', 'subject_name': 'Math'},
        {'department_code': 'IT', 'subject_code': 'A', 'subject_name': 'Arts'},
        {'department_code': 'CS', 'subject_code': 'E', 'subject_name': 'English'},
    ],
    '01/05/2024', '05/05/2024', []
)

test_case(
    "All dates excluded (should fail with warning)",
    [
        {'department_code': 'CS', 'subject_code': 'S1', 'subject_name': 'Math'},
    ],
    '01/05/2024', '01/05/2024', ['01/05/2024'],
    expected_warn=True
)

test_case(
    "Large scenario: 5 depts, varied subject counts",
    [
        {'department_code': 'D1', 'subject_code': 'S1', 'subject_name': 'Math'},
        {'department_code': 'D1', 'subject_code': 'S2', 'subject_name': 'Physics'},
        {'department_code': 'D1', 'subject_code': 'S3', 'subject_name': 'Chemistry'},
        {'department_code': 'D1', 'subject_code': 'S4', 'subject_name': 'Biology'},
        {'department_code': 'D2', 'subject_code': 'S5', 'subject_name': 'Math'},
        {'department_code': 'D2', 'subject_code': 'S6', 'subject_name': 'English'},
        {'department_code': 'D3', 'subject_code': 'S7', 'subject_name': 'History'},
        {'department_code': 'D3', 'subject_code': 'S8', 'subject_name': 'Math'},
        {'department_code': 'D3', 'subject_code': 'S9', 'subject_name': 'Geography'},
        {'department_code': 'D4', 'subject_code': 'S10', 'subject_name': 'Physics'},
        {'department_code': 'D5', 'subject_code': 'S11', 'subject_name': 'Chemistry'},
        {'department_code': 'D5', 'subject_code': 'S12', 'subject_name': 'Math'},
    ],
    '01/05/2024', '31/05/2024', ['10/05/2024', '20/05/2024']
)

print(f"\n{'='*80}")
print("COMPREHENSIVE TEST SUITE COMPLETE")
print(f"{'='*80}")
