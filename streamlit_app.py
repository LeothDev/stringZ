import streamlit as st
import subprocess
import pandas as pd
import io
import time
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import our core modules
from stringZ.models.data_models import TranslationDataset
from stringZ.core.processor import TranslationProcessor, ProcessingConfig

# Configure Streamlit
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

def main():
    # Header
    st.image(image="https://cdn.moogold.com/2024/10/watcher-of-realms.jpg", width=100)
    st.title("🎮 StringZ")
    st.markdown("**Translation QA Tool for ZGAME**")
    st.markdown("*Deduplicate translations and sort by semantic correlation*")
    st.markdown("""
    <style>
    /* Enable text wrapping in dataframe cells */
    .stDataFrame [data-testid="stDataFrameResizable"] div[data-testid="cell"] {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        max-width: 300px !important;
        overflow-wrap: break-word !important;
    }
    
    /* Adjust row height to accommodate wrapped text */
    .stDataFrame [data-testid="stDataFrameResizable"] {
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if we have processed data to show tabs
    if st.session_state.processed_dataset is not None:
        # Show tabs when data is processed
        tab1, tab2 = st.tabs(["📊 Results", "📋 Data Viewer"])
        
        with tab1:
            show_results()
        
        with tab2:
            show_full_dataframe_viewer()
            
        # Sidebar with reset option
        with st.sidebar:
            st.header("🔄 Process New File")
            
            if st.button("🆕 Start Over", type="secondary", use_container_width=True):
                st.session_state.dataset = None
                st.session_state.processed_dataset = None
                st.session_state.processing_stats = None
                st.rerun()
            
            st.markdown("---")
            dataset = st.session_state.processed_dataset
            st.write(f"📝 **{len(dataset)}** entries")
            st.write(f"🌍 **{dataset.source_lang}** → **{dataset.target_lang}**")
    
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
                sort_by_correlation = st.checkbox("Sort by Correlation", value=True)
                
                correlation_strategy = st.selectbox(
                    "Correlation Method",
                    ["hybrid", "substring", "semantic", "occurrences", "alphabetical"],
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
        
        ### How to get started:
        1. **Upload your Excel file** using the sidebar
        2. **Choose processing options** (deduplication + correlation)
        3. **Click "Process File"** and get optimized results
        4. **Download the cleaned file** ready for translation work
        
        ### File Requirements:
        - Excel format (.xlsx or .xls)
        - Must contain: `strId`, `EN`, and target language columns
        """)
    
    with col2:
        st.markdown("""
        ### 🎯 Benefits:

        **For LQA Team:**
        - No more duplicate work
        - Related strings grouped together
        - Easier consistency checking
        - Faster localization
        """)


def show_preview():
    """Show preview of uploaded file before processing"""
    
    dataset = st.session_state.dataset
    
    st.subheader("📋 File Preview")
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Entries", len(dataset))
    
    with col2:
        duplicates = len(dataset.get_duplicates())
        st.metric("Duplicate Groups", duplicates)
    
    with col3:
        completion = dataset.get_completion_rate()
        st.metric("Completion Rate", f"{completion:.1f}%")
    
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


