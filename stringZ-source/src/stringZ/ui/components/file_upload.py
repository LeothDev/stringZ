import streamlit as st

def enhanced_file_upload():
    """Enhanced file upload that remembers original filename"""
    uploaded_file = st.file_uploader(
        "Upload Translation File",
        type=['xlsx', 'xls'],
        help="Upload Excel file with strId, EN, and target language columns"
    )
    
    if uploaded_file:
        # Store original filename in session state
        st.session_state.original_filename = uploaded_file.name
    
    return uploaded_file
