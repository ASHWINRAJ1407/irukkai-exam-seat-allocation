"""Exam timetable generation: one exam per department per day, respect exclusions, max 2 depts per subject per day."""
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


def generate_timetable(rows, start_date_str, excluded_dates_str_list):
    """
    rows: list of dicts with keys department_code, subject_code (e.g. from parse_timetable_subjects_file).
    start_date_str: dd/mm/yyyy.
    excluded_dates_str_list: list of dd/mm/yyyy strings (can be empty).
    Returns: (list of (date, dept_code, subject_code), subject_names_map)
    subject_names_map can be filled by caller from DB: { subject_code: name }.
    """
    start_date = _parse_dd_mm_yyyy(start_date_str)
    excluded = set()
    for s in (excluded_dates_str_list or []):
        s = str(s).strip()
        if not s:
            continue
        try:
            excluded.add(_parse_dd_mm_yyyy(s))
        except (ValueError, TypeError):
            pass

    # List of (dept_code, subject_code) to place
    items = [(r["department_code"].upper(), r["subject_code"].upper()) for r in rows if r.get("department_code") and r.get("subject_code")]

    if not items:
        return [], {}

    # Unplaced: list of (dept, subj) still to assign
    unplaced = list(items)
    schedule = []  # (date, dept_code, subject_code)

    # Number of dates we might need: at least max subjects per dept
    dept_counts = defaultdict(int)
    for d, s in items:
        dept_counts[d] += 1
    max_per_dept = max(dept_counts.values()) if dept_counts else 1
    max_dates = max_per_dept * 2 + 30  # safety

    current = start_date
    days_tried = 0
    while unplaced and days_tried < max_dates:
        days_tried += 1
        if current in excluded:
            current += timedelta(days=1)
            continue

        dept_assigned_this_date = set()
        subject_count_this_date = defaultdict(int)

        # Try to assign as many (dept, subj) as possible to current date
        still_unplaced = []
        for (dept, subj) in unplaced:
            if dept in dept_assigned_this_date:
                still_unplaced.append((dept, subj))
                continue
            if subject_count_this_date[subj] >= 2:
                still_unplaced.append((dept, subj))
                continue
            schedule.append((current, dept, subj))
            dept_assigned_this_date.add(dept)
            subject_count_this_date[subj] += 1

        unplaced = still_unplaced
        current += timedelta(days=1)

    return schedule, {}


def subject_counts_per_department(rows):
    """From rows with department_code, subject_code return dict dept_code -> count."""
    counts = defaultdict(int)
    for r in rows:
        dept = (r.get("department_code") or "").strip().upper()
        subj = (r.get("subject_code") or "").strip().upper()
        if dept and subj:
            counts[dept] += 1
    return dict(counts)
