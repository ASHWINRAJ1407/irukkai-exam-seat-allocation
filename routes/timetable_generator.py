"""Exam Timetable Generator: generate conflict-free timetable, then feed to scheduling."""
from datetime import datetime, date, time
from io import BytesIO
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, session
from flask_login import login_required, current_user
from models import db, Exam, ExamSchedule, Department, Subject, Student
from utils.excel_parser import parse_timetable_subjects_file
from utils.timetable_generator import generate_timetable, subject_counts_per_department
from utils.pdf_generator import create_master_timetable_pdf
from utils.subscription import is_feature_allowed, record_usage
import pandas as pd

timetable_bp = Blueprint('timetable_generator', __name__)

SESSION_KEYS = {
    'rows': 'timetable_rows',
    'exam_name': 'timetable_exam_name',
    'academic_year': 'timetable_academic_year',
    'start_date': 'timetable_start_date',
    'time_str': 'timetable_time_str',
    'excluded': 'timetable_excluded',
    'schedule': 'timetable_schedule',
    'subject_names': 'timetable_subject_names',
}


def _normalize_academic_year(year_str):
    """Normalize academic year to match Student.academic_year format (e.g. 2024-25)."""
    if not year_str or not isinstance(year_str, str):
        return '2024-25'
    s = year_str.strip()
    if not s:
        return '2024-25'
    if '-' in s:
        parts = s.split('-', 1)
        if len(parts) == 2:
            p0, p1 = parts[0].strip(), parts[1].strip()
            if len(p1) >= 2:
                return f"{p0}-{p1[-2:]}"  # 2024-2025 -> 2024-25
            return f"{p0}-{p1}"
    return s


def _parse_time_for_display(t_str):
    """Parse a time string to a `time` object and 12-hour display string.

    Accepts:
    - 'HH:MM' (24-hour, e.g. '13:15' from HTML time input)
    - 'HH:MM AM/PM' (12-hour, e.g. '01:15 PM')
    """
    if not t_str or not str(t_str).strip():
        return None, ''
    s = str(t_str).strip()
    s_up = s.upper().replace('.', ':')
    am_pm = None
    if 'AM' in s_up or 'PM' in s_up:
        if 'AM' in s_up:
            am_pm = 'AM'
            s_up = s_up.replace('AM', '').strip()
        else:
            am_pm = 'PM'
            s_up = s_up.replace('PM', '').strip()
    parts = s_up.split(':')
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return None, s

    if am_pm:
        # Convert 12-hour to 24-hour
        if am_pm == 'AM':
            h_24 = 0 if h == 12 else h
        else:
            h_24 = 12 if h == 12 else h + 12
        t = time(h_24, m)
    else:
        # Assume already 24-hour
        t = time(h, m)

    # Build 12-hour display string
    hour_12 = t.hour % 12 or 12
    suffix = 'AM' if t.hour < 12 else 'PM'
    display = f"{hour_12:02d}:{t.minute:02d} {suffix}"
    return t, display


@timetable_bp.route('/')
@login_required
def index():
    """Step 1: Upload Excel (exam name, academic year, file)."""
    # Provide existing academic years (batches) for convenience in a dropdown.
    years_query = db.session.query(Student.academic_year)
    # Each user has their own data set; filter by owner_user_id
    years_query = years_query.filter(Student.owner_user_id == current_user.id)
    batches = [y[0] for y in years_query.distinct().all() if y[0]]
    return render_template('timetable_generator/index.html', batches=batches)


