import streamlit as st
import numpy as np
from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.components.header import header_dashboard
from src.database.db import create_teacher, check_teacher_exists, teacher_login, get_teacher_subjects, get_attendance_for_teacher, get_subject_attendance_stats_for_teacher, get_subject_defaulters, get_attendance_with_students_for_teacher, get_subject_daily_attendance
import time
from src.components.dialog_create_subject import create_subject_dialog
from src.components.dialog_share_subject import share_subject_dialog
from src.components.subject_card import subject_card
from src.components.dialog_add_photo import add_photos_dialog
from src.pipelines.face_pipeline import predict_attendance
from src.database.config import supabase
from datetime import datetime
import pandas as pd
import calendar as cal_module
from collections import defaultdict
from src.components.dialog_attendance_results import attendance_result_dialog
from src.components.dialog_voice_attendance import voice_attendance_dialog



def teacher_screen():
    style_background_dashboard()
    style_base_layout()

    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type=="login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type =="register":
        teacher_screen_register()


def teacher_dashboard():
    teacher_data = st.session_state.teacher_data

    c1,c2 = st.columns(2, gap="xxlarge", vertical_alignment="center")

    with c1:
      header_dashboard()

    with c2:
      st.subheader(f""" Welcome {teacher_data["name"]}""")
      if st.button("Logout", type="secondary", key="loginbackbtn"):
        st.session_state["is_logged_in"] = False
        del st.session_state.teacher_data
        st.rerun()

    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = "take_attendance"

    tab1, tab2, tab3 = st.columns(3)

    with tab1:
         type1 = "primary" if st.session_state.current_teacher_tab == 'take_attendance' else "tertiary"
         if st.button('Take Attendance',type=type1, width='stretch', icon=':material/ar_on_you:'):
             st.session_state.current_teacher_tab = "take_attendance"
             st.rerun()
    
    with tab2:
         type2 = "primary" if st.session_state.current_teacher_tab == 'manage_subjects' else "tertiary"
         if st.button('Manage Subjects',type=type2, width='stretch', icon=':material/book_ribbon:'):
             st.session_state.current_teacher_tab = "manage_subjects"
             st.rerun()
    
    with tab3:
         type3 = "primary" if st.session_state.current_teacher_tab == 'attendance_records' else "tertiary"
         if st.button('Attendance Records', type=type3, width='stretch', icon=':material/cards_stack:'):
             st.session_state.current_teacher_tab = "attendance_records"
             st.rerun()

    st.divider()


    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()


def teacher_tab_take_attendance():
    teacher_id = st.session_state.teacher_data["teacher_id"]
    st.header("Take attendance")

    if "attendance_images" not in st.session_state:
        st.session_state.attendance_images=[]

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning('You havent created any subjects yet! Please create one to begin!')
        return
    
    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1, col2 = st.columns([3,1], vertical_alignment="bottom")

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button("Add Photos",type='primary', icon=':material/photo_prints:', width='stretch'):
            add_photos_dialog()

        selected_subject_id = subject_options[selected_subject_label]

    st.divider()

    if st.session_state.attendance_images:
        st.header("Added Photos")
        gallery_cols = st.columns(4)

        for idx, img in enumerate(st.session_state.attendance_images):
          with gallery_cols[idx % 4 ]:
              st.image(img, width="stretch", caption=f"Photo {idx+1}")
        
    has_photos = bool(st.session_state.attendance_images )
    c1, c2, c3 = st.columns(3)

    with c1:
            if st.button("Clear all images", width="stretch", type="tertiary",icon=':material/delete:',disabled=not has_photos):
                st.session_state.attendance_images=[]
                st.rerun()

    with c2:
            if st.button("Run Face Analysis", type="secondary",width="stretch", icon=':material/analytics:', disabled=not has_photos):
                with st.spinner("Deep scanning classroom photos"):
                    all_detected_ids={}

                    for idx, img in enumerate(st.session_state.attendance_images):
                        img_np = np.array(img.convert("RGB"))

                        detected,_,_ = predict_attendance(img_np)

                        if detected:
                            for sid in detected.keys():
                                student_id = int(sid)

                                all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")


                    enrolled_res = supabase.table('subject_students').select("*, students(*)").eq('subject_id',selected_subject_id ).execute()
                    enrolled_students = enrolled_res.data

                    if not enrolled_students:
                        st.warning('No students enrolled in this course')
                    else:
                        results, attendance_to_log  = [], []

                        current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                        for node in enrolled_students:
                            student = node["students"]
                            sources = all_detected_ids.get(int(student["student_id"]), [])
                            is_present = len(sources) > 0

                            results.append({
                                "Name":student["name"],
                                "ID":student["student_id"],
                                "Sources":", ".join(sources) if is_present else "-",
                                "Status":"✅ Present" if is_present else "❌ Absent"
                            })

                            attendance_to_log.append({
                            'student_id': student['student_id'],
                            'subject_id': selected_subject_id,
                            'timestamp': current_timestamp,
                            'is_present': bool(is_present)
                            })
                

                attendance_result_dialog(pd.DataFrame(results), attendance_to_log)


    with c3:
            if st.button('Use Voice Attendance', type='primary', width='stretch', icon=':material/mic:'):
                voice_attendance_dialog(selected_subject_id)



