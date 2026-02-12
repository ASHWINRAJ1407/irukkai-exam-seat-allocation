"""Exam Seat Allocation System - Main Flask Application."""
import os
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User

# Ensure uploads directory exists
Path(Config.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CSRFProtect(app)

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.departments import departments_bp
    from routes.students import students_bp
    from routes.subjects import subjects_bp
    from routes.exam_halls import exam_halls_bp
    from routes.timetable_generator import timetable_bp
    from routes.exam_schedule import exam_schedule_bp
    from routes.allocation import allocation_bp
    from routes.subscriptions import subscriptions_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(departments_bp, url_prefix='/departments')
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(subjects_bp, url_prefix='/subjects')
    app.register_blueprint(exam_halls_bp, url_prefix='/exam-halls')
    app.register_blueprint(timetable_bp, url_prefix='/timetable')
    app.register_blueprint(exam_schedule_bp, url_prefix='/exam-schedule')
    app.register_blueprint(allocation_bp, url_prefix='/allocation')
    app.register_blueprint(subscriptions_bp, url_prefix='')

    # Admin-only approval dashboard (does not expose tenant data)
    from routes.overall_dashboard import overall_dashboard_bp
    app.register_blueprint(overall_dashboard_bp, url_prefix='/admin')

    with app.app_context():
        db.create_all()
        # Lightweight schema adjustments for existing databases (SQLite/PostgreSQL)
        from sqlalchemy import text, inspect
        try:
            insp = inspect(db.engine)
            table_names = insp.get_table_names()

            if 'students' in table_names:
                cols = [c['name'] for c in insp.get_columns('students')]
                if 'section' not in cols:
                    db.session.execute(text('ALTER TABLE students ADD COLUMN section VARCHAR(20)'))
                    db.session.commit()
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE students ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'departments' in table_names:
                cols = [c['name'] for c in insp.get_columns('departments')]
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE departments ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'subjects' in table_names:
                cols = [c['name'] for c in insp.get_columns('subjects')]
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE subjects ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'exam_halls' in table_names:
                cols = [c['name'] for c in insp.get_columns('exam_halls')]
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE exam_halls ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'exams' in table_names:
                cols = [c['name'] for c in insp.get_columns('exams')]
                if 'academic_year' not in cols:
                    db.session.execute(text('ALTER TABLE exams ADD COLUMN academic_year VARCHAR(20)'))
                    db.session.commit()
                if 'default_start_time' not in cols:
                    db.session.execute(text('ALTER TABLE exams ADD COLUMN default_start_time TIME'))
                    db.session.commit()
                if 'default_end_time' not in cols:
                    db.session.execute(text('ALTER TABLE exams ADD COLUMN default_end_time TIME'))
                    db.session.commit()
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE exams ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'exam_schedules' in table_names:
                cols = [c['name'] for c in insp.get_columns('exam_schedules')]
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE exam_schedules ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'seat_allocations' in table_names:
                cols = [c['name'] for c in insp.get_columns('seat_allocations')]
                if 'owner_user_id' not in cols:
                    db.session.execute(text('ALTER TABLE seat_allocations ADD COLUMN owner_user_id INTEGER'))
                    db.session.commit()

            if 'users' in table_names:
                cols = [c['name'] for c in insp.get_columns('users')]
                if 'is_admin' not in cols:
                    db.session.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
                    db.session.commit()
                if 'account_status' not in cols:
                    # Store account approval status for institute users.
                    # Use a default so existing rows become usable.
                    db.session.execute(text("ALTER TABLE users ADD COLUMN account_status VARCHAR(20) DEFAULT 'approved'"))
                    db.session.commit()
        except Exception:
            db.session.rollback()

        # Seed default admin user
        if not User.query.filter_by(user_id='ashwin').first():
            admin = User(user_id='ashwin', name='Administrator', is_admin=True, account_status='approved')
            admin.set_password('ashwin0211')
            db.session.add(admin)
            db.session.commit()
        else:
            # Ensure seeded admin remains approved even after schema updates.
            admin = User.query.filter_by(user_id='ashwin').first()
            if admin and not admin.account_status:
                admin.account_status = 'approved'
                db.session.commit()

    # Gate access: only approved users can use the app.
    from flask import request, redirect, url_for, flash
    from flask_login import current_user, logout_user

    @app.before_request
    def enforce_account_approval():
        # Allow unauthenticated access to auth endpoints
        if not current_user.is_authenticated:
            return None

        # Admin account always allowed; admin does not see tenant data in routes.
        if getattr(current_user, 'is_admin', False):
            return None

        status = getattr(current_user, 'account_status', 'pending') or 'pending'

        # Always allow logout, waiting page, and auth endpoints
        allowed_endpoints = {
            'auth.logout',
            'auth.waiting',
            'auth.login',
            'auth.register',
            'static',
        }
        if request.endpoint in allowed_endpoints or (request.endpoint or '').startswith('static'):
            return None

        if status == 'approved':
            return None

        if status in ('rejected', 'revoked'):
            logout_user()
            flash('Your account access has been disabled. Please contact the administrator.', 'danger')
            return redirect(url_for('auth.login'))

        # pending
        return redirect(url_for('auth.waiting'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