@timetable_bp.route('/import', methods=['POST'])
@login_required
def import_file():
    """Parse uploaded Excel and store in session; redirect to generate form."""
    exam_name = (request.form.get('exam_name') or '').strip()
    academic_year = (request.form.get('academic_year') or '').strip() or '2024-2025'
    file = request.files.get('file')
    if not exam_name:
        flash('Exam name is required.', 'danger')
        return redirect(url_for('timetable_generator.index'))
    if not file or not file.filename:
        flash('Please select an Excel file (.xlsx or .xls) or CSV.', 'danger')
        return redirect(url_for('timetable_generator.index'))
    fn = file.filename.lower()
    if not (fn.endswith('.xlsx') or fn.endswith('.xls') or fn.endswith('.csv')):
        flash('File must be Excel (.xlsx, .xls) or CSV.', 'danger')
        return redirect(url_for('timetable_generator.index'))
    try:
        content = file.read()
        rows = parse_timetable_subjects_file(content, file.filename)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('timetable_generator.index'))
    if not rows:
        flash('No valid rows found. Ensure columns: department_code, subject_code.', 'danger')
        return redirect(url_for('timetable_generator.index'))
    counts = subject_counts_per_department(rows)
    session[SESSION_KEYS['rows']] = rows
    session[SESSION_KEYS['exam_name']] = exam_name
    session[SESSION_KEYS['academic_year']] = academic_year
    session['timetable_counts'] = counts
    return redirect(url_for('timetable_generator.generate_form'))


@timetable_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate_form():
    """Step 2: Start date, timing, excluded dates; then run generator."""
    if request.method == 'GET':
        rows = session.get(SESSION_KEYS['rows'])
        if not rows:
            flash('Please upload an Excel file first.', 'warning')
            return redirect(url_for('timetable_generator.index'))
        counts = session.get('timetable_counts', subject_counts_per_department(rows))
        # Provide available batches for the user to choose from
        years_query = db.session.query(Student.academic_year).filter(Student.owner_user_id == current_user.id)
        batches = [y[0] for y in years_query.distinct().all() if y[0]]
        return render_template('timetable_generator/generate.html',
            exam_name=session.get(SESSION_KEYS['exam_name'], ''),
            academic_year=session.get(SESSION_KEYS['academic_year'], '2024-2025'),
            counts=counts,
            batches=batches)

    # POST: run generator
    rows = session.get(SESSION_KEYS['rows'])
    if not rows:
        flash('Session expired. Please upload the file again.', 'danger')
        return redirect(url_for('timetable_generator.index'))

    start_date_str = (request.form.get('start_date') or '').strip()
    start_time_raw = (request.form.get('exam_start_time') or '').strip()
    end_time_raw = (request.form.get('exam_end_time') or '').strip()
    excluded_raw = request.form.getlist('excluded_date')
    excluded = [x.strip() for x in excluded_raw if x.strip()]

    if not start_date_str:
        flash('Starting date is required.', 'danger')
        return redirect(url_for('timetable_generator.generate_form'))
    if not start_time_raw or not end_time_raw:
        flash('Both start time and end time are required.', 'danger')
        return redirect(url_for('timetable_generator.generate_form'))

    # Resolve subject names from DB FIRST before generating timetable
    subj_codes = list({r.get('subject_code', '').upper() for r in rows if r.get('subject_code')})
    subject_names_map = {}
    if subj_codes:
        subjects = Subject.query.filter(
            Subject.code.in_(subj_codes),
            Subject.owner_user_id == current_user.id,
        ).all()
        subject_names_map = {s.code: s.name for s in subjects}

    try:
        # Pass subject_names_map to generate_timetable for subject-name-based conflict resolution
        schedule, subject_names_map = generate_timetable(
            rows, start_date_str, excluded, subject_names_map=subject_names_map
        )
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('timetable_generator.generate_form'))

    # Parse times and prepare display string (12-hour format)
    start_time_obj, start_display = _parse_time_for_display(start_time_raw)
    end_time_obj, end_display = _parse_time_for_display(end_time_raw)
    if not start_time_obj or not end_time_obj:
        flash('Invalid time format. Please use a valid time value.', 'danger')
        return redirect(url_for('timetable_generator.generate_form'))

    # Freemium check: timetable generation usage
    allowed, msg = is_feature_allowed(current_user, "timetable")
    if not allowed:
        flash(msg, 'warning')
        return redirect(url_for('subscriptions.plans'))

    # Store schedule as list of (date_iso, dept, code, name) for PDF/Excel (ISO string for session serialization)
    schedule_with_names = []
    for item in schedule:
        if len(item) >= 4:
            d, dept, code, name = item[0], item[1], item[2], item[3]
        else:
            d, dept, code = item[0], item[1], item[2]
            name = subject_names_map.get(code, '')
        date_iso = d.isoformat() if hasattr(d, 'isoformat') else str(d)
        schedule_with_names.append((date_iso, dept, code, name))

    session[SESSION_KEYS['schedule']] = schedule_with_names
    session[SESSION_KEYS['exam_name']] = session.get(SESSION_KEYS['exam_name'], '')
    # Respect user-selected batch if provided on the form
    selected_year = request.form.get('academic_year') or session.get(SESSION_KEYS['academic_year'], '2024-2025')
    session[SESSION_KEYS['academic_year']] = selected_year
    session[SESSION_KEYS['start_date']] = start_date_str
    session[SESSION_KEYS['time_str']] = f"{start_display} - {end_display}"
    session[SESSION_KEYS['subject_names']] = subject_names_map
    # Store 24-hour times for later scheduling
    session['timetable_start_time'] = start_time_obj.strftime('%H:%M')
    session['timetable_end_time'] = end_time_obj.strftime('%H:%M')
    # Record usage only after successful generation
    record_usage(current_user, "timetable")
    return redirect(url_for('timetable_generator.result'))


