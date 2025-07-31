import streamlit as st
import pandas as pd
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stringZ.models.data_models import TranslationDataset

from stringZ.ui.tabs.results_tab import show_results
from stringZ.ui.tabs.review_tab import show_review_mode
from stringZ.ui.tabs.validation_tab import show_validation_tab

from stringZ.ui.components.welcome import show_welcome
from stringZ.ui.components.preview import show_preview
from stringZ.ui.components.file_upload import enhanced_file_upload
from stringZ.ui.components.processing import process_file


st.set_page_config(
    page_title="StringZ - ZGAME Translation Tool",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'dataset' not in st.session_state:
    st.session_state.dataset = None
if 'processed_dataset' not in st.session_state:
    st.session_state.processed_dataset = None
if 'processing_stats' not in st.session_state:
    st.session_state.processing_stats = None
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None

def main():
    # Header
    st.image(image="https://cdn.moogold.com/2024/10/watcher-of-realms.jpg", width=100)
    st.title("StringZ")
    st.markdown("**Translation QA Tool for ZGAME**")
    st.markdown("*Deduplicate, sort by similarity, and validate translations*")
    
    # Custom CSS for better text wrapping
    st.markdown("""
    <style>
    .stDataFrame [data-testid="stDataFrameResizable"] div[data-testid="cell"] {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        max-width: 300px !important;
        overflow-wrap: break-word !important;
    }
    .stDataFrame [data-testid="stDataFrameResizable"] {
        font-size: 14px;
    }
    .copy-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ddd;
        margin: 5px 0;
        font-family: monospace;
        word-break: break-all;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if we have processed data to show tabs
    if st.session_state.processed_dataset is not None:
        # Show tabs when data is processed
        tab1, tab2, tab3 = st.tabs(["📊 Results", "🔍 Review Translations", "⚠️ LQA Validation"])
        
        with tab1:
            show_results()
        
        with tab2:
            show_review_mode()
            
        with tab3:
            show_validation_tab()
            
        # Sidebar with reset option
        with st.sidebar:
            st.header("🔄 Process New File")
            
            if st.button("🆕 Start Over", type="secondary", use_container_width=True):
                st.session_state.dataset = None
                st.session_state.processed_dataset = None
                st.session_state.processing_stats = None
                st.session_state.validation_results = None
                st.rerun()
            
            st.markdown("---")
            dataset = st.session_state.processed_dataset
            st.write(f"📝 **{len(dataset)}** entries")
            st.write(f"🌍 **{dataset.source_lang}** → **{dataset.target_lang}**")
            
            # Quick stats in sidebar
            df = dataset.to_dataframe()
            if 'Occurrences' in df.columns:
                avg_occ = df['Occurrences'].mean()
                max_occ = df['Occurrences'].max()
                st.write(f"📊 Avg occurrences: **{avg_occ:.1f}**")
                st.write(f"🔥 Max occurrences: **{max_occ}**")
            
            if dataset.target_lang in df.columns:
                completion_rate = (df[dataset.target_lang].notna().sum() / len(df) * 100)
                st.write(f"✅ Completion: **{completion_rate:.1f}%**")
    
    else:
        # Original workflow - sidebar controls + main content
        with st.sidebar:
            st.header("⚙️ Processing Controls")
            
            # File upload
            uploaded_file = enhanced_file_upload()
           
            if uploaded_file:
                # Load and analyze file
                if st.session_state.dataset is None:
                    with st.spinner("Loading file..."):
                        try:
                            df = pd.read_excel(uploaded_file)
                            
                            # Language selection
                            st.subheader("🌍 Select Target Language")
                            
                            # Find potential language columns (exclude strId and EN)
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
                                    # Filter dataframe to keep only selected columns
                                    columns_to_keep = ["strId", "EN", selected_language]
                                    df_filtered = df[columns_to_keep].copy()
                                    
                                    # Create dataset from filtered dataframe
                                    st.session_state.dataset = TranslationDataset.from_dataframe(
                                        df_filtered, 
                                        source_col="EN",
                                        target_col=selected_language,
                                        str_id_col="strId"
                                    )
                                    
                                    st.success(f"✅ Loaded {len(st.session_state.dataset)} entries")
                                    st.rerun()
                            
                            return  # Don't continue until language is selected
                            
                        except Exception as e:
                            st.error(f"Error loading file: {str(e)}")
                            return
                
                # Show processing options
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
                
                # Advanced settings in expander
                with st.expander("⚙️ Advanced Settings"):
                    if sort_by_correlation and correlation_strategy in ["semantic", "hybrid"]:
                        similarity_threshold = st.slider(
                            "Similarity Threshold",
                            min_value=0.5,
                            max_value=0.9,
                            value=0.7,
                            step=0.1
                        )
                        max_cluster_size = st.slider(
                            "Max Cluster Size",
                            min_value=5,
                            max_value=30,
                            value=15,
                            step=5
                        )
                    else:
                        similarity_threshold = 0.7
                        max_cluster_size = 15
                    
                    if sort_by_correlation and correlation_strategy in ["substring", "hybrid"]:
                        min_substring_length = st.slider(
                            "Min Substring Length",
                            min_value=3,
                            max_value=15,
                            value=5,
                            step=1
                        )
                    else:
                        min_substring_length = 5
                
                # Process button
                if st.button("🚀 Process File", type="primary", use_container_width=True):
                    process_file(
                        dataset,
                        remove_duplicates,
                        "keep_first_with_occurrences",
                        sort_by_correlation,
                        correlation_strategy,
                        similarity_threshold,
                        max_cluster_size,
                        min_substring_length 
                    )
        
        # Main content area
        if st.session_state.dataset is not None:
            show_preview()
        else:
            show_welcome()

if __name__ == "__main__":
    main()
