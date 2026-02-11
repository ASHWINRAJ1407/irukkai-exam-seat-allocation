"""Admin dashboard routes."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Department, Student, ExamHall, Subject, Exam, ExamSchedule
from sqlalchemy import func
from datetime import date

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    dept_q = Department.query
    stu_q = Student.query
    hall_q = ExamHall.query
    subj_q = Subject.query
    sched_q = ExamSchedule.query
    exam_q = Exam.query
    if not current_user.is_admin:
        dept_q = dept_q.filter(Department.owner_user_id == current_user.id)
        stu_q = stu_q.filter(Student.owner_user_id == current_user.id)
        hall_q = hall_q.filter(ExamHall.owner_user_id == current_user.id)
        subj_q = subj_q.filter(Subject.owner_user_id == current_user.id)
        sched_q = sched_q.filter(ExamSchedule.owner_user_id == current_user.id)
        exam_q = exam_q.filter(Exam.owner_user_id == current_user.id)

    total_departments = dept_q.count()
    total_students = stu_q.count()
    total_halls = hall_q.count()
    total_subjects = subj_q.count()

    upcoming = sched_q.filter(ExamSchedule.exam_date >= date.today())\
        .order_by(ExamSchedule.exam_date).limit(10).all()
    exam_ids = list({s.exam_id for s in upcoming})
    exams = exam_q.filter(Exam.id.in_(exam_ids)).all() if exam_ids else []
    exam_map = {e.id: e.name for e in exams}

    upcoming_list = []
    for s in upcoming:
        exam_name = exam_map.get(s.exam_id, 'Unknown')
        dept = s.department
        subj = s.subject
        upcoming_list.append({
            'exam_name': exam_name,
            'date': s.exam_date,
            'department': dept.name if dept else '',
            'subject': subj.name if subj else '',
            'time': f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}" if s.start_time and s.end_time else ''
        })

    return render_template('dashboard/index.html',
        total_departments=total_departments,
        total_students=total_students,
        total_halls=total_halls,
        total_subjects=total_subjects,
        upcoming_exams=upcoming_list)
