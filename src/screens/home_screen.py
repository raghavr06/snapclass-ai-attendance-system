import streamlit as st
from src.components.header import header_home
from src.ui.base_layout import style_base_layout, style_background_home

def home_screen():

    header_home()

    style_background_home()
    style_base_layout()

    st.markdown("""
        <div style="text-align:center; padding:0 0 22px 0;">
            <p style="
                color:#FFFFFF;
                font-size:1.15rem;
                font-weight:500;
                margin-bottom:1.4rem;
                letter-spacing:0.01em;
            ">
                AI-Powered Attendance Management Platform
            </p>
            <div style="
                display:grid;
                grid-template-columns:repeat(2,1fr);
                gap:10px;
                max-width:460px;
                margin:0 auto;
            ">
                <div style="background:#fff;border-radius:14px;padding:12px 16px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,0.18);">
                    <span style="font-size:1.5rem;">👤</span>
                    <span style="color:#1a1a2e;font-weight:700;font-size:0.88rem;">Face Recognition</span>
                </div>
                <div style="background:#fff;border-radius:14px;padding:12px 16px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,0.18);">
                    <span style="font-size:1.5rem;">🎤</span>
                    <span style="color:#1a1a2e;font-weight:700;font-size:0.88rem;">Voice Recognition</span>
                </div>
                <div style="background:#fff;border-radius:14px;padding:12px 16px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,0.18);">
                    <span style="font-size:1.5rem;">📱</span>
                    <span style="color:#1a1a2e;font-weight:700;font-size:0.88rem;">QR Enrollment</span>
                </div>
                <div style="background:#fff;border-radius:14px;padding:12px 16px;display:flex;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,0.18);">
                    <span style="font-size:1.5rem;">📊</span>
                    <span style="color:#1a1a2e;font-weight:700;font-size:0.88rem;">Attendance Analytics</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)



    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.header("I'm Student")
        st.image("https://i.ibb.co/844D9Lrt/mascot-student.png", width=120)
        if st.button('Student Portal', type='primary', icon=':material/arrow_outward:', icon_position='right'):
            st.session_state['login_type']='student'
            st.rerun()

    with col2:
        st.header("I'm Teacher")
        st.image("https://i.ibb.co/CsmQQV6X/mascot-prof.png", width=145)
        if st.button('Teacher Portal', type='primary', icon=':material/arrow_outward:', icon_position='right'):
            st.session_state['login_type']='teacher'
            st.rerun()
