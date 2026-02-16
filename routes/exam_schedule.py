"""Exam schedule management routes."""
from datetime import datetime, date, time
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Exam, ExamSchedule, Department, Subject, SeatAllocation
from utils.excel_parser import parse_schedule_file

exam_schedule_bp = Blueprint('exam_schedule', __name__)

def _parse_time(val):
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    if isinstance(val, time):
        return val
    if isinstance(val, str):
        parts = val.replace('.', ':').split(':')
        try:
            return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            return None
    return None

@exam_schedule_bp.route('/')
@login_required
def index():
    # Always show only exams owned by the logged-in user
    query = Exam.query.order_by(Exam.id.desc()).filter(Exam.owner_user_id == current_user.id)
    exams = query.all()
    return render_template('exam_schedule/index.html', exams=exams)

@exam_schedule_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    dept_q = Department.query.order_by(Department.code).filter(Department.owner_user_id == current_user.id)
    subj_q = Subject.query.order_by(Subject.code).filter(Subject.owner_user_id == current_user.id)
    departments = dept_q.all()
    subjects = subj_q.all()
    if request.method == 'POST':
        exam_name = request.form.get('exam_name', '').strip()
        if not exam_name:
            flash('Exam name is required.', 'danger')
            return render_template('exam_schedule/add.html',
                departments=departments, subjects=subjects)
        # Defaults set from the first entry to reduce repeated typing later.
        exam = Exam(name=exam_name, owner_user_id=current_user.id)
        db.session.add(exam)
        db.session.flush()
        dept_id = request.form.get('department_id')
        subj_id = request.form.get('subject_id')
        date_str = request.form.get('exam_date')
        start = _parse_time(request.form.get('start_time'))
        end = _parse_time(request.form.get('end_time'))
        year = request.form.get('academic_year', '2024-25')
        if dept_id and subj_id and date_str and start and end:
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d').date()
                exam.academic_year = year
                exam.default_start_time = start
                exam.default_end_time = end
                s = ExamSchedule(exam_id=exam.id, department_id=dept_id, subject_id=subj_id,
                    exam_date=d, start_time=start, end_time=end, academic_year=year)
                db.session.add(s)
            except ValueError:
                pass
        db.session.commit()
        flash(f'Exam "{exam_name}" created.', 'success')
        return redirect(url_for('exam_schedule.detail', exam_id=exam.id))
    return render_template('exam_schedule/add.html',
        departments=departments, subjects=subjects)

@exam_schedule_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_schedule():
    if request.method == 'POST':
        exam_name = request.form.get('exam_name', '').strip()
        file = request.files.get('file')
        year = request.form.get('academic_year', '2024-25')
        if not exam_name:
            flash('Exam name is required.', 'danger')
            return render_template('exam_schedule/import.html')
        if not file or file.filename == '':
            flash('Please select a file to upload.', 'danger')
            return render_template('exam_schedule/import.html')
        try:
            content = file.read()
            records = parse_schedule_file(content, file.filename)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('exam_schedule/import.html')
        if not records:
            flash('No valid schedule records found in file.', 'danger')
            return render_template('exam_schedule/import.html')
        # Academic year is entered once; times come from file per-row, but we store defaults
        # from the first valid row to streamline later manual entries.
        exam = Exam(name=exam_name, academic_year=year, owner_user_id=current_user.id)
        db.session.add(exam)
        db.session.flush()
        dept_q = Department.query.filter(Department.owner_user_id == current_user.id)
        subj_q = Subject.query.filter(Subject.owner_user_id == current_user.id)
        dept_map = {d.code.upper(): d.id for d in dept_q.all()}
        subj_map = {s.code.upper(): s.id for s in subj_q.all()}
        added = 0
        first_times_set = False
        for r in records:
            dept_id = dept_map.get(r['department_code'])
            subj_id = subj_map.get(r['subject_code'])
            if not dept_id or not subj_id:
                continue
            if not first_times_set and r.get('start_time') and r.get('end_time'):
                exam.default_start_time = r['start_time']
                exam.default_end_time = r['end_time']
                first_times_set = True
            s = ExamSchedule(
                exam_id=exam.id,
                department_id=dept_id,
                subject_id=subj_id,
                exam_date=r['exam_date'],
                start_time=r['start_time'],
                end_time=r['end_time'],
                academic_year=year,
                owner_user_id=current_user.id,
            )
            db.session.add(s)
            added += 1
        db.session.commit()
        flash(f'Imported {added} schedule entries for "{exam_name}".', 'success')
        return redirect(url_for('exam_schedule.detail', exam_id=exam.id))
    return render_template('exam_schedule/import.html')

