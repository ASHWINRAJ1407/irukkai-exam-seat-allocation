"""Seat allocation routes."""
from datetime import date
from io import BytesIO
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from models import (db, Exam, ExamSchedule, ExamHall, Student, Department, Subject, SeatAllocation)
from collections import defaultdict
from math import ceil
from utils.allocation_engine import allocate_seats
from utils.subscription import record_usage
from utils.pdf_generator import (
    create_overall_allocation_pdf,
    create_classroom_allocation_pdf,
    create_attendance_sheet_pdf,
)
from utils.word_generator import create_overall_allocation_docx
from config import Config

allocation_bp = Blueprint('allocation', __name__)


def get_exams_by_date():
    """Get exams grouped by date with stats for the current user."""
    today = date.today()
    schedules = (
        ExamSchedule.query
        .filter(ExamSchedule.exam_date >= today, ExamSchedule.owner_user_id == current_user.id)
        .order_by(ExamSchedule.exam_date)
        .all()
    )
    exam_ids = list({s.exam_id for s in schedules})
    exams = {
        e.id: e
        for e in Exam.query.filter(Exam.id.in_(exam_ids), Exam.owner_user_id == current_user.id).all()
    } if exam_ids else {}

    by_date = defaultdict(list)
    for s in schedules:
        exam = exams.get(s.exam_id)
        if exam:
            by_date[(str(s.exam_date), exam.id, exam.name)].append(s)

    result = []
    for (d, exam_id, exam_name), scheds in sorted(by_date.items(), key=lambda x: x[0][0]):
        dept_ids = list({s.department_id for s in scheds})
        years = [s.academic_year for s in scheds]
        students = Student.query.filter(
            Student.department_id.in_(dept_ids),
            Student.academic_year.in_(years),
            Student.owner_user_id == current_user.id,
        ).all()
        total_students = len(students)
        halls = ExamHall.query.filter(ExamHall.owner_user_id == current_user.id).all()
        total_seats = sum(h.capacity for h in halls)
        rooms_allocated = len(halls)
        required_rooms = ceil(total_students / Config.DEFAULT_HALL_CAPACITY) if total_students else 0
        rooms_needed_for_allocation = max(required_rooms - rooms_allocated, 0)
        required_seats = max(total_students - total_seats, 0)
        result.append({
            'exam_id': exam_id,
            'exam_name': exam_name,
            'exam_date': d,
            'departments_count': len(dept_ids),
            'total_students': total_students,
            'available_seats': total_seats,
            'rooms_allocated': rooms_allocated,
            'required_rooms': required_rooms,
            'rooms_needed_for_allocation': rooms_needed_for_allocation,
            'required_seats': required_seats,
            'schedules': scheds,
        })
    return result
