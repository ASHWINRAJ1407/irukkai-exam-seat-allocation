"""
Simple test runner that avoids Unicode issues in Windows
"""
import sys
import io
from datetime import date
from utils.timetable_generator import generate_timetable

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_basic_gap_filling():
    """Test 1: Basic gap-filling with 2 depts, 2 subjects each"""
    print("\n" + "="*70)
    print("TEST 1: Basic Gap-Filling (2 depts, 2 subjects each)")
    print("="*70)
    
    rows = [
        {"department_code": "AIDS", "subject_code": "S1", "subject_name": "DataStructures"},
        {"department_code": "AIDS", "subject_code": "S2", "subject_name": "Algorithms"},
        {"department_code": "AIML", "subject_code": "S1", "subject_name": "DataStructures"},
        {"department_code": "AIML", "subject_code": "S2", "subject_name": "Algorithms"},
    ]
    
    schedule, subject_map = generate_timetable(rows, "01/01/2024", [])
    dates_used = set(d for (d, dept, subj, name) in schedule)
    
    print(f"Input: 4 subjects across 2 departments")
    print(f"Output Schedule Length: {len(dates_used)} dates")
    print(f"Expected: 2 dates (optimized)")
    
    for date_val, dept, subj, name in sorted(schedule):
        print(f"  {date_val}: {dept:6} - {subj:6} ({name})")
    
    assert len(dates_used) == 2, f"Expected 2 dates, got {len(dates_used)}"
    assert len(schedule) == 4, f"Expected 4 subjects scheduled, got {len(schedule)}"
    
    print("[PASS] Gap-filling works correctly!")
    return True


def test_subject_name_constraint():
    """Test 2: Subject name constraint (max 2 depts per name per date)"""
    print("\n" + "="*70)
    print("TEST 2: Subject Name Constraint (Max 2 depts per name)")
    print("="*70)
    
    rows = [
        {"department_code": "AIDS", "subject_code": "M1", "subject_name": "Math"},
        {"department_code": "AIML", "subject_code": "M1", "subject_name": "Math"},
        {"department_code": "CSE", "subject_code": "M1", "subject_name": "Math"},
    ]
    
    schedule, subject_map = generate_timetable(rows, "01/01/2024", [])
    dates_used = set(d for (d, dept, subj, name) in schedule)
    
    print(f"Input: 3 depts with same subject name 'Math'")
    print(f"Output Schedule Length: {len(dates_used)} dates")
    print(f"Expected: 2 dates (max 2 depts per name per date)")
    
    for date_val, dept, subj, name in sorted(schedule):
        print(f"  {date_val}: {dept:6} - {subj:6} ({name})")
    
    # Verify constraint
    for date_val in dates_used:
        math_depts = [dept for d, dept, subj, name in schedule if d == date_val and name == "Math"]
        assert len(math_depts) <= 2, f"Date {date_val} has {len(math_depts)} depts for Math (max 2)"
    
    assert len(dates_used) == 2, f"Expected 2 dates, got {len(dates_used)}"
    assert len(schedule) == 3, f"Expected 3 subjects scheduled, got {len(schedule)}"
    
    print("[PASS] Subject name constraint enforced correctly!")
    return True


def test_complex_schedule():
    """Test 3: Complex scenario with multiple subjects"""
    print("\n" + "="*70)
    print("TEST 3: Complex Schedule (8 subjects, mix of shared/unique names)")
    print("="*70)
    
    rows = [
        {"department_code": "AIDS", "subject_code": "S1", "subject_name": "Math"},
        {"department_code": "AIDS", "subject_code": "S2", "subject_name": "English"},
        {"department_code": "AIML", "subject_code": "S1", "subject_name": "Math"},
        {"department_code": "AIML", "subject_code": "S2", "subject_name": "Science"},
        {"department_code": "CSE", "subject_code": "S1", "subject_name": "Math"},
        {"department_code": "CSE", "subject_code": "S2", "subject_name": "Science"},
        {"department_code": "ECE", "subject_code": "S1", "subject_name": "History"},
        {"department_code": "ECE", "subject_code": "S2", "subject_name": "Geography"},
    ]
    
    schedule, subject_map = generate_timetable(rows, "01/01/2024", [])
    dates_used = set(d for (d, dept, subj, name) in schedule)
    
    print(f"Input: 8 subjects across 4 departments")
    print(f"Output Schedule Length: {len(dates_used)} dates")
    print(f"Expected: 3 dates (due to constraint on Math/Science)")
    
    for date_val, dept, subj, name in sorted(schedule):
        print(f"  {date_val}: {dept:6} - {subj:6} ({name})")
    
    assert len(schedule) == 8, f"Expected 8 subjects scheduled, got {len(schedule)}"
    print("[PASS] Complex schedule generated successfully!")
    return True


def test_excluded_dates():
    """Test 4: Excluded dates handling"""
    print("\n" + "="*70)
    print("TEST 4: Excluded Dates Handling")
    print("="*70)
    
    rows = [
        {"department_code": "AIDS", "subject_code": "S1", "subject_name": "Math"},
        {"department_code": "AIDS", "subject_code": "S2", "subject_name": "English"},
    ]
    
    excluded = ["01/01/2024"]  # Exclude first date
    schedule, subject_map = generate_timetable(rows, "01/01/2024", excluded)
    
    print(f"Input: 2 subjects, excluded dates: {excluded}")
    print(f"Schedule generated:")
    
    for date_val, dept, subj, name in sorted(schedule):
        print(f"  {date_val}: {dept:6} - {subj:6} ({name})")
        assert date_val not in excluded, f"Scheduled on excluded date {date_val}"
    
    print("[PASS] Excluded dates respected!")
    return True


def test_imports():
    """Test 5: Module imports"""
    print("\n" + "="*70)
    print("TEST 5: Module Imports")
    print("="*70)
    
    try:
        from utils.timetable_generator import generate_timetable
        from models import db, Department, Subject, ExamSchedule
        
        print("[PASS] All core modules imported successfully!")
        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("ESAL v2.0 - COMPREHENSIVE VERIFICATION TEST SUITE")
    print("="*70)
    
    results = []
    
    try:
        results.append(("Basic Gap-Filling", test_basic_gap_filling()))
    except Exception as e:
        print(f"[FAIL] {e}")
        results.append(("Basic Gap-Filling", False))
    
    try:
        results.append(("Subject Name Constraint", test_subject_name_constraint()))
    except Exception as e:
        print(f"[FAIL] {e}")
        results.append(("Subject Name Constraint", False))
    
    try:
        results.append(("Complex Schedule", test_complex_schedule()))
    except Exception as e:
        print(f"[FAIL] {e}")
        results.append(("Complex Schedule", False))
    
    try:
        results.append(("Excluded Dates", test_excluded_dates()))
    except Exception as e:
        print(f"[FAIL] {e}")
        results.append(("Excluded Dates", False))
    
    try:
        results.append(("Module Imports", test_imports()))
    except Exception as e:
        print(f"[FAIL] {e}")
        results.append(("Module Imports", False))
    
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:30} {status}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n[SUCCESS] ALL TESTS PASSED - SYSTEM READY!")
    else:
        print("\n[ERROR] SOME TESTS FAILED")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
