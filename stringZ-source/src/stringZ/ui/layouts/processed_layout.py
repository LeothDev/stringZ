import streamlit as st
from ..tabs.results_tab import show_results
from ..tabs.review_tab import show_review_mode
from ..tabs.validation_tab import show_validation_tab

def render_processed_layout():
    """Layout for when data has been processed - shows tabs and stats sidebar"""
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Results", "🔍 Review Translations", "⚠️ LQA Validation"])
    
    with tab1:
        show_results()
    
    with tab2:
        show_review_mode()
        
    with tab3:
        show_validation_tab()
    
    # Sidebar with stats and reset option
    render_processed_sidebar()

def render_processed_sidebar():
    """Sidebar for processed data with stats and reset button"""
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
        
        # Quick stats
        df = dataset.to_dataframe()
        if 'Occurrences' in df.columns:
            avg_occ = df['Occurrences'].mean()
            max_occ = df['Occurrences'].max()
            st.write(f"📊 Avg occurrences: **{avg_occ:.1f}**")
            st.write(f"🔥 Max occurrences: **{max_occ}**")
        
        if dataset.target_lang in df.columns:
            completion_rate = (df[dataset.target_lang].notna().sum() / len(df) * 100)
            st.write(f"✅ Completion: **{completion_rate:.1f}%**")
