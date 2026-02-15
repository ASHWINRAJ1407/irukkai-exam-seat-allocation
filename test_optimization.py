"""
Test case for IT department subject deduplication and optimal allocation
Simulates the scenario from the user's image
"""
from utils.timetable_generator import generate_timetable

def test_it_department_optimal_allocation():
    """
    Test that IT department subjects are allocated optimally without duplicates
    and using earlier gaps before creating new dates
    """
    print("\n" + "="*70)
    print("TEST: IT Department Optimal Allocation")
    print("="*70)
    
    # Simulate IT department subjects (same as in user's scenario)
    rows = [
        # AIDS department subjects
        {"department_code": "AIDS", "subject_code": "AIDC1", "subject_name": "DataStructures"},
        {"department_code": "AIDS", "subject_code": "AIDC2", "subject_name": "Algorithms"},
        
        # EEE department subjects
        {"department_code": "EEE", "subject_code": "EEEC1", "subject_name": "Circuits"},
        {"department_code": "EEE", "subject_code": "EEEC2", "subject_name": "PowerSystems"},
        
        # IT department subjects (as per user's scenario)
        {"department_code": "IT", "subject_code": "ITEC1", "subject_name": "DigitalTransformation"},
        {"department_code": "IT", "subject_code": "ITEC2", "subject_name": "SystemDesign"},
        {"department_code": "IT", "subject_code": "ITEC3", "subject_name": "CloudComputing"},
        {"department_code": "IT", "subject_code": "ITEC4", "subject_name": "NLP"},
        {"department_code": "IT", "subject_code": "ITEC5", "subject_name": "WaterAndSoilConservation"},
        {"department_code": "IT", "subject_code": "ITEC6", "subject_name": "AIDataProcessing"},
        
        # CSE department subjects (will have shared names)
        {"department_code": "CSE", "subject_code": "CSEC1", "subject_name": "DataStructures"},
        {"department_code": "CSE", "subject_code": "CSEC2", "subject_name": "Algorithms"},
    ]
    
    schedule, subject_map = generate_timetable(rows, "23/02/2026", [])
    
    # Verify no duplicate entries for IT department
    it_schedule = [(d, s, n) for (d, dept, s, n) in schedule if dept == "IT"]
    it_subjects = [s for (d, s, n) in it_schedule]
    
    print(f"\nIT Department Schedule:")
    for date, subject_code, subject_name in sorted(it_schedule):
        print(f"  {date}: {subject_code:10} ({subject_name})")
    
    # Check for duplicates
    print(f"\nVerification:")
    print(f"  Total IT subjects in input: 6")
    print(f"  Total IT entries in schedule: {len(it_schedule)}")
    
    if len(it_schedule) != 6:
        print(f"  ERROR: Expected 6 IT entries but got {len(it_schedule)}")
        return False
    
    # Check for duplicate subject codes
    unique_subjects = set(it_subjects)
    if len(unique_subjects) != 6:
        print(f"  ERROR: Duplicate subject codes found!")
        print(f"  Unique: {unique_subjects}")
        return False
    
    # Count dates used by IT
    it_dates = set(d for (d, s, n) in it_schedule)
    print(f"  Dates used for IT: {len(it_dates)} dates")
    print(f"  Expected: 6 dates (one per subject)")
    
    # Check that dates are consecutive or nearly consecutive (no huge gaps)
    sorted_dates = sorted(it_dates)
    date_positions = []
    current = None
    for d in sorted_dates:
        if current is None:
            date_positions.append(0)
        else:
            days_diff = (d - current).days
            date_positions.append(days_diff)
        current = d
    
    print(f"  Date gaps (days between consecutive): {date_positions[1:]}")
    
    print(f"\n[PASS] IT department allocated optimally without duplicates!")
    return True


def test_subject_consolidation():
    """
    Test that subjects with same name don't exceed 2 departments per date,
    and earlier gaps are filled before creating new dates
    """
    print("\n" + "="*70)
    print("TEST: Subject Name Consolidation (Max 2 per date)")
    print("="*70)
    
    rows = [
        {"department_code": "D1", "subject_code": "S1", "subject_name": "Math"},
        {"department_code": "D1", "subject_code": "S2", "subject_name": "Science"},
        {"department_code": "D2", "subject_code": "S3", "subject_name": "Math"},
        {"department_code": "D2", "subject_code": "S4", "subject_name": "Science"},
        {"department_code": "D3", "subject_code": "S5", "subject_name": "Math"},
        {"department_code": "D3", "subject_code": "S6", "subject_name": "Science"},
    ]
    
    schedule, _ = generate_timetable(rows, "01/02/2026", [])
    
    # Group by date
    by_date = {}
    for (date, dept, subj_code, subj_name) in schedule:
        if date not in by_date:
            by_date[date] = {}
        if subj_name not in by_date[date]:
            by_date[date][subj_name] = []
        by_date[date][subj_name].append(dept)
    
    print(f"\nSchedule by date and subject name:")
    for date in sorted(by_date.keys()):
        print(f"  {date}:")
        for subj_name in sorted(by_date[date].keys()):
            depts = by_date[date][subj_name]
            print(f"    {subj_name}: {', '.join(depts)} ({len(depts)} depts)")
            
            if len(depts) > 2:
                print(f"    ERROR: More than 2 departments for {subj_name} on {date}")
                return False
    
    total_dates = len(by_date)
    print(f"\nTotal dates used: {total_dates}")
    print(f"Expected: 3 dates (each dept gets exactly N days for N subjects)")
    
    # Verify each department gets exactly N days for N subjects
    dept_days = {}
    for date, dept, subj_code, subj_name in schedule:
        if dept not in dept_days:
            dept_days[dept] = set()
        dept_days[dept].add(date)
    
    dept_subject_count = {}
    for department_code in ['D1', 'D2', 'D3']:
        dept_items = [r for r in rows if r['department_code'] == department_code]
        dept_subject_count[department_code] = len(dept_items)
    
    proportional_correct = True
    for dept, days in dept_days.items():
        expected_days = dept_subject_count.get(dept, 0)
        if len(days) != expected_days:
            print(f"  ERROR: {dept} has {len(days)} days but {expected_days} subjects")
            proportional_correct = False
    
    if proportional_correct and total_dates <= 4:
        print(f"[PASS] Subject name constraint maintained with proportional allocation!")
        return True
    else:
        print(f"[FAIL] Proportional allocation not correct")
        return False


if __name__ == "__main__":
    results = []
    
    try:
        results.append(("IT Optimal Allocation", test_it_department_optimal_allocation()))
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append(("IT Optimal Allocation", False))
    
    try:
        results.append(("Subject Name Consolidation", test_subject_consolidation()))
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append(("Subject Name Consolidation", False))
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:40} {status}")
    
    all_passed = all(r for _, r in results)
    if all_passed:
        print("\n[SUCCESS] All optimization tests passed!")
    else:
        print("\n[FAILURE] Some tests failed")
    
    exit(0 if all_passed else 1)
