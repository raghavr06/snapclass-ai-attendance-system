from src.database.config import supabase
import bcrypt
from zoneinfo import ZoneInfo

def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def check_pass(pwd, hashed):
     return bcrypt.checkpw(pwd.encode(), hashed.encode())



def check_teacher_exists(username):
    response = supabase.table("teachers").select("username").eq("username", username).execute()
    return len(response.data) > 0


def create_teacher(username, password, name):
    data={"username": username, "password":hash_pass(password), "name":name}
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher["password"]):
            return teacher
    return None



def get_all_students():
    response = supabase.table("students").select("*").execute()
    return response.data


def create_student(new_name, face_embedding=None, voice_embedding=None):
    data={"name":new_name, "face_embedding":face_embedding, "voice_embedding":voice_embedding}
    response = supabase.table("students").insert(data).execute()
    return response.data


def create_subject(subject_code,name, section, teacher_id):
    existing = supabase.table("subjects").select("subject_id").eq("subject_code", subject_code).execute()

    if existing.data:
        raise Exception("Subject code already exists")


    data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data


def get_teacher_subjects(teacher_id):
    response = supabase.table("subjects").select("*", "subject_students(count)","attendance_logs(timestamp)").eq("teacher_id", teacher_id).execute()
    subjects = response.data

    for sub in subjects:
        sub['total_students'] = sub.get("subject_students", [{}])[0].get('count', 0) if sub.get('subject_students') else 0
        attendance = sub.get('attendance_logs', [])
        unique_sessions = len(set(log["timestamp"] for log in attendance))
        sub['total_classes'] = unique_sessions

        sub.pop('subject_students', None)
        sub.pop('attendance_logs', None)

    return subjects


def enroll_student_to_subject(student_id, subject_id):
    data={"student_id":student_id, "subject_id":subject_id}
    response=supabase.table("subject_students").insert(data).execute()
    return response.data

def unenroll_student_to_subject(student_id, subject_id):
    data={"student_id":student_id, "subject_id":subject_id}
    response=supabase.table("subject_students").delete().eq("student_id",student_id).eq("subject_id", subject_id).execute()
    return response.data


def get_student_subjects(student_id):
     response = supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
     return response.data

def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def create_attendance(logs):
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data

def get_attendance_for_teacher(teacher_id):
    response = supabase.table("attendance_logs").select("*, subjects!inner(*)").eq('subjects.teacher_id', teacher_id).execute()
    return response.data



def get_subject_enrollment_preview(subject_code):
    response = (
        supabase.table("subjects")
        .select("subject_id, name, subject_code, section, teachers(name), subject_students(count)")
        .eq("subject_code", subject_code)
        .execute()
    )
    if not response.data:
        return None
    sub = response.data[0]
    sub['instructor_name'] = (sub.get('teachers') or {}).get('name', 'N/A')
    sub['enrolled_count'] = (sub.get('subject_students') or [{}])[0].get('count', 0)
    return sub


def get_subject_attendance_stats_for_teacher(teacher_id):
    response = (
        supabase.table("attendance_logs")
        .select("subject_id, is_present, subjects!inner(teacher_id)")
        .eq("subjects.teacher_id", teacher_id)
        .execute()
    )
    raw = {}
    for log in response.data:
        sid = log['subject_id']
        if sid not in raw:
            raw[sid] = {'total': 0, 'present': 0}
        raw[sid]['total'] += 1
        if log.get('is_present'):
            raw[sid]['present'] += 1

    return {
        sid: (round(s['present'] / s['total'] * 100) if s['total'] > 0 else 0)
        for sid, s in raw.items()
    }


def get_subject_defaulters(subject_id):
    response = (
        supabase.table("attendance_logs")
        .select("student_id, is_present, students(name)")
        .eq("subject_id", subject_id)
        .execute()
    )
    stats = {}
    for log in response.data:
        sid = log['student_id']
        if sid not in stats:
            stats[sid] = {
                'name': (log.get('students') or {}).get('name', 'Unknown'),
                'total': 0,
                'present': 0,
            }
        stats[sid]['total'] += 1
        if log.get('is_present'):
            stats[sid]['present'] += 1

    defaulters = []
    for s in stats.values():
        pct = round(s['present'] / s['total'] * 100) if s['total'] > 0 else 0
        if pct < 75:
            defaulters.append({'name': s['name'], 'pct': pct})

    defaulters.sort(key=lambda x: x['pct'])
    return defaulters


def get_attendance_with_students_for_teacher(teacher_id):
    response = (
        supabase.table("attendance_logs")
        .select("*, subjects!inner(*), students(name, student_id)")
        .eq("subjects.teacher_id", teacher_id)
        .execute()
    )
    return response.data


def get_subject_daily_attendance(subject_id):
    from datetime import datetime
    from collections import defaultdict

    response = (
        supabase.table("attendance_logs")
        .select("is_present, timestamp")
        .eq("subject_id", subject_id)
        .execute()
    )

    day_stats = defaultdict(lambda: {"present": 0, "total": 0})
    for log in response.data:
        ts = log.get("timestamp")
        if ts:
            d = datetime.fromisoformat(ts).astimezone(ZoneInfo("Asia/Kolkata")).date()
            day_stats[d]["total"] += 1
            if log.get("is_present"):
                day_stats[d]["present"] += 1

    return {
        d: {
            "present": s["present"],
            "total":   s["total"],
            "pct":     round(s["present"] / s["total"] * 100) if s["total"] > 0 else 0,
        }
        for d, s in day_stats.items()
    }
