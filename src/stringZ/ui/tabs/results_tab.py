import io
import os
import sys
import streamlit as st
import time
import re
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


from stringZ.export.visualizer import generate_visualizer_html


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
