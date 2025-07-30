import streamlit as st
import pandas as pd
import io
import time
import sys
import os
import re

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stringZ.models.data_models import TranslationDataset
from stringZ.core.processor import TranslationProcessor, ProcessingConfig
from stringZ.export.visualizer import generate_visualizer_html
from strinZ.validation.validators import run_validation

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

def show_results():
    """Modified show_results function with visualizer export"""
    
    processed_dataset = st.session_state.processed_dataset
    stats = st.session_state.processing_stats
    summary = stats['processing_summary']
    
    st.subheader("📊 Processing Results")

    # Compute word count
    df = processed_dataset.to_dataframe()
    target_lang = processed_dataset.target_lang
    word_count = 0
    if target_lang in df.columns:
        word_count = df[target_lang].dropna().astype(str).apply(lambda x: len(x.split())).sum()
    
    # Main metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
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
        st.metric("Groups Created", summary['clusters_created'])

    with col5:
        st.metric(f"{target_lang} Words", f"{word_count:,}")
    
    # MAIN DOWNLOAD SECTION - NEW LAYOUT
    st.subheader("📥 Export Processed Results")
    
    # Two-column layout for main downloads
    col1, col2 = st.columns(2)
    
    with col1:       
        # Generate filename for visualizer
        current_time = int(time.time())
        original_filename = getattr(st.session_state, 'original_filename', None)
        
        if original_filename:
            clean_name = re.sub(r'\.[^.]+$', '', original_filename)
            visualizer_filename = f"Visualizer-{clean_name}.html"
        else:
            visualizer_filename = f"StringZ-Visualizer-{processed_dataset.target_lang}-{current_time}.html"
        
        # Generate visualizer HTML
        try:
            visualizer_html = generate_visualizer_html(processed_dataset, original_filename)
            
            st.download_button(
                label="Download Visualizer",
                data=visualizer_html.encode('utf-8'),
                file_name=visualizer_filename,
                mime="text/html",
                type="primary",
                use_container_width=True,
                help="Interactive HTML file for LQA Raw/Formatted Data"
            )
            
        except Exception as e:
            st.error(f"Error generating visualizer: {str(e)}")
            st.exception(e)
    
    with col2:
        df_processed = processed_dataset.to_dataframe()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_processed.to_excel(writer, sheet_name='Processed_Translations', index=False)
        
        st.download_button(
            label="📊 Download Processed Spreadsheet",
            data=buffer.getvalue(),
            file_name=f"StringZ-Processed-{current_time}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary",
            use_container_width=True,
            help="Excel file with processed translations, duplicates removed, and strings organized"
        )       
    
    # Additional download options (smaller)
    st.markdown("---")
    st.markdown("**Additional Export Options:**")
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
                    label=f"❌ Missing Only ({len(missing_df)} strings)",
                    data=missing_buffer.getvalue(),
                    file_name=f"StringZ-Missing-{current_time}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    with col2:
        # High priority strings (high occurrences)
        if 'Occurrences' in df_processed.columns:
            priority_df = df_processed[df_processed['Occurrences'] > 5]
            if len(priority_df) > 0:
                priority_buffer = io.BytesIO()
                with pd.ExcelWriter(priority_buffer, engine='openpyxl') as writer:
                    priority_df.to_excel(writer, sheet_name='Priority_Strings', index=False)
                
                st.download_button(
                    label=f"⭐ High Priority ({len(priority_df)} strings)",
                    data=priority_buffer.getvalue(),
                    file_name=f"StringZ-Priority-{current_time}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

def show_review_mode():
    """LQA-focused review interface for consistency checking"""
    processed_dataset = st.session_state.processed_dataset
    
    st.title("🔍 Translation Review")
    st.markdown("**Review similar strings grouped together for consistency checking**")
    
    # Get the dataframe
    df = processed_dataset.to_dataframe()
    
    # Simple controls focused on review workflow
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        search_term = st.text_input(
            "🔍 Find specific strings", 
            placeholder="Search for specific content to review...",
            key="review_search"
        )
    
    with col2:
        # Simple per page options with "All" for consistency checking
        per_page_options = [50, 100, 250, "All"]
        entries_per_page = st.selectbox("📄 Per Page", per_page_options, index=1)
    
    with col3:
        # Focus only on translation-relevant filters
        review_filters = ["All Strings", "Missing Translations", "High Priority (>5 uses)"]
        filter_choice = st.selectbox("📋 Show", review_filters)
    
    # Apply focused filters
    filtered_df = df.copy()
    
    # Search filter
    if search_term:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    # Review-focused filters
    if filter_choice == "Missing Translations":
        filtered_df = filtered_df[filtered_df[processed_dataset.target_lang].isna()]
    elif filter_choice == "High Priority (>5 uses)" and 'Occurrences' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Occurrences'] > 5]
    
    # Show info about the correlation sorting
    if search_term:
        st.info(f"🔍 Found **{len(filtered_df)}** matches. Strings are sorted by similarity to help spot inconsistencies.")
    else:
        st.info("✨ **Strings are automatically sorted by similarity** - similar strings appear together to make consistency checking easier!")
    
    # Stats focused on review work
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Strings to Review", len(filtered_df))
    with col2:
        if processed_dataset.target_lang in filtered_df.columns and len(filtered_df) > 0:
            missing_count = filtered_df[processed_dataset.target_lang].isna().sum()
            st.metric("❌ Missing Translations", missing_count)
    with col3:
        if 'Occurrences' in filtered_df.columns and len(filtered_df) > 0:
            high_priority = (filtered_df['Occurrences'] > 5).sum()
            st.metric("⭐ High Priority", high_priority)
    
    # Pagination or show all
    total_entries = len(filtered_df)
    
    if entries_per_page == "All":
        # Show all entries - great for consistency checking
        page_df = filtered_df.reset_index(drop=True)
        if total_entries > 500:
            st.warning("⚠️ Showing all entries for consistency review. This might take a moment to load.")
        st.caption(f"Showing all {total_entries} strings (sorted by similarity)")
    else:
        # Paginated view
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
            
            st.caption(f"Showing strings {start_idx + 1}-{end_idx} of {total_entries} (sorted by similarity)")
        else:
            page_df = filtered_df.reset_index(drop=True)
    
    # Column configuration optimized for translation review
    column_config = {
        "strId": st.column_config.TextColumn(
            "ID", 
            width="small",
            help="String identifier"
        ),
        processed_dataset.source_lang: st.column_config.TextColumn(
            "English", 
            width="large",
            help="Source text to translate"
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
            "Uses", 
            width="small",
            help="How many times this string appears in the game"
        )
    
    # Display the review table
    st.dataframe(
        page_df,
        use_container_width=True,
        height=600 if entries_per_page != "All" else None,
        column_config=column_config,
        hide_index=True
    )
    
    # Simple export for review work
    st.subheader("📥 Export for Translation")
    col1, col2 = st.columns(2)
    st.write("WIP - Stay Tuned!")
    
    # with col1:
    #     if st.button("📊 Export Current View", use_container_width=True):
    #         export_dataframe(page_df, "review_current")
    
    # with col2:
    #     if st.button("📋 Export All Filtered", use_container_width=True):
    #         export_dataframe(filtered_df, "review_filtered")


def show_validation_tab():
    """LQA validation tab - SIMPLE AND CLEAN"""
    processed_dataset = st.session_state.processed_dataset
    
    st.title("⚠️ LQA Validation")
    st.markdown("**Automated validation for game translation formatting and consistency**")
    
    # Validation controls
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **This validation checks for:**
        - 🎯 **Token mismatches** (color tags, variables, brackets)
        - 🏷️ **Malformed game tags** (extra characters, unmatched tags)
        - 📝 **Punctuation inconsistencies** (missing or different endings)
        - 🔢 **Numeric value differences** in color tags
        - 🎮 **Game element consistency** (abilities, skills, colors)
        """)
    
    with col2:
        if st.button("🔍 Run Validation", type="primary", use_container_width=True):
            with st.spinner("🔍 Validating translations..."):
                validation_results = run_validation(processed_dataset)
                st.session_state.validation_results = validation_results
                st.success("✅ Validation completed!")
                st.rerun()
    
    # Show validation results if available
    if st.session_state.validation_results:
        results = st.session_state.validation_results
        
        # Summary metrics
        st.subheader("📊 Validation Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Strings", results['total_strings'])
        
        with col2:
            st.metric("Issues Found", results['issues_found'])
        
        with col3:
            st.metric("Critical Issues", results['critical_issues'], 
                     delta=None if results['critical_issues'] == 0 else f"❌ {results['critical_issues']}")
        
        with col4:
            st.metric("Warnings", results['warnings'],
                     delta=None if results['warnings'] == 0 else f"⚠️ {results['warnings']}")
        
        if results['issues_found'] == 0:
            st.success("🎉 **No validation issues found!** Your translations look great.")
            return
        
        # Filter and display options
        st.subheader("🔍 Issue Details")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            issue_filter = st.selectbox(
                "Filter by Issue Type",
                ["All Issues"] + list(set(issue['type'] for issue in results['detailed_issues']))
            )
        
        with col2:
            severity_filter = st.selectbox(
                "Filter by Severity",
                ["All Severities", "CRITICAL", "WARNING"]
            )
        
        with col3:
            per_page = st.selectbox("Issues per page", [10, 25, 50, "All"], index=1)
        
        # Filter issues
        filtered_issues = results['detailed_issues']
        
        if issue_filter != "All Issues":
            filtered_issues = [issue for issue in filtered_issues if issue['type'] == issue_filter]
        
        if severity_filter != "All Severities":
            filtered_issues = [issue for issue in filtered_issues if issue['severity'] == severity_filter]
        
        st.write(f"Showing {len(filtered_issues)} of {results['issues_found']} issues")
        
        # Pagination for issues
        if per_page != "All" and len(filtered_issues) > per_page:
            total_pages = (len(filtered_issues) + per_page - 1) // per_page
            page = st.selectbox("Page", range(1, total_pages + 1))
            
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, len(filtered_issues))
            page_issues = filtered_issues[start_idx:end_idx]
        else:
            page_issues = filtered_issues
        
        # Display issues - SIMPLE AND CLEAN
        for i, issue in enumerate(page_issues, 1):
            severity_icon = "🚨" if issue['severity'] == 'CRITICAL' else "⚠️"
            
            # Create clean header for easy identification
            issue_header = f"{severity_icon} {issue['str_id']} - {issue['type']}"
            
            with st.expander(issue_header, expanded=i<=3):
                
                # SIMPLE ISSUE SUMMARY
                st.markdown("### 📋 Issue Summary")
                
                # Use columns for clean layout
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.markdown("**String ID:**")
                    st.markdown("**Issue:**")
                    st.markdown("**English:**")
                    st.markdown(f"**{processed_dataset.target_lang}:**")
                
                with col2:
                    st.markdown(f"`{issue['str_id']}`")
                    st.markdown(f"{issue['type']} - {issue['detail']}")
                    st.markdown(f"`{issue['en_text']}`")
                    st.markdown(f"`{issue['target_text']}`")
                

        # Export validation results
        st.subheader("📥 Export Validation Report")
        
        # col1, col2 = st.columns(2)
        
        # with col1:
        #     if st.button("📊 Download Issues Report", use_container_width=True):
        #         # Create issues dataframe
        #         issues_data = []
        #         for issue in results['detailed_issues']:
        #             issues_data.append({
        #                 'strId': issue['str_id'],
        #                 'Issue Type': issue['type'],
        #                 'Severity': issue['severity'],
        #                 'Detail': issue['detail'],
        #                 'English Text': issue['en_text'],
        #                 f'{processed_dataset.target_lang} Text': issue['target_text']
        #             })
                
        #         issues_df = pd.DataFrame(issues_data)
        #         export_dataframe(issues_df, "validation_issues")
        
        # with col2:
        #     if st.button("🚨 Download Critical Issues Only", use_container_width=True):
        #         # Create critical issues dataframe
        #         critical_data = []
        #         for issue in results['detailed_issues']:
        #             if issue['severity'] == 'CRITICAL':
        #                 critical_data.append({
        #                     'strId': issue['str_id'],
        #                     'Issue Type': issue['type'],
        #                     'Detail': issue['detail'],
        #                     'English Text': issue['en_text'],
        #                     f'{processed_dataset.target_lang} Text': issue['target_text']
        #                 })
                
        #         if critical_data:
        #             critical_df = pd.DataFrame(critical_data)
        #             export_dataframe(critical_df, "critical_issues")
        #         else:
        #             st.info("No critical issues to export!")

        st.write("WIP - Stay Tuned!")

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
