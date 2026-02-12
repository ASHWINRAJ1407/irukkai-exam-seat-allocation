"""Database models for Exam Seat Allocation System."""
from datetime import datetime, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User account for authentication (admin or institute user)."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    # Account approval flow:
    # - pending: newly registered, waiting for admin approval
    # - approved: can access the application
    # - rejected: cannot log in
    # - revoked: access removed after previously being approved
    account_status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Department(db.Model):
    """Academic departments."""
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    # Code is unique per user (owner_user_id, code)
    code = db.Column(db.String(20), nullable=False)
    total_students = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    students = db.relationship('Student', backref='department', lazy=True)
    exam_schedules = db.relationship('ExamSchedule', backref='department', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('owner_user_id', 'code', name='unique_dept_code_per_user'),
    )


class Student(db.Model):
    """Student records."""
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    section = db.Column(db.String(20))  # Optional, e.g. A, CSE-A
    academic_year = db.Column(db.String(20), default='2024-25')  # For filtering by batch/year
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    __table_args__ = (db.UniqueConstraint('roll_number', 'department_id', name='unique_roll_per_dept'),)


class Subject(db.Model):
    """Subjects offered by departments."""
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    exam_schedules = db.relationship('ExamSchedule', backref='subject', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('owner_user_id', 'code', name='unique_subject_code_per_user'),
    )


class ExamHall(db.Model):
    """Examination halls."""
    __tablename__ = 'exam_halls'
    id = db.Column(db.Integer, primary_key=True)
    hall_number = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=45)
    building_name = db.Column(db.String(100))
    floor = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    __table_args__ = (
        db.UniqueConstraint('owner_user_id', 'hall_number', name='unique_hall_per_user'),
    )


class Exam(db.Model):
    """Exam master - groups schedules under one exam name."""
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    academic_year = db.Column(db.String(20))  # Optional default for schedule entries
    default_start_time = db.Column(db.Time)  # Optional default for schedule entries
    default_end_time = db.Column(db.Time)  # Optional default for schedule entries
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    schedules = db.relationship('ExamSchedule', backref='exam', lazy=True, cascade='all, delete-orphan')


class ExamSchedule(db.Model):
    """Individual exam schedule entries."""
    __tablename__ = 'exam_schedules'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    academic_year = db.Column(db.String(20), default='2024-25')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class SeatAllocation(db.Model):
    """Stored seat allocations per exam date."""
    __tablename__ = 'seat_allocations'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('exam_halls.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    bench_number = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False)  # 1, 2, or 3 on bench
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    student = db.relationship('Student', backref='allocations')
    hall = db.relationship('ExamHall', backref='allocations')
    department = db.relationship('Department', backref='allocations')
    subject = db.relationship('Subject', backref='allocations')


class AdminSettings(db.Model):
    """Global admin-configurable settings (bank details, payment instructions)."""
    __tablename__ = 'admin_settings'
    id = db.Column(db.Integer, primary_key=True)
    bank_details = db.Column(db.Text)  # e.g. account number, IFSC, UPI, etc.
    payment_instructions = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SubscriptionPlan(db.Model):
    """Subscription plans defined by the administrator (e.g. Monthly, Yearly)."""
    __tablename__ = 'subscription_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration_months = db.Column(db.Integer, nullable=False)  # e.g. 1 for monthly, 12 for yearly
    price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subscription(db.Model):
    """Active or historical subscription for a user."""
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PaymentSubmission(db.Model):
    """User-submitted payment proof for manual verification."""
    __tablename__ = 'payment_submissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    reference = db.Column(db.String(120), nullable=False)  # UTR / transaction id / note
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    admin_note = db.Column(db.Text)


class UsageEvent(db.Model):
    """Tracks feature usage per user to enforce free-tier limits."""
    __tablename__ = 'usage_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feature = db.Column(db.String(50), nullable=False)  # timetable, scheduling, allocation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
