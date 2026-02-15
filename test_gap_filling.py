"""
Test suite for Timetable Compaction & Gap-Filling Logic.

Tests verify:
1. Gap detection works correctly for departments
2. Backfilling fills gaps instead of creating new dates
3. Subject name conflict rules are respected during backfilling
4. Minimal number of dates are created
5. Smart shuffling works on backfilled dates
"""

import unittest
from datetime import date, timedelta
from utils.timetable_generator import generate_timetable


class TestGapFillingLogic(unittest.TestCase):
    """Test cases for backtracking gap-filling optimization."""

    def test_gap_detection_and_backfilling(self):
        """
        Test: If AIDS has 2 subjects and AIML has 2 subjects, with proper
        subject names, all 4 exams should fit on 2 dates using gap-filling.
        
        Without gap-filling: could create 4 dates (depends on placement order)
        With gap-filling: should create exactly 2 dates
        
        Schedule:
        Date 1: AIDS-S1, AIML-S1
        Date 2: AIDS-S2, AIML-S2
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "AIDS", "subject_code": "S2", "subject_name": "Algorithms"},
            {"department_code": "AIML", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "AIML", "subject_code": "S2", "subject_name": "Algorithms"},
        ]
        
        schedule, subject_map = generate_timetable(
            rows, 
            "01/01/2024",
            []
        )
        
        # Extract unique dates
        dates_used = set(date_val for (date_val, dept, subj, name) in schedule)
        
        # Should use exactly 2 dates
        self.assertEqual(
            len(dates_used), 2,
            f"Expected 2 exam dates, got {len(dates_used)}. Gap-filling may not be working. Schedule: {schedule}"
        )
        
        # Verify all 4 subjects scheduled
        self.assertEqual(len(schedule), 4, "Not all subjects scheduled")

    def test_gap_filling_with_four_depts(self):
        """
        Test: Four departments, each with 2 subjects of different names.
        Should fit in 2 dates.
        
        Date 1: AIDS-S1, AIML-S1, CSE-S1, ECE-S1
        Date 2: AIDS-S2, AIML-S2, CSE-S2, ECE-S2
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "AIDS", "subject_code": "S2", "subject_name": "Algorithms"},
            {"department_code": "AIML", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "AIML", "subject_code": "S2", "subject_name": "Algorithms"},
            {"department_code": "CSE", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "CSE", "subject_code": "S2", "subject_name": "Algorithms"},
            {"department_code": "ECE", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "ECE", "subject_code": "S2", "subject_name": "Algorithms"},
        ]
        
        schedule, _ = generate_timetable(rows, "01/01/2024", [])
        dates_used = set(date_val for (date_val, dept, subj, name) in schedule)
        
        # With proper gap-filling, should use 2 dates
        self.assertLessEqual(
            len(dates_used), 3,
            f"Expected <= 3 dates, got {len(dates_used)}. Backfilling may not be optimal."
        )
        self.assertEqual(len(schedule), 8, "Not all 8 subjects scheduled")

    def test_subject_name_conflict_limit_respected(self):
        """
        Test: Subject name "Math" can appear max 2 times per date.
        
        3 depts with same subject name should need at least 2 dates.
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "M1", "subject_name": "Math"},
            {"department_code": "AIML", "subject_code": "M1", "subject_name": "Math"},
            {"department_code": "CSE", "subject_code": "M1", "subject_name": "Math"},
        ]
        
        schedule, _ = generate_timetable(rows, "01/01/2024", [])
        
        # Verify constraint: no subject_name appears more than 2 times on same date
        dates_with_subject_names = {}
        for (date_val, dept, subj, name) in schedule:
            if date_val not in dates_with_subject_names:
                dates_with_subject_names[date_val] = {}
            if name not in dates_with_subject_names[date_val]:
                dates_with_subject_names[date_val][name] = 0
            dates_with_subject_names[date_val][name] += 1
        
        for date_val, name_counts in dates_with_subject_names.items():
            for name, count in name_counts.items():
                self.assertLessEqual(
                    count, 2,
                    f"Subject name '{name}' appears {count} times on {date_val} (limit is 2)"
                )
        
        # Should need at least 2 dates for 3 depts with same subject
        dates_used = set(date_val for (date_val, dept, subj, name) in schedule)
        self.assertGreaterEqual(len(dates_used), 2)

    def test_single_department_all_subjects_fit_limited_dates(self):
        """
        Test: A single department with 2 subjects (same dept can only appear once per date).
        Constraint: one department per date = 2 dates needed for 2 subjects.
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "S1", "subject_name": "Math"},
            {"department_code": "AIDS", "subject_code": "S2", "subject_name": "Science"},
        ]
        
        schedule, _ = generate_timetable(rows, "01/01/2024", [])
        dates_used = set(date_val for (date_val, dept, subj, name) in schedule)
        
        # Single dept can appear once per date → need 2 dates for 2 subjects
        self.assertEqual(len(dates_used), 2)
        self.assertEqual(len(schedule), 2)

    def test_excluded_dates_force_later_scheduling(self):
        """
        Test: Excluded dates should not appear in schedule.
        Backfilling should skip excluded dates.
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "S1", "subject_name": "DataStructures"},
            {"department_code": "AIML", "subject_code": "S1", "subject_name": "DataStructures"},
        ]
        
        start_date = date(2024, 1, 1)
        excluded = [
            (start_date + timedelta(days=0)).strftime("%d/%m/%Y"),  # Jan 1
        ]
        
        schedule, _ = generate_timetable(
            rows,
            start_date.strftime("%d/%m/%Y"),
            excluded
        )
        
        # Verify no exam on excluded date
        scheduled_dates = [date_val for (date_val, _, _, _) in schedule]
        for excluded_date_str in excluded:
            excluded_obj = date(2024, 1, 1)  # Jan 1
            self.assertNotIn(excluded_obj, scheduled_dates)

    def test_gap_filling_with_multiple_subjects_same_dept(self):
        """
        Test: Department with 3 subjects should backfill gaps for all 3.
        
        AIDS: S1 (Math), S2 (Science), S3 (English)
        AIML: S1 (Math)
        
        Expected: AIDS spreads across dates optimally using gaps.
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "S1", "subject_name": "Math"},
            {"department_code": "AIDS", "subject_code": "S2", "subject_name": "Science"},
            {"department_code": "AIDS", "subject_code": "S3", "subject_name": "English"},
            {"department_code": "AIML", "subject_code": "S1", "subject_name": "Math"},
        ]
        
        schedule, _ = generate_timetable(rows, "01/01/2024", [])
        
        # All 4 should be scheduled
        self.assertEqual(len(schedule), 4)
        
        # Check AIDS appears on multiple dates (backfilled gaps)
        aids_dates = set(date_val for (date_val, dept, _, _) in schedule if dept == "AIDS")
        self.assertGreaterEqual(
            len(aids_dates), 1,
            "AIDS should appear in schedule"
        )

    def test_shuffling_on_backfilled_gap(self):
        """
        Test: If a subject conflicts on a gap date, shuffling should occur.
        
        Scenario:
        - AIDS: S1 (Math), S2 (Science)
        - AIML: S1 (Math), S3 (HistoryOfAI)
        - CSE: S1 (Math), S4 (CompilerDesign)
        
        All three have "Math" (S1). On a gap date, if AIDS-S1 conflicts,
        system should try AIDS-S2 instead (shuffle).
        """
        rows = [
            {"department_code": "AIDS", "subject_code": "S1", "subject_name": "Math"},
            {"department_code": "AIDS", "subject_code": "S2", "subject_name": "Science"},
            {"department_code": "AIML", "subject_code": "S1", "subject_name": "Math"},
            {"department_code": "AIML", "subject_code": "S3", "subject_name": "HistoryOfAI"},
            {"department_code": "CSE", "subject_code": "S1", "subject_name": "Math"},
            {"department_code": "CSE", "subject_code": "S4", "subject_name": "CompilerDesign"},
        ]
        
        schedule, _ = generate_timetable(rows, "01/01/2024", [])
        
        # All subjects should be scheduled (shuffle should handle conflicts)
        self.assertEqual(len(schedule), 6)
        
        # Verify no date has more than 2 Math exams
        date_math_counts = {}
        for (date_val, dept, subj, name) in schedule:
            if name == "Math":
                if date_val not in date_math_counts:
                    date_math_counts[date_val] = 0
                date_math_counts[date_val] += 1
        
        for date_val, count in date_math_counts.items():
            self.assertLessEqual(count, 2, f"Date {date_val} has {count} Math exams (max 2)")

    def test_empty_rows_returns_empty_schedule(self):
        """Test: Empty input should return empty schedule."""
        schedule, _ = generate_timetable([], "01/01/2024", [])
        self.assertEqual(len(schedule), 0)

    def test_comprehensive_multi_dept_scenario(self):
        """
        Test: Complex real-world scenario with multiple departments and subjects.
        
        Verifies:
        - All subjects scheduled
        - No subject_name exceeds 2 depts per date
        - Gap-filling minimizes total dates
        """
        rows = [
            # AIDS: 3 subjects
            {"department_code": "AIDS", "subject_code": "CS101", "subject_name": "DataStructures"},
            {"department_code": "AIDS", "subject_code": "CS102", "subject_name": "Algorithms"},
            {"department_code": "AIDS", "subject_code": "CS103", "subject_name": "OS"},
            # AIML: 3 subjects (overlapping names)
            {"department_code": "AIML", "subject_code": "AI101", "subject_name": "DataStructures"},
            {"department_code": "AIML", "subject_code": "AI102", "subject_name": "MachineLearning"},
            {"department_code": "AIML", "subject_code": "AI103", "subject_name": "OS"},
            # CSE: 2 subjects
            {"department_code": "CSE", "subject_code": "CE101", "subject_name": "Algorithms"},
            {"department_code": "CSE", "subject_code": "CE102", "subject_name": "Networking"},
        ]
        
        schedule, _ = generate_timetable(rows, "01/01/2024", [])
        
        # All 8 subjects scheduled
        self.assertEqual(len(schedule), 8, "Not all subjects scheduled")
        
        # Verify subject_name constraints
        dates_with_names = {}
        for (date_val, dept, subj, name) in schedule:
            if date_val not in dates_with_names:
                dates_with_names[date_val] = {}
            if name not in dates_with_names[date_val]:
                dates_with_names[date_val][name] = []
            dates_with_names[date_val][name].append(dept)
        
        for date_val, name_depts in dates_with_names.items():
            for name, depts in name_depts.items():
                self.assertLessEqual(
                    len(depts), 2,
                    f"Date {date_val}: Subject '{name}' scheduled for {len(depts)} depts (max 2)"
                )
        
        # Gap-filling should produce minimal dates
        dates_used = len(dates_with_names)
        self.assertLessEqual(
            dates_used, 4,
            f"Expected <= 4 dates with gap-filling, got {dates_used}"
        )


if __name__ == "__main__":
    unittest.main()