def run_allocation(exam_id, exam_date_str):
    """Generate seat allocation for given exam and date for the current user."""
    from datetime import datetime
    exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
    schedules = (
        ExamSchedule.query
        .filter_by(exam_id=exam_id, exam_date=exam_date)
        .filter(ExamSchedule.owner_user_id == current_user.id)
        .all()
    )
    if not schedules:
        return None, 'No schedules found for this date.'

    halls = ExamHall.query.order_by(ExamHall.hall_number).filter(ExamHall.owner_user_id == current_user.id).all()
    if not halls:
        return None, 'No exam halls configured.'

    dept_ids = {s.department_id for s in schedules}
    years = {s.academic_year for s in schedules}
    students_for_exam = Student.query.filter(
        Student.department_id.in_(list(dept_ids)),
        Student.academic_year.in_(list(years)),
        Student.owner_user_id == current_user.id,
    ).all()
    total_students = len(students_for_exam)
    total_seats = sum(h.capacity for h in halls)
    if total_students > total_seats:
        missing = total_students - total_seats
        return None, f'Not enough seats configured across exam halls. You need {missing} more seat(s) to run allocation.'

    subj_dept_map = defaultdict(set)
    for s in schedules:
        subj_dept_map[s.subject_id].add(s.department_id)
    conflict_subjects = [sid for sid, depts in subj_dept_map.items() if len(depts) >= 3]
    if conflict_subjects:
        flash(
            'Some subjects are shared by three or more departments on this date. '
            'For completely conflict-free rooms, consider adjusting the timetable.',
            'warning',
        )

    # Build subject_names_map for allocation engine
    subject_ids = set(s.subject_id for s in schedules)
    subjects = Subject.query.filter(
        Subject.id.in_(list(subject_ids)),
        Subject.owner_user_id == current_user.id,
    ).all() if subject_ids else []
    subject_names_map = {s.id: s.name for s in subjects}

    students_by_dept_subj = defaultdict(list)
    for s in schedules:
        students = Student.query.filter(
            Student.department_id == s.department_id,
            Student.academic_year == s.academic_year,
            Student.owner_user_id == current_user.id,
        ).all()
        key = (s.department_id, s.subject_id)
        students_by_dept_subj[key].extend(students)

    if not students_by_dept_subj:
        return None, 'No students found for the scheduled departments.'

    allocations, halls_sorted, hall_matrix, hall_seats = allocate_seats(
        students_by_dept_subj,
        halls,
        capacity_per_bench=Config.STUDENTS_PER_BENCH,
        benches_per_hall=Config.BENCHES_PER_HALL,
        target_capacity=None,
        subject_names_map=subject_names_map,
    )

    exam = Exam.query.get(exam_id)
    if not exam or exam.owner_user_id != current_user.id:
        return None, 'You are not allowed to run allocation for this exam.'

    SeatAllocation.query.filter_by(exam_id=exam_id, exam_date=exam_date).delete()

    for (hall_id, bench, pos, stu_tuple) in allocations:
        # stu_tuple = (st_id, roll, name, dept_id, subj_id, subj_name)
        st_id, roll, name, dept_id, subj_id = stu_tuple[:5]
        sa = SeatAllocation(
            exam_id=exam_id,
            exam_date=exam_date,
            hall_id=hall_id,
            department_id=dept_id,
            subject_id=subj_id,
            student_id=st_id,
            bench_number=bench,
            position=pos,
            owner_user_id=current_user.id,
        )
        db.session.add(sa)
    db.session.commit()

    hall_info_map = {}
    for h in halls_sorted:
        hall_info_map[h.id] = {
            'id': h.id, 'hall_number': h.hall_number,
            'capacity': h.capacity, 'building_name': h.building_name or '',
            'floor': h.floor or '', 'allocations': [], 'seats': [], 'students': [],
            'subject_code_summary': {}  # For group-by summary by subject_code
        }

    for (hall_id, bench, pos, stu_tuple) in allocations:
        # stu_tuple = (st_id, roll, name, dept_id, subj_id, subj_name)
        st_id, roll, name, dept_id, subj_id = stu_tuple[:5]
        subj_name = stu_tuple[5] if len(stu_tuple) > 5 else ''
        dept = Department.query.get(dept_id)
        subj = Subject.query.get(subj_id)
        info = hall_info_map[hall_id]
        info['seats'].append((bench, pos, roll))
        info['students'].append({'roll_number': roll, 'name': name, 'subject_code': subj.code if subj else '', 'subject_name': subj.name if subj else ''})
        
        # Group by (department_code, subject_code) for allocation breakdown
        key = (dept.code if dept else '', subj.code if subj else '')
        existing = next((a for a in info['allocations'] if (a.get('department_code') == key[0] and a.get('subject_code') == key[1])), None)
        if existing:
            existing['count'] += 1
            existing['roll_numbers'].append(roll)
        else:
            info['allocations'].append({
                'department_code': key[0], 'dept_name': dept.name if dept else '',
                'subject_code': key[1], 'subject_name': subj.name if subj else '',
                'count': 1, 'roll_numbers': [roll]
            })
        
        # Track subject_code counts for attendance summary
        if key[1]:  # subject_code
            if key[1] not in info['subject_code_summary']:
                info['subject_code_summary'][key[1]] = 0
            info['subject_code_summary'][key[1]] += 1

    for a in hall_info_map.values():
        for al in a['allocations']:
            rn = al.get('roll_numbers', [])
            if rn:
                rn_sorted = sorted(rn, key=lambda x: (len(x), x))
                al['roll_range'] = f"{min(rn_sorted)} - {max(rn_sorted)}" if len(rn_sorted) > 1 else str(rn_sorted[0])

    return list(hall_info_map.values()), None


