"""
Comprehensive Verification Script for ESAL v2.0
Tests all features including gap-filling optimization
"""

import sys
from datetime import date
from utils.timetable_generator import generate_timetable


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
    
    print("✅ PASS: Gap-filling works correctly!")
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
    
    schedule, _ = generate_timetable(rows, "01/01/2024", [])
    
    # Verify constraint
    date_counts = {}
    for (date_val, dept, subj, name) in schedule:
        if date_val not in date_counts:
            date_counts[date_val] = {}
        if name not in date_counts[date_val]:
            date_counts[date_val][name] = 0
        date_counts[date_val][name] += 1
    
    print(f"Input: 3 depts with same subject 'Math'")
    print(f"Schedule:")
    for date_val, names in sorted(date_counts.items()):
        for name, count in names.items():
            print(f"  {date_val}: {name} → {count} depts")
    
    for date_val, names in date_counts.items():
        for name, count in names.items():
            assert count <= 2, f"Subject '{name}' on {date_val} has {count} depts (max 2)"
    
    print("✅ PASS: Subject name constraint respected!")
    return True


def test_complex_scenario():
    """Test 3: Complex multi-department scenario"""
    print("\n" + "="*70)
    print("TEST 3: Complex Scenario (8 subjects, mix of shared names)")
    print("="*70)
    
    rows = [
        {"department_code": "AIDS", "subject_code": "CS101", "subject_name": "DataStructures"},
        {"department_code": "AIDS", "subject_code": "CS102", "subject_name": "Algorithms"},
        {"department_code": "AIDS", "subject_code": "CS103", "subject_name": "OS"},
        {"department_code": "AIML", "subject_code": "AI101", "subject_name": "DataStructures"},
        {"department_code": "AIML", "subject_code": "AI102", "subject_name": "MachineLearning"},
        {"department_code": "AIML", "subject_code": "AI103", "subject_name": "OS"},
        {"department_code": "CSE", "subject_code": "CE101", "subject_name": "Algorithms"},
        {"department_code": "CSE", "subject_code": "CE102", "subject_name": "Networking"},
    ]
    
    schedule, _ = generate_timetable(rows, "01/01/2024", [])
    dates_used = set(d for (d, dept, subj, name) in schedule)
    
    print(f"Input: 8 subjects across 3 departments")
    print(f"Shared names: DataStructures (AIDS, AIML), Algorithms (AIDS, CSE), OS (AIDS, AIML)")
    print(f"Output: {len(dates_used)} exam dates")
    
    for date_val in sorted(dates_used):
        exams_on_date = [(dept, subj, name) for (d, dept, subj, name) in schedule if d == date_val]
        print(f"  Date {date_val}:")
        for dept, subj, name in sorted(exams_on_date):
            print(f"    - {dept} ({name})")
    
    assert len(schedule) == 8, f"Expected 8 subjects, got {len(schedule)}"
    assert len(dates_used) <= 4, f"Expected <= 4 dates, got {len(dates_used)}"
    
    print("✅ PASS: Complex scenario handled optimally!")
    return True


def test_excluded_dates():
    """Test 4: Excluded dates are respected"""
    print("\n" + "="*70)
    print("TEST 4: Excluded Dates Handling")
    print("="*70)
    
    rows = [
        {"department_code": "AIDS", "subject_code": "S1", "subject_name": "Math"},
        {"department_code": "AIML", "subject_code": "S1", "subject_name": "Math"},
    ]
    
    excluded = ["01/01/2024"]  # Exclude first date
    schedule, _ = generate_timetable(rows, "01/01/2024", excluded)
    
    scheduled_dates = [d for (d, _, _, _) in schedule]
    
    print(f"Input: 2 subjects starting 01/01/2024 with 01/01/2024 excluded")
    print(f"Scheduled dates: {scheduled_dates}")
    print(f"Excluded date: 01/01/2024")
    
    excluded_obj = date(2024, 1, 1)
    assert excluded_obj not in scheduled_dates, "Excluded date appears in schedule!"
    
    print("✅ PASS: Excluded dates respected!")
    return True


def test_syntax_validation():
    """Test 5: Verify all modules import correctly"""
    print("\n" + "="*70)
    print("TEST 5: Module Import Validation")
    print("="*70)
    
    try:
        from utils import timetable_generator
        print("✅ utils.timetable_generator imported successfully")
        
        from utils import allocation_engine
        print("✅ utils.allocation_engine imported successfully")
        
        from utils import pdf_generator
        print("✅ utils.pdf_generator imported successfully")
        
        from models import Subject
        print("✅ models.Subject imported successfully")
        
        print("\n✅ PASS: All modules import successfully!")
        return True
    except Exception as e:
        print(f"❌ FAIL: Import error: {e}")
        return False


def main():
    """Run all verification tests"""
    print("\n" + "="*70)
    print("ESAL v2.0 - COMPREHENSIVE VERIFICATION TEST SUITE")
    print("="*70)
    print("Testing: Gap-Filling Optimization + Subject Name Features")
    
    results = []
    
    try:
        results.append(("Basic Gap-Filling", test_basic_gap_filling()))
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(("Basic Gap-Filling", False))
    
    try:
        results.append(("Subject Name Constraint", test_subject_name_constraint()))
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(("Subject Name Constraint", False))
    
    try:
        results.append(("Complex Scenario", test_complex_scenario()))
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(("Complex Scenario", False))
    
    try:
        results.append(("Excluded Dates", test_excluded_dates()))
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(("Excluded Dates", False))
    
    try:
        results.append(("Module Imports", test_syntax_validation()))
    except Exception as e:
        print(f"❌ FAIL: {e}")
        results.append(("Module Imports", False))
    
    # Print summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for (name, result) in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION! 🎉\n")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed - see details above\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
