"""Authentication routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')
        if not user_id or not password:
            flash('Please enter both User ID and password.', 'danger')
            return render_template('auth/login.html')
        user = User.query.filter_by(user_id=user_id).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next') or url_for('dashboard.index')
            flash(f'Welcome back, {user.name or user.user_id}!', 'success')
            return redirect(next_page)
        flash('Invalid User ID or password.', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Simple self-service registration for institute users (non-admin)."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        user_id = (request.form.get('user_id') or '').strip()
        name = (request.form.get('name') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''
        if not user_id or not password or not confirm:
            flash('User ID and password are required.', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(user_id=user_id).first():
            flash('This User ID is already taken. Please choose another.', 'danger')
            return render_template('auth/register.html')
        user = User(user_id=user_id, name=name or user_id, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created successfully. Welcome!', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html')
