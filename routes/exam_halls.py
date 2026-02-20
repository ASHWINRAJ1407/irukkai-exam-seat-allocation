"""Exam hall management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models import db, ExamHall, Exam, ExamSchedule, Student
from config import Config
from utils.excel_parser import parse_halls_file

exam_halls_bp = Blueprint('exam_halls', __name__)


@exam_halls_bp.route('/')
@login_required
def index():
    """List exam halls for the current user."""
    query = ExamHall.query.order_by(ExamHall.hall_number).filter(ExamHall.owner_user_id == current_user.id)
    halls = query.all()
    total_seats = sum(h.capacity for h in halls)

    # Determine if capacity is already tight for any upcoming exam date
    # Using the same default capacity assumption as allocation summary.
    from datetime import date
    from math import ceil

    capacity_warning = False
    if halls:
        today = date.today()
        schedules = ExamSchedule.query.filter(ExamSchedule.exam_date >= today, ExamSchedule.owner_user_id == current_user.id).all()
        if schedules:
            exam_ids = {s.exam_id for s in schedules}
            exams = {e.id: e for e in Exam.query.filter(Exam.id.in_(exam_ids), Exam.owner_user_id == current_user.id).all()}
            # Group schedules per (date, exam)
            grouped = {}
            for s in schedules:
                exam = exams.get(s.exam_id)
                if not exam:
                    continue
                key = (s.exam_date, s.exam_id)
                grouped.setdefault(key, []).append(s)

            for (_d, _exam_id), scheds in grouped.items():
                dept_ids = {s.department_id for s in scheds}
                years = {s.academic_year for s in scheds}
                students = Student.query.filter(
                    Student.department_id.in_(dept_ids),
                    Student.academic_year.in_(list(years)),
                    Student.owner_user_id == current_user.id,
                ).all()
                total_students = len(students)
                if total_students == 0:
                    continue
                rooms_allocated = len(halls)
                required_rooms = ceil(total_students / Config.DEFAULT_HALL_CAPACITY)
                if rooms_allocated <= required_rooms:
                    capacity_warning = True
                    break

    return render_template(
        'exam_halls/index.html',
        halls=halls,
        total_seats=total_seats,
        capacity_warning=capacity_warning,
    )

@exam_halls_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        hall_number = request.form.get('hall_number', '').strip()
        capacity = request.form.get('capacity', Config.DEFAULT_HALL_CAPACITY)
        building = request.form.get('building_name', '').strip() or 'Main Building'
        floor = request.form.get('floor', '').strip() or 'Ground'
        try:
            capacity = int(capacity)
        except ValueError:
            capacity = Config.DEFAULT_HALL_CAPACITY
        if not hall_number:
            flash('Hall number is required.', 'danger')
            return render_template('exam_halls/add.html')

        # Check for duplicate hall number only within the current user's data
        existing_q = ExamHall.query.filter_by(
            hall_number=hall_number,
            owner_user_id=current_user.id,
        )
        if existing_q.first():
            flash(f'Hall {hall_number} already exists in your account.', 'danger')
            return render_template('exam_halls/add.html')

        h = ExamHall(
            hall_number=hall_number,
            capacity=capacity,
            building_name=building,
            floor=floor,
            owner_user_id=current_user.id,
        )
        try:
            db.session.add(h)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not save hall because this hall number already exists in your account. '
                'Please choose a different hall number.',
                'danger',
            )
            return render_template('exam_halls/add.html')

        flash(f'Hall {hall_number} added successfully.', 'success')
        return redirect(url_for('exam_halls.index'))
    return render_template('exam_halls/add.html', default_capacity=Config.DEFAULT_HALL_CAPACITY)

@exam_halls_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_halls():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Please select a file to upload.', 'danger')
            return render_template('exam_halls/import.html')
        try:
            content = file.read()
            records = parse_halls_file(content, file.filename)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('exam_halls/import.html')
        added = 0
        skipped = 0
        for r in records:
            existing_q = ExamHall.query.filter_by(
                hall_number=r['hall_number'],
                owner_user_id=current_user.id,
            )
            if existing_q.first():
                skipped += 1
                continue
            h = ExamHall(
                hall_number=r['hall_number'],
                capacity=r['capacity'],
                building_name=r['building_name'],
                floor=r['floor'],
                owner_user_id=current_user.id,
            )
            db.session.add(h)
            added += 1
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Some halls could not be imported because their hall numbers already exist '
                'in your account. Duplicates have been skipped.',
                'warning',
            )
            return redirect(url_for('exam_halls.index'))

        flash(f'Imported {added} halls. Skipped {skipped} duplicates.', 'success')
        return redirect(url_for('exam_halls.index'))
    return render_template('exam_halls/import.html')

@exam_halls_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    hall = ExamHall.query.get_or_404(id)
    if hall.owner_user_id != current_user.id:
        flash('You are not allowed to edit this hall.', 'danger')
        return redirect(url_for('exam_halls.index'))
    if request.method == 'POST':
        hall.hall_number = request.form.get('hall_number', '').strip()
        try:
            hall.capacity = int(request.form.get('capacity', 45))
        except ValueError:
            pass
        hall.building_name = request.form.get('building_name', '').strip() or 'Main Building'
        hall.floor = request.form.get('floor', '').strip() or 'Ground'

        # Ensure the new hall number is not used by any other hall of this user
        existing_q = ExamHall.query.filter(
            ExamHall.owner_user_id == current_user.id,
            ExamHall.hall_number == hall.hall_number,
            ExamHall.id != id,
        )
        if existing_q.first():
            flash(f'Hall number {hall.hall_number} already in use in your account.', 'danger')
            return render_template('exam_halls/edit.html', hall=hall)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not update hall because this hall number already exists in your account. '
                'Please choose a different hall number.',
                'danger',
            )
            return render_template('exam_halls/edit.html', hall=hall)

        flash('Hall updated successfully.', 'success')
        return redirect(url_for('exam_halls.index'))
    return render_template('exam_halls/edit.html', hall=hall)

@exam_halls_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    hall = ExamHall.query.get_or_404(id)
    if hall.owner_user_id != current_user.id:
        flash('You are not allowed to delete this hall.', 'danger')
        return redirect(url_for('exam_halls.index'))
    try:
        db.session.delete(hall)
        db.session.commit()
        flash('Hall deleted.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        # Most likely this hall is referenced in existing allocations.
        flash(
            'This hall could not be deleted because it is already used in seat allocations. '
            'Please clear or regenerate allocations before deleting this hall.',
            'danger',
        )
    return redirect(url_for('exam_halls.index'))


@exam_halls_bp.route('/delete-multiple', methods=['POST'])
@login_required
def delete_multiple():
    """Delete multiple exam halls selected from the list."""
    ids = request.form.getlist('ids')
    if not ids:
        flash('No exam halls selected for deletion.', 'info')
        return redirect(url_for('exam_halls.index'))
    deleted = 0
    failed = 0
    for id_str in ids:
        try:
            hall_id = int(id_str)
        except ValueError:
            continue
        hall = ExamHall.query.get(hall_id)
        if not hall:
            continue
        if hall.owner_user_id != current_user.id:
            failed += 1
            continue
        try:
            db.session.delete(hall)
            deleted += 1
        except SQLAlchemyError:
            db.session.rollback()
            failed += 1
    if deleted:
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            failed += deleted
            deleted = 0
    if deleted:
        flash(f'Deleted {deleted} hall(s).', 'success')
    if failed:
        flash('Some halls could not be deleted because they are already used in seat allocations.', 'warning')
    return redirect(url_for('exam_halls.index'))
