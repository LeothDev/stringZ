import streamlit as st
from .processed_layout import render_processed_layout
from .upload_layout import render_upload_layout

def render_main_layout():
    """Main layout router. It handles which layout to show"""
    if st.session_state.processed_dataset is not None:
        render_processed_layout()
    else:
        render_upload_layout()