def show_results():
    """Show processing results with download button"""
    
    processed_dataset = st.session_state.processed_dataset
    stats = st.session_state.processing_stats
    summary = stats['processing_summary']
    
    st.subheader("📊 Processing Results")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Original Entries", summary['original_count'])
    
    with col2:
        st.metric(
            "Final Entries",
            summary['final_count'],
            delta=-summary['duplicates_removed'] if summary['duplicates_removed'] > 0 else None
        )
    
    with col3:
        st.metric("Duplicates Removed", summary['duplicates_removed'])
    
    with col4:
        st.metric("Clusters Created", summary['clusters_created'])
    
    # MAIN DOWNLOAD SECTION - PROMINENTLY PLACED
    st.subheader("📥 Download Processed File")
    
    df_processed = processed_dataset.to_dataframe()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_processed.to_excel(writer, sheet_name='Processed_Translations', index=False)
    
    # MAIN DOWNLOAD BUTTON
    st.download_button(
        label="📊 Download Processed Translation File",
        data=buffer.getvalue(),
        file_name=f"stringz_processed_{int(time.time())}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        help="Download the complete processed file with duplicates removed and strings organized"
    )
    
    # Additional download options
    st.markdown("**Additional Downloads:**")
    col1, col2 = st.columns(2)
    
    with col1:
        # Missing translations only
        if processed_dataset.target_lang in df_processed.columns:
            missing_df = df_processed[df_processed[processed_dataset.target_lang].isna()]
            if len(missing_df) > 0:
                missing_buffer = io.BytesIO()
                with pd.ExcelWriter(missing_buffer, engine='openpyxl') as writer:
                    missing_df.to_excel(writer, sheet_name='Missing_Translations', index=False)
                
                st.download_button(
                    label=f"❌ Download Missing Only ({len(missing_df)} strings)",
                    data=missing_buffer.getvalue(),
                    file_name=f"stringz_missing_{int(time.time())}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    with col2:
        # High priority strings (high occurrences)
        if 'Occurrences' in df_processed.columns:
            priority_df = df_processed[df_processed['Occurrences'] > 3]
            if len(priority_df) > 0:
                priority_buffer = io.BytesIO()
                with pd.ExcelWriter(priority_buffer, engine='openpyxl') as writer:
                    priority_df.to_excel(writer, sheet_name='Priority_Strings', index=False)
                
                st.download_button(
                    label=f"⭐ Download High Priority ({len(priority_df)} strings)",
                    data=priority_buffer.getvalue(),
                    file_name=f"stringz_priority_{int(time.time())}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    # Show clusters if any
    cluster_details = stats.get('cluster_details', [])
    if cluster_details:
        st.subheader("🧠 String Clusters")
        with st.expander(f"View {len(cluster_details)} clusters created"):
            for i, cluster in enumerate(cluster_details, 1):
                cluster_type_emoji = "🔗" if cluster['cluster_type'] == "substring" else "🧠"
                st.write(f"**{cluster_type_emoji} Cluster {i}:** {cluster['size']} strings ({cluster['cluster_type']})")
                for j, text in enumerate(cluster['sample_texts'], 1):
                    st.write(f"  {j}. {text}")
                st.write("---")

def show_full_dataframe_viewer():
    """Full dataframe viewer with search and filtering"""
    processed_dataset = st.session_state.processed_dataset
    
    st.title("📊 Data Viewer")
    
    # Get the dataframe
    df = processed_dataset.to_dataframe()
    
    # Controls
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Search in all columns", 
            placeholder="Type to search across all text...",
            key="full_search"
        )
    
    with col2:
        filter_options = ["Show All", "High Occurrences (>5)", "No Translation"]
        filter_choice = st.selectbox("📋 Filter", filter_options)
    
    with col3:
        entries_per_page = st.selectbox("📄 Per Page", [25, 50, 100, 200], index=1)
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_term:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
        st.info(f"🔍 Found **{len(filtered_df)}** matches")
    
    if filter_choice == "High Occurrences (>5)" and 'Occurrences' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Occurrences'] > 5]
    elif filter_choice == "No Translation":
        filtered_df = filtered_df[filtered_df[processed_dataset.target_lang].isna()]
    
    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Entries", len(filtered_df))
    with col2:
        if 'Occurrences' in filtered_df.columns:
            avg_occ = filtered_df['Occurrences'].mean()
            st.metric("📊 Avg Occurrences", f"{avg_occ:.1f}")
    with col3:
        if processed_dataset.target_lang in filtered_df.columns:
            completion_rate = (filtered_df[processed_dataset.target_lang].notna().sum() / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.metric("✅ Completion", f"{completion_rate:.1f}%")
    
    # Pagination
    total_entries = len(filtered_df)
    total_pages = (total_entries + entries_per_page - 1) // entries_per_page
    
    if total_pages > 1:
        page = st.selectbox(
            "📄 Page", 
            range(1, total_pages + 1), 
            format_func=lambda x: f"Page {x} of {total_pages}"
        )
        
        start_idx = (page - 1) * entries_per_page
        end_idx = min(start_idx + entries_per_page, total_entries)
        page_df = filtered_df.iloc[start_idx:end_idx].reset_index(drop=True)
        
        st.caption(f"Showing entries {start_idx + 1}-{end_idx} of {total_entries}")
    else:
        page_df = filtered_df.reset_index(drop=True)
    
    # ENHANCED Display dataframe with better text wrapping
    column_config = {
        "strId": st.column_config.TextColumn(
            "String ID", 
            width="small",
            help="Unique identifier"
        ),
        processed_dataset.source_lang: st.column_config.TextColumn(
            processed_dataset.source_lang, 
            width="large",
            help="English source text"
        ),
    }
    
    if processed_dataset.target_lang in page_df.columns:
        column_config[processed_dataset.target_lang] = st.column_config.TextColumn(
            processed_dataset.target_lang, 
            width="large",
            help=f"Translation in {processed_dataset.target_lang}"
        )
    
    if 'Occurrences' in page_df.columns:
        column_config["Occurrences"] = st.column_config.NumberColumn(
            "Occurrences", 
            width="small",
            help="Number of times this string appears"
        )
    
    st.dataframe(
        page_df,
        use_container_width=True,
        height=600,
        column_config=column_config,
        hide_index=True
    )
    
    # Export options
    st.subheader("📥 Export Options")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export Current View", use_container_width=True):
            export_dataframe(page_df, "current_view")
    
    with col2:
        if st.button("📋 Export All Filtered", use_container_width=True):
            export_dataframe(filtered_df, "filtered_data")

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