@exam_schedule_bp.route('/exam/<int:exam_id>')
@login_required
def detail(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.owner_user_id != current_user.id:
        flash('You are not allowed to view this exam.', 'danger')
        return redirect(url_for('exam_schedule.index'))
    sched_q = ExamSchedule.query.filter_by(exam_id=exam_id).filter(ExamSchedule.owner_user_id == current_user.id).order_by(
        ExamSchedule.exam_date, ExamSchedule.start_time
    )
    schedules = sched_q.all()
    dept_q = Department.query.order_by(Department.code).filter(Department.owner_user_id == current_user.id)
    subj_q = Subject.query.order_by(Subject.code).filter(Subject.owner_user_id == current_user.id)
    departments = dept_q.all()
    subjects = subj_q.all()
    dates_seen = {}
    for s in schedules:
        d = str(s.exam_date)
        if d not in dates_seen:
            dates_seen[d] = []
        dates_seen[d].append(s)
    by_date = [(d, dates_seen[d]) for d in sorted(dates_seen.keys())]
    return render_template('exam_schedule/detail.html', exam=exam,
        schedules=schedules, by_date=by_date, departments=departments, subjects=subjects)

@exam_schedule_bp.route('/clear-entries/<int:exam_id>', methods=['POST'])
@login_required
def clear_entries(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.owner_user_id != current_user.id:
        flash('You are not allowed to clear this exam.', 'danger')
        return redirect(url_for('exam_schedule.index'))
    SeatAllocation.query.filter_by(exam_id=exam_id).delete()
    ExamSchedule.query.filter_by(exam_id=exam_id).delete()
    db.session.commit()
    flash('All schedule entries and allocations for this exam have been cleared. You can add new entries or re-import.', 'warning')
    return redirect(url_for('exam_schedule.detail', exam_id=exam_id))

@exam_schedule_bp.route('/delete-all', methods=['POST'])
@login_required
def delete_all():
    exam_id = request.form.get('exam_id')
    if exam_id:
        exam = Exam.query.get(exam_id)
        if exam and exam.owner_user_id == current_user.id:
            SeatAllocation.query.filter_by(exam_id=exam_id).delete()
            ExamSchedule.query.filter_by(exam_id=exam_id).delete()
            Exam.query.filter_by(id=exam_id).delete()
        db.session.commit()
        flash('Exam and all its schedules have been deleted.', 'warning')
    return redirect(url_for('exam_schedule.index'))

@exam_schedule_bp.route('/add-entry/<int:exam_id>', methods=['POST'])
@login_required
def add_entry(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    if exam.owner_user_id != current_user.id:
        flash('You are not allowed to modify this exam.', 'danger')
        return redirect(url_for('exam_schedule.index'))
    dept_id = request.form.get('department_id')
    subj_id = request.form.get('subject_id')
    date_str = request.form.get('exam_date')
    # After the first entry, we default start/end/year from the exam.
    start = _parse_time(request.form.get('start_time')) or exam.default_start_time
    end = _parse_time(request.form.get('end_time')) or exam.default_end_time
    year = request.form.get('academic_year') or exam.academic_year or '2024-25'

    if dept_id and subj_id and date_str:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
            if not start or not end:
                flash('Start time and end time are required for the first entry.', 'danger')
                return redirect(url_for('exam_schedule.detail', exam_id=exam_id))
            if not exam.academic_year:
                exam.academic_year = year
            if not exam.default_start_time:
                exam.default_start_time = start
            if not exam.default_end_time:
                exam.default_end_time = end
            s = ExamSchedule(
                exam_id=exam_id,
                department_id=dept_id,
                subject_id=subj_id,
                exam_date=d,
                start_time=start,
                end_time=end,
                academic_year=year,
                owner_user_id=current_user.id,
            )
            db.session.add(s)
            db.session.commit()
            flash('Schedule entry added.', 'success')
        except ValueError:
            flash('Invalid date format.', 'danger')
    return redirect(url_for('exam_schedule.detail', exam_id=exam_id))

@exam_schedule_bp.route('/delete-entry/<int:id>', methods=['POST'])
@login_required
def delete_entry(id):
    s = ExamSchedule.query.get_or_404(id)
    exam = Exam.query.get(s.exam_id)
    if exam and exam.owner_user_id != current_user.id:
        flash('You are not allowed to delete this entry.', 'danger')
        return redirect(url_for('exam_schedule.index'))
    exam_id = s.exam_id
    db.session.delete(s)
    db.session.commit()
    flash('Schedule entry deleted.', 'success')
    return redirect(url_for('exam_schedule.detail', exam_id=exam_id))
