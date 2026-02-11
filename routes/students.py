"""Student management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Student, Department, SeatAllocation
from utils.excel_parser import parse_students_file

students_bp = Blueprint('students', __name__)

@students_bp.route('/')
@login_required
def index():
    dept_id = request.args.get('department')
    year_filter = request.args.get('academic_year', '')
    section_filter = request.args.get('section', '')
    query = Student.query
    if not current_user.is_admin:
        query = query.filter(Student.owner_user_id == current_user.id)
    if dept_id:
        query = query.filter(Student.department_id == dept_id)
    if year_filter:
        query = query.filter(Student.academic_year == year_filter)
    if section_filter:
        query = query.filter(Student.section == section_filter)
    students = query.order_by(Student.roll_number).all()
    dept_query = Department.query.order_by(Department.code)
    if not current_user.is_admin:
        dept_query = dept_query.filter(Department.owner_user_id == current_user.id)
    departments = dept_query.all()
    years_query = db.session.query(Student.academic_year)
    if not current_user.is_admin:
        years_query = years_query.filter(Student.owner_user_id == current_user.id)
    years = years_query.distinct().all()
    years = [y[0] for y in years if y[0]]
    sections = db.session.query(Student.section).distinct().filter(Student.section.isnot(None), Student.section != '').all()
    sections = [s[0] for s in sections if s[0]]
    filtered_count = len(students)
    filters_applied = bool(dept_id or year_filter or section_filter)
    return render_template('students/index.html',
        students=students, departments=departments, years=years, sections=sections,
        selected_dept=dept_id, selected_year=year_filter, selected_section=section_filter,
        filtered_count=filtered_count, filters_applied=filters_applied)

@students_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    dept_query = Department.query.order_by(Department.code)
    if not current_user.is_admin:
        dept_query = dept_query.filter(Department.owner_user_id == current_user.id)
    departments = dept_query.all()
    batch_query = db.session.query(Student.academic_year)
    if not current_user.is_admin:
        batch_query = batch_query.filter(Student.owner_user_id == current_user.id)
    batches = [y[0] for y in batch_query.distinct().all() if y[0]]
    if request.method == 'POST':
        roll = request.form.get('roll_number', '').strip()
        name = request.form.get('name', '').strip()
        dept_id = request.form.get('department_id')
        section = request.form.get('section', '').strip() or None
        year = request.form.get('academic_year', '2024-25')
        if not roll or not name or not dept_id:
            flash('Roll number, name, and department are required.', 'danger')
            return render_template('students/add.html', departments=departments, batches=batches)
        dept = Department.query.get(dept_id)
        if not dept:
            flash('Invalid department.', 'danger')
            return render_template('students/add.html', departments=departments, batches=batches)

        # Check for duplicate roll number within the same department to honor DB uniqueness
        existing_q = Student.query.filter_by(roll_number=roll, department_id=dept_id)
        if existing_q.first():
            flash(f'Student with roll {roll} already exists in this department.', 'danger')
            return render_template('students/add.html', departments=departments, batches=batches)

        s = Student(
            roll_number=roll,
            name=name,
            department_id=dept_id,
            section=section,
            academic_year=year,
            owner_user_id=current_user.id,
        )
        try:
            db.session.add(s)
            dept.total_students = Student.query.filter_by(department_id=dept_id).count() + 1
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not save student because this roll number is already used in the department.',
                'danger',
            )
            return render_template('students/add.html', departments=departments, batches=batches)

        flash('Student added successfully.', 'success')
        return redirect(url_for('students.index'))
    return render_template('students/add.html', departments=departments, batches=batches)

@students_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_students():
    dept_query = Department.query.order_by(Department.code)
    if not current_user.is_admin:
        dept_query = dept_query.filter(Department.owner_user_id == current_user.id)
    departments = dept_query.all()
    batch_query = db.session.query(Student.academic_year)
    if not current_user.is_admin:
        batch_query = batch_query.filter(Student.owner_user_id == current_user.id)
    batches = [y[0] for y in batch_query.distinct().all() if y[0]]
    if request.method == 'POST':
        dept_id = request.form.get('department_id')
        section = request.form.get('section', '').strip() or None
        year = request.form.get('academic_year', '2024-25')
        file = request.files.get('file')
        if not dept_id or not file or file.filename == '':
            flash('Please select department and upload file.', 'danger')
            return render_template('students/import.html', departments=departments, batches=batches)
        dept = Department.query.get(dept_id)
        if not dept:
            flash('Invalid department.', 'danger')
            return render_template('students/import.html', departments=departments, batches=batches)
        try:
            content = file.read()
            records = parse_students_file(content, file.filename)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('students/import.html', departments=departments, batches=batches)
        added = 0
        skipped = 0
        for r in records:
            existing_q = Student.query.filter_by(roll_number=r['roll_number'], department_id=dept_id)
            if existing_q.first():
                skipped += 1
                continue
            row_section = r.get('section') or section
            s = Student(
                roll_number=r['roll_number'],
                name=r['name'],
                department_id=dept_id,
                section=row_section,
                academic_year=year,
                owner_user_id=current_user.id,
            )
            db.session.add(s)
            added += 1
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Some students could not be imported because their roll numbers are already '
                'used in this department. Duplicates have been skipped.',
                'warning',
            )
            return redirect(url_for('students.index'))

        dept.total_students = Student.query.filter_by(department_id=dept_id).count()
        db.session.commit()
        flash(f'Imported {added} students. Skipped {skipped} duplicates.', 'success')
        return redirect(url_for('students.index'))
    return render_template('students/import.html', departments=departments, batches=batches)

@students_bp.route('/delete-filtered', methods=['POST'])
@login_required
def delete_filtered():
    dept_id = request.form.get('department')
    year_filter = request.form.get('academic_year', '')
    section_filter = request.form.get('section', '')
    query = Student.query
    if not current_user.is_admin:
        query = query.filter(Student.owner_user_id == current_user.id)
    if dept_id:
        query = query.filter(Student.department_id == dept_id)
    if year_filter:
        query = query.filter(Student.academic_year == year_filter)
    if section_filter:
        query = query.filter(Student.section == section_filter)
    to_delete = query.all()
    count = len(to_delete)
    if count == 0:
        flash('No students match the current filters.', 'info')
        return redirect(url_for('students.index'))
    student_ids = [s.id for s in to_delete]
    SeatAllocation.query.filter(SeatAllocation.student_id.in_(student_ids)).delete(synchronize_session=False)
    for s in to_delete:
        db.session.delete(s)
    for dept in Department.query.all():
        dept.total_students = Student.query.filter_by(department_id=dept.id).count()
    db.session.commit()
    flash(f'Deleted {count} student(s) matching the applied filters.', 'warning')
    params = {}
    if dept_id:
        params['department'] = dept_id
    if year_filter:
        params['academic_year'] = year_filter
    if section_filter:
        params['section'] = section_filter
    return redirect(url_for('students.index', **params))

@students_bp.route('/delete-all', methods=['POST'])
@login_required
def delete_all():
    base_q = Student.query
    if not current_user.is_admin:
        base_q = base_q.filter(Student.owner_user_id == current_user.id)
    count = base_q.count()
    if count == 0:
        flash('No students to delete.', 'info')
        return redirect(url_for('students.index'))
    if current_user.is_admin:
        SeatAllocation.query.delete()
        Student.query.delete()
        for dept in Department.query.all():
            dept.total_students = 0
    else:
        # Delete only current user's data
        student_ids = [s.id for s in base_q.all()]
        if student_ids:
            SeatAllocation.query.filter(SeatAllocation.student_id.in_(student_ids)).delete(synchronize_session=False)
            for s in base_q.all():
                db.session.delete(s)
        for dept in Department.query.filter(Department.owner_user_id == current_user.id).all():
            dept.total_students = 0
    db.session.commit()
    flash(f'All {count} students have been deleted.', 'warning')
    return redirect(url_for('students.index'))

@students_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    s = Student.query.get_or_404(id)
    if not current_user.is_admin and s.owner_user_id != current_user.id:
        flash('You are not allowed to delete this student.', 'danger')
        return redirect(url_for('students.index'))
    dept_id = s.department_id
    SeatAllocation.query.filter_by(student_id=id).delete()
    db.session.delete(s)
    dept = Department.query.get(dept_id)
    if dept:
        dept.total_students = Student.query.filter_by(department_id=dept_id).count() - 1
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('students.index'))
