import streamlit as st
from src.ui.base_layout import style_background_dashboard, style_base_layout
from src.components.header import header_dashboard
from PIL import Image
import numpy as np
import math
import calendar as cal_module
import pandas as pd
from datetime import datetime
from collections import defaultdict
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings, train_classifier
from src.database.db import get_all_students, create_student, get_student_subjects, get_student_attendance, unenroll_student_to_subject
import time
from src.pipelines.voice_pipeline import get_voice_embedding
from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card



def render_attendance_calendar(logs):
    date_status = {}
    for log in logs:
        ts = log.get('timestamp')
        if ts:
            d = datetime.fromisoformat(ts.split('.')[0]).date()

            if d not in date_status or log.get('is_present'):
                date_status[d] = log.get('is_present', False)

    if not date_status:
        st.info("No attendance records to display.")
        return

    months = defaultdict(dict)
    for d, status in date_status.items():
        months[(d.year, d.month)][d.day] = status

    for (year, month) in sorted(months.keys()):
        month_name = cal_module.month_name[month]
        html = f"<p style='font-weight:600; margin:8px 0 4px 0; color:#555;'>📅 {month_name} {year}</p>"
        html += "<table style='border-collapse:collapse; width:100%;'>"
        html += "<tr>" + "".join(
            f"<th style='text-align:center; padding:4px 0; font-size:0.75rem; color:#888;'>{day}</th>"
            for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        ) + "</tr>"

        month_days = months[(year, month)]
        for week in cal_module.monthcalendar(year, month):
            html += "<tr>"
            for day in week:
                if day == 0:
                    html += "<td style='padding:6px;'></td>"
                elif day in month_days:
                    icon = "🟢" if month_days[day] else "🔴"
                    html += f"<td style='text-align:center; padding:6px; font-size:0.85rem;'>{icon}<br/><span style='font-size:0.7rem;'>{day}</span></td>"
                else:
                    html += f"<td style='text-align:center; padding:6px; font-size:0.85rem; color:#aaa;'>{day}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)



@st.dialog("Attendance Details")
def subject_attendance_dialog(sub_name, sub_code, section, stats, logs, subject_id):

    attended = stats['attended']
    total = stats['total']
    pct = round(attended / total * 100) if total > 0 else 0

    if pct >= 75:
        status_label = "🟢 Safe"
    elif pct >= 70:
        status_label = "🟡 Warning"
    else:
        status_label = "🔴 Critical"

    st.subheader(sub_name)
    st.caption(f"Code: {sub_code} | Section: {section}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Attendance", f"{pct}%")
    c2.metric("Classes Attended", f"{attended} / {total}")

    with c3:
        if pct >= 75:
            badge_color, badge_bg = "#166534", "#dcfce7"   
        elif pct >= 70:
            badge_color, badge_bg = "#92400e", "#fef3c7"   
        else:
            badge_color, badge_bg = "#991b1b", "#fee2e2"
        st.markdown("**Status**")
        st.markdown(
            f"<div style='"
            f"display:inline-block;"
            f"background:{badge_bg};"
            f"color:{badge_color};"
            f"border:2px solid {badge_color};"
            f"border-radius:999px;"
            f"padding:5px 14px;"
            f"font-weight:700;"
            f"font-size:0.85rem;"
            f"white-space:nowrap;"
            f"'>{status_label}</div>",
            unsafe_allow_html=True,
        )
  


    st.divider()

    subject_logs = [log for log in logs if log.get('subject_id') == subject_id]

    if not subject_logs:
        st.info("No attendance records found for this subject.")
        return


    st.subheader("📅 Attendance Calendar")
    render_attendance_calendar(subject_logs)

    st.divider()


    st.subheader("📋 Attendance History")
    history = []
    for log in sorted(subject_logs, key=lambda x: x.get('timestamp', ''), reverse=True):
        ts = log.get('timestamp')
        if ts:
            date_str = datetime.fromisoformat(ts.split('.')[0]).strftime("%d %b %Y")
            history.append({
                "Date": date_str,
                "Status": "✅ Present" if log.get('is_present') else "❌ Absent",
            })
    if history:
        st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)

    st.divider()


    st.subheader("🔮 Attendance Predictor")
    if total == 0:
        st.info("No classes held yet for this subject.")
    elif pct >= 75:
        # max classes student can miss and still stay >= 75%
        # attended / (total + X) >= 0.75  →  X <= (attended - 0.75*total) / 0.75
        can_miss = math.floor((attended - 0.75 * total) / 0.75)
        if can_miss > 0:
            st.success(
                f"**Current Attendance: {pct}%**\n\n"
                f"You can miss **{can_miss}** more class(es) and still remain above 75%."
            )
        else:
            st.success(
                f"**Current Attendance: {pct}%**\n\n"
                "You are exactly at the safe threshold. Attend all upcoming classes!"
            )
    else:
        # min consecutive classes needed to reach 75%
        # (attended + X) / (total + X) >= 0.75  →  X >= (0.75*total - attended) / 0.25
        need = math.ceil((0.75 * total - attended) / 0.25)
        st.warning(
            f"**Current Attendance: {pct}%**\n\n"
            f"Attend the next **{need}** consecutive class(es) to reach 75%."
        )


