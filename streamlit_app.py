import streamlit as st
import pandas as pd
import io
import time
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stringZ.models.data_models import TranslationDataset
from stringZ.core.processor import TranslationProcessor, ProcessingConfig

from stringZ.ui.tabs.results_tab import show_results
from stringZ.ui.tabs.review_tab import show_review_mode
from stringZ.ui.tabs.validation_tab import show_validation_tab


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
            uploaded_file = st.file_uploader(
                "Upload Translation File",
                type=['xlsx', 'xls'],
                help="Upload Excel file with strId, EN, and target language columns"
            )
            
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


def process_file(dataset, remove_duplicates, dedup_strategy, sort_by_correlation, 
                correlation_strategy, similarity_threshold, max_cluster_size, min_substring_length):
    """Process the uploaded file with given settings"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("⚙️ Initializing processing...")
        progress_bar.progress(20)
        
        # Create processing configuration
        config = ProcessingConfig(
            remove_duplicates=remove_duplicates,
            deduplication_strategy=dedup_strategy,
            sort_by_correlation=sort_by_correlation,
            correlation_strategy=correlation_strategy,
            similarity_threshold=similarity_threshold,
            max_cluster_size=max_cluster_size,
            min_substring_length=min_substring_length
        )
        
        processor = TranslationProcessor(config)
        
        status_text.text("🔄 Processing dataset...")
        progress_bar.progress(60)
        
        processed_dataset = processor.process(dataset)
        
        progress_bar.progress(90)
        status_text.text("📊 Generating statistics...")
        
        # Store results
        st.session_state.processed_dataset = processed_dataset
        st.session_state.processing_stats = processor.get_processing_stats(processed_dataset)
        
        progress_bar.progress(100)
        status_text.text("✅ Processing completed!")
        
        # Clear progress after a moment
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()
        
        st.success("✅ Processing completed!")
        st.rerun()
        
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Processing failed: {str(e)}")
        st.exception(e)


def show_welcome():
    """Show welcome screen with instructions"""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Welcome to StringZ! 🎉
        
        ### What this tool does:
        - **🔄 Removes duplicate translations** automatically
        - **🧠 Groups similar strings together** using AI
        - **⚠️ Validates translations** for formatting errors
        
        ### How to get started:
        1. **Upload your Excel file** using the sidebar
        2. **Choose processing options** (deduplication + correlation)
        3. **Click "Process File"** and get optimized results
        4. **Review translations** and **validate** for errors
        5. **Download the cleaned file** ready for translation work
        
        ### File Requirements:
        - Excel format (.xlsx or .xls)
        - Must contain: `strId`, `EN`, and target language columns
        """)
    
    with col2:
        st.markdown("""
        ### 🎯 Benefits:

        **For LQA Team:**
        - No more duplicate work
        - Similar strings grouped together
        - Automated error detection
        - Faster consistency checking
        - Translation validation
        """)


def show_preview():
    """Show preview of uploaded file before processing"""
    
    dataset = st.session_state.dataset
    
    st.subheader("📋 File Preview")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", len(dataset))
    
    with col2:
        duplicates = len(dataset.get_duplicates())
        st.metric("Duplicate Groups", duplicates)
    
    with col3:
        completion = dataset.get_completion_rate()
        st.metric("Completion Rate", f"{completion:.1f}%")
    
    with col4:
        # Calculate average string length
        avg_length = sum(len(entry.source_text) for entry in dataset.entries) / len(dataset.entries)
        st.metric("Avg String Length", f"{avg_length:.0f}")
    
    # Data preview
    df = dataset.to_dataframe()
    
    # Search functionality
    search_term = st.text_input("🔍 Search in translations", placeholder="Type to search...")
    if search_term:
        mask = (
            df[dataset.source_lang].str.contains(search_term, case=False, na=False) |
            (df[dataset.target_lang].str.contains(search_term, case=False, na=False) if dataset.target_lang in df.columns else False)
        )
        df_display = df[mask]
        st.write(f"Found {len(df_display)} matches")
    else:
        df_display = df.head(100) 
        if len(df) > 100:
            st.write(f"Showing first 100 of {len(df)} entries")
    
    st.dataframe(df_display, use_container_width=True, height=400)

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

def export_dataframe(df, name):
    """Export dataframe to Excel"""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)
    
    timestamp = int(time.time())
    st.download_button(
        label="📥 Download Excel File",
        data=buffer.getvalue(),
        file_name=f"stringz_{name}_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    main()
