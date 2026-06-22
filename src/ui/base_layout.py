import streamlit as st

def style_background_home():
    st.markdown("""
            <style> 
                
                .stApp{
                    background: #5865F2 !important;
                    color:black;
                }

                .stApp div[data-testid="stColumn"]{
                    background-color:#E0E3FF !important;
                    padding:2.5rem !important;
                    border-radius: 5rem !important;
                }

            </style>


            """
        ,unsafe_allow_html=True)
    
def style_background_dashboard():
    st.markdown("""
            <style> 
                
                .stApp{
                    background: #E0E3FF !important;
                    color:black;
                }

            </style>


            """
        ,unsafe_allow_html=True)

def style_base_layout():
    st.markdown("""
            <style> 
                @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital@0;1&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');
                @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&family=Plus+Jakarta+Sans:ital@0;1&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');


                    /* Hide Toolbar of streamlit */

                    #MainMenu,footer,header{
                        visibility:hidden;
                    }

                    .block-container{
                        padding-top:1.5rem !important;                
                    }
                
                    h1, h2{
                        font-family:sans-serif !important;
                        font-size:2.0rem !important;
                        line-height:1.1 !important;
                        margin-bottom:0rem !important;
                        color:black;
                    }
                
                    h3,h4,p{
                        font-family:Outfit !important;
                    }
                
                    button{
                        border-radius:1.5rem !important;
                        background-color: #5865F2 !important;
                        border:none !important;
                        color:white !important;
                        padding:10px 20px !important;
                        transition: transform 0.25s ease-in-out !important;
                    }
                
                    button[kind="secondary"]{
                        border-radius:1.5rem !important;
                        background-color: #EB459E !important;
                        border:none !important;
                        color:white !important;
                        padding:10px 20px !important;
                        transition: transform 0.25s ease-in-out !important;
                    }
                
                    button[kind="tertiary"]{
                        border-radius:1.5rem !important;
                        background-color: black !important;
                        border:none !important;
                        color:white !important;
                        padding:10px 20px !important;
                        transition: transform 0.25s ease-in-out !important;
                    }
                    button:hover{
                        transform :scale(1.05);
                }
                


            </style>


            """
        ,unsafe_allow_html=True)