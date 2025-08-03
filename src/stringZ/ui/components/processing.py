import time
import streamlit as st

from stringZ.core.processor import TranslationProcessor, ProcessingConfig

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