@allocation_bp.route('/')
@login_required
def index():
    daily_exams = get_exams_by_date()
    return render_template('allocation/index.html', daily_exams=daily_exams)


def _parse_exam_date(d):
    from datetime import datetime
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d), '%Y-%m-%d').date()


@allocation_bp.route('/view/<int:exam_id>/<exam_date>')
@login_required
def view(exam_id, exam_date):
    exam = Exam.query.get_or_404(exam_id)
    if exam.owner_user_id != current_user.id:
        flash('You are not allowed to view allocation for this exam.', 'danger')
        return redirect(url_for('allocation.index'))
    exam_date_obj = _parse_exam_date(exam_date)
    allocations = SeatAllocation.query.filter_by(
        exam_id=exam_id, exam_date=exam_date_obj
    ).all()
    if not allocations:
        hall_info, err = run_allocation(exam_id, str(exam_date_obj))
        if err:
            flash(err, 'danger')
            return redirect(url_for('allocation.index'))
    else:
        hall_info = []
        hall_ids = list({a.hall_id for a in allocations})
        halls = {h.id: h for h in ExamHall.query.filter(ExamHall.id.in_(hall_ids), ExamHall.owner_user_id == current_user.id).all()}
        for hid in hall_ids:
            h = halls.get(hid)
            if not h:
                continue
            hall_alloc = [a for a in allocations if a.hall_id == hid]
            dept_groups = defaultdict(list)
            for a in hall_alloc:
                dept_groups[(a.department_id, a.subject_id)].append(a)
            alloc_list = []
            for (dept_id, subj_id), allocs in dept_groups.items():
                dept = Department.query.get(dept_id)
                subj = Subject.query.get(subj_id)
                rolls = [a.student.roll_number for a in allocs if a.student]
                alloc_list.append({
                    'department_code': dept.code if dept else '',
                    'subject_code': subj.code if subj else '',
                    'count': len(allocs),
                    'roll_range': f"{min(rolls)} - {max(rolls)}" if len(rolls) > 1 else (rolls[0] if rolls else '')
                })
            seats_raw = [(a.bench_number, a.position, a.student.roll_number if a.student else '') for a in hall_alloc]
            seat_grid = {}
            for bench, pos, roll in seats_raw:
                if bench not in seat_grid:
                    seat_grid[bench] = {1: '', 2: '', 3: ''}
                seat_grid[bench][pos] = roll
            seat_rows = [(b, seat_grid[b].get(1,''), seat_grid[b].get(2,''), seat_grid[b].get(3,'')) for b in sorted(seat_grid.keys())]
            seats_for_pdf = [(b, pos, roll) for b, row in seat_grid.items() for pos, roll in row.items() if roll]
            students = [{'roll_number': a.student.roll_number, 'name': a.student.name} for a in hall_alloc if a.student]
            hall_info.append({
                'hall_number': h.hall_number,
                'capacity': h.capacity,
                'building_name': h.building_name or '',
                'floor': h.floor or '',
                'allocations': alloc_list,
                'seat_rows': seat_rows,
                'seats': seats_for_pdf,
                'students': students,
            })
    return render_template('allocation/view.html', exam=exam, exam_date=exam_date, hall_info=hall_info)


