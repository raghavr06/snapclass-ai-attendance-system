import streamlit as st
from src.database.config import supabase
from src.database.db import enroll_student_to_subject, get_subject_enrollment_preview
import time


@st.dialog("Enroll in Subject")
def enroll_dialog():
    st.write('Enter the subject code provided by your teacher to enroll')
    join_code = st.text_input('Subject Code', placeholder='Eg. CS101')

    if join_code:
        preview = get_subject_enrollment_preview(join_code)

        if preview:
            with st.container(border=True):
                st.subheader(preview['name'])
                st.caption(f"Code: {preview['subject_code']} | Section: {preview['section']}")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Instructor", preview['instructor_name'])
                with c2:
                    st.metric("Students Enrolled", preview['enrolled_count'])

            student_id = st.session_state.student_data["student_id"]

            check = supabase.table("subject_students").select("*") \
                .eq("subject_id", preview["subject_id"]) \
                .eq("student_id", student_id) \
                .execute()

            if check.data:
                st.warning("You are already enrolled in this subject")
            else:
                if st.button("Enroll Now", type="primary", width="stretch"):
                    enroll_student_to_subject(student_id, preview["subject_id"])
                    st.success("Successfully Enrolled")
                    time.sleep(1)
                    st.rerun()
        else:
            st.error("Subject code doesn't exist")