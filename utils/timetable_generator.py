"""
Intelligent exam timetable generation with continuous date allocation.
- Each department gets exactly N continuous dates for N subjects
- Continuous means no gaps between allocation dates (excluding non-available dates)
- Respects exclusion dates
- Max 1 department per subject_name on any date
- No conflicts between department exams
"""
from datetime import date, timedelta
from collections import defaultdict


def _parse_dd_mm_yyyy(s):
    """Parse dd/mm/yyyy or YYYY-MM-DD to date."""
    if isinstance(s, date):
        return s
    s = str(s).strip()
    if not s:
        raise ValueError("Date is required")
    # Support HTML date input (YYYY-MM-DD)
    if len(s) == 10 and s[4] == '-' and s[7] == '-':
        y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        return date(y, m, d)
    parts = s.split('/')
    if len(parts) != 3:
        raise ValueError("Date must be dd/mm/yyyy or YYYY-MM-DD")
    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
    return date(y, m, d)


def generate_timetable(rows, start_date_str, excluded_dates_str_list, subject_names_map=None):

    """
    Generate exam timetable with backtracking gap-filling and date sufficiency check.
    Args:
        rows: list of dicts with department_code, subject_code, subject_name
        start_date_str: dd/mm/yyyy
        end_date_str: dd/mm/yyyy (NEW, must be passed as a kwarg or in subject_names_map)
        excluded_dates_str_list: list of excluded dd/mm/yyyy strings
        subject_names_map: optional dict {subject_code: subject_name}
    Returns:
        (schedule_list, subject_names_map, warning) where schedule_list is list of 
        (date, dept_code, subject_code, subject_name) tuples, and warning is None or a string
    """
    # Support end_date as kwarg or in subject_names_map
    end_date_str = None
    if subject_names_map and isinstance(subject_names_map, dict) and '__end_date__' in subject_names_map:
        end_date_str = subject_names_map['__end_date__']
    if not end_date_str and isinstance(subject_names_map, dict) and 'end_date_str' in subject_names_map:
        end_date_str = subject_names_map['end_date_str']

    start_date = _parse_dd_mm_yyyy(start_date_str)

    # Track whether caller provided an explicit end date (via subject_names_map)
    provided_end_date = bool(end_date_str)

    # Build excluded set first so we can infer end_date when missing
    excluded = set()
    for s in (excluded_dates_str_list or []):
        s = str(s).strip()
        if not s:
            continue
        try:
            excluded.add(_parse_dd_mm_yyyy(s))
        except (ValueError, TypeError):
            pass

    # Determine maximum subjects any department needs (for inferring end_date)
    dept_subjects_count = {}
    for r in rows:
        dept = (r.get("department_code") or "").strip().upper()
        if dept:
            dept_subjects_count[dept] = dept_subjects_count.get(dept, 0) + 1
    max_subjects = max(dept_subjects_count.values()) if dept_subjects_count else 0

    # Also consider subject-name conflicts: if N departments share the same
    # subject name, they need at least N distinct dates (max 1 per date).
    name_depts = {}
    for r in rows:
        name = (r.get("subject_name") or "").strip()
        dept = (r.get("department_code") or "").strip().upper()
        if not name or not dept:
            continue
        name_depts.setdefault(name, set()).add(dept)
    max_name_need = 0
    for depts in name_depts.values():
        cnt = len(depts)
        need = cnt
        if need > max_name_need:
            max_name_need = need

    # Required dates must satisfy both per-department continuous needs and
    # subject-name concurrency constraints.
    required_dates = max(max_subjects, max_name_need)

    # If there are no subjects to schedule, return empty schedule (2-tuple)
    if max_subjects == 0:
        return [], subject_names_map or {}

    # If end_date_str not provided, infer a compact window starting at start_date
    # that contains at least `max_subjects` available (non-excluded) dates.
    if not end_date_str:
        available_dates = []
        d = start_date
        # Guard: avoid infinite loop; limit search to a reasonable horizon (e.g., 365 days)
        days_searched = 0
        while len(available_dates) < required_dates and days_searched < 365:
            if d not in excluded:
                available_dates.append(d)
            d += timedelta(days=1)
            days_searched += 1
        if len(available_dates) < required_dates:
            warning = f"Insufficient dates in inferred window: found {len(available_dates)}, need {required_dates}."
            if provided_end_date:
                return [], subject_names_map, warning
            return [], subject_names_map
        end_date = available_dates[-1]
    else:
        end_date = _parse_dd_mm_yyyy(end_date_str)
        # Build the list of available dates in the window
        available_dates = []
        d = start_date
        while d <= end_date:
            if d not in excluded:
                available_dates.append(d)
            d += timedelta(days=1)

    # Check if the available dates are sufficient
    dept_subjects_count = {}
    for r in rows:
        dept = (r.get("department_code") or "").strip().upper()
        if dept:
            dept_subjects_count[dept] = dept_subjects_count.get(dept, 0) + 1
    max_subjects = max(dept_subjects_count.values()) if dept_subjects_count else 0
    if len(available_dates) < max_subjects:
        warning = f"Insufficient dates: {len(available_dates)} available, but at least {max_subjects} needed for department with most subjects."
        if provided_end_date:
            return [], subject_names_map, warning
        return [], subject_names_map

    # Build subject_code -> subject_name map
    names_from_rows = {}
    for r in rows:
        code = (r.get("subject_code") or "").upper().strip()
        name = (r.get("subject_name") or "").strip()
        if code and name:
            names_from_rows[code] = name
    
    if subject_names_map is None:
        subject_names_map = names_from_rows
    else:
        for code, name in names_from_rows.items():
            if code not in subject_names_map:
                subject_names_map[code] = name

    # Extract and sort items for deterministic processing
    items = [(r["department_code"].upper(), r["subject_code"].upper()) 
             for r in rows if r.get("department_code") and r.get("subject_code")]
    items = sorted(set(items))
    
    if not items:
        return [], subject_names_map

    # Group subjects by department for easy lookup
    dept_subjects = defaultdict(list)
    for dept, subj in items:
        dept_subjects[dept].append(subj)
    
    # Build subject_code -> subject_name map
    names_from_rows = {}
    for r in rows:
        code = (r.get("subject_code") or "").upper().strip()
        name = (r.get("subject_name") or "").strip()
        if code and name:
            names_from_rows[code] = name

    if subject_names_map is None:
        subject_names_map = names_from_rows
    else:
        for code, name in names_from_rows.items():
            if code not in subject_names_map:
                subject_names_map[code] = name

    # Group subjects by department (order-independent)
    dept_subjects = defaultdict(list)
    for r in rows:
        dept = (r.get("department_code") or "").strip().upper()
        subj = (r.get("subject_code") or "").strip().upper()
        if dept and subj:
            dept_subjects[dept].append(subj)

    departments = sorted(dept_subjects.keys())
    schedule = []

    # (no debug prints)

    # Helper: count subject_name on a date
    def count_subject_on_date(date_val, subject_name, schedule):
        return sum(1 for (d, _, _, n) in schedule if d == date_val and n == subject_name)

    # Helper: check if dept has exam on date
    def dept_has_exam(date_val, dept, schedule):
        return any(d == date_val and dept == dept_code for (d, dept_code, _, _) in schedule)

    # Backtracking allocation: try to fill all subjects for all depts in compact window
    from copy import deepcopy

    def allocate(dept_idx, schedule, dept_subjects_left):
        if dept_idx == len(departments):
            return schedule  # All departments scheduled
        dept = departments[dept_idx]
        subjects = dept_subjects_left[dept]
        # Try all permutations of subject order for this department
        from itertools import permutations
        for subj_order in permutations(subjects):
            # Exhaustive backtracking over dates for the chosen subject order
            temp_schedule = deepcopy(schedule)
            used_dates = set(d for d, dpt, _, _ in temp_schedule if dpt == dept)

            def assign_subjects(idx, cur_schedule, cur_used_dates):
                # All subjects for this department assigned; recurse to next department
                if idx == len(subj_order):
                    new_dept_subjects_left = deepcopy(dept_subjects_left)
                    new_dept_subjects_left[dept] = []
                    return allocate(dept_idx + 1, cur_schedule, new_dept_subjects_left)

                subj_code = subj_order[idx]
                subj_name = subject_names_map.get(subj_code, subj_code)

                # Try each available date
                for d in available_dates:
                    if d in cur_used_dates:
                        continue
                    if count_subject_on_date(d, subj_name, cur_schedule) >= 1:
                        continue
                    if dept_has_exam(d, dept, cur_schedule):
                        continue
                    # Place and recurse
                    cur_schedule.append((d, dept, subj_code, subj_name))
                    cur_used_dates.add(d)
                    res = assign_subjects(idx + 1, cur_schedule, cur_used_dates)
                    if res is not None:
                        return res
                    # Backtrack
                    cur_used_dates.remove(d)
                    cur_schedule.pop()
                return None

            result = assign_subjects(0, temp_schedule, used_dates)
            if result is not None:
                return result
        return None

    # Prepare subject pools for each department
    dept_subjects_left = {dept: list(set(subjs)) for dept, subjs in dept_subjects.items()}
    result_schedule = allocate(0, [], dept_subjects_left)
    if result_schedule is None:
        warning = "Unable to allocate all subjects for all departments within the given date range."
        if provided_end_date:
            return [], subject_names_map, warning
        return [], subject_names_map
    result_schedule.sort()
    # Return shape compatibility:
    # - If caller provided an explicit end_date, return 3-tuple (schedule, subject_names_map, warning)
    # - If caller used old two-arg signature (no end_date), return 2-tuple (schedule, subject_names_map)
    if provided_end_date:
        return result_schedule, subject_names_map, None
    return result_schedule, subject_names_map


def subject_counts_per_department(rows):
    """From rows with department_code, subject_code return dict dept_code -> count."""
    counts = defaultdict(int)
    for r in rows:
        dept = (r.get("department_code") or "").strip().upper()
        subj = (r.get("subject_code") or "").strip().upper()
        if dept and subj:
            counts[dept] += 1
    return dict(counts)
