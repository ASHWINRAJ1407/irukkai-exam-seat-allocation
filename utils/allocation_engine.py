"""Seat allocation engine - strict two-dept pairing, saturation, and overflow rules."""
from collections import defaultdict
from math import ceil

# Historical default layout: 15 benches × 3 positions = 45 seats.
TARGET_CAPACITY = 45


def allocate_seats(students_by_dept_subject, halls, capacity_per_bench=3, benches_per_hall=15, target_capacity=None, subject_names_map=None):
    """
    Allocate students to halls with strict rules:

    1. Saturation: Fill each room up to its capacity (default 45) before moving to next;
       no empty seats except last overflow.
    2. Two-Dept Pairing: Select exactly two departments per room; balance ratio (e.g. 23+22).
       Exhaustion: If second dept runs out, immediately add third dept to fill remaining seats.
    3. Anti-Single Department: Every room must have at least two distinct departments.
    4. Malpractice: No two students with same subject_name adjacent on same bench (A-B-A alternating pattern).
       Uses subject_name for conflict checking instead of subject_code.
    5. Overflow: Combine all leftover students into final hall(s); anti-single-dept still applies.

    Notes on flexibility:
    - For traditional 45-capacity halls, we preserve the historic 15×3 bench layout.
    - For halls with capacity != 45, we dynamically increase/decrease the number of benches
      so that benches_per_hall is effectively ceil(capacity / students_per_bench), while
      still respecting the same adjacency rules on each bench row.

    students_by_dept_subject: { (dept_id, subject_id): [Student, ...] }
    halls: [ExamHall, ...]
    subject_names_map: optional dict {subject_id: subject_name} for adjacency conflict checking.
    Returns: list of (hall_id, bench, position, student_tuple)
    """
    STUDS_PER_BENCH = capacity_per_bench

    # Build mutable queues per (dept, subject) - we pop from these
    pools = {}
    dept_totals = defaultdict(int)
    for (dept_id, subj_id), students in students_by_dept_subject.items():
        # Include subject_name in tuple for later reference
        subj_name = subject_names_map.get(subj_id, str(subj_id)) if subject_names_map else str(subj_id)
        tuples = [(s.id, s.roll_number, s.name, dept_id, subj_id, subj_name) for s in students]
        pools[(dept_id, subj_id)] = list(tuples)
        dept_totals[dept_id] += len(students)

    keys_by_dept = defaultdict(list)
    for (dept_id, subj_id) in pools.keys():
        keys_by_dept[dept_id].append((dept_id, subj_id))

    all_depts = sorted(dept_totals.keys(), key=lambda d: dept_totals[d], reverse=True)
    dominant_dept = all_depts[0] if all_depts else None
    smaller_depts = all_depts[1:] if len(all_depts) > 1 else []

    def count_remaining():
        return sum(len(q) for q in pools.values())

    def get_dept_remaining(dept_id):
        return sum(len(pools.get(k, [])) for k in keys_by_dept.get(dept_id, []))

    def subject_conflict_in_hall(hall_subject_dept, dept_id, subj_id):
        """Check if this subject is already assigned to a different dept in this hall."""
        if subj_id not in hall_subject_dept:
            return False
        return hall_subject_dept[subj_id] != dept_id

    def get_adjacent_same_subject_name(hall_matrix, subj_name, bench, pos):
        """
        Check if any adjacent seat has a student with the SAME subject_name.
        hall_matrix contains (bench, pos) -> (dept_id, subj_id, subj_name) tuples.
        """
        adj = []
        if pos == 1:
            adj.append((bench, 2))
        elif pos == 2:
            adj.extend([(bench, 1), (bench, 3)])
        else:  # pos == 3
            adj.append((bench, 2))
        for (b, p) in adj:
            if (b, p) in hall_matrix:
                _, _, adj_subj_name = hall_matrix[(b, p)]
                if adj_subj_name == subj_name:
                    return True
        return False

    def find_valid_seat(hall_matrix, subj_name, benches_count):
        """Find a valid seat where no adjacent seat has the same subject_name."""
        used = set(hall_matrix.keys())
        for b in range(1, benches_count + 1):
            for p in range(1, STUDS_PER_BENCH + 1):
                if (b, p) not in used and not get_adjacent_same_subject_name(hall_matrix, subj_name, b, p):
                    return b, p
        return None

    def pop_student(dept_id, subj_id):
        key = (dept_id, subj_id)
        if key not in pools or not pools[key]:
            return None
        return pools[key].pop(0)

    def get_keys_for_depts(allowed_depts):
        result = []
        for d in allowed_depts:
            for k in keys_by_dept.get(d, []):
                if pools.get(k):
                    result.append(k)
        return result

    halls_sorted = sorted(halls, key=lambda h: (h.hall_number or str(h.id)))
    allocations = []
    hall_seats = {}
    hall_matrix = {}
    dominant_pair_idx = 0

    # Phase 1: Two-dept paired halls - fill each towards its target capacity
    hall_idx = 0
    while hall_idx < len(halls_sorted) and count_remaining() > 0:
        hall = halls_sorted[hall_idx]
        hid = hall.id
        # Compute effective capacity and benches per hall.
        hall_capacity = getattr(hall, "capacity", TARGET_CAPACITY) or TARGET_CAPACITY
        # Historical behaviour: for 45-seat halls we keep exactly 15 benches.
        if hall_capacity == TARGET_CAPACITY:
            benches_for_hall = benches_per_hall
        else:
            benches_for_hall = max(1, ceil(hall_capacity / STUDS_PER_BENCH))
        capacity = hall_capacity
        # Optional global cap (kept for backward compatibility). In the new flow we normally
        # call allocate_seats without a target_capacity so each hall can use its full capacity.
        if target_capacity is not None:
            capacity = min(capacity, target_capacity)
        target = capacity
        hall_seats[hid] = []
        hall_matrix[hid] = {}
        hall_subject_dept = {}

        # Select two departments for this room (load balancing: dominant + smaller in rotation)
        depts_with_students = [d for d in all_depts if get_dept_remaining(d) > 0]
        if len(depts_with_students) < 2:
            break

        if dominant_dept and dominant_dept in depts_with_students and smaller_depts:
            smaller_with_students = [d for d in smaller_depts if get_dept_remaining(d) > 0]
            if smaller_with_students:
                idx = dominant_pair_idx % len(smaller_with_students)
                dept_b = smaller_with_students[idx]
                dept_a = dominant_dept
                allowed = {dept_a, dept_b}
                dominant_pair_idx += 1
            else:
                allowed = set(depts_with_students[:2])
        else:
            allowed = set(depts_with_students[:2])

        placed_this_round = True
        while len(hall_matrix[hid]) < target and (placed_this_round or count_remaining() > 0):
            placed_this_round = False
            keys = get_keys_for_depts(allowed)

            # Ratio / alternating: round-robin between primary depts (A-B-A pattern)
            dept_order = sorted(allowed)
            if len(dept_order) >= 2:
                n_placed = len(hall_matrix[hid])
                next_dept = dept_order[n_placed % 2]
                keys_primary = [k for k in keys if k[0] == next_dept]
                keys_other = [k for k in keys if k[0] != next_dept]
                keys = keys_primary + keys_other

            for (dept_id, subj_id) in keys:
                if subject_conflict_in_hall(hall_subject_dept, dept_id, subj_id):
                    continue
                stu = pop_student(dept_id, subj_id)
                if stu is None:
                    continue
                # stu = (st_id, roll, name, dept_id, subj_id, subj_name)
                subj_name = stu[5] if len(stu) > 5 else str(subj_id)
                seat = find_valid_seat(hall_matrix[hid], subj_name, benches_for_hall)
                if seat:
                    bench, pos = seat
                    allocations.append((hid, bench, pos, stu))
                    hall_seats[hid].append((bench, pos))
                    # Store (dept_id, subj_id, subj_name) in hall_matrix for adjacency checks
                    hall_matrix[hid][(bench, pos)] = (dept_id, subj_id, subj_name)
                    if subj_id not in hall_subject_dept:
                        hall_subject_dept[subj_id] = dept_id
                    placed_this_round = True
                    break
                else:
                    pools[(dept_id, subj_id)].insert(0, stu)

            if not placed_this_round and len(hall_matrix[hid]) < target:
                # Exhaustion: add another dept to fill remaining seats
                remaining_depts = [d for d in all_depts if get_dept_remaining(d) > 0 and d not in allowed]
                for d in remaining_depts:
                    d_keys = [k for k in keys_by_dept.get(d, []) if pools.get(k)]
                    if not d_keys:
                        continue
                    can_add = False
                    for (dept_id, subj_id) in d_keys:
                        if not subject_conflict_in_hall(hall_subject_dept, dept_id, subj_id):
                            can_add = True
                            break
                    if can_add:
                        allowed.add(d)
                        placed_this_round = True
                        break
                if not placed_this_round:
                    break

        hall_idx += 1

    # Phase 2: Overflow - remaining students into final hall(s)
    while hall_idx < len(halls_sorted) and count_remaining() > 0:
        hall = halls_sorted[hall_idx]
        hid = hall.id
        hall_capacity = getattr(hall, "capacity", TARGET_CAPACITY) or TARGET_CAPACITY
        if hall_capacity == TARGET_CAPACITY:
            benches_for_hall = benches_per_hall
        else:
            benches_for_hall = max(1, ceil(hall_capacity / STUDS_PER_BENCH))
        capacity = hall_capacity
        if target_capacity is not None:
            capacity = min(capacity, target_capacity)
        if hid not in hall_matrix:
            hall_matrix[hid] = {}
            hall_seats[hid] = []
        hall_subject_dept = {}
        for (b, p), entry in hall_matrix[hid].items():
            # Handle both old format (d, s) and new format (d, s, s_name)
            if len(entry) == 3:
                d, s, _ = entry
            else:
                d, s = entry
            hall_subject_dept[s] = d

        depts_with_students = [d for d in all_depts if get_dept_remaining(d) > 0]
        if len(depts_with_students) < 2:
            break

        allowed = set(depts_with_students)
        placed_this_round = True
        while count_remaining() > 0 and placed_this_round:
            placed_this_round = False
            keys = get_keys_for_depts(allowed)
            for (dept_id, subj_id) in keys:
                if subject_conflict_in_hall(hall_subject_dept, dept_id, subj_id):
                    continue
                stu = pop_student(dept_id, subj_id)
                if stu is None:
                    continue
                # stu = (st_id, roll, name, dept_id, subj_id, subj_name)
                subj_name = stu[5] if len(stu) > 5 else str(subj_id)
                seat = find_valid_seat(hall_matrix[hid], subj_name, benches_for_hall)
                if seat:
                    bench, pos = seat
                    allocations.append((hid, bench, pos, stu))
                    hall_seats[hid].append((bench, pos))
                    # Store (dept_id, subj_id, subj_name) in hall_matrix for adjacency checks
                    hall_matrix[hid][(bench, pos)] = (dept_id, subj_id, subj_name)
                    if subj_id not in hall_subject_dept:
                        hall_subject_dept[subj_id] = dept_id
                    placed_this_round = True
                    break
                else:
                    pools[(dept_id, subj_id)].insert(0, stu)

        hall_idx += 1

    for h in halls_sorted:
        if h.id not in hall_seats:
            hall_seats[h.id] = []
        if h.id not in hall_matrix:
            hall_matrix[h.id] = {}

    return allocations, halls_sorted, hall_matrix, hall_seats
