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


def generate_timetable(rows, start_date_str, excluded_dates_str_list, subject_names_map=None):
    """
    rows: list of dicts with keys department_code, subject_code, subject_name (e.g. from parse_timetable_subjects_file).
    start_date_str: dd/mm/yyyy.
    excluded_dates_str_list: list of dd/mm/yyyy strings (can be empty).
    subject_names_map: optional dict {subject_code: subject_name} for name resolution.
    Returns: (list of (date, dept_code, subject_code, subject_name), subject_names_map)
    
    Logic:
    - Use a Global Subject Name Counter per date to limit subject names to 2 departments max.
    - If a third dept attempts same subject_name, trigger Recursive Shuffle for that dept's subject.
    - NEW: Timetable Compaction & Gap-Filling using Backtracking:
      * Scans for earlier gaps (empty slots for a department on earlier dates)
      * Attempts to backfill gaps with remaining subjects (look-ahead)
      * Smart shuffling if current subject conflicts on gap-date
      * Only creates new dates if no gap can be filled
      * Optimizes for minimal exam days
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

    # Build subject_code -> subject_name map from rows or use provided map
    names_from_rows = {}
    for r in rows:
        code = (r.get("subject_code") or "").upper().strip()
        name = (r.get("subject_name") or "").strip()
        if code and name:
            names_from_rows[code] = name
    
    if subject_names_map is None:
        subject_names_map = names_from_rows
    else:
        # Merge provided map with names from rows
        for code, name in names_from_rows.items():
            if code not in subject_names_map:
                subject_names_map[code] = name

    # List of (dept_code, subject_code) to place
    items = [(r["department_code"].upper(), r["subject_code"].upper()) for r in rows if r.get("department_code") and r.get("subject_code")]

    if not items:
        return [], subject_names_map

    # Unplaced: list of (dept, subj_code) still to assign
    unplaced = list(items)
    schedule = []  # (date, dept_code, subject_code, subject_name)

    # Number of dates we might need: at least max subjects per dept
    dept_counts = defaultdict(int)
    for d, s in items:
        dept_counts[d] += 1
    max_per_dept = max(dept_counts.values()) if dept_counts else 1
    max_dates = max_per_dept * 2 + 30  # safety

    def get_subject_name(subject_code):
        """Resolve subject name from map."""
        return subject_names_map.get(subject_code, subject_code)

    def find_gaps_for_department(dept_code, current_date):
        """
        Find all earlier dates where this department has NO exam yet (gaps).
        Returns: list of gap_date objects (sorted chronologically first to last).
        """
        dates_with_dept = set()
        for (date_val, dept, subj_code, subj_name) in schedule:
            if dept == dept_code:
                dates_with_dept.add(date_val)
        
        # Scan backwards from current_date-1 to find gaps
        gaps = []
        if dates_with_dept:
            earliest_dept_date = min(dates_with_dept)
            temp_date = current_date - timedelta(days=1)
            while temp_date >= earliest_dept_date:
                if temp_date not in dates_with_dept:
                    gaps.append(temp_date)
                temp_date -= timedelta(days=1)
        
        return sorted(gaps)  # Sort chronologically (earliest first)

    def count_subject_names_on_date(date_val):
        """
        Returns dict {subject_name: count} of how many depts scheduled on this date.
        """
        counts = defaultdict(int)
        for (d, dept, subj_code, subj_name) in schedule:
            if d == date_val:
                counts[subj_name] += 1
        return counts

    def get_remaining_subjects_for_dept(dept_code):
        """
        Returns list of subject_codes for this department in unplaced list.
        """
        return [subj_code for (d, subj_code) in unplaced if d == dept_code]

    def can_fit_subject_in_gap(subj_code, subj_name, gap_date):
        """
        Check if a subject can fit on a gap date.
        Rules:
        - Subject name must not already have 2+ depts on this date.
        Returns: bool (True = can fit)
        """
        subject_name_counts = count_subject_names_on_date(gap_date)
        return subject_name_counts.get(subj_name, 0) < 2

    def backfill_gaps(current_date):
        """
        Attempt to backfill gaps on earlier dates with remaining unplaced subjects.
        
        Scans all departments' unplaced subjects and tries to fit them on earlier gap dates.
        Uses smart shuffling if conflicts occur.
        
        Returns: backfilled_count (how many subjects were backfilled)
        """
        nonlocal unplaced
        
        backfilled = []
        still_unplaced = list(unplaced)
        
        # Group unplaced by department
        depts_with_unplaced = {}
        for (dept, subj_code) in still_unplaced:
            if dept not in depts_with_unplaced:
                depts_with_unplaced[dept] = []
            depts_with_unplaced[dept].append(subj_code)
        
        # For each department, try to backfill their gaps
        for dept_code in depts_with_unplaced:
            department_subjects = depts_with_unplaced[dept_code]
            gaps = find_gaps_for_department(dept_code, current_date)
            
            for gap_date in gaps:
                still_subject_list = [s for s in department_subjects if s not in backfilled]
                if not still_subject_list:
                    continue
                
                # Try to fit a subject on this gap date
                subject_placed = False
                for attempt_subj_code in still_subject_list:
                    subj_name = get_subject_name(attempt_subj_code)
                    
                    if can_fit_subject_in_gap(attempt_subj_code, subj_name, gap_date):
                        # Fits! Add to schedule and mark as backfilled
                        schedule.append((gap_date, dept_code, attempt_subj_code, subj_name))
                        backfilled.append(attempt_subj_code)
                        subject_placed = True
                        break  # Found a subject for this gap, move to next gap
                
                if not subject_placed:
                    # Subject conflicts; try shuffling with another subject from same dept
                    remaining_in_dept = get_remaining_subjects_for_dept(dept_code)
                    remaining_in_dept = [s for s in remaining_in_dept if s not in backfilled]
                    
                    if remaining_in_dept:
                        # Try picking a different subject via shuffle logic
                        subject_name_counts_gap = count_subject_names_on_date(gap_date)
                        alternate = shuffle_and_pick_subject(
                            dept_code, remaining_in_dept[0], gap_date, subject_name_counts_gap, set()
                        )
                        if alternate:
                            alt_name = get_subject_name(alternate)
                            if can_fit_subject_in_gap(alternate, alt_name, gap_date):
                                schedule.append((gap_date, dept_code, alternate, alt_name))
                                backfilled.append(alternate)
        
        # Remove backfilled subjects from unplaced
        unplaced = [(d, s) for (d, s) in still_unplaced if s not in backfilled]
        return len(backfilled)

    def shuffle_and_pick_subject(dept, subject_code, date_obj, subject_name_counts, excluded_code_set):
        """
        Recursive Shuffle: try to find an alternative subject for this dept on this date
        that doesn't conflict (subject_name count < 2).
        Returns: (dept, new_subject_code) or None if no valid subject found.
        """
        # Collect all subjects available for this dept (from unplaced items)
        available_subjects = set()
        for d, s in unplaced:
            if d == dept:
                available_subjects.add(s)
        
        # Try to find a subject not already scheduled for this dept on this date,
        # and whose subject_name has count < 2 on this date
        for alt_code in sorted(available_subjects):
            if alt_code == subject_code or alt_code in excluded_code_set:
                continue
            alt_name = get_subject_name(alt_code)
            if subject_name_counts.get(alt_name, 0) < 2:
                return alt_code
        
        # No alternative found; return None
        return None

    current = start_date
    days_tried = 0
    while unplaced and days_tried < max_dates:
        days_tried += 1
        if current in excluded:
            current += timedelta(days=1)
            continue

        # STEP 1: Attempt to backfill gaps on earlier dates
        # This prioritizes filling existing gaps over creating new dates
        backfilled_count = backfill_gaps(current)
        
        if unplaced:  # If still unplaced after backfilling, schedule on current date
            dept_assigned_this_date = set()
            subject_name_counts_this_date = defaultdict(int)  # subject_name -> count
            scheduled_codes_this_date = set()  # subject codes already scheduled

            # Try to assign as many (dept, subj_code) as possible to current date
            still_unplaced = []
            for (dept, subj_code) in unplaced:
                if dept in dept_assigned_this_date:
                    still_unplaced.append((dept, subj_code))
                    continue
                
                subj_name = get_subject_name(subj_code)
                
                # Check if this subject_name already has 2 depts on this date
                if subject_name_counts_this_date[subj_name] >= 2:
                    # Trigger Recursive Shuffle to pick an alternative subject for this dept
                    alt_code = shuffle_and_pick_subject(
                        dept, subj_code, current, subject_name_counts_this_date, scheduled_codes_this_date
                    )
                    if alt_code is not None:
                        # Use the alternative subject
                        subj_code = alt_code
                        subj_name = get_subject_name(alt_code)
                    else:
                        # No alternative found; defer this dept to next date
                        still_unplaced.append((dept, subj_code))
                        continue
                
                # Assign this (dept, subj_code) to current date
                schedule.append((current, dept, subj_code, subj_name))
                dept_assigned_this_date.add(dept)
                subject_name_counts_this_date[subj_name] += 1
                scheduled_codes_this_date.add(subj_code)

            unplaced = still_unplaced
        
        current += timedelta(days=1)

    return schedule, subject_names_map


def subject_counts_per_department(rows):
    """From rows with department_code, subject_code return dict dept_code -> count."""
    counts = defaultdict(int)
    for r in rows:
        dept = (r.get("department_code") or "").strip().upper()
        subj = (r.get("subject_code") or "").strip().upper()
        if dept and subj:
            counts[dept] += 1
    return dict(counts)
