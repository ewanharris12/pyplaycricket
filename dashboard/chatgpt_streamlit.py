import streamlit as st

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
st.title("🏏 AlleynCC Dashboard")
st.write("Welcome to the Alleyn Cricket Club dashboard.")

if st.button("Run Dummy Function"):
    run_dummy()