@allocation_bp.route('/generate/<int:exam_id>/<exam_date>')
@login_required
def generate(exam_id, exam_date):
    exam = Exam.query.get_or_404(exam_id)
    if exam.owner_user_id != current_user.id:
        flash('You are not allowed to generate allocation for this exam.', 'danger')
        return redirect(url_for('allocation.index'))
    exam_date_obj = _parse_exam_date(exam_date)
    allocations = SeatAllocation.query.filter_by(
        exam_id=exam_id, exam_date=exam_date_obj
    ).all()
    # No subscription enforcement: allow generation for authenticated users.
    if not allocations:
        hall_info, err = run_allocation(exam_id, str(exam_date_obj))
        if err:
            flash(err, 'danger')
            return redirect(url_for('allocation.index'))
        # Skip unallocated halls in downloads
        hall_info = [h for h in hall_info if h.get('seats')]
    else:
        hall_ids = list({a.hall_id for a in allocations})
        halls = {h.id: h for h in ExamHall.query.filter(ExamHall.id.in_(hall_ids), ExamHall.owner_user_id == current_user.id).all()}
        hall_info = []
        for hid in hall_ids:
            h = halls.get(hid)
            hall_alloc = [a for a in allocations if a.hall_id == hid]
            dept_groups = defaultdict(list)
            for a in hall_alloc:
                dept_groups[(a.department_id, a.subject_id)].append(a)
            alloc_list = []
            for (dept_id, subj_id), allocs in dept_groups.items():
                dept = Department.query.get(dept_id)
                subj = Subject.query.get(subj_id)
                rolls = [a.student.roll_number for a in allocs if a.student]
                alloc_list.append({
                    'department_code': dept.code if dept else '',
                    'subject_code': subj.code if subj else '',
                    'count': len(allocs),
                    'roll_range': f"{min(rolls)} - {max(rolls)}" if len(rolls) > 1 else (rolls[0] if rolls else ''),
                    'roll_numbers': rolls
                })
            seats = [(a.bench_number, a.position, a.student.roll_number if a.student else '') for a in hall_alloc]
            students = [{'roll_number': a.student.roll_number, 'name': a.student.name} for a in hall_alloc if a.student]
            hall_info.append({
                'hall_number': h.hall_number,
                'capacity': h.capacity,
                'building_name': h.building_name or '',
                'floor': h.floor or '',
                'allocations': alloc_list,
                'seats': seats,
                'students': students,
            })

    from zipfile import ZipFile
    zip_buffer = BytesIO()
    try:
        with ZipFile(zip_buffer, 'w') as zf:
            overall = create_overall_allocation_pdf(hall_info, exam.name, str(exam_date_obj))
            zf.writestr('overall_allocation.pdf', overall.getvalue())
            try:
                overall_docx = create_overall_allocation_docx(hall_info, exam.name, str(exam_date_obj))
                zf.writestr('overall_allocation.docx', overall_docx.getvalue())
            except Exception:
                # If Word generation fails, still provide PDFs and inform the user.
                flash('Word file generation failed. PDF files were generated successfully.', 'warning')
            for hi in hall_info:
                room_pdf = create_classroom_allocation_pdf(hi, exam.name, str(exam_date_obj))
                zf.writestr(f"hall_{hi['hall_number']}_seating.pdf", room_pdf.getvalue())
                att_pdf = create_attendance_sheet_pdf(hi, exam.name, str(exam_date_obj))
                zf.writestr(f"hall_{hi['hall_number']}_attendance.pdf", att_pdf.getvalue())
        zip_buffer.seek(0)
        # Allocation generation counts as one usage event (when successful).
        record_usage(current_user, "allocation")
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'allocation_{exam.name}_{str(exam_date_obj)}.zip'
        )
    except Exception:
        # Catch any unexpected error and avoid showing a raw error page.
        flash('An error occurred while generating the allocation files. Please try again.', 'danger')
        return redirect(url_for('allocation.index'))