@timetable_bp.route('/result')
@login_required
def result():
    """Step 3: Show generated timetable and buttons (Excel, PDF, Make Scheduling)."""
    schedule = session.get(SESSION_KEYS['schedule'])
    if not schedule:
        flash('No generated timetable in session. Please generate again.', 'warning')
        return redirect(url_for('timetable_generator.index'))
    exam_name = session.get(SESSION_KEYS['exam_name'], '')
    academic_year = session.get(SESSION_KEYS['academic_year'], '')
    time_str = session.get(SESSION_KEYS['time_str'], '')
    schedule_display = [( _format_date_for_display(d), dept, code, name) for d, dept, code, name in schedule]
    return render_template('timetable_generator/result.html',
        schedule=schedule_display,
        exam_name=exam_name,
        academic_year=academic_year,
        time_str=time_str)


def _format_date_for_display(d):
    """Format date for Excel/PDF display (dd.mm.yyyy)."""
    if hasattr(d, 'strftime'):
        return d.strftime('%d.%m.%Y')
    if isinstance(d, str) and len(d) == 10 and d[4] == '-' and d[7] == '-':
        # ISO date
        try:
            y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
            return f"{day:02d}.{m:02d}.{y:04d}"
        except (ValueError, IndexError):
            pass
    return str(d)


def _normalize_date(d):
    """Return date object for sorting/display; accept date or ISO string."""
    if hasattr(d, 'year'):
        return d
    if isinstance(d, str) and len(d) >= 10 and d[4] == '-' and d[7] == '-':
        try:
            return date(int(d[:4]), int(d[5:7]), int(d[8:10]))
        except (ValueError, IndexError):
            pass
    if isinstance(d, str) and '/' in d:
        parts = d.split('/')
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    return d


def _schedule_to_excel_bytes():
    """Build Excel (BytesIO) from session schedule."""
    schedule = session.get(SESSION_KEYS['schedule'], [])
    if not schedule:
        return None
    date_set = set()
    for s in schedule:
        d = _normalize_date(s[0])
        date_set.add(d)
    dates = sorted([x for x in date_set if hasattr(x, 'year')], key=lambda x: x)
    if not dates and date_set:
        dates = sorted(date_set, key=str)
    depts = []
    seen = set()
    for s in schedule:
        if s[1] not in seen:
            seen.add(s[1])
            depts.append(s[1])
    grid = {}
    for s in schedule:
        d_raw, dept, code = s[0], s[1], s[2]
        name = s[3] if len(s) > 3 else ''
        d_norm = _normalize_date(d_raw)
        grid[(dept, d_norm)] = f"{code} - {name}" if name else code
    rows = []
    rows.append(['DEPT'] + [_format_date_for_display(d) for d in dates])
    for dept in depts:
        row = [dept]
        for d in dates:
            row.append(grid.get((dept, d), '-'))
        rows.append(row)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    buf = BytesIO()
    df.to_excel(buf, index=False, engine='openpyxl')
    buf.seek(0)
    return buf


