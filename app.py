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
        except Exception:
            db.session.rollback()

        # Seed default admin user
        if not User.query.filter_by(user_id='ashwin').first():
            admin = User(user_id='ashwin', name='Administrator', is_admin=True)
            admin.set_password('ashwin0211')
            db.session.add(admin)
            db.session.commit()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