def render_teacher_attendance_calendar(daily_stats):
    if not daily_stats:
        st.info("No attendance data recorded yet.")
        return

    months = defaultdict(dict)
    for d, stats in daily_stats.items():
        months[(d.year, d.month)][d.day] = stats["pct"]

    for (year, month) in sorted(months.keys()):
        month_name = cal_module.month_name[month]
        html = (
            f"<p style='font-weight:600; margin:8px 0 4px 0; color:#555;'>"
            f"📅 {month_name} {year}</p>"
        )
        html += "<table style='border-collapse:collapse; width:100%;'>"
        html += "<tr>" + "".join(
            f"<th style='text-align:center;padding:4px 0;font-size:0.75rem;color:#888;'>{day}</th>"
            for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        ) + "</tr>"

        month_days = months[(year, month)]
        for week in cal_module.monthcalendar(year, month):
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td style='padding:6px;'></td>"
                elif day in month_days:
                    pct = month_days[day]
                    if pct >= 80:
                        color, bg = "#166534", "#dcfce7"
                    elif pct >= 60:
                        color, bg = "#92400e", "#fef3c7"
                    else:
                        color, bg = "#991b1b", "#fee2e2"
                    html += (
                        f"<td style='text-align:center;padding:3px;'>"
                        f"<div style='background:{bg};border-radius:8px;padding:4px 2px;'>"
                        f"<span style='color:{color};font-weight:700;font-size:0.78rem;'>{pct}%</span>"
                        f"<br/><span style='font-size:0.68rem;color:#555;'>{day}</span>"
                        f"</div></td>"
                    )
                else:
                    html += (
                        f"<td style='text-align:center;padding:6px;"
                        f"font-size:0.85rem;color:#aaa;'>{day}</td>"
                    )
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)



@st.dialog("Session Attendance Details", width="large")
def teacher_session_detail_dialog(session_label, present_students, absent_students):
    st.subheader(session_label)

    total         = len(present_students) + len(absent_students)
    present_count = len(present_students)
    absent_count  = len(absent_students)
    pct           = round(present_count / total * 100) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Present ✅", present_count)
    c2.metric("Absent ❌",  absent_count)
    c3.metric("Attendance", f"{pct}%")

    st.divider()

    col_p, col_a = st.columns(2)
    with col_p:
        st.markdown("#### ✅ Present Students")
        if present_students:
            for name in sorted(present_students):
                st.markdown(f"✓ &nbsp; **{name}**")
        else:
            st.info("No students were marked present.")

    with col_a:
        st.markdown("#### ❌ Absent Students")
        if absent_students:
            for name in sorted(absent_students):
                st.markdown(f"✗ &nbsp; {name}")
        else:
            st.success("All students were present! 🎉")


def teacher_tab_manage_subjects():
    teacher_id = st.session_state.teacher_data["teacher_id"]

    col1, col2 = st.columns(2)
    with col1:
        st.header('Manage Subjects', width='stretch')

    with col2:
        if st.button("Create New Subject", width="stretch"):
            create_subject_dialog(teacher_id)

    # List all subjects
    subjects = get_teacher_subjects(teacher_id)

    if subjects:
        attendance_stats = get_subject_attendance_stats_for_teacher(teacher_id)

        for sub in subjects:
            avg_pct = attendance_stats.get(sub['subject_id'], 0)
            stats = [
                ("🤺", "Students",      sub['total_students']),
                ("🕰️", "Classes",       sub['total_classes']),
                ("📊", "Avg Attendance", f"{avg_pct}%"),
            ]

            def share_btn(sub=sub):
                if st.button(f"Share Code: {sub['name']}", key=f"share_{sub['subject_code']}", icon=":material/share:"):
                    share_subject_dialog(sub["name"], sub["subject_code"])
                st.space()

            subject_card(
                name=sub['name'],
                code=sub['subject_code'],
                section=sub['section'],
                stats=stats,
                footer_callback=share_btn,
            )

        
            defaulters = get_subject_defaulters(sub['subject_id'])
            if defaulters:
                with st.expander(f"⚠️ Attendance Defaulters — {len(defaulters)} student(s) below 75%"):
                    for d in defaulters:
                        st.markdown(f"**{d['name']}** — {d['pct']}%")
            else:
                with st.expander("✅ Attendance — No Defaulters"):
                    st.success("All enrolled students are above 75% attendance.")

            daily_stats = get_subject_daily_attendance(sub['subject_id'])
            if daily_stats:
                with st.expander("📅 Attendance Calendar"):
                    render_teacher_attendance_calendar(daily_stats)
    else:
        st.info("NO SUBJECTS FOUND. CREATE ONE ABOVE")


