import streamlit as st

from .styling import apply_custom_styles

def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="StringZ - ZGAME Translation Tool",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def initialize_session_state():
    """Initialize all session state variables"""
    if 'dataset' not in st.session_state:
        st.session_state.dataset = None
    if 'processed_dataset' not in st.session_state:
        st.session_state.processed_dataset = None
    if 'processing_stats' not in st.session_state:
        st.session_state.processing_stats = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None

def render_header():
    """Render the app header"""
    st.image(image="https://cdn.moogold.com/2024/10/watcher-of-realms.jpg", width=100)
    st.title("StringZ")
    st.markdown("**Translation QA Tool for ZGAME**")
    st.markdown("*Deduplicate, sort by similarity, and validate translations*")
    

def initialize_app():
    """Initialize the complete app"""
    configure_page()
    initialize_session_state()
    render_header()
    apply_custom_styles()

