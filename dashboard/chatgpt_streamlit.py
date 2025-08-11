import streamlit as st
from dashboard.dashboard_utils import *

# --- Brand Colours ---
PRIMARY_BLUE = "#1d1b5e"
PRIMARY_RED = "#c92a1d"

# --- Page Config ---
st.set_page_config(page_title="AlleynCC Dashboard", layout="wide")

# --- Custom CSS ---
st.markdown(
    f"""
    <style>
        /* Page background and heading colour */
        h1, h2, h3, h4, h5, h6 {{
            color: {PRIMARY_BLUE};
        }}
        
        /* Button styling */
        div.stButton > button:first-child {{
            background-color: {PRIMARY_RED};
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
            font-size: 1rem;
            font-weight: bold;
        }}
        div.stButton > button:first-child:hover {{
            background-color: #a02118;
            color: white;
        }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Dummy Function ---
def run_dummy():
    st.success("✅ Dummy function executed successfully!")

# --- Dashboard Layout ---
st.title("Alleyn CC Dashboard")
st.write("Welcome to the Alleyn Cricket Club dashboard.")


with st.form("team_input_form", border=True):
    st.subheader('Input your fixture details')
    header = st.columns([2,2])
    header[0].subheader('Fixture Date')
    header[1].subheader('Alleyn CC Team')
    
    row1 = st.columns([2,2])
    row1[0].radio("Select fixture date"
             , options=[f"Last Saturday: {get_last_saturday()}", f"Next Saturday: {get_next_saturday()}"]
             , key="fixture_date_option")
    
    row1[1].radio("Select Alleyn CC team"
             , options=["1st XI", "2nd XI", "3rd XI", "4th XI", "5th XI"]
             , key="selected_acc_team")
    
    submitted_fixture_details = st.form_submit_button('Get Opposition Team Sheet')

if submitted_fixture_details:
    run_dummy()