def teacher_tab_attendance_records():
    teacher_id = st.session_state.teacher_data["teacher_id"]

    records = get_attendance_with_students_for_teacher(teacher_id)

    if not records:
        st.info("No attendance records found.")
        return

    data = []
    for r in records:
        ts = r.get("timestamp")
        data.append({
            "ts_group":    ts.split(".")[0] if ts else None,
            "Time":        datetime.fromisoformat(ts).strftime("%Y-%m-%d %I:%M %p") if ts else "N/A",
            "Subject":     r["subjects"]["name"],
            "Subject Code":r["subjects"]["subject_code"],
            "is_present":  bool(r.get("is_present", False)),
            "student_name":(r.get("students") or {}).get("name", "Unknown"),
        })

    df = pd.DataFrame(data)

    summary = (
        df.groupby(["ts_group", "Time", "Subject", "Subject Code"])
        .agg(
            Present_Count=("is_present", "sum"),
            Total_Count=("is_present", "count"),
        ).reset_index()
    )

    summary["Absent_Count"]  = summary["Total_Count"] - summary["Present_Count"]
    summary["Attendance %"] = (
        (summary["Present_Count"] / summary["Total_Count"] * 100).round(1).astype(str) + "%"
    )


    for idx, (_, row) in enumerate(
        summary.sort_values("ts_group", ascending=False).iterrows()
    ):
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([4, 2, 2, 2, 2], vertical_alignment="center")

            with c1:
                st.markdown(f"**{row['Time']}**")
                st.caption(f"{row['Subject']}  ·  `{row['Subject Code']}`")

            c2.metric("Present ✅", int(row["Present_Count"]))
            c3.metric("Absent ❌",  int(row["Absent_Count"]))
            c4.metric("Attendance", row["Attendance %"])

            with c5:
                if st.button(
                    "👥 View Details",
                    key=f"det_session_{idx}",
                    width="stretch",
                    type="secondary",
                ):
                    session_df = df[df["ts_group"] == row["ts_group"]]
                    present = session_df[session_df["is_present"]]["student_name"].tolist()
                    absent  = session_df[~session_df["is_present"]]["student_name"].tolist()
                    teacher_session_detail_dialog(
                        f"{row['Time']}  —  {row['Subject']}",
                        present,
                        absent,
                    )




def login_teacher(username, password):
    if not username or not password:
        return False
    
    teacher = teacher_login(username, password)
    if teacher:
        st.session_state.user_role = "teacher"
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
    
    return False


def teacher_screen_login():
     c1,c2 = st.columns(2, gap="xxlarge", vertical_alignment="center")

     with c1:
        header_dashboard()

     with c2:
        if st.button("Go back to Home", type="secondary", key="loginbackbtn"):
            st.session_state["login_type"] = None
            st.rerun()

     st.header("Login using password", text_alignment="center")
     st.space()
    

     teacher_username = st.text_input("Enter username", placeholder="ram@123")

     teacher_pass = st.text_input("Enter password", type="password", placeholder="Enter password")

     st.divider()

     btnc1, btnc2 = st.columns(2)

     with btnc1:
         if st.button('Login', icon=':material/passkey:', width='stretch'):
             if login_teacher(teacher_username, teacher_pass):
                 st.toast("Welcome back!")
                 time.sleep(1)
                 st.rerun()
             else:
                 st.error("Invalid username and password combo")
    
     with btnc2:
         if st.button('Register Instead', type="primary", icon=':material/passkey:', width='stretch'):
             st.session_state.teacher_login_type='register'


def register_teacher(teacher_username, teacher_pass, teacher_name, teacher_pass_confirm):
    if not teacher_username or not teacher_name or not teacher_pass:
        return False, "All Fields are required!"
    
    if check_teacher_exists(teacher_username):
        return False, "Username already taken"
    
    if teacher_pass!=teacher_pass_confirm:
        return False, "Password doesn't match"
    
    try:
        create_teacher(teacher_username, teacher_pass, teacher_name)
        return True, "Successfully Created! Login Now"
    
    except Exception as e:
        return False, "Unexpected error!"


def teacher_screen_register():
     c1,c2 = st.columns(2, gap="xxlarge", vertical_alignment="center")

     with c1:
        header_dashboard()

     with c2:
        if st.button("Go back to Home", type="secondary", key="loginbackbtn"):
            st.session_state["login_type"] = None
            st.rerun()
    
     st.header("Register your teacher profile")
     st.space()
    

     teacher_username = st.text_input("Enter username", placeholder="ram@123")

     teacher_name = st.text_input("Enter name", placeholder='Ram Joshi')

     teacher_pass = st.text_input("Enter password", type="password", placeholder="Enter password")

     teacher_pass_confirm = st.text_input("Confirm your password", type='password', placeholder="Enter password")

     st.divider()

     btnc1, btnc2 = st.columns(2)

     with btnc1:
         if st.button('Register Now', icon=':material/passkey:', width='stretch'):
             success, message = register_teacher(teacher_username, teacher_pass, teacher_name, teacher_pass_confirm)
             if success:
                 st.success(message)
                 time.sleep(2)
                 st.session_state.teacher_login_type='login'
                 st.rerun()
             else:
                st.error(message)
             
    
     with btnc2:
         if st.button('Login Instead', type="primary", icon=':material/passkey:', width='stretch'):
             st.session_state.teacher_login_type='login'
             

