import streamlit as st
import pandas as pd
from ..components.file_upload import enhanced_file_upload
from ..components.processing import process_file
from ..components.welcome import show_welcome
from ..components.preview import show_preview
from ...models.data_models import TranslationDataset

def render_upload_layout():
    """Layout for upload workflow - sidebar controls + main content"""
    render_upload_sidebar()
    render_main_content()

def render_upload_sidebar():
    """Sidebar with file upload and processing controls"""
    with st.sidebar:
        st.header("⚙️ Processing Controls")
        
        # File upload
        uploaded_file = enhanced_file_upload()
       
        if uploaded_file:
            if st.session_state.dataset is None:
                handle_file_upload(uploaded_file)
            else:
                show_processing_options()

def handle_file_upload(uploaded_file):
    """Handle the file upload and language selection"""
    with st.spinner("Loading file..."):
        try:
            df = pd.read_excel(uploaded_file)
            
            # Language selection
            st.subheader("🌍 Select Target Language")
            
            # Find potential language columns
            lang_columns = [col for col in df.columns if col not in ["strId", "EN"]]
            
            if not lang_columns:
                st.error("No target language columns found! Make sure your file has columns other than 'strId' and 'EN'.")
                return
            
            # Let user select target language
            selected_language = st.selectbox(
                "Choose target language:",
                options=lang_columns,
                help="All other language columns will be removed"
            )
            
            # Button to confirm language selection and load data
            if st.button("✅ Load Data", type="primary"):
                with st.spinner(f"Loading data with {selected_language}..."):
                    columns_to_keep = ["strId", "EN", selected_language]
                    df_filtered = df[columns_to_keep].copy()
                    
                    st.session_state.dataset = TranslationDataset.from_dataframe(
                        df_filtered, 
                        source_col="EN",
                        target_col=selected_language,
                        str_id_col="strId"
                    )
                    
                    st.success(f"✅ Loaded {len(st.session_state.dataset)} entries")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")

def show_processing_options():
    """Show processing options when dataset is loaded"""
    dataset = st.session_state.dataset
    st.subheader("📊 File Information")
    st.write(f"**{len(dataset)}** entries loaded")
    
    st.subheader("🔧 Processing Options")
    
    # Main settings
    remove_duplicates = st.checkbox("Remove Duplicates", value=True)
    sort_by_correlation = st.checkbox("Sort by Similarity", value=True)
    
    correlation_strategy = st.selectbox(
        "Sorting Method",
        ["hybrid", "substring", "semantic"],
        help="hybrid: Best of substring + semantic"
    ) if sort_by_correlation else "hybrid"
    
    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        if sort_by_correlation and correlation_strategy in ["semantic", "hybrid"]:
            similarity_threshold = st.slider("Similarity Threshold", 0.5, 0.9, 0.7, 0.1)
            max_cluster_size = st.slider("Max Cluster Size", 5, 30, 15, 5)
        else:
            similarity_threshold = 0.7
            max_cluster_size = 15
        
        if sort_by_correlation and correlation_strategy in ["substring", "hybrid"]:
            min_substring_length = st.slider("Min Substring Length", 3, 15, 5, 1)
        else:
            min_substring_length = 5
    
    # Process button
    if st.button("🚀 Process File", type="primary", use_container_width=True):
        process_file(
            dataset, remove_duplicates, "keep_first_with_occurrences",
            sort_by_correlation, correlation_strategy, similarity_threshold,
            max_cluster_size, min_substring_length 
        )

def render_main_content():
    """Main content area - preview or welcome"""
    if st.session_state.dataset is not None:
        show_preview()
    else:
        show_welcome()