def student_dashboard():
  student_data = st.session_state.student_data
  student_id = student_data["student_id"]
  c1,c2 = st.columns(2, gap="xxlarge", vertical_alignment="center")

  with c1:
    header_dashboard()

  with c2:
    st.subheader(f""" Welcome {student_data["name"]}""")
    if st.button("Logout", type="secondary", key="loginbackbtn"):
      st.session_state["is_logged_in"] = False
      del st.session_state.student_data
      st.rerun()

  st.space()

  c1, c2 =st.columns(2)
  with c1:
      st.header('Your Enrolled Subjects')
  with c2:
      if st.button("Enroll in subject", type="primary", width="stretch"):
        enroll_dialog()

  st.divider()

  with st.spinner('Loading your enrolled subjects..'):
       subjects = get_student_subjects(student_id)
       logs = get_student_attendance(student_id)


  stats_map = {}
  for log in logs:
      sid = log['subject_id']
      if sid not in stats_map:
          stats_map[sid] = {"total": 0, "attended": 0}
      stats_map[sid]['total'] += 1
      if log.get("is_present"):
          stats_map[sid]["attended"] += 1

  cols = st.columns(2)
  for i, sub_node in enumerate(subjects):
      sub = sub_node['subjects']
      sid = sub['subject_id']

      stats = stats_map.get(sid, {"total": 0, "attended": 0})
      attended = stats['attended']
      total = stats['total']


      pct = round(attended / total * 100) if total > 0 else 0
      status = "🟢 Safe" if pct >= 75 else ("🟡 Warning" if pct >= 70 else "🔴 Critical")


      def card_footer(sub=sub, sid=sid, stats=stats, pct=pct, status=status):
          c1, c2 = st.columns(2)
          with c1:
              if st.button(
                  "📊 View Details",
                  key=f"details_{sub['subject_id']}",
                  width='stretch',
                  type='secondary',
              ):
                  subject_attendance_dialog(
                      sub['name'], sub['subject_code'], sub['section'],
                      stats, logs, sid
                  )
          with c2:
              if st.button(
                  "Unenroll",
                  type='tertiary',
                  width='stretch',
                  icon=':material/delete_forever:',
                  key=f"unenroll_{sub['subject_id']}",
              ):
                  unenroll_student_to_subject(student_id, sid)
                  st.toast(f"Unenrolled from {sub['name']} successfully!")
                  st.rerun()

      with cols[i % 2]:
          subject_card(
              name=sub['name'],
              code=sub['subject_code'],
              section=sub['section'],
              stats=[
                  ('📅', 'Classes', f"{attended} / {total}"),
                  ('📊', 'Attendance', f"{pct}%  {status}"),
              ],
              footer_callback=card_footer,
          )


      
  

def student_screen():
    style_background_dashboard()
    style_base_layout()

    if "student_data" in st.session_state:
        student_dashboard()
        return

    c1,c2 = st.columns(2, gap="xxlarge", vertical_alignment="center")

    with c1:
     header_dashboard()

    with c2:
     if st.button("Go back to Home", type="secondary", key="loginbackbtn"):
        st.session_state["login_type"] = None
        st.rerun()

    st.header("Login using FaceID", text_alignment="center")
    st.space()

    show_registration=False

    photo_src = st.camera_input("Position your face in center")


    if photo_src:
      
      img = np.array(Image.open(photo_src))


      with st.spinner("Scanning image..."):
        try:
          detected, all_ids, num_faces = predict_attendance(img)
        
        except Exception as e:
          st.error(f"Prediction Error: {e}")
      

        if num_faces==0:
          st.warning('Face not found!')
        elif num_faces>1:
          st.warning("Multiple faces detected!")
        else:
          
          if detected:
            student_id = list(detected.keys())[0]
            all_students = get_all_students()
            student = None

            for s in all_students:
                if s["student_id"] == student_id:
                    student = s
                    break
            
            if student:
              st.session_state.is_logged_in = True
              st.session_state.user_role = "student"
              st.session_state.student_data = student
              st.toast(f"Welcome back {student["name"]}")
              time.sleep(1)
              st.rerun()

          else:
            st.info("Face not recognized! You might be a new student")
            show_registration=True
    

    if show_registration:
      with st.container(border=True):
        st.header("Register new profile")
        new_name = st.text_input("Enter your name")

        st.subheader('Optional : Voice Enrollment')
        st.info("Enroll for voice only attendance")

        audio_data=None

        try:
          audio_data = st.audio_input("Record a short phrase, E.g - My name is Raghav, I'm present")
        except Exception:
          st.error("Audio data failed")

        if st.button("Create Account", type="primary"): 
          if new_name:
            with st.spinner('Creating profile..'):
              img = np.array(Image.open(photo_src))
              encodings = get_face_embeddings(img)

              if encodings:
                face_emb = encodings[0].tolist()

                voice_emb = None
                if audio_data:
                  voice_emb = get_voice_embedding(audio_data.read())
                
                response_data = create_student(new_name, face_embedding = face_emb, voice_embedding = voice_emb)
                if response_data:
                  train_classifier()
                  st.session_state.is_logged_in = True
                  st.session_state.user_role = "student"
                  st.session_state.student_data = response_data[0]
                  st.toast(f"Profile Created! Hi {new_name}")
                  time.sleep(1)
                  st.rerun()

              else:
                  st.error('Couldnt capture your facial features for registration')
              
          
          else:
            st.warning("Enter your name")
          

          

          

          
          