@timetable_bp.route('/download-excel')
@login_required
def download_excel():
    schedule = session.get(SESSION_KEYS['schedule'])
    if not schedule:
        flash('No timetable to download.', 'warning')
        return redirect(url_for('timetable_generator.index'))
    buf = _schedule_to_excel_bytes()
    if not buf:
        return redirect(url_for('timetable_generator.result'))
    exam_name = session.get(SESSION_KEYS['exam_name'], 'timetable').replace(' ', '_')
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'master_timetable_{exam_name}.xlsx')


@timetable_bp.route('/download-pdf')
@login_required
def download_pdf():
    schedule = session.get(SESSION_KEYS['schedule'])
    if not schedule:
        flash('No timetable to download.', 'warning')
        return redirect(url_for('timetable_generator.index'))
    exam_name = session.get(SESSION_KEYS['exam_name'], '')
    academic_year = session.get(SESSION_KEYS['academic_year'], '')
    time_str = session.get(SESSION_KEYS['time_str'], '')
    buf = create_master_timetable_pdf(schedule, exam_name, academic_year, time_str)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
        download_name=f'master_timetable_{exam_name.replace(" ", "_")}.pdf')


@timetable_bp.route('/make-scheduling', methods=['POST'])
@login_required
def make_scheduling():
    """Create Exam + ExamSchedule from generated timetable; redirect to exam schedule detail."""
    schedule = session.get(SESSION_KEYS['schedule'])
    if not schedule:
        flash('No generated timetable in session. Please generate again.', 'danger')
        return redirect(url_for('timetable_generator.index'))

    # Freemium check: scheduling usage
    allowed, msg = is_feature_allowed(current_user, "scheduling")
    if not allowed:
        flash(msg, "warning")
        return redirect(url_for("subscriptions.plans"))

    exam_name = session.get(SESSION_KEYS['exam_name'], 'Generated Exam')
    academic_year = _normalize_academic_year(session.get(SESSION_KEYS['academic_year'], '2024-2025'))
    start_24 = session.get('timetable_start_time', '13:15')
    end_24 = session.get('timetable_end_time')
    start_obj, _ = _parse_time_for_display(start_24)
    if not start_obj:
        start_obj = time(13, 15)
    if end_24:
        end_obj, _ = _parse_time_for_display(end_24)
        if not end_obj:
            end_obj = time((start_obj.hour + 3) % 24, start_obj.minute)
    else:
        # Fallback: 3 hours after start
        end_obj = time((start_obj.hour + 3) % 24, start_obj.minute)

    # Only use departments and subjects belonging to the current user
    dept_q = Department.query.filter(Department.owner_user_id == current_user.id)
    subj_q = Subject.query.filter(Subject.owner_user_id == current_user.id)
    dept_map = {d.code.upper(): d.id for d in dept_q.all()}
    subj_map = {s.code.upper(): s.id for s in subj_q.all()}

    exam = Exam(
        name=exam_name,
        academic_year=academic_year,
        default_start_time=start_obj,
        default_end_time=end_obj,
        owner_user_id=current_user.id,
    )
    db.session.add(exam)
    db.session.flush()
    added = 0
    for item in schedule:
        d, dept_code, subj_code = item[0], item[1], item[2]
        dept_id = dept_map.get(dept_code)
        subj_id = subj_map.get(subj_code)
        if not dept_id or not subj_id:
            continue
        exam_date = _normalize_date(d)
        if not hasattr(exam_date, 'year'):
            continue
        es = ExamSchedule(
            exam_id=exam.id,
            department_id=dept_id,
            subject_id=subj_id,
            exam_date=exam_date,
            start_time=start_obj,
            end_time=end_obj,
            academic_year=academic_year,
            owner_user_id=current_user.id,
        )
        db.session.add(es)
        added += 1
    db.session.commit()
    # Record scheduling usage when exam and schedules are created.
    record_usage(current_user, "scheduling")
    session.pop(SESSION_KEYS['schedule'], None)
    session.pop(SESSION_KEYS['rows'], None)
    flash(f'Timetable transferred to Exam Schedule. Created exam "{exam_name}" with {added} schedule entries.', 'success')
    return redirect(url_for('exam_schedule.detail', exam_id=exam.id))
