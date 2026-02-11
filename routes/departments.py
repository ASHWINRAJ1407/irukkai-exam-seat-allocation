"""Department management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Department

departments_bp = Blueprint('departments', __name__)


@departments_bp.route('/')
@login_required
def index():
    """List departments for the current user (admin or normal)."""
    query = Department.query.order_by(Department.code)
    query = query.filter(Department.owner_user_id == current_user.id)
    departments = query.all()
    return render_template('departments/index.html', departments=departments)

@departments_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        total_students = request.form.get('total_students', 0)
        try:
            total_students = int(total_students)
        except ValueError:
            total_students = 0
        if not name or not code:
            flash('Name and code are required.', 'danger')
            return render_template('departments/add.html')

        # Check for duplicate code only within the current user's data
        existing_q = Department.query.filter_by(
            code=code,
            owner_user_id=current_user.id,
        )
        if existing_q.first():
            flash(f'Department with code {code} already exists in your account.', 'danger')
            return render_template('departments/add.html')

        dept = Department(
            name=name,
            code=code,
            total_students=total_students,
            owner_user_id=current_user.id,
        )
        try:
            db.session.add(dept)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not save department because this code already exists in your account. '
                'Please choose a different code.',
                'danger',
            )
            return render_template('departments/add.html')

        flash(f'Department {name} added successfully.', 'success')
        return redirect(url_for('departments.index'))
    return render_template('departments/add.html')

@departments_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    dept = Department.query.get_or_404(id)
    # Ensure user can only edit their own department
    if dept.owner_user_id != current_user.id:
        flash('You are not allowed to edit this department.', 'danger')
        return redirect(url_for('departments.index'))
    if request.method == 'POST':
        dept.name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        # Ensure the new code is not used by any other department of this user
        if Department.query.filter(
            Department.owner_user_id == current_user.id,
            Department.code == code,
            Department.id != id,
        ).first():
            flash(f'Department code {code} already in use in your account.', 'danger')
            return render_template('departments/edit.html', department=dept)

        dept.code = code
        try:
            dept.total_students = int(request.form.get('total_students', 0))
        except ValueError:
            pass
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not update department because the code already exists. '
                'Please choose a different code.',
                'danger',
            )
            return render_template('departments/edit.html', department=dept)
        flash('Department updated successfully.', 'success')
        return redirect(url_for('departments.index'))
    return render_template('departments/edit.html', department=dept)

@departments_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    dept = Department.query.get_or_404(id)
    if not current_user.is_admin and dept.owner_user_id != current_user.id:
        flash('You are not allowed to delete this department.', 'danger')
        return redirect(url_for('departments.index'))
    if dept.students:
        flash('Cannot delete department with existing students. Remove students first.', 'danger')
        return redirect(url_for('departments.index'))
    db.session.delete(dept)
    db.session.commit()
    flash('Department deleted.', 'success')
    return redirect(url_for('departments.index'))


@departments_bp.route('/delete-multiple', methods=['POST'])
@login_required
def delete_multiple():
    """Delete multiple departments selected from the list."""
    ids = request.form.getlist('ids')
    if not ids:
        flash('No departments selected for deletion.', 'info')
        return redirect(url_for('departments.index'))
    deleted = 0
    blocked = 0
    for id_str in ids:
        try:
            dept_id = int(id_str)
        except ValueError:
            continue
        dept = Department.query.get(dept_id)
        if not dept:
            continue
        if not current_user.is_admin and dept.owner_user_id != current_user.id:
            blocked += 1
            continue
        if dept.students:
            blocked += 1
            continue
        db.session.delete(dept)
        deleted += 1
    if deleted:
        db.session.commit()
    if deleted:
        flash(f'Deleted {deleted} department(s).', 'success')
    if blocked:
        flash(f'{blocked} department(s) were not deleted because they still have students.', 'warning')
    return redirect(url_for('departments.index'))
