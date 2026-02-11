"""Subject management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from models import db, Subject
from utils.excel_parser import parse_subjects_file

subjects_bp = Blueprint('subjects', __name__)


@subjects_bp.route('/')
@login_required
def index():
    """List subjects for the current user."""
    query = Subject.query.order_by(Subject.code)
    query = query.filter(Subject.owner_user_id == current_user.id)
    subjects = query.all()
    return render_template('subjects/index.html', subjects=subjects)

@subjects_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        if not name or not code:
            flash('Name and code are required.', 'danger')
            return render_template('subjects/add.html')

        # Check for duplicate code only within the current user's data
        existing_q = Subject.query.filter_by(
            code=code,
            owner_user_id=current_user.id,
        )
        if existing_q.first():
            flash(f'Subject with code {code} already exists in your account.', 'danger')
            return render_template('subjects/add.html')

        s = Subject(name=name, code=code, owner_user_id=current_user.id)
        try:
            db.session.add(s)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not save subject because this code already exists in your account. '
                'Please choose a different code.',
                'danger',
            )
            return render_template('subjects/add.html')

        flash(f'Subject {name} added successfully.', 'success')
        return redirect(url_for('subjects.index'))
    return render_template('subjects/add.html')

@subjects_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_subjects():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('Please select a file to upload.', 'danger')
            return render_template('subjects/import.html')
        try:
            content = file.read()
            records = parse_subjects_file(content, file.filename)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('subjects/import.html')
        added = 0
        skipped = 0
        for r in records:
            existing_q = Subject.query.filter_by(
                code=r['code'],
                owner_user_id=current_user.id,
            )
            if existing_q.first():
                skipped += 1
                continue
            s = Subject(name=r['name'], code=r['code'], owner_user_id=current_user.id)
            db.session.add(s)
            added += 1
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Some subjects could not be imported because their codes already exist '
                'in your account. Duplicates have been skipped.',
                'warning',
            )
            return redirect(url_for('subjects.index'))

        flash(f'Imported {added} subjects. Skipped {skipped} duplicates.', 'success')
        return redirect(url_for('subjects.index'))
    return render_template('subjects/import.html')

@subjects_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    subj = Subject.query.get_or_404(id)
    if subj.owner_user_id != current_user.id:
        flash('You are not allowed to edit this subject.', 'danger')
        return redirect(url_for('subjects.index'))
    if request.method == 'POST':
        subj.name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()

        # Ensure the new code is not used by any other subject of this user
        existing_q = Subject.query.filter(
            Subject.owner_user_id == current_user.id,
            Subject.code == code,
            Subject.id != id,
        )
        if existing_q.first():
            flash(f'Subject code {code} already in use in your account.', 'danger')
            return render_template('subjects/edit.html', subject=subj)

        subj.code = code
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                'Could not update subject because this code already exists in your account. '
                'Please choose a different code.',
                'danger',
            )
            return render_template('subjects/edit.html', subject=subj)

        flash('Subject updated successfully.', 'success')
        return redirect(url_for('subjects.index'))
    return render_template('subjects/edit.html', subject=subj)

@subjects_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    subj = Subject.query.get_or_404(id)
    if not current_user.is_admin and subj.owner_user_id != current_user.id:
        flash('You are not allowed to delete this subject.', 'danger')
        return redirect(url_for('subjects.index'))
    if subj.exam_schedules:
        flash('Cannot delete subject with existing exam schedules.', 'danger')
        return redirect(url_for('subjects.index'))
    db.session.delete(subj)
    db.session.commit()
    flash('Subject deleted.', 'success')
    return redirect(url_for('subjects.index'))


@subjects_bp.route('/delete-multiple', methods=['POST'])
@login_required
def delete_multiple():
    """Delete multiple subjects selected from the list."""
    ids = request.form.getlist('ids')
    if not ids:
        flash('No subjects selected for deletion.', 'info')
        return redirect(url_for('subjects.index'))
    deleted = 0
    blocked = 0
    for id_str in ids:
        try:
            subj_id = int(id_str)
        except ValueError:
            continue
        subj = Subject.query.get(subj_id)
        if not subj:
            continue
        if not current_user.is_admin and subj.owner_user_id != current_user.id:
            blocked += 1
            continue
        if subj.exam_schedules:
            blocked += 1
            continue
        db.session.delete(subj)
        deleted += 1
    if deleted:
        db.session.commit()
    if deleted:
        flash(f'Deleted {deleted} subject(s).', 'success')
    if blocked:
        flash(f'{blocked} subject(s) were not deleted because they have exam schedules.', 'warning')
    return redirect(url_for('subjects.index'))